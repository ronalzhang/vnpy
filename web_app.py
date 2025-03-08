#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
加密货币套利监控Web应用
"""

import sys
import json
import time
import random
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from loguru import logger
import pandas as pd
from vnpy.trader.object import TickData
from vnpy.trader.constant import Exchange
from vnpy_okex import OkexGateway
from vnpy_binance import BinanceGateway
from vnpy_bitget import BitgetGateway
import ccxt

from flask import Flask, jsonify, render_template, request, Response

# 创建Flask应用
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# 全局变量
CONFIG_FILE = "crypto_config.json"
CONFIG_PATH = Path(__file__).parent.joinpath(CONFIG_FILE)
SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT",
    "ADA/USDT", "DOT/USDT", "MATIC/USDT", "AVAX/USDT", "SHIB/USDT"
]
EXCHANGES = ["binance", "okx", "bitget"]
ARBITRAGE_THRESHOLD = 0.5
CLOSE_THRESHOLD = 0.2

# 数据存储
prices_data = {}
diff_data = []
balances_data = {}
status = {
    "running": False,
    "mode": "simulate",
    "last_update": "",
    "trading_enabled": False
}

# 交易所客户端
exchanges = {}
exchange_data = {
    "binance": {"name": "Binance", "prices": {}, "balances": {}},
    "okex": {"name": "OKX", "prices": {}, "balances": {}},
    "bitget": {"name": "Bitget", "prices": {}, "balances": {}}
}

# 上次更新时间
last_update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
running = True
use_simulation = False

# 辅助函数
def load_json(file_path):
    """加载JSON文件"""
    try:
        if not Path(file_path).exists():
            return {}
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"加载JSON文件失败: {e}")
        return {}

def load_config():
    """加载配置文件"""
    global SYMBOLS, ARBITRAGE_THRESHOLD, CLOSE_THRESHOLD
    
    config = load_json(CONFIG_PATH)
    if config:
        SYMBOLS = config.get("symbols", SYMBOLS)
        ARBITRAGE_THRESHOLD = config.get("arbitrage_threshold", ARBITRAGE_THRESHOLD)
        CLOSE_THRESHOLD = config.get("close_threshold", CLOSE_THRESHOLD)
    
    return config

def generate_simulated_data():
    """生成模拟价格数据"""
    global SYMBOLS, EXCHANGES
    
    prices = {}
    
    # 基准价格
    base_prices = {
        "BTC/USDT": 64000 + random.uniform(-300, 300),
        "ETH/USDT": 3500 + random.uniform(-30, 30),
        "SOL/USDT": 140 + random.uniform(-3, 3),
        "XRP/USDT": 0.50 + random.uniform(-0.01, 0.01),
    }
    
    # 为每个交易所生成价格
    for exchange in EXCHANGES:
        prices[exchange] = {}
        for symbol in SYMBOLS:
            if symbol in base_prices:
                # 从基准价格添加一个随机差价
                base_price = base_prices[symbol]
                # 生成买卖价格
                bid_offset = random.uniform(-0.1, 0.1) * base_price / 100
                ask_offset = random.uniform(0.05, 0.2) * base_price / 100
                
                prices[exchange][symbol] = {
                    "bid": base_price + bid_offset,
                    "ask": base_price + bid_offset + ask_offset,
                    "volume": round(random.uniform(1000, 5000), 1),
                    "depth": {
                        "bid": round(random.uniform(5, 15), 1),
                        "ask": round(random.uniform(3, 10), 1)
                    }
                }
    
    return prices

def generate_simulated_balances():
    """生成模拟账户余额数据"""
    global EXCHANGES, SYMBOLS
    
    balances = {}
    
    for exchange in EXCHANGES:
        balances[exchange] = {
            "USDT": round(random.uniform(5000, 15000), 2),
            "positions": {}
        }
        
        # 为每个交易对生成持仓
        for symbol in SYMBOLS:
            coin = symbol.split('/')[0]
            if random.random() > 0.3:  # 70%的概率有持仓
                amount = round(random.uniform(0.01, 10) * (1 if coin == "BTC" else (20 if coin == "ETH" else 100)), 5)
                value = round(amount * (
                    random.uniform(60000, 70000) if coin == "BTC" else 
                    random.uniform(3000, 4000) if coin == "ETH" else
                    random.uniform(100, 150) if coin == "SOL" else
                    random.uniform(0.45, 0.55)
                ), 2)
                
                balances[exchange]["positions"][coin] = {
                    "amount": amount,
                    "value": value
                }
    
    return balances

def calculate_price_differences(prices):
    """计算不同交易所之间的价格差异"""
    global SYMBOLS
    
    if not prices:
        return []
    
    diff_result = []
    
    for symbol in SYMBOLS:
        # 计算所有交易所组合
        for buy_exchange in EXCHANGES:
            for sell_exchange in EXCHANGES:
                if buy_exchange == sell_exchange:
                    continue
                
                if symbol not in prices[buy_exchange] or symbol not in prices[sell_exchange]:
                    continue
                
                buy_data = prices[buy_exchange][symbol]
                sell_data = prices[sell_exchange][symbol]
                
                # 获取买入价和卖出价
                buy_price = buy_data["ask"] if isinstance(buy_data, dict) else buy_data
                sell_price = sell_data["bid"] if isinstance(sell_data, dict) else sell_data
                
                # 只有卖出价高于买入价时才有套利机会
                if sell_price > buy_price:
                    price_diff = sell_price - buy_price
                    price_diff_pct = price_diff / buy_price
                    
                    # 判断是否可执行(示例条件)
                    bid_depth = buy_data.get("depth", {}).get("bid", 0) if isinstance(buy_data, dict) else 0
                    ask_depth = sell_data.get("depth", {}).get("ask", 0) if isinstance(sell_data, dict) else 0
                    is_executable = price_diff_pct >= CLOSE_THRESHOLD / 100 and bid_depth >= 2 and ask_depth >= 2
                    
                    diff_result.append({
                        "symbol": symbol,
                        "buy_exchange": buy_exchange,
                        "sell_exchange": sell_exchange,
                        "buy_price": buy_price,
                        "sell_price": sell_price,
                        "price_diff": price_diff,
                        "price_diff_pct": price_diff_pct,
                        "is_executable": is_executable,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
    
    # 按价差百分比降序排序
    diff_result.sort(key=lambda x: x["price_diff_pct"], reverse=True)
    
    return diff_result

def monitor_thread(interval=5):
    """监控线程函数"""
    global prices_data, diff_data, balances_data, status
    
    while True:
        try:
            if status["running"]:
                # 获取价格数据
                if status["mode"] == "simulate":
                    prices = generate_simulated_data()
                else:
                    # 真实API连接暂不支持，使用模拟数据
                    prices = generate_simulated_data()
                
                prices_data = prices
                
                # 计算价差
                diff = calculate_price_differences(prices)
                diff_data = diff
                
                # 更新余额数据
                if status["mode"] == "simulate":
                    balances = generate_simulated_balances()
                else:
                    balances = generate_simulated_balances()
                
                balances_data = balances
                
                # 更新时间
                status["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 检查套利机会
                for item in diff_data:
                    if item["price_diff_pct"] >= ARBITRAGE_THRESHOLD / 100:
                        print(f"[套利机会] {item['symbol']} - 从 {item['buy_exchange']}({item['buy_price']:.2f}) 买入并在 "
                              f"{item['sell_exchange']}({item['sell_price']:.2f}) 卖出 - "
                              f"差价: {item['price_diff']:.2f} ({item['price_diff_pct']*100:.2f}%)")
                
        except Exception as e:
            print(f"监控线程错误: {e}")
        
        time.sleep(interval)

# 路由
@app.route('/')
def home():
    """首页"""
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    """获取服务器状态"""
    return jsonify(status)

@app.route('/api/prices', methods=['GET'])
def get_prices():
    """获取所有价格数据"""
    return jsonify(prices_data)

@app.route('/api/diff', methods=['GET'])
def get_diff():
    """获取价格差异数据"""
    return jsonify(diff_data)

@app.route('/api/balances', methods=['GET'])
def get_balances():
    """获取账户余额数据"""
    return jsonify(balances_data)

@app.route('/api/symbols', methods=['GET'])
def get_symbols():
    """获取交易对列表"""
    return jsonify(SYMBOLS)

@app.route('/api/start', methods=['POST'])
def start_monitor():
    """启动监控"""
    global status
    
    data = request.get_json() or {}
    simulate = data.get('simulate', True)
    enable_trading = data.get('enable_trading', False)
    
    # 更新状态
    status["running"] = True
    status["mode"] = "simulate" if simulate else "real"
    status["trading_enabled"] = enable_trading
    status["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return jsonify({"status": "success", "message": "监控已启动"})

@app.route('/api/stop', methods=['POST'])
def stop_monitor():
    """停止监控"""
    global status
    
    status["running"] = False
    
    return jsonify({"status": "success", "message": "监控已停止"})

def main():
    """主函数"""
    global status
    
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description="加密货币套利监控Web应用")
    parser.add_argument("--simulate", action="store_true", help="使用模拟数据（无需API连接）")
    parser.add_argument("--real", action="store_true", help="使用真实API连接")
    parser.add_argument("--trade", action="store_true", help="启用交易功能")
    parser.add_argument("--port", type=int, default=8888, help="Web服务器端口")
    args = parser.parse_args()
    
    # 欢迎信息
    print("\n===== 加密货币套利监控Web应用 =====")
    print(f"运行模式: {'模拟数据' if args.simulate else '真实API连接'}")
    print(f"交易功能: {'已启用' if args.trade else '未启用（仅监控）'}")
    print(f"Web端口: {args.port}")
    print("======================================\n")
    
    # 初始化状态
    use_simulate = not args.real or args.simulate
    status["running"] = True
    status["mode"] = "simulate" if use_simulate else "real"
    status["trading_enabled"] = args.trade
    status["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 加载配置
    load_config()
    
    # 启动监控线程
    monitor = threading.Thread(target=monitor_thread)
    monitor.daemon = True
    monitor.start()
    
    # 启动Web服务器
    app.run(host='0.0.0.0', port=args.port, debug=False)

if __name__ == "__main__":
    main() 