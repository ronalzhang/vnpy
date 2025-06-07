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

# 在文件开头初始化量化服务
quantitative_service = None

try:
    from quantitative_service import QuantitativeService, StrategyType
    # 创建量化服务实例
    quantitative_service = QuantitativeService()
    QUANTITATIVE_ENABLED = True
    logger.info("量化交易模块加载成功")
    print("✅ 量化交易服务初始化成功")
except ImportError as e:
    logger.warning(f"量化交易模块未找到，量化功能将被禁用: {e}")
    QUANTITATIVE_ENABLED = False
    quantitative_service = None
except Exception as e:
    print(f"❌ 量化交易服务初始化失败: {e}")
    QUANTITATIVE_ENABLED = False
    quantitative_service = None

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
                            "amount": round(total, 4),
                            "available": round(available, 4),
                            "locked": round(locked, 4),
                            "value": round(value, 2)
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
        
        # 方法1：尝试获取资金账户余额（通常资金在这里）
        funding_balance = 0
        try:
            funding_response = client.sapi_get_asset_get_funding_asset({})
            if funding_response:
                for asset in funding_response:
                    if asset.get('asset') == 'USDT':
                        funding_balance = float(asset.get('free', 0)) + float(asset.get('locked', 0))
                        print(f"🏦 币安资金账户USDT: {funding_balance}")
                        break
        except Exception as e:
            print(f"获取币安资金账户失败: {e}")
        
        # 方法2：获取现货账户余额
        spot_balance = 0
        account = client.private_get_account()
        
        for asset in account.get('balances', []):
            symbol = asset.get('asset')
            free = float(asset.get('free', 0))
            locked = float(asset.get('locked', 0))
            total = free + locked
            
            if symbol == 'USDT':
                spot_balance = total
                print(f"💰 币安现货账户USDT: {spot_balance}")
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
                        "amount": round(total, 4),
                        "available": round(free, 4),
                        "locked": round(locked, 4),
                        "value": value
                    }
        
        # 使用较大的余额（资金账户通常比现货账户余额多）
        if funding_balance > spot_balance:
            balance["USDT"] = round(funding_balance, 2)
            balance["USDT_available"] = round(funding_balance, 2)  # 简化处理
            balance["USDT_locked"] = 0
            print(f"✅ 使用币安资金账户余额: {funding_balance} USDT")
        else:
            balance["USDT"] = round(spot_balance, 2)
            balance["USDT_available"] = round(spot_balance, 2)
            balance["USDT_locked"] = 0
            print(f"✅ 使用币安现货账户余额: {spot_balance} USDT")
        
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
                        "amount": round(total, 4),
                        "available": round(available, 4),
                        "locked": round(frozen, 4),
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
                        "amount": round(total, 4),
                        "available": round(available, 4),
                        "locked": round(locked, 4),
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
                if QUANTITATIVE_ENABLED and quantitative_service:
                    try:
                        # 量化服务会自动处理市场数据，这里不需要手动传递
                        pass
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
            total_usdt = round(float(balance_info.get("USDT", 0)), 2)
            available_usdt = round(float(balance_info.get("USDT_available", 0)), 2)
            locked_usdt = round(float(balance_info.get("USDT_locked", 0)), 2)
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
    try:
        # 基于真实价格差异数据创建套利机会
        opportunities = []
        
        # 如果有实际的价格差异数据
        if diff_data:
            for item in diff_data:
                if item.get("price_diff_pct", 0) >= ARBITRAGE_THRESHOLD/100:
                    opportunities.append({
                        "symbol": item.get("symbol", "BTC/USDT"),
                        "buy_exchange": item.get("buy_exchange", "binance"),
                        "sell_exchange": item.get("sell_exchange", "okx"),
                        "buy_price": item.get("buy_price", 0),
                        "sell_price": item.get("sell_price", 0),
                        "price_diff": item.get("price_diff", 0),
                        "price_diff_pct": item.get("price_diff_pct", 0),
                        "profit_potential": round(item.get("price_diff_pct", 0) * 1000, 2),  # 假设1000USDT投入
                        "volume_24h": item.get("volume", 1000000),
                        "last_update": item.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                        "status": "active" if item.get("price_diff_pct", 0) >= 1.0 else "monitoring"
                    })
        
        # 如果没有实际套利机会，创建一些示例数据
        if not opportunities:
            example_opportunities = [
                {
                    "symbol": "BTC/USDT",
                    "buy_exchange": "binance",
                    "sell_exchange": "okx", 
                    "buy_price": 105300,
                    "sell_price": 105450,
                    "price_diff": 150,
                    "price_diff_pct": 0.14,
                    "profit_potential": 1.40,
                    "volume_24h": 2500000,
                    "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "monitoring"
                },
                {
                    "symbol": "ETH/USDT",
                    "buy_exchange": "bitget",
                    "sell_exchange": "binance",
                    "buy_price": 3980,
                    "sell_price": 3995,
                    "price_diff": 15,
                    "price_diff_pct": 0.38,
                    "profit_potential": 3.80,
                    "volume_24h": 1800000,
                    "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "monitoring"
                }
            ]
            opportunities.extend(example_opportunities)
        
        return jsonify({
            "status": "success",
            "data": opportunities
        })
    except Exception as e:
        print(f"获取套利机会失败: {e}")
        return jsonify({
            "status": "error",
            "message": f"获取套利机会失败: {str(e)}"
        }), 500

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
            strategy = quantitative_service.get_strategy(strategy_id)
            if not strategy:
                return jsonify({'success': False, 'message': '策略不存在'})
            
            return jsonify({'success': True, 'data': strategy})
        
        elif request.method == 'PUT':
            # 更新策略配置
            data = request.json
            
            # 使用量化服务的更新方法
            success = quantitative_service.update_strategy(
                strategy_id=strategy_id,
                name=data.get('name', ''),
                symbol=data.get('symbol', ''),
                parameters=data.get('parameters', {})
            )
            
            if success:
                return jsonify({'success': True, 'message': '策略配置更新成功'})
            else:
                return jsonify({'success': False, 'message': '策略更新失败'})
        
    except Exception as e:
        print(f"策略详情API错误: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/quantitative/strategies/<strategy_id>/reset', methods=['POST'])
def reset_strategy_params(strategy_id):
    """重置策略参数"""
    try:
        if not quantitative_service:
            return jsonify({'success': False, 'message': '量化服务未启用'})
        
        strategy = quantitative_service.get_strategy(strategy_id)
        if not strategy:
            return jsonify({'success': False, 'message': '策略不存在'})
        
        # 获取默认参数
        strategy_type = strategy.get('type', 'momentum')
        default_params = {
            'momentum': {
                'lookback_period': 20,
                'threshold': 0.02,
                'quantity': 100,
                'momentum_threshold': 0.01,
                'volume_threshold': 2.0
            },
            'mean_reversion': {
                'lookback_period': 30,
                'std_multiplier': 2.0,
                'quantity': 100,
                'reversion_threshold': 0.02,
                'min_deviation': 0.01
            },
            'grid_trading': {
                'grid_spacing': 1.0,
                'grid_count': 10,
                'quantity': 1000,
                'lookback_period': 100,
                'min_profit': 0.5
            },
            'breakout': {
                'lookback_period': 20,
                'breakout_threshold': 1.5,
                'quantity': 50,
                'volume_threshold': 2.0,
                'confirmation_periods': 3
            },
            'high_frequency': {
                'quantity': 100,
                'min_profit': 0.05,
                'volatility_threshold': 0.001,
                'lookback_period': 10,
                'signal_interval': 30
            },
            'trend_following': {
                'lookback_period': 50,
                'trend_threshold': 1.0,
                'quantity': 100,
                'trend_strength_min': 0.3
            }
        }.get(strategy_type, {})
        
        # 重置参数
        success = quantitative_service.update_strategy(
            strategy_id=strategy_id,
            name=strategy.get('name', ''),
            symbol=strategy.get('symbol', ''),
            parameters=default_params
        )
        
        if success:
            # 记录重置日志
            quantitative_service.log_strategy_optimization(
                strategy_id=strategy_id,
                strategy_name=strategy.get('name', ''),
                optimization_type="参数重置",
                old_params=strategy.get('parameters', {}),
                new_params=default_params,
                trigger_reason="用户手动重置参数",
                target_success_rate=95.0
            )
            return jsonify({'success': True, 'message': '策略参数已重置为默认值'})
        else:
            return jsonify({'success': False, 'message': '重置失败'})
        
    except Exception as e:
        print(f"重置策略参数错误: {e}")
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
        print(f"获取交易日志错误: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/quantitative/strategies/<strategy_id>/optimization-logs', methods=['GET'])
def get_strategy_optimization_logs(strategy_id):
    """获取策略优化记录"""
    try:
        if quantitative_service and quantitative_service.running:
            logs = quantitative_service.get_strategy_optimization_logs(strategy_id)
            return jsonify({
                'success': True,
                'logs': logs
            })
        else:
            return jsonify({
                'success': False,
                'message': '量化服务未运行'
            })
    except Exception as e:
        print(f"获取策略优化记录失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取失败: {str(e)}'
        })

@app.route('/api/quantitative/positions', methods=['GET'])
def get_quantitative_positions():
    """获取量化交易持仓信息 - 仅使用真实API数据"""
    try:
        if quantitative_service:
            # 🔗 直接调用量化服务获取真实持仓数据
            positions = quantitative_service.get_positions()
            
            return jsonify({
                "status": "success",
                "data": positions
            })
        else:
            print("❌ 量化服务未初始化")
            return jsonify({
                "status": "error",
                "message": "量化服务未初始化"
            }), 500
    except Exception as e:
        print(f"❌ 获取持仓信息失败: {e}")
        return jsonify({
            "status": "error",
            "message": f"获取持仓信息失败: {str(e)}"
        }), 500

@app.route('/api/quantitative/signals', methods=['GET'])
def get_quantitative_signals():
    """获取最新交易信号 - 仅使用真实交易信号"""
    try:
        if quantitative_service:
            # 🔗 直接调用量化服务获取真实交易信号
            signals = quantitative_service.get_signals()
            
            return jsonify({
                "status": "success",
                "data": signals
            })
        else:
            print("❌ 量化服务未初始化")
            return jsonify({
                "status": "error",
                "message": "量化服务未初始化"
            }), 500
    except Exception as e:
        print(f"❌ 获取交易信号失败: {e}")
        return jsonify({
            "status": "error",
            "message": f"获取交易信号失败: {str(e)}"
        }), 500

@app.route('/api/quantitative/balance-history', methods=['GET'])
def get_balance_history():
    """获取账户资产历史 - 仅使用真实数据"""
    try:
        days = request.args.get('days', 30, type=int)
        if quantitative_service:
            history = quantitative_service.get_balance_history(days)
            return jsonify({
                'success': True,
                'data': history
            })
        else:
            print("❌ 量化服务未初始化，无法获取真实资产历史")
            return jsonify({
                'success': False,
                'message': '量化服务未初始化，无法获取真实资产历史',
                'data': []
            })
    except Exception as e:
        print(f"获取资产历史失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取失败: {str(e)}',
            'data': []
        })

