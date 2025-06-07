#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试交易所API连接
"""

import json
import ccxt

def test_api_connections():
    """测试所有交易所API连接"""
    print("🔍 测试交易所API连接...")
    
    # 读取配置
    try:
        with open("crypto_config.json", "r") as f:
            config = json.load(f)
        print("✅ 配置文件读取成功")
    except Exception as e:
        print(f"❌ 配置文件读取失败: {e}")
        return
    
    # 测试Binance
    try:
        print("\n📊 测试Binance API...")
        binance = ccxt.binance({
            'apiKey': config["binance"]["api_key"],
            'secret': config["binance"]["secret_key"],
            'enableRateLimit': True,
            'sandbox': False
        })
        
        # 测试价格获取
        ticker = binance.fetch_ticker('BTC/USDT')
        print(f"✅ Binance连接成功 - BTC价格: {ticker['last']}")
        
        # 测试账户信息（需要API权限）
        try:
            balance = binance.fetch_balance()
            print(f"✅ Binance账户信息获取成功")
            usdt_balance = balance.get('USDT', {}).get('total', 0)
            print(f"📈 USDT余额: {usdt_balance}")
        except Exception as e:
            print(f"⚠️ Binance账户信息获取失败: {e}")
            
    except Exception as e:
        print(f"❌ Binance连接失败: {e}")
    
    # 测试OKX
    try:
        print("\n📊 测试OKX API...")
        okx = ccxt.okx({
            'apiKey': config["okx"]["api_key"],
            'secret': config["okx"]["secret_key"],
            'password': config["okx"]["password"],
            'enableRateLimit': True,
            'sandbox': False
        })
        
        # 测试价格获取
        ticker = okx.fetch_ticker('BTC/USDT')
        print(f"✅ OKX连接成功 - BTC价格: {ticker['last']}")
        
        # 测试账户信息
        try:
            balance = okx.fetch_balance()
            print(f"✅ OKX账户信息获取成功")
            usdt_balance = balance.get('USDT', {}).get('total', 0)
            print(f"📈 USDT余额: {usdt_balance}")
        except Exception as e:
            print(f"⚠️ OKX账户信息获取失败: {e}")
            
    except Exception as e:
        print(f"❌ OKX连接失败: {e}")
    
    # 测试Bitget
    try:
        print("\n📊 测试Bitget API...")
        bitget = ccxt.bitget({
            'apiKey': config["bitget"]["api_key"],
            'secret': config["bitget"]["secret_key"],
            'password': config["bitget"]["password"],
            'enableRateLimit': True,
            'sandbox': False
        })
        
        # 测试价格获取
        ticker = bitget.fetch_ticker('BTC/USDT')
        print(f"✅ Bitget连接成功 - BTC价格: {ticker['last']}")
        
        # 测试账户信息
        try:
            balance = bitget.fetch_balance()
            print(f"✅ Bitget账户信息获取成功")
            usdt_balance = balance.get('USDT', {}).get('total', 0)
            print(f"📈 USDT余额: {usdt_balance}")
        except Exception as e:
            print(f"⚠️ Bitget账户信息获取失败: {e}")
            
    except Exception as e:
        print(f"❌ Bitget连接失败: {e}")

if __name__ == "__main__":
    test_api_connections() 