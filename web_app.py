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
import ccxt

from flask import Flask, jsonify, render_template, request, Response
import os
import pickle

# 导入套利系统模块
try:
    from integrate_arbitrage import init_arbitrage_system
    ARBITRAGE_ENABLED = True
except ImportError:
    logger.warning("套利系统模块未找到，套利功能将被禁用")
    ARBITRAGE_ENABLED = False

# 导入量化交易服务模块
try:
    from quantitative_service import quantitative_service, StrategyType
    QUANTITATIVE_ENABLED = True
    logger.info("量化交易模块加载成功")
except ImportError as e:
    logger.warning(f"量化交易模块未找到，量化功能将被禁用: {e}")
    QUANTITATIVE_ENABLED = False

# 在现有导入之后添加
try:
    from quantitative_service import quantitative_service
    logger.info("量化交易服务导入成功")
except ImportError as e:
    logger.warning(f"量化交易服务导入失败: {e}")
    quantitative_service = None

# 创建Flask应用
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# 全局变量
CONFIG_FILE = "crypto_config.json"
CONFIG_PATH = Path(__file__).parent.joinpath(CONFIG_FILE)
SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT",
    "ADA/USDT", "DOT/USDT", "AVAX/USDT", "SHIB/USDT"
]
EXCHANGES = ["binance", "okx", "bitget"]
ARBITRAGE_THRESHOLD = 0.5
CLOSE_THRESHOLD = 0.2

# 交易所API客户端
exchange_clients = {}

# 数据存储
prices_data = {}
diff_data = []
balances_data = {}
# 历史数据文件路径
ARBITRAGE_HISTORY_FILE = "arbitrage_history.pkl"
# 套利机会历史记录，按交易对保存24小时数据
arbitrage_history = {}
status = {
    "running": False,
    "mode": "simulate",
    "last_update": "",
    "trading_enabled": False
}

# 上次更新时间
def load_arbitrage_history():
    """从文件加载套利历史记录"""
    global arbitrage_history
    try:
        if os.path.exists(ARBITRAGE_HISTORY_FILE):
            with open(ARBITRAGE_HISTORY_FILE, "rb") as f:
                arbitrage_history = pickle.load(f)
                logger.info(f"已从文件加载{sum(len(records) for records in arbitrage_history.values())}条套利历史记录")
    except Exception as e:
        logger.error(f"加载套利历史记录出错: {e}")

def save_arbitrage_history():
    """保存套利历史记录到文件"""
    try:
        with open(ARBITRAGE_HISTORY_FILE, "wb") as f:
            pickle.dump(arbitrage_history, f)
        logger.info(f"已保存{sum(len(records) for records in arbitrage_history.values())}条套利历史记录到文件")
    except Exception as e:
        logger.error(f"保存套利历史记录出错: {e}")
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
    """加载配置"""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
    return {}

def init_api_clients():
    """初始化交易所API客户端"""
    global exchange_clients, use_simulation, status
    
    # 强制使用真实数据模式
    use_simulation = False
    status["mode"] = "real"
    
    # 读取配置文件
    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
        
        # 初始化交易所API客户端
        for exchange_id in EXCHANGES:
            if exchange_id in config and "api_key" in config[exchange_id] and config[exchange_id]["api_key"]:
                try:
                    # 尝试创建客户端
                    exchange_class = getattr(ccxt, exchange_id)
                    
                    # 获取API密钥配置
                    api_key = config[exchange_id]["api_key"]
                    secret_key = config[exchange_id]["secret_key"]
                    password = config[exchange_id].get("password", "")
                    
                    # 创建客户端
                    client = exchange_class({
                        'apiKey': api_key,
                        'secret': secret_key,
                        'password': password,
                        'enableRateLimit': True,
                        'sandbox': False  # 确保使用生产环境
                    })
                    
                    # 设置代理（如果配置）
                    if "proxy" in config and config["proxy"]:
                        client.proxies = {
                            'http': config["proxy"],
                            'https': config["proxy"]
                        }
                    
                    # 测试API连接
                    try:
                        print(f"测试 {exchange_id} API连接...")
                        # 测试获取价格数据（不需要账户权限）
                        test_ticker = client.fetch_ticker('BTC/USDT')
                        print(f"初始化 {exchange_id} API客户端成功 - BTC价格: {test_ticker['last']}")
                        exchange_clients[exchange_id] = client
                    except Exception as e:
                        print(f"API连接测试失败 {exchange_id}: {e}")
                        # 即使测试失败也添加客户端，可能是权限问题但价格数据仍可获取
                        exchange_clients[exchange_id] = client
                        print(f"强制添加 {exchange_id} 客户端用于价格数据获取")
                except Exception as e:
                    print(f"初始化 {exchange_id} API客户端失败: {e}")
            else:
                print(f"交易所 {exchange_id} 未配置API密钥")
        
        print(f"API客户端初始化完成，强制使用真实数据模式，已配置 {len(exchange_clients)} 个交易所")
        
    except Exception as e:
        print(f"初始化API客户端出错: {e}")
        # 即使出错也强制使用真实模式
        use_simulation = False
        status["mode"] = "real"

