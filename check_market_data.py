#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
市场数据检查脚本
"""

import ccxt

def check_market_data():
    print('=== 市场数据检查 ===')
    try:
        exchange = ccxt.binance()
        ticker = exchange.fetch_ticker('BTC/USDT')
        print(f'BTC价格: {ticker["last"]}')
        
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=5)
        print(f'K线数据: {len(ohlcv)}条')
        
        print('市场数据获取正常')
        return True
        
    except Exception as e:
        print(f'市场数据获取失败: {e}')
        return False

if __name__ == "__main__":
    check_market_data() 