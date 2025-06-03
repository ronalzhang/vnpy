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
    """动量策略"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.price_history = []
        
    def generate_signal(self, price_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """基于动量指标生成信号"""
        if not self.is_running:
            return None
            
        current_price = price_data.get('price', 0)
        self.price_history.append(current_price)
        
        # 保留最近N个价格点
        lookback_period = self.config.parameters.get('lookback_period', 20)
        if len(self.price_history) > lookback_period:
            self.price_history.pop(0)
            
        if len(self.price_history) < lookback_period:
            return None
            
        # 计算动量指标
        returns = pd.Series(self.price_history).pct_change().dropna()
        momentum = returns.mean()
        
        threshold = self.config.parameters.get('momentum_threshold', 0.001)
        quantity = self.config.parameters.get('quantity', 1.0)
        
        # 生成信号
        if momentum > threshold:
            signal_type = SignalType.BUY
            confidence = min(abs(momentum) / threshold, 1.0)
        elif momentum < -threshold:
            signal_type = SignalType.SELL
            confidence = min(abs(momentum) / threshold, 1.0)
        else:
            return None
            
        signal = TradingSignal(
            id=f"signal_{int(time.time() * 1000)}",
            strategy_id=self.config.id,
            symbol=self.config.symbol,
            signal_type=signal_type,
            price=current_price,
            quantity=quantity,
            confidence=confidence,
            timestamp=datetime.now(),
            executed=False
        )
        
        return signal

class MeanReversionStrategy(QuantitativeStrategy):
    """均值回归策略"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.price_history = []
        
    def generate_signal(self, price_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """基于均值回归生成信号"""
        if not self.is_running:
            return None
            
        current_price = price_data.get('price', 0)
        self.price_history.append(current_price)
        
        lookback_period = self.config.parameters.get('lookback_period', 20)
        if len(self.price_history) > lookback_period:
            self.price_history.pop(0)
            
        if len(self.price_history) < lookback_period:
            return None
            
        # 计算布林带
        prices = pd.Series(self.price_history)
        sma = prices.mean()
        std = prices.std()
        
        std_multiplier = self.config.parameters.get('std_multiplier', 2.0)
        upper_band = sma + std_multiplier * std
        lower_band = sma - std_multiplier * std
        
        quantity = self.config.parameters.get('quantity', 1.0)
        
        # 生成信号
        if current_price < lower_band:
            # 价格低于下轨，买入信号
            confidence = min((lower_band - current_price) / (upper_band - lower_band), 1.0)
            signal_type = SignalType.BUY
        elif current_price > upper_band:
            # 价格高于上轨，卖出信号
            confidence = min((current_price - upper_band) / (upper_band - lower_band), 1.0)
            signal_type = SignalType.SELL
        else:
            return None
            
        signal = TradingSignal(
            id=f"signal_{int(time.time() * 1000)}",
            strategy_id=self.config.id,
            symbol=self.config.symbol,
            signal_type=signal_type,
            price=current_price,
            quantity=quantity,
            confidence=confidence,
            timestamp=datetime.now(),
            executed=False
        )
        
        return signal

class BreakoutStrategy(QuantitativeStrategy):
    """突破策略"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.price_history = []
        
    def generate_signal(self, price_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """基于价格突破生成信号"""
        if not self.is_running:
            return None
            
        current_price = price_data.get('price', 0)
        self.price_history.append(current_price)
        
        lookback_period = self.config.parameters.get('lookback_period', 20)
        if len(self.price_history) > lookback_period:
            self.price_history.pop(0)
            
        if len(self.price_history) < lookback_period:
            return None
            
        # 计算支撑和阻力位
        prices = pd.Series(self.price_history)
        resistance = prices.max()
        support = prices.min()
        
        breakout_threshold = self.config.parameters.get('breakout_threshold', 0.01)
        quantity = self.config.parameters.get('quantity', 1.0)
        
        # 生成信号
        if current_price > resistance * (1 + breakout_threshold):
            # 向上突破
            confidence = min((current_price - resistance) / resistance, 1.0)
            signal_type = SignalType.BUY
        elif current_price < support * (1 - breakout_threshold):
            # 向下突破
            confidence = min((support - current_price) / support, 1.0)
            signal_type = SignalType.SELL
        else:
            return None
            
        signal = TradingSignal(
            id=f"signal_{int(time.time() * 1000)}",
            strategy_id=self.config.id,
            symbol=self.config.symbol,
            signal_type=signal_type,
            price=current_price,
            quantity=quantity,
            confidence=confidence,
            timestamp=datetime.now(),
            executed=False
        )
        
        return signal

class QuantitativeService:
    """量化交易服务主类"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.strategies: Dict[str, QuantitativeStrategy] = {}
        self.positions: Dict[str, Position] = {}
        self.performance_data = []
        self.is_running = False
        self._monitor_thread = None
        
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
        
    def get_strategies(self) -> List[Dict[str, Any]]:
        """获取所有策略"""
        strategies = []
        for strategy in self.strategies.values():
            strategies.append({
                'id': strategy.config.id,
                'name': strategy.config.name,
                'type': strategy.config.strategy_type.value,
                'symbol': strategy.config.symbol,
                'enabled': strategy.config.enabled,
                'running': strategy.is_running,
                'parameters': strategy.config.parameters,
                'created_time': strategy.config.created_time.isoformat(),
                'updated_time': strategy.config.updated_time.isoformat()
            })
        return strategies
        
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
        for strategy in self.strategies.values():
            if strategy.config.symbol == symbol and strategy.is_running:
                signal = strategy.generate_signal(price_data)
                if signal:
                    self._save_signal_to_db(signal)
                    logger.info(f"生成交易信号: {signal.signal_type.value} {signal.symbol} @ {signal.price}")
                    
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
                SET enabled = ?, parameters = ?, updated_time = ?
                WHERE id = ?
            """, (
                config.enabled, json.dumps(config.parameters),
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