#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
加密货币套利引擎
"""

import os
import json
import time
import ccxt
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread
from typing import Dict, List, Set, Any, Optional
import logging

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine
from vnpy.trader.event import EVENT_TIMER
from vnpy.trader.utility import load_json, save_json
from .utility import LogData

# 常量定义
APP_NAME = "CryptoArbitrage"

# 事件定义
EVENT_CRYPTO_LOG = "eCryptoLog"
EVENT_CRYPTO_PRICE = "eCryptoPrice"
EVENT_CRYPTO_DIFF = "eCryptoDiff"
EVENT_CRYPTO_TRADE = "eCryptoTrade"
EVENT_CRYPTO_BALANCE = "eCryptoBalance"

# 套利参数
ARBITRAGE_THRESHOLD = 0.005  # 开始套利的差价阈值（0.5%）
CLOSE_THRESHOLD = 0.002      # 平仓差价阈值（0.2%）
TRADE_AMOUNT = {             # 每个交易对的交易数量
    "BTC/USDT": 0.001,        # 比特币
    "ETH/USDT": 0.01,         # 以太坊
    "BNB/USDT": 0.1,         # 币安币
    "SOL/USDT": 0.1,           # 索拉纳
    "XRP/USDT": 100,         # 瑞波币
    "ADA/USDT": 100,         # 艾达币
    "DOGE/USDT": 1000,       # 狗狗币
    "DOT/USDT": 10,          # 波卡
    "AVAX/USDT": 5,          # 雪崩
    "MATIC/USDT": 100,       # Polygon
    "LINK/USDT": 10,         # 链接
    "UNI/USDT": 10,          # Uniswap
    "SHIB/USDT": 1000000,    # 柴犬币
    "LTC/USDT": 1,           # 莱特币
    "ATOM/USDT": 5,          # Cosmos
    "TRX/USDT": 1000         # 波场
}

# 交易所资金要求（USDT）
MIN_BALANCE_REQUIRED = 50  # 每个交易所至少需要这些USDT作为余额

# 默认更新间隔（秒）
UPDATE_INTERVAL = 5

# 默认交易对
DEFAULT_SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", 
    "XRP/USDT", "ADA/USDT", "DOGE/USDT", "DOT/USDT"
]

class CryptoArbitrageEngine:
    """加密货币套利引擎"""
    
    def __init__(self, event_engine: EventEngine = None):
        """构造函数"""
        self.event_engine = event_engine or EventEngine()
        self.exchanges = {}
        self.settings = {}
        self.verbosity = 1
        self.verbose_logging = False
        self.update_interval = UPDATE_INTERVAL
        self.enable_trading = False
        self.price_diff_data = {}
        self.last_update_time = None
        self.monitor_thread = None
        self.is_active = False
        self.last_price = {}  # 记录最新价格
        
        # 添加模拟模式标志
        self.simulate_mode = False
        
        # 初始化
        self.symbols = DEFAULT_SYMBOLS.copy()  # 交易对列表
        self.trade_amount = TRADE_AMOUNT.copy()  # 交易数量
        self.arbitrage_threshold = ARBITRAGE_THRESHOLD  # 套利阈值（百分比）
        self.close_threshold = CLOSE_THRESHOLD  # 平仓阈值（百分比）
        
        # 日志控制
        self.log_levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        
        # 设置日志格式
        self.setup_logger()
        
        # 配置文件路径
        self.config_path = str(Path.cwd().joinpath("crypto_config.json"))
        self.write_log(f"初始化配置文件路径: {self.config_path}", level="INFO", force=True)
        
        # 交易所余额
        self.exchange_balances = {}
        
        # 数据容器
        self.prices: Dict[str, Dict[str, float]] = {}   # 价格数据
        self.diff_data: List[Dict[str, Any]] = []       # 价格差异数据
        self.active_arbitrages: Dict[str, Dict] = {}    # 活跃套利数据
        
        # 交易所列表
        self.exchange_names = ["okex", "binance", "bitget"]
        
        # 运行状态
        self.monitor_thread = None
        
        # 添加模拟模式标志
        self.simulate_mode = False
        
        # 初始化
        self.register_event()
        self.load_config()
        
    def register_event(self) -> None:
        """注册事件监听"""
        self.event_engine.register(EVENT_TIMER, self.process_timer_event)
        
    def process_timer_event(self, event: Event) -> None:
        """处理定时事件"""
        # 检查连接状态
        if self.is_active and not self.exchanges:
            self.init_exchanges()
            
    def load_config(self) -> dict:
        """加载配置文件"""
        try:
            # 打印配置文件路径
            self.write_log(f"尝试加载配置文件: {self.config_path}", level="INFO", force=True)
            
            # 确保配置文件存在
            config_file = Path(self.config_path)
            if not config_file.exists():
                self.write_log(f"配置文件不存在，已创建默认配置：{self.config_path}", level="WARNING", force=True)
                self.create_default_config()
            
            # 读取配置文件内容并保存到变量方便调试
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_content = f.read()
                
            # 检查配置文件内容
            if not config_content.strip():
                self.write_log("配置文件为空", level="ERROR", force=True)
                return {}
                
            # 加载JSON配置
            config = json.loads(config_content)
            
            # 检查配置内容
            if not config:
                self.write_log("配置为空", level="ERROR", force=True)
                return {}
                
            # 获取交易所配置
            exchange_configs = config.get("api_keys", {})
            
            # 输出配置内容以便调试
            self.write_log(f"配置文件已加载，包含交易所: {list(exchange_configs.keys())}", level="INFO", force=True)
            
            # 检查交易所配置
            for exchange_name, exchange_config in exchange_configs.items():
                if isinstance(exchange_config, dict):
                    # 输出密钥信息（不显示实际内容，只显示是否存在）
                    key_info = "已设置" if exchange_config.get("key") else "未设置"
                    secret_info = "已设置" if exchange_config.get("secret") else "未设置"
                    passphrase_info = "已设置" if exchange_config.get("passphrase") else "未设置" if exchange_name.lower() in ["okex", "bitget"] else "不需要"
                    
                    self.write_log(f"交易所 {exchange_name.upper()} API配置: key={key_info}, secret={secret_info}, passphrase={passphrase_info}", level="INFO", force=True)
            
            return config
        except json.JSONDecodeError as e:
            self.write_log(f"解析配置文件失败，JSON解析错误: {e}", level="ERROR", force=True)
            # 输出配置文件内容前100个字符以便诊断
            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read(100)
                self.write_log(f"配置文件内容预览: {content}...", level="ERROR", force=True)
            return {}
        except Exception as e:
            self.write_log(f"加载配置文件失败：{e}", level="ERROR", force=True)
            # 记录详细错误信息和堆栈跟踪
            import traceback
            self.write_log(f"错误详情: {traceback.format_exc()}", level="ERROR", force=True)
            return {}
            
    def init_exchanges(self):
        """初始化交易所"""
        config = self.settings
        if not config:
            self.write_log("初始化交易所失败：配置为空", level="ERROR")
            return False
        
        # 获取API配置
        api_keys = config.get("api_keys", {})
        
        # 添加模拟模式标志，当API密钥为空时启用
        api_ok_count = 0
        connection_errors = []
        
        self.write_log(f"开始初始化交易所连接，共有{len(api_keys)}个交易所配置", level="INFO", force=True)
        
        try:
            # 获取OKEX交易所配置
            okex_config = api_keys.get("okex", {})
            if okex_config:
                okex_key = okex_config.get("key", "")
                okex_secret = okex_config.get("secret", "")
                okex_passphrase = okex_config.get("passphrase", "")
                
                if okex_key and okex_secret and okex_passphrase:
                    try:
                        self.write_log(f"正在连接OKX交易所API...", level="INFO", force=True)
                        self.exchanges["okex"] = ccxt.okx({
                            'apiKey': okex_key,
                            'secret': okex_secret,
                            'password': okex_passphrase,
                            'enableRateLimit': True,
                            'timeout': 10000,  # 10秒超时
                            'proxies': self.get_proxy(config)
                        })
                        # 测试API连接 - 使用简单的公共API测试，而不是加载整个市场
                        self.write_log(f"OKX API连接成功，正在测试API...", level="INFO", force=True)
                        
                        import time
                        start_time = time.time()
                        # 只测试一个交易对的行情
                        test_result = self.exchanges["okex"].fetch_ticker("BTC/USDT")
                        time_used = time.time() - start_time
                        self.write_log(f"OKX API请求耗时: {time_used:.2f}秒", level="INFO", force=True)
                        
                        if test_result:
                            self.write_log(f"OKX API测试成功，当前BTC价格: {test_result['last']:.2f} USDT", level="INFO", force=True)
                            api_ok_count += 1
                    except Exception as e:
                        error_msg = f"OKX交易所初始化失败: {str(e)}"
                        self.write_log(error_msg, level="ERROR", force=True)
                        connection_errors.append(error_msg)
                        if "okex" in self.exchanges:
                            del self.exchanges["okex"]
                else:
                    self.write_log("OKX交易所API密钥未完全设置，跳过", level="WARNING", force=True)
            
            # 获取Binance交易所配置
            binance_config = api_keys.get("binance", {})
            if binance_config:
                binance_key = binance_config.get("key", "")
                binance_secret = binance_config.get("secret", "")
                
                if binance_key and binance_secret:
                    try:
                        self.write_log(f"正在连接Binance交易所API...", level="INFO", force=True)
                        self.exchanges["binance"] = ccxt.binance({
                            'apiKey': binance_key,
                            'secret': binance_secret,
                            'enableRateLimit': True,
                            'timeout': 10000,  # 10秒超时
                            'proxies': self.get_proxy(config)
                        })
                        # 测试API连接 - 使用简单的公共API测试，而不是加载整个市场
                        self.write_log(f"Binance API连接成功，正在测试API...", level="INFO", force=True)
                        
                        import time
                        start_time = time.time()
                        # 只测试一个交易对的行情
                        test_result = self.exchanges["binance"].fetch_ticker("BTC/USDT")
                        time_used = time.time() - start_time
                        self.write_log(f"Binance API请求耗时: {time_used:.2f}秒", level="INFO", force=True)
                        
                        if test_result:
                            self.write_log(f"Binance API测试成功，当前BTC价格: {test_result['last']:.2f} USDT", level="INFO", force=True)
                            api_ok_count += 1
                    except Exception as e:
                        error_msg = f"Binance交易所初始化失败: {str(e)}"
                        self.write_log(error_msg, level="ERROR", force=True)
                        connection_errors.append(error_msg)
                        if "binance" in self.exchanges:
                            del self.exchanges["binance"]
                else:
                    self.write_log("Binance交易所API密钥未完全设置，跳过", level="WARNING", force=True)
            
            # 获取Bitget交易所配置
            bitget_config = api_keys.get("bitget", {})
            if bitget_config:
                bitget_key = bitget_config.get("key", "")
                bitget_secret = bitget_config.get("secret", "")
                bitget_passphrase = bitget_config.get("passphrase", "")
                
                if bitget_key and bitget_secret and bitget_passphrase:
                    try:
                        self.write_log(f"正在连接Bitget交易所API...", level="INFO", force=True)
                        self.exchanges["bitget"] = ccxt.bitget({
                            'apiKey': bitget_key,
                            'secret': bitget_secret,
                            'password': bitget_passphrase,
                            'enableRateLimit': True,
                            'timeout': 10000,  # 10秒超时
                            'proxies': self.get_proxy(config)
                        })
                        # 测试API连接 - 使用简单的公共API测试，而不是加载整个市场
                        self.write_log(f"Bitget API连接成功，正在测试API...", level="INFO", force=True)
                        
                        import time
                        start_time = time.time()
                        # 只测试一个交易对的行情
                        test_result = self.exchanges["bitget"].fetch_ticker("BTC/USDT")
                        time_used = time.time() - start_time
                        self.write_log(f"Bitget API请求耗时: {time_used:.2f}秒", level="INFO", force=True)
                        
                        if test_result:
                            self.write_log(f"Bitget API测试成功，当前BTC价格: {test_result['last']:.2f} USDT", level="INFO", force=True)
                            api_ok_count += 1
                    except Exception as e:
                        error_msg = f"Bitget交易所初始化失败: {str(e)}"
                        self.write_log(error_msg, level="ERROR", force=True)
                        connection_errors.append(error_msg)
                        if "bitget" in self.exchanges:
                            del self.exchanges["bitget"]
                else:
                    self.write_log("Bitget交易所API密钥未完全设置，跳过", level="WARNING", force=True)
            
            # 如果没有任何交易所连接成功，尝试创建模拟交易所
            if not self.exchanges:
                self.write_log("没有任何交易所连接成功，将启用模拟模式", level="WARNING", force=True)
                self.simulate_mode = True
                return False
                
            # 显示初始化结果
            self.write_log(f"交易所初始化完成: 成功连接 {api_ok_count} 个交易所", level="INFO", force=True)
            
            # 如果有连接错误，显示详细信息
            if connection_errors:
                error_summary = "\n".join(connection_errors)
                self.write_log(f"交易所连接错误详情:\n{error_summary}", level="WARNING", force=True)
            
            return api_ok_count > 0
            
        except Exception as e:
            self.write_log(f"初始化交易所时发生错误: {e}", level="ERROR", force=True)
            import traceback
            self.write_log(traceback.format_exc(), level="ERROR", force=True)
            return False
    
    def get_proxy(self, config):
        """获取代理设置"""
        # 获取代理配置
        proxy_config = config.get("proxy", {})
        
        if proxy_config and proxy_config.get("enabled", False):
            host = proxy_config.get("host", "")
            port = proxy_config.get("port", 0)
            
            if host and port:
                # 构建代理URL
                proxy_url = f"http://{host}:{port}"
                self.write_log(f"使用代理: {proxy_url}", level="INFO", force=True)
                return {
                    'http': proxy_url,
                    'https': proxy_url
                }
        
        # 无代理
        return None
        
    def start(self, enable_trading: bool = False) -> None:
        """启动套利监控"""
        self.enable_trading = enable_trading
        
        # 如果已经在运行，先停止
        if self.is_active:
            self.stop()
        
        # 初始化交易所连接（如果尚未初始化）
        if not self.exchanges and not self.simulate_mode:
            init_result = self.init_exchanges()
            if not init_result:
                self.write_log("实盘API初始化失败，请检查配置", level="ERROR", force=True)
                return
        
        # 检查余额
        if not self.simulate_mode:
            self.check_balances()
        
        # 启动监控线程
        self.is_active = True
        self.write_log("开始监控价格差异", level="INFO", force=True)
        self.monitor_thread = Thread(target=self.monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop(self) -> None:
        """停止套利监控"""
        if not self.is_active:
            return
            
        self.is_active = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
            self.monitor_thread = None
            
        self.write_log("套利监控已停止", level="INFO", force=True)
        
    def check_balances(self) -> Dict[str, Dict]:
        """检查交易所余额"""
        balances = {}
        
        for name, exchange in self.exchanges.items():
            try:
                balance = exchange.fetch_balance()
                
                # 只保存有余额的币种
                non_zero = {
                    currency: data 
                    for currency, data in balance['total'].items() 
                    if data > 0 and currency != 'info'
                }
                
                balances[name] = non_zero
                self.exchange_balances[name] = non_zero
                
                # 记录余额到日志
                balance_str = ", ".join([f"{cur}: {amt:.6f}" for cur, amt in sorted(non_zero.items()) if amt > 0.0001])
                self.write_log(f"{name} 余额: {balance_str}")
                
                # 发送余额更新事件
                self.on_balance(name, non_zero)
                
            except Exception as e:
                self.write_log(f"获取 {name} 余额失败: {e}", level="ERROR")
                
        return balances
        
    def has_sufficient_balance(self, symbol: str, exchange_name: str, required_amount: float) -> bool:
        """检查交易所是否有足够余额执行交易"""
        if exchange_name not in self.exchange_balances:
            self.write_log(f"交易所 {exchange_name} 余额数据不可用", level="WARNING")
            return False
            
        balances = self.exchange_balances[exchange_name]
        
        # 如果是模拟模式，假设余额充足
        if self.simulate_mode:
            return True
            
        # 解析交易对
        base_currency, quote_currency = symbol.split('/')
        
        # 检查买入所需的USDT余额
        if required_amount == 0:  # 买入检查
            if quote_currency not in balances:
                self.write_log(f"交易所 {exchange_name} 没有 {quote_currency} 余额", level="WARNING")
                return False
                
            quote_balance = balances[quote_currency]
            required_quote = required_amount * self.last_price.get(symbol, 1)
            
            if quote_balance < required_quote:
                self.write_log(f"交易所 {exchange_name} {quote_currency} 余额不足: {quote_balance:.6f} < {required_quote:.6f}", level="WARNING")
                return False
        else:  # 卖出检查
            if base_currency not in balances:
                self.write_log(f"交易所 {exchange_name} 没有 {base_currency} 余额", level="WARNING")
                return False
                
            base_balance = balances[base_currency]
            
            if base_balance < required_amount:
                self.write_log(f"交易所 {exchange_name} {base_currency} 余额不足: {base_balance:.6f} < {required_amount:.6f}", level="WARNING")
                return False
                
        return True
        
    def get_ticker(self, exchange, symbol: str) -> dict:
        """获取单个交易对的行情数据"""
        try:
            ticker = exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            self.write_log(f"获取行情失败：{exchange.id} {symbol} - {e}")
            return {}
            
    def fetch_all_prices(self) -> Dict[str, Dict[str, Dict[str, float]]]:
        """获取所有交易所的所有交易对价格"""
        # 如果是模拟模式，返回模拟数据
        if self.simulate_mode:
            return self.generate_simulated_data()
            
        if not self.exchanges:
            self.write_log("未初始化任何交易所，无法获取价格", level="ERROR")
            return {}

        result = {}
        for exchange_name, exchange in self.exchanges.items():
            result[exchange_name] = {}
            
            for symbol in self.symbols:
                # 添加重试逻辑
                max_retries = 3
                retry_delay = 2
                for retry in range(max_retries):
                    try:
                        # 只有verbosity大于1才输出详细日志
                        if self.verbose_logging > 1:
                            self.write_log(f"正在获取 {exchange_name} {symbol} 价格...")
                        
                        ticker = exchange.fetch_ticker(symbol)
                        
                        bid = ticker['bid']
                        ask = ticker['ask']
                        last = ticker['last']
                        
                        result[exchange_name][symbol] = {
                            'bid': bid,
                            'ask': ask,
                            'last': last,
                            'volume': ticker.get('volume', 0),
                            'timestamp': ticker['timestamp']
                        }
                        
                        # 成功获取数据，跳出重试循环
                        break
                        
                    except Exception as e:
                        if retry < max_retries - 1:
                            self.write_log(f"{exchange_name} {symbol} 价格获取失败(重试 {retry+1}/{max_retries}): {str(e)}", level="WARNING")
                            import time
                            # 每次重试增加等待时间
                            time.sleep(retry_delay * (retry + 1))
                        else:
                            self.write_log(f"{exchange_name} {symbol} 价格获取失败: {str(e)}", level="ERROR")
                            # 设置默认值防止程序崩溃
                            result[exchange_name][symbol] = {
                                'bid': None,
                                'ask': None,
                                'last': None,
                                'volume': 0,
                                'timestamp': 0
                            }
                
                # 添加小延迟避免请求速率限制
                import time
                time.sleep(0.2)
                        
        return result
        
    def calculate_price_differences(self, prices: Dict[str, Dict[str, Dict[str, float]]]) -> List[Dict[str, Any]]:
        """计算价格差异"""
        diff_data = []
        
        # 遍历所有交易对
        for symbol in self.symbols:
            symbol_data = {}
            
            # 收集所有交易所的该交易对价格
            for exchange_name, exchange_prices in prices.items():
                if symbol in exchange_prices:
                    price_data = exchange_prices[symbol]
                    if price_data['last'] is not None:  # 确保价格有效
                        symbol_data[exchange_name] = price_data
            
            # 如果至少有两个交易所数据，才能计算差价
            if len(symbol_data) >= 2:
                # 找出最低和最高价格的交易所
                min_exchange = None
                max_exchange = None
                min_price = float('inf')
                max_price = 0
                
                volumes = {}
                
                for exchange_name, price_data in symbol_data.items():
                    last_price = price_data['last']
                    
                    # 更新成交量数据
                    volumes[exchange_name] = price_data.get('volume', 0)
                    
                    # 更新最低价
                    if last_price < min_price:
                        min_price = last_price
                        min_exchange = exchange_name
                    
                    # 更新最高价
                    if last_price > max_price:
                        max_price = last_price
                        max_exchange = exchange_name
                
                # 计算价差
                price_diff = max_price - min_price
                
                # 计算价差百分比
                price_diff_pct = price_diff / min_price if min_price > 0 else 0
                
                # 添加到结果
                if price_diff_pct > 0:
                    diff_data.append({
                        "symbol": symbol,
                        "min_exchange": min_exchange,
                        "max_exchange": max_exchange,
                        "min_price": min_price,
                        "max_price": max_price,
                        "price_diff": price_diff,
                        "price_diff_pct": price_diff_pct,
                        "volumes": volumes
                    })
        
        # 按价差百分比排序
        diff_data.sort(key=lambda x: x["price_diff_pct"], reverse=True)
        
        return diff_data
        
    def log_arbitrage_opportunity(self, diff_data: List[Dict[str, Any]]) -> None:
        """记录套利机会"""
        # 只记录较大的套利机会，减少日志量
        threshold = self.arbitrage_threshold * 0.8  # 使用较低的阈值记录潜在机会
        
        for item in diff_data:
            if item["price_diff_pct"] >= threshold:  # 只记录明显的套利机会
                self.write_log(
                    f"套利机会: {item['symbol']} - {item['min_exchange']}({item['min_price']:.2f}) → "
                    f"{item['max_exchange']}({item['max_price']:.2f}) - "
                    f"差价: {item['price_diff']:.2f} ({item['price_diff_pct']*100:.2f}%)"
                )
                
    def execute_arbitrage(self, diff_data: List[Dict[str, Any]]) -> None:
        """执行套利交易"""
        # 如果是模拟模式，只记录交易信号
        if self.simulate_mode:
            for item in diff_data:
                if item["price_diff_pct"] >= self.arbitrage_threshold:
                    self.write_log(
                        f"[模拟] 套利信号: {item['symbol']} - 从 {item['min_exchange']}({item['min_price']:.4f}) "
                        f"买入并在 {item['max_exchange']}({item['max_price']:.4f}) 卖出 - "
                        f"差价: {item['price_diff']:.4f} ({item['price_diff_pct']*100:.2f}%)",
                        level="INFO", force=True
                    )
            return
            
        # 真实交易逻辑
        for item in diff_data:
            symbol = item["symbol"]
            price_diff_pct = item.get("price_diff_pct", 0)
            
            # 检查是否达到套利阈值
            if price_diff_pct >= self.arbitrage_threshold:
                try:
                    buy_exchange_name = item["min_exchange"]
                    sell_exchange_name = item["max_exchange"]
                    
                    amount = self.trade_amount.get(symbol, 0.001)
                    
                    # 检查余额是否充足
                    if not self.has_sufficient_balance(symbol, buy_exchange_name, 0):  # 买入时只需检查USDT余额是否充足
                        self.write_log(f"套利失败: {symbol} - {buy_exchange_name} USDT余额不足")
                        continue
                        
                    if not self.has_sufficient_balance(symbol, sell_exchange_name, amount):
                        self.write_log(f"套利失败: {symbol} - {sell_exchange_name} {symbol.split('/')[0]}余额不足")
                        continue
                    
                    # 在低价交易所买入
                    buy_exchange = self.exchanges[buy_exchange_name]
                    buy_result = buy_exchange.create_market_buy_order(symbol, amount)
                    
                    # 在高价交易所卖出
                    sell_exchange = self.exchanges[sell_exchange_name]
                    sell_result = sell_exchange.create_market_sell_order(symbol, amount)
                    
                    expected_profit = item["price_diff"] * amount
                    expected_profit_pct = price_diff_pct * 100
                    
                    self.write_log(
                        f"套利执行: {symbol} - 从 {buy_exchange_name}({item['min_price']:.4f}) "
                        f"买入并在 {sell_exchange_name}({item['max_price']:.4f}) 卖出 - "
                        f"数量: {amount} - 预期利润: {expected_profit:.4f} USDT ({expected_profit_pct:.2f}%)",
                        level="INFO", force=True
                    )
                    
                    # 发送交易事件
                    trade_info = {
                        "symbol": symbol,
                        "type": "arbitrage",
                        "buy_exchange": buy_exchange_name,
                        "sell_exchange": sell_exchange_name,
                        "amount": amount,
                        "buy_price": item["min_price"],
                        "sell_price": item["max_price"],
                        "price_diff": item["price_diff"],
                        "price_diff_pct": price_diff_pct,
                        "profit": expected_profit,
                        "timestamp": time.time()
                    }
                    self.on_trade(symbol, "open", trade_info, buy_result, sell_result)
                    
                    # 更新余额
                    self.check_balances()
                    
                except Exception as e:
                    self.write_log(f"套利执行失败 {symbol}: {e}", level="ERROR")
                    import traceback
                    self.write_log(traceback.format_exc(), level="ERROR")
    
    def on_diff(self, diff_data: List[Dict[str, Any]]) -> None:
        """处理价差更新事件"""
        if self.event_engine:
            event = Event(EVENT_CRYPTO_DIFF, diff_data)
            self.event_engine.put(event)
            
    def on_trade(self, symbol: str, trade_type: str, arb_info: dict, order1: dict, order2: dict) -> None:
        """处理交易事件"""
        if self.event_engine:
            trade_data = {
                "symbol": symbol,
                "type": trade_type,
                "arb_info": arb_info,
                "order1": order1,
                "order2": order2,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            event = Event(EVENT_CRYPTO_TRADE, trade_data)
            self.event_engine.put(event)
        
    def on_balance(self, exchange_name: str, balance: dict) -> None:
        """处理余额更新事件"""
        event = Event(EVENT_CRYPTO_BALANCE, (exchange_name, balance))
        self.event_engine.put(event)
        
    def create_default_config(self) -> None:
        """创建默认配置文件"""
        try:
            # 检查config_path
            if not hasattr(self, "config_path") or not self.config_path:
                self.config_path = str(Path.cwd().joinpath("crypto_config.json"))
                
            self.write_log(f"正在创建默认配置文件: {self.config_path}", level="INFO", force=True)
                
            # 创建默认配置
            default_config = {
                "OKEX": {
                    "key": "你的OKX API Key",
                    "secret": "你的OKX Secret Key",
                    "passphrase": "你的OKX API密码",
                    "server": "SPOT",
                    "proxy_host": "",
                    "proxy_port": 0
                },
                "BINANCE": {
                    "key": "你的Binance API Key",
                    "secret": "你的Binance Secret Key",
                    "server": "SPOT",
                    "proxy_host": "",
                    "proxy_port": 0
                },
                "BITGET": {
                    "key": "你的Bitget API Key",
                    "secret": "你的Bitget Secret Key",
                    "passphrase": "你的Bitget API密码",
                    "server": "SPOT",
                    "proxy_host": "",
                    "proxy_port": 0
                }
            }
            
            # 写入配置文件，使用格式化的JSON以便阅读
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
                
            self.write_log(f"默认配置文件已创建: {self.config_path}", level="INFO", force=True)
            self.write_log("请修改配置文件，填入正确的API密钥信息", level="WARNING", force=True)
            
            # 尝试创建一个明确的示例文件，供用户参考
            example_path = str(Path.cwd().joinpath("crypto_config_example.json"))
            with open(example_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
                
            self.write_log(f"配置文件示例已创建: {example_path}", level="INFO", force=True)
            
            # 检查是否有提供的API密钥信息 (注意安全性，实际应用中不要记录敏感信息)
            api_info_path = str(Path.cwd().joinpath("API-KEY.md"))
            if Path(api_info_path).exists():
                self.write_log(f"检测到API密钥信息文件: {api_info_path}", level="INFO", force=True)
                self.write_log("请参考该文件中的信息填写配置文件", level="INFO", force=True)
            
            return True
        except Exception as e:
            self.write_log(f"创建默认配置文件失败: {e}", level="ERROR", force=True)
            import traceback
            self.write_log(f"错误详情: {traceback.format_exc()}", level="ERROR", force=True)
            return False
        
    def create_simulation_data(self) -> None:
        """创建模拟数据以供测试和演示
        当无法连接到真实交易所时，将使用此方法生成模拟数据
        """
        try:
            import random
            
            self.write_log("初始化模拟数据模式", level="INFO", force=True)
            
            # 模拟交易所列表
            exchanges_names = ["okex", "binance", "bitget"]
            
            # 清空原有交易所对象，创建模拟交易所
            self.exchanges = {}
            
            # 在模拟模式下初始化一个交易所对象，用于存储模拟数据
            for name in exchanges_names:
                # 创建模拟交易所对象
                class SimulationExchange:
                    def __init__(self, name):
                        self.id = name
                        self.name = name
                        self.base_prices = {
                            "BTC/USDT": 65000 + random.uniform(-2000, 2000),
                            "ETH/USDT": 3500 + random.uniform(-100, 100),
                            "BNB/USDT": 600 + random.uniform(-20, 20),
                            "SOL/USDT": 140 + random.uniform(-5, 5),
                            "XRP/USDT": 0.55 + random.uniform(-0.02, 0.02),
                            "ADA/USDT": 0.45 + random.uniform(-0.01, 0.01),
                            "DOGE/USDT": 0.12 + random.uniform(-0.005, 0.005),
                            "DOT/USDT": 7.2 + random.uniform(-0.2, 0.2),
                            "AVAX/USDT": 35 + random.uniform(-1, 1),
                            "MATIC/USDT": 0.85 + random.uniform(-0.03, 0.03),
                            "LINK/USDT": 17 + random.uniform(-0.5, 0.5),
                            "UNI/USDT": 9.5 + random.uniform(-0.3, 0.3),
                            "SHIB/USDT": 0.00002 + random.uniform(-0.000001, 0.000001),
                            "LTC/USDT": 80 + random.uniform(-2, 2),
                            "ATOM/USDT": 8.2 + random.uniform(-0.25, 0.25),
                            "TRX/USDT": 0.11 + random.uniform(-0.003, 0.003)
                        }
                        self.last_update = {symbol: time.time() for symbol in self.base_prices}
                        self.simulation_balances = {
                            "USDT": 10000.0,
                            "BTC": 0.5,
                            "ETH": 5.0,
                            "BNB": 20.0,
                            "SOL": 50.0,
                            "XRP": 1000.0,
                            "ADA": 5000.0,
                            "DOGE": 50000.0,
                            "DOT": 200.0
                        }
                        # 添加模拟迁移和提现功能的时间记录
                        self.transfer_times = {}
                    
                    def fetch_ticker(self, symbol):
                        """获取模拟行情数据"""
                        current_time = time.time()
                        # 随机价格波动（基于上次更新时间）
                        time_diff = current_time - self.last_update.get(symbol, current_time)
                        # 更新价格（加入随机波动）
                        base_price = self.base_prices.get(symbol, 1.0)
                        # 每秒最大波动幅度为0.05%
                        max_change_pct = 0.0005 * time_diff
                        change_pct = random.uniform(-max_change_pct, max_change_pct)
                        price = base_price * (1 + change_pct)
                        
                        # 更新基础价格和更新时间
                        self.base_prices[symbol] = price
                        self.last_update[symbol] = current_time
                        
                        # 返回模拟行情数据
                        return {
                            'symbol': symbol,
                            'timestamp': int(current_time * 1000),
                            'datetime': datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S'),
                            'high': price * (1 + random.uniform(0, 0.002)),
                            'low': price * (1 - random.uniform(0, 0.002)),
                            'bid': price * (1 - random.uniform(0, 0.001)),
                            'ask': price * (1 + random.uniform(0, 0.001)),
                            'last': price,
                            'close': price,
                            'previousClose': price * (1 - change_pct),
                            'change': price * change_pct,
                            'percentage': change_pct * 100,
                            'average': price,
                            'baseVolume': random.uniform(100, 10000),
                            'quoteVolume': random.uniform(100, 10000) * price,
                            'info': {}
                        }
                        
                    def fetch_order_book(self, symbol):
                        """获取模拟订单簿数据"""
                        # 获取当前价格作为基准
                        ticker = self.fetch_ticker(symbol)
                        current_price = ticker['last']
                        
                        # 生成模拟订单簿数据
                        bids = []  # 买单
                        asks = []  # 卖单
                        
                        # 创建10层买单
                        for i in range(10):
                            # 买单价格逐渐降低 (从当前价格的99.9%到99%)
                            bid_price = current_price * (0.999 - i * 0.0001)
                            # 数量随机，较高层位数量较大
                            bid_volume = random.uniform(0.5, 5) * TRADE_AMOUNT.get(symbol, 1) * (10 - i) / 10
                            bids.append([bid_price, bid_volume])
                        
                        # 创建10层卖单
                        for i in range(10):
                            # 卖单价格逐渐升高 (从当前价格的100.1%到101%)
                            ask_price = current_price * (1.001 + i * 0.0001)
                            # 数量随机，较高层位数量较大
                            ask_volume = random.uniform(0.5, 5) * TRADE_AMOUNT.get(symbol, 1) * (10 - i) / 10
                            asks.append([ask_price, ask_volume])
                        
                        # 返回模拟订单簿数据
                        return {
                            'symbol': symbol,
                            'timestamp': int(time.time() * 1000),
                            'datetime': datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'),
                            'bids': bids,
                            'asks': asks,
                            'nonce': int(time.time() * 1000)
                        }
                    
                    def fetch_balance(self):
                        """获取模拟余额数据"""
                        return {
                            'info': {},
                            'timestamp': int(time.time() * 1000),
                            'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'free': self.simulation_balances.copy(),
                            'used': {k: 0.0 for k in self.simulation_balances},
                            'total': self.simulation_balances.copy()
                        }
                        
                    def create_market_buy_order(self, symbol, amount):
                        """模拟市价买入订单"""
                        base, quote = symbol.split('/')
                        ticker = self.fetch_ticker(symbol)
                        price = ticker['last']
                        cost = price * amount
                        
                        # 检查余额是否足够
                        if self.simulation_balances.get(quote, 0) < cost:
                            raise Exception(f"模拟交易所 {self.name} 余额不足：需要 {cost} {quote}，但只有 {self.simulation_balances.get(quote, 0)}")
                        
                        # 更新余额
                        self.simulation_balances[quote] = self.simulation_balances.get(quote, 0) - cost
                        self.simulation_balances[base] = self.simulation_balances.get(base, 0) + amount
                        
                        # 返回订单信息
                        return {
                            'id': f"sim_{int(time.time() * 1000)}_{random.randint(100000, 999999)}",
                            'symbol': symbol,
                            'type': 'market',
                            'side': 'buy',
                            'price': price,
                            'amount': amount,
                            'cost': cost,
                            'status': 'closed',
                            'fee': {'cost': cost * 0.001, 'currency': quote},
                            'info': {}
                        }
                        
                    def create_market_sell_order(self, symbol, amount):
                        """模拟市价卖出订单"""
                        base, quote = symbol.split('/')
                        ticker = self.fetch_ticker(symbol)
                        price = ticker['last']
                        cost = price * amount
                        
                        # 检查余额是否足够
                        if self.simulation_balances.get(base, 0) < amount:
                            raise Exception(f"模拟交易所 {self.name} 余额不足：需要 {amount} {base}，但只有 {self.simulation_balances.get(base, 0)}")
                        
                        # 更新余额
                        self.simulation_balances[base] = self.simulation_balances.get(base, 0) - amount
                        self.simulation_balances[quote] = self.simulation_balances.get(quote, 0) + cost
                        
                        # 返回订单信息
                        return {
                            'id': f"sim_{int(time.time() * 1000)}_{random.randint(100000, 999999)}",
                            'symbol': symbol,
                            'type': 'market',
                            'side': 'sell',
                            'price': price,
                            'amount': amount,
                            'cost': cost,
                            'status': 'closed',
                            'fee': {'cost': cost * 0.001, 'currency': quote},
                            'info': {}
                        }
                    
                    def transfer_to_exchange(self, currency, amount, target_exchange_name):
                        """模拟将资金从当前交易所转移到目标交易所"""
                        # 检查当前交易所余额是否足够
                        if self.simulation_balances.get(currency, 0) < amount:
                            raise Exception(f"{self.name}余额不足，无法转移{amount} {currency}到{target_exchange_name}")
                        
                        # 记录转账时间
                        transfer_id = f"{self.name}_{target_exchange_name}_{currency}_{time.time()}"
                        self.transfer_times[transfer_id] = {
                            "start_time": time.time(),
                            "currency": currency,
                            "amount": amount,
                            "target": target_exchange_name,
                            "completed": False
                        }
                        
                        # 从当前交易所扣除资金
                        self.simulation_balances[currency] = self.simulation_balances.get(currency, 0) - amount
                        
                        # 返回转账信息
                        return {
                            "id": transfer_id,
                            "status": "pending",
                            "currency": currency,
                            "amount": amount,
                            "fee": amount * 0.001,  # 模拟0.1%转账费
                            "timestamp": time.time(),
                            "info": {}
                        }
                    
                    def check_transfer_status(self, transfer_id):
                        """检查转账状态"""
                        if transfer_id not in self.transfer_times:
                            raise Exception(f"转账ID {transfer_id} 不存在")
                        
                        transfer_info = self.transfer_times[transfer_id]
                        current_time = time.time()
                        time_diff = current_time - transfer_info["start_time"]
                        
                        # 模拟转账需要的时间（2分钟）
                        if time_diff >= 120 and not transfer_info["completed"]:
                            transfer_info["completed"] = True
                            # 目标交易所增加资金的逻辑需要在外部处理
                            return {
                                "id": transfer_id,
                                "status": "completed",
                                "currency": transfer_info["currency"],
                                "amount": transfer_info["amount"],
                                "target": transfer_info["target"],
                                "completion_time": current_time
                            }
                        elif not transfer_info["completed"]:
                            # 转账尚未完成
                            progress = min(int(time_diff / 120 * 100), 99)  # 最多显示99%进度
                            return {
                                "id": transfer_id,
                                "status": "in_progress",
                                "currency": transfer_info["currency"],
                                "amount": transfer_info["amount"],
                                "target": transfer_info["target"],
                                "progress": f"{progress}%",
                                "estimated_completion": transfer_info["start_time"] + 120
                            }
                        else:
                            # 转账已完成
                            return {
                                "id": transfer_id,
                                "status": "completed",
                                "currency": transfer_info["currency"],
                                "amount": transfer_info["amount"],
                                "target": transfer_info["target"],
                                "completion_time": transfer_info["start_time"] + 120
                            }
                
                # 将模拟交易所添加到交易所列表
                self.exchanges[name] = SimulationExchange(name)
            
            self.write_log("模拟数据初始化完成，可以正常使用系统", level="INFO", force=True)
        except Exception as e:
            self.write_log(f"模拟数据初始化失败: {e}", level="ERROR", force=True) 

    # 添加禁用模拟模式的方法
    def disable_simulation_mode(self) -> None:
        """禁用模拟模式，强制使用真实API"""
        self.disable_simulation = True
        self.write_log("已禁用模拟模式，系统将仅使用真实交易所API", level="INFO", force=True) 

    def generate_simulated_data(self) -> Dict[str, Dict[str, Dict[str, float]]]:
        """生成模拟数据用于测试"""
        import random
        from datetime import datetime
        
        self.write_log("生成模拟价格数据...", level="INFO", force=True)
        
        # 基础价格数据（近似真实市场价格）
        base_prices = {
            "BTC/USDT": 65000 + random.randint(-500, 500),
            "ETH/USDT": 3500 + random.randint(-50, 50),
            "SOL/USDT": 150 + random.randint(-5, 5),
            "XRP/USDT": 0.65 + random.random() * 0.05,
            "BNB/USDT": 550 + random.randint(-10, 10),
            "ADA/USDT": 0.45 + random.random() * 0.03,
            "DOGE/USDT": 0.12 + random.random() * 0.01,
            "DOT/USDT": 7.5 + random.random() * 0.5,
        }
        
        # 确保只使用已配置的交易对
        available_symbols = [s for s in self.symbols if s in base_prices]
        
        # 创建交易所和交易对的数据结构
        result = {
            "okex": {},
            "binance": {},
            "bitget": {}
        }
        
        timestamp = int(datetime.now().timestamp() * 1000)
        
        # 为每个交易所生成略微不同的价格
        for symbol in available_symbols:
            base_price = base_prices[symbol]
            
            # OKX价格 (基础价 ± 0.1%)
            okx_variance = base_price * (0.999 + random.random() * 0.002)
            # Binance价格 (基础价 ± 0.1%)
            binance_variance = base_price * (0.999 + random.random() * 0.002)
            # Bitget价格 (基础价 ± 0.1%)
            bitget_variance = base_price * (0.999 + random.random() * 0.002)
            
            # 确保至少有一对有一定的差价 (制造套利机会)
            if random.random() < 0.3:  # 30%的概率产生套利机会
                # 随机选择一个交易所价格高一些
                high_exchange = random.choice(["okex", "binance", "bitget"])
                # 随机选择一个交易所价格低一些
                low_exchange = random.choice([e for e in ["okex", "binance", "bitget"] if e != high_exchange])
                
                if high_exchange == "okex":
                    okx_variance = base_price * 1.005  # 高0.5%
                elif high_exchange == "binance":
                    binance_variance = base_price * 1.005  # 高0.5%
                elif high_exchange == "bitget":
                    bitget_variance = base_price * 1.005  # 高0.5%
                
                if low_exchange == "okex":
                    okx_variance = base_price * 0.997  # 低0.3%
                elif low_exchange == "binance":
                    binance_variance = base_price * 0.997  # 低0.3%
                elif low_exchange == "bitget":
                    bitget_variance = base_price * 0.997  # 低0.3%
            
            # 计算买卖价差
            okx_spread = okx_variance * 0.0005  # 0.05%的价差
            binance_spread = binance_variance * 0.0005  # 0.05%的价差
            bitget_spread = bitget_variance * 0.0005  # 0.05%的价差
            
            # OKX数据
            result["okex"][symbol] = {
                'bid': okx_variance - okx_spread/2,
                'ask': okx_variance + okx_spread/2,
                'last': okx_variance,
                'volume': random.randint(1000, 10000),
                'timestamp': timestamp
            }
            
            # Binance数据
            result["binance"][symbol] = {
                'bid': binance_variance - binance_spread/2,
                'ask': binance_variance + binance_spread/2,
                'last': binance_variance,
                'volume': random.randint(2000, 20000),
                'timestamp': timestamp
            }
            
            # Bitget数据
            result["bitget"][symbol] = {
                'bid': bitget_variance - bitget_spread/2,
                'ask': bitget_variance + bitget_spread/2,
                'last': bitget_variance,
                'volume': random.randint(500, 5000),
                'timestamp': timestamp
            }
        
        return result 

    def setup_logger(self):
        """设置日志配置"""
        logger = logging.getLogger("crypto_arbitrage")
        logger.setLevel(logging.DEBUG)
        
        # 创建控制台处理程序
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 创建日志目录
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # 创建文件处理程序
        log_file = log_dir.joinpath(f"crypto_arbitrage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        
        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # 添加处理程序
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        self.logger = logger
        print(f"日志系统初始化完成，日志文件: {log_file}")
        
    def write_log(self, msg: str, level: str = "INFO", force: bool = False) -> None:
        """记录日志
        
        参数:
            msg (str): 日志消息
            level (str): 日志级别，默认INFO
            force (bool): 是否强制记录，忽略日志控制
        """
        # 检查是否需要记录日志
        # 如果不是详细日志模式且不是强制记录，则降低日志频率
        if hasattr(self, "verbose_logging") and not self.verbose_logging and not force:
            # 检查时间间隔
            current_time = time.time()
            if hasattr(self, "last_update_time") and self.last_update_time is not None:
                if (current_time - self.last_update_time) < self.update_interval:
                    # 时间间隔内不输出普通日志
                    if level == "INFO":
                        return
                else:
                    self.last_update_time = current_time
            else:
                # 初始化last_update_time
                self.last_update_time = current_time
            
        # 使用logger记录日志
        if hasattr(self, "logger"):
            log_level = self.log_levels.get(level, logging.INFO)
            self.logger.log(log_level, msg)
            
        # 如果有事件引擎，也发送事件
        if hasattr(self, "event_engine") and self.event_engine:
            log = LogData(
                gateway_name=APP_NAME,
                msg=msg,
                level=level
            )
            event = Event(EVENT_CRYPTO_LOG, log)
            self.event_engine.put(event) 

    def init_engine(self, settings: Dict = None, verbose: bool = False, enable_trading: bool = False, simulate: bool = False):
        """初始化引擎"""
        self.verbose_logging = verbose
        self.enable_trading = enable_trading
        self.simulate_mode = simulate
        
        if self.verbose_logging:
            self.verbosity = 2
        
        # 初始化设置
        if settings:
            self.settings = settings
        else:
            self.load_settings()
            
        # 初始化交易所
        if not simulate:
            api_ok = self.init_exchanges()
            if not api_ok:
                self.write_log("实盘API初始化失败，请检查配置", level="ERROR", force=True)
                return False
        else:
            self.write_log("启动模拟数据模式，将使用模拟数据而不是真实API连接", level="INFO", force=True)
            self.create_simulation_data()
            api_ok = True
        
        return api_ok
        
    def load_settings(self):
        """加载配置"""
        self.write_log(f"尝试加载配置文件: {self.config_path}", level="INFO", force=True)
        
        try:
            config = load_json(self.config_path)
            
            # 检查配置是否为空
            if not config:
                self.write_log("配置文件为空，使用默认设置", level="WARNING", force=True)
                return {}
                
            # 检查基本配置结构
            exchange_config = config.get("api_keys", {})
            
            # 日志输出配置信息
            self.write_log(f"配置文件已加载，包含交易所: {list(exchange_config.keys())}", level="INFO", force=True)
            
            # 检查交易所配置
            for name, api_info in exchange_config.items():
                has_key = "key" in api_info and api_info["key"]
                has_secret = "secret" in api_info and api_info["secret"]
                has_passphrase = "passphrase" in api_info and api_info["passphrase"]
                
                # 检查OKEX需要passphrase
                if name.lower() == "okex":
                    self.write_log(
                        f"交易所 {name} API配置: key={'已设置' if has_key else '未设置'}, "
                        f"secret={'已设置' if has_secret else '未设置'}, "
                        f"passphrase={'已设置' if has_passphrase else '未设置'}",
                        level="INFO", force=True
                    )
                elif name.lower() == "bitget":
                    self.write_log(
                        f"交易所 {name} API配置: key={'已设置' if has_key else '未设置'}, "
                        f"secret={'已设置' if has_secret else '未设置'}, "
                        f"passphrase={'已设置' if has_passphrase else '未设置'}",
                        level="INFO", force=True
                    )
                else:
                    self.write_log(
                        f"交易所 {name} API配置: key={'已设置' if has_key else '未设置'}, "
                        f"secret={'已设置' if has_secret else '未设置'}, "
                        f"passphrase={'不需要'}",
                        level="INFO", force=True
                    )
            
            # 更新交易对配置
            if "symbols" in config:
                self.symbols = config["symbols"]
                
            # 更新交易数量配置
            if "trade_amount" in config:
                for symbol, amount in config["trade_amount"].items():
                    self.trade_amount[symbol] = amount
                    
            # 更新套利阈值配置
            if "arbitrage_threshold" in config:
                self.arbitrage_threshold = config["arbitrage_threshold"] / 100.0  # 转换为小数
                
            # 更新平仓阈值配置
            if "close_threshold" in config:
                self.close_threshold = config["close_threshold"] / 100.0  # 转换为小数
                
            # 更新更新间隔配置
            if "update_interval" in config:
                self.update_interval = config["update_interval"]
                
            self.settings = config
            return config
            
        except json.JSONDecodeError:
            self.write_log(f"配置文件 {self.config_path} 不是有效的JSON格式", level="ERROR", force=True)
            # 读取文件前100个字符以便诊断
            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read(100)
                self.write_log(f"配置文件内容预览: {content}...", level="ERROR", force=True)
            return {}
        except Exception as e:
            self.write_log(f"加载配置文件失败：{e}", level="ERROR", force=True)
            # 记录详细错误信息和堆栈跟踪
            import traceback
            self.write_log(f"错误详情: {traceback.format_exc()}", level="ERROR", force=True)
            return {} 

    def monitor_loop(self) -> None:
        """监控价格循环"""
        reconnect_count = 0
        last_update_time = 0
        
        try:
            while self.is_active:
                try:
                    current_time = time.time()
                    update_interval = self.update_interval
                    
                    # 检查更新间隔（不要太频繁请求）
                    if current_time - last_update_time < update_interval:
                        time.sleep(0.5)
                        continue
                    
                    # 获取价格数据
                    prices = self.fetch_all_prices()
                    
                    if prices:
                        # 计算价格差异
                        self.diff_data = self.calculate_price_differences(prices)
                        
                        # 记录套利机会
                        self.log_arbitrage_opportunity(self.diff_data)
                        
                        # 如果启用交易，执行套利
                        if self.enable_trading:
                            self.execute_arbitrage(self.diff_data)
                            
                        # 重置重连计数器
                        reconnect_count = 0
                        last_update_time = current_time
                    
                    # 等待0.5秒，减少CPU使用
                    time.sleep(0.5)
                    
                except Exception as e:
                    reconnect_count += 1
                    self.write_log(f"监控循环错误: {e}", level="ERROR", force=True)
                    
                    # 连续失败5次以上，尝试重新连接
                    if reconnect_count >= 5:
                        self.reconnect_exchanges()
                        reconnect_count = 0
                    
                    # 等待1秒
                    time.sleep(1)
        except Exception as e:
            self.write_log(f"监控线程异常: {e}", level="ERROR", force=True)
            import traceback
            self.write_log(traceback.format_exc(), level="ERROR", force=True) 