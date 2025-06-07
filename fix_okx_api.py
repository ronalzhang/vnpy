#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复OKX API连接问题
"""

import json
import ccxt

def test_okx_with_debug():
    """调试OKX API连接"""
    try:
        with open("crypto_config.json", "r") as f:
            config = json.load(f)
        
        print("🔍 调试OKX API连接...")
        print(f"API Key: {config['okx']['api_key'][:10]}...")
        print(f"Secret: {config['okx']['secret_key'][:10]}...")
        print(f"Password: {config['okx']['password']}")
        
        # 方式1：使用password
        try:
            print("\n📊 测试方式1：使用password字段")
            okx1 = ccxt.okx({
                'apiKey': config["okx"]["api_key"],
                'secret': config["okx"]["secret_key"],
                'password': config["okx"]["password"],
                'enableRateLimit': True,
                'sandbox': False,
                'timeout': 30000
            })
            
            ticker = okx1.fetch_ticker('BTC/USDT')
            print(f"✅ 方式1成功 - BTC价格: {ticker['last']}")
            return True
            
        except Exception as e:
            print(f"❌ 方式1失败: {e}")
        
        # 方式2：使用passphrase
        try:
            print("\n📊 测试方式2：使用passphrase字段")
            okx2 = ccxt.okx({
                'apiKey': config["okx"]["key"],
                'secret': config["okx"]["secret"],
                'password': config["okx"]["passphrase"],
                'enableRateLimit': True,
                'sandbox': False,
                'timeout': 30000
            })
            
            ticker = okx2.fetch_ticker('BTC/USDT')
            print(f"✅ 方式2成功 - BTC价格: {ticker['last']}")
            return True
            
        except Exception as e:
            print(f"❌ 方式2失败: {e}")
        
        # 方式3：只获取公开数据
        try:
            print("\n📊 测试方式3：公开数据（不需要API密钥）")
            okx3 = ccxt.okx({
                'enableRateLimit': True,
                'sandbox': False,
                'timeout': 30000
            })
            
            ticker = okx3.fetch_ticker('BTC/USDT')
            print(f"✅ 方式3成功 - BTC价格: {ticker['last']}")
            print("⚠️ 注意：这只能获取公开数据，无法获取账户信息")
            return True
            
        except Exception as e:
            print(f"❌ 方式3失败: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ 配置读取失败: {e}")
        return False

if __name__ == "__main__":
    test_okx_with_debug() 