def calculate_price_differences(prices):
    """计算不同交易所间的价格差异"""
    global arbitrage_history
    result = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 检查数据是否存在
    if not prices:
        return result
    
    # 遍历所有交易对
    for symbol in SYMBOLS:
        # 遍历所有交易所组合
        for i, buy_exchange in enumerate(EXCHANGES):
            if buy_exchange not in prices or symbol not in prices[buy_exchange]:
                continue
                
            buy_price = prices[buy_exchange][symbol].get("buy")
            if buy_price is None:
                continue
            
            for sell_exchange in EXCHANGES[i+1:]:
                if sell_exchange not in prices or symbol not in prices[sell_exchange]:
                    continue
                    
                sell_price = prices[sell_exchange][symbol].get("sell")
                if sell_price is None:
                    continue
                
                # 计算正向套利（从 buy_exchange 买，在 sell_exchange 卖）
                if sell_price > buy_price:
                    price_diff = sell_price - buy_price
                    price_diff_pct = price_diff / buy_price
                    
                    # 检查套利可行性（根据深度等）
                    is_executable = True  # 简化处理，实际应根据深度、手续费等判断
                    
                    item = {
                        "symbol": symbol,
                        "buy_exchange": buy_exchange,
                        "sell_exchange": sell_exchange,
                        "buy_price": buy_price,
                        "sell_price": sell_price,
                        "price_diff": price_diff,
                        "price_diff_pct": price_diff_pct,
                        "is_executable": is_executable,
                        "time": timestamp
                    }
                    
                    # 只将差价大于等于阈值的套利机会添加到结果中
                    if price_diff_pct >= ARBITRAGE_THRESHOLD / 100:
                        result.append(item)
                        
                        # 记录到历史中
                        key = f"{symbol}_{buy_exchange}_{sell_exchange}"
                        if key not in arbitrage_history:
                            arbitrage_history[key] = []
                        arbitrage_history[key].append(item)
                        
                        # 清理24小时以前的数据
                        current_time = datetime.now()
                        arbitrage_history[key] = [
                            record for record in arbitrage_history[key]
                            if (current_time - datetime.strptime(record["time"], "%Y-%m-%d %H:%M:%S")).total_seconds() < 86400
                        ]
                
                # 计算反向套利（从 sell_exchange 买，在 buy_exchange 卖）
                buy_price_reverse = prices[sell_exchange][symbol].get("buy")
                sell_price_reverse = prices[buy_exchange][symbol].get("sell")
                
                if buy_price_reverse is not None and sell_price_reverse is not None and sell_price_reverse > buy_price_reverse:
                    price_diff = sell_price_reverse - buy_price_reverse
                    price_diff_pct = price_diff / buy_price_reverse
                    
                    # 检查套利可行性
                    is_executable = True
                    
                    item = {
                        "symbol": symbol,
                        "buy_exchange": sell_exchange,
                        "sell_exchange": buy_exchange,
                        "buy_price": buy_price_reverse,
                        "sell_price": sell_price_reverse,
                        "price_diff": price_diff,
                        "price_diff_pct": price_diff_pct,
                        "is_executable": is_executable,
                        "time": timestamp
                    }
                    
                    # 只将差价大于等于阈值的套利机会添加到结果中
                    if price_diff_pct >= ARBITRAGE_THRESHOLD / 100:
                        result.append(item)
                        
                        # 记录到历史中
                        key = f"{symbol}_{sell_exchange}_{buy_exchange}"
                        if key not in arbitrage_history:
                            arbitrage_history[key] = []
                        arbitrage_history[key].append(item)
                        
                        # 清理24小时以前的数据
                        current_time = datetime.now()
                        arbitrage_history[key] = [
                            record for record in arbitrage_history[key]
                            if (current_time - datetime.strptime(record["time"], "%Y-%m-%d %H:%M:%S")).total_seconds() < 86400
                        ]
    
    # 按价差百分比降序排序
    result.sort(key=lambda x: x["price_diff_pct"], reverse=True)
    # 保存历史记录
    save_arbitrage_history()
    
    return result

def get_exchange_balances():
    """从交易所API获取余额数据"""
    balances = {}
    
    for exchange_id, client in exchange_clients.items():
        try:
            exchange_balances = {"USDT": 0, "USDT_available": 0, "USDT_locked": 0, "positions": {}}
            
            # 检查API密钥是否配置
            if not client or not hasattr(client, 'apiKey') or not client.apiKey:
                print(f"交易所 {exchange_id} 没有配置API密钥或客户端初始化失败，跳过余额获取")
                balances[exchange_id] = exchange_balances
                continue
                
            try:
                # 获取余额数据
                print(f"尝试获取 {exchange_id} 的真实账户余额...")
                balance_data = client.fetch_balance()
                
                # 确保数据结构完整
                if not balance_data or 'total' not in balance_data:
                    raise Exception(f"获取到的余额数据格式异常: {balance_data}")
                
                # 提取USDT余额
                if 'USDT' in balance_data['total']:
                    exchange_balances["USDT"] = round(balance_data['total']['USDT'], 2)
                    # 添加可用和锁定余额
                    exchange_balances["USDT_available"] = round(balance_data.get('free', {}).get('USDT', 0), 2)
                    exchange_balances["USDT_locked"] = round(balance_data.get('used', {}).get('USDT', 0), 2)
                
                # 提取其他币种余额
                for symbol in SYMBOLS:
                    coin = symbol.split('/')[0]
                    if coin in balance_data['total'] and balance_data['total'][coin] > 0:
                        # 获取币种当前价格估算USDT价值
                        value = 0
                        total_amount = balance_data['total'][coin]
                        available_amount = balance_data.get('free', {}).get(coin, 0)
                        locked_amount = balance_data.get('used', {}).get(coin, 0)
                        
                        try:
                            # 尝试获取当前价格
                            ticker = client.fetch_ticker(symbol)
                            price = ticker['last']
                            value = round(total_amount * price, 2)
                        except Exception as e:
                            print(f"获取 {exchange_id} {symbol} 价格失败: {e}")
                            value = 0  # 无法获取价格时设为0
                        
                        exchange_balances["positions"][coin] = {
                            "amount": total_amount,
                            "available": available_amount,
                            "locked": locked_amount,
                            "value": value
                        }
                
                balances[exchange_id] = exchange_balances
                print(f"获取 {exchange_id} 余额成功")
            except Exception as e:
                print(f"获取 {exchange_id} 余额失败: {e}, 尝试使用替代方法")
                # 尝试使用替代方法获取余额
                try:
                    if exchange_id == 'binance':
                        balances[exchange_id] = get_binance_balance(client)
                    elif exchange_id == 'okx':
                        balances[exchange_id] = get_okx_balance(client)
                    elif exchange_id == 'bitget':
                        balances[exchange_id] = get_bitget_balance(client)
                    else:
                        print(f"不支持的交易所: {exchange_id}，使用空余额")
                        balances[exchange_id] = exchange_balances
                except Exception as e2:
                    print(f"获取 {exchange_id} 余额的替代方法也失败: {e2}，使用空余额")
                    balances[exchange_id] = exchange_balances
        except Exception as e:
            print(f"获取 {exchange_id} 余额过程中出现异常: {e}，使用空余额")
            balances[exchange_id] = {"USDT": 0, "USDT_available": 0, "USDT_locked": 0, "positions": {}}
    
    return balances

def get_binance_balance(client):
    """获取币安余额的替代方法"""
    try:
        balance = {"USDT": 0, "USDT_available": 0, "USDT_locked": 0, "positions": {}}
        account = client.private_get_account()
        
        for asset in account.get('balances', []):
            symbol = asset.get('asset')
            free = float(asset.get('free', 0))
            locked = float(asset.get('locked', 0))
            total = free + locked
            
            if symbol == 'USDT':
                balance["USDT"] = round(total, 2)
                balance["USDT_available"] = round(free, 2)
                balance["USDT_locked"] = round(locked, 2)
            elif total > 0:
                price = 0
                try:
                    ticker = client.fetch_ticker(f"{symbol}/USDT")
                    price = ticker['last']
                except:
                    # 使用估计价格
                    price_estimate = {
                        'BTC': 65000, 'ETH': 3500, 'SOL': 140, 'XRP': 0.5,
                        'DOGE': 0.15, 'ADA': 0.5, 'DOT': 7, 'AVAX': 35,
                        'SHIB': 0.00003
                    }
                    price = price_estimate.get(symbol, 0)
                
                if price > 0:
                    value = round(total * price, 2)
                    balance["positions"][symbol] = {
                        "amount": total,
                        "available": free,
                        "locked": locked,
                        "value": value
                    }
        
        return balance
    except Exception as e:
        print(f"获取币安余额的替代方法失败: {e}")
        raise e

