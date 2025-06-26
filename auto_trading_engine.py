#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动交易引擎 - 2.0增强版
实现全自动无人干预交易，整合市场环境分类、策略资源分配和自动异常处理

作者: 系统架构优化团队
日期: 2025年6月8日
"""

import os
import sys
import time
import logging
import json
import sqlite3
import traceback
import signal
import threading
import subprocess
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# 配置日志系统
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/auto_trading_engine.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 导入自定义模块
try:
    from market_environment_classifier import get_market_classifier
    market_classifier_available = True
except ImportError:
    logger.warning("市场环境分类器未找到，相关功能将被禁用")
    market_classifier_available = False

try:
    from strategy_resource_allocator import get_resource_allocator
    resource_allocator_available = True
except ImportError:
    logger.warning("策略资源分配器未找到，相关功能将被禁用")
    resource_allocator_available = False

# 尝试导入API模块
try:
    from vnpy.trader.object import TickData, BarData, OrderData, TradeData
    from vnpy.trader.constant import Direction, Offset, Status
    from vnpy.trader.utility import load_json, save_json
except ImportError:
    logger.warning("VNPY模块导入失败，部分功能可能受限")


class AutoTradingEngine:
    """自动交易引擎 - 全自动无人干预交易系统"""
    
    def __init__(self, config_file="auto_trading_config.json"):
        """初始化自动交易引擎"""
        # 加载配置
        self.config = self._load_config(config_file)
        self.engine_name = self.config.get("engine_name", "AutoTrader2.0")
        
        # 状态变量
        self.running = False
        self.paused = False
        self.initialized = False
        self.last_error = None
        self.start_time = None
        self.last_check_time = None
        self.last_allocation_time = None
        self.last_market_analysis_time = None
        self.last_data_update_time = None
        self.last_strategy_update_time = None
        self.trade_count = 0
        self.error_count = 0
        
        # 组件状态
        self.market_classifier = None
        self.resource_allocator = None
        self.current_market_state = None
        self.current_allocations = {}
        self.active_strategies = []
        
        # 引擎状态
        self.engine_status = {
            "status": "initialized",
            "market_state": None,
            "active_strategies": 0,
            "last_trade_time": None,
            "uptime": 0,
            "errors": [],
            "warnings": [],
            "performance": {}
        }
        
        # 数据库连接
        self.db = self._connect_database()
        
        # 初始化完成
        logger.info(f"🚀 {self.engine_name} 初始化完成")
    
    def _load_config(self, config_file: str) -> Dict:
        """加载配置文件"""
        default_config = {
            "engine_name": "AutoTrader2.0",
            "database_path": "quantitative.db",
            "check_interval": 60,
            "allocation_interval": 86400,  # 1天
            "market_analysis_interval": 3600,  # 1小时
            "data_update_interval": 300,  # 5分钟
            "strategy_update_interval": 3600,  # 1小时
            "max_active_strategies": 5,
            "emergency_shutdown_balance": 100,
            "reserve_balance": 50,
            "enable_auto_recovery": True,
            "trading_hours": {
                "enabled": False,
                "start": "09:30",
                "end": "16:00",
                "timezone": "Asia/Shanghai"
            },
            "exchanges": ["binance", "okex"],
            "assets": ["BTC", "ETH", "BNB"],
            "quote_currency": "USDT",
            "enable_market_classifier": True,
            "enable_resource_allocator": True,
            "dry_run": False,
            "log_level": "INFO"
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                # 合并配置与默认值
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            else:
                logger.warning(f"配置文件 {config_file} 不存在，使用默认配置")
                return default_config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return default_config
    
    def _connect_database(self):
        """连接到数据库"""
        try:
            db_path = self.config["database_path"]
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            logger.info(f"数据库连接成功: {db_path}")
            return conn
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return None
    
    def _initialize_components(self):
        """初始化核心组件"""
        try:
            # 初始化市场环境分类器
            if self.config["enable_market_classifier"] and market_classifier_available:
                self.market_classifier = get_market_classifier()
                logger.info("市场环境分类器初始化成功")
            
            # 初始化资源分配器
            if self.config["enable_resource_allocator"] and resource_allocator_available:
                self.resource_allocator = get_resource_allocator()
                logger.info("策略资源分配器初始化成功")
            
            # 创建必要的目录
            os.makedirs("logs", exist_ok=True)
            os.makedirs("data", exist_ok=True)
            
            # 标记初始化完成
            self.initialized = True
            logger.info("核心组件初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"初始化核心组件失败: {e}")
            logger.error(traceback.format_exc())
            self.last_error = str(e)
            return False
    
    def _load_active_strategies(self) -> List[Dict]:
        """从数据库加载活跃策略"""
        if not self.db:
            logger.warning("数据库未连接，无法加载活跃策略")
            return []
        
        try:
            cursor = self.db.cursor()
            
            # 查询活跃策略
            cursor.execute("""
                SELECT id, name, strategy_type, final_score, enabled, parameters, status
                FROM strategies
                WHERE enabled = 1
                ORDER BY final_score DESC
            """)
            
            strategies = []
            for row in cursor.fetchall():
                strategy = {
                    "id": row["id"],
                    "name": row["name"],
                    "strategy_type": row["strategy_type"],
                    "score": row["final_score"],
                    "enabled": bool(row["enabled"]),
                    "parameters": json.loads(row["parameters"]) if row["parameters"] else {},
                    "status": row["status"]
                }
                strategies.append(strategy)
            
            logger.info(f"已加载 {len(strategies)} 个活跃策略")
            return strategies
            
        except Exception as e:
            logger.error(f"加载活跃策略失败: {e}")
            return []
    
    def _update_market_state(self):
        """更新市场环境状态"""
        if not self.market_classifier:
            logger.warning("市场环境分类器未初始化，无法更新市场状态")
            return False
        
        try:
            # 获取OHLCV数据
            ohlcv_data = self._fetch_market_data()
            if ohlcv_data is None or len(ohlcv_data) < 20:
                logger.warning("市场数据不足，无法分析市场状态")
                return False
            
            # 检测市场状态
            market_state = self.market_classifier.detect_market_state(ohlcv_data)
            self.market_classifier.update_market_state_history(market_state)
            
            # 更新当前状态
            self.current_market_state = market_state
            
            # 记录分析时间
            self.last_market_analysis_time = datetime.now()
            
            logger.info(f"市场环境分析完成: {market_state}")
            
            # 更新引擎状态
            self.engine_status["market_state"] = market_state
            
            return True
            
        except Exception as e:
            logger.error(f"更新市场状态失败: {e}")
            logger.error(traceback.format_exc())
            self.error_count += 1
            self.last_error = str(e)
            self.engine_status["errors"].append({
                "time": datetime.now().isoformat(),
                "component": "market_classifier",
                "error": str(e)
            })
            return False
    
    def _fetch_market_data(self) -> pd.DataFrame:
        """获取市场数据"""
        try:
            # 优先从数据库获取
            if self.db:
                cursor = self.db.cursor()
                
                # 默认使用BTC/USDT作为市场状态参考
                symbol = self.config.get("market_reference_symbol", "BTC/USDT")
                exchange = self.config.get("market_reference_exchange", "binance")
                
                # 查询最近的K线数据
                cursor.execute("""
                    SELECT * FROM (
                        SELECT 
                            timestamp, open, high, low, close, volume
                        FROM market_data
                        WHERE symbol = ? AND exchange = ?
                        ORDER BY timestamp DESC
                        LIMIT 100
                    ) ORDER BY timestamp ASC
                """, (symbol, exchange))
                
                rows = cursor.fetchall()
                
                if rows:
                    # 转换为DataFrame
                    data = {
                        'timestamp': [],
                        'open': [],
                        'high': [],
                        'low': [],
                        'close': [],
                        'volume': []
                    }
                    
                    for row in rows:
                        data['timestamp'].append(row['timestamp'])
                        data['open'].append(row['open'])
                        data['high'].append(row['high'])
                        data['low'].append(row['low'])
                        data['close'].append(row['close'])
                        data['volume'].append(row['volume'])
                    
                    df = pd.DataFrame(data)
                    df.columns = [col.lower() for col in df.columns]
                    return df
            
            # 如果数据库没有数据，尝试其他方式获取
            logger.warning("数据库中没有足够的市场数据，无法获取OHLCV数据")
            
            # TODO: 增加备用数据源获取方式
            
            return None
            
        except Exception as e:
            logger.error(f"获取市场数据失败: {e}")
            return None
    
    def _optimize_resource_allocation(self):
        """优化资源分配"""
        if not self.resource_allocator:
            logger.warning("资源分配器未初始化，无法优化资源分配")
            return False
        
        try:
            # 加载活跃策略
            strategies = self._load_active_strategies()
            if not strategies:
                logger.warning("没有活跃策略可用于资源分配")
                return False
            
            # 获取可用资金
            available_capital = self._get_available_capital()
            if available_capital <= 0:
                logger.warning(f"可用资金不足: {available_capital}")
                return False
            
            # 获取当前市场状态
            market_state = self.current_market_state or "SIDEWAYS"
            
            # 选择最优策略组合
            optimal_strategies = self.resource_allocator.get_optimal_strategy_mix(
                strategies, 
                max_strategies=self.config.get("max_active_strategies", 5)
            )
            
            # 如果没有最优策略，使用所有策略
            if not optimal_strategies:
                optimal_strategies = [s["id"] for s in strategies]
                
                # 限制最大策略数
                max_strategies = self.config.get("max_active_strategies", 5)
                if len(optimal_strategies) > max_strategies:
                    # 按分数排序
                    strategies_by_score = sorted(strategies, key=lambda s: s.get("score", 0), reverse=True)
                    optimal_strategies = [s["id"] for s in strategies_by_score[:max_strategies]]
            
            # 优化资金分配
            allocation_result = self.resource_allocator.optimize_allocations(
                optimal_strategies,
                available_capital,
                market_state=market_state
            )
            
            # 更新当前分配
            self.current_allocations = allocation_result
            
            # 更新活跃策略列表
            self.active_strategies = list(allocation_result["allocations"].keys())
            
            # 记录分配时间
            self.last_allocation_time = datetime.now()
            
            # 更新引擎状态
            self.engine_status["active_strategies"] = len(self.active_strategies)
            
            logger.info(f"资源分配优化完成，{len(self.active_strategies)} 个活跃策略")
            
            # 应用资金分配
            self._apply_resource_allocation(allocation_result)
            
            return True
            
        except Exception as e:
            logger.error(f"优化资源分配失败: {e}")
            logger.error(traceback.format_exc())
            self.error_count += 1
            self.last_error = str(e)
            self.engine_status["errors"].append({
                "time": datetime.now().isoformat(),
                "component": "resource_allocator",
                "error": str(e)
            })
            return False
    
    def _get_available_capital(self) -> float:
        """获取可用资金"""
        if self.config.get("dry_run", False):
            # 测试模式使用配置中的模拟资金
            return self.config.get("test_capital", 10000.0)
        
        try:
            # 从数据库获取账户余额
            if self.db:
                cursor = self.db.cursor()
                
                # 获取最新的余额记录
                cursor.execute("""
                    SELECT SUM(balance) as total_balance
                    FROM account_balance
                    WHERE currency = ? AND timestamp = (
                        SELECT MAX(timestamp) FROM account_balance
                    )
                """, (self.config.get("quote_currency", "USDT"),))
                
                row = cursor.fetchone()
                if row and row["total_balance"] is not None:
                    total_balance = float(row["total_balance"])
                    
                    # 确保预留余额
                    reserve = self.config.get("reserve_balance", 50)
                    available = max(0, total_balance - reserve)
                    
                    logger.info(f"总余额: {total_balance}, 可用余额: {available}")
                    return available
            
            # 如果无法从数据库获取，使用默认值
            logger.warning("无法从数据库获取账户余额，使用默认值")
            return self.config.get("default_available_capital", 1000.0)
            
        except Exception as e:
            logger.error(f"获取可用资金失败: {e}")
            return 0.0
    
    def _apply_resource_allocation(self, allocation_result: Dict):
        """应用资源分配结果"""
        if self.config.get("dry_run", False):
            logger.info("测试模式，不实际应用资源分配")
            return True
        
        try:
            # 获取当前分配
            allocations = allocation_result.get("allocations", {})
            if not allocations:
                logger.warning("没有资源分配结果可应用")
                return False
            
            # 将分配写入数据库
            if self.db:
                cursor = self.db.cursor()
                
                # 记录分配结果
                for strategy_id, amount in allocations.items():
                    cursor.execute("""
                        INSERT INTO strategy_allocations
                        (strategy_id, allocation_amount, allocation_time)
                        VALUES (?, ?, datetime('now'))
                    """, (strategy_id, amount))
                
                # 提交事务
                self.db.commit()
            
            logger.info(f"资源分配已应用到 {len(allocations)} 个策略")
            
            # TODO: 实际应用分配结果到交易系统
            
            return True
            
        except Exception as e:
            logger.error(f"应用资源分配失败: {e}")
            return False
    
    def _update_strategy_performance(self):
        """更新策略性能指标"""
        if not self.resource_allocator:
            logger.warning("资源分配器未初始化，无法更新策略性能")
            return False
        
        try:
            # 从数据库更新策略性能
            self.resource_allocator.update_strategy_performances_from_db()
            
            # 记录更新时间
            self.last_strategy_update_time = datetime.now()
            
            logger.info("策略性能指标已更新")
            return True
            
        except Exception as e:
            logger.error(f"更新策略性能失败: {e}")
            return False
    
    def _check_trading_conditions(self) -> bool:
        """检查交易条件是否满足"""
        # 检查交易时间
        if self.config.get("trading_hours", {}).get("enabled", False):
            trading_hours = self.config["trading_hours"]
            start_time = trading_hours.get("start", "09:30")
            end_time = trading_hours.get("end", "16:00")
            
            current_time = datetime.now().strftime("%H:%M")
            
            if not (start_time <= current_time <= end_time):
                logger.info(f"当前时间 {current_time} 不在交易时段 {start_time}-{end_time}")
                return False
        
        # 检查紧急停止条件
        emergency_threshold = self.config.get("emergency_shutdown_balance", 100)
        available_capital = self._get_available_capital()
        
        if available_capital < emergency_threshold:
            logger.warning(f"可用资金 {available_capital} 低于紧急停止阈值 {emergency_threshold}")
            return False
        
        # 检查系统状态
        if self.error_count > 10:
            logger.warning(f"错误次数过多 ({self.error_count})，暂停交易")
            return False
        
        return True
    
    def _monitor_system_health(self):
        """监控系统健康状态"""
        try:
            # 检查数据库连接
            if not self.db:
                self._connect_database()
            
            # 检查内存使用
            import psutil
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                logger.warning(f"内存使用率过高: {memory.percent}%")
                self.engine_status["warnings"].append({
                    "time": datetime.now().isoformat(),
                    "component": "system",
                    "warning": f"内存使用率过高: {memory.percent}%"
                })
            
            # 检查磁盘空间
            disk = psutil.disk_usage('/')
            if disk.percent > 90:
                logger.warning(f"磁盘使用率过高: {disk.percent}%")
                self.engine_status["warnings"].append({
                    "time": datetime.now().isoformat(),
                    "component": "system",
                    "warning": f"磁盘使用率过高: {disk.percent}%"
                })
            
            # 限制警告消息数量
            if len(self.engine_status["warnings"]) > 50:
                self.engine_status["warnings"] = self.engine_status["warnings"][-50:]
            if len(self.engine_status["errors"]) > 50:
                self.engine_status["errors"] = self.engine_status["errors"][-50:]
            
            # 更新引擎运行时间
            if self.start_time:
                uptime = (datetime.now() - self.start_time).total_seconds() / 3600  # 小时
                self.engine_status["uptime"] = round(uptime, 2)
            
            # 保存引擎状态
            self._save_engine_status()
            
        except Exception as e:
            logger.error(f"健康监控失败: {e}")
    
    def _save_engine_status(self):
        """保存引擎状态到文件"""
        try:
            status_file = "data/auto_trading_status.json"
            os.makedirs(os.path.dirname(status_file), exist_ok=True)
            
            with open(status_file, 'w') as f:
                status_data = {**self.engine_status, "timestamp": datetime.now().isoformat()}
                json.dump(status_data, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"保存引擎状态失败: {e}")
    
    def _handle_signals(self):
        """处理系统信号"""
        def signal_handler(sig, frame):
            logger.info(f"收到信号 {sig}，准备停止引擎")
            self.stop()
        
        # 注册信号处理
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _update_data(self):
        """更新市场数据"""
        # 记录更新时间
        self.last_data_update_time = datetime.now()
        
        # TODO: 实现数据更新逻辑
        
        logger.info("市场数据已更新")
    
    def start(self):
        """启动自动交易引擎"""
        if self.running:
            logger.warning("引擎已经在运行")
            return False
        
        logger.info(f"🚀 开始启动 {self.engine_name}")
        
        # 初始化组件
        if not self.initialized and not self._initialize_components():
            logger.error("组件初始化失败，引擎无法启动")
            return False
        
        # 记录启动时间
        self.start_time = datetime.now()
        self.running = True
        self.paused = False
        self.engine_status["status"] = "running"
        
        # 设置信号处理
        self._handle_signals()
        
        # 主循环
        try:
            logger.info("引擎已启动，开始主循环")
            
            # 初始市场分析
            self._update_market_state()
            
            # 初始资源分配
            self._optimize_resource_allocation()
            
            while self.running:
                try:
                    # 检查时间
                    now = datetime.now()
                    
                    # 健康检查
                    self._monitor_system_health()
                    
                    # 检查是否需要暂停
                    if not self.paused and not self._check_trading_conditions():
                        logger.info("交易条件不满足，引擎进入暂停状态")
                        self.paused = True
                        self.engine_status["status"] = "paused"
                    elif self.paused and self._check_trading_conditions():
                        logger.info("交易条件恢复，引擎继续运行")
                        self.paused = False
                        self.engine_status["status"] = "running"
                    
                    # 如果暂停状态，跳过交易逻辑
                    if self.paused:
                        time.sleep(self.config["check_interval"])
                        continue
                    
                    # 检查是否需要更新市场数据
                    if not self.last_data_update_time or \
                       (now - self.last_data_update_time).total_seconds() >= self.config["data_update_interval"]:
                        self._update_data()
                    
                    # 检查是否需要更新市场状态
                    if not self.last_market_analysis_time or \
                       (now - self.last_market_analysis_time).total_seconds() >= self.config["market_analysis_interval"]:
                        self._update_market_state()
                    
                    # 检查是否需要更新策略性能
                    if not self.last_strategy_update_time or \
                       (now - self.last_strategy_update_time).total_seconds() >= self.config["strategy_update_interval"]:
                        self._update_strategy_performance()
                    
                    # 检查是否需要优化资源分配
                    if not self.last_allocation_time or \
                       (now - self.last_allocation_time).total_seconds() >= self.config["allocation_interval"]:
                        self._optimize_resource_allocation()
                    
                    # 执行策略检查和交易
                    self._run_trading_cycle()
                    
                    # 状态检查
                    self.last_check_time = now
                    
                    # 等待下一个检查周期
                    time.sleep(self.config["check_interval"])
                    
                except Exception as e:
                    logger.error(f"交易周期出错: {e}")
                    logger.error(traceback.format_exc())
                    self.error_count += 1
                    self.last_error = str(e)
                    self.engine_status["errors"].append({
                        "time": datetime.now().isoformat(),
                        "component": "trading_cycle",
                        "error": str(e)
                    })
                    
                    # 短暂暂停，避免错误循环
                    time.sleep(5)
            
            logger.info("引擎正常停止")
            
        except KeyboardInterrupt:
            logger.info("收到键盘中断，引擎停止")
        except Exception as e:
            logger.critical(f"引擎运行出现严重错误: {e}")
            logger.critical(traceback.format_exc())
        finally:
            # 清理工作
            self.running = False
            self.engine_status["status"] = "stopped"
            self._save_engine_status()
            
            if self.db:
                self.db.close()
                
            logger.info("引擎已停止，资源清理完毕")
    
    def _run_trading_cycle(self):
        """执行交易周期"""
        if self.config.get("dry_run", False):
            logger.info("测试模式，跳过实际交易执行")
            return
        
        try:
            # 循环处理活跃策略
            for strategy_id in self.active_strategies:
                # 检查策略是否需要执行交易
                self._process_strategy(strategy_id)
                
            # 更新交易计数
            self.trade_count = self._get_trade_count()
            
        except Exception as e:
            logger.error(f"交易周期执行失败: {e}")
            raise
    
    def _process_strategy(self, strategy_id):
        """处理单个策略"""
        try:
            # 获取策略信息
            cursor = self.db.cursor()
            cursor.execute("SELECT * FROM strategies WHERE id = ?", (strategy_id,))
            strategy_row = cursor.fetchone()
            
            if not strategy_row or not strategy_row["enabled"]:
                logger.warning(f"策略 {strategy_id} 不存在或已禁用")
                return
            
            # 获取资金分配
            allocated_amount = self.current_allocations.get("allocations", {}).get(strategy_id, 0)
            if allocated_amount <= 0:
                logger.info(f"策略 {strategy_id} 未分配资金，跳过交易")
                return
            
            # 获取策略参数
            params = {}
            if strategy_row["parameters"]:
                try:
                    params = json.loads(strategy_row["parameters"])
                except:
                    pass
            
            # 检查交易信号
            signals = self._check_strategy_signals(strategy_id, params)
            
            if not signals:
                logger.info(f"策略 {strategy_id} 没有交易信号")
                return
            
            # 处理交易信号
            for signal in signals:
                self._execute_trade(strategy_id, signal, allocated_amount)
            
        except Exception as e:
            logger.error(f"处理策略 {strategy_id} 失败: {e}")
            raise
    
    def _check_strategy_signals(self, strategy_id, params):
        """检查策略交易信号"""
        try:
            # TODO: 实现策略信号检查逻辑
            # 这部分需要根据实际策略实现
            
            # 测试信号
            import random
            if random.random() < 0.1:  # 10%概率产生信号，仅用于测试
                return [{
                    "symbol": "BTC/USDT",
                    "direction": "long" if random.random() > 0.5 else "short",
                    "price": 50000 + random.random() * 1000,
                    "amount": 0.01,
                    "timestamp": datetime.now().isoformat()
                }]
            
            return []
            
        except Exception as e:
            logger.error(f"检查策略 {strategy_id} 信号失败: {e}")
            return []
    
    def _execute_trade(self, strategy_id, signal, allocated_amount):
        """执行交易"""
        try:
            # TODO: 实现交易执行逻辑
            # 这里需要根据实际交易API实现
            
            logger.info(f"执行交易: 策略 {strategy_id}, 信号 {signal}")
            
            # 记录交易
            if self.db:
                cursor = self.db.cursor()
                
                # 插入交易记录
                cursor.execute("""
                    INSERT INTO strategy_trade_logs
                    (strategy_id, symbol, direction, price, amount, timestamp)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                """, (
                    strategy_id, 
                    signal["symbol"],
                    signal["direction"],
                    signal["price"],
                    signal["amount"]
                ))
                
                self.db.commit()
            
            # 更新最后交易时间
            self.engine_status["last_trade_time"] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"执行交易失败: {e}")
            raise
    
    def _get_trade_count(self):
        """获取总交易次数"""
        if not self.db:
            return 0
        
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM strategy_trade_logs")
            row = cursor.fetchone()
            return row["count"] if row else 0
        except:
            return 0
    
    def stop(self):
        """停止自动交易引擎"""
        if not self.running:
            logger.warning("引擎未运行")
            return
        
        logger.info("准备停止引擎")
        self.running = False
        self.engine_status["status"] = "stopping"
    
    def pause(self):
        """暂停自动交易引擎"""
        if not self.running:
            logger.warning("引擎未运行")
            return
        
        logger.info("暂停引擎")
        self.paused = True
        self.engine_status["status"] = "paused"
    
    def resume(self):
        """恢复自动交易引擎"""
        if not self.running:
            logger.warning("引擎未运行")
            return
        
        if not self.paused:
            logger.warning("引擎未暂停")
            return
        
        logger.info("恢复引擎运行")
        self.paused = False
        self.engine_status["status"] = "running"
    
    def get_status(self):
        """获取引擎状态"""
        # 更新一些实时状态
        if self.running:
            if self.paused:
                status = "paused"
            else:
                status = "running"
        else:
            status = "stopped"
        
        self.engine_status["status"] = status
        
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds() / 3600  # 小时
            self.engine_status["uptime"] = round(uptime, 2)
        
        self.engine_status["active_strategies"] = len(self.active_strategies)
        
        # 获取策略性能
        if self.resource_allocator and self.current_allocations:
            portfolio_metrics = self.resource_allocator.get_portfolio_metrics(
                self.current_allocations.get("normalized", {})
            )
            self.engine_status["performance"] = portfolio_metrics
        
        return self.engine_status


def main():
    """主函数"""
    try:
        # 设置工作目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        # 创建引擎实例
        engine = AutoTradingEngine()
        
        # 启动引擎
        engine.start()
        
    except Exception as e:
        print(f"启动失败: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 