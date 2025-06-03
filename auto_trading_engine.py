#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
自动交易引擎
实现币安自动下单、动态止盈止损、智能资金管理
"""

import ccxt
import json
import time
import threading
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
import pandas as pd
import numpy as np

@dataclass
class TradePosition:
    """交易持仓"""
    symbol: str
    side: str  # 'buy' or 'sell'
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

class AutoTradingEngine:
    """自动交易引擎"""
    
    def __init__(self, config_file: str = "crypto_config.json"):
        """初始化交易引擎"""
        self.config = self._load_config(config_file)
        self.exchange = self._init_binance()
        self.positions = {}  # symbol -> TradePosition
        self.trade_history = []
        self.balance = 0.0
        self.daily_target_return = 0.05  # 每日5%目标收益
        self.max_daily_loss = 0.03  # 每日最大亏损3%
        self.daily_pnl = 0.0
        self.start_balance = 0.0
        self.trade_lock = threading.Lock()
        
        # 智能资金管理参数
        self.base_position_size = 0.02  # 基础仓位2%
        self.max_position_size = 0.15   # 最大单笔仓位15%
        self.win_rate_threshold = 0.7   # 胜率阈值
        self.profit_factor_threshold = 1.5  # 盈利因子阈值
        
        # 动态止盈止损参数
        self.base_stop_loss = 0.02      # 基础止损2%
        self.base_take_profit = 0.06    # 基础止盈6%
        self.trailing_stop_factor = 0.3 # 跟踪止损因子
        
        self._init_daily_tracking()
        
    def _load_config(self, config_file: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def _init_binance(self) -> ccxt.Exchange:
        """初始化币安交易所"""
        try:
            binance_config = self.config.get('binance', {})
            exchange = ccxt.binance({
                'apiKey': binance_config.get('api_key', ''),
                'secret': binance_config.get('secret_key', ''),
                'sandbox': False,  # 生产环境
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'  # 现货交易
                }
            })
            
            # 测试连接
            balance = exchange.fetch_balance()
            self.balance = float(balance['USDT']['free'])
            self.start_balance = self.balance
            
            logger.info(f"币安交易所初始化成功，USDT余额: {self.balance}")
            return exchange
            
        except Exception as e:
            logger.error(f"币安交易所初始化失败: {e}")
            raise
    
    def _init_daily_tracking(self):
        """初始化每日追踪"""
        self.daily_trades = 0
        self.daily_wins = 0
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
    
    def _reset_daily_tracking(self):
        """重置每日追踪数据"""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            logger.info(f"每日数据重置 - 昨日PnL: {self.daily_pnl:.2f} USDT, 交易次数: {self.daily_trades}")
            self._init_daily_tracking()
    
    def calculate_position_size(self, symbol: str, strategy_id: str, confidence: float) -> float:
        """智能计算仓位大小"""
        # 获取策略历史表现
        strategy_stats = self._get_strategy_stats(strategy_id)
        
        base_size = self.base_position_size
        
        # 根据策略胜率调整
        if strategy_stats['win_rate'] > self.win_rate_threshold:
            size_multiplier = 1.0 + (strategy_stats['win_rate'] - self.win_rate_threshold) * 2
        else:
            size_multiplier = 0.5 + strategy_stats['win_rate']
        
        # 根据盈利因子调整
        if strategy_stats['profit_factor'] > self.profit_factor_threshold:
            size_multiplier *= 1.0 + (strategy_stats['profit_factor'] - self.profit_factor_threshold) * 0.5
        
        # 根据信号置信度调整
        confidence_multiplier = 0.5 + (confidence * 0.5)
        
        # 根据当日表现调整
        daily_performance_factor = 1.0
        if self.daily_trades > 0:
            daily_win_rate = self.daily_wins / self.daily_trades
            if daily_win_rate > 0.7:
                daily_performance_factor = 1.2
            elif daily_win_rate < 0.4:
                daily_performance_factor = 0.6
        
        # 计算最终仓位
        final_size = base_size * size_multiplier * confidence_multiplier * daily_performance_factor
        final_size = min(final_size, self.max_position_size)
        
        # 检查风险限制
        if self._check_risk_limits():
            final_size *= 0.5  # 风险过高时减半仓位
        
        logger.info(f"策略 {strategy_id} 计算仓位: {final_size:.3f} (基础:{base_size}, 置信度:{confidence:.2f}, 胜率:{strategy_stats['win_rate']:.2f})")
        
        return final_size
    
    def calculate_dynamic_stops(self, symbol: str, entry_price: float, side: str, 
                              volatility: float, confidence: float) -> Tuple[float, float]:
        """计算动态止盈止损"""
        
        # 基础止损止盈
        base_sl = self.base_stop_loss
        base_tp = self.base_take_profit
        
        # 根据波动率调整
        volatility_factor = min(volatility / 0.02, 2.0)  # 基准波动率2%
        adjusted_sl = base_sl * volatility_factor
        adjusted_tp = base_tp * volatility_factor
        
        # 根据置信度调整
        confidence_factor = 0.7 + (confidence * 0.6)
        adjusted_sl *= (2 - confidence_factor)  # 置信度高时止损更小
        adjusted_tp *= confidence_factor        # 置信度高时止盈更大
        
        # 确保风险回报比至少1:2
        if adjusted_tp / adjusted_sl < 2.0:
            adjusted_tp = adjusted_sl * 2.5
        
        if side == 'buy':
            stop_loss = entry_price * (1 - adjusted_sl)
            take_profit = entry_price * (1 + adjusted_tp)
        else:  # sell
            stop_loss = entry_price * (1 + adjusted_sl)
            take_profit = entry_price * (1 - adjusted_tp)
        
        logger.info(f"{symbol} 动态止损止盈: SL={stop_loss:.6f} ({adjusted_sl:.1%}), TP={take_profit:.6f} ({adjusted_tp:.1%})")
        
        return stop_loss, take_profit
    
    def execute_trade(self, symbol: str, side: str, strategy_id: str, 
                     confidence: float, current_price: float) -> TradeResult:
        """执行交易"""
        
        with self.trade_lock:
            self._reset_daily_tracking()
            
            # 检查是否已达到每日目标或风险限制
            if self._should_stop_trading():
                return TradeResult(False, message="已达到每日目标或风险限制")
            
            # 检查是否已有该币种持仓
            if symbol in self.positions:
                logger.warning(f"{symbol} 已有持仓，跳过交易")
                return TradeResult(False, message="已有持仓")
            
            try:
                # 计算仓位大小
                position_ratio = self.calculate_position_size(symbol, strategy_id, confidence)
                trade_amount = self.balance * position_ratio
                
                # 获取最新价格和市场信息
                ticker = self.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                # 计算交易数量
                if side == 'buy':
                    quantity = trade_amount / current_price
                else:
                    # 做空需要借币，这里简化为现货交易
                    logger.warning(f"现货交易不支持做空 {symbol}")
                    return TradeResult(False, message="现货不支持做空")
                
                # 精确化数量
                market = self.exchange.market(symbol)
                quantity = float(Decimal(str(quantity)).quantize(
                    Decimal(str(market['precision']['amount'])), rounding=ROUND_DOWN))
                
                if quantity * current_price < 10:  # 最小交易金额10 USDT
                    return TradeResult(False, message="交易金额过小")
                
                # 计算波动率
                volatility = self._calculate_volatility(symbol)
                
                # 计算动态止盈止损
                stop_loss, take_profit = self.calculate_dynamic_stops(
                    symbol, current_price, side, volatility, confidence)
                
                # 执行市价单
                order = self.exchange.create_market_order(symbol, side, quantity)
                
                if order['status'] == 'closed':
                    # 创建持仓记录
                    position = TradePosition(
                        symbol=symbol,
                        side=side,
                        entry_price=order['average'] or current_price,
                        quantity=order['filled'],
                        entry_time=datetime.now(),
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        strategy_id=strategy_id,
                        order_id=order['id']
                    )
                    
                    self.positions[symbol] = position
                    
                    # 更新余额
                    self._update_balance()
                    
                    # 设置止损止盈订单
                    self._set_stop_orders(position)
                    
                    logger.success(f"交易执行成功: {side} {quantity} {symbol} @ {position.entry_price:.6f}")
                    
                    return TradeResult(
                        success=True,
                        order_id=order['id'],
                        filled_price=position.entry_price,
                        filled_quantity=order['filled'],
                        message=f"交易成功 {side} {quantity} {symbol}"
                    )
                else:
                    return TradeResult(False, message=f"订单未完全成交: {order['status']}")
                    
            except Exception as e:
                logger.error(f"执行交易失败 {symbol}: {e}")
                return TradeResult(False, message=f"交易失败: {str(e)}")
    
    def _set_stop_orders(self, position: TradePosition):
        """设置止损止盈订单"""
        try:
            # 币安现货需要使用OCO订单或手动监控
            # 这里使用监控线程的方式
            thread = threading.Thread(
                target=self._monitor_position, 
                args=(position,), 
                daemon=True
            )
            thread.start()
            
        except Exception as e:
            logger.error(f"设置止损止盈失败 {position.symbol}: {e}")
    
    def _monitor_position(self, position: TradePosition):
        """监控持仓的止损止盈"""
        try:
            while position.symbol in self.positions:
                # 获取当前价格
                ticker = self.exchange.fetch_ticker(position.symbol)
                current_price = ticker['last']
                
                # 更新未实现盈亏
                if position.side == 'buy':
                    pnl_ratio = (current_price - position.entry_price) / position.entry_price
                    position.unrealized_pnl = position.quantity * position.entry_price * pnl_ratio
                    
                    # 检查止损止盈
                    if current_price <= position.stop_loss:
                        self._close_position(position, "止损")
                        break
                    elif current_price >= position.take_profit:
                        self._close_position(position, "止盈")
                        break
                    
                    # 更新跟踪止损
                    self._update_trailing_stop(position, current_price)
                
                time.sleep(5)  # 每5秒检查一次
                
        except Exception as e:
            logger.error(f"监控持仓失败 {position.symbol}: {e}")
    
    def _update_trailing_stop(self, position: TradePosition, current_price: float):
        """更新跟踪止损"""
        if position.side == 'buy':
            # 如果价格上涨，向上调整止损
            profit_ratio = (current_price - position.entry_price) / position.entry_price
            if profit_ratio > 0.03:  # 盈利超过3%时启动跟踪止损
                new_stop_loss = current_price * (1 - self.base_stop_loss * self.trailing_stop_factor)
                if new_stop_loss > position.stop_loss:
                    position.stop_loss = new_stop_loss
                    logger.info(f"{position.symbol} 跟踪止损更新: {new_stop_loss:.6f}")
    
    def _close_position(self, position: TradePosition, reason: str):
        """平仓"""
        try:
            with self.trade_lock:
                if position.symbol not in self.positions:
                    return
                
                # 执行平仓
                close_side = 'sell' if position.side == 'buy' else 'buy'
                order = self.exchange.create_market_order(
                    position.symbol, close_side, position.quantity)
                
                if order['status'] == 'closed':
                    close_price = order['average']
                    
                    # 计算盈亏
                    if position.side == 'buy':
                        profit = (close_price - position.entry_price) * position.quantity
                    else:
                        profit = (position.entry_price - close_price) * position.quantity
                    
                    # 更新统计
                    self.daily_trades += 1
                    self.daily_pnl += profit
                    
                    if profit > 0:
                        self.daily_wins += 1
                    
                    # 记录交易历史
                    trade_record = {
                        'symbol': position.symbol,
                        'strategy_id': position.strategy_id,
                        'side': position.side,
                        'entry_price': position.entry_price,
                        'close_price': close_price,
                        'quantity': position.quantity,
                        'profit': profit,
                        'profit_ratio': profit / (position.quantity * position.entry_price),
                        'reason': reason,
                        'entry_time': position.entry_time,
                        'close_time': datetime.now()
                    }
                    
                    self.trade_history.append(trade_record)
                    
                    # 移除持仓
                    del self.positions[position.symbol]
                    
                    # 更新余额
                    self._update_balance()
                    
                    logger.success(f"平仓成功 {reason}: {position.symbol} 盈亏 {profit:.2f} USDT ({profit/(position.quantity*position.entry_price)*100:.2f}%)")
                    
        except Exception as e:
            logger.error(f"平仓失败 {position.symbol}: {e}")
    
    def _calculate_volatility(self, symbol: str, period: int = 24) -> float:
        """计算价格波动率"""
        try:
            # 获取24小时K线数据
            ohlcv = self.exchange.fetch_ohlcv(symbol, '1h', limit=period)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # 计算收益率
            df['returns'] = df['close'].pct_change()
            volatility = df['returns'].std()
            
            return float(volatility) if volatility else 0.02
            
        except Exception as e:
            logger.error(f"计算波动率失败 {symbol}: {e}")
            return 0.02  # 默认2%波动率
    
    def _get_strategy_stats(self, strategy_id: str) -> Dict:
        """获取策略统计数据"""
        strategy_trades = [t for t in self.trade_history if t['strategy_id'] == strategy_id]
        
        if not strategy_trades:
            return {
                'win_rate': 0.5,
                'profit_factor': 1.0,
                'avg_profit': 0.0,
                'total_trades': 0
            }
        
        wins = [t for t in strategy_trades if t['profit'] > 0]
        losses = [t for t in strategy_trades if t['profit'] < 0]
        
        win_rate = len(wins) / len(strategy_trades) if strategy_trades else 0.5
        total_profit = sum(t['profit'] for t in wins)
        total_loss = abs(sum(t['profit'] for t in losses))
        profit_factor = total_profit / total_loss if total_loss > 0 else 1.0
        
        return {
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_profit': sum(t['profit'] for t in strategy_trades) / len(strategy_trades),
            'total_trades': len(strategy_trades)
        }
    
    def _check_risk_limits(self) -> bool:
        """检查风险限制"""
        # 检查每日亏损限制
        if self.daily_pnl < -self.balance * self.max_daily_loss:
            logger.warning("已达到每日最大亏损限制")
            return True
        
        # 检查持仓数量
        if len(self.positions) >= 8:  # 最多8个持仓
            logger.warning("持仓数量过多")
            return True
        
        return False
    
    def _should_stop_trading(self) -> bool:
        """判断是否应该停止交易"""
        # 已达到每日目标收益
        if self.daily_pnl >= self.balance * self.daily_target_return:
            logger.info(f"已达到每日目标收益: {self.daily_pnl:.2f} USDT")
            return True
        
        # 风险限制
        if self._check_risk_limits():
            return True
        
        return False
    
    def _update_balance(self):
        """更新账户余额"""
        try:
            balance = self.exchange.fetch_balance()
            self.balance = float(balance['USDT']['free'])
        except Exception as e:
            logger.error(f"更新余额失败: {e}")
    
    def get_status(self) -> Dict:
        """获取交易引擎状态"""
        self._reset_daily_tracking()
        
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        return {
            'balance': self.balance,
            'start_balance': self.start_balance,
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'daily_wins': self.daily_wins,
            'daily_win_rate': self.daily_wins / self.daily_trades if self.daily_trades > 0 else 0,
            'positions_count': len(self.positions),
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_pnl': self.daily_pnl + total_unrealized_pnl,
            'daily_return': (self.daily_pnl + total_unrealized_pnl) / self.start_balance,
            'positions': [
                {
                    'symbol': pos.symbol,
                    'side': pos.side,
                    'quantity': pos.quantity,
                    'entry_price': pos.entry_price,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'strategy_id': pos.strategy_id
                }
                for pos in self.positions.values()
            ]
        }

# 全局交易引擎实例
_trading_engine = None

def get_trading_engine() -> AutoTradingEngine:
    """获取交易引擎实例"""
    global _trading_engine
    if _trading_engine is None:
        _trading_engine = AutoTradingEngine()
    return _trading_engine 