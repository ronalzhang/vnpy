#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修复OKX API连接问题的完整脚本
解决 unsupported operand type(s) for +: 'NoneType' and 'str' 错误
"""

import json
import ccxt
import traceback

def test_okx_api():
    """测试OKX API连接"""
    print("🔍 开始测试OKX API连接...")
    
    # 读取配置
    try:
        with open('crypto_config.json', 'r') as f:
            config = json.load(f)
        print("✅ 配置文件读取成功")
    except Exception as e:
        print(f"❌ 配置文件读取失败: {e}")
        return False
    
    if 'okx' not in config:
        print("❌ 配置中缺少OKX配置")
        return False
    
    okx_config = config['okx']
    print(f"📊 OKX配置: api_key长度={len(okx_config.get('api_key', ''))}")
    print(f"📊 OKX配置: secret_key长度={len(okx_config.get('secret_key', ''))}")
    print(f"📊 OKX配置: password长度={len(okx_config.get('password', ''))}")
    
    # 测试1: 基础连接
    try:
        print("\n🔧 测试1: 基础OKX客户端创建...")
        okx = ccxt.okx({
            'apiKey': okx_config['api_key'],
            'secret': okx_config['secret_key'],
            'password': okx_config['password'],
            'enableRateLimit': True,
            'sandbox': False
        })
        print("✅ OKX客户端创建成功")
    except Exception as e:
        print(f"❌ OKX客户端创建失败: {e}")
        traceback.print_exc()
        return False
    
    # 测试2: 获取行情数据
    try:
        print("\n🔧 测试2: 获取BTC/USDT行情...")
        ticker = okx.fetch_ticker('BTC/USDT')
        print(f"✅ 获取行情成功: BTC价格 = {ticker['last']}")
    except Exception as e:
        print(f"❌ 获取行情失败: {e}")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误详情: {str(e)}")
        traceback.print_exc()
        
        # 如果是字符串连接错误，打印更详细信息
        if "unsupported operand type" in str(e) and "NoneType" in str(e):
            print("\n🔍 检测到NoneType字符串连接错误，分析原因...")
            print(f"API Key: {okx_config['api_key'][:10]}...")
            print(f"Secret Key: {okx_config['secret_key'][:10]}...")
            print(f"Password: {okx_config['password'][:5]}...")
        return False
    
    # 测试3: 获取订单簿
    try:
        print("\n🔧 测试3: 获取订单簿...")
        orderbook = okx.fetch_order_book('BTC/USDT')
        if orderbook and 'bids' in orderbook and 'asks' in orderbook:
            print(f"✅ 订单簿获取成功: 买一价 = {orderbook['bids'][0][0]}, 卖一价 = {orderbook['asks'][0][0]}")
        else:
            print(f"⚠️ 订单簿格式异常: {orderbook}")
    except Exception as e:
        print(f"❌ 获取订单簿失败: {e}")
        traceback.print_exc()
        return False
    
    # 测试4: 获取账户余额
    try:
        print("\n🔧 测试4: 获取账户余额...")
        balance = okx.fetch_balance()
        print(f"✅ 账户余额获取成功")
        print(f"📊 USDT余额: {balance.get('USDT', {}).get('total', 0)}")
    except Exception as e:
        print(f"❌ 获取账户余额失败: {e}")
        print("这可能是权限问题，不影响价格获取功能")
    
    return True

def fix_okx_config():
    """修复OKX配置"""
    print("\n🔧 开始修复OKX配置...")
    
    try:
        with open('crypto_config.json', 'r') as f:
            config = json.load(f)
        
        # 确保OKX配置完整
        if 'okx' not in config:
            config['okx'] = {}
        
        okx_config = config['okx']
        
        # 从API-KEY.md重新读取正确的配置
        api_key = "41da5169-9d1e-4a54-a2cd-85fb381daa80"
        secret_key = "E17B80E7A616601FEEE262CABBBDA2DE"
        password = "123abc$74531ABC"
        
        # 更新配置
        okx_config.update({
            'api_key': api_key,
            'secret_key': secret_key,
            'password': password,
            'key': api_key,  # 兼容字段
            'secret': secret_key,  # 兼容字段
            'passphrase': password  # 兼容字段
        })
        
        # 保存配置
        with open('crypto_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print("✅ OKX配置修复完成")
        return True
        
    except Exception as e:
        print(f"❌ 修复OKX配置失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 OKX API完整修复开始...")
    
    # 步骤1: 修复配置
    if not fix_okx_config():
        print("❌ 配置修复失败，退出")
        return
    
    # 步骤2: 测试API
    if test_okx_api():
        print("\n🎉 OKX API修复成功！")
        print("现在可以正常获取OKX的价格数据了")
    else:
        print("\n❌ OKX API修复失败")
        print("需要进一步检查API密钥或网络连接")

if __name__ == "__main__":
    main() 