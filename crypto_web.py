#!/usr/bin/env python
import json
import time
import argparse
import threading
from datetime import datetime
from pathlib import Path
import logging
import random
from flask import Flask, render_template, jsonify
import ccxt
from loguru import logger

# 创建Flask应用
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# 全局变量
CONFIG_FILE = "crypto_config.json"
SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT",
    "ADA/USDT", "DOT/USDT", "MATIC/USDT", "AVAX/USDT", "SHIB/USDT"
]

# 状态变量
running = True
use_simulation = False
last_update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# 数据存储
exchanges = {}  # 交易所API客户端
exchange_data = {
    "binance": {"name": "Binance", "prices": {}, "balances": {}},
    "okex": {"name": "OKX", "prices": {}, "balances": {}},
    "bitget": {"name": "Bitget", "prices": {}, "balances": {}}
}
price_data = {}  # 价格数据
balance_data = {}  # 余额数据
arbitrage_opportunities = []  # 套利机会

# 添加常量
ARBITRAGE_THRESHOLD = 0.5  # 套利阈值，0.5%

# 初始化交易所连接
def init_exchanges():
    """初始化交易所API连接"""
    global exchanges
    
    try:
        # 读取配置文件
        config_path = Path(CONFIG_FILE)
        if not config_path.exists():
            logger.warning(f"配置文件 {CONFIG_FILE} 不存在，将使用模拟数据")
            return False
            
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        
        if not use_simulation:
            # 初始化Binance
            binance_config = {
                'apiKey': config["binance"]["key"],
                'secret': config["binance"]["secret"],
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'
                }
            }
            
            # 添加代理设置（如有需要）
            if 'proxy' in config:
                binance_config['proxies'] = {
                    'http': config['proxy'],
                    'https': config['proxy']
                }
                
            exchanges["binance"] = ccxt.binance(binance_config)
            logger.info("Binance API连接初始化完成")
            
            # 初始化OKEX
            okex_config = {
                'apiKey': config["okex"]["key"],
                'secret': config["okex"]["secret"],
                'password': config["okex"]["password"],
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'
                }
            }
            
            # 添加代理设置
            if 'proxy' in config:
                okex_config['proxies'] = {
                    'http': config['proxy'],
                    'https': config['proxy']
                }
                
            exchanges["okex"] = ccxt.okx(okex_config)
            logger.info("OKEX API连接初始化完成")
            
            # 初始化Bitget
            bitget_config = {
                'apiKey': config["bitget"]["key"],
                'secret': config["bitget"]["secret"],
                'password': config["bitget"]["password"] if "password" in config["bitget"] else None,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'
                }
            }
            
            # 添加代理设置
            if 'proxy' in config:
                bitget_config['proxies'] = {
                    'http': config['proxy'],
                    'https': config['proxy']
                }
                
            exchanges["bitget"] = ccxt.bitget(bitget_config)
            logger.info("Bitget API连接初始化完成")
            
            # 获取账户余额
            update_balances()
            
        logger.info("所有交易所API初始化完成")
        return True
    
    except Exception as e:
        logger.error(f"初始化交易所API失败: {e}")
        return False

