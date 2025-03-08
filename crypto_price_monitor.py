#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
加密货币跨交易所差价监控和自动套利系统
使用ccxt库连接交易所API，监控价格差异
"""

import os
import time
import json
import ccxt
import pandas as pd
from tabulate import tabulate
from loguru import logger
from datetime import datetime
import threading
import traceback

# 设置日志
logger.add("crypto_monitor_{time}.log", rotation="100 MB")

# 要监控的交易对列表
SYMBOLS = [
    "BTC/USDT", 
    "ETH/USDT", 
    "SOL/USDT", 
    "BNB/USDT", 
    "XRP/USDT", 
    "DOGE/USDT", 
    "ADA/USDT", 
    "AVAX/USDT", 
    "MATIC/USDT", 
    "DOT/USDT"
]

# 交易所配置文件路径
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crypto_config.json")

# 交易所对象字典
exchanges = {}

# 套利参数
ARBITRAGE_THRESHOLD = 0.005  # 开始套利的差价阈值（0.5%）
CLOSE_THRESHOLD = 0.001      # 平仓差价阈值（0.1%）
TRADE_AMOUNT = {             # 每个交易对的交易数量
    "BTC/USDT": 0.01,
    "ETH/USDT": 0.1,
    "SOL/USDT": 1,
    "BNB/USDT": 0.5,
    "XRP/USDT": 100,
    "DOGE/USDT": 1000,
    "ADA/USDT": 100,
    "AVAX/USDT": 5,
    "MATIC/USDT": 100,
    "DOT/USDT": 10
}

# 交易所资金要求（USDT）
MIN_BALANCE_REQUIRED = 50  # 每个交易所至少需要这些USDT作为余额

# 存储交易所余额信息
exchange_balances = {}

# 存储活跃套利交易
active_arbitrages = {}


def load_config():
    """加载交易所配置"""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return None


def init_exchanges():
    """初始化交易所连接"""
    config = load_config()
    if not config:
        logger.error("无法加载配置，请确保crypto_config.json文件存在且格式正确")
        return False
    
    try:
        # 初始化OKEX交易所
        if "OKEX" in config:
            exchanges["okex"] = ccxt.okx({
                'apiKey': config["OKEX"]["key"],
                'secret': config["OKEX"]["secret"],
                'password': config["OKEX"]["passphrase"],
                'timeout': 30000,
                'enableRateLimit': True,
            })
            logger.info("OKEX交易所初始化成功")
        
        # 初始化Binance交易所
        if "BINANCE" in config:
            exchanges["binance"] = ccxt.binance({
                'apiKey': config["BINANCE"]["key"],
                'secret': config["BINANCE"]["secret"],
                'timeout': 30000,
                'enableRateLimit': True,
            })
            logger.info("Binance交易所初始化成功")
        
        # 初始化Bitget交易所
        if "BITGET" in config:
            exchanges["bitget"] = ccxt.bitget({
                'apiKey': config["BITGET"]["key"],
                'secret': config["BITGET"]["secret"],
                'password': config["BITGET"]["passphrase"],
                'timeout': 30000,
                'enableRateLimit': True,
            })
            logger.info("Bitget交易所初始化成功")
        
        return len(exchanges) >= 2  # 至少需要两个交易所才能进行套利
    
    except Exception as e:
        logger.error(f"初始化交易所失败: {e}")
        return False


def get_ticker(exchange, symbol):
    """获取交易对的最新价格"""
    try:
        ticker = exchange.fetch_ticker(symbol)
        return {
            "bid": ticker["bid"],  # 买一价
            "ask": ticker["ask"],  # 卖一价
            "last": ticker["last"],  # 最新成交价
            "timestamp": ticker["timestamp"]
        }
    except Exception as e:
        logger.error(f"获取{exchange.id} {symbol}价格失败: {e}")
        return None


def fetch_all_prices():
    """获取所有交易所和交易对的价格"""
    results = {}
    for symbol in SYMBOLS:
        symbol_data = {"symbol": symbol}
        
        for name, exchange in exchanges.items():
            ticker = get_ticker(exchange, symbol)
            if ticker:
                symbol_data[name] = ticker
        
        results[symbol] = symbol_data
    
    return results


def calculate_price_differences(prices):
    """计算交易所之间的价格差异"""
    results = []
    
    for symbol, data in prices.items():
        row = {"symbol": symbol}
        max_price = 0
        min_price = float('inf')
        max_exchange = ""
        min_exchange = ""
        
        # 找出最高价和最低价的交易所
        for name, ticker in data.items():
            if name == "symbol":
                continue
            
            price = ticker["last"]
            row[name] = price
            
            if price > max_price:
                max_price = price
                max_exchange = name
            
            if price < min_price:
                min_price = price
                min_exchange = name
        
        # 计算差价和差价百分比
        if min_price > 0:
            price_diff = max_price - min_price
            price_diff_pct = price_diff / min_price
            
            row["max_price"] = max_price
            row["max_exchange"] = max_exchange
            row["min_price"] = min_price
            row["min_exchange"] = min_exchange
            row["price_diff"] = price_diff
            row["price_diff_pct"] = price_diff_pct
            
            results.append(row)
    
    return results


def display_price_diff_table(diff_data):
    """显示价格差异表格"""
    table_data = []
    
    for item in diff_data:
        symbol = item["symbol"]
        row = [symbol]
        
        # 添加各交易所的价格
        for name in exchanges.keys():
            if name in item:
                price = item[name]
                row.append(f"{price:.4f}")
            else:
                row.append("N/A")
        
        # 添加最大差价（以USD计）
        price_diff = item.get("price_diff", 0)
        price_diff_pct = item.get("price_diff_pct", 0)
        row.append(f"{price_diff:.4f} USDT")
        row.append(f"{price_diff_pct*100:.2f}%")
        
        # 添加套利方向
        if "max_exchange" in item and "min_exchange" in item:
            arb_direction = f"{item['min_exchange']} → {item['max_exchange']}"
            row.append(arb_direction)
        else:
            row.append("N/A")
        
        table_data.append(row)
    
    # 创建表头
    headers = ["交易对"]
    for name in exchanges.keys():
        headers.append(name.capitalize())
    headers.extend(["价差(USDT)", "价差(%)", "套利方向"])
    
    # 打印表格
    print("\n" + "="*80)
    print(f"加密货币跨交易所价格监控 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print("\n")


def log_arbitrage_opportunity(diff_data):
    """记录套利机会到日志"""
    for item in diff_data:
        symbol = item["symbol"]
        price_diff_pct = item.get("price_diff_pct", 0)
        
        if price_diff_pct >= ARBITRAGE_THRESHOLD:
            logger.info(
                f"套利机会: {symbol} - 从 {item['min_exchange']}({item['min_price']:.4f}) "
                f"到 {item['max_exchange']}({item['max_price']:.4f}) - "
                f"差价: {item['price_diff']:.4f} USDT ({price_diff_pct*100:.2f}%)"
            )


def check_balances():
    """检查交易所余额"""
    global exchange_balances
    balances = {}
    
    print("\n--- 交易所余额 ---")
    
    for name, exchange in exchanges.items():
        try:
            balance = exchange.fetch_balance()
            
            # 只保存有余额的币种
            non_zero = {
                currency: data 
                for currency, data in balance['total'].items() 
                if data > 0 and currency != 'info'
            }
            
            balances[name] = non_zero
            exchange_balances[name] = non_zero
            
            # 打印余额
            print(f"{name.upper()} 账户余额:")
            for currency, amount in non_zero.items():
                print(f"  {currency}: {amount}")
                
        except Exception as e:
            print(f"获取{name}余额失败: {e}")
    
    print()  # 空行
    return balances


def has_sufficient_balance(symbol, exchange_name, required_amount):
    """检查特定交易所对特定交易对是否有足够余额"""
    global exchange_balances
    
    # 如果没有余额信息，先获取
    if not exchange_balances or exchange_name not in exchange_balances:
        check_balances()
    
    if exchange_name not in exchange_balances:
        print(f"错误: 无法获取 {exchange_name} 的余额信息")
        return False
    
    # 获取交易对的基础货币和报价货币
    base_currency, quote_currency = symbol.split('/')
    
    # 检查是否有足够的基础货币和USDT
    balances = exchange_balances[exchange_name]
    base_balance = balances.get(base_currency, 0)
    quote_balance = balances.get(quote_currency, 0)
    
    # 如果买入需要quote_currency，如果卖出需要base_currency
    has_enough = (quote_balance >= MIN_BALANCE_REQUIRED and base_balance >= required_amount)
    
    if not has_enough:
        print(
            f"警告: {exchange_name} 余额不足 - 需要: {base_currency}={required_amount}, "
            f"{quote_currency}={MIN_BALANCE_REQUIRED}, 实际: {base_currency}={base_balance}, "
            f"{quote_currency}={quote_balance}"
        )
    
    return has_enough


def execute_arbitrage(diff_data):
    """执行套利交易"""
    for item in diff_data:
        symbol = item["symbol"]
        price_diff_pct = item.get("price_diff_pct", 0)
        
        # 检查是否有活跃的套利交易
        if symbol in active_arbitrages:
            # 平仓逻辑
            if price_diff_pct <= CLOSE_THRESHOLD:
                try:
                    arb_info = active_arbitrages[symbol]
                    amount = TRADE_AMOUNT[symbol]
                    
                    # 检查余额是否充足
                    if not has_sufficient_balance(symbol, arb_info["buy_exchange"], amount):
                        print(f"平仓套利失败: {symbol} - {arb_info['buy_exchange']} 余额不足")
                        continue
                        
                    if not has_sufficient_balance(symbol, arb_info["sell_exchange"], 0):  # 卖出时只需检查USDT余额是否充足
                        print(f"平仓套利失败: {symbol} - {arb_info['sell_exchange']} 余额不足")
                        continue
                    
                    # 卖出之前在低价交易所买入的币
                    sell_exchange = exchanges[arb_info["buy_exchange"]]
                    sell_result = sell_exchange.create_market_sell_order(symbol, amount)
                    
                    # 买入之前在高价交易所卖出的币
                    buy_exchange = exchanges[arb_info["sell_exchange"]]
                    buy_result = buy_exchange.create_market_buy_order(symbol, amount)
                    
                    profit = arb_info["price_diff"] * amount
                    print(
                        f"平仓套利: {symbol} - 利润: {profit:.4f} USDT - "
                        f"耗时: {(time.time() - arb_info['timestamp'])/60:.2f}分钟"
                    )
                    
                    # 记录交易详情
                    print(f"平仓交易详情 - 买入: {buy_result}, 卖出: {sell_result}")
                    
                    # 移除活跃套利
                    del active_arbitrages[symbol]
                    
                    # 更新余额
                    check_balances()
                    
                except Exception as e:
                    print(f"平仓套利失败 {symbol}: {e}")
        
        # 开仓逻辑
        elif price_diff_pct >= ARBITRAGE_THRESHOLD:
            try:
                buy_exchange_name = item["min_exchange"]
                sell_exchange_name = item["max_exchange"]
                
                amount = TRADE_AMOUNT[symbol]
                
                # 检查余额是否充足
                if not has_sufficient_balance(symbol, buy_exchange_name, 0):  # 买入时只需检查USDT余额是否充足
                    print(f"开仓套利失败: {symbol} - {buy_exchange_name} USDT余额不足")
                    continue
                    
                if not has_sufficient_balance(symbol, sell_exchange_name, amount):
                    print(f"开仓套利失败: {symbol} - {sell_exchange_name} {symbol.split('/')[0]}余额不足")
                    continue
                
                buy_exchange = exchanges[buy_exchange_name]
                sell_exchange = exchanges[sell_exchange_name]
                
                # 在低价交易所买入
                buy_result = buy_exchange.create_market_buy_order(symbol, amount)
                
                # 在高价交易所卖出
                sell_result = sell_exchange.create_market_sell_order(symbol, amount)
                
                # 记录套利信息
                active_arbitrages[symbol] = {
                    "buy_exchange": buy_exchange_name,
                    "sell_exchange": sell_exchange_name,
                    "buy_price": item["min_price"],
                    "sell_price": item["max_price"],
                    "price_diff": item["price_diff"],
                    "price_diff_pct": price_diff_pct,
                    "amount": amount,
                    "timestamp": time.time()
                }
                
                print(
                    f"开始套利: {symbol} - 从 {buy_exchange_name}({item['min_price']:.4f}) "
                    f"到 {sell_exchange_name}({item['max_price']:.4f}) - "
                    f"数量: {amount} - 预期利润: {item['price_diff'] * amount:.4f} USDT"
                )
                
                # 记录交易详情
                print(f"开仓交易详情 - 买入: {buy_result}, 卖出: {sell_result}")
                
                # 更新余额
                check_balances()
                
            except Exception as e:
                print(f"执行套利失败 {symbol}: {e}")


def monitor_loop(enable_trading=False):
    """价格监控循环"""
    while True:
        try:
            # 获取价格数据
            prices = fetch_all_prices()
            
            # 计算价格差异
            diff_data = calculate_price_differences(prices)
            
            # 显示价格差异表格
            display_price_diff_table(diff_data)
            
            # 记录套利机会
            log_arbitrage_opportunity(diff_data)
            
            # 如果启用交易，执行套利
            if enable_trading:
                execute_arbitrage(diff_data)
            
            # 每10分钟检查一次余额
            if int(time.time()) % 600 < 30:
                check_balances()
                
        except Exception as e:
            logger.error(f"监控循环异常: {e}")
            logger.error(traceback.format_exc())
        
        # 暂停30秒
        time.sleep(30)


def main():
    """主函数"""
    print("="*80)
    print("加密货币跨交易所差价监控和自动套利系统")
    print("="*80)
    
    # 初始化交易所连接
    if not init_exchanges():
        print("初始化交易所失败，请检查配置文件")
        return
    
    print(f"成功连接 {len(exchanges)} 个交易所")
    print(f"监控 {len(SYMBOLS)} 个交易对: {', '.join(SYMBOLS)}")
    
    # 询问是否启用自动交易
    enable_trading = False
    while True:
        choice = input("\n是否启用自动套利交易? (y/n): ").strip().lower()
        if choice == 'y':
            enable_trading = True
            print("\n⚠️ 警告: 已启用自动套利交易!")
            print(f"套利开仓阈值: {ARBITRAGE_THRESHOLD*100:.1f}%")
            print(f"套利平仓阈值: {CLOSE_THRESHOLD*100:.1f}%")
            break
        elif choice == 'n':
            print("\n仅监控模式，不会执行自动交易")
            break
        else:
            print("无效输入，请输入 'y' 或 'n'")
    
    # 检查交易所余额
    check_balances()
    
    print("\n开始监控价格差异...")
    logger.info("开始监控加密货币跨交易所价格差异")
    
    try:
        # 启动监控循环
        monitor_loop(enable_trading)
    except KeyboardInterrupt:
        print("\n用户中断，退出程序")
        logger.info("用户中断，退出程序")
    except Exception as e:
        print(f"\n程序异常: {e}")
        logger.error(f"程序异常: {e}")
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main() 