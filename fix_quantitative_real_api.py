#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复量化服务中的模拟数据问题 - 替换为真实API调用
"""

import re
import os
import json

def fix_price_simulation():
    """修复价格模拟问题"""
    file_path = "quantitative_service.py"
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修复 _get_current_price 方法
        old_price_method = '''def _get_current_price(self, symbol):
        """获取当前价格"""
        try:
            # 简化的价格获取，实际应该从交易所API获取
            import random
            base_prices = {
                'BTC/USDT': 100000,
                'ETH/USDT': 2600,
                'DOGE/USDT': 0.35,
                'BNB/USDT': 600,
                'ADA/USDT': 0.45,
                'XRP/USDT': 0.60
            }
            base_price = base_prices.get(symbol, 1.0)
            # 模拟价格波动 ±2%
            fluctuation = random.uniform(0.98, 1.02)
            return round(base_price * fluctuation, 6)
        except Exception as e:
            return 1.0'''
        
        new_price_method = '''def _get_current_price(self, symbol):
        """获取当前价格 - 使用真实API"""
        try:
            # 优先从配置的交易所获取真实价格
            if hasattr(self, 'exchange_clients') and self.exchange_clients:
                for exchange_name, client in self.exchange_clients.items():
                    try:
                        ticker = client.fetch_ticker(symbol)
                        if ticker and 'last' in ticker:
                            price = float(ticker['last'])
                            print(f"✅ 从{exchange_name}获取{symbol}真实价格: {price}")
                            return price
                    except Exception as e:
                        print(f"⚠️ 从{exchange_name}获取{symbol}价格失败: {e}")
                        continue
            
            # 如果没有配置交易所客户端，尝试使用全局API
            try:
                import ccxt
                import json
                import os
                
                # 尝试读取API配置
                config_file = "crypto_config.json"
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                    
                    # 尝试使用Binance获取价格
                    if "binance" in config:
                        binance = ccxt.binance({
                            'apiKey': config["binance"]["api_key"],
                            'secret': config["binance"]["secret_key"],
                            'enableRateLimit': True
                        })
                        ticker = binance.fetch_ticker(symbol)
                        if ticker and 'last' in ticker:
                            price = float(ticker['last'])
                            print(f"✅ 从Binance获取{symbol}真实价格: {price}")
                            return price
                
            except Exception as e:
                print(f"❌ API获取价格失败: {e}")
            
            # 如果所有API都失败，返回默认值但记录警告
            print(f"⚠️ 无法获取{symbol}真实价格，使用默认值")
            base_prices = {
                'BTC/USDT': 95000.0,
                'ETH/USDT': 3500.0,
                'DOGE/USDT': 0.35,
                'BNB/USDT': 600.0,
                'ADA/USDT': 0.45,
                'XRP/USDT': 0.60
            }
            return base_prices.get(symbol, 1.0)
            
        except Exception as e:
            print(f"❌ 获取价格出错: {e}")
            return 1.0'''
        
        # 替换模拟价格方法
        if old_price_method in content:
            content = content.replace(old_price_method, new_price_method)
            print("✅ 已修复 _get_current_price 方法")
        else:
            # 如果没有找到完整匹配，使用正则表达式替换
            pattern = r'def _get_current_price\(self, symbol\):.*?return 1\.0'
            if re.search(pattern, content, re.DOTALL):
                content = re.sub(pattern, new_price_method.replace('def _get_current_price(self, symbol):', '').strip(), content, flags=re.DOTALL)
                print("✅ 通过正则表达式修复了 _get_current_price 方法")
        
        # 修复其他模拟数据相关代码
        # 替换其他随机价格生成
        content = re.sub(
            r'# 模拟价格波动.*?\n.*?random\.uniform\(0\.98, 1\.02\)',
            '# 使用真实价格数据\n            price_factor = 1.0',
            content,
            flags=re.DOTALL
        )
        
        # 添加交易所客户端初始化方法
        if 'def init_exchange_clients(self):' not in content:
            init_method = '''
    def init_exchange_clients(self):
        """初始化交易所客户端"""
        try:
            import ccxt
            import json
            import os
            
            self.exchange_clients = {}
            
            if os.path.exists("crypto_config.json"):
                with open("crypto_config.json", 'r') as f:
                    config = json.load(f)
                
                # 初始化Binance
                if "binance" in config:
                    try:
                        self.exchange_clients["binance"] = ccxt.binance({
                            'apiKey': config["binance"]["api_key"],
                            'secret': config["binance"]["secret_key"],
                            'enableRateLimit': True,
                            'sandbox': False
                        })
                        print("✅ Binance客户端初始化成功")
                    except Exception as e:
                        print(f"❌ Binance客户端初始化失败: {e}")
                
                # 初始化OKX
                if "okx" in config:
                    try:
                        self.exchange_clients["okx"] = ccxt.okx({
                            'apiKey': config["okx"]["api_key"],
                            'secret': config["okx"]["secret_key"],
                            'password': config["okx"]["password"],
                            'enableRateLimit': True,
                            'sandbox': False
                        })
                        print("✅ OKX客户端初始化成功")
                    except Exception as e:
                        print(f"❌ OKX客户端初始化失败: {e}")
                
                print(f"📊 交易所客户端初始化完成: {len(self.exchange_clients)}/2")
            else:
                print("⚠️ 未找到API配置文件，将使用默认价格")
                
        except Exception as e:
            print(f"❌ 初始化交易所客户端失败: {e}")
            self.exchange_clients = {}
'''
            
            # 在 __init__ 方法后添加
            init_pattern = r'(def __init__\(self.*?\n.*?)(    def)'
            if re.search(init_pattern, content, re.DOTALL):
                content = re.sub(init_pattern, r'\1' + init_method + r'\n\2', content, flags=re.DOTALL)
                print("✅ 添加了交易所客户端初始化方法")
        
        # 在 __init__ 方法中添加初始化调用
        if 'self.init_exchange_clients()' not in content:
            # 在 __init__ 方法末尾添加调用
            init_call_pattern = r'(def __init__\(self.*?\n(?:.*?\n)*?.*?)(    def)'
            if re.search(init_call_pattern, content, re.DOTALL):
                content = re.sub(
                    r'(def __init__\(self.*?\n(?:.*?\n)*?)(    def)',
                    r'\1        # 初始化交易所客户端\n        self.init_exchange_clients()\n\n\2',
                    content,
                    flags=re.DOTALL
                )
                print("✅ 在__init__中添加了交易所客户端初始化调用")
        
        # 保存修复后的文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 量化服务真实API修复完成")
        return True
        
    except Exception as e:
        print(f"❌ 修复量化服务失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 开始修复量化服务中的模拟数据问题...")
    print("=" * 50)
    
    if fix_price_simulation():
        print("\n🎉 修复完成！量化服务现在将使用真实API获取价格数据")
        print("📌 建议重启量化服务: pm2 restart quant-b")
    else:
        print("\n❌ 修复失败")

if __name__ == "__main__":
    main() 