# 更新账户余额
def update_balances():
    """获取各交易所账户余额"""
    global exchange_data, balance_data
    
    if use_simulation:
        # 模拟数据
        exchange_data["binance"]["balances"] = {
            "USDT": 12345.67,
            "BTC": 0.12345,
            "ETH": 1.5432,
            "SOL": 12.345
        }
        exchange_data["okex"]["balances"] = {
            "USDT": 9876.54,
            "BTC": 0.08765,
            "ETH": 2.1098
        }
        exchange_data["bitget"]["balances"] = {
            "USDT": 7654.32,
            "BTC": 0.05432,
            "SOL": 32.109
        }
        
        # 更新全局余额数据
        balance_data = {
            "binance": exchange_data["binance"]["balances"],
            "okex": exchange_data["okex"]["balances"],
            "bitget": exchange_data["bitget"]["balances"]
        }
        return
    
    try:
        balances = {}
        
        # 获取Binance余额
        binance_client = exchanges.get("binance")
        if binance_client:
            try:
                balance = binance_client.fetch_balance()
                if balance and 'free' in balance:
                    exchange_data["binance"]["balances"] = {
                        asset: float(amount)
                        for asset, amount in balance['free'].items()
                        if asset in ["USDT", "BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "DOT", "MATIC", "AVAX", "SHIB"] 
                        and float(amount) > 0
                    }
                    balances["binance"] = exchange_data["binance"]["balances"]
                logger.info("Binance余额更新成功")
            except Exception as e:
                logger.error(f"获取Binance余额失败: {e}")
        
        # 获取OKEX余额
        okex_client = exchanges.get("okex")
        if okex_client:
            try:
                balance = okex_client.fetch_balance()
                if balance and 'free' in balance:
                    exchange_data["okex"]["balances"] = {
                        asset: float(amount)
                        for asset, amount in balance['free'].items()
                        if asset in ["USDT", "BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "DOT", "MATIC", "AVAX", "SHIB"] 
                        and float(amount) > 0
                    }
                    balances["okex"] = exchange_data["okex"]["balances"]
                logger.info("OKX余额更新成功")
            except Exception as e:
                logger.error(f"获取OKX余额失败: {e}")
        
        # 获取Bitget余额
        bitget_client = exchanges.get("bitget")
        if bitget_client:
            try:
                balance = bitget_client.fetch_balance()
                if balance and 'free' in balance:
                    exchange_data["bitget"]["balances"] = {
                        asset: float(amount)
                        for asset, amount in balance['free'].items()
                        if asset in ["USDT", "BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "DOT", "MATIC", "AVAX", "SHIB"] 
                        and float(amount) > 0
                    }
                    balances["bitget"] = exchange_data["bitget"]["balances"]
                logger.info("Bitget余额更新成功")
            except Exception as e:
                logger.error(f"获取Bitget余额失败: {e}")
        
        # 更新全局余额数据
        balance_data = balances
        
    except Exception as e:
        logger.error(f"获取账户余额失败: {e}")

# 生成模拟价格数据
def generate_simulated_prices():
    """生成模拟的价格数据"""
    prices = {}
    
    for symbol in SYMBOLS:
        base, quote = symbol.split('/')
        base_price = {"BTC": 64000, "ETH": 3400, "SOL": 142, "XRP": 0.52, "DOGE": 0.13,
                      "ADA": 0.45, "DOT": 6.8, "MATIC": 0.65, "AVAX": 33, "SHIB": 0.000023}.get(base, 100)
        
        # 为每个交易所生成略微不同的价格
        binance_bid = base_price * (1 - random.uniform(0, 0.002))
        binance_ask = base_price * (1 + random.uniform(0, 0.002))
        okex_bid = base_price * (1 - random.uniform(0, 0.003))
        okex_ask = base_price * (1 + random.uniform(0, 0.003))
        bitget_bid = base_price * (1 - random.uniform(0, 0.0025))
        bitget_ask = base_price * (1 + random.uniform(0, 0.0025))
        
        # 生成随机深度
        binance_depth = round(random.uniform(5, 20), 1)
        okex_depth = round(random.uniform(4, 15), 1)
        bitget_depth = round(random.uniform(3, 12), 1)
        
        symbol_data = {
            "binance": {
                "buy": binance_bid,
                "sell": binance_ask,
                "depth": binance_depth
            },
            "okex": {
                "buy": okex_bid,
                "sell": okex_ask,
                "depth": okex_depth
            },
            "bitget": {
                "buy": bitget_bid,
                "sell": bitget_ask,
                "depth": bitget_depth
            },
            "max_depth": max(binance_depth, okex_depth, bitget_depth)
        }
        
        # 计算最大差价比例
        min_buy = min(binance_bid, okex_bid, bitget_bid)
        max_sell = max(binance_ask, okex_ask, bitget_ask)
        max_diff_pct = round((max_sell / min_buy - 1) * 100, 3)
        symbol_data["max_diff_pct"] = max_diff_pct
        
        prices[symbol] = symbol_data
    
    return prices

# 从交易所获取实际价格数据
def fetch_exchange_prices():
    """从交易所获取实际价格数据"""
    prices = {}
    
    for symbol in SYMBOLS:
        symbol_data = {}
        
        try:
            # Binance数据
            if "binance" in exchanges:
                try:
                    ticker = exchanges["binance"].fetch_ticker(symbol)
                    order_book = exchanges["binance"].fetch_order_book(symbol, 5)
                    if ticker and order_book:
                        binance_bid = ticker['bid'] if 'bid' in ticker else order_book['bids'][0][0] if order_book['bids'] else 0
                        binance_ask = ticker['ask'] if 'ask' in ticker else order_book['asks'][0][0] if order_book['asks'] else 0
                        binance_depth = min(
                            sum([amt for price, amt in order_book['bids'][:5]]),
                            sum([amt for price, amt in order_book['asks'][:5]])
                        ) if order_book['bids'] and order_book['asks'] else 0
                        
                        symbol_data["binance"] = {
                            "buy": binance_bid, 
                            "sell": binance_ask,
                            "depth": binance_depth
                        }
                        logger.debug(f"获取Binance {symbol}数据成功")
                except Exception as e:
                    logger.error(f"获取Binance {symbol}数据失败: {e}")
            
            # OKEX数据
            if "okex" in exchanges:
                try:
                    ticker = exchanges["okex"].fetch_ticker(symbol)
                    order_book = exchanges["okex"].fetch_order_book(symbol, 5)
                    if ticker and order_book:
                        okex_bid = ticker['bid'] if 'bid' in ticker else order_book['bids'][0][0] if order_book['bids'] else 0
                        okex_ask = ticker['ask'] if 'ask' in ticker else order_book['asks'][0][0] if order_book['asks'] else 0
                        okex_depth = min(
                            sum([amt for price, amt in order_book['bids'][:5]]),
                            sum([amt for price, amt in order_book['asks'][:5]])
                        ) if order_book['bids'] and order_book['asks'] else 0
                        
                        symbol_data["okex"] = {
                            "buy": okex_bid, 
                            "sell": okex_ask,
                            "depth": okex_depth
                        }
                        logger.debug(f"获取OKX {symbol}数据成功")
                except Exception as e:
                    logger.error(f"获取OKX {symbol}数据失败: {e}")
            
            # Bitget数据
            if "bitget" in exchanges:
                try:
                    ticker = exchanges["bitget"].fetch_ticker(symbol)
                    order_book = exchanges["bitget"].fetch_order_book(symbol, 5)
                    if ticker and order_book:
                        bitget_bid = ticker['bid'] if 'bid' in ticker else order_book['bids'][0][0] if order_book['bids'] else 0
                        bitget_ask = ticker['ask'] if 'ask' in ticker else order_book['asks'][0][0] if order_book['asks'] else 0
                        bitget_depth = min(
                            sum([amt for price, amt in order_book['bids'][:5]]),
                            sum([amt for price, amt in order_book['asks'][:5]])
                        ) if order_book['bids'] and order_book['asks'] else 0
                        
                        symbol_data["bitget"] = {
                            "buy": bitget_bid, 
                            "sell": bitget_ask,
                            "depth": bitget_depth
                        }
                        logger.debug(f"获取Bitget {symbol}数据成功")
                except Exception as e:
                    logger.error(f"获取Bitget {symbol}数据失败: {e}")
            
            # 如果成功获取至少一个交易所的数据
            if symbol_data:
                # 计算最大深度
                depths = [data.get("depth", 0) for ex, data in symbol_data.items()]
                max_depth = max(depths) if depths else 0
                symbol_data["max_depth"] = max_depth
                
                # 计算差价比例
                if len(symbol_data) >= 2:
                    buy_prices = [data.get("buy", 0) for ex, data in symbol_data.items() if "buy" in data]
                    sell_prices = [data.get("sell", 0) for ex, data in symbol_data.items() if "sell" in data]
                    
                    if buy_prices and sell_prices:
                        min_buy = min(buy_prices)
                        max_sell = max(sell_prices)
                        max_diff_pct = round((max_sell / min_buy - 1) * 100, 3) if min_buy > 0 else 0
                        symbol_data["max_diff_pct"] = max_diff_pct
                
                prices[symbol] = symbol_data
        
        except Exception as e:
            logger.error(f"处理{symbol}价格数据失败: {e}")
    
    return prices

# 价格监控线程
def price_monitor_thread():
    """持续获取价格数据的线程"""
    global price_data, arbitrage_opportunities, last_update_time
    
    logger.info("价格监控线程启动")
    
    while running:
        try:
            # 获取价格数据
            if use_simulation:
                current_prices = generate_simulated_prices()
            else:
                current_prices = fetch_exchange_prices()
            
            # 更新价格数据
            price_data = current_prices
            
            # 计算套利机会
            arbitrage_opportunities = calculate_arbitrage(current_prices)
            
            # 更新时间戳
            last_update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 每5秒更新一次
            time.sleep(5)
            
            # 每隔5分钟更新一次余额
            if int(time.time()) % 300 < 5 and not use_simulation:
                update_balances()
                
        except Exception as e:
            logger.error(f"价格监控线程异常: {e}")
            time.sleep(10)

# 计算套利机会
def calculate_arbitrage(prices):
    """计算所有可能的套利机会"""
    opportunities = []
    
    for symbol, data in prices.items():
        # 确保至少有两个交易所的数据
        exchanges_with_data = [ex for ex in ["binance", "okex", "bitget"] if ex in data]
        if len(exchanges_with_data) < 2:
            continue
        
        # 计算所有可能的交易所对之间的套利机会
        for buy_exchange in exchanges_with_data:
            for sell_exchange in exchanges_with_data:
                if buy_exchange == sell_exchange:
                    continue
                
                if "buy" in data[buy_exchange] and "sell" in data[sell_exchange]:
                    buy_price = data[buy_exchange]["buy"]
                    sell_price = data[sell_exchange]["sell"]
                    
                    # 确保买价小于卖价，才有套利空间
                    if sell_price > buy_price:
                        diff = sell_price - buy_price
                        diff_pct = (sell_price / buy_price - 1) * 100
                        
                        # 检查是否可执行（基于深度）
                        buy_depth = data[buy_exchange].get("depth", 0)
                        sell_depth = data[sell_exchange].get("depth", 0)
                        is_executable = diff_pct >= 0.1 and min(buy_depth, sell_depth) >= 0.01
                        
                        opportunity = {
                            "symbol": symbol,
                            "buy_exchange": buy_exchange,
                            "sell_exchange": sell_exchange,
                            "buy_price": buy_price,
                            "sell_price": sell_price,
                            "diff": diff,
                            "diff_pct": round(diff_pct, 3),
                            "executable": is_executable
                        }
                        opportunities.append(opportunity)
    
    # 按差价比例降序排序
    opportunities.sort(key=lambda x: x["diff_pct"], reverse=True)
    
    # 只返回前10个机会
    return opportunities[:10]

# API路由
@app.route('/')
def home():
    """渲染主页"""
    mode = "模拟模式" if use_simulation else "实盘模式"
    return render_template('index.html', mode=mode, last_update=last_update_time)

@app.route('/api/data')
def get_data():
    """API: 返回所有数据"""
    return jsonify({
        "status": "running",
        "mode": "simulation" if use_simulation else "real",
        "last_update": last_update_time,
        "exchanges": {
            "binance": {
                "name": "Binance",
                "prices": {symbol: data.get("binance", {}) for symbol, data in price_data.items() if "binance" in data}
            },
            "okex": {
                "name": "OKX",
                "prices": {symbol: data.get("okex", {}) for symbol, data in price_data.items() if "okex" in data}
            },
            "bitget": {
                "name": "Bitget",
                "prices": {symbol: data.get("bitget", {}) for symbol, data in price_data.items() if "bitget" in data}
            },
            "arbitrage": arbitrage_opportunities
        }
    })

@app.route('/api/prices')
def get_prices():
    """API: 返回价格数据"""
    return jsonify({
        "last_update": last_update_time,
        "prices": price_data
    })

@app.route('/api/balances')
def get_balances():
    """API: 返回余额数据"""
    return jsonify({
        "last_update": last_update_time,
        "balances": balance_data
    })

@app.route('/api/arbitrage')
def get_arbitrage():
    """API: 返回套利机会"""
    return jsonify({
        "last_update": last_update_time,
        "opportunities": arbitrage_opportunities
    })

@app.route('/api/symbols')
def get_symbols():
    """API: 返回支持的交易对列表"""
    return jsonify({
        "symbols": SYMBOLS
    })

# 主函数
def main():
    global use_simulation, running
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="加密货币套利监控系统")
    parser.add_argument("--simulate", action="store_true", help="使用模拟数据")
    parser.add_argument("--port", type=int, default=8888, help="Web服务端口")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    args = parser.parse_args()
    
    use_simulation = args.simulate
    
    # 配置日志
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger.remove()  # 移除默认处理器
    logger.add("crypto_web.log", rotation="10 MB", level=log_level)
    logger.add(lambda msg: print(msg), level=log_level)
    
    logger.info("=" * 37)
    logger.info("===== 加密货币套利监控Web应用 =====")
    logger.info(f"运行模式: {'模拟数据' if use_simulation else '实盘数据'}")
    logger.info(f"交易功能: {'未启用（仅监控）'}")
    logger.info(f"Web端口: {args.port}")
    logger.info("=" * 37)
    
    # 初始化交易所连接
    if not use_simulation:
        success = init_exchanges()
        if not success:
            logger.warning("交易所API初始化失败，将使用模拟数据")
            use_simulation = True
    else:
        # 生成模拟余额数据
        update_balances()
    
    # 启动价格监控线程
    monitor_thread = threading.Thread(target=price_monitor_thread)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    try:
        # 启动Web服务
        app.run(host='0.0.0.0', port=args.port, threaded=True)
    except KeyboardInterrupt:
        logger.info("接收到停止信号，正在关闭...")
    finally:
        running = False
        logger.info("系统已停止")

if __name__ == "__main__":
    main() 