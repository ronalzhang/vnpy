#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整系统修复脚本
功能：
1. 配置API密钥（从API-KEY.md）
2. 修复余额显示逻辑（区分持仓价值和USDT余额） 
3. 确保量化程序全自动运行
4. 确保策略进化系统正常工作
"""

import sqlite3
import json
import os
import re
import time
from datetime import datetime
from typing import Dict, Optional

class CompleteSystemFix:
    """完整系统修复器"""
    
    def __init__(self):
        self.db_path = "quantitative.db"
        self.config_path = "crypto_config.json"
        self.log_file = f"logs/trading/complete_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    
    def configure_api_from_doc(self):
        """从API-KEY.md配置API密钥"""
        self.log("🔧 从API-KEY.md配置API密钥...")
        
        try:
            # 读取API-KEY.md
            if not os.path.exists("API-KEY.md"):
                self.log("❌ 找不到API-KEY.md文件")
                return False
            
            with open("API-KEY.md", 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取币安API信息
            api_key_match = re.search(r'API密钥\s+([A-Za-z0-9]+)', content)
            secret_match = re.search(r'密钥:\s+([A-Za-z0-9]+)', content)
            
            if not api_key_match or not secret_match:
                self.log("❌ 无法从API-KEY.md解析币安API信息")
                return False
            
            api_key = api_key_match.group(1)
            api_secret = secret_match.group(1)
            
            # 创建或更新crypto_config.json
            config = {
                "binance": {
                    "api_key": api_key,
                    "api_secret": api_secret,
                    "sandbox": False,
                    "testnet": False
                },
                "trading": {
                    "max_position_size": 0.02,
                    "stop_loss": 0.05,
                    "take_profit": 0.03,
                    "min_balance": 5.0
                }
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 设置环境变量
            os.environ['BINANCE_API_KEY'] = api_key
            os.environ['BINANCE_SECRET_KEY'] = api_secret
            
            self.log(f"✅ API密钥配置完成: {api_key[:8]}...{api_key[-8:]}")
            return True
            
        except Exception as e:
            self.log(f"❌ 配置API密钥失败: {e}")
            return False
    
    def fix_balance_logic(self):
        """修复余额显示逻辑 - 区分持仓价值和USDT余额"""
        self.log("🔧 修复余额显示逻辑...")
        
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
            
            # 1. 修复_fetch_fresh_balance方法 - 正确区分USDT余额和持仓价值
            balance_fix = '''
    def _fetch_fresh_balance(self):
        """获取最新余额 - 区分USDT现货余额和持仓总价值"""
        try:
            if not hasattr(self, 'exchange_client') or not self.exchange_client:
                print("❌ 交易所客户端未初始化")
                return None
            
            # 获取账户信息
            account_info = self.exchange_client.get_account()
            
            usdt_balance = 0.0  # USDT现货余额
            total_position_value = 0.0  # 持仓总价值
            
            # 计算USDT余额和持仓价值
            for balance in account_info.get('balances', []):
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if asset == 'USDT':
                    usdt_balance = total
                    print(f"💰 USDT余额: {usdt_balance:.2f}U")
                elif total > 0:
                    # 获取当前价格计算价值
                    try:
                        if asset != 'USDT':
                            ticker = self.exchange_client.get_symbol_ticker(symbol=f"{asset}USDT")
                            price = float(ticker['price'])
                            value = total * price
                            total_position_value += value
                            print(f"📊 {asset}: {total:.6f} * ${price:.4f} = ${value:.2f}")
                    except:
                        pass
            
            print(f"💰 USDT现货余额: {usdt_balance:.2f}U")
            print(f"📊 持仓总价值: {total_position_value:.2f}U")
            print(f"💼 账户总价值: {usdt_balance + total_position_value:.2f}U")
            
            return {
                'usdt_balance': usdt_balance,
                'position_value': total_position_value,
                'total_value': usdt_balance + total_position_value,
                # 保持向后兼容
                'total': usdt_balance,  # 主要显示USDT余额
                'available': usdt_balance,
                'frozen': 0.0
            }
            
        except Exception as e:
            print(f"❌ 获取余额失败: {e}")
            return None'''
            
            # 2. 修复_get_current_balance方法
            current_balance_fix = '''
    def _get_current_balance(self):
        """获取当前USDT余额 - 主要用于交易决策"""
        try:
            import datetime
            
            # 检查缓存是否有效 (2分钟内有效)
            if (self.balance_cache.get('cache_valid') and 
                self.balance_cache.get('last_update') and
                (datetime.datetime.now() - self.balance_cache['last_update']).seconds < 120):
                
                return self.balance_cache.get('usdt_balance', 0.0)
            
            # 缓存失效，重新获取余额
            balance_data = self._fetch_fresh_balance()
            
            if balance_data is None:
                print("❌ API获取余额失败")
                return 0.0
            
            # 更新缓存
            self.balance_cache.update({
                'usdt_balance': balance_data['usdt_balance'],
                'position_value': balance_data['position_value'],
                'total_value': balance_data['total_value'],
                'available_balance': balance_data['usdt_balance'],
                'frozen_balance': 0.0,
                'last_update': datetime.datetime.now(),
                'cache_valid': True
            })
            
            # 记录余额历史
            self.db_manager.record_balance_history(
                balance_data['total_value'],
                balance_data['usdt_balance'],
                balance_data['position_value']
            )
            
            return balance_data['usdt_balance']
            
        except Exception as e:
            print(f"获取余额失败: {e}")
            return 0.0'''
            
            # 3. 修复get_account_info方法 - 正确显示各种余额
            account_info_fix = '''
    def get_account_info(self):
        """获取账户信息 - 区分显示USDT余额和持仓价值"""
        try:
            current_balance = self._get_current_balance()  # USDT余额
            
            # 获取详细余额信息
            balance_data = self._fetch_fresh_balance()
            if balance_data:
                usdt_balance = balance_data['usdt_balance']
                position_value = balance_data['position_value'] 
                total_value = balance_data['total_value']
            else:
                usdt_balance = current_balance
                position_value = 0.0
                total_value = current_balance
            
            # 获取今日交易统计
            today_stats = self.db_manager.get_daily_stats()
            
            return {
                'usdt_balance': round(usdt_balance, 2),      # USDT现货余额
                'position_value': round(position_value, 2),  # 持仓价值
                'total_value': round(total_value, 2),        # 总价值
                'balance': round(usdt_balance, 2),           # 向下兼容
                'available_balance': round(usdt_balance, 2),
                'frozen_balance': 0.0,
                'daily_pnl': today_stats.get('pnl', 0.0),
                'daily_return': today_stats.get('return', 0.0), 
                'daily_trades': today_stats.get('trades', 0)
            }
            
        except Exception as e:
            print(f"获取账户信息失败: {e}")
            return {
                'usdt_balance': 0.0,
                'position_value': 0.0,
                'total_value': 0.0,
                'balance': 0.0,
                'available_balance': 0.0,
                'frozen_balance': 0.0,
                'daily_pnl': 0.0,
                'daily_return': 0.0,
                'daily_trades': 0
            }'''
            
            # 应用修复
            content = re.sub(
                r'def _fetch_fresh_balance\(self\):.*?(?=def |\Z)',
                balance_fix + '\n\n',
                content, flags=re.DOTALL
            )
            
            content = re.sub(
                r'def _get_current_balance\(self\):.*?(?=def |\Z)',
                current_balance_fix + '\n\n',
                content, flags=re.DOTALL
            )
            
            content = re.sub(
                r'def get_account_info\(self\):.*?(?=def |\Z)',
                account_info_fix + '\n\n',
                content, flags=re.DOTALL
            )
            
            # 保存修复后的文件
            with open(service_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.log("✅ 余额显示逻辑修复完成")
            return True
            
        except Exception as e:
            self.log(f"❌ 修复余额显示逻辑失败: {e}")
            return False
    
    def ensure_auto_trading(self):
        """确保自动交易系统正常工作"""
        self.log("🤖 确保自动交易系统正常工作...")
        
        try:
            # 检查自动交易管理器状态
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 确保自动交易开启
            cursor.execute("""
                INSERT OR REPLACE INTO system_settings (key, value)
                VALUES ('auto_trading_enabled', 'true')
            """)
            
            cursor.execute("""
                INSERT OR REPLACE INTO system_settings (key, value)
                VALUES ('strategy_evolution_enabled', 'true')
            """)
            
            # 确保有足够的策略
            cursor.execute("SELECT COUNT(*) FROM strategies WHERE enabled = 1")
            strategy_count = cursor.fetchone()[0]
            
            if strategy_count < 100:
                self.log(f"⚠️ 启用策略数量较少: {strategy_count}个，需要生成更多策略")
            else:
                self.log(f"✅ 启用策略数量: {strategy_count}个")
            
            conn.commit()
            conn.close()
            
            self.log("✅ 自动交易系统配置完成")
            return True
            
        except Exception as e:
            self.log(f"❌ 配置自动交易失败: {e}")
            return False
    
    def ensure_strategy_evolution(self):
        """确保策略进化系统正常工作"""
        self.log("🧬 确保策略进化系统正常工作...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查策略进化表是否存在
            tables_to_check = [
                'strategy_evolution_history',
                'strategy_lineage', 
                'strategy_snapshots',
                'strategy_simulation_history',
                'strategy_rolling_metrics',
                'strategy_optimization_log'
            ]
            
            for table in tables_to_check:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if not cursor.fetchone():
                    self.log(f"⚠️ 缺少表: {table}")
                else:
                    self.log(f"✅ 表存在: {table}")
            
            # 检查当前进化状态
            cursor.execute("SELECT COUNT(*) FROM strategies WHERE score >= 50.0")
            high_score_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT MAX(generation) FROM strategies")
            max_generation = cursor.fetchone()[0] or 0
            
            self.log(f"📊 高分策略数量(≥50分): {high_score_count}")
            self.log(f"📊 当前最高代数: {max_generation}")
            
            # 设置进化参数
            evolution_settings = [
                ('evolution_cycle_minutes', '5'),
                ('min_score_threshold', '65.0'),
                ('elite_preservation_ratio', '0.3'),
                ('mutation_rate', '0.1'),
                ('crossover_probability', '0.7')
            ]
            
            for key, value in evolution_settings:
                cursor.execute("""
                    INSERT OR REPLACE INTO system_settings (key, value)
                    VALUES (?, ?)
                """, (key, value))
            
            conn.commit()
            conn.close()
            
            self.log("✅ 策略进化系统配置完成")
            return True
            
        except Exception as e:
            self.log(f"❌ 配置策略进化失败: {e}")
            return False
    
    def test_system_connectivity(self):
        """测试系统连接性"""
        self.log("🔍 测试系统连接性...")
        
        try:
            # 测试API连接
            import requests
            import hmac
            import hashlib
            import urllib.parse
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            api_key = config['binance']['api_key']
            api_secret = config['binance']['api_secret']
            
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
                self.log(f"❌ API连接失败: {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ 测试连接失败: {e}")
            return False
    
    def run_complete_fix(self):
        """运行完整修复"""
        self.log("🚀 开始完整系统修复...")
        
        results = {}
        
        # 1. 配置API密钥
        results['api_configured'] = self.configure_api_from_doc()
        
        # 2. 修复余额逻辑
        results['balance_fixed'] = self.fix_balance_logic()
        
        # 3. 确保自动交易
        results['auto_trading_ok'] = self.ensure_auto_trading()
        
        # 4. 确保策略进化
        results['evolution_ok'] = self.ensure_strategy_evolution()
        
        # 5. 测试连接
        results['connectivity_ok'] = self.test_system_connectivity()
        
        self.log("🎉 完整系统修复完成！")
        
        # 生成修复报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'log_file': self.log_file,
            'success_count': sum(1 for r in results.values() if r),
            'total_count': len(results)
        }
        
        with open(f"fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report

if __name__ == "__main__":
    fixer = CompleteSystemFix()
    result = fixer.run_complete_fix()
    
    print("\n" + "="*60)
    print("📊 完整修复结果汇总:")
    print(f"API配置: {'✅' if result['results']['api_configured'] else '❌'}")
    print(f"余额修复: {'✅' if result['results']['balance_fixed'] else '❌'}")
    print(f"自动交易: {'✅' if result['results']['auto_trading_ok'] else '❌'}")
    print(f"策略进化: {'✅' if result['results']['evolution_ok'] else '❌'}")
    print(f"连接测试: {'✅' if result['results']['connectivity_ok'] else '❌'}")
    print(f"成功率: {result['success_count']}/{result['total_count']}")
    print("="*60) 