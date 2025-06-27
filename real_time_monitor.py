#!/usr/bin/env python3
"""
实时监控系统
监控策略性能、进化进度、系统状态等
"""

import psycopg2
import asyncio
import websockets
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import threading
import time

class RealTimeMonitor:
    """实时监控系统"""
    
    def __init__(self):
        self.logger = self._setup_logger()
        self.connected_clients = set()
        self.monitoring_data = {
            'strategies': {},
            'system_metrics': {},
            'evolution_progress': {},
            'alerts': []
        }
        self.running = False
        
    def _setup_logger(self):
        """设置日志"""
        logger = logging.getLogger('RealTimeMonitor')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host="localhost",
            database="quantitative",
            user="quant_user",
            password="123abc74531"
        )
    
    async def register_client(self, websocket, path):
        """注册新的WebSocket客户端"""
        self.connected_clients.add(websocket)
        self.logger.info(f"新客户端连接: {websocket.remote_address}")
        
        try:
            # 发送当前状态
            await websocket.send(json.dumps({
                'type': 'initial_state',
                'data': self.monitoring_data,
                'timestamp': datetime.now().isoformat()
            }))
            
            # 保持连接
            await websocket.wait_closed()
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.connected_clients.remove(websocket)
            self.logger.info(f"客户端断开连接: {websocket.remote_address}")
    
    async def broadcast_update(self, update_type: str, data: Dict[str, Any]):
        """广播更新到所有连接的客户端"""
        if not self.connected_clients:
            return
        
        message = json.dumps({
            'type': update_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
        
        # 广播到所有客户端
        dead_clients = set()
        for client in self.connected_clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                dead_clients.add(client)
        
        # 清理断开的连接
        self.connected_clients -= dead_clients
    
    def monitor_strategies(self):
        """监控策略性能"""
        while self.running:
            try:
                conn = self.get_db_connection()
                cursor = conn.cursor()
                
                # 获取策略基本信息
                cursor.execute("""
                    SELECT 
                        id, name, symbol, enabled, final_score,
                        created_at, updated_at, parameters,
                        (SELECT COUNT(*) FROM strategy_trades WHERE strategy_id = strategies.id) as trade_count,
                        (SELECT AVG(pnl) FROM strategy_trades WHERE strategy_id = strategies.id AND pnl IS NOT NULL) as avg_pnl,
                        (SELECT MAX(timestamp) FROM strategy_trades WHERE strategy_id = strategies.id) as last_trade
                    FROM strategies 
                    ORDER BY final_score DESC
                    LIMIT 20
                """)
                
                strategies = cursor.fetchall()
                strategy_data = {}
                
                for strategy in strategies:
                    strategy_id = strategy[0]
                    
                    # 获取最近24小时的交易统计
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as recent_trades,
                            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                            AVG(pnl) as avg_pnl_24h,
                            SUM(pnl) as total_pnl_24h
                        FROM strategy_trades 
                        WHERE strategy_id = %s 
                        AND timestamp >= %s
                    """, (strategy_id, datetime.now() - timedelta(hours=24)))
                    
                    recent_stats = cursor.fetchone()
                    if recent_stats is None:
                        recent_stats = (0, 0, 0, 0)
                    
                    # 获取进化记录
                    cursor.execute("""
                        SELECT generation, individual, score, parameters, timestamp
                        FROM evolution_logs 
                        WHERE strategy_id = %s 
                        ORDER BY timestamp DESC 
                        LIMIT 5
                    """, (strategy_id,))
                    
                    evolution_logs = cursor.fetchall()
                    
                    strategy_data[strategy_id] = {
                        'basic_info': {
                            'name': strategy[1],
                            'symbol': strategy[2],
                            'enabled': strategy[3],
                            'score': float(strategy[4] or 0),
                            'created_at': strategy[5].isoformat() if strategy[5] else None,
                            'updated_at': strategy[6].isoformat() if strategy[6] else None,
                            'parameters': json.loads(strategy[7]) if strategy[7] else {},
                            'total_trades': strategy[8] or 0,
                            'avg_pnl': float(strategy[9] or 0),
                            'last_trade': strategy[10].isoformat() if strategy[10] else None
                        },
                        'recent_performance': {
                            'trades_24h': recent_stats[0] or 0,
                            'winning_trades_24h': recent_stats[1] or 0,
                            'win_rate_24h': (recent_stats[1] or 0) / max(recent_stats[0] or 1, 1) * 100,
                            'avg_pnl_24h': float(recent_stats[2] or 0),
                            'total_pnl_24h': float(recent_stats[3] or 0)
                        },
                        'evolution_status': [
                            {
                                'generation': log[0],
                                'individual': log[1],
                                'score': float(log[2] or 0),
                                'parameters': json.loads(log[3]) if log[3] else {},
                                'timestamp': log[4].isoformat() if log[4] else None
                            }
                            for log in evolution_logs
                        ]
                    }
                
                # 更新监控数据
                self.monitoring_data['strategies'] = strategy_data
                
                # 异步广播更新
                asyncio.create_task(self.broadcast_update('strategy_update', strategy_data))
                
                conn.close()
                
            except Exception as e:
                self.logger.error(f"策略监控错误: {e}")
            
            time.sleep(10)  # 每10秒更新一次
    
    def monitor_system_metrics(self):
        """监控系统指标"""
        while self.running:
            try:
                import psutil
                
                # 系统资源使用情况
                system_metrics = {
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_usage': psutil.disk_usage('/').percent,
                    'network_io': dict(psutil.net_io_counters()._asdict()),
                    'process_count': len(psutil.pids()),
                    'timestamp': datetime.now().isoformat()
                }
                
                # 数据库连接状态
                try:
                    conn = self.get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT version()")
                    db_result = cursor.fetchone()
                    if db_result:
                        db_version = db_result[0]
                        system_metrics['database_status'] = 'online'
                        system_metrics['database_version'] = db_version
                    else:
                        system_metrics['database_status'] = 'offline'
                        system_metrics['database_error'] = 'No version returned'
                    conn.close()
                except Exception as e:
                    system_metrics['database_status'] = 'offline'
                    system_metrics['database_error'] = str(e)
                
                self.monitoring_data['system_metrics'] = system_metrics
                
                # 异步广播更新
                asyncio.create_task(self.broadcast_update('system_metrics', system_metrics))
                
            except Exception as e:
                self.logger.error(f"系统监控错误: {e}")
            
            time.sleep(30)  # 每30秒更新一次
    
    def start_monitoring(self):
        """启动监控"""
        self.running = True
        self.logger.info("启动实时监控系统")
        
        # 启动监控线程
        strategy_thread = threading.Thread(target=self.monitor_strategies)
        metrics_thread = threading.Thread(target=self.monitor_system_metrics)
        
        strategy_thread.daemon = True
        metrics_thread.daemon = True
        
        strategy_thread.start()
        metrics_thread.start()
        
        # 启动WebSocket服务器
        start_server = websockets.serve(
            self.register_client, 
            "localhost", 
            8765,
            max_size=1024*1024,  # 1MB
            max_queue=100
        )
        
        self.logger.info("WebSocket服务器启动在 ws://localhost:8765")
        
        return start_server
    
    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        self.logger.info("停止实时监控系统")

# 独立运行的监控服务
if __name__ == "__main__":
    monitor = RealTimeMonitor()
    
    # 启动监控
    loop = asyncio.get_event_loop()
    start_server = monitor.start_monitoring()
    
    try:
        loop.run_until_complete(start_server)
        loop.run_forever()
    except KeyboardInterrupt:
        monitor.stop_monitoring()
        print("监控系统已停止") 