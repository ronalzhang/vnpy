#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库字段修复脚本
修复score字段问题，添加缺失的表和字段
"""

import sqlite3
import json
from datetime import datetime

class DatabaseFieldFix:
    """数据库字段修复器"""
    
    def __init__(self):
        self.db_path = "quantitative.db"
        
    def log(self, message: str):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}")
    
    def fix_strategies_table(self):
        """修复strategies表，添加缺失的字段"""
        self.log("🔧 修复strategies表...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取现有列
            cursor.execute("PRAGMA table_info(strategies)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            # 添加缺失的字段
            fields_to_add = [
                ('score', 'REAL DEFAULT 0.0'),
                ('generation', 'INTEGER DEFAULT 1'),
                ('cycle', 'INTEGER DEFAULT 1'),
                ('protected_status', 'INTEGER DEFAULT 0'),
                ('is_persistent', 'INTEGER DEFAULT 1'),
                ('qualified_for_trading', 'INTEGER DEFAULT 0')
            ]
            
            for field_name, field_definition in fields_to_add:
                if field_name not in columns:
                    try:
                        cursor.execute(f"ALTER TABLE strategies ADD COLUMN {field_name} {field_definition}")
                        self.log(f"✅ 添加字段: {field_name}")
                    except Exception as e:
                        self.log(f"⚠️ 字段{field_name}可能已存在: {e}")
            
            # 如果没有score字段，但有final_score，复制数据
            if 'score' not in columns and 'final_score' in columns:
                cursor.execute("UPDATE strategies SET score = final_score WHERE score IS NULL OR score = 0")
                self.log("✅ 已将final_score复制到score字段")
            
            conn.commit()
            conn.close()
            
            self.log("✅ strategies表修复完成")
            return True
            
        except Exception as e:
            self.log(f"❌ 修复strategies表失败: {e}")
            return False
    
    def create_missing_tables(self):
        """创建缺失的表"""
        self.log("🗄️ 创建缺失的表...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建strategy_rolling_metrics表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_rolling_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT,
                    metric_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    rolling_window INTEGER DEFAULT 30,
                    rolling_return REAL DEFAULT 0.0,
                    rolling_volatility REAL DEFAULT 0.0,
                    rolling_sharpe REAL DEFAULT 0.0,
                    rolling_max_drawdown REAL DEFAULT 0.0,
                    rolling_win_rate REAL DEFAULT 0.0,
                    performance_trend TEXT DEFAULT 'stable',
                    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
                )
            """)
            
            # 检查system_settings表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            
            self.log("✅ 缺失表创建完成")
            return True
            
        except Exception as e:
            self.log(f"❌ 创建表失败: {e}")
            return False
    
    def test_api_with_proxy(self):
        """使用代理测试API连接"""
        self.log("🔍 测试API连接（使用代理）...")
        
        try:
            import requests
            import hmac
            import hashlib
            import urllib.parse
            
            # 读取配置
            with open("crypto_config.json", 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            
            # 创建测试请求
            import time
            params = {
                'timestamp': int(time.time() * 1000),
                'recvWindow': 60000
            }
            
            query_string = urllib.parse.urlencode(params)
            signature = hmac.new(
                api_secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            query_string += f"&signature={signature}"
            
            headers = {
                'X-MBX-APIKEY': api_key,
                'Content-Type': 'application/json'
            }
            
            # 使用不同的URL尝试
            urls = [
                f"https://api.binance.com/api/v3/account?{query_string}",
                f"https://api1.binance.com/api/v3/account?{query_string}",
                f"https://api2.binance.com/api/v3/account?{query_string}"
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        usdt_balance = 0.0
                        position_count = 0
                        
                        for balance in data.get('balances', []):
                            if balance['asset'] == 'USDT':
                                usdt_balance = float(balance['free']) + float(balance['locked'])
                            elif float(balance['free']) + float(balance['locked']) > 0:
                                position_count += 1
                        
                        self.log(f"✅ API连接成功！")
                        self.log(f"💰 USDT余额: {usdt_balance:.2f}U")
                        self.log(f"📊 持仓币种数: {position_count}")
                        return True
                    else:
                        self.log(f"⚠️ API返回错误: {response.status_code} - {response.text[:100]}")
                        
                except requests.exceptions.Timeout:
                    self.log(f"⚠️ 连接超时，尝试下一个URL...")
                    continue
                except Exception as e:
                    self.log(f"⚠️ 请求失败: {e}")
                    continue
            
            self.log("❌ 所有API端点都无法连接")
            return False
                
        except Exception as e:
            self.log(f"❌ 测试API连接失败: {e}")
            return False
    
    def run_database_fix(self):
        """运行数据库修复"""
        self.log("🚀 开始数据库修复...")
        
        results = {}
        
        # 1. 修复strategies表
        results['strategies_fixed'] = self.fix_strategies_table()
        
        # 2. 创建缺失的表
        results['tables_created'] = self.create_missing_tables()
        
        # 3. 重新测试API
        results['api_test'] = self.test_api_with_proxy()
        
        self.log("🎉 数据库修复完成！")
        
        return results

if __name__ == "__main__":
    fixer = DatabaseFieldFix()
    result = fixer.run_database_fix()
    
    print("\n" + "="*50)
    print("📊 数据库修复结果:")
    print(f"表结构修复: {'✅' if result['strategies_fixed'] else '❌'}")
    print(f"缺失表创建: {'✅' if result['tables_created'] else '❌'}")
    print(f"API连接测试: {'✅' if result['api_test'] else '❌'}")
    print("="*50) 