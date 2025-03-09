#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试OKX API连接脚本
"""

import sys
import json
import time
import ccxt

# OKX API配置
okx_config = {
    "api_key": "41da5169-9d1e-4a54-a2cd-85fb381daa80",
    "secret_key": "E17B80E7A616601FEEE262CABBBDA2DE",
    "password": "123abc$74531ABC"  # 特殊字符 $ 可能需要特殊处理
}

def test_okx_api():
    """测试OKX API连接"""
    print("===== 测试OKX API连接 =====")
    
    # 尝试不同的密码格式
    passwords = [
        okx_config["password"],                  # 原始密码
        okx_config["password"].replace("$", ""), # 移除特殊字符
        "123abc74531ABC",                        # 简化密码
    ]
    
    for i, password in enumerate(passwords):
        print(f"\n尝试密码格式 {i+1}: {password}")
        try:
            # 创建OKX客户端
            okx = ccxt.okx({
                'apiKey': okx_config["api_key"],
                'secret': okx_config["secret_key"],
                'password': password,
                'enableRateLimit': True
            })
            
            # 测试API连接 - 获取余额
            print("尝试获取余额...")
            balance = okx.fetch_balance()
            if balance:
                print("成功获取余额!")
                print(f"原始余额数据结构: {type(balance)}")
                
                # 安全地获取USDT余额
                usdt_total = 0
                if 'USDT' in balance and isinstance(balance['USDT'], dict):
                    usdt_total = balance['USDT'].get('total', 0)
                print(f"USDT余额: {usdt_total}")
                
                # 打印余额详情
                print("余额详情:")
                for currency, details in balance.items():
                    if isinstance(details, dict) and details.get('total', 0) > 0:
                        print(f"{currency}: 总额={details.get('total', 0)}, 可用={details.get('free', 0)}, 锁定={details.get('used', 0)}")
            
            # 测试获取行情
            print("\n尝试获取BTC/USDT行情...")
            ticker = okx.fetch_ticker("BTC/USDT")
            if ticker:
                print("成功获取行情!")
                print(f"最新价: {ticker.get('last')}")
                print(f"买一价: {ticker.get('bid')}")
                print(f"卖一价: {ticker.get('ask')}")
            
            print("\n该密码格式配置有效!")
            return True
            
        except Exception as e:
            print(f"错误: {e}")
            print("该密码格式配置无效，尝试下一个格式...")
    
    print("\n所有密码格式均无效，请检查API密钥或密码")
    return False

if __name__ == "__main__":
    test_okx_api() 