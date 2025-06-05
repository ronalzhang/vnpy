#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
量化交易前端Web应用 - 优化版本
通过HTTP API与后端通信，避免数据库并发冲突
"""

import sys
import json
import time
import random
import threading
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from loguru import logger
import ccxt

from flask import Flask, jsonify, render_template, request, Response
import os

# 后端API配置
BACKEND_API_BASE = 'http://127.0.0.1:5000'  # 后端API地址
QUANTITATIVE_ENABLED = True

# API辅助函数
def call_backend_api(endpoint: str, method: str = 'GET', data: Dict = None) -> Dict:
    """调用后端API"""
    try:
        url = f"{BACKEND_API_BASE}{endpoint}"
        if method == 'GET':
            response = requests.get(url, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=10)
        else:
            response = requests.request(method, url, json=data, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"API调用失败: {endpoint}, 状态码: {response.status_code}")
            return {'error': f'API调用失败: {response.status_code}'}
    except requests.exceptions.RequestException as e:
        logger.error(f"API调用异常: {endpoint}, 错误: {e}")
        return {'error': f'API调用异常: {str(e)}'}

# 导入套利系统模块
try:
    from integrate_arbitrage import init_arbitrage_system
    ARBITRAGE_ENABLED = True
except ImportError:
    logger.warning("套利系统模块未找到，套利功能将被禁用")
    ARBITRAGE_ENABLED = False

# 创建Flask应用
app = Flask(__name__)

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/strategies')
def get_strategies():
    """获取策略列表"""
    return call_backend_api('/api/strategies')

@app.route('/api/system/status')
def get_system_status():
    """获取系统状态"""
    return call_backend_api('/api/system/status')

@app.route('/api/account/info')
def get_account_info():
    """获取账户信息"""
    return call_backend_api('/api/account/info')

@app.route('/api/signals')
def get_signals():
    """获取交易信号"""
    limit = request.args.get('limit', 50)
    return call_backend_api(f'/api/signals?limit={limit}')

@app.route('/api/balance/history')
def get_balance_history():
    """获取余额历史"""
    days = request.args.get('days', 30)
    return call_backend_api(f'/api/balance/history?days={days}')

@app.route('/api/strategy/<strategy_id>', methods=['GET'])
def get_strategy_detail(strategy_id):
    """获取策略详情"""
    return call_backend_api(f'/api/strategy/{strategy_id}')

@app.route('/api/strategy/<strategy_id>', methods=['PUT'])
def update_strategy(strategy_id):
    """更新策略"""
    data = request.get_json()
    return call_backend_api(f'/api/strategy/{strategy_id}', 'PUT', data)

@app.route('/api/strategy/<strategy_id>/toggle', methods=['POST'])
def toggle_strategy(strategy_id):
    """启用/禁用策略"""
    return call_backend_api(f'/api/strategy/{strategy_id}/toggle', 'POST')

@app.route('/api/auto-trading', methods=['POST'])
def set_auto_trading():
    """设置自动交易"""
    data = request.get_json()
    return call_backend_api('/api/auto-trading', 'POST', data)

@app.route('/api/evolution/status')
def get_evolution_status():
    """获取进化状态"""
    return call_backend_api('/api/evolution/status')

@app.route('/api/evolution/toggle', methods=['POST'])
def toggle_evolution():
    """启用/禁用进化"""
    data = request.get_json()
    return call_backend_api('/api/evolution/toggle', 'POST', data)

@app.route('/api/evolution/manual', methods=['POST'])
def manual_evolution():
    """手动进化"""
    return call_backend_api('/api/evolution/manual', 'POST')

@app.route('/api/logs/operations')
def get_operation_logs():
    """获取操作日志"""
    limit = request.args.get('limit', 50)
    return call_backend_api(f'/api/logs/operations?limit={limit}')

@app.route('/health')
def health_check():
    """健康检查"""
    # 检查后端连接
    backend_status = call_backend_api('/health')
    if 'error' in backend_status:
        return jsonify({
            'status': 'unhealthy',
            'frontend': 'ok',
            'backend': 'error',
            'error': backend_status['error']
        }), 503
    
    return jsonify({
        'status': 'healthy',
        'frontend': 'ok',
        'backend': 'ok',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='量化交易前端服务')
    parser.add_argument('--port', type=int, default=8888, help='端口号')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    parser.add_argument('--backend', type=str, default='http://127.0.0.1:5000', help='后端API地址')
    
    args = parser.parse_args()
    
    # 更新后端API地址
    BACKEND_API_BASE = args.backend
    
    print(f"🌐 量化交易前端启动中...")
    print(f"📡 后端API地址: {BACKEND_API_BASE}")
    print(f"🚀 前端服务地址: http://0.0.0.0:{args.port}")
    
    # 启动Flask应用
    app.run(
        host='0.0.0.0',
        port=args.port,
        debug=args.debug,
        threaded=True
    ) 