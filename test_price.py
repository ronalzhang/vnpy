#!/usr/bin/env python3
import ccxt
import json

try:
    # 加载配置
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    # 创建币安客户端
    binance = ccxt.binance({
        'apiKey': config['exchanges']['binance']['api_key'],
        'secret': config['exchanges']['binance']['secret_key'],
        'sandbox': False
    })
    
    # 测试价格获取
    symbols = ['BNB/USDT', 'MANA/USDT']
    
    for symbol in symbols:
        try:
            ticker = binance.fetch_ticker(symbol)
            print(f'{symbol} 价格: {ticker["last"]}')
        except Exception as e:
            print(f'{symbol} 获取失败: {e}')
            
except Exception as e:
    print(f'初始化失败: {e}') 