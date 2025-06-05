#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复版自动交易引擎
解决启动后立即关闭的问题，增强错误处理和日志记录
"""

import ccxt
import json
import time
import threading
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enhanced_logging_system import get_enhanced_logger, log_trading, log_system
import pandas as pd
import numpy as np

@dataclass
class TradePosition:
    """交易持仓"""
    symbol: str
    side: str
    entry_price: float
    quantity: float
    entry_time: datetime
    stop_loss: float
    take_profit: float
    strategy_id: str
    order_id: str = None
    unrealized_pnl: float = 0.0

@dataclass
class TradeResult:
    """交易结果"""
    success: bool
    order_id: str = None
    filled_price: float = 0.0
    filled_quantity: float = 0.0
    message: str = ""
    profit: float = 0.0

class FixedAutoTradingEngine:
    """修复版自动交易引擎"""
    
    def __init__(self, config_file: str = "crypto_config.json"):
        """初始化交易引擎"""
        self.logger = get_enhanced_logger()
        self.running = False
        self.config = {}
        self.exchange = None
        self.positions = {}
        self.trade_history = []
        self.balance = 0.0
        self.daily_target_return = 0.05
        self.max_daily_loss = 0.03
        self.daily_pnl = 0.0
        self.start_balance = 0.0
        self.trade_lock = threading.Lock()
        self.monitor_thread = None
        
        # 智能资金管理参数
        self.base_position_size = 0.02
        self.max_position_size = 0.15
        self.win_rate_threshold = 0.7
        self.profit_factor_threshold = 1.5
        
        # 动态止盈止损参数
        self.base_stop_loss = 0.02
        self.base_take_profit = 0.06
        self.trailing_stop_factor = 0.3
        
        # 安全初始化
        try:
            self._safe_init(config_file)
        except Exception as e:
            log_system("ERROR", f"自动交易引擎初始化失败: {e}")
            raise
        
    def _safe_init(self, config_file: str):
        """安全初始化流程"""
        log_system("INFO", "开始初始化自动交易引擎")
        
        # 1. 加载配置
        self.config = self._load_config(config_file)
        if not self.config:
            raise Exception("配置文件加载失败")
        
        # 2. 初始化交易所（生产环境必须成功）
        try:
            self.exchange = self._init_binance()
            log_system("INFO", f"币安交易所初始化成功，当前余额: {self.balance:.2f} USDT")
        except Exception as e:
            log_system("ERROR", f"币安交易所初始化失败: {e}")
            # 生产环境不允许切换到模拟模式
            raise Exception(f"生产环境交易所初始化失败，无法继续: {e}")
        
        # 3. 初始化日常追踪
        self._init_daily_tracking()
        
        log_system("INFO", "自动交易引擎初始化完成")
        
    def _load_config(self, config_file: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            log_system("INFO", f"配置文件 {config_file} 加载成功")
            return config
        except FileNotFoundError:
            log_system("WARNING", f"配置文件 {config_file} 不存在，使用默认配置")
            return self._get_default_config()
        except Exception as e:
            log_system("ERROR", f"加载配置文件失败: {e}")
            return {}
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            'binance': {
                'api_key': '',
                'secret_key': '',
                'sandbox': True
            },
            'trading': {
                'max_daily_trades': 10,
                'min_confidence': 0.6,
                'default_symbols': ['BTC/USDT', 'ETH/USDT']
            }
        }
    
    def _init_binance(self) -> ccxt.Exchange:
        """初始化币安交易所"""
        binance_config = self.config.get('binance', {})
        api_key = binance_config.get('api_key', '')
        secret_key = binance_config.get('secret_key', '')
        
        if not api_key or not secret_key:
            raise Exception("API密钥未配置")
        
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret_key,
            'sandbox': binance_config.get('sandbox', False),
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'},
            'timeout': 30000  # 30秒超时
        })
        
        # 测试连接 - 生产环境重试机制
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                log_system("INFO", f"尝试连接币安API (第 {attempt + 1} 次)")
                balance = exchange.fetch_balance()
                self.balance = float(balance.get('USDT', {}).get('free', 0))
                self.start_balance = self.balance
                
                if self.balance < 10:
                    log_system("WARNING", f"账户余额不足: {self.balance} USDT")
                
                log_system("INFO", f"✅ 币安API连接成功，余额: {self.balance:.2f} USDT")
                return exchange
                
            except Exception as e:
                log_system("ERROR", f"币安API连接失败 (第 {attempt + 1} 次): {e}")
                
                if attempt < max_retries - 1:
                    log_system("INFO", f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    log_system("ERROR", "🚫 生产环境API连接失败，无法启动自动交易")
                    raise Exception(f"API连接重试 {max_retries} 次后仍失败: {e}")
    
    def _init_daily_tracking(self):
        """初始化每日追踪"""
        self.daily_trades = 0
        self.daily_wins = 0
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
        log_system("INFO", "每日追踪数据已初始化")
    
    def start(self):
        """启动自动交易引擎"""
        if self.running:
            log_system("WARNING", "自动交易引擎已经在运行")
            return True
        
        try:
            self.running = True
            log_trading("ENGINE_START", result="启动成功")
            
            # 启动监控线程
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()
            
            log_system("INFO", "自动交易引擎启动成功")
            return True
            
        except Exception as e:
            self.running = False
            log_trading("ENGINE_START", error_message=str(e))
            log_system("ERROR", f"自动交易引擎启动失败: {e}")
            return False
    
    def stop(self):
        """停止自动交易引擎"""
        if not self.running:
            log_system("INFO", "自动交易引擎未运行")
            return
        
        try:
            self.running = False
            log_trading("ENGINE_STOP", result="停止成功")
            
            # 等待监控线程结束
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5)
            
            # 关闭所有持仓
            self._close_all_positions("系统停止")
            
            log_system("INFO", "自动交易引擎已停止")
            
        except Exception as e:
            log_trading("ENGINE_STOP", error_message=str(e))
            log_system("ERROR", f"停止自动交易引擎失败: {e}")
    
    def _monitoring_loop(self):
        """监控主循环"""
        log_system("INFO", "监控循环启动")
        
        while self.running:
            try:
                # 重置每日数据
                self._reset_daily_tracking()
                
                # 监控持仓
                self._monitor_all_positions()
                
                # 更新余额
                self._update_balance()
                
                # 检查风险限制
                if self._should_stop_trading():
                    log_system("WARNING", "触发风险限制，暂停交易")
                    time.sleep(60)
                    continue
                
                # 健康检查
                self._health_check()
                
                time.sleep(10)  # 每10秒检查一次
                
            except Exception as e:
                log_system("ERROR", f"监控循环出错: {e}")
                time.sleep(30)  # 出错后等待30秒
        
        log_system("INFO", "监控循环结束")
    
    def _reset_daily_tracking(self):
        """重置每日追踪数据"""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            log_system("INFO", f"每日数据重置 - 昨日PnL: {self.daily_pnl:.2f} USDT, 交易次数: {self.daily_trades}")
            self._init_daily_tracking()
    
    def _monitor_all_positions(self):
        """监控所有持仓"""
        if not self.positions:
            return
        
        positions_to_close = []
        
        for symbol, position in self.positions.items():
            try:
                self._monitor_position(position)
                
                # 检查是否需要关闭
                if self._should_close_position(position):
                    positions_to_close.append(position)
                    
            except Exception as e:
                log_system("ERROR", f"监控持仓 {symbol} 失败: {e}")
        
        # 关闭需要关闭的持仓
        for position in positions_to_close:
            self._close_position(position, "监控触发")
    
    def _monitor_position(self, position: TradePosition):
        """监控单个持仓"""
        try:
            current_price = self._get_current_price(position.symbol)
            if not current_price:
                return
            
            # 更新未实现盈亏
            if position.side == 'buy':
                position.unrealized_pnl = (current_price - position.entry_price) * position.quantity
            else:
                position.unrealized_pnl = (position.entry_price - current_price) * position.quantity
            
            # 更新跟踪止损
            self._update_trailing_stop(position, current_price)
            
        except Exception as e:
            log_system("ERROR", f"监控持仓失败: {e}")
    
    def _should_close_position(self, position: TradePosition) -> bool:
        """判断是否应该关闭持仓"""
        try:
            current_price = self._get_current_price(position.symbol)
            if not current_price:
                return False
            
            # 检查止损
            if position.side == 'buy' and current_price <= position.stop_loss:
                return True
            if position.side == 'sell' and current_price >= position.stop_loss:
                return True
            
            # 检查止盈
            if position.side == 'buy' and current_price >= position.take_profit:
                return True
            if position.side == 'sell' and current_price <= position.take_profit:
                return True
            
            # 检查持仓时间（最长持仓24小时）
            if datetime.now() - position.entry_time > timedelta(hours=24):
                return True
            
            return False
            
        except Exception as e:
            log_system("ERROR", f"判断平仓条件失败: {e}")
            return False
    
    def _update_trailing_stop(self, position: TradePosition, current_price: float):
        """更新跟踪止损"""
        try:
            if position.side == 'buy':
                # 价格上涨时，提高止损线
                new_stop = current_price * (1 - self.base_stop_loss)
                if new_stop > position.stop_loss:
                    position.stop_loss = new_stop
            else:
                # 价格下跌时，降低止损线
                new_stop = current_price * (1 + self.base_stop_loss)
                if new_stop < position.stop_loss:
                    position.stop_loss = new_stop
                    
        except Exception as e:
            log_system("ERROR", f"更新跟踪止损失败: {e}")
    
    def _close_position(self, position: TradePosition, reason: str):
        """关闭持仓"""
        try:
            current_price = self._get_current_price(position.symbol)
            if not current_price:
                log_trading("CLOSE_POSITION", 
                          strategy_id=position.strategy_id,
                          symbol=position.symbol,
                          error_message="无法获取当前价格")
                return
            
            # 模拟交易执行
            if self.exchange:
                # 实际交易逻辑
                trade_result = self._execute_close_order(position, current_price)
            else:
                # 模拟交易
                trade_result = self._simulate_close_order(position, current_price)
            
            if trade_result.success:
                # 更新统计
                self.daily_trades += 1
                if trade_result.profit > 0:
                    self.daily_wins += 1
                
                self.daily_pnl += trade_result.profit
                
                # 记录交易
                log_trading("CLOSE_POSITION",
                          strategy_id=position.strategy_id,
                          symbol=position.symbol,
                          price=current_price,
                          quantity=position.quantity,
                          result=f"盈亏: {trade_result.profit:.2f} USDT")
                
                # 从持仓中移除
                if position.symbol in self.positions:
                    del self.positions[position.symbol]
                
                log_system("INFO", f"持仓已关闭: {position.symbol}, 原因: {reason}, 盈亏: {trade_result.profit:.2f} USDT")
            else:
                log_trading("CLOSE_POSITION",
                          strategy_id=position.strategy_id,
                          symbol=position.symbol,
                          error_message=trade_result.message)
                
        except Exception as e:
            log_system("ERROR", f"关闭持仓失败: {e}")
    
    def _simulate_close_order(self, position: TradePosition, current_price: float) -> TradeResult:
        """模拟关闭订单"""
        try:
            # 计算盈亏
            if position.side == 'buy':
                profit = (current_price - position.entry_price) * position.quantity
            else:
                profit = (position.entry_price - current_price) * position.quantity
            
            return TradeResult(
                success=True,
                filled_price=current_price,
                filled_quantity=position.quantity,
                message="模拟交易成功",
                profit=profit
            )
            
        except Exception as e:
            return TradeResult(
                success=False,
                message=f"模拟交易失败: {e}"
            )
    
    def _execute_close_order(self, position: TradePosition, current_price: float) -> TradeResult:
        """执行实际关闭订单"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                if not self.exchange:
                    raise Exception("交易所连接未初始化")
                
                # 实际交易逻辑
                side = 'sell' if position.side == 'buy' else 'buy'
                order = self.exchange.create_market_order(
                    symbol=position.symbol,
                    side=side,
                    amount=position.quantity
                )
                
                # 计算盈亏
                if position.side == 'buy':
                    profit = (order['price'] - position.entry_price) * position.quantity
                else:
                    profit = (position.entry_price - order['price']) * position.quantity
                
                return TradeResult(
                    success=True,
                    order_id=order['id'],
                    filled_price=order['price'],
                    filled_quantity=order['amount'],
                    message="交易执行成功",
                    profit=profit
                )
                
            except Exception as e:
                log_system("ERROR", f"执行关闭订单失败 (第 {attempt + 1} 次): {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 1.5
                else:
                    return TradeResult(
                        success=False,
                        message=f"交易执行重试 {max_retries} 次后失败: {e}"
                    )
    
    def _close_all_positions(self, reason: str):
        """关闭所有持仓"""
        positions_copy = list(self.positions.values())
        for position in positions_copy:
            self._close_position(position, reason)
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """获取当前价格"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                if self.exchange:
                    ticker = self.exchange.fetch_ticker(symbol)
                    return float(ticker['last'])
                else:
                    raise Exception("交易所连接未初始化")
                    
            except Exception as e:
                log_system("ERROR", f"获取 {symbol} 价格失败 (第 {attempt + 1} 次): {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 1.5
                else:
                    log_system("ERROR", f"获取价格重试 {max_retries} 次后仍失败")
                    return None
    
    def _update_balance(self):
        """更新余额"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                if self.exchange:
                    balance = self.exchange.fetch_balance()
                    self.balance = float(balance.get('USDT', {}).get('free', 0))
                    return
                else:
                    raise Exception("交易所连接未初始化")
                    
            except Exception as e:
                log_system("ERROR", f"更新余额失败 (第 {attempt + 1} 次): {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 1.5
                else:
                    log_system("ERROR", f"余额更新重试 {max_retries} 次后仍失败")
    
    def _should_stop_trading(self) -> bool:
        """检查是否应该停止交易"""
        # 每日亏损限制
        if self.daily_pnl < -self.max_daily_loss * self.start_balance:
            return True
        
        # 余额不足
        if self.balance < 10:
            return True
        
        # 每日交易次数限制
        max_daily_trades = self.config.get('trading', {}).get('max_daily_trades', 20)
        if self.daily_trades >= max_daily_trades:
            return True
        
        return False
    
    def _health_check(self):
        """健康检查"""
        try:
            # 检查系统状态
            status = {
                'running': self.running,
                'balance': self.balance,
                'daily_pnl': self.daily_pnl,
                'daily_trades': self.daily_trades,
                'active_positions': len(self.positions)
            }
            
            log_system("DEBUG", f"系统健康检查: {status}")
            
        except Exception as e:
            log_system("ERROR", f"健康检查失败: {e}")
    
    def execute_trade(self, symbol: str, side: str, strategy_id: str, 
                     confidence: float, current_price: float) -> TradeResult:
        """执行交易"""
        if not self.running:
            return TradeResult(success=False, message="交易引擎未运行")
        
        try:
            # 计算仓位大小
            position_size = self.calculate_position_size(symbol, strategy_id, confidence)
            quantity = (self.balance * position_size) / current_price
            
            # 计算止损止盈
            volatility = self._calculate_volatility(symbol)
            stop_loss, take_profit = self.calculate_dynamic_stops(
                symbol, current_price, side, volatility, confidence
            )
            
            # 创建持仓
            position = TradePosition(
                symbol=symbol,
                side=side,
                entry_price=current_price,
                quantity=quantity,
                entry_time=datetime.now(),
                stop_loss=stop_loss,
                take_profit=take_profit,
                strategy_id=strategy_id
            )
            
            # 执行真实交易
            trade_result = self._execute_real_trade(position)
            
            if trade_result.success:
                self.positions[symbol] = position
                log_trading("OPEN_POSITION",
                          strategy_id=strategy_id,
                          symbol=symbol,
                          signal_type=side,
                          price=current_price,
                          quantity=quantity,
                          confidence=confidence,
                          result="交易执行成功")
            else:
                log_trading("OPEN_POSITION",
                          strategy_id=strategy_id,
                          symbol=symbol,
                          signal_type=side,
                          error_message=trade_result.message)
            
            return trade_result
            
        except Exception as e:
            error_msg = f"执行交易失败: {e}"
            log_trading("OPEN_POSITION",
                      strategy_id=strategy_id,
                      symbol=symbol,
                      signal_type=side,
                      error_message=error_msg)
            return TradeResult(success=False, message=error_msg)
    
    def _execute_real_trade(self, position: TradePosition) -> TradeResult:
        """执行实际交易"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                if not self.exchange:
                    raise Exception("交易所连接未初始化")
                
                order = self.exchange.create_market_order(
                    symbol=position.symbol,
                    side=position.side,
                    amount=position.quantity
                )
                
                return TradeResult(
                    success=True,
                    order_id=order['id'],
                    filled_price=order['price'],
                    filled_quantity=order['amount'],
                    message="实际交易成功"
                )
                
            except Exception as e:
                log_system("ERROR", f"执行交易失败 (第 {attempt + 1} 次): {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 1.5
                else:
                    return TradeResult(
                        success=False,
                        message=f"交易执行重试 {max_retries} 次后失败: {e}"
                    )
    
    def calculate_position_size(self, symbol: str, strategy_id: str, confidence: float) -> float:
        """计算仓位大小"""
        base_size = self.base_position_size
        
        # 根据置信度调整
        confidence_multiplier = 0.5 + (confidence * 0.5)
        
        # 根据当日表现调整
        daily_performance_factor = 1.0
        if self.daily_trades > 0:
            daily_win_rate = self.daily_wins / self.daily_trades
            if daily_win_rate > 0.7:
                daily_performance_factor = 1.2
            elif daily_win_rate < 0.4:
                daily_performance_factor = 0.6
        
        final_size = base_size * confidence_multiplier * daily_performance_factor
        final_size = min(final_size, self.max_position_size)
        
        return final_size
    
    def calculate_dynamic_stops(self, symbol: str, entry_price: float, side: str, 
                              volatility: float, confidence: float) -> Tuple[float, float]:
        """计算动态止盈止损"""
        base_sl = self.base_stop_loss
        base_tp = self.base_take_profit
        
        # 根据波动率调整
        volatility_factor = min(volatility / 0.02, 2.0)
        adjusted_sl = base_sl * volatility_factor
        adjusted_tp = base_tp * volatility_factor
        
        # 根据置信度调整
        confidence_factor = 0.7 + (confidence * 0.6)
        adjusted_sl *= (2 - confidence_factor)
        adjusted_tp *= confidence_factor
        
        # 确保风险回报比至少1:2
        if adjusted_tp / adjusted_sl < 2.0:
            adjusted_tp = adjusted_sl * 2.5
        
        if side == 'buy':
            stop_loss = entry_price * (1 - adjusted_sl)
            take_profit = entry_price * (1 + adjusted_tp)
        else:
            stop_loss = entry_price * (1 + adjusted_sl)
            take_profit = entry_price * (1 - adjusted_tp)
        
        return stop_loss, take_profit
    
    def _calculate_volatility(self, symbol: str, period: int = 24) -> float:
        """计算波动率"""
        try:
            if self.exchange:
                # 获取真实历史数据
                ohlcv = self.exchange.fetch_ohlcv(symbol, '1h', limit=period)
                prices = [candle[4] for candle in ohlcv]  # 收盘价
                returns = np.diff(np.log(prices))
                return np.std(returns) * np.sqrt(24)  # 年化波动率
            else:
                # 模拟波动率
                return 0.02  # 2%
                
        except Exception as e:
            log_system("ERROR", f"计算波动率失败: {e}")
            return 0.02
    
    def get_status(self) -> Dict:
        """获取引擎状态"""
        try:
            return {
                'running': self.running,
                'balance': self.balance,
                'start_balance': self.start_balance,
                'daily_pnl': self.daily_pnl,
                'daily_trades': self.daily_trades,
                'daily_wins': self.daily_wins,
                'daily_win_rate': self.daily_wins / max(self.daily_trades, 1),
                'active_positions': len(self.positions),
                'positions': [
                    {
                        'symbol': pos.symbol,
                        'side': pos.side,
                        'entry_price': pos.entry_price,
                        'quantity': pos.quantity,
                        'unrealized_pnl': pos.unrealized_pnl,
                        'strategy_id': pos.strategy_id
                    }
                    for pos in self.positions.values()
                ],
                'exchange_connected': self.exchange is not None,
                'last_update': datetime.now().isoformat()
            }
        except Exception as e:
            log_system("ERROR", f"获取状态失败: {e}")
            return {'error': str(e)}

# 全局交易引擎实例
_trading_engine = None

def get_fixed_trading_engine() -> FixedAutoTradingEngine:
    """获取修复版交易引擎实例"""
    global _trading_engine
    if _trading_engine is None:
        _trading_engine = FixedAutoTradingEngine()
    return _trading_engine 