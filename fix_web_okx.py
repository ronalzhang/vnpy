#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修复web应用中OKX API连接问题
"""

import json
import sys
import os

def fix_web_okx():
    """修复web应用中的OKX实现"""
    print("🔧 开始修复web应用中的OKX问题...")
    
    # 读取web_app.py
    try:
        with open('web_app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        print("✅ 读取web_app.py成功")
    except Exception as e:
        print(f"❌ 读取web_app.py失败: {e}")
        return False
    
    # 修复OKX客户端创建部分
    fixes_made = []
    
    # 修复1: 增强OKX客户端创建的错误处理
    old_okx_creation = '''elif exchange_id == "okx":
        client = ccxt.okx({
            'apiKey': config[exchange_id]["api_key"],
            'secret': config[exchange_id]["secret_key"],
            'password': config[exchange_id]["password"],
            'enableRateLimit': True,
            'sandbox': False
        })'''
    
    new_okx_creation = '''elif exchange_id == "okx":
        try:
            client = ccxt.okx({
                'apiKey': str(config[exchange_id]["api_key"]),
                'secret': str(config[exchange_id]["secret_key"]),
                'password': str(config[exchange_id]["password"]),
                'enableRateLimit': True,
                'sandbox': False
            })
            # 验证连接
            client.load_markets()
            print(f"✅ OKX客户端创建并验证成功")
        except Exception as e:
            print(f"❌ OKX客户端创建失败: {e}")
            continue'''
    
    if old_okx_creation.replace(' ', '').replace('\n', '') in content.replace(' ', '').replace('\n', ''):
        content = content.replace(old_okx_creation, new_okx_creation)
        fixes_made.append("OKX客户端创建增强")
    
    # 修复2: 改进OKX价格获取
    old_okx_price = '''# 检查客户端配置
        if exchange_id == 'okx':
            # 因为OKX可能需要特殊处理密码中的特殊字符
            # 打印一些调试信息，不包含敏感信息
            print(f"获取 {exchange_id} 价格数据，客户端配置：apiKey长度={len(client.apiKey) if hasattr(client, 'apiKey') and client.apiKey else 0}, password长度={len(client.password) if hasattr(client, 'password') and client.password else 0}")'''
    
    new_okx_price = '''# 检查客户端配置
        if exchange_id == 'okx':
            print(f"获取 {exchange_id} 价格数据...")
            try:
                # 简单测试连接
                test_ticker = client.fetch_ticker("BTC/USDT")
                print(f"✅ OKX API连接正常")
            except Exception as e:
                print(f"❌ OKX API连接异常: {e}")
                # 跳过这个交易所的价格获取
                continue'''
    
    if old_okx_price in content:
        content = content.replace(old_okx_price, new_okx_price)
        fixes_made.append("OKX价格获取优化")
    
    # 修复3: 简化OKX余额获取
    old_okx_balance = '''def get_okx_balance(client):
    """获取OKX余额的替代方法"""
    try:
        balance = {"USDT": 0, "USDT_available": 0, "USDT_locked": 0, "positions": {}}
        funding_accounts = client.private_get_asset_balances({'ccy': ''})'''
    
    new_okx_balance = '''def get_okx_balance(client):
    """获取OKX余额的替代方法"""
    try:
        balance = {"USDT": 0, "USDT_available": 0, "USDT_locked": 0, "positions": {}}
        # 使用标准方法获取余额
        account_balance = client.fetch_balance()
        
        # 处理USDT余额
        if 'USDT' in account_balance:
            usdt_info = account_balance['USDT']
            balance["USDT"] = round(usdt_info.get('total', 0), 2)
            balance["USDT_available"] = round(usdt_info.get('free', 0), 2)
            balance["USDT_locked"] = round(usdt_info.get('used', 0), 2)
        
        # 处理其他资产
        for symbol, info in account_balance.items():
            if symbol != 'USDT' and symbol not in ['info', 'free', 'used', 'total']:
                total = info.get('total', 0)
                if total > 0:
                    try:
                        ticker = client.fetch_ticker(f"{symbol}/USDT")
                        price = ticker['last']'''
    
    if old_okx_balance in content:
        content = content.replace(old_okx_balance, new_okx_balance)
        fixes_made.append("OKX余额获取简化")
    
    # 保存修复后的文件
    if fixes_made:
        try:
            with open('web_app.py', 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ web_app.py修复完成，应用了以下修复:")
            for fix in fixes_made:
                print(f"  - {fix}")
            return True
        except Exception as e:
            print(f"❌ 保存修复后的web_app.py失败: {e}")
            return False
    else:
        print("ℹ️ 未发现需要修复的OKX相关代码")
        return True

if __name__ == "__main__":
    fix_web_okx() 