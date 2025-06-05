#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动修复后的量化交易系统
特点：
1. 无自动交易风险 - 只进行策略优化
2. 真正的持续模拟和优化
3. 从历史高分策略继续工作
4. 完善的日志记录
"""

import sqlite3
import json
import time
import logging
import threading
from datetime import datetime
from flask import Flask, render_template, jsonify, request
import os

# 导入优化器
from real_continuous_optimization import RealContinuousOptimizer

class FixedQuantitativeSystem:
    """修复后的量化交易系统"""
    
    def __init__(self):
        self.db_path = "quantitative.db"
        self.logger = self._setup_logger()
        self.optimizer = None
        self.web_app = None
        
    def _setup_logger(self):
        logger = logging.getLogger("FixedSystem")
        logger.setLevel(logging.INFO)
        
        # 创建日志目录
        os.makedirs("logs/system", exist_ok=True)
        
        # 文件处理器
        file_handler = logging.FileHandler(
            f"logs/system/fixed_system_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setLevel(logging.INFO)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 格式器
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def create_web_app(self):
        """创建Web应用"""
        app = Flask(__name__)
        
        @app.route('/')
        def index():
            return render_template('dashboard.html')
        
        @app.route('/api/strategies')
        def get_strategies():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, name, symbol, type, final_score, win_rate, 
                           total_return, enabled, qualified_for_trading,
                           updated_at
                    FROM strategies 
                    ORDER BY final_score DESC 
                    LIMIT 100
                """)
                
                strategies = []
                for row in cursor.fetchall():
                    strategy = {
                        'id': row[0],
                        'name': row[1],
                        'symbol': row[2],
                        'type': row[3],
                        'final_score': row[4],
                        'win_rate': row[5],
                        'total_return': row[6],
                        'enabled': bool(row[7]),
                        'qualified_for_trading': bool(row[8]),
                        'updated_at': row[9]
                    }
                    strategies.append(strategy)
                
                conn.close()
                return jsonify(strategies)
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/status')
        def get_status():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # 统计数据
                cursor.execute("SELECT COUNT(*) FROM strategies")
                total_strategies = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM strategies WHERE final_score >= 50")
                high_score_strategies = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM strategies WHERE final_score >= 65")
                trading_ready = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM strategies WHERE enabled = 1")
                active_strategies = cursor.fetchone()[0]
                
                cursor.execute("SELECT MAX(final_score) FROM strategies")
                max_score = cursor.fetchone()[0] or 0
                
                cursor.execute("SELECT AVG(final_score) FROM strategies WHERE final_score > 0")
                avg_score = cursor.fetchone()[0] or 0
                
                # 系统状态
                cursor.execute("SELECT status FROM continuous_optimization_status WHERE id = 1")
                optimization_status = cursor.fetchone()
                optimization_status = optimization_status[0] if optimization_status else 'unknown'
                
                # 获取系统设置
                cursor.execute("SELECT value FROM system_settings WHERE key = 'auto_trading_enabled'")
                auto_trading = cursor.fetchone()
                auto_trading_enabled = auto_trading[0] == 'true' if auto_trading else False
                
                conn.close()
                
                status = {
                    'total_strategies': total_strategies,
                    'high_score_strategies': high_score_strategies,
                    'trading_ready_strategies': trading_ready,
                    'active_strategies': active_strategies,
                    'max_score': round(max_score, 2),
                    'avg_score': round(avg_score, 2),
                    'optimization_status': optimization_status,
                    'auto_trading_enabled': auto_trading_enabled,
                    'system_safe': not auto_trading_enabled,
                    'last_update': datetime.now().isoformat()
                }
                
                return jsonify(status)
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/optimization/start', methods=['POST'])
        def start_optimization():
            if self.optimizer and self.optimizer.running:
                return jsonify({'message': '优化系统已在运行'}), 400
            
            try:
                self.start_optimizer()
                return jsonify({'message': '优化系统启动成功'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/optimization/stop', methods=['POST'])
        def stop_optimization():
            if not self.optimizer or not self.optimizer.running:
                return jsonify({'message': '优化系统未在运行'}), 400
            
            try:
                self.optimizer.stop_optimization()
                return jsonify({'message': '优化系统已停止'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/safety/status')
        def safety_status():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT key, value FROM system_settings WHERE key IN ('auto_trading_enabled', 'trading_mode', 'emergency_stop_time')")
                settings = dict(cursor.fetchall())
                
                # 检查是否有启用的策略
                cursor.execute("SELECT COUNT(*) FROM strategies WHERE enabled = 1")
                enabled_count = cursor.fetchone()[0]
                
                conn.close()
                
                safety_info = {
                    'auto_trading_disabled': settings.get('auto_trading_enabled', 'false') == 'false',
                    'trading_mode': settings.get('trading_mode', 'manual'),
                    'emergency_stop_time': settings.get('emergency_stop_time'),
                    'enabled_strategies_count': enabled_count,
                    'is_safe': settings.get('auto_trading_enabled', 'false') == 'false' and enabled_count == 0,
                    'protection_level': 'MAXIMUM' if enabled_count == 0 else 'MEDIUM'
                }
                
                return jsonify(safety_info)
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        return app
    
    def start_optimizer(self):
        """启动优化器"""
        if self.optimizer and self.optimizer.running:
            self.logger.warning("优化器已在运行")
            return
        
        self.logger.info("🚀 启动持续优化器...")
        self.optimizer = RealContinuousOptimizer()
        self.optimizer.start_optimization()
        
        self.logger.info("✅ 持续优化器启动成功")
    
    def start_web_server(self):
        """启动Web服务器"""
        self.logger.info("🌐 启动Web服务器...")
        
        self.web_app = self.create_web_app()
        
        def run_web():
            try:
                self.web_app.run(
                    host='0.0.0.0',
                    port=8888,
                    debug=False,
                    threaded=True
                )
            except Exception as e:
                self.logger.error(f"Web服务器启动失败: {e}")
        
        web_thread = threading.Thread(target=run_web, daemon=True)
        web_thread.start()
        
        self.logger.info("✅ Web服务器启动成功 (端口:8888)")
    
    def monitor_system(self):
        """系统监控"""
        self.logger.info("📊 开始系统监控...")
        
        while True:
            try:
                # 每分钟检查一次系统状态
                time.sleep(60)
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # 统计策略数量
                cursor.execute("SELECT COUNT(*) FROM strategies WHERE final_score >= 65")
                trading_ready = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM strategies WHERE enabled = 1")
                enabled_strategies = cursor.fetchone()[0]
                
                cursor.execute("SELECT MAX(final_score) FROM strategies")
                max_score = cursor.fetchone()[0] or 0
                
                conn.close()
                
                self.logger.info(
                    f"📈 系统状态: 交易就绪策略={trading_ready}, "
                    f"启用策略={enabled_strategies}, 最高分={max_score:.1f}"
                )
                
                # 安全检查
                if enabled_strategies > 0:
                    self.logger.warning(f"⚠️ 发现 {enabled_strategies} 个启用的策略！自动禁用...")
                    
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE strategies SET enabled = 0")
                    conn.commit()
                    conn.close()
                    
                    self.logger.info("✅ 所有策略已自动禁用，确保资金安全")
                
            except Exception as e:
                self.logger.error(f"系统监控出错: {e}")
                time.sleep(60)
    
    def start_system(self):
        """启动整个系统"""
        self.logger.info("🎯 启动修复后的量化交易系统...")
        
        # 1. 启动持续优化
        self.start_optimizer()
        
        # 2. 启动Web服务器
        self.start_web_server()
        
        # 3. 等待Web服务器启动
        time.sleep(2)
        
        self.logger.info("✅ 系统启动完成!")
        self.logger.info("📋 系统特点:")
        self.logger.info("   ✓ 自动交易已完全禁用")
        self.logger.info("   ✓ 持续策略优化运行中")
        self.logger.info("   ✓ 历史高分策略已恢复")
        self.logger.info("   ✓ Web界面: http://localhost:8888")
        self.logger.info("   ✓ 资金安全保护激活")
        
        # 4. 开始监控
        self.monitor_system()

def main():
    """主函数"""
    system = FixedQuantitativeSystem()
    
    try:
        system.start_system()
    except KeyboardInterrupt:
        print("\n接收到停止信号...")
        if system.optimizer:
            system.optimizer.stop_optimization()
        print("系统已安全停止")
    except Exception as e:
        print(f"系统启动失败: {e}")

if __name__ == "__main__":
    main() 