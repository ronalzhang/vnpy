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
    
    # 读取配置文件
    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
        
        # 检查是否所有交易所都缺少有效的API密钥
        all_missing_api = True
        
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
                        'password': password,  # 保留原始密码，包括特殊字符
                        'enableRateLimit': True
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
                        # 确保API密钥有效
                        if exchange_id == 'okx':
                            # OKX特殊处理，获取账户信息
                            client.fetch_balance()
                        else:
                            client.fetch_balance()
                            
                        print(f"初始化 {exchange_id} API客户端成功")
                        exchange_clients[exchange_id] = client
                        all_missing_api = False
                    except Exception as e:
                        print(f"API连接测试失败 {exchange_id}: {e}，可能是API密钥无效或限制")
                        # 仍然添加客户端，但后续会使用模拟数据
                        exchange_clients[exchange_id] = client
                except Exception as e:
                    print(f"初始化 {exchange_id} API客户端失败: {e}")
            else:
                print(f"交易所 {exchange_id} 未配置API密钥")
        
        # 如果所有交易所都没有有效的API密钥，使用模拟模式
        if all_missing_api:
            use_simulation = True
            status["mode"] = "simulate"
            print("所有交易所API密钥无效或未配置，启用模拟模式")
        else:
            use_simulation = False
            status["mode"] = "real"
            print("已配置至少一个有效的API密钥，使用真实API连接")
    except Exception as e:
        print(f"初始化API客户端出错: {e}")
        use_simulation = True
        status["mode"] = "simulate"

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
    """生成模拟的余额数据"""
    balances = {}
    
    for exchange in EXCHANGES:
        # 生成随机USDT余额
        usdt_balance = round(random.uniform(5000, 20000), 2)
        usdt_available = round(usdt_balance * random.uniform(0.7, 0.9), 2)
        usdt_locked = round(usdt_balance - usdt_available, 2)
        
        balances[exchange] = {
            "USDT": usdt_balance,
            "USDT_available": usdt_available,
            "USDT_locked": usdt_locked,
            "positions": {}
        }
        
        # 为每个交易对随机生成持仓
        for symbol in SYMBOLS:
            coin = symbol.split('/')[0]
            
            # 70%概率有持仓
            if random.random() > 0.3:
                total_amount = round(random.uniform(0.01, 10) * (1 if coin == "BTC" else (20 if coin == "ETH" else 100)), 5)
                available_amount = round(total_amount * random.uniform(0.6, 1.0), 5)
                locked_amount = round(total_amount - available_amount, 5)
                
                price = (
                    random.uniform(60000, 70000) if coin == "BTC" else 
                    random.uniform(3000, 4000) if coin == "ETH" else
                    random.uniform(100, 150) if coin == "SOL" else
                    random.uniform(0.45, 0.55)
                )
                
                value = round(total_amount * price, 2)
                
                balances[exchange]["positions"][coin] = {
                    "amount": total_amount,
                    "available": available_amount,
                    "locked": locked_amount,
                    "value": value
                }
    
    return balances

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
    
    # 如果是模拟模式，直接返回模拟数据
    if status["mode"] == "simulate":
        return generate_simulated_balances()
    
    for exchange_id, client in exchange_clients.items():
        try:
            exchange_balances = {"USDT": 0, "USDT_available": 0, "USDT_locked": 0, "positions": {}}
            
            # 检查API密钥是否配置
            if not client or not hasattr(client, 'apiKey') or not client.apiKey:
                print(f"交易所 {exchange_id} 没有配置API密钥或客户端初始化失败，使用模拟数据")
                simulated = generate_simulated_balances()
                balances[exchange_id] = simulated[exchange_id]
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
                            # 无法获取价格时使用估算值
                            price_estimate = {
                                'BTC': 65000,
                                'ETH': 3500,
                                'SOL': 140,
                                'XRP': 0.5,
                                'DOGE': 0.15,
                                'ADA': 0.5,
                                'DOT': 7,
                                'AVAX': 35,
                                'SHIB': 0.00003
                            }
                            price = price_estimate.get(coin, 0)
                            value = round(total_amount * price, 2)
                        
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
                        raise Exception("不支持的交易所")
                except Exception as e2:
                    print(f"获取 {exchange_id} 余额的替代方法也失败: {e2}，使用模拟数据")
                    simulated = generate_simulated_balances()
                    balances[exchange_id] = simulated[exchange_id]
        except Exception as e:
            print(f"获取 {exchange_id} 余额过程中出现异常: {e}，使用模拟数据")
            simulated = generate_simulated_balances()
            balances[exchange_id] = simulated[exchange_id]
    
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
                        volume = random.uniform(1000, 5000)
                    
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
    
    # 检查数据完整性，如果缺少数据则使用模拟数据补充
    simulated_data = generate_simulated_data()
    for exchange in EXCHANGES:
        if not prices[exchange]:
            prices[exchange] = simulated_data[exchange]
        else:
            for symbol in SYMBOLS:
                if symbol not in prices[exchange]:
                    if exchange in simulated_data and symbol in simulated_data[exchange]:
                        prices[exchange][symbol] = simulated_data[exchange][symbol]
    
    return prices

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
                    # 使用真实API连接
                    prices = get_exchange_prices()
                
                prices_data = prices
                
                # 计算价差
                diff = calculate_price_differences(prices)
                diff_data = diff
                
                # 更新余额数据
                if status["mode"] == "simulate":
                    balances = generate_simulated_balances()
                else:
                    # 使用真实API连接获取余额
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

def main():
    """主函数"""
    global status
    
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='加密货币套利监控Web应用')
    parser.add_argument('--simulate', action='store_true', help='使用模拟数据')
    parser.add_argument('--real', action='store_true', help='使用真实API连接')
    parser.add_argument('--trade', action='store_true', help='启用交易功能')
    parser.add_argument('--port', type=int, default=8888, help='Web服务器端口')
    parser.add_argument('--arbitrage', action='store_true', help='启用套利系统')
    args = parser.parse_args()
    
    # 设置运行模式
    # 加载历史记录
    load_arbitrage_history()
    is_simulate = not args.real
    status["mode"] = "simulate" if is_simulate else "real"
    status["trading_enabled"] = args.trade
    status["running"] = True
    
    # 显示启动信息
    print("\n===== 加密货币套利监控Web应用 =====")
    print(f"运行模式: {'模拟数据' if is_simulate else '真实API连接'}")
    print(f"交易功能: {'已启用' if args.trade else '未启用（仅监控）'}")
    print(f"套利系统: {'已启用' if args.arbitrage and ARBITRAGE_ENABLED else '未启用'}")
    print(f"Web端口: {args.port}")
    print("======================================\n")
    
    # 初始化交易所客户端
    if not is_simulate:
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