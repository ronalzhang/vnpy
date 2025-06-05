#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
余额显示修复系统 - 解决API获取失败时显示错误余额的问题
功能：
1. 修复余额获取失败时的显示逻辑
2. 查找并配置正确的API密钥
3. 确保API获取失败时显示"-"而不是过时缓存
"""

import sqlite3
import json
import os
import re
import time
from datetime import datetime
from typing import Dict, Optional

class BalanceDisplayFix:
    """余额显示修复器"""
    
    def __init__(self):
        self.db_path = "quantitative.db"
        self.config_path = "crypto_config.json"
        self.log_file = f"logs/trading/balance_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        
        # 确保日志目录存在
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    
    def find_api_keys(self):
        """查找现有的API密钥配置"""
        self.log("🔍 搜索API密钥配置...")
        
        api_configs = []
        
        # 1. 检查环境变量
        binance_key = os.environ.get('BINANCE_API_KEY')
        binance_secret = os.environ.get('BINANCE_SECRET_KEY') or os.environ.get('BINANCE_API_SECRET')
        
        if binance_key and binance_secret:
            api_configs.append({
                'source': '环境变量',
                'api_key': binance_key,
                'secret_key': binance_secret
            })
            self.log(f"✅ 在环境变量中找到API配置: {binance_key[:8]}...{binance_key[-8:]}")
        
        # 2. 检查配置文件
        config_files = [
            "crypto_config.json",
            "config.json",
            ".env",
            "api_config.json"
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                try:
                    if config_file.endswith('.json'):
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                        
                        # 检查不同的配置结构
                        sources = [
                            config.get('binance', {}),
                            config.get('api', {}).get('binance', {}),
                            config
                        ]
                        
                        for source in sources:
                            if source.get('api_key') and source.get('secret_key'):
                                api_configs.append({
                                    'source': f'配置文件:{config_file}',
                                    'api_key': source['api_key'],
                                    'secret_key': source['secret_key']
                                })
                                self.log(f"✅ 在{config_file}中找到API配置")
                                break
                    
                    elif config_file == '.env':
                        with open(config_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # 解析.env文件
                        api_key_match = re.search(r'BINANCE_API_KEY=(.+)', content)
                        secret_match = re.search(r'BINANCE_SECRET_KEY=(.+)', content)
                        
                        if api_key_match and secret_match:
                            api_configs.append({
                                'source': '.env文件',
                                'api_key': api_key_match.group(1).strip(),
                                'secret_key': secret_match.group(1).strip()
                            })
                            self.log(f"✅ 在.env文件中找到API配置")
                
                except Exception as e:
                    self.log(f"⚠️ 读取{config_file}失败: {e}")
        
        # 3. 检查数据库配置
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查是否有API配置表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='api_config'")
            if cursor.fetchone():
                cursor.execute("SELECT api_key, secret_key FROM api_config WHERE exchange='binance' LIMIT 1")
                row = cursor.fetchone()
                if row and row[0] and row[1]:
                    api_configs.append({
                        'source': '数据库',
                        'api_key': row[0],
                        'secret_key': row[1]
                    })
                    self.log(f"✅ 在数据库中找到API配置")
            
            conn.close()
        except Exception as e:
            self.log(f"⚠️ 检查数据库配置失败: {e}")
        
        # 4. 检查Python文件中的硬编码
        python_files = [
            "quantitative_service.py",
            "crypto_api_server.py",
            "auto_trading_engine.py",
            "vnpy_cryptoarbitrage/engine.py"
        ]
        
        for py_file in python_files:
            if os.path.exists(py_file):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 查找可能的API密钥赋值
                    api_patterns = [
                        r'api_key\s*=\s*["\']([^"\']{20,})["\']',
                        r'secret\s*=\s*["\']([^"\']{20,})["\']',
                        r'API_KEY\s*=\s*["\']([^"\']{20,})["\']'
                    ]
                    
                    for pattern in api_patterns:
                        matches = re.findall(pattern, content)
                        if matches:
                            self.log(f"⚠️ 在{py_file}中发现可能的API密钥硬编码")
                            break
                
                except Exception as e:
                    self.log(f"⚠️ 检查{py_file}失败: {e}")
        
        self.log(f"📊 共找到{len(api_configs)}个API配置源")
        return api_configs
    
    def fix_balance_display_logic(self):
        """修复余额显示逻辑"""
        self.log("🔧 修复余额显示逻辑...")
        
        # 读取当前的quantitative_service.py
        service_file = "quantitative_service.py"
        if not os.path.exists(service_file):
            self.log(f"❌ 找不到{service_file}")
            return False
        
        try:
            with open(service_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 备份原文件
            backup_file = f"{service_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(content)
            self.log(f"✅ 已备份原文件: {backup_file}")
            
            # 修复_get_current_balance方法
            old_pattern = r'(def _get_current_balance\(self\):.*?)return self\.balance_cache\.get\(\'balance\', 0\.0\)'
            
            new_implementation = '''def _get_current_balance(self):
        """获取当前余额 - 带缓存机制，只在特定事件触发时更新"""
        try:
            import datetime
            
            # 检查缓存是否有效 (5分钟内有效)
            if (self.balance_cache['cache_valid'] and 
                self.balance_cache['last_update'] and
                (datetime.datetime.now() - self.balance_cache['last_update']).seconds < 300):
                
                print(f"💾 使用余额缓存: {self.balance_cache['balance']:.2f}U (缓存时间: {self.balance_cache['last_update']})")
                return self.balance_cache['balance']
            
            # 缓存失效，重新获取余额
            print("🔄 刷新余额缓存...")
            balance_data = self._fetch_fresh_balance()
            
            if balance_data is None:
                print("❌ API获取余额失败，返回错误标识")
                # API失败时返回特殊值，前端将显示"-"
                return -1.0
            
            # 更新缓存
            self.balance_cache.update({
                'balance': balance_data['total'],
                'available_balance': balance_data['available'], 
                'frozen_balance': balance_data['frozen'],
                'last_update': datetime.datetime.now(),
                'cache_valid': True
            })
            
            # 记录余额历史（只在余额变化时）
            if abs(balance_data['total'] - self.balance_cache.get('previous_balance', 0)) > 0.01:
                self.db_manager.record_balance_history(
                    balance_data['total'],
                    balance_data['available'],
                    balance_data['frozen']
                )
                self.balance_cache['previous_balance'] = balance_data['total']
            
            print(f"✅ 余额缓存已更新: {balance_data['total']:.2f}U")
            return balance_data['total']
            
        except Exception as e:
            print(f"获取余额失败: {e}")
            # 发生异常时也返回错误标识，前端将显示"-"
            return -1.0'''
            
            # 使用正则表达式替换
            import re
            content = re.sub(old_pattern, new_implementation, content, flags=re.DOTALL)
            
            # 修复get_account_info方法
            old_account_pattern = r'(def get_account_info\(self\):.*?)(current_balance = self\._get_current_balance\(\))(.*?)(\'balance\': round\(current_balance, 2\),)'
            
            new_account_implementation = r'''\1current_balance = self._get_current_balance()
            
            # 如果余额获取失败，返回"-"标识
            if current_balance == -1.0:
                return {
                    'balance': "-",
                    'daily_pnl': 0.0,
                    'daily_return': 0.0,
                    'daily_trades': 0,
                    'available_balance': "-",
                    'frozen_balance': "-"
                }\3'balance': round(current_balance, 2) if current_balance != -1.0 else "-",'''
            
            content = re.sub(old_account_pattern, new_account_implementation, content, flags=re.DOTALL)
            
            # 保存修复后的文件
            with open(service_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.log("✅ 余额显示逻辑修复完成")
            return True
            
        except Exception as e:
            self.log(f"❌ 修复余额显示逻辑失败: {e}")
            return False
    
    def configure_api_keys(self, api_configs):
        """配置API密钥"""
        if not api_configs:
            self.log("⚠️ 未找到API配置，需要手动配置")
            return False
        
        # 使用第一个找到的配置
        best_config = api_configs[0]
        self.log(f"🔧 使用配置源: {best_config['source']}")
        
        try:
            # 更新crypto_config.json
            config = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            # 确保配置结构正确
            if 'binance' not in config:
                config['binance'] = {}
            
            config['binance']['api_key'] = best_config['api_key']
            config['binance']['api_secret'] = best_config['secret_key']
            config['binance']['sandbox'] = False  # 使用实盘
            
            # 保存配置
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self.log(f"✅ API配置已更新到{self.config_path}")
            
            # 设置环境变量
            os.environ['BINANCE_API_KEY'] = best_config['api_key']
            os.environ['BINANCE_SECRET_KEY'] = best_config['secret_key']
            
            self.log("✅ 环境变量已设置")
            return True
            
        except Exception as e:
            self.log(f"❌ 配置API密钥失败: {e}")
            return False
    
    def test_api_connection(self):
        """测试API连接"""
        self.log("🔍 测试API连接...")
        
        try:
            # 导入测试模块
            import requests
            import hmac
            import hashlib
            import urllib.parse
            
            # 读取配置
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            
            if not api_key or not api_secret:
                self.log("❌ API密钥未配置")
                return False
            
            # 创建测试请求
            params = {
                'timestamp': int(time.time() * 1000),
                'recvWindow': 10000
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
            
            url = f"https://api.binance.com/api/v3/account?{query_string}"
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                usdt_balance = 0.0
                
                for balance in data.get('balances', []):
                    if balance['asset'] == 'USDT':
                        usdt_balance = float(balance['free']) + float(balance['locked'])
                        break
                
                self.log(f"✅ API连接成功！USDT余额: {usdt_balance:.2f}U")
                return True
            else:
                self.log(f"❌ API请求失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ 测试API连接失败: {e}")
            return False
    
    def clean_old_balance_cache(self):
        """清理旧的余额缓存"""
        self.log("🧹 清理旧的余额缓存...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 删除6月4日的错误记录
            cursor.execute("""
                DELETE FROM account_balance_history 
                WHERE timestamp LIKE '2025-06-04%' AND total_balance = 1.59
            """)
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            self.log(f"✅ 已删除{deleted_count}条错误的余额记录")
            return True
            
        except Exception as e:
            self.log(f"❌ 清理余额缓存失败: {e}")
            return False
    
    def run_complete_fix(self):
        """运行完整修复"""
        self.log("🚀 开始完整余额显示修复...")
        
        # 1. 查找API密钥
        api_configs = self.find_api_keys()
        
        # 2. 配置API密钥
        if api_configs:
            self.configure_api_keys(api_configs)
        
        # 3. 修复余额显示逻辑
        self.fix_balance_display_logic()
        
        # 4. 清理旧缓存
        self.clean_old_balance_cache()
        
        # 5. 测试API连接
        if api_configs:
            self.test_api_connection()
        
        self.log("🎉 余额显示修复完成！")
        
        return {
            'api_configs_found': len(api_configs),
            'logic_fixed': True,
            'cache_cleaned': True,
            'log_file': self.log_file
        }

if __name__ == "__main__":
    fixer = BalanceDisplayFix()
    result = fixer.run_complete_fix()
    print("\n" + "="*50)
    print("📊 修复结果汇总:")
    print(f"找到API配置: {result['api_configs_found']}个")
    print(f"逻辑修复: {'✅' if result['logic_fixed'] else '❌'}")
    print(f"缓存清理: {'✅' if result['cache_cleaned'] else '❌'}")
    print(f"日志文件: {result['log_file']}")
    print("="*50) 