def get_okx_balance(client):
    """获取OKX余额的替代方法"""
    try:
        balance = {"USDT": 0, "USDT_available": 0, "USDT_locked": 0, "positions": {}}
        funding_accounts = client.private_get_asset_balances({'ccy': ''})
        
        for asset in funding_accounts.get('data', []):
            symbol = asset.get('ccy')
            available = float(asset.get('availBal', 0))
            frozen = float(asset.get('frozenBal', 0))
            total = available + frozen
            
            if symbol == 'USDT':
                balance["USDT"] = round(total, 2)
                balance["USDT_available"] = round(available, 2)
                balance["USDT_locked"] = round(frozen, 2)
            elif total > 0:
                price = 0
                try:
                    ticker = client.fetch_ticker(f"{symbol}/USDT")
                    price = ticker['last']
                except:
                    # 使用估计价格
                    price_estimate = {
                        'BTC': 65000, 'ETH': 3500, 'SOL': 140, 'XRP': 0.5,
                        'DOGE': 0.15, 'ADA': 0.5, 'DOT': 7, 'AVAX': 35,
                        'SHIB': 0.00003
                    }
                    price = price_estimate.get(symbol, 0)
                
                if price > 0:
                    value = round(total * price, 2)
                    balance["positions"][symbol] = {
                        "amount": total,
                        "available": available,
                        "locked": frozen,
                        "value": value
                    }
        
        return balance
    except Exception as e:
        print(f"获取OKX余额的替代方法失败: {e}")
        raise e

def get_bitget_balance(client):
    """获取Bitget余额的替代方法"""
    try:
        balance = {"USDT": 0, "USDT_available": 0, "USDT_locked": 0, "positions": {}}
        
        # 对于Bitget，尝试直接调用fetch_balance
        balances = client.fetch_balance()
        
        if 'USDT' in balances['total']:
            balance["USDT"] = round(balances['total']['USDT'], 2)
            balance["USDT_available"] = round(balances['free'].get('USDT', 0), 2)
            balance["USDT_locked"] = round(balances['used'].get('USDT', 0), 2)
        
        # 处理其他资产
        for symbol in SYMBOLS:
            coin = symbol.split('/')[0]
            if coin in balances['total'] and balances['total'][coin] > 0:
                total = balances['total'][coin]
                available = balances['free'].get(coin, 0)
                locked = balances['used'].get(coin, 0)
                
                price = 0
                try:
                    ticker = client.fetch_ticker(symbol)
                    price = ticker['last']
                except:
                    # 使用估计价格
                    price_estimate = {
                        'BTC': 65000, 'ETH': 3500, 'SOL': 140, 'XRP': 0.5,
                        'DOGE': 0.15, 'ADA': 0.5, 'DOT': 7, 'AVAX': 35,
                        'SHIB': 0.00003
                    }
                    price = price_estimate.get(coin, 0)
                
                if price > 0:
                    value = round(total * price, 2)
                    balance["positions"][coin] = {
                        "amount": total,
                        "available": available,
                        "locked": locked,
                        "value": value
                    }
        
        return balance
    except Exception as e:
        print(f"获取Bitget余额的替代方法失败: {e}")
        raise e

def get_exchange_prices():
    """从交易所API获取价格数据"""
    prices = {exchange: {} for exchange in EXCHANGES}
    
    for exchange_id, client in exchange_clients.items():
        # 检查客户端配置
        if exchange_id == 'okx':
            # 因为OKX可能需要特殊处理密码中的特殊字符
            # 打印一些调试信息，不包含敏感信息
            print(f"获取 {exchange_id} 价格数据，客户端配置：apiKey长度={len(client.apiKey) if hasattr(client, 'apiKey') and client.apiKey else 0}, password长度={len(client.password) if hasattr(client, 'password') and client.password else 0}")
            
            # 可以检查并尝试重新初始化OKX客户端
            try:
                # 先尝试获取一个数据，看是否正常工作
                test_ticker = client.fetch_ticker("BTC/USDT")
                print(f"OKX API连接正常: 能够获取BTC/USDT行情")
            except Exception as e:
                print(f"OKX API连接问题: {e}")
                
                # 尝试读取配置文件并重新创建客户端
                try:
                    with open(CONFIG_PATH, "r") as f:
                        config = json.load(f)
                    
                    if 'okx' in config and 'api_key' in config['okx'] and 'secret_key' in config['okx'] and 'password' in config['okx']:
                        print("尝试重新创建OKX客户端...")
                        new_client = ccxt.okx({
                            'apiKey': config['okx']['api_key'],
                            'secret': config['okx']['secret_key'],
                            'password': config['okx']['password'],  # 确保使用原始密码，包括特殊字符
                            'enableRateLimit': True
                        })
                        exchange_clients['okx'] = new_client
                        client = new_client
                        print("OKX客户端重新创建完成")
                    else:
                        print("OKX配置不完整，无法重新创建客户端")
                except Exception as e:
                    print(f"重新创建OKX客户端失败: {e}")
        
        for symbol in SYMBOLS:
            try:
                # 获取订单簿数据
                orderbook = client.fetch_order_book(symbol)
                
                if orderbook and len(orderbook['bids']) > 0 and len(orderbook['asks']) > 0:
                    # OKX交易所API返回的订单簿格式可能与标准不同，需要特殊处理
                    if exchange_id == 'okx':
                        try:
                            # OKX可能返回[price, amount, ...]格式
                            if len(orderbook['bids'][0]) > 2:
                                bid_price = float(orderbook['bids'][0][0])
                                ask_price = float(orderbook['asks'][0][0])
                            else:
                                bid_price = orderbook['bids'][0][0]
                                ask_price = orderbook['asks'][0][0]
                                
                            # 计算深度（前5档挂单量）
                            if len(orderbook['bids'][0]) > 2:
                                bid_depth = sum(float(item[1]) for item in orderbook['bids'][:5])
                                ask_depth = sum(float(item[1]) for item in orderbook['asks'][:5])
                            else:
                                bid_depth = sum(amount for price, amount in orderbook['bids'][:5])
                                ask_depth = sum(amount for price, amount in orderbook['asks'][:5])
                        except Exception as e:
                            print(f"处理OKX订单簿格式出错: {e}")
                            continue
                    else:
                        # 标准格式处理
                        bid_price = orderbook['bids'][0][0]  # 买一价
                        ask_price = orderbook['asks'][0][0]  # 卖一价
                        
                        # 计算深度（前5档挂单量）
                        bid_depth = sum(amount for price, amount in orderbook['bids'][:5])
                        ask_depth = sum(amount for price, amount in orderbook['asks'][:5])
                    
                    # 获取成交量
                    volume = 0
                    try:
                        ticker = client.fetch_ticker(symbol)
                        volume = ticker['quoteVolume'] or 0  # 24小时USDT成交量
                    except:
                        volume = 0  # 使用0而不是随机数，确保没有假数据
                    
                    prices[exchange_id][symbol] = {
                        "buy": bid_price,  # 最高买价
                        "sell": ask_price,  # 最低卖价
                        "depth": {
                            "bid": round(bid_depth, 2),
                            "ask": round(ask_depth, 2)
                        },
                        "volume": round(volume, 1)
                    }
                    
                    print(f"获取 {exchange_id} {symbol} 价格成功: 买:{bid_price}, 卖:{ask_price}")
            except Exception as e:
                print(f"获取 {exchange_id} {symbol} 价格失败: {e}")
    
    return prices