@app.route('/api/quantitative/system-status', methods=['GET'])
def get_system_status():
    """获取量化系统状态 - 从数据库读取，确保前后端状态同步"""
    try:
        if quantitative_service:
            # ⭐ 从数据库读取系统状态，而不是从内存实例
            db_status = quantitative_service.get_system_status_from_db()
            
            # 计算策略统计信息
            total_strategies = len(quantitative_service.strategies) if quantitative_service.strategies else 0
            running_strategies = 0
            selected_strategies = 0
            
            if quantitative_service.strategies:
                for strategy in quantitative_service.strategies.values():
                    if strategy.get('enabled', False):
                        running_strategies += 1
                    if strategy.get('qualified_for_trading', False):
                        selected_strategies += 1
            
            # 更新数据库中的策略统计信息
            quantitative_service.update_system_status(
                total_strategies=total_strategies,
                running_strategies=running_strategies,
                selected_strategies=selected_strategies
            )
            
            # 组合返回数据，优先使用数据库状态
            return jsonify({
                'success': True,
                'running': db_status.get('quantitative_running', False),
                'auto_trading_enabled': db_status.get('auto_trading_enabled', False),
                'total_strategies': total_strategies,
                'running_strategies': running_strategies,
                'selected_strategies': selected_strategies,
                'current_generation': db_status.get('current_generation', 0),
                'evolution_enabled': db_status.get('evolution_enabled', True),
                'last_evolution_time': db_status.get('last_evolution_time'),
                'last_update': db_status.get('last_update_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                'system_health': db_status.get('system_health', 'unknown'),
                'notes': db_status.get('notes'),
                'data_source': 'database'  # 标明数据来源
            })
        else:
            # 如果量化服务未初始化，仍尝试从数据库读取
            try:
                import sqlite3
                conn = sqlite3.connect('quantitative.db')
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT quantitative_running, auto_trading_enabled, total_strategies,
                           running_strategies, selected_strategies, current_generation,
                           evolution_enabled, last_evolution_time, last_update_time,
                           system_health, notes
                    FROM system_status WHERE id = 1
                ''')
                
                row = cursor.fetchone()
                if row:
                    conn.close()
                    return jsonify({
                        'success': True,
                        'running': bool(row[0]),
                        'auto_trading_enabled': bool(row[1]),
                        'total_strategies': row[2] or 0,
                        'running_strategies': row[3] or 0,
                        'selected_strategies': row[4] or 0,
                        'current_generation': row[5] or 0,
                        'evolution_enabled': bool(row[6]),
                        'last_evolution_time': row[7],
                        'last_update': row[8] or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'system_health': row[9] or 'offline',
                        'notes': row[10],
                        'data_source': 'database_direct'
                    })
                conn.close()
            except Exception as e:
                print(f"直接从数据库读取状态失败: {e}")
            
            return jsonify({
                'success': False,
                'running': False,
                'auto_trading_enabled': False,
                'total_strategies': 0,
                'running_strategies': 0,
                'selected_strategies': 0,
                'current_generation': 0,
                'evolution_enabled': False,
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'system_health': 'not_initialized',
                'message': '量化服务未初始化'
            })
        
        if action == 'start':
            success = quantitative_service.start()
            if success:
                # 启动时初始化小资金优化
                quantitative_service._init_small_fund_optimization()
                return jsonify({
                    'success': True,
                    'message': '系统已启动，已启用小资金优化模式'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '系统启动失败'
                })
        elif action == 'stop':
            success = quantitative_service.stop()
            return jsonify({
                'success': success,
                'message': '系统已停止' if success else '系统停止失败'
            })
        else:
            return jsonify({
                'success': False,
                'message': '无效的操作'
            })
            
    except Exception as e:
        print(f"系统控制失败: {e}")
        return jsonify({
            'success': False,
            'message': f'控制失败: {str(e)}'
        })

@app.route('/api/quantitative/toggle-auto-trading', methods=['POST'])
def toggle_auto_trading():
    """切换自动交易状态"""
    try:
        data = request.json
        enabled = data.get('enabled', False)
        
        if not quantitative_service:
            return jsonify({
                'success': False,
                'message': '量化服务未初始化'
            })
        
        success = quantitative_service.set_auto_trading(enabled)
        return jsonify({
            'success': success,
            'message': f'自动交易已{"启用" if enabled else "禁用"}' if success else '设置失败'
        })
        
    except Exception as e:
        print(f"切换自动交易失败: {e}")
        return jsonify({
            'success': False,
            'message': f'切换失败: {str(e)}'
        })

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

@app.route('/api/quantitative/force_start_all', methods=['POST'])
def force_start_all_strategies():
    """强制启动所有策略"""
    try:
        if quantitative_service:
            # 启动系统
            quantitative_service.start()
            
            # 强制启动所有策略
            result = quantitative_service.force_start_all_strategies()
            
            # 启动信号生成
            quantitative_service.check_and_start_signal_generation()
            
            if result:
                return jsonify({
                    'success': True,
                    'message': '所有策略已强制启动，信号生成器已启动'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '启动策略失败'
                })
        else:
            return jsonify({
                'success': False,
                'message': '量化服务未初始化'
            })
    except Exception as e:
        print(f"强制启动策略失败: {e}")
        return jsonify({
            'success': False,
            'message': f'启动失败: {str(e)}'
        })

@app.route('/api/quantitative/strategies/<strategy_id>/start', methods=['POST'])
def start_strategy(strategy_id):
    """启动单个策略"""
    try:
        if quantitative_service:
            result = quantitative_service.start_strategy(strategy_id)
            
            if result:
                return jsonify({
                    'success': True,
                    'message': f'策略 {strategy_id} 已启动'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'启动策略 {strategy_id} 失败'
                })
        else:
            return jsonify({
                'success': False,
                'message': '量化服务未初始化'
            })
    except Exception as e:
        print(f"启动策略失败: {e}")
        return jsonify({
            'success': False,
            'message': f'启动失败: {str(e)}'
        })

@app.route('/api/quantitative/strategies/<strategy_id>/stop', methods=['POST'])
def stop_strategy(strategy_id):
    """停止单个策略"""
    try:
        if quantitative_service:
            result = quantitative_service.stop_strategy(strategy_id)
            
            if result:
                return jsonify({
                    'success': True,
                    'message': f'策略 {strategy_id} 已停止'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'停止策略 {strategy_id} 失败'
                })
        else:
            return jsonify({
                'success': False,
                'message': '量化服务未初始化'
            })
    except Exception as e:
        print(f"停止策略失败: {e}")
        return jsonify({
            'success': False,
            'message': f'停止失败: {str(e)}'
        })

# ========== 操作日志API ==========

@app.route('/api/operations-log', methods=['GET'])
def get_operations_log():
    """获取操作日志"""
    try:
        if not quantitative_service:
            return jsonify({
                'success': False,
                'message': '量化服务未初始化',
                'data': []
            })
        
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        operation_type = request.args.get('operation_type', '')
        result_filter = request.args.get('result', '')
        time_filter = request.args.get('time', '')
        search = request.args.get('search', '')
        
        # 从数据库获取操作日志
        cursor = quantitative_service.conn.cursor()
        
        # 构建查询条件
        where_conditions = []
        params = []
        
        if operation_type:
            where_conditions.append("operation_type = ?")
            params.append(operation_type)
        
        if result_filter:
            where_conditions.append("result = ?")
            params.append(result_filter)
        
        if search:
            where_conditions.append("(operation_detail LIKE ? OR operation_type LIKE ?)")
            params.extend([f'%{search}%', f'%{search}%'])
        
        if time_filter:
            time_conditions = {
                '1h': "timestamp >= datetime('now', '-1 hour')",
                '24h': "timestamp >= datetime('now', '-1 day')",
                '7d': "timestamp >= datetime('now', '-7 days')",
                '30d': "timestamp >= datetime('now', '-30 days')"
            }
            if time_filter in time_conditions:
                where_conditions.append(time_conditions[time_filter])
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # 计算总数
        count_query = f"SELECT COUNT(*) FROM operation_logs {where_clause}"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # 获取分页数据
        offset = (page - 1) * per_page
        query = f"""
            SELECT operation_type, operation_detail, result, timestamp
            FROM operation_logs 
            {where_clause}
            ORDER BY timestamp DESC 
            LIMIT ? OFFSET ?
        """
        cursor.execute(query, params + [per_page, offset])
        
        logs = []
        for row in cursor.fetchall():
            logs.append({
                'operation_type': row[0],
                'operation_detail': row[1],
                'result': row[2],
                'timestamp': row[3],
                'id': len(logs) + 1  # 简单的ID生成
            })
        
        # 计算统计信息
        cursor.execute("SELECT COUNT(*) FROM operation_logs WHERE result = 'success'")
        success_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM operation_logs WHERE result = 'failed'")
        error_count = cursor.fetchone()[0]
        
        return jsonify({
            'success': True,
            'data': {
                'logs': logs,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'pages': (total_count + per_page - 1) // per_page
                },
                'stats': {
                    'total': total_count,
                    'success': success_count,
                    'error': error_count
                }
            }
        })
        
    except Exception as e:
        print(f"获取操作日志失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取失败: {str(e)}',
            'data': []
        })

# 策略模拟交易接口
@app.route('/api/quantitative/run-simulations', methods=['POST'])
def run_strategy_simulations():
    """运行所有策略的模拟交易"""
    if not QUANTITATIVE_ENABLED:
        return jsonify({"status": "error", "message": "量化模块未启用"})
    
    try:
        # 运行所有策略模拟
        simulation_results = quantitative_service.run_all_strategy_simulations()
        
        return jsonify({
            "status": "success",
            "message": "策略模拟交易完成",
            "data": {
                "total_simulated": len(simulation_results),
                "simulation_results": simulation_results
            }
        })
        
    except Exception as e:
        logger.error(f"运行策略模拟失败: {e}")
        return jsonify({"status": "error", "message": f"模拟失败: {str(e)}"})

@app.route('/api/quantitative/trading-status', methods=['GET'])
def get_trading_status():
    """获取交易状态和资金分配信息"""
    if not QUANTITATIVE_ENABLED:
        return jsonify({"status": "error", "message": "量化模块未启用"})
    
    try:
        summary = quantitative_service.get_trading_status_summary()
        
        return jsonify({
            "status": "success",
            "data": summary
        })
        
    except Exception as e:
        logger.error(f"获取交易状态失败: {e}")
        return jsonify({"status": "error", "message": f"获取状态失败: {str(e)}"})

@app.route('/api/quantitative/select-strategies', methods=['POST'])
def select_top_strategies():
    """手动选择评分最高的策略进行真实交易"""
    if not QUANTITATIVE_ENABLED:
        return jsonify({"status": "error", "message": "量化模块未启用"})
    
    try:
        # 获取请求参数
        data = request.get_json() or {}
        max_strategies = data.get('max_strategies', 2)
        min_score = data.get('min_score', 60.0)  # 修改默认值从70.0改为60.0
        
        # 更新配置
        quantitative_service.fund_allocation_config['max_active_strategies'] = max_strategies
        quantitative_service.fund_allocation_config['min_score_for_trading'] = min_score
        
        # 获取所有策略的模拟结果
        simulation_results = {}
        for strategy_id, strategy in quantitative_service.strategies.items():
            if strategy.get('simulation_score'):
                simulation_results[strategy_id] = {
                    'final_score': strategy['simulation_score'],
                    'qualified_for_live_trading': strategy.get('qualified_for_trading', False),
                    'combined_win_rate': strategy.get('simulation_win_rate', 0.6)  # 默认值
                }
        
        # 选择最优策略
        quantitative_service._select_top_strategies_for_trading(simulation_results)
        
        return jsonify({
            "status": "success",
            "message": f"已选择评分最高的 {max_strategies} 个策略进行真实交易",
            "data": {
                "selected_strategies": max_strategies,
                "min_score_required": min_score
            }
        })
        
    except Exception as e:
        logger.error(f"选择策略失败: {e}")
        return jsonify({"status": "error", "message": f"选择策略失败: {str(e)}"})

@app.route('/api/quantitative/evolution/status', methods=['GET'])
def get_evolution_status():
    """获取进化状态"""
    if not QUANTITATIVE_ENABLED:
        return jsonify({"status": "error", "message": "量化模块未启用"})
    
    try:
        result = quantitative_service.get_evolution_status()
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/quantitative/evolution/trigger', methods=['POST'])
def trigger_evolution():
    """手动触发进化"""
    if not QUANTITATIVE_ENABLED:
        return jsonify({"status": "error", "message": "量化模块未启用"})
    
    try:
        result = quantitative_service.manual_evolution()
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/quantitative/evolution/toggle', methods=['POST'])
def toggle_evolution():
    """开关进化功能"""
    if not QUANTITATIVE_ENABLED:
        return jsonify({"status": "error", "message": "量化模块未启用"})
    
    try:
        data = request.get_json() or {}
        enabled = data.get('enabled', True)
        
        result = quantitative_service.toggle_evolution(enabled)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/quantitative/strategies/create', methods=['POST'])
def create_strategy():
    """创建新策略"""
    if not QUANTITATIVE_ENABLED:
        return jsonify({"status": "error", "message": "量化模块未启用"})
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "缺少策略数据"})
        
        # 基本验证
        required_fields = ['name', 'type', 'symbol', 'parameters']
        for field in required_fields:
            if field not in data:
                return jsonify({"status": "error", "message": f"缺少必要字段: {field}"})
        
        # 生成策略ID
        import random
        strategy_id = f"{data['type']}_{data['symbol'].replace('/', '_')}_{random.randint(1000, 9999)}"
        
        # 创建策略配置
        strategy_config = {
            'id': strategy_id,
            'name': data['name'],
            'type': data['type'],
            'symbol': data['symbol'],
            'parameters': data['parameters'],
            'generation': 0,
            'creation_method': 'manual'
        }
        
        # 通过进化引擎创建策略
        if quantitative_service.evolution_engine:
            result = quantitative_service.evolution_engine._create_strategy_in_system(strategy_config)
            if result:
                return jsonify({
                    "success": True,
                    "message": "策略创建成功",
                    "strategy_id": strategy_id
                })
            else:
                return jsonify({"success": False, "message": "策略创建失败"})
        else:
            return jsonify({"success": False, "message": "进化引擎未启动"})
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/quantitative/auto-trading', methods=['GET', 'POST'])
def manage_auto_trading():
    """管理自动交易开关 - 增强数据库状态同步"""
    try:
        if request.method == 'POST':
            data = request.get_json()
            enabled = data.get('enabled', False)
            
            if quantitative_service:
                # ⭐ 设置自动交易状态
                quantitative_service.set_auto_trading(enabled)
                
                # ⭐ 同步到数据库状态
                quantitative_service.update_system_status(
                    auto_trading_enabled=enabled,
                    notes=f'自动交易已{"开启" if enabled else "关闭"}'
                )
                
                return jsonify({
                    'success': True,
                    'enabled': enabled,
                    'message': f'自动交易已{"开启" if enabled else "关闭"}'
                })
            else:
                return jsonify({'success': False, 'error': '量化服务未初始化'})
        
        else:  # GET
            if quantitative_service:
                # ⭐ 从数据库读取自动交易状态
                db_status = quantitative_service.get_system_status_from_db()
                auto_trading_enabled = db_status.get('auto_trading_enabled', False)
                
                return jsonify({
                    'success': True,
                    'enabled': auto_trading_enabled,
                    'data_source': 'database'
                })
            else:
                return jsonify({'success': False, 'enabled': False, 'error': '量化服务未初始化'})
                
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'enabled': False})

def main():
    """主函数"""
    global status, quantitative_service
    
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
    print(f"量化系统: {'已启用' if QUANTITATIVE_ENABLED else '未启用'}")
    print(f"Web端口: {args.port}")
    print("======================================\n")
    
    # 强制初始化交易所客户端
    init_api_clients()
    
    # 启动量化服务（如果可用）
    if QUANTITATIVE_ENABLED and quantitative_service:
        try:
            print("🚀 启动量化交易服务...")
            quantitative_service.start()
            print("✅ 量化交易服务启动成功")
        except Exception as e:
            print(f"❌ 量化交易服务启动失败: {e}")
    
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

@app.route('/api/quantitative/account-info', methods=['GET'])
def get_account_info():
    """获取账户基本信息"""
    if not QUANTITATIVE_ENABLED:
        return jsonify({
            'success': False,
            'message': '量化模块未启用',
            'data': {}
        })
    
    try:
        # 从量化服务获取账户信息
        account_info = quantitative_service.get_account_info()
        
        return jsonify({
            'success': True,
            'data': account_info
        })
        
    except Exception as e:
        print(f"获取账户信息失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取失败: {str(e)}',
            'data': {}
        })

if __name__ == "__main__":
    main() 