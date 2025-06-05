#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
量化交易服务模块 - PostgreSQL版本
包含策略管理、信号生成、持仓监控、收益统计等功能
使用PostgreSQL解决并发访问问题
"""

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
import random
import uuid
import requests
import traceback
import ccxt
import logging
from db_config import get_db_adapter

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

class DatabaseManager:
    """PostgreSQL数据库管理类"""
    
    def __init__(self, db_path: str = "quantitative.db"):
        self.db_path = db_path  # 保持兼容性，但实际使用PostgreSQL
        self.db_adapter = get_db_adapter()
        self.conn = self.db_adapter.connection
        print("✅ PostgreSQL数据库管理器初始化完成")
    
    def execute_query(self, query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
        """执行SQL查询 - 使用PostgreSQL适配器"""
        try:
            return self.db_adapter.execute_query(query, params, fetch_one, fetch_all)
        except Exception as e:
            print(f"❌ PostgreSQL查询失败: {e}")
            return None
    
    def init_database(self):
        """初始化PostgreSQL数据库表"""
        try:
            print("🔄 初始化PostgreSQL数据库表...")
            
            # 初始化基础表结构
            self.db_adapter.init_tables()
            
            # 创建系统状态表
            self.execute_query('''
                CREATE TABLE IF NOT EXISTS system_status (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建交易信号表
            self.execute_query('''
                CREATE TABLE IF NOT EXISTS trading_signals (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP,
                    symbol TEXT,
                    signal_type TEXT,
                    price REAL,
                    confidence REAL,
                    executed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建策略交易日志表
            self.execute_query('''
                CREATE TABLE IF NOT EXISTS strategy_trade_logs (
                    id SERIAL PRIMARY KEY,
                    strategy_id TEXT,
                    signal_id TEXT,
                    symbol TEXT,
                    signal_type TEXT,
                    price REAL,
                    quantity REAL,
                    pnl REAL DEFAULT 0,
                    executed INTEGER DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建持仓表
            self.execute_query('''
                CREATE TABLE IF NOT EXISTS positions (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT,
                    quantity REAL,
                    avg_price REAL,
                    current_price REAL,
                    unrealized_pnl REAL,
                    realized_pnl REAL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建余额历史表
            self.execute_query('''
                CREATE TABLE IF NOT EXISTS balance_history (
                    id SERIAL PRIMARY KEY,
                    total_balance REAL,
                    available_balance REAL,
                    frozen_balance REAL,
                    daily_pnl REAL DEFAULT 0,
                    daily_return REAL DEFAULT 0,
                    milestone_note TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建策略优化日志表
            self.execute_query('''
                CREATE TABLE IF NOT EXISTS strategy_optimization_logs (
                    id SERIAL PRIMARY KEY,
                    strategy_id TEXT,
                    optimization_type TEXT,
                    old_parameters TEXT,
                    new_parameters TEXT,
                    trigger_reason TEXT,
                    target_success_rate REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            print("✅ PostgreSQL数据库表初始化完成")
            
        except Exception as e:
            print(f"❌ PostgreSQL数据库初始化失败: {e}")
            traceback.print_exc()

# 其他类保持不变，但所有数据库操作都通过DatabaseManager进行
if __name__ == "__main__":
    print("🚀 启动PostgreSQL版本量化交易服务...")
    db_manager = DatabaseManager()
    db_manager.init_database()
    print("✅ PostgreSQL版本量化服务初始化完成！") 