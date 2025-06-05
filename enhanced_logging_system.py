#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
增强日志系统
统一管理自动交易、策略进化、系统状态的日志记录
"""

import os
import sys
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from loguru import logger
import sqlite3
from pathlib import Path

@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: str
    module: str
    category: str
    message: str
    data: Optional[Dict] = None

class EnhancedLoggingSystem:
    """增强日志系统"""
    
    def __init__(self, db_path: str = "quantitative.db"):
        self.db_path = db_path
        self.log_buffer = []
        self.buffer_lock = threading.Lock()
        self.log_categories = {
            'STRATEGY_EVOLUTION': '策略进化',
            'AUTO_TRADING': '自动交易',
            'SYSTEM_STATUS': '系统状态',
            'PERFORMANCE': '性能分析',
            'ERROR_TRACKING': '错误追踪',
            'USER_ACTION': '用户操作'
        }
        
        self._setup_logging()
        self._setup_database()
        self._start_log_processor()
        
    def _setup_logging(self):
        """设置日志配置"""
        # 清除现有处理器
        logger.remove()
        
        # 创建日志目录
        os.makedirs('logs', exist_ok=True)
        os.makedirs('logs/evolution', exist_ok=True)
        os.makedirs('logs/trading', exist_ok=True)
        os.makedirs('logs/system', exist_ok=True)
        
        # 格式化配置
        log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{extra[module]: <15}</cyan> | <blue>{extra[category]: <12}</blue> | <level>{message}</level>"
        
        # 控制台输出
        logger.add(
            sys.stdout,
            format=log_format,
            level="INFO",
            filter=lambda record: record["extra"].get("category") in ["策略进化", "自动交易", "系统状态"]
        )
        
        # 主日志文件
        logger.add(
            "logs/quantitative_{time:YYYY-MM-DD}.log",
            format=log_format,
            level="DEBUG",
            rotation="1 day",
            retention="30 days",
            compression="zip"
        )
        
        # 策略进化专用日志
        logger.add(
            "logs/evolution/evolution_{time:YYYY-MM-DD}.log",
            format=log_format,
            level="DEBUG",
            rotation="1 day",
            retention="30 days",
            filter=lambda record: record["extra"].get("category") == "策略进化"
        )
        
        # 自动交易专用日志
        logger.add(
            "logs/trading/trading_{time:YYYY-MM-DD}.log",
            format=log_format,
            level="DEBUG",
            rotation="1 day",
            retention="30 days",
            filter=lambda record: record["extra"].get("category") == "自动交易"
        )
        
        # 系统状态专用日志
        logger.add(
            "logs/system/system_{time:YYYY-MM-DD}.log",
            format=log_format,
            level="DEBUG",
            rotation="1 day",
            retention="30 days",
            filter=lambda record: record["extra"].get("category") == "系统状态"
        )
        
        logger.info("📋 增强日志系统初始化完成", module="LOGGING", category="系统状态")
        
    def _setup_database(self):
        """设置数据库日志表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建详细日志表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS enhanced_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    module TEXT NOT NULL,
                    category TEXT NOT NULL,
                    message TEXT NOT NULL,
                    data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建策略进化日志表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_evolution_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT NOT NULL,
                    generation INTEGER DEFAULT 0,
                    action_type TEXT NOT NULL,
                    old_parameters TEXT,
                    new_parameters TEXT,
                    score_before REAL DEFAULT 0,
                    score_after REAL DEFAULT 0,
                    reason TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建自动交易日志表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auto_trading_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT NOT NULL,
                    strategy_id TEXT,
                    symbol TEXT,
                    signal_type TEXT,
                    price REAL,
                    quantity REAL,
                    confidence REAL,
                    result TEXT,
                    error_message TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"数据库日志表初始化失败: {e}", module="LOGGING", category="错误追踪")
    
    def _start_log_processor(self):
        """启动日志处理器"""
        def process_logs():
            while True:
                try:
                    if self.log_buffer:
                        with self.buffer_lock:
                            logs_to_process = self.log_buffer.copy()
                            self.log_buffer.clear()
                        
                        self._save_logs_to_db(logs_to_process)
                    
                    time.sleep(5)  # 每5秒处理一次
                    
                except Exception as e:
                    logger.error(f"日志处理器错误: {e}", module="LOGGING", category="错误追踪")
        
        processor_thread = threading.Thread(target=process_logs, daemon=True)
        processor_thread.start()
    
    def _save_logs_to_db(self, logs: List[LogEntry]):
        """保存日志到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for log_entry in logs:
                cursor.execute('''
                    INSERT INTO enhanced_logs (timestamp, level, module, category, message, data)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    log_entry.timestamp.isoformat(),
                    log_entry.level,
                    log_entry.module,
                    log_entry.category,
                    log_entry.message,
                    json.dumps(log_entry.data) if log_entry.data else None
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"保存日志到数据库失败: {e}", module="LOGGING", category="错误追踪")
    
    def log(self, level: str, message: str, module: str, category: str, data: Optional[Dict] = None):
        """记录日志"""
        try:
            # 添加到缓冲区
            log_entry = LogEntry(
                timestamp=datetime.now(),
                level=level,
                module=module,
                category=self.log_categories.get(category, category),
                message=message,
                data=data
            )
            
            with self.buffer_lock:
                self.log_buffer.append(log_entry)
            
            # 使用loguru记录
            logger_func = getattr(logger, level.lower(), logger.info)
            logger_func(message, module=module, category=self.log_categories.get(category, category))
            
        except Exception as e:
            logger.error(f"日志记录失败: {e}", module="LOGGING", category="错误追踪")
    
    def log_strategy_evolution(self, strategy_id: str, action_type: str, reason: str,
                             old_params: Optional[Dict] = None, new_params: Optional[Dict] = None,
                             score_before: float = 0, score_after: float = 0, generation: int = 0):
        """记录策略进化"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO strategy_evolution_logs 
                (strategy_id, generation, action_type, old_parameters, new_parameters, 
                 score_before, score_after, reason, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                strategy_id,
                generation,
                action_type,
                json.dumps(old_params) if old_params else None,
                json.dumps(new_params) if new_params else None,
                score_before,
                score_after,
                reason,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            # 记录详细日志
            message = f"策略 {strategy_id} {action_type}: {reason}"
            if score_before and score_after:
                message += f" (评分: {score_before:.1f} → {score_after:.1f})"
            
            self.log("INFO", message, "EVOLUTION", "STRATEGY_EVOLUTION", {
                'strategy_id': strategy_id,
                'action_type': action_type,
                'generation': generation,
                'score_change': score_after - score_before if score_before and score_after else 0
            })
            
        except Exception as e:
            self.log("ERROR", f"记录策略进化失败: {e}", "EVOLUTION", "ERROR_TRACKING")
    
    def log_auto_trading(self, action_type: str, strategy_id: str = None, symbol: str = None,
                        signal_type: str = None, price: float = None, quantity: float = None,
                        confidence: float = None, result: str = None, error_message: str = None):
        """记录自动交易"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO auto_trading_logs 
                (action_type, strategy_id, symbol, signal_type, price, quantity, 
                 confidence, result, error_message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                action_type,
                strategy_id,
                symbol,
                signal_type,
                price,
                quantity,
                confidence,
                result,
                error_message,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            # 记录详细日志
            message = f"自动交易 {action_type}"
            if strategy_id:
                message += f" [策略: {strategy_id}]"
            if symbol and signal_type:
                message += f" {symbol} {signal_type}"
            if price:
                message += f" 价格: {price}"
            if result:
                message += f" 结果: {result}"
            if error_message:
                message += f" 错误: {error_message}"
            
            level = "ERROR" if error_message else "INFO"
            self.log(level, message, "TRADING", "AUTO_TRADING", {
                'action_type': action_type,
                'strategy_id': strategy_id,
                'symbol': symbol,
                'signal_type': signal_type,
                'success': error_message is None
            })
            
        except Exception as e:
            self.log("ERROR", f"记录自动交易失败: {e}", "TRADING", "ERROR_TRACKING")
    
    def get_evolution_logs(self, strategy_id: str = None, days: int = 7) -> List[Dict]:
        """获取策略进化日志"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT * FROM strategy_evolution_logs 
                WHERE timestamp >= datetime('now', '-{} days')
            '''.format(days)
            
            if strategy_id:
                query += f" AND strategy_id = '{strategy_id}'"
            
            query += " ORDER BY timestamp DESC LIMIT 100"
            
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            conn.close()
            
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            self.log("ERROR", f"获取进化日志失败: {e}", "LOGGING", "ERROR_TRACKING")
            return []
    
    def get_trading_logs(self, strategy_id: str = None, days: int = 7) -> List[Dict]:
        """获取自动交易日志"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT * FROM auto_trading_logs 
                WHERE timestamp >= datetime('now', '-{} days')
            '''.format(days)
            
            if strategy_id:
                query += f" AND strategy_id = '{strategy_id}'"
            
            query += " ORDER BY timestamp DESC LIMIT 100"
            
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            conn.close()
            
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            self.log("ERROR", f"获取交易日志失败: {e}", "LOGGING", "ERROR_TRACKING")
            return []
    
    def get_system_health_summary(self) -> Dict:
        """获取系统健康状况摘要"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 最近24小时的错误统计
            cursor.execute('''
                SELECT COUNT(*) FROM enhanced_logs 
                WHERE level = 'ERROR' AND timestamp >= datetime('now', '-1 day')
            ''')
            error_count = cursor.fetchone()[0]
            
            # 最近的策略进化活动
            cursor.execute('''
                SELECT COUNT(*) FROM strategy_evolution_logs 
                WHERE timestamp >= datetime('now', '-1 day')
            ''')
            evolution_count = cursor.fetchone()[0]
            
            # 最近的交易活动
            cursor.execute('''
                SELECT COUNT(*) FROM auto_trading_logs 
                WHERE timestamp >= datetime('now', '-1 day')
            ''')
            trading_count = cursor.fetchone()[0]
            
            conn.close()
            
            health_status = "良好"
            if error_count > 10:
                health_status = "需要关注"
            elif error_count > 50:
                health_status = "异常"
            
            return {
                'health_status': health_status,
                'error_count_24h': error_count,
                'evolution_activity_24h': evolution_count,
                'trading_activity_24h': trading_count,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.log("ERROR", f"获取系统健康摘要失败: {e}", "LOGGING", "ERROR_TRACKING")
            return {'health_status': '未知', 'error': str(e)}

# 全局日志实例
_enhanced_logger = None

def get_enhanced_logger():
    """获取增强日志实例"""
    global _enhanced_logger
    if _enhanced_logger is None:
        _enhanced_logger = EnhancedLoggingSystem()
    return _enhanced_logger

def log_evolution(strategy_id: str, action_type: str, reason: str, **kwargs):
    """便捷的策略进化日志记录函数"""
    get_enhanced_logger().log_strategy_evolution(
        strategy_id=strategy_id,
        action_type=action_type,
        reason=reason,
        **kwargs
    )

def log_trading(action_type: str, **kwargs):
    """便捷的自动交易日志记录函数"""
    get_enhanced_logger().log_auto_trading(
        action_type=action_type,
        **kwargs
    )

def log_system(level: str, message: str, module: str = "SYSTEM", data: Optional[Dict] = None):
    """便捷的系统日志记录函数"""
    get_enhanced_logger().log(level, message, module, "SYSTEM_STATUS", data) 