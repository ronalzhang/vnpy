#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最小化量化服务
解决导入和重启问题
"""

import sys
import os
import json
import sqlite3
import time
import logging
from datetime import datetime
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import threading

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/minimal_service.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MinimalQuantitativeService:
    """最小化量化服务"""
    
    def __init__(self):
        self.db_path = "quantitative.db"
        self.strategies = []
        self.balance = 10000.0
        self.running = True
        logger.info("✅ 最小化服务初始化")
    
    def init_database(self):
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建基础表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT DEFAULT 'momentum',
                    strategy_type TEXT DEFAULT 'momentum',
                    symbol TEXT DEFAULT 'BTCUSDT',
                    status TEXT DEFAULT 'active',
                    balance REAL DEFAULT 0,
                    total_return REAL DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    total_trades INTEGER DEFAULT 0,
                    final_score REAL DEFAULT 50,
                    created_time TEXT,
                    parameters TEXT DEFAULT '{}'
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS balance_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    balance REAL NOT NULL,
                    change_amount REAL DEFAULT 0,
                    change_reason TEXT DEFAULT '系统运行'
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ 数据库初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 数据库初始化失败: {e}")
            return False
    
    def load_strategies(self):
        """加载策略"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM strategies LIMIT 50")
            rows = cursor.fetchall()
            
            columns = [description[0] for description in cursor.description]
            self.strategies = []
            
            for row in rows:
                strategy = dict(zip(columns, row))
                # 确保参数是字典格式
                try:
                    strategy['parameters'] = json.loads(strategy.get('parameters', '{}'))
                except:
                    strategy['parameters'] = {}
                self.strategies.append(strategy)
            
            conn.close()
            logger.info(f"✅ 加载了 {len(self.strategies)} 个策略")
            return True
            
        except Exception as e:
            logger.error(f"❌ 加载策略失败: {e}")
            return False
    
    def get_strategies(self):
        """获取策略列表"""
        return {
            'success': True,
            'data': self.strategies,
            'total': len(self.strategies)
        }
    
    def get_balance_info(self):
        """获取余额信息"""
        return {
            'success': True,
            'balance': self.balance,
            'currency': 'USDT',
            'last_update': datetime.now().isoformat()
        }
    
    def get_system_status(self):
        """获取系统状态"""
        return {
            'success': True,
            'status': 'running',
            'uptime': 'stable',
            'strategies_count': len(self.strategies),
            'balance': self.balance,
            'last_check': datetime.now().isoformat()
        }
    
    def background_worker(self):
        """后台工作线程"""
        logger.info("🔄 后台工作线程启动")
        
        while self.running:
            try:
                # 简单的心跳检查
                time.sleep(30)
                logger.info(f"💓 系统正常运行，策略数: {len(self.strategies)}")
                
                # 简单的余额更新
                if len(self.strategies) > 0:
                    self.balance += 0.1  # 模拟小幅增长
                
            except Exception as e:
                logger.error(f"后台工作出错: {e}")
                time.sleep(10)
    
    def start(self):
        """启动服务"""
        try:
            # 初始化数据库
            if not self.init_database():
                return False
            
            # 加载策略
            if not self.load_strategies():
                return False
            
            # 启动后台线程
            worker_thread = threading.Thread(target=self.background_worker, daemon=True)
            worker_thread.start()
            
            logger.info("✅ 最小化服务启动成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 服务启动失败: {e}")
            return False
    
    def stop(self):
        """停止服务"""
        self.running = False
        logger.info("🛑 服务停止")

# 创建Flask应用
app = Flask(__name__)
CORS(app)

# 创建服务实例
service = MinimalQuantitativeService()

@app.route('/api/strategies', methods=['GET'])
def api_strategies():
    """获取策略API"""
    return jsonify(service.get_strategies())

@app.route('/api/balance', methods=['GET'])
def api_balance():
    """获取余额API"""
    return jsonify(service.get_balance_info())

@app.route('/api/system/status', methods=['GET'])
def api_system_status():
    """系统状态API"""
    return jsonify(service.get_system_status())

@app.route('/api/health', methods=['GET'])
def api_health():
    """健康检查API"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/')
def index():
    """主页"""
    return '''<!DOCTYPE html>
<html>
<head>
    <title>最小化量化交易系统</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>✅ 最小化量化交易系统</h1>
    <p>系统运行正常</p>
    <ul>
        <li><a href="/api/strategies">策略列表</a></li>
        <li><a href="/api/balance">余额信息</a></li>
        <li><a href="/api/system/status">系统状态</a></li>
        <li><a href="/api/health">健康检查</a></li>
    </ul>
</body>
</html>'''

def main():
    """主函数"""
    try:
        # 创建日志目录
        os.makedirs('logs', exist_ok=True)
        
        # 启动服务
        if service.start():
            logger.info("🚀 启动Web服务器...")
            app.run(host='0.0.0.0', port=8888, debug=False)
        else:
            logger.error("❌ 服务启动失败")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("👋 收到停止信号")
        service.stop()
    except Exception as e:
        logger.error(f"❌ 服务运行出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 