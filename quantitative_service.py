#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
量化交易服务模块
包含策略管理、信号生成、持仓监控、收益统计等功能
"""

import sqlite3
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import numpy as np
from loguru import logger

# 策略类型枚举
class StrategyType(Enum):
    MOMENTUM = "momentum"          # 动量策略
    MEAN_REVERSION = "mean_reversion"  # 均值回归策略
    BREAKOUT = "breakout"         # 突破策略
    GRID_TRADING = "grid_trading"  # 网格交易策略
    HIGH_FREQUENCY = "high_frequency"  # 高频交易策略
    TREND_FOLLOWING = "trend_following"  # 趋势跟踪策略

# 信号类型枚举
class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

# 订单状态枚举
class OrderStatus(Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    FAILED = "failed"

@dataclass
class StrategyConfig:
    """策略配置"""
    id: str
    name: str
    strategy_type: StrategyType
    symbol: str
    enabled: bool
    parameters: Dict[str, Any]
    created_time: datetime
    updated_time: datetime

@dataclass
class TradingSignal:
    """交易信号"""
    id: str
    strategy_id: str
    symbol: str
    signal_type: SignalType
    price: float
    quantity: float
    confidence: float
    timestamp: datetime
    executed: bool

@dataclass
class TradingOrder:
    """交易订单"""
    id: str
    strategy_id: str
    signal_id: str
    symbol: str
    side: str  # buy/sell
    quantity: float
    price: float
    status: OrderStatus
    created_time: datetime
    executed_time: Optional[datetime] = None
    execution_price: Optional[float] = None

@dataclass
class Position:
    """持仓信息"""
    symbol: str
    quantity: float
    avg_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    updated_time: datetime

@dataclass
class PerformanceMetrics:
    """绩效指标"""
    total_return: float
    daily_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    profitable_trades: int
    timestamp: datetime

class DatabaseManager:
    """数据库管理类"""
    
    def __init__(self, db_path: str = "quantitative.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 策略配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quant_strategies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    strategy_type TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    enabled BOOLEAN NOT NULL,
                    parameters TEXT NOT NULL,
                    created_time TIMESTAMP NOT NULL,
                    updated_time TIMESTAMP NOT NULL
                )
            """)
            
            # 交易信号表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading_signals (
                    id TEXT PRIMARY KEY,
                    strategy_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    confidence REAL NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    executed BOOLEAN NOT NULL,
                    FOREIGN KEY (strategy_id) REFERENCES quant_strategies (id)
                )
            """)
            
            # 交易订单表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading_orders (
                    id TEXT PRIMARY KEY,
                    strategy_id TEXT NOT NULL,
                    signal_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_time TIMESTAMP NOT NULL,
                    executed_time TIMESTAMP,
                    execution_price REAL,
                    FOREIGN KEY (strategy_id) REFERENCES quant_strategies (id),
                    FOREIGN KEY (signal_id) REFERENCES trading_signals (id)
                )
            """)
            
            # 持仓表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    symbol TEXT PRIMARY KEY,
                    quantity REAL NOT NULL,
                    avg_price REAL NOT NULL,
                    current_price REAL NOT NULL,
                    unrealized_pnl REAL NOT NULL,
                    realized_pnl REAL NOT NULL,
                    updated_time TIMESTAMP NOT NULL
                )
            """)
            
            # 绩效指标表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_return REAL NOT NULL,
                    daily_return REAL NOT NULL,
                    max_drawdown REAL NOT NULL,
                    sharpe_ratio REAL NOT NULL,
                    win_rate REAL NOT NULL,
                    total_trades INTEGER NOT NULL,
                    profitable_trades INTEGER NOT NULL,
                    timestamp TIMESTAMP NOT NULL
                )
            """)
            
            # 操作日志表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS operation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    operation_detail TEXT NOT NULL,
                    user_id TEXT DEFAULT 'system',
                    result TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL
                )
            """)
            
            conn.commit()
            logger.info("数据库初始化完成")

class QuantitativeStrategy:
    """量化策略基类"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.is_running = False
        self.last_signal_time = None
        
    def start(self):
        """启动策略"""
        self.is_running = True
        logger.info(f"策略 {self.config.name} 已启动")
        
    def stop(self):
        """停止策略"""
        self.is_running = False
        logger.info(f"策略 {self.config.name} 已停止")
        
    def generate_signal(self, price_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """生成交易信号（子类实现）"""
        raise NotImplementedError
        
    def update_parameters(self, parameters: Dict[str, Any]):
        """更新策略参数"""
        self.config.parameters.update(parameters)
        self.config.updated_time = datetime.now()

class MomentumStrategy(QuantitativeStrategy):
    """动量策略 - 优化版本，追求高收益"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.price_history = []
        self.volume_history = []
        self.rsi_values = []
        self.macd_values = []
        
    def generate_signal(self, price_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """基于多重技术指标的动量策略 - 优化版"""
        if not self.is_running:
            return None
            
        current_price = price_data.get('price', 0)
        current_volume = price_data.get('volume', 0)
        
        self.price_history.append(current_price)
        self.volume_history.append(current_volume)
        
        # 保留最近N个价格点
        lookback_period = self.config.parameters.get('lookback_period', 20)
        if len(self.price_history) > lookback_period * 3:  # 保留更多历史数据
            self.price_history.pop(0)
            self.volume_history.pop(0)
            
        if len(self.price_history) < lookback_period:
            return None
            
        # 计算多重技术指标
        prices = pd.Series(self.price_history)
        volumes = pd.Series(self.volume_history)
        
        # 1. 动量指标
        returns = prices.pct_change().dropna()
        momentum = returns.rolling(window=min(10, len(returns))).mean().iloc[-1]
        
        # 2. RSI指标
        rsi = self._calculate_rsi(prices, period=14)
        
        # 3. MACD指标
        macd_line, signal_line = self._calculate_macd(prices)
        
        # 4. 成交量确认
        volume_ma = volumes.rolling(window=min(20, len(volumes))).mean().iloc[-1]
        volume_ratio = current_volume / volume_ma if volume_ma > 0 else 1
        
        # 5. 价格突破
        high_20 = prices.rolling(window=20).max().iloc[-1]
        low_20 = prices.rolling(window=20).min().iloc[-1]
        price_position = (current_price - low_20) / (high_20 - low_20) if high_20 > low_20 else 0.5
        
        # 综合信号判断 - 多重确认机制
        threshold = self.config.parameters.get('momentum_threshold', self.config.parameters.get('threshold', 0.001))
        quantity = self.config.parameters.get('quantity', 1.0)
        
        # 强烈买入信号条件 (追求高收益)
        strong_buy_conditions = [
            momentum > threshold * 2,  # 强劲动量
            rsi < 30,  # 超卖后反弹
            macd_line > signal_line,  # MACD金叉
            volume_ratio > 1.5,  # 成交量放大
            price_position > 0.8  # 价格接近高点突破
        ]
        
        # 强烈卖出信号条件
        strong_sell_conditions = [
            momentum < -threshold * 2,  # 强劲下跌动量
            rsi > 70,  # 超买后回调
            macd_line < signal_line,  # MACD死叉
            volume_ratio > 1.5,  # 成交量放大确认
            price_position < 0.2  # 价格接近低点破位
        ]
        
        # 计算信号强度和置信度
        buy_score = sum(strong_buy_conditions)
        sell_score = sum(strong_sell_conditions)
        
        signal_type = None
        confidence = 0
        adjusted_quantity = quantity
        
        if buy_score >= 3:  # 至少3个指标确认买入
            signal_type = SignalType.BUY
            confidence = min(buy_score / 5.0, 1.0)
            # 高置信度时增加仓位
            adjusted_quantity = quantity * (1 + confidence)
        elif sell_score >= 3:  # 至少3个指标确认卖出
            signal_type = SignalType.SELL
            confidence = min(sell_score / 5.0, 1.0)
            adjusted_quantity = quantity * (1 + confidence)
        else:
            return None
            
        signal = TradingSignal(
            id=f"signal_{int(time.time() * 1000)}",
            strategy_id=self.config.id,
            symbol=self.config.symbol,
            signal_type=signal_type,
            price=current_price,
            quantity=adjusted_quantity,
            confidence=confidence,
            timestamp=datetime.now(),
            executed=False
        )
        
        return signal
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """计算RSI指标"""
        if len(prices) < period + 1:
            return 50
            
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
    
    def _calculate_macd(self, prices: pd.Series) -> tuple:
        """计算MACD指标"""
        if len(prices) < 26:
            return 0, 0
            
        exp1 = prices.ewm(span=12).mean()
        exp2 = prices.ewm(span=26).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=9).mean()
        
        return macd_line.iloc[-1], signal_line.iloc[-1]

class MeanReversionStrategy(QuantitativeStrategy):
    """均值回归策略 - 优化版本，动态参数调整"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.price_history = []
        self.volume_history = []
        self.volatility_history = []
        
    def generate_signal(self, price_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """基于动态布林带和波动率的均值回归策略"""
        if not self.is_running:
            return None
            
        current_price = price_data.get('price', 0)
        current_volume = price_data.get('volume', 0)
        
        self.price_history.append(current_price)
        self.volume_history.append(current_volume)
        
        lookback_period = self.config.parameters.get('lookback_period', 20)
        if len(self.price_history) > lookback_period * 2:
            self.price_history.pop(0)
            self.volume_history.pop(0)
            
        if len(self.price_history) < lookback_period:
            return None
            
        # 计算动态技术指标
        prices = pd.Series(self.price_history)
        volumes = pd.Series(self.volume_history)
        
        # 1. 动态布林带计算
        volatility = self._calculate_volatility(prices)
        self.volatility_history.append(volatility)
        if len(self.volatility_history) > 10:
            self.volatility_history.pop(0)
            
        # 根据市场波动率动态调整布林带宽度
        base_std_multiplier = self.config.parameters.get('std_multiplier', 2.0)
        volatility_factor = self._get_volatility_factor()
        dynamic_std_multiplier = base_std_multiplier * volatility_factor
        
        sma = prices.rolling(window=lookback_period).mean().iloc[-1]
        std = prices.rolling(window=lookback_period).std().iloc[-1]
        
        upper_band = sma + dynamic_std_multiplier * std
        lower_band = sma - dynamic_std_multiplier * std
        middle_band = sma
        
        # 2. 计算均值回归强度
        distance_from_mean = abs(current_price - middle_band) / std if std > 0 else 0
        
        # 3. 成交量分析
        volume_ma = volumes.rolling(window=min(10, len(volumes))).mean().iloc[-1]
        volume_ratio = current_volume / volume_ma if volume_ma > 0 else 1
        
        # 4. 短期趋势确认
        short_ma = prices.rolling(window=5).mean().iloc[-1]
        medium_ma = prices.rolling(window=10).mean().iloc[-1]
        
        # 5. 波动率突破确认
        volatility_breakout = volatility > np.mean(self.volatility_history) * 1.5 if self.volatility_history else False
        
        quantity = self.config.parameters.get('quantity', 1.0)
        
        # 高置信度信号条件
        signal_type = None
        confidence = 0
        adjusted_quantity = quantity
        
        # 强力买入信号 (价格大幅偏离下轨)
        if current_price < lower_band:
            # 计算偏离程度
            deviation_ratio = (lower_band - current_price) / (upper_band - lower_band)
            
            # 确认条件
            buy_confirmations = [
                deviation_ratio > 0.1,  # 显著偏离下轨
                short_ma < medium_ma,  # 短期下跌确认
                volume_ratio > 1.2,  # 成交量增加
                distance_from_mean > 1.5,  # 距离均值较远
                volatility_breakout  # 波动率突破
            ]
            
            confirmation_count = sum(buy_confirmations)
            if confirmation_count >= 3:
                signal_type = SignalType.BUY
                confidence = min(confirmation_count / 5.0 + deviation_ratio, 1.0)
                # 根据偏离程度和确认强度调整仓位
                adjusted_quantity = quantity * (1 + deviation_ratio + confidence * 0.5)
                
        # 强力卖出信号 (价格大幅偏离上轨)
        elif current_price > upper_band:
            # 计算偏离程度
            deviation_ratio = (current_price - upper_band) / (upper_band - lower_band)
            
            # 确认条件
            sell_confirmations = [
                deviation_ratio > 0.1,  # 显著偏离上轨
                short_ma > medium_ma,  # 短期上涨确认
                volume_ratio > 1.2,  # 成交量增加
                distance_from_mean > 1.5,  # 距离均值较远
                volatility_breakout  # 波动率突破
            ]
            
            confirmation_count = sum(sell_confirmations)
            if confirmation_count >= 3:
                signal_type = SignalType.SELL
                confidence = min(confirmation_count / 5.0 + deviation_ratio, 1.0)
                adjusted_quantity = quantity * (1 + deviation_ratio + confidence * 0.5)
        
        if signal_type is None:
            return None
            
        signal = TradingSignal(
            id=f"signal_{int(time.time() * 1000)}",
            strategy_id=self.config.id,
            symbol=self.config.symbol,
            signal_type=signal_type,
            price=current_price,
            quantity=adjusted_quantity,
            confidence=confidence,
            timestamp=datetime.now(),
            executed=False
        )
        
        return signal
    
    def _calculate_volatility(self, prices: pd.Series) -> float:
        """计算历史波动率"""
        if len(prices) < 2:
            return 0
        returns = prices.pct_change().dropna()
        return returns.std() * np.sqrt(252)  # 年化波动率
    
    def _get_volatility_factor(self) -> float:
        """根据波动率历史调整布林带宽度"""
        if not self.volatility_history:
            return 1.0
            
        current_vol = self.volatility_history[-1]
        avg_vol = np.mean(self.volatility_history)
        
        # 高波动时扩大布林带，低波动时缩小布林带
        if current_vol > avg_vol * 1.5:
            return 1.3  # 扩大30%
        elif current_vol < avg_vol * 0.7:
            return 0.8  # 缩小20%
        else:
            return 1.0  # 保持不变

class BreakoutStrategy(QuantitativeStrategy):
    """突破策略 - 优化版本，多重确认机制"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.price_history = []
        self.volume_history = []
        self.high_history = []
        self.low_history = []
        
    def generate_signal(self, price_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """基于多重确认的突破策略"""
        if not self.is_running:
            return None
            
        current_price = price_data.get('price', 0)
        current_volume = price_data.get('volume', 0)
        current_high = price_data.get('high', current_price)
        current_low = price_data.get('low', current_price)
        
        self.price_history.append(current_price)
        self.volume_history.append(current_volume)
        self.high_history.append(current_high)
        self.low_history.append(current_low)
        
        lookback_period = self.config.parameters.get('lookback_period', 20)
        if len(self.price_history) > lookback_period * 2:
            self.price_history.pop(0)
            self.volume_history.pop(0)
            self.high_history.pop(0)
            self.low_history.pop(0)
            
        if len(self.price_history) < lookback_period:
            return None
            
        # 计算多重技术指标
        prices = pd.Series(self.price_history)
        volumes = pd.Series(self.volume_history)
        highs = pd.Series(self.high_history)
        lows = pd.Series(self.low_history)
        
        # 1. 动态支撑阻力计算
        resistance_periods = [10, 20, 50]  # 多时间框架
        support_periods = [10, 20, 50]
        
        resistances = [highs.rolling(window=min(p, len(highs))).max().iloc[-1] for p in resistance_periods]
        supports = [lows.rolling(window=min(p, len(lows))).min().iloc[-1] for p in support_periods]
        
        # 取最强阻力和支撑
        key_resistance = max(resistances)
        key_support = min(supports)
        
        # 2. 成交量突破确认
        volume_ma_short = volumes.rolling(window=min(10, len(volumes))).mean().iloc[-1]
        volume_ma_long = volumes.rolling(window=min(20, len(volumes))).mean().iloc[-1]
        volume_ratio = current_volume / volume_ma_short if volume_ma_short > 0 else 1
        volume_trend = volume_ma_short / volume_ma_long if volume_ma_long > 0 else 1
        
        # 3. 价格动量分析
        price_momentum = self._calculate_momentum(prices, period=10)
        price_acceleration = self._calculate_acceleration(prices, period=5)
        
        # 4. 突破幅度计算
        breakout_threshold = self.config.parameters.get('breakout_threshold', 0.01)
        quantity = self.config.parameters.get('quantity', 1.0)
        
        # 5. 市场结构分析
        higher_highs = self._count_higher_highs(highs, period=10)
        lower_lows = self._count_lower_lows(lows, period=10)
        
        signal_type = None
        confidence = 0
        adjusted_quantity = quantity
        
        # 向上突破确认
        upward_breakout_conditions = [
            current_price > key_resistance * (1 + breakout_threshold),  # 价格突破
            volume_ratio > 2.0,  # 成交量爆发
            volume_trend > 1.1,  # 成交量趋势向上
            price_momentum > 0.005,  # 正向动量
            price_acceleration > 0,  # 价格加速
            higher_highs >= 2,  # 形成上升趋势
            current_price > prices.rolling(window=5).mean().iloc[-1]  # 短期均线确认
        ]
        
        # 向下突破确认
        downward_breakout_conditions = [
            current_price < key_support * (1 - breakout_threshold),  # 价格跌破
            volume_ratio > 2.0,  # 成交量爆发
            volume_trend > 1.1,  # 成交量趋势向上
            price_momentum < -0.005,  # 负向动量
            price_acceleration < 0,  # 价格加速下跌
            lower_lows >= 2,  # 形成下降趋势
            current_price < prices.rolling(window=5).mean().iloc[-1]  # 短期均线确认
        ]
        
        upward_score = sum(upward_breakout_conditions)
        downward_score = sum(downward_breakout_conditions)
        
        # 强力突破信号 (至少5个条件确认)
        if upward_score >= 5:
            signal_type = SignalType.BUY
            confidence = min(upward_score / 7.0, 1.0)
            
            # 计算突破强度
            breakout_strength = (current_price - key_resistance) / key_resistance
            adjusted_quantity = quantity * (1 + confidence + breakout_strength * 2)
            
        elif downward_score >= 5:
            signal_type = SignalType.SELL
            confidence = min(downward_score / 7.0, 1.0)
            
            # 计算突破强度
            breakout_strength = (key_support - current_price) / key_support
            adjusted_quantity = quantity * (1 + confidence + breakout_strength * 2)
        
        if signal_type is None:
            return None
            
        signal = TradingSignal(
            id=f"signal_{int(time.time() * 1000)}",
            strategy_id=self.config.id,
            symbol=self.config.symbol,
            signal_type=signal_type,
            price=current_price,
            quantity=adjusted_quantity,
            confidence=confidence,
            timestamp=datetime.now(),
            executed=False
        )
        
        return signal
    
    def _calculate_momentum(self, prices: pd.Series, period: int = 10) -> float:
        """计算价格动量"""
        if len(prices) < period + 1:
            return 0
        return (prices.iloc[-1] - prices.iloc[-period-1]) / prices.iloc[-period-1]
    
    def _calculate_acceleration(self, prices: pd.Series, period: int = 5) -> float:
        """计算价格加速度"""
        if len(prices) < period * 2:
            return 0
        recent_momentum = self._calculate_momentum(prices.iloc[-period:], period // 2)
        past_momentum = self._calculate_momentum(prices.iloc[-period*2:-period], period // 2)
        return recent_momentum - past_momentum
    
    def _count_higher_highs(self, highs: pd.Series, period: int = 10) -> int:
        """计算近期创新高次数"""
        if len(highs) < period:
            return 0
        recent_highs = highs.iloc[-period:]
        count = 0
        for i in range(1, len(recent_highs)):
            if recent_highs.iloc[i] > recent_highs.iloc[i-1]:
                count += 1
        return count
    
    def _count_lower_lows(self, lows: pd.Series, period: int = 10) -> int:
        """计算近期创新低次数"""
        if len(lows) < period:
            return 0
        recent_lows = lows.iloc[-period:]
        count = 0
        for i in range(1, len(recent_lows)):
            if recent_lows.iloc[i] < recent_lows.iloc[i-1]:
                count += 1
        return count

class GridTradingStrategy(QuantitativeStrategy):
    """网格交易策略 - 适合横盘震荡市场，稳定获利"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.price_history = []
        self.grid_levels = []
        self.last_trade_price = None
        self.position_count = 0
        
    def generate_signal(self, price_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """网格交易信号生成"""
        if not self.is_running:
            return None
            
        current_price = price_data.get('price', 0)
        self.price_history.append(current_price)
        
        # 保持价格历史
        lookback_period = self.config.parameters.get('lookback_period', 100)
        if len(self.price_history) > lookback_period:
            self.price_history.pop(0)
            
        if len(self.price_history) < 50:  # 需要足够数据来计算网格
            return None
            
        # 计算网格参数
        grid_spacing = self.config.parameters.get('grid_spacing', 0.02)  # 2%网格间距
        grid_count = self.config.parameters.get('grid_count', 10)  # 网格数量
        quantity = self.config.parameters.get('quantity', 1.0)
        
        # 动态计算网格中心价格
        prices = pd.Series(self.price_history)
        center_price = prices.median()  # 使用中位数作为中心
        
        # 生成网格级别
        if not self.grid_levels:
            self._generate_grid_levels(center_price, grid_spacing, grid_count)
        
        # 检查价格是否触及网格线
        signal_type = None
        confidence = 0.8  # 网格策略置信度固定较高
        
        for i, level in enumerate(self.grid_levels):
            price_diff = abs(current_price - level) / level
            
            # 价格接近网格线（0.1%容差）
            if price_diff < 0.001:
                # 判断买卖方向
                if current_price <= center_price and (not self.last_trade_price or current_price < self.last_trade_price * 0.98):
                    # 在中心价格以下且价格下跌时买入
                    signal_type = SignalType.BUY
                    self.last_trade_price = current_price
                    self.position_count += 1
                elif current_price >= center_price and (not self.last_trade_price or current_price > self.last_trade_price * 1.02):
                    # 在中心价格以上且价格上涨时卖出
                    signal_type = SignalType.SELL
                    self.last_trade_price = current_price
                    self.position_count -= 1
                break
        
        if signal_type is None:
            return None
            
        # 根据位置调整交易量
        adjusted_quantity = quantity * min(1 + abs(self.position_count) * 0.1, 3.0)  # 最多放大3倍
        
        signal = TradingSignal(
            id=f"signal_{int(time.time() * 1000)}",
            strategy_id=self.config.id,
            symbol=self.config.symbol,
            signal_type=signal_type,
            price=current_price,
            quantity=adjusted_quantity,
            confidence=confidence,
            timestamp=datetime.now(),
            executed=False
        )
        
        return signal
    
    def _generate_grid_levels(self, center_price: float, spacing: float, count: int):
        """生成网格级别"""
        self.grid_levels = []
        for i in range(-count//2, count//2 + 1):
            level = center_price * (1 + i * spacing)
            self.grid_levels.append(level)
        self.grid_levels.sort()

class HighFrequencyStrategy(QuantitativeStrategy):
    """高频交易策略 - 追求小幅价差快速获利"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.price_history = []
        self.volume_history = []
        self.last_signal_time = None
        self.micro_trend_history = []
        
    def generate_signal(self, price_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """高频交易信号生成"""
        if not self.is_running:
            return None
            
        current_time = datetime.now()
        current_price = price_data.get('price', 0)
        current_volume = price_data.get('volume', 0)
        
        # 高频策略需要限制信号频率
        if self.last_signal_time and (current_time - self.last_signal_time).total_seconds() < 30:
            return None
            
        self.price_history.append(current_price)
        self.volume_history.append(current_volume)
        
        # 只保留最近的短期数据
        max_history = 30  # 只看最近30个数据点
        if len(self.price_history) > max_history:
            self.price_history.pop(0)
            self.volume_history.pop(0)
            
        if len(self.price_history) < 10:
            return None
            
        # 计算微观市场指标
        prices = pd.Series(self.price_history)
        volumes = pd.Series(self.volume_history)
        
        # 1. 微趋势识别
        micro_trend = self._calculate_micro_trend(prices)
        self.micro_trend_history.append(micro_trend)
        if len(self.micro_trend_history) > 10:
            self.micro_trend_history.pop(0)
        
        # 2. 短期动量
        short_momentum = (prices.iloc[-1] - prices.iloc[-3]) / prices.iloc[-3] if len(prices) >= 3 else 0
        
        # 3. 成交量激增
        volume_spike = self._detect_volume_spike(volumes)
        
        # 4. 价格微波动
        price_volatility = prices.rolling(window=5).std().iloc[-1] if len(prices) >= 5 else 0
        volatility_threshold = self.config.parameters.get('volatility_threshold', 0.001)
        
        # 5. 订单簿不平衡模拟（基于价格变化速度）
        order_imbalance = self._estimate_order_imbalance(prices, volumes)
        
        quantity = self.config.parameters.get('quantity', 0.5)  # 高频交易使用较小仓位
        min_profit_threshold = self.config.parameters.get('min_profit', 0.0005)  # 0.05%最小利润
        
        signal_type = None
        confidence = 0
        
        # 高频买入条件
        hf_buy_conditions = [
            short_momentum > min_profit_threshold,  # 正向动量
            volume_spike,  # 成交量激增
            price_volatility > volatility_threshold,  # 足够波动
            order_imbalance > 0.6,  # 买单占优
            micro_trend > 0.5,  # 微趋势向上
        ]
        
        # 高频卖出条件
        hf_sell_conditions = [
            short_momentum < -min_profit_threshold,  # 负向动量
            volume_spike,  # 成交量激增
            price_volatility > volatility_threshold,  # 足够波动
            order_imbalance < 0.4,  # 卖单占优
            micro_trend < 0.5,  # 微趋势向下
        ]
        
        buy_score = sum(hf_buy_conditions)
        sell_score = sum(hf_sell_conditions)
        
        if buy_score >= 4:  # 至少4个条件确认
            signal_type = SignalType.BUY
            confidence = min(buy_score / 5.0 + abs(short_momentum) * 100, 1.0)
        elif sell_score >= 4:
            signal_type = SignalType.SELL
            confidence = min(sell_score / 5.0 + abs(short_momentum) * 100, 1.0)
        
        if signal_type is None:
            return None
            
        self.last_signal_time = current_time
        
        # 高频策略根据信号强度调整仓位
        adjusted_quantity = quantity * (1 + confidence * 2)
        
        signal = TradingSignal(
            id=f"signal_{int(time.time() * 1000)}",
            strategy_id=self.config.id,
            symbol=self.config.symbol,
            signal_type=signal_type,
            price=current_price,
            quantity=adjusted_quantity,
            confidence=confidence,
            timestamp=current_time,
            executed=False
        )
        
        return signal
    
    def _calculate_micro_trend(self, prices: pd.Series) -> float:
        """计算微趋势（0-1，0.5为中性）"""
        if len(prices) < 5:
            return 0.5
        recent_slope = (prices.iloc[-1] - prices.iloc[-5]) / prices.iloc[-5]
        return max(0, min(1, 0.5 + recent_slope * 100))  # 标准化到0-1
    
    def _detect_volume_spike(self, volumes: pd.Series) -> bool:
        """检测成交量激增"""
        if len(volumes) < 5:
            return False
        current_vol = volumes.iloc[-1]
        avg_vol = volumes.iloc[-5:-1].mean()
        return current_vol > avg_vol * 2.0
    
    def _estimate_order_imbalance(self, prices: pd.Series, volumes: pd.Series) -> float:
        """估算订单簿不平衡（0-1，>0.5买单占优）"""
        if len(prices) < 3:
            return 0.5
        price_change = prices.iloc[-1] - prices.iloc[-2]
        volume_current = volumes.iloc[-1] if len(volumes) > 0 else 1
        
        # 简化的不平衡估算：价格上涨+高成交量 = 买单占优
        if price_change > 0:
            return min(1.0, 0.6 + price_change * volume_current * 10)
        else:
            return max(0.0, 0.4 + price_change * volume_current * 10)

class TrendFollowingStrategy(QuantitativeStrategy):
    """趋势跟踪策略 - 捕获长期趋势获得大幅收益"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.price_history = []
        self.volume_history = []
        self.trend_strength_history = []
        self.position_state = "neutral"  # neutral, long, short
        
    def generate_signal(self, price_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """趋势跟踪信号生成"""
        if not self.is_running:
            return None
            
        current_price = price_data.get('price', 0)
        current_volume = price_data.get('volume', 0)
        
        self.price_history.append(current_price)
        self.volume_history.append(current_volume)
        
        lookback_period = self.config.parameters.get('lookback_period', 50)
        if len(self.price_history) > lookback_period * 2:
            self.price_history.pop(0)
            self.volume_history.pop(0)
            
        if len(self.price_history) < lookback_period:
            return None
            
        # 计算多重趋势指标
        prices = pd.Series(self.price_history)
        volumes = pd.Series(self.volume_history)
        
        # 1. 多重移动平均线
        ma_short = prices.rolling(window=10).mean().iloc[-1]
        ma_medium = prices.rolling(window=20).mean().iloc[-1]
        ma_long = prices.rolling(window=50).mean().iloc[-1]
        
        # 2. 趋势强度计算
        trend_strength = self._calculate_trend_strength(prices)
        self.trend_strength_history.append(trend_strength)
        if len(self.trend_strength_history) > 20:
            self.trend_strength_history.pop(0)
        
        # 3. ADX指标计算（趋势强度）
        adx = self._calculate_adx(prices, period=14)
        
        # 4. 成交量确认
        volume_ma = volumes.rolling(window=20).mean().iloc[-1]
        volume_ratio = current_volume / volume_ma if volume_ma > 0 else 1
        
        # 5. 价格相对位置
        price_position = self._calculate_price_position(prices, period=50)
        
        quantity = self.config.parameters.get('quantity', 2.0)  # 趋势策略使用较大仓位
        trend_threshold = self.config.parameters.get('trend_threshold', 0.02)  # 2%趋势阈值
        
        signal_type = None
        confidence = 0
        
        # 强烈上涨趋势确认
        uptrend_conditions = [
            ma_short > ma_medium > ma_long,  # 均线多头排列
            current_price > ma_short * (1 + trend_threshold),  # 价格远离短期均线
            trend_strength > 0.7,  # 强趋势
            adx > 25,  # ADX确认趋势强度
            volume_ratio > 1.1,  # 成交量确认
            price_position > 0.7,  # 价格处于高位区域
            self.position_state != "long"  # 避免重复信号
        ]
        
        # 强烈下跌趋势确认
        downtrend_conditions = [
            ma_short < ma_medium < ma_long,  # 均线空头排列
            current_price < ma_short * (1 - trend_threshold),  # 价格远离短期均线
            trend_strength < 0.3,  # 弱趋势（下跌）
            adx > 25,  # ADX确认趋势强度
            volume_ratio > 1.1,  # 成交量确认
            price_position < 0.3,  # 价格处于低位区域
            self.position_state != "short"  # 避免重复信号
        ]
        
        uptrend_score = sum(uptrend_conditions)
        downtrend_score = sum(downtrend_conditions)
        
        if uptrend_score >= 5:  # 强烈上涨趋势
            signal_type = SignalType.BUY
            confidence = min(uptrend_score / 7.0, 1.0)
            self.position_state = "long"
        elif downtrend_score >= 5:  # 强烈下跌趋势
            signal_type = SignalType.SELL
            confidence = min(downtrend_score / 7.0, 1.0)
            self.position_state = "short"
        
        if signal_type is None:
            return None
            
        # 趋势策略根据趋势强度大幅调整仓位
        trend_multiplier = abs(trend_strength - 0.5) * 4  # 0-2倍数
        adjusted_quantity = quantity * (1 + trend_multiplier + confidence)
        
        signal = TradingSignal(
            id=f"signal_{int(time.time() * 1000)}",
            strategy_id=self.config.id,
            symbol=self.config.symbol,
            signal_type=signal_type,
            price=current_price,
            quantity=adjusted_quantity,
            confidence=confidence,
            timestamp=datetime.now(),
            executed=False
        )
        
        return signal
    
    def _calculate_trend_strength(self, prices: pd.Series) -> float:
        """计算趋势强度（0-1）"""
        if len(prices) < 20:
            return 0.5
        
        # 计算线性回归斜率
        x = np.arange(len(prices))
        y = prices.values
        slope, _ = np.polyfit(x, y, 1)
        
        # 标准化斜率到0-1范围
        normalized_slope = np.tanh(slope / np.mean(y) * 1000)  # 放大并限制范围
        return (normalized_slope + 1) / 2  # 转换到0-1范围
    
    def _calculate_adx(self, prices: pd.Series, period: int = 14) -> float:
        """计算平均方向指数ADX"""
        if len(prices) < period + 1:
            return 0
            
        # 简化ADX计算
        price_changes = prices.diff().abs()
        tr = price_changes.rolling(window=period).mean()
        dm_plus = prices.diff().where(prices.diff() > 0, 0).rolling(window=period).mean()
        dm_minus = (-prices.diff()).where(prices.diff() < 0, 0).rolling(window=period).mean()
        
        di_plus = dm_plus / tr * 100
        di_minus = dm_minus / tr * 100
        
        dx = abs(di_plus - di_minus) / (di_plus + di_minus) * 100
        adx = dx.rolling(window=period).mean().iloc[-1]
        
        return adx if not pd.isna(adx) else 0
    
    def _calculate_price_position(self, prices: pd.Series, period: int = 50) -> float:
        """计算价格在周期内的相对位置（0-1）"""
        if len(prices) < period:
            return 0.5
            
        recent_prices = prices.iloc[-period:]
        high = recent_prices.max()
        low = recent_prices.min()
        current = prices.iloc[-1]
        
        if high == low:
            return 0.5
        return (current - low) / (high - low)

class AutomatedStrategyManager:
    """全自动化策略管理系统 - 目标每月100%收益"""
    
    def __init__(self, quantitative_service):
        self.service = quantitative_service
        self.initial_capital = 10000  # 初始资金10000 USDT
        self.monthly_target = 1.0  # 月收益目标100%
        self.risk_limit = 0.05  # 单次风险限制5%
        self.performance_window = 24  # 性能评估窗口24小时
        self.last_optimization = None
        
    def auto_manage_strategies(self):
        """全自动策略管理 - 每小时执行一次"""
        logger.info("开始执行全自动策略管理...")
        
        try:
            # 1. 评估所有策略表现
            strategy_performances = self._evaluate_all_strategies()
            
            # 2. 动态调整资金分配
            self._rebalance_capital(strategy_performances)
            
            # 3. 优化策略参数
            self._optimize_strategy_parameters(strategy_performances)
            
            # 4. 风险管理
            self._risk_management()
            
            # 5. 启停策略决策
            self._strategy_selection(strategy_performances)
            
            # 6. 记录管理日志
            self._log_management_actions(strategy_performances)
            
            logger.info("全自动策略管理完成")
            
        except Exception as e:
            logger.error(f"全自动策略管理出错: {e}")
    
    def _evaluate_all_strategies(self) -> Dict[str, Dict]:
        """评估所有策略表现"""
        strategies = self.service.get_strategies()
        performances = {}
        
        for strategy in strategies:
            strategy_id = strategy['id']
            
            # 计算关键指标
            total_return = strategy.get('total_return', 0)
            daily_return = strategy.get('daily_return', 0)
            win_rate = strategy.get('win_rate', 0)
            total_trades = strategy.get('total_trades', 0)
            
            # 计算夏普比率
            sharpe_ratio = self._calculate_sharpe_ratio(strategy_id)
            
            # 计算最大回撤
            max_drawdown = self._calculate_max_drawdown(strategy_id)
            
            # 计算盈利因子
            profit_factor = self._calculate_profit_factor(strategy_id)
            
            # 综合评分 (0-100)
            score = self._calculate_strategy_score(
                total_return, win_rate, sharpe_ratio, max_drawdown, profit_factor
            )
            
            performances[strategy_id] = {
                'name': strategy['name'],
                'type': strategy['type'],
                'symbol': strategy['symbol'],
                'enabled': strategy['enabled'],
                'total_return': total_return,
                'daily_return': daily_return,
                'win_rate': win_rate,
                'total_trades': total_trades,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'profit_factor': profit_factor,
                'score': score,
                'capital_allocation': self._get_current_allocation(strategy_id)
            }
        
        return performances
    
    def _calculate_strategy_score(self, total_return: float, win_rate: float, 
                                sharpe_ratio: float, max_drawdown: float, profit_factor: float) -> float:
        """计算策略综合评分"""
        # 权重分配
        weights = {
            'return': 0.30,    # 收益率权重30%
            'win_rate': 0.20,  # 胜率权重20%
            'sharpe': 0.25,    # 夏普比率权重25%
            'drawdown': 0.15,  # 最大回撤权重15%
            'profit_factor': 0.10  # 盈利因子权重10%
        }
        
        # 标准化分数
        return_score = min(total_return * 100, 100)  # 收益率转百分比
        win_rate_score = win_rate * 100
        sharpe_score = min(max(sharpe_ratio * 20, 0), 100)  # 夏普比率标准化
        drawdown_score = max(100 - abs(max_drawdown) * 100, 0)  # 回撤越小分数越高
        profit_factor_score = min(profit_factor * 20, 100)
        
        # 加权综合评分
        total_score = (
            return_score * weights['return'] +
            win_rate_score * weights['win_rate'] +
            sharpe_score * weights['sharpe'] +
            drawdown_score * weights['drawdown'] +
            profit_factor_score * weights['profit_factor']
        )
        
        return min(max(total_score, 0), 100)
    
    def _rebalance_capital(self, performances: Dict[str, Dict]):
        """动态资金再平衡 - 优秀策略获得更多资金"""
        # 按评分排序
        sorted_strategies = sorted(performances.items(), key=lambda x: x[1]['score'], reverse=True)
        
        # 资金分配算法
        total_capital = self.initial_capital
        allocations = {}
        
        # 前3名策略获得更多资金
        high_performers = sorted_strategies[:3]
        medium_performers = sorted_strategies[3:5]
        low_performers = sorted_strategies[5:]
        
        # 分配比例
        for i, (strategy_id, perf) in enumerate(high_performers):
            if perf['score'] > 70:  # 高分策略
                allocations[strategy_id] = total_capital * (0.25 - i * 0.05)  # 25%, 20%, 15%
            else:
                allocations[strategy_id] = total_capital * 0.10
        
        for strategy_id, perf in medium_performers:
            allocations[strategy_id] = total_capital * 0.08  # 8%
        
        for strategy_id, perf in low_performers:
            if perf['score'] > 30:
                allocations[strategy_id] = total_capital * 0.05  # 5%
            else:
                allocations[strategy_id] = total_capital * 0.02  # 2%
        
        # 更新策略资金分配
        self._update_capital_allocations(allocations)
        
        logger.info(f"资金再平衡完成，前3名策略: {[perf['name'] for _, perf in high_performers]}")
    
    def _optimize_strategy_parameters(self, performances: Dict[str, Dict]):
        """动态优化策略参数"""
        for strategy_id, perf in performances.items():
            if perf['score'] < 60:  # 表现不佳的策略需要优化
                self._auto_tune_parameters(strategy_id, perf)
    
    def _auto_tune_parameters(self, strategy_id: str, performance: Dict):
        """自动调参优化"""
        strategy = self.service.strategies.get(strategy_id)
        if not strategy:
            return
        
        strategy_type = performance['type']
        current_params = strategy.config.parameters.copy()
        
        # 根据策略类型和表现调整参数
        if strategy_type == 'momentum':
            # 动量策略参数优化
            if performance['win_rate'] < 0.5:
                # 胜率低，提高阈值
                current_params['threshold'] = current_params.get('threshold', 0.001) * 1.2
            if performance['total_return'] < 0:
                # 收益为负，缩短观察期
                current_params['lookback_period'] = max(10, current_params.get('lookback_period', 20) - 5)
                
        elif strategy_type == 'mean_reversion':
            # 均值回归策略参数优化
            if performance['max_drawdown'] > 0.1:
                # 回撤过大，扩大布林带
                current_params['std_multiplier'] = current_params.get('std_multiplier', 2.0) * 1.1
            if performance['total_trades'] < 10:
                # 交易次数过少，缩小布林带
                current_params['std_multiplier'] = current_params.get('std_multiplier', 2.0) * 0.9
                
        elif strategy_type == 'grid_trading':
            # 网格策略参数优化
            if performance['total_return'] < 0.02:
                # 收益过低，调整网格间距
                current_params['grid_spacing'] = current_params.get('grid_spacing', 0.02) * 0.9
            if performance['win_rate'] > 0.8:
                # 胜率过高但收益一般，可能网格过密
                current_params['grid_spacing'] = current_params.get('grid_spacing', 0.02) * 1.1
        
        # 更新策略参数
        self.service.update_strategy(
            strategy_id, 
            strategy.config.name, 
            strategy.config.symbol, 
            current_params
        )
        
        logger.info(f"策略 {performance['name']} 参数已优化")
    
    def _risk_management(self):
        """风险管理"""
        # 检查总体风险敞口
        total_exposure = self._calculate_total_exposure()
        
        if total_exposure > self.initial_capital * 3:  # 总敞口超过3倍资金
            self._reduce_position_sizes()
            logger.warning("总风险敞口过高，已减少仓位")
        
        # 检查单一策略风险
        for strategy_id in self.service.strategies.keys():
            strategy_risk = self._calculate_strategy_risk(strategy_id)
            if strategy_risk > self.risk_limit:
                self._limit_strategy_position(strategy_id)
                logger.warning(f"策略 {strategy_id} 风险过高，已限制仓位")
    
    def _strategy_selection(self, performances: Dict[str, Dict]):
        """智能策略启停决策"""
        for strategy_id, perf in performances.items():
            strategy = self.service.strategies.get(strategy_id)
            if not strategy:
                continue
            
            # 启动高分策略
            if perf['score'] > 70 and not strategy.is_running:
                self.service.start_strategy(strategy_id)
                logger.info(f"启动高分策略: {perf['name']} (评分: {perf['score']:.1f})")
            
            # 停止低分策略
            elif perf['score'] < 30 and strategy.is_running:
                self.service.stop_strategy(strategy_id)
                logger.info(f"停止低分策略: {perf['name']} (评分: {perf['score']:.1f})")
            
            # 重启表现改善的策略
            elif perf['score'] > 60 and not strategy.is_running and perf['total_trades'] > 0:
                self.service.start_strategy(strategy_id)
                logger.info(f"重启改善策略: {perf['name']} (评分: {perf['score']:.1f})")
    
    def _calculate_sharpe_ratio(self, strategy_id: str) -> float:
        """计算夏普比率"""
        # 简化实现
        try:
            daily_returns = self._get_strategy_daily_returns(strategy_id)
            if len(daily_returns) < 7:
                return 0.0
            
            avg_return = np.mean(daily_returns)
            std_return = np.std(daily_returns)
            
            if std_return == 0:
                return 0.0
            
            return avg_return / std_return * np.sqrt(365)  # 年化夏普比率
        except:
            return 0.0
    
    def _calculate_max_drawdown(self, strategy_id: str) -> float:
        """计算最大回撤"""
        try:
            cumulative_returns = self._get_strategy_cumulative_returns(strategy_id)
            if len(cumulative_returns) < 2:
                return 0.0
            
            peak = cumulative_returns[0]
            max_dd = 0.0
            
            for value in cumulative_returns:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak if peak > 0 else 0
                max_dd = max(max_dd, drawdown)
            
            return max_dd
        except:
            return 0.0
    
    def _calculate_profit_factor(self, strategy_id: str) -> float:
        """计算盈利因子"""
        try:
            with sqlite3.connect(self.service.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        SUM(CASE WHEN signal_type = 'sell' AND price > 
                            (SELECT AVG(price) FROM trading_signals s2 
                             WHERE s2.strategy_id = s1.strategy_id 
                             AND s2.signal_type = 'buy' 
                             AND s2.timestamp < s1.timestamp) 
                        THEN price * quantity ELSE 0 END) as profits,
                        SUM(CASE WHEN signal_type = 'sell' AND price < 
                            (SELECT AVG(price) FROM trading_signals s2 
                             WHERE s2.strategy_id = s1.strategy_id 
                             AND s2.signal_type = 'buy' 
                             AND s2.timestamp < s1.timestamp) 
                        THEN price * quantity ELSE 0 END) as losses
                    FROM trading_signals s1
                    WHERE strategy_id = ? AND executed = 1
                """, (strategy_id,))
                
                result = cursor.fetchone()
                if result and result[1] and result[1] > 0:
                    return result[0] / result[1]
                return 1.0
        except:
            return 1.0
    
    def _get_current_allocation(self, strategy_id: str) -> float:
        """获取当前资金分配"""
        # 简化实现，返回平均分配
        return self.initial_capital / len(self.service.strategies) if self.service.strategies else 0
    
    def _update_capital_allocations(self, allocations: Dict[str, float]):
        """更新资金分配"""
        for strategy_id, allocation in allocations.items():
            strategy = self.service.strategies.get(strategy_id)
            if strategy:
                # 根据分配调整交易量
                base_quantity = strategy.config.parameters.get('quantity', 1.0)
                allocation_factor = allocation / (self.initial_capital / len(self.service.strategies))
                new_quantity = base_quantity * allocation_factor
                
                # 更新策略参数
                new_params = strategy.config.parameters.copy()
                new_params['quantity'] = new_quantity
                
                self.service.update_strategy(
                    strategy_id, 
                    strategy.config.name, 
                    strategy.config.symbol, 
                    new_params
                )
    
    def _calculate_total_exposure(self) -> float:
        """计算总风险敞口"""
        total = 0
        for strategy in self.service.strategies.values():
            quantity = strategy.config.parameters.get('quantity', 0)
            # 假设平均价格计算敞口
            total += quantity * 50000  # 简化计算
        return total
    
    def _calculate_strategy_risk(self, strategy_id: str) -> float:
        """计算单一策略风险"""
        strategy = self.service.strategies.get(strategy_id)
        if not strategy:
            return 0
        
        quantity = strategy.config.parameters.get('quantity', 0)
        return quantity * 50000 / self.initial_capital  # 风险比例
    
    def _reduce_position_sizes(self):
        """减少所有策略仓位"""
        for strategy in self.service.strategies.values():
            current_quantity = strategy.config.parameters.get('quantity', 1.0)
            new_params = strategy.config.parameters.copy()
            new_params['quantity'] = current_quantity * 0.8  # 减少20%
            
            self.service.update_strategy(
                strategy.config.id,
                strategy.config.name,
                strategy.config.symbol,
                new_params
            )
    
    def _limit_strategy_position(self, strategy_id: str):
        """限制单一策略仓位"""
        strategy = self.service.strategies.get(strategy_id)
        if strategy:
            new_params = strategy.config.parameters.copy()
            new_params['quantity'] = min(new_params.get('quantity', 1.0), 0.5)  # 最大0.5
            
            self.service.update_strategy(
                strategy_id,
                strategy.config.name,
                strategy.config.symbol,
                new_params
            )
    
    def _get_strategy_daily_returns(self, strategy_id: str) -> List[float]:
        """获取策略日收益序列"""
        # 简化实现
        return [0.01, 0.02, -0.005, 0.015, 0.008]  # 示例数据
    
    def _get_strategy_cumulative_returns(self, strategy_id: str) -> List[float]:
        """获取策略累计收益序列"""
        # 简化实现
        daily_returns = self._get_strategy_daily_returns(strategy_id)
        cumulative = [1.0]
        for ret in daily_returns:
            cumulative.append(cumulative[-1] * (1 + ret))
        return cumulative
    
    def _log_management_actions(self, performances: Dict[str, Dict]):
        """记录管理操作"""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_strategies': len(performances),
            'running_strategies': sum(1 for p in performances.values() if p['enabled']),
            'avg_score': np.mean([p['score'] for p in performances.values()]),
            'best_strategy': max(performances.items(), key=lambda x: x[1]['score'])[1]['name'],
            'total_return': sum(p['total_return'] for p in performances.values()) / len(performances)
        }
        
        self.service._log_operation(
            "auto_management",
            f"自动管理完成: 平均评分{summary['avg_score']:.1f}, 最佳策略{summary['best_strategy']}, 平均收益{summary['total_return']*100:.2f}%",
            "success"
        )
        
        logger.info(f"管理摘要: {summary}")

class QuantitativeService:
    """量化交易服务主类"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.strategies: Dict[str, QuantitativeStrategy] = {}
        self.positions: Dict[str, Position] = {}
        self.performance_data = []
        self.is_running = False
        self._monitor_thread = None
        
        # 初始化自动化管理器
        self.auto_manager = AutomatedStrategyManager(self)
        
        # 从数据库加载已存在的策略
        self._load_strategies_from_db()
        
        # 启动自动化管理定时器
        self._start_auto_management()
    
    def _start_auto_management(self):
        """启动自动化管理定时器"""
        import threading
        
        def auto_management_loop():
            import time
            while True:
                try:
                    time.sleep(3600)  # 每小时执行一次
                    if self.is_running:
                        self.auto_manager.auto_manage_strategies()
                except Exception as e:
                    logger.error(f"自动管理循环出错: {e}")
        
        auto_thread = threading.Thread(target=auto_management_loop, daemon=True)
        auto_thread.start()
        logger.info("自动化策略管理已启动，每小时执行一次")

    def _load_strategies_from_db(self):
        """从数据库加载策略"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM quant_strategies")
                
                for row in cursor.fetchall():
                    strategy_id, name, strategy_type_str, symbol, enabled, parameters_json, created_time_str, updated_time_str = row
                    
                    # 解析参数
                    parameters = json.loads(parameters_json)
                    
                    # 解析时间
                    created_time = datetime.fromisoformat(created_time_str)
                    updated_time = datetime.fromisoformat(updated_time_str)
                    
                    # 创建策略配置
                    config = StrategyConfig(
                        id=strategy_id,
                        name=name,
                        strategy_type=StrategyType(strategy_type_str),
                        symbol=symbol,
                        enabled=bool(enabled),
                        parameters=parameters,
                        created_time=created_time,
                        updated_time=updated_time
                    )
                    
                    # 创建策略实例
                    if config.strategy_type == StrategyType.MOMENTUM:
                        strategy = MomentumStrategy(config)
                    elif config.strategy_type == StrategyType.MEAN_REVERSION:
                        strategy = MeanReversionStrategy(config)
                    elif config.strategy_type == StrategyType.BREAKOUT:
                        strategy = BreakoutStrategy(config)
                    elif config.strategy_type == StrategyType.GRID_TRADING:
                        strategy = GridTradingStrategy(config)
                    elif config.strategy_type == StrategyType.HIGH_FREQUENCY:
                        strategy = HighFrequencyStrategy(config)
                    elif config.strategy_type == StrategyType.TREND_FOLLOWING:
                        strategy = TrendFollowingStrategy(config)
                    else:
                        logger.warning(f"不支持的策略类型: {config.strategy_type}")
                        continue
                    
                    self.strategies[strategy_id] = strategy
                    
                    # 如果策略之前是启用状态，重新启动
                    if config.enabled:
                        strategy.start()
                        
                logger.info(f"从数据库加载了 {len(self.strategies)} 个策略")
                        
        except Exception as e:
            logger.error(f"从数据库加载策略失败: {e}")
            # 即使加载失败也不要抛出异常，服务仍然可以正常工作
        
    def create_strategy(self, name: str, strategy_type: StrategyType, symbol: str, parameters: Dict[str, Any]) -> str:
        """创建新策略"""
        strategy_id = f"strategy_{int(time.time() * 1000)}"
        
        config = StrategyConfig(
            id=strategy_id,
            name=name,
            strategy_type=strategy_type,
            symbol=symbol,
            enabled=False,
            parameters=parameters,
            created_time=datetime.now(),
            updated_time=datetime.now()
        )
        
        # 创建策略实例
        if strategy_type == StrategyType.MOMENTUM:
            strategy = MomentumStrategy(config)
        elif strategy_type == StrategyType.MEAN_REVERSION:
            strategy = MeanReversionStrategy(config)
        elif strategy_type == StrategyType.BREAKOUT:
            strategy = BreakoutStrategy(config)
        elif strategy_type == StrategyType.GRID_TRADING:
            strategy = GridTradingStrategy(config)
        elif strategy_type == StrategyType.HIGH_FREQUENCY:
            strategy = HighFrequencyStrategy(config)
        elif strategy_type == StrategyType.TREND_FOLLOWING:
            strategy = TrendFollowingStrategy(config)
        else:
            raise ValueError(f"不支持的策略类型: {strategy_type}")
            
        self.strategies[strategy_id] = strategy
        
        # 保存到数据库
        self._save_strategy_to_db(config)
        
        # 记录操作日志
        self._log_operation("create_strategy", f"创建策略: {name} ({strategy_type.value})", "success")
        
        logger.info(f"创建策略成功: {name} (ID: {strategy_id})")
        return strategy_id
        
    def start_strategy(self, strategy_id: str) -> bool:
        """启动策略"""
        if strategy_id not in self.strategies:
            self._log_operation("start_strategy", f"启动策略失败: 策略ID {strategy_id} 不存在", "failed")
            return False
            
        strategy = self.strategies[strategy_id]
        strategy.start()
        strategy.config.enabled = True
        strategy.config.updated_time = datetime.now()
        
        # 更新数据库
        self._update_strategy_in_db(strategy.config)
        
        # 记录操作日志
        self._log_operation("start_strategy", f"启动策略: {strategy.config.name}", "success")
        
        return True
        
    def stop_strategy(self, strategy_id: str) -> bool:
        """停止策略"""
        if strategy_id not in self.strategies:
            self._log_operation("stop_strategy", f"停止策略失败: 策略ID {strategy_id} 不存在", "failed")
            return False
            
        strategy = self.strategies[strategy_id]
        strategy.stop()
        strategy.config.enabled = False
        strategy.config.updated_time = datetime.now()
        
        # 更新数据库
        self._update_strategy_in_db(strategy.config)
        
        # 记录操作日志
        self._log_operation("stop_strategy", f"停止策略: {strategy.config.name}", "success")
        
        return True
        
    def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """获取单个策略"""
        if strategy_id not in self.strategies:
            return None
            
        strategy = self.strategies[strategy_id]
        return {
            'id': strategy.config.id,
            'name': strategy.config.name,
            'type': strategy.config.strategy_type.value,
            'symbol': strategy.config.symbol,
            'enabled': strategy.config.enabled,
            'running': strategy.is_running,
            'parameters': strategy.config.parameters,
            'created_time': strategy.config.created_time.isoformat(),
            'updated_time': strategy.config.updated_time.isoformat()
        }
        
    def delete_strategy(self, strategy_id: str) -> bool:
        """删除策略"""
        if strategy_id not in self.strategies:
            return False
            
        strategy = self.strategies[strategy_id]
        
        # 如果策略正在运行，先停止
        if strategy.is_running:
            strategy.stop()
            
        # 从内存中删除
        del self.strategies[strategy_id]
        
        # 从数据库中删除
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM quant_strategies WHERE id = ?", (strategy_id,))
            conn.commit()
        
        # 记录操作日志
        self._log_operation("delete_strategy", f"删除策略: {strategy.config.name}", "success")
        
        logger.info(f"删除策略成功: {strategy.config.name} (ID: {strategy_id})")
        return True
        
    def update_strategy(self, strategy_id: str, name: str, symbol: str, parameters: Dict[str, Any]) -> bool:
        """更新策略配置"""
        if strategy_id not in self.strategies:
            return False
            
        strategy = self.strategies[strategy_id]
        old_name = strategy.config.name
        
        # 更新策略配置
        strategy.config.name = name
        strategy.config.symbol = symbol
        strategy.config.parameters.update(parameters)
        strategy.config.updated_time = datetime.now()
        
        # 更新数据库
        self._update_strategy_in_db(strategy.config)
        
        # 记录操作日志
        self._log_operation("update_strategy", f"更新策略配置: {old_name} -> {name}", "success")
        
        logger.info(f"更新策略成功: {name} (ID: {strategy_id})")
        return True

    def get_strategies(self) -> List[Dict[str, Any]]:
        """获取所有策略 - 按收益率排序"""
        strategies = []
        for strategy in self.strategies.values():
            # 计算策略收益率
            strategy_return = self._calculate_strategy_return(strategy.config.id)
            
            strategies.append({
                'id': strategy.config.id,
                'name': strategy.config.name,
                'type': strategy.config.strategy_type.value,
                'symbol': strategy.config.symbol,
                'enabled': strategy.config.enabled,
                'running': strategy.is_running,
                'parameters': strategy.config.parameters,
                'created_time': strategy.config.created_time.isoformat(),
                'updated_time': strategy.config.updated_time.isoformat(),
                'total_return': strategy_return,
                'daily_return': self._calculate_daily_return(strategy.config.id),
                'win_rate': self._calculate_win_rate(strategy.config.id),
                'total_trades': self._count_strategy_trades(strategy.config.id),
                'last_signal_time': self._get_last_signal_time(strategy.config.id)
            })
        
        # 按收益率排序（收益高的排前面）
        strategies.sort(key=lambda x: x['total_return'], reverse=True)
        return strategies

    def _calculate_strategy_return(self, strategy_id: str) -> float:
        """计算策略总收益率"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT SUM(
                        CASE 
                            WHEN signal_type = 'buy' THEN -price * quantity
                            WHEN signal_type = 'sell' THEN price * quantity
                            ELSE 0
                        END
                    ) as total_pnl,
                    SUM(
                        CASE 
                            WHEN signal_type = 'buy' THEN price * quantity
                            ELSE 0
                        END
                    ) as total_investment
                    FROM trading_signals 
                    WHERE strategy_id = ? AND executed = 1
                """, (strategy_id,))
                
                result = cursor.fetchone()
                if result and result[1] and result[1] > 0:
                    return result[0] / result[1]
                return 0.0
        except Exception as e:
            logger.error(f"计算策略收益时出错: {e}")
            return 0.0

    def _calculate_daily_return(self, strategy_id: str) -> float:
        """计算策略日收益率"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT SUM(
                        CASE 
                            WHEN signal_type = 'buy' THEN -price * quantity
                            WHEN signal_type = 'sell' THEN price * quantity
                            ELSE 0
                        END
                    ) as daily_pnl,
                    SUM(
                        CASE 
                            WHEN signal_type = 'buy' THEN price * quantity
                            ELSE 0
                        END
                    ) as daily_investment
                    FROM trading_signals 
                    WHERE strategy_id = ? AND executed = 1 
                    AND date(timestamp) = date('now')
                """, (strategy_id,))
                
                result = cursor.fetchone()
                if result and result[1] and result[1] > 0:
                    return result[0] / result[1]
                return 0.0
        except Exception as e:
            logger.error(f"计算策略日收益时出错: {e}")
            return 0.0

    def _calculate_win_rate(self, strategy_id: str) -> float:
        """计算策略胜率"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN (
                            SELECT SUM(
                                CASE 
                                    WHEN s2.signal_type = 'sell' THEN s2.price * s2.quantity
                                    WHEN s2.signal_type = 'buy' THEN -s2.price * s2.quantity
                                    ELSE 0
                                END
                            ) FROM trading_signals s2 
                            WHERE s2.strategy_id = s1.strategy_id 
                            AND s2.timestamp >= s1.timestamp
                            AND s2.timestamp <= datetime(s1.timestamp, '+1 hour')
                        ) > 0 THEN 1 ELSE 0 END) as profitable_trades
                    FROM trading_signals s1
                    WHERE s1.strategy_id = ? AND s1.executed = 1
                """, (strategy_id,))
                
                result = cursor.fetchone()
                if result and result[0] > 0:
                    return result[1] / result[0]
                return 0.0
        except Exception as e:
            logger.error(f"计算策略胜率时出错: {e}")
            return 0.0

    def _count_strategy_trades(self, strategy_id: str) -> int:
        """统计策略交易次数"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM trading_signals 
                    WHERE strategy_id = ? AND executed = 1
                """, (strategy_id,))
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"统计策略交易次数时出错: {e}")
            return 0

    def _get_last_signal_time(self, strategy_id: str) -> Optional[str]:
        """获取策略最后信号时间"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT timestamp FROM trading_signals 
                    WHERE strategy_id = ? 
                    ORDER BY timestamp DESC LIMIT 1
                """, (strategy_id,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"获取策略最后信号时间时出错: {e}")
            return None
            
    def get_signals(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取最新信号"""
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trading_signals 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            signals = []
            for row in cursor.fetchall():
                signals.append({
                    'id': row[0],
                    'strategy_id': row[1],
                    'symbol': row[2],
                    'signal_type': row[3],
                    'price': row[4],
                    'quantity': row[5],
                    'confidence': row[6],
                    'timestamp': row[7],
                    'executed': bool(row[8])
                })
            return signals
            
    def get_positions(self) -> List[Dict[str, Any]]:
        """获取持仓信息"""
        positions = []
        for position in self.positions.values():
            positions.append({
                'symbol': position.symbol,
                'quantity': position.quantity,
                'avg_price': position.avg_price,
                'current_price': position.current_price,
                'unrealized_pnl': position.unrealized_pnl,
                'realized_pnl': position.realized_pnl,
                'updated_time': position.updated_time.isoformat()
            })
        return positions
        
    def get_performance(self, days: int = 30) -> Dict[str, Any]:
        """获取绩效数据"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM performance_metrics 
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
            """, (start_date, end_date))
            
            metrics = []
            for row in cursor.fetchall():
                metrics.append({
                    'total_return': row[1],
                    'daily_return': row[2],
                    'max_drawdown': row[3],
                    'sharpe_ratio': row[4],
                    'win_rate': row[5],
                    'total_trades': row[6],
                    'profitable_trades': row[7],
                    'timestamp': row[8]
                })
                
        return {
            'metrics': metrics,
            'summary': self._calculate_performance_summary(metrics) if metrics else {}
        }
        
    def get_operation_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取操作日志"""
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM operation_logs 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            logs = []
            for row in cursor.fetchall():
                logs.append({
                    'id': row[0],
                    'operation_type': row[1],
                    'operation_detail': row[2],
                    'user_id': row[3],
                    'result': row[4],
                    'timestamp': row[5]
                })
            return logs
            
    def process_market_data(self, symbol: str, price_data: Dict[str, Any]):
        """处理市场数据，生成交易信号"""
        logger.debug(f"处理市场数据: {symbol}, 价格: {price_data.get('price', 'N/A')}")
        
        for strategy in self.strategies.values():
            if strategy.config.symbol == symbol and strategy.is_running:
                try:
                    signal = strategy.generate_signal(price_data)
                    if signal:
                        self._save_signal_to_db(signal)
                        logger.info(f"生成交易信号: {signal.signal_type.value} {signal.symbol} @ {signal.price}")
                except Exception as e:
                    logger.error(f"策略 {strategy.config.name} 生成信号时出错: {e}")
        
        running_strategies = [s for s in self.strategies.values() if s.is_running]
        if not running_strategies:
            logger.debug(f"没有运行中的策略处理 {symbol} 的市场数据")
        else:
            symbol_strategies = [s for s in running_strategies if s.config.symbol == symbol]
            if not symbol_strategies:
                logger.debug(f"没有针对 {symbol} 的运行中策略")
            else:
                logger.debug(f"为 {symbol} 找到 {len(symbol_strategies)} 个运行中的策略")
        
    def _save_strategy_to_db(self, config: StrategyConfig):
        """保存策略到数据库"""
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO quant_strategies 
                (id, name, strategy_type, symbol, enabled, parameters, created_time, updated_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                config.id, config.name, config.strategy_type.value, config.symbol,
                config.enabled, json.dumps(config.parameters),
                config.created_time, config.updated_time
            ))
            conn.commit()
            
    def _update_strategy_in_db(self, config: StrategyConfig):
        """更新数据库中的策略"""
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE quant_strategies 
                SET name = ?, symbol = ?, enabled = ?, parameters = ?, updated_time = ?
                WHERE id = ?
            """, (
                config.name, config.symbol, config.enabled, json.dumps(config.parameters),
                config.updated_time, config.id
            ))
            conn.commit()
            
    def _save_signal_to_db(self, signal: TradingSignal):
        """保存信号到数据库"""
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trading_signals 
                (id, strategy_id, symbol, signal_type, price, quantity, confidence, timestamp, executed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.id, signal.strategy_id, signal.symbol, signal.signal_type.value,
                signal.price, signal.quantity, signal.confidence, signal.timestamp, signal.executed
            ))
            conn.commit()
            
    def _log_operation(self, operation_type: str, detail: str, result: str):
        """记录操作日志"""
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO operation_logs 
                (operation_type, operation_detail, result, timestamp)
                VALUES (?, ?, ?, ?)
            """, (operation_type, detail, result, datetime.now()))
            conn.commit()
            
    def _calculate_performance_summary(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算绩效摘要"""
        if not metrics:
            return {}
            
        latest = metrics[-1]
        returns = [m['daily_return'] for m in metrics]
        
        return {
            'total_return': latest['total_return'],
            'avg_daily_return': np.mean(returns),
            'volatility': np.std(returns),
            'max_drawdown': latest['max_drawdown'],
            'sharpe_ratio': latest['sharpe_ratio'],
            'win_rate': latest['win_rate'],
            'total_trades': latest['total_trades']
        }

# 全局量化服务实例
quantitative_service = QuantitativeService() 

# 在QuantitativeService类末尾添加所有缺失的方法（在创建实例之前）