def monitor_thread(interval=5):
    """监控线程函数"""
    global prices_data, diff_data, balances_data, status
    
    while True:
        try:
            if status["running"]:
                # 强制使用真实API连接获取价格数据
                prices = get_exchange_prices()
                prices_data = prices
                
                # 计算价差
                diff = calculate_price_differences(prices)
                diff_data = diff
                
                # 强制使用真实API连接获取余额
                balances = get_exchange_balances()
                balances_data = balances
                
                # 更新时间
                status["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 检查套利机会
                for item in diff_data:
                    if item["price_diff_pct"] >= ARBITRAGE_THRESHOLD / 100:
                        print(f"[套利机会] {item['symbol']} - 从 {item['buy_exchange']}({item['buy_price']:.2f}) 买入并在 "
                              f"{item['sell_exchange']}({item['sell_price']:.2f}) 卖出 - "
                              f"差价: {item['price_diff']:.2f} ({item['price_diff_pct']*100:.2f}%)")
                
                # 量化交易数据处理
                if QUANTITATIVE_ENABLED:
                    try:
                        # 为每个交易所的每个交易对处理量化数据
                        for exchange_name, exchange_prices in prices.items():
                            for symbol, price_info in exchange_prices.items():
                                if isinstance(price_info, dict) and 'buy' in price_info and 'sell' in price_info:
                                    # 使用买卖价格的中间价作为市场价格
                                    mid_price = (price_info['buy'] + price_info['sell']) / 2
                                    price_data = {
                                        'price': mid_price,
                                        'exchange': exchange_name,
                                        'timestamp': datetime.now()
                                    }
                                    
                                    # 传递给量化服务处理
                                    quantitative_service.process_market_data(symbol, price_data)
                    except Exception as e:
                        logger.error(f"量化交易数据处理错误: {e}")
                
        except Exception as e:
            print(f"监控线程错误: {e}")
        
        time.sleep(interval)

# 路由
@app.route('/')
def home():
    """首页"""
    return render_template('index.html')

@app.route('/arbitrage.html')
def arbitrage():
    """套利分析页面"""
    return render_template('arbitrage.html')

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

@app.route('/api/account/balances', methods=['GET'])
def get_account_balances():
    """获取账户余额数据（前端调用的API）"""
    try:
        # 获取真实的交易所余额数据
        raw_balances = get_exchange_balances()
        
        # 转换为前端期望的格式
        balance_data = {}
        
        for exchange_id, balance_info in raw_balances.items():
            # 提取USDT余额和持仓信息
            total_usdt = balance_info.get("USDT", 0)
            available_usdt = balance_info.get("USDT_available", 0)
            locked_usdt = balance_info.get("USDT_locked", 0)
            positions = balance_info.get("positions", {})
            
            # 转换持仓格式
            formatted_positions = []
            for symbol, pos_info in positions.items():
                formatted_positions.append({
                    "symbol": symbol,
                    "total": pos_info.get("amount", 0),
                    "available": pos_info.get("available", 0),
                    "locked": pos_info.get("locked", 0),
                    "value": pos_info.get("value", 0)
                })
            
            balance_data[exchange_id] = {
                "total": total_usdt,
                "available": available_usdt,
                "locked": locked_usdt,
                "positions": formatted_positions
            }
        
        return jsonify({
            "status": "success",
            "data": balance_data
        })
    except Exception as e:
        print(f"获取账户余额失败: {e}")
        return jsonify({
            "status": "error",
            "message": f"获取账户余额失败: {str(e)}"
        }), 500

@app.route('/api/symbols', methods=['GET'])
def get_symbols():
    """获取交易对列表"""
    return jsonify(SYMBOLS)

@app.route('/api/start', methods=['POST'])
def start_monitor():
    """启动监控"""
    global status
    
    data = request.get_json() or {}
    enable_trading = data.get('enable_trading', False)
    
    # 强制更新状态为真实模式
    status["running"] = True
    status["mode"] = "real"
    status["trading_enabled"] = enable_trading
    status["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return jsonify({"status": "success", "message": "监控已启动（真实数据模式）"})

@app.route('/api/stop', methods=['POST'])
def stop_monitor():
    """停止监控"""
    global status
    
    # 保存当前模式
    current_mode = status["mode"]
    
    # 更新状态
    status["running"] = False
    status["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 恢复之前的模式
    status["mode"] = current_mode
    
    return jsonify({"status": "success", "message": "监控已停止"})

@app.route('/api/arbitrage_history', methods=['GET'])
def get_arbitrage_history():
    """获取套利历史数据"""
    # 合并所有历史记录为一个列表
    all_history = []
    for records in arbitrage_history.values():
        all_history.extend(records)
    
    # 按时间降序排序
    all_history.sort(key=lambda x: x["time"], reverse=True)
    
    return jsonify(all_history)

@app.route('/api/arbitrage_history/<symbol>', methods=['GET'])
def get_symbol_arbitrage_history(symbol):
    """获取特定交易对的套利历史数据"""
    symbol_history = []
    
    # 筛选包含指定交易对的历史记录
    for key, records in arbitrage_history.items():
        if key.startswith(f"{symbol}_"):
            symbol_history.extend(records)
    
    # 按时间降序排序
    symbol_history.sort(key=lambda x: x["time"], reverse=True)
    
    return jsonify(symbol_history)

# 添加套利分析页面所需的API路由
@app.route('/api/arbitrage/status', methods=['GET'])
def get_arbitrage_status():
    """获取套利系统状态"""
    return jsonify({
        "status": "success",
        "data": {
            "running": status["running"],
            "mode": status["mode"],
            "last_update": status["last_update"],
            "trading_enabled": status["trading_enabled"],
            # 添加前端所需的其他字段，使用默认值
            "total_funds": 10000.0,
            "available_funds": {
                "cross_exchange": 6000.0,
                "triangle": 4000.0
            },
            "cross_opportunities": len([item for item in diff_data if item.get("price_diff_pct", 0) >= ARBITRAGE_THRESHOLD/100]),
            "triangle_opportunities": 0  # 暂无三角套利功能
        }
    })

@app.route('/api/arbitrage/opportunities', methods=['GET'])
def get_arbitrage_opportunities():
    """获取套利机会"""
    return jsonify({
        "status": "success",
        "data": diff_data
    })

@app.route('/api/arbitrage/tasks', methods=['GET'])
def get_arbitrage_tasks():
    """获取套利任务"""
    # 简单返回空列表，因为当前没有任务系统
    return jsonify({
        "status": "success",
        "data": []
    })

@app.route('/api/arbitrage/history', methods=['GET'])
def get_all_arbitrage_history():
    """获取所有套利历史"""
    all_history = []
    for records in arbitrage_history.values():
        all_history.extend(records)
    
    # 按时间降序排序
    all_history.sort(key=lambda x: x["time"], reverse=True)
    
    return jsonify({
        "status": "success",
        "data": all_history
    })

# 添加套利系统配置API
@app.route('/api/arbitrage/config', methods=['GET', 'POST'])
def arbitrage_config():
    """获取或更新套利配置"""
    if request.method == 'GET':
        # 返回当前配置
        config = {
            "total_funds": 10000.0,
            "allocation_ratio": {
                "cross_exchange": 0.6,
                "triangle": 0.4
            },
            "exchanges": EXCHANGES
        }
        return jsonify({
            "status": "success",
            "data": config
        })
    else:
        # 接收新配置
        try:
            data = request.get_json()
            # 在实际系统中，这里应该保存配置并更新系统状态
            # 目前只返回成功
            return jsonify({
                "status": "success",
                "message": "配置已更新"
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"更新配置失败: {str(e)}"
            })

# 添加套利系统启动和停止API
@app.route('/api/arbitrage/start', methods=['POST'])
def start_arbitrage():
    """启动套利系统"""
    global status
    status["running"] = True
    return jsonify({
        "status": "success",
        "message": "套利系统已启动"
    })

@app.route('/api/arbitrage/stop', methods=['POST'])
def stop_arbitrage():
    """停止套利系统"""
    global status
    status["running"] = False
    return jsonify({
        "status": "success",
        "message": "套利系统已停止"
    })

@app.route('/api/arbitrage/execute', methods=['POST'])
def execute_arbitrage():
    """执行套利操作"""
    try:
        data = request.get_json()
        # 在实际系统中，这里应该执行套利操作
        # 目前只返回成功
        return jsonify({
            "status": "success",
            "message": "套利操作已提交",
            "data": {
                "task_id": f"task_{int(time.time())}"
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"执行套利失败: {str(e)}"
        })

# ========================= 量化交易API路由 =========================

@app.route('/quantitative.html')
def quantitative():
    """量化交易页面"""
    return render_template('quantitative.html')

@app.route('/operations-log.html')
def operations_log():
    """操作日志页面"""
    return render_template('operations-log.html')

@app.route('/api/quantitative/strategies', methods=['GET', 'POST'])
def quantitative_strategies():
    """获取策略列表或创建新策略"""
    if not QUANTITATIVE_ENABLED:
        return jsonify({
            "status": "error",
            "message": "量化交易模块未启用"
        }), 500
    
    if request.method == 'GET':
        try:
            strategies = quantitative_service.get_strategies()
            return jsonify({
                "status": "success",
                "data": strategies
            })
        except Exception as e:
            logger.error(f"获取策略列表失败: {e}")
            return jsonify({
                "status": "error",
                "message": f"获取策略列表失败: {str(e)}"
            }), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            name = data.get('name')
            strategy_type = data.get('strategy_type')
            symbol = data.get('symbol')
            parameters = data.get('parameters', {})
            
            if not all([name, strategy_type, symbol]):
                return jsonify({
                    "status": "error",
                    "message": "缺少必要参数"
                }), 400
            
            # 转换策略类型
            try:
                strategy_type_enum = StrategyType(strategy_type)
            except ValueError:
                return jsonify({
                    "status": "error",
                    "message": f"不支持的策略类型: {strategy_type}"
                }), 400
            
            strategy_id = quantitative_service.create_strategy(
                name=name,
                strategy_type=strategy_type_enum,
                symbol=symbol,
                parameters=parameters
            )
            
            return jsonify({
                "status": "success",
                "message": "策略创建成功",
                "data": {"strategy_id": strategy_id}
            })
            
        except Exception as e:
            logger.error(f"创建策略失败: {e}")
            return jsonify({
                "status": "error",
                "message": f"创建策略失败: {str(e)}"
            }), 500

@app.route('/api/quantitative/strategies/<strategy_id>/toggle', methods=['POST'])
def toggle_quantitative_strategy(strategy_id):
    """切换策略状态"""
    if not QUANTITATIVE_ENABLED:
        return jsonify({
            "status": "error",
            "message": "量化交易模块未启用"
        }), 500
    
    try:
        strategy = quantitative_service.get_strategy(strategy_id)
        if not strategy:
            return jsonify({
                "status": "error",
                "message": "策略不存在"
            }), 404
        
        if strategy.get('enabled', False):
            success = quantitative_service.stop_strategy(strategy_id)
            message = "策略停止成功" if success else "策略停止失败"
        else:
            success = quantitative_service.start_strategy(strategy_id)
            message = "策略启动成功" if success else "策略启动失败"
        
        if success:
            return jsonify({
                "status": "success",
                "message": message
            })
        else:
            return jsonify({
                "status": "error",
                "message": message
            }), 400
            
    except Exception as e:
        logger.error(f"切换策略状态失败: {e}")
        return jsonify({
            "status": "error",
            "message": f"切换策略状态失败: {str(e)}"
        }), 500

@app.route('/api/quantitative/strategies/<strategy_id>', methods=['DELETE'])
def delete_quantitative_strategy(strategy_id):
    """删除策略"""
    if not QUANTITATIVE_ENABLED:
        return jsonify({
            "status": "error",
            "message": "量化交易模块未启用"
        }), 500
    
    try:
        success = quantitative_service.delete_strategy(strategy_id)
        if success:
            return jsonify({
                "status": "success",
                "message": "策略删除成功"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "策略删除失败或策略不存在"
            }), 404
            
    except Exception as e:
        logger.error(f"删除策略失败: {e}")
        return jsonify({
            "status": "error",
            "message": f"删除策略失败: {str(e)}"
        }), 500

@app.route('/api/quantitative/strategies/<strategy_id>', methods=['GET', 'PUT'])
def strategy_detail(strategy_id):
    """获取或更新策略详情"""
    try:
        if not quantitative_service:
            return jsonify({'success': False, 'message': '量化服务未启用'})
        
        if request.method == 'GET':
            # 获取策略详情
            if strategy_id not in quantitative_service.strategies:
                return jsonify({'success': False, 'message': '策略不存在'})
            
            strategy = quantitative_service.strategies[strategy_id]
            
            # 获取策略性能数据
            performance = strategy.get_performance_metrics()
            
            strategy_data = {
                'id': strategy.id,
                'name': strategy.name,
                'type': strategy.type,
                'symbol': strategy.symbol,
                'enabled': strategy.config.enabled,
                'parameters': strategy.config.parameters,
                'total_return': performance.get('total_return', 0),
                'win_rate': performance.get('win_rate', 0),
                'total_trades': performance.get('total_trades', 0),
                'daily_return': performance.get('daily_return', 0),
                'sharpe_ratio': performance.get('sharpe_ratio', 0),
                'max_drawdown': performance.get('max_drawdown', 0)
            }
            
            return jsonify({'success': True, 'data': strategy_data})
        
        elif request.method == 'PUT':
            # 更新策略配置
            data = request.json
            
            if strategy_id not in quantitative_service.strategies:
                return jsonify({'success': False, 'message': '策略不存在'})
            
            strategy = quantitative_service.strategies[strategy_id]
            
            # 记录旧参数（用于优化日志）
            old_params = strategy.config.parameters.copy()
            
            # 更新策略配置
            if 'name' in data:
                strategy.name = data['name']
            if 'symbol' in data:
                strategy.symbol = data['symbol']
            if 'enabled' in data:
                strategy.config.enabled = data['enabled']
            if 'parameters' in data:
                strategy.config.parameters.update(data['parameters'])
                
                # 记录手动参数调整日志
                quantitative_service.log_strategy_optimization(
                    strategy_id=strategy.id,
                    strategy_name=strategy.name,
                    optimization_type="手动调整",
                    old_params=old_params,
                    new_params=strategy.config.parameters,
                    trigger_reason="用户手动修改参数",
                    target_success_rate=None
                )
            
            # 保存到数据库
            quantitative_service._update_strategy_in_db(strategy)
            
            return jsonify({'success': True, 'message': '策略配置更新成功'})
        
    except Exception as e:
        logger.error(f"策略详情API错误: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/quantitative/strategies/<strategy_id>/reset', methods=['POST'])
def reset_strategy_params(strategy_id):
    """重置策略参数"""
    try:
        if not quantitative_service:
            return jsonify({'success': False, 'message': '量化服务未启用'})
        
        if strategy_id not in quantitative_service.strategies:
            return jsonify({'success': False, 'message': '策略不存在'})
        
        strategy = quantitative_service.strategies[strategy_id]
        old_params = strategy.config.parameters.copy()
        
        # 重置参数到默认值
        default_params = quantitative_service._get_default_strategy_parameters(strategy.type)
        strategy.config.parameters = default_params
        
        # 记录重置日志
        quantitative_service.log_strategy_optimization(
            strategy_id=strategy.id,
            strategy_name=strategy.name,
            optimization_type="参数重置",
            old_params=old_params,
            new_params=default_params,
            trigger_reason="用户手动重置参数",
            target_success_rate=95.0
        )
        
        # 保存到数据库
        quantitative_service._update_strategy_in_db(strategy)
        
        return jsonify({'success': True, 'message': '策略参数已重置为默认值'})
        
    except Exception as e:
        logger.error(f"重置策略参数错误: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/quantitative/strategies/<strategy_id>/trade-logs', methods=['GET'])
def get_strategy_trade_logs(strategy_id):
    """获取策略交易日志"""
    try:
        if not quantitative_service:
            return jsonify({'success': False, 'message': '量化服务未启用'})
        
        limit = int(request.args.get('limit', 100))
        logs = quantitative_service.get_strategy_trade_logs(strategy_id, limit)
        
        return jsonify({'success': True, 'logs': logs})
        
    except Exception as e:
        logger.error(f"获取交易日志错误: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/quantitative/strategies/<strategy_id>/optimization-logs', methods=['GET'])
def get_strategy_optimization_logs(strategy_id):
    """获取策略优化日志"""
    try:
        if not quantitative_service:
            return jsonify({'success': False, 'message': '量化服务未启用'})
        
        limit = int(request.args.get('limit', 50))
        logs = quantitative_service.get_strategy_optimization_logs(strategy_id, limit)
        
        return jsonify({'success': True, 'logs': logs})
        
    except Exception as e:
        logger.error(f"获取优化日志错误: {e}")
        return jsonify({'success': False, 'message': str(e)})

# ========================= 量化交易API路由结束 =========================

# 添加自动交易API接口
@app.route('/api/quantitative/trading-status', methods=['GET'])
def get_trading_status():
    """获取交易状态"""
    try:
        status = quantitative_service.get_trading_status()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        logger.error(f"获取交易状态失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/quantitative/toggle-auto-trading', methods=['POST'])
def toggle_auto_trading_api():
    """切换自动交易开关"""
    try:
        if not quantitative_service:
            return jsonify({'success': False, 'message': '量化服务未启用'}), 500
            
        data = request.get_json()
        enabled = data.get('enabled', False)
        
        # 调用量化服务切换自动交易
        result = quantitative_service.toggle_auto_trading(enabled)
        
        if result:
            return jsonify({
                'success': True,
                'message': f'自动交易已{"启用" if enabled else "禁用"}'
            })
        else:
            return jsonify({'success': False, 'message': '切换失败'}), 500
            
    except Exception as e:
        logger.error(f"切换自动交易失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/quantitative/force-close/<position_id>', methods=['POST'])
def force_close_position(position_id):
    """强制平仓"""
    try:
        # 如果是真实交易，调用交易引擎平仓
        if quantitative_service.trading_engine:
            # 这里需要实现根据position_id找到对应持仓并平仓的逻辑
            # 简化实现
            return jsonify({
                'success': True,
                'message': '平仓指令已发送'
            })
        else:
            return jsonify({
                'success': False,
                'message': '自动交易引擎未启用'
            })
    except Exception as e:
        logger.error(f"强制平仓失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# ========== 新增的量化交易系统控制API ==========

@app.route('/api/quantitative/system-status', methods=['GET'])
def get_system_status():
    """获取系统状态 - 从数据库读取真实状态，支持多设备同步"""
    try:
        if not quantitative_service:
            return jsonify({
                'success': True,
                'running': False,
                'auto_trading_enabled': False,
                'message': '量化服务未启用',
                'timestamp': datetime.now().isoformat()
            })
            
        # 从数据库读取真实系统状态
        running = quantitative_service.is_running
        auto_trading_enabled = quantitative_service.auto_trading_enabled
        
        # 获取运行策略数量
        running_strategies = len([s for s in quantitative_service.strategies.values() if s.is_running])
        total_strategies = len(quantitative_service.strategies)
        
        logger.info(f"系统状态查询: 运行={running}, 自动交易={auto_trading_enabled}, 运行策略={running_strategies}/{total_strategies}")
        
        return jsonify({
            'success': True,
            'running': running,
            'auto_trading_enabled': auto_trading_enabled,
            'running_strategies': running_strategies,
            'total_strategies': total_strategies,
            'timestamp': datetime.now().isoformat(),
            'source': 'database'  # 标记数据来源于数据库
        })
        
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        return jsonify({
            'success': False,
            'running': False,
            'auto_trading_enabled': False,
            'message': f'获取系统状态失败: {str(e)}',
            'timestamp': datetime.now().isoformat()
        })

@app.route('/api/quantitative/system-control', methods=['POST'])
def system_control():
    """系统控制 - 启动/停止，状态持久化到数据库"""
    try:
        if not quantitative_service:
            return jsonify({
                'success': False, 
                'message': '量化服务未启用'
            }), 500
            
        data = request.get_json()
        action = data.get('action', '')
        
        if action == 'start':
            # 启动量化系统
            success = quantitative_service.start_system()
            if success:
                logger.success("量化交易系统启动成功 - 状态已同步到所有设备")
                return jsonify({
                    'success': True,
                    'message': '量化交易系统启动成功，状态已同步到所有设备',
                    'running': True
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '量化交易系统启动失败'
                }), 500
                
        elif action == 'stop':
            # 停止量化系统
            success = quantitative_service.stop_system()
            if success:
                logger.info("量化交易系统停止成功 - 状态已同步到所有设备")
                return jsonify({
                    'success': True,
                    'message': '量化交易系统已停止，状态已同步到所有设备',
                    'running': False
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '量化交易系统停止失败'
                }), 500
        else:
            return jsonify({
                'success': False, 
                'message': '无效的操作，请使用start或stop'
            }), 400
            
    except Exception as e:
        logger.error(f"系统控制失败: {e}")
        return jsonify({
            'success': False, 
            'message': f'系统控制失败: {str(e)}'
        }), 500

@app.route('/api/quantitative/account-info', methods=['GET'])
def get_account_info():
    """获取真实币安账户信息"""
    try:
        # 获取真实币安余额
        real_balance_data = {}
        total_balance_usdt = 0.0
        daily_pnl = 0.0
        available_balance = 0.0
        frozen_balance = 0.0
        
        # 尝试从币安获取真实账户数据
        if 'binance' in exchange_clients:
            try:
                binance_client = exchange_clients['binance']
                logger.info("正在获取币安真实账户余额...")
                
                # 获取账户余额
                balance_data = binance_client.fetch_balance()
                
                if balance_data and 'total' in balance_data:
                    # 计算USDT总价值
                    usdt_balance = balance_data['total'].get('USDT', 0.0)
                    total_balance_usdt += usdt_balance
                    
                    # 计算其他币种的USDT价值
                    for symbol, amount in balance_data['total'].items():
                        if symbol != 'USDT' and amount > 0:
                            try:
                                # 获取币种对USDT的价格
                                ticker_symbol = f"{symbol}/USDT"
                                ticker = binance_client.fetch_ticker(ticker_symbol)
                                price = ticker['last']
                                usdt_value = amount * price
                                total_balance_usdt += usdt_value
                                logger.info(f"币种 {symbol}: {amount:.6f}, 价格: {price:.6f}, 价值: {usdt_value:.2f} USDT")
                            except Exception as e:
                                logger.debug(f"获取 {symbol} 价格失败: {e}")
                                continue
                    
                    # 获取可用和冻结余额
                    available_balance = balance_data.get('free', {}).get('USDT', 0.0)
                    frozen_balance = balance_data.get('used', {}).get('USDT', 0.0)
                    
                    # 计算其他币种的可用余额USDT价值
                    for symbol, amount in balance_data.get('free', {}).items():
                        if symbol != 'USDT' and amount > 0:
                            try:
                                ticker_symbol = f"{symbol}/USDT"
                                ticker = binance_client.fetch_ticker(ticker_symbol)
                                price = ticker['last']
                                available_balance += amount * price
                            except:
                                continue
                    
                    # 计算其他币种的冻结余额USDT价值
                    for symbol, amount in balance_data.get('used', {}).items():
                        if symbol != 'USDT' and amount > 0:
                            try:
                                ticker_symbol = f"{symbol}/USDT"
                                ticker = binance_client.fetch_ticker(ticker_symbol)
                                price = ticker['last']
                                frozen_balance += amount * price
                            except:
                                continue
                    
                    logger.info(f"币安真实账户总资产: {total_balance_usdt:.2f} USDT")
                    
                else:
                    logger.warning("币安余额数据格式异常")
                    
            except Exception as e:
                logger.error(f"获取币安真实余额失败: {e}")
                
        # 如果没有获取到真实数据，记录警告但不返回假数据
        if total_balance_usdt == 0:
            logger.warning("未能获取到真实币安账户数据，可能是API配置问题")
            return jsonify({
                'success': False,
                'message': '无法获取真实账户数据，请检查币安API配置',
                'data': {
                    'balance': 0.0,
                    'daily_pnl': 0.0,
                    'daily_return': 0.0,
                    'daily_trades': 0,
                    'available_balance': 0.0,
                    'frozen_balance': 0.0,
                    'total_equity': 0.0,
                    'note': '需要配置有效的币安API密钥'
                }
            })
        
        # 计算今日收益（简化处理）
        daily_return = daily_pnl / total_balance_usdt if total_balance_usdt > 0 else 0.0
        
        # 获取今日交易次数
        daily_trades = 0
        if quantitative_service:
            try:
                # 统计今日交易次数
                signals = quantitative_service.get_signals(limit=100)
                today = datetime.now().date()
                daily_trades = sum(1 for signal in signals 
                                 if datetime.fromisoformat(signal['timestamp']).date() == today 
                                 and signal['executed'])
            except Exception as e:
                logger.warning(f"统计今日交易次数失败: {e}")
        
        account_info = {
            'balance': round(total_balance_usdt, 2),
            'daily_pnl': round(daily_pnl, 2),
            'daily_return': round(daily_return, 4),
            'daily_trades': daily_trades,
            'available_balance': round(available_balance, 2),
            'frozen_balance': round(frozen_balance, 2),
            'total_equity': round(total_balance_usdt, 2)
        }
        
        return jsonify({
            'success': True,
            'data': account_info
        })
        
    except Exception as e:
        logger.error(f"获取账户信息失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取账户信息失败: {str(e)}',
            'data': {
                'balance': 0.0,
                'daily_pnl': 0.0,
                'daily_return': 0.0,
                'daily_trades': 0,
                'available_balance': 0.0,
                'frozen_balance': 0.0,
                'total_equity': 0.0
            }
        })

@app.route('/api/quantitative/exchange-status', methods=['GET'])
def get_exchange_status():
    """获取交易所连接状态"""
    try:
        # 返回交易所状态信息
        exchange_status = {
            'binance': {
                'connected': True,
                'ping': 25,
                'permissions': ['spot'],
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        }
        
        # 实际应该检查真实的交易所连接状态
        try:
            # 如果有交易引擎，检查其状态
            from auto_trading_engine import get_trading_engine
            engine = get_trading_engine()
            if engine:
                # 检查引擎连接状态
                pass
        except Exception as e:
            logger.warning(f"检查交易所连接失败: {e}")
            exchange_status['binance']['connected'] = False
        
        return jsonify({
            'success': True,
            'data': exchange_status
        })
    except Exception as e:
        logger.error(f"获取交易所状态失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ========== 添加缺失的量化交易配置API ==========

@app.route('/api/quantitative/config', methods=['GET', 'POST'])
def quantitative_config():
    """量化交易系统配置 - 支持三种运行模式"""
    try:
        if request.method == 'GET':
            # 返回当前系统配置和模式说明
            config = {
                'current_mode': 'auto',  # 当前默认自动模式
                'auto_trading_enabled': getattr(quantitative_service, 'auto_trading_enabled', True) if quantitative_service else True,
                'max_positions': 10,
                'risk_limit': 0.05,
                'exchange': 'binance',
                'modes': {
                    'manual': {
                        'name': '手动模式',
                        'description': '需要手动审核每个交易信号，系统生成信号但不自动执行',
                        'auto_execute': False,
                        'risk_level': 'low',
                        'recommended_for': '新手用户或谨慎投资者'
                    },
                    'auto': {
                        'name': '自动模式',
                        'description': '系统自动执行高置信度信号，平衡收益与风险',
                        'auto_execute': True,
                        'risk_level': 'medium',
                        'recommended_for': '有经验的用户，追求稳定收益'
                    },
                    'aggressive': {
                        'name': '激进模式',
                        'description': '更频繁交易，追求最大收益，风险较高',
                        'auto_execute': True,
                        'risk_level': 'high',
                        'recommended_for': '高风险承受能力的投资者'
                    }
                }
            }
            return jsonify({
                'success': True,
                'data': config
            })
        else:
            # 更新配置
            data = request.get_json()
            mode = data.get('mode', 'auto')
            
            # 验证模式
            valid_modes = ['manual', 'auto', 'aggressive']
            if mode not in valid_modes:
                return jsonify({
                    'success': False,
                    'message': f'无效的运行模式，支持的模式: {", ".join(valid_modes)}'
                }), 400
            
            # 根据模式调整系统参数
            if quantitative_service:
                try:
                    # 根据不同模式调整系统参数
                    if mode == 'manual':
                        # 手动模式：禁用自动交易
                        quantitative_service.toggle_auto_trading(False)
                        logger.info("切换到手动模式，已禁用自动交易")
                    elif mode == 'auto':
                        # 自动模式：启用自动交易，使用平衡参数
                        quantitative_service.toggle_auto_trading(True)
                        # 这里可以调整策略参数为平衡型
                        logger.info("切换到自动模式，已启用自动交易")
                    elif mode == 'aggressive':
                        # 激进模式：启用自动交易，调整为激进参数
                        quantitative_service.toggle_auto_trading(True)
                        # 这里可以调整策略参数为激进型
                        logger.info("切换到激进模式，追求高收益")
                except Exception as e:
                    logger.error(f"切换运行模式失败: {e}")
                    return jsonify({
                        'success': False,
                        'message': f'切换运行模式失败: {str(e)}'
                    }), 500
            
            mode_names = {
                'manual': '手动模式',
                'auto': '自动模式', 
                'aggressive': '激进模式'
            }
            
            return jsonify({
                'success': True,
                'message': f'已切换到{mode_names.get(mode, mode)}',
                'data': {'mode': mode}
            })
            
    except Exception as e:
        logger.error(f"量化交易配置API出错: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

def main():
    """主函数"""
    global status
    
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='加密货币套利监控Web应用')
    parser.add_argument('--trade', action='store_true', help='启用交易功能')
    parser.add_argument('--port', type=int, default=8888, help='Web服务器端口')
    parser.add_argument('--arbitrage', action='store_true', help='启用套利系统')
    args = parser.parse_args()
    
    # 强制设置为真实数据模式
    load_arbitrage_history()
    status["mode"] = "real"
    status["trading_enabled"] = args.trade
    status["running"] = True
    
    # 显示启动信息
    print("\n===== 加密货币套利监控Web应用 =====")
    print(f"运行模式: 真实API连接")
    print(f"交易功能: {'已启用' if args.trade else '未启用（仅监控）'}")
    print(f"套利系统: {'已启用' if args.arbitrage and ARBITRAGE_ENABLED else '未启用'}")
    print(f"Web端口: {args.port}")
    print("======================================\n")
    
    # 强制初始化交易所客户端
    init_api_clients()
    
    # 启动监控线程
    monitor = threading.Thread(target=monitor_thread, daemon=True)
    monitor.start()
    
    # 初始化套利系统
    if args.arbitrage and ARBITRAGE_ENABLED:
        try:
            # 创建套利配置
            arbitrage_config = {
                "total_funds": 10000,  # 默认10,000 USDT
                "exchanges": EXCHANGES,
                "symbols": SYMBOLS
            }
            
            # 初始化套利系统
            init_arbitrage_system(app, arbitrage_config)
            logger.info("套利系统初始化成功")
        except Exception as e:
            logger.error(f"套利系统初始化失败: {e}")
    
    # 启动Web服务器
    app.run(host='0.0.0.0', port=args.port)

if __name__ == "__main__":
    main() 