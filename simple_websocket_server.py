#!/usr/bin/env python3
"""
简化的WebSocket服务器
专门用于量化交易系统的实时数据推送
"""
import asyncio
import websockets
import json
import psycopg2
import logging
from datetime import datetime, timedelta
from typing import Set, Any
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 存储连接的客户端
connected_clients: Set[Any] = set()

def get_db_connection():
    """获取数据库连接"""
    try:
        return psycopg2.connect(
            host="localhost",
            database="quantitative", 
            user="quant_user",
            password="123abc74531"
        )
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        return None

async def register_client(websocket, path):
    """注册新的WebSocket客户端"""
    global connected_clients
    connected_clients.add(websocket)
    logger.info(f"新客户端连接: {websocket.remote_address}")
    
    try:
        # 发送欢迎消息
        await websocket.send(json.dumps({
            'type': 'welcome',
            'message': '欢迎连接量化交易实时监控',
            'timestamp': datetime.now().isoformat()
        }))
        
        # 发送初始数据
        initial_data = get_latest_strategies()
        if initial_data:
            await websocket.send(json.dumps({
                'type': 'initial_data',
                'data': initial_data,
                'timestamp': datetime.now().isoformat()
            }))
        
        # 保持连接
        await websocket.wait_closed()
        
    except websockets.exceptions.ConnectionClosed:
        logger.info("客户端正常断开连接")
    except Exception as e:
        logger.error(f"客户端连接错误: {e}")
    finally:
        connected_clients.discard(websocket)
        logger.info("客户端已从连接列表移除")

async def broadcast_to_clients(message_type: str, data):
    """广播消息到所有连接的客户端"""
    global connected_clients
    if not connected_clients:
        return
    
    message = json.dumps({
        'type': message_type,
        'data': data,
        'timestamp': datetime.now().isoformat()
    })
    
    # 创建发送任务列表
    disconnected_clients = set()
    
    for client in connected_clients.copy():
        try:
            await client.send(message)
        except websockets.exceptions.ConnectionClosed:
            disconnected_clients.add(client)
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            disconnected_clients.add(client)
    
    # 清理断开的连接
    connected_clients -= disconnected_clients
    
    if disconnected_clients:
        logger.info(f"清理了 {len(disconnected_clients)} 个断开的连接")

def get_latest_strategies():
    """获取最新策略数据"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                id, name, symbol, enabled, final_score,
                created_at, updated_at,
                (SELECT COUNT(*) FROM strategy_trades WHERE strategy_id = strategies.id) as trade_count,
                (SELECT MAX(timestamp) FROM strategy_trades WHERE strategy_id = strategies.id) as last_trade
            FROM strategies 
            ORDER BY final_score DESC
            LIMIT 10
        """)
        
        strategies = cursor.fetchall()
        result = []
        
        for strategy in strategies:
            result.append({
                'id': strategy[0],
                'name': strategy[1],
                'symbol': strategy[2],
                'enabled': strategy[3],
                'score': float(strategy[4] or 0),
                'created_at': strategy[5].isoformat() if strategy[5] else None,
                'updated_at': strategy[6].isoformat() if strategy[6] else None,
                'trade_count': strategy[7] or 0,
                'last_trade': strategy[8].isoformat() if strategy[8] else None
            })
        
        conn.close()
        return result
        
    except Exception as e:
        logger.error(f"获取策略数据失败: {e}")
        if conn:
            conn.close()
        return None

def get_latest_evolution_logs():
    """获取最新进化日志"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                strategy_id, action, details, timestamp
            FROM strategy_optimization_logs
            ORDER BY timestamp DESC
            LIMIT 50
        """)
        
        logs = cursor.fetchall()
        result = []
        
        for log in logs:
            result.append({
                'strategy_id': log[0],
                'action': log[1],
                'details': log[2],
                'timestamp': log[3].isoformat() if log[3] else None
            })
        
        conn.close()
        return result
        
    except Exception as e:
        logger.error(f"获取进化日志失败: {e}")
        if conn:
            conn.close()
        return []

async def periodic_data_update():
    """定期数据更新"""
    while True:
        try:
            if connected_clients:
                # 获取策略数据
                strategies = get_latest_strategies()
                if strategies:
                    await broadcast_to_clients('strategy_update', strategies)
                
                # 获取进化日志
                evolution_logs = get_latest_evolution_logs()
                if evolution_logs:
                    await broadcast_to_clients('evolution_update', evolution_logs)
                
                logger.info(f"数据更新完成，活跃连接: {len(connected_clients)}")
            
        except Exception as e:
            logger.error(f"定期数据更新错误: {e}")
        
        # 每30秒更新一次
        await asyncio.sleep(30)

async def main():
    """主函数"""
    logger.info("启动简化WebSocket服务器...")
    
    # 启动定期数据更新任务
    update_task = asyncio.create_task(periodic_data_update())
    
    # 启动WebSocket服务器
    server = await websockets.serve(
        register_client,
        "0.0.0.0",  # 监听所有接口
        8765,
        max_size=1024*1024,  # 1MB
        max_queue=100,
        ping_interval=20,
        ping_timeout=10
    )
    
    logger.info("WebSocket服务器启动成功: ws://0.0.0.0:8765")
    
    try:
        # 等待服务器和更新任务
        await asyncio.gather(server.wait_closed(), update_task)
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭服务器...")
        server.close()
        await server.wait_closed()
        update_task.cancel()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("WebSocket服务器已停止") 