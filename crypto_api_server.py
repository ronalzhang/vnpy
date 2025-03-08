#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
加密货币套利监控API服务器
- 提供RESTful API接口
- 基于Flask实现
- 在8888端口提供服务
"""

import sys
import json
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# 添加项目路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

# 导入Flask
from flask import Flask, jsonify, request

# 导入自定义模块
from vnpy_cryptoarbitrage.engine import CryptoArbitrageEngine
from vnpy_cryptoarbitrage.utility import load_json, save_json

# 配置文件路径
CONFIG_FILE = "crypto_config.json"
CONFIG_PATH = Path(current_dir).joinpath(CONFIG_FILE)

# 创建Flask应用
app = Flask(__name__)

# 创建套利引擎
engine = None
prices_data = {}
diff_data = []
status = {
    "running": False,
    "mode": "simulate",
    "last_update": "",
    "trading_enabled": False
}

# 初始化套利引擎
def init_engine(simulate=True, verbose=False, enable_trading=False):
    global engine, status
    
    # 加载配置
    config = load_config()
    
    # 创建引擎
    engine = CryptoArbitrageEngine()
    
    # 初始化引擎
    engine.init_engine(
        settings=config,
        verbose=verbose,
        enable_trading=enable_trading,
        simulate=simulate
    )
    
    # 更新状态
    status["running"] = True
    status["mode"] = "simulate" if simulate else "real"
    status["trading_enabled"] = enable_trading
    status["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return engine

# 加载配置
def load_config():
    """加载配置文件"""
    try:
        if not CONFIG_PATH.exists():
            print(f"配置文件不存在: {CONFIG_PATH}")
            return {}
        
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        return config
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        return {}

# 监控线程
def monitor_thread(interval=10):
    global engine, prices_data, diff_data, status
    
    while status["running"]:
        try:
            # 获取价格数据
            if engine:
                # 更新价格
                if status["mode"] == "simulate":
                    prices = engine.generate_simulated_data()
                else:
                    prices = engine.fetch_all_prices()
                
                prices_data = prices
                
                # 计算价差
                diff = engine.calculate_price_differences(prices)
                diff_data = diff
                
                # 更新时间
                status["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 检查套利机会
                engine.log_arbitrage_opportunity(diff)
                
                # 在交易模式下执行套利
                if status["trading_enabled"]:
                    engine.execute_arbitrage(diff)
        
        except Exception as e:
            print(f"监控线程错误: {e}")
        
        time.sleep(interval)

# API路由
@app.route('/api/status', methods=['GET'])
def get_status():
    """获取服务器状态"""
    return jsonify(status)

@app.route('/api/prices', methods=['GET'])
def get_prices():
    """获取所有价格数据"""
    return jsonify(prices_data)

@app.route('/api/diff', methods=['GET'])
def get_diff():
    """获取价格差异数据"""
    return jsonify(diff_data)

@app.route('/api/symbols', methods=['GET'])
def get_symbols():
    """获取交易对列表"""
    if engine:
        return jsonify(engine.symbols)
    return jsonify([])

@app.route('/api/start', methods=['POST'])
def start_monitor():
    """启动监控"""
    global status
    
    data = request.get_json() or {}
    simulate = data.get('simulate', True)
    enable_trading = data.get('enable_trading', False)
    verbose = data.get('verbose', False)
    
    # 初始化引擎
    init_engine(simulate, verbose, enable_trading)
    
    return jsonify({"status": "success", "message": "监控已启动"})

@app.route('/api/stop', methods=['POST'])
def stop_monitor():
    """停止监控"""
    global status
    
    status["running"] = False
    
    return jsonify({"status": "success", "message": "监控已停止"})

# 主函数
def main():
    """主函数"""
    global engine
    
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description="加密货币套利监控API服务器")
    parser.add_argument("--simulate", action="store_true", help="使用模拟数据（无需API连接）")
    parser.add_argument("--real", action="store_true", help="使用真实API连接")
    parser.add_argument("--trade", action="store_true", help="启用交易功能")
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")
    parser.add_argument("--interval", type=int, default=10, help="监控间隔（秒）")
    parser.add_argument("--port", type=int, default=8888, help="API服务器端口")
    args = parser.parse_args()
    
    # 欢迎信息
    print("\n===== 加密货币套利监控API服务器 =====")
    print(f"运行模式: {'模拟数据' if args.simulate else '真实API连接'}")
    print(f"交易功能: {'已启用' if args.trade else '未启用（仅监控）'}")
    print(f"监控间隔: {args.interval} 秒")
    print(f"API端口: {args.port}")
    print("======================================\n")
    
    # 初始化引擎
    use_simulate = not args.real or args.simulate
    init_engine(simulate=use_simulate, verbose=args.verbose, enable_trading=args.trade)
    
    # 启动监控线程
    monitor = threading.Thread(target=monitor_thread, args=(args.interval,))
    monitor.daemon = True
    monitor.start()
    
    # 启动API服务器
    app.run(host='0.0.0.0', port=args.port, debug=False)

if __name__ == "__main__":
    main() 