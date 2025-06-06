#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全启动脚本
确保系统稳定启动
"""

import os
import sys
import time
import logging
import subprocess
import signal
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/safe_startup.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SafeStartup:
    def __init__(self):
        self.processes = []
        self.running = True
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}，开始优雅关闭...")
        self.running = False
        self.cleanup()
    
    def pre_startup_check(self):
        """启动前检查"""
        logger.info("🔍 进行启动前检查...")
        
        # 检查数据库
        if not os.path.exists("quantitative.db"):
            logger.error("❌ 数据库文件不存在")
            return False
        
        # 检查日志目录
        Path("logs").mkdir(exist_ok=True)
        
        # 检查关键文件
        critical_files = [
            "quantitative_service.py",
            "enhanced_strategy_evolution.py"
        ]
        
        for file_path in critical_files:
            if not os.path.exists(file_path):
                logger.error(f"❌ 关键文件缺失: {file_path}")
                return False
        
        logger.info("✅ 启动前检查通过")
        return True
    
    def start_services(self):
        """启动服务"""
        if not self.pre_startup_check():
            logger.error("❌ 启动前检查失败，终止启动")
            return False
        
        logger.info("🚀 开始启动服务...")
        
        try:
            # 启动量化服务
            proc = subprocess.Popen([
                sys.executable, "quantitative_service.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.processes.append(proc)
            logger.info("✅ 量化服务启动成功")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 服务启动失败: {e}")
            return False
    
    def monitor_services(self):
        """监控服务状态"""
        logger.info("🔍 开始监控服务状态...")
        
        restart_count = 0
        max_restarts = 3
        
        while self.running:
            try:
                # 检查进程状态
                active_processes = []
                for proc in self.processes:
                    if proc.poll() is None:  # 进程仍在运行
                        active_processes.append(proc)
                    else:
                        logger.warning(f"⚠️ 进程已退出: PID {proc.pid}")
                        
                        # 重启服务
                        if restart_count < max_restarts:
                            logger.info("🔄 尝试重启服务...")
                            if self.start_services():
                                restart_count += 1
                                logger.info(f"✅ 服务重启成功 ({restart_count}/{max_restarts})")
                            else:
                                logger.error("❌ 服务重启失败")
                        else:
                            logger.error("❌ 达到最大重启次数，停止监控")
                            self.running = False
                
                self.processes = active_processes
                time.sleep(10)  # 每10秒检查一次
                
            except KeyboardInterrupt:
                logger.info("👋 监控停止")
                self.running = False
            except Exception as e:
                logger.error(f"❌ 监控出错: {e}")
                time.sleep(5)
    
    def cleanup(self):
        """清理资源"""
        logger.info("🧹 开始清理资源...")
        
        for proc in self.processes:
            try:
                proc.terminate()
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
            except Exception as e:
                logger.error(f"清理进程失败: {e}")
        
        logger.info("✅ 资源清理完成")
    
    def run(self):
        """运行安全启动器"""
        try:
            if self.start_services():
                self.monitor_services()
            else:
                logger.error("❌ 初始启动失败")
        finally:
            self.cleanup()

if __name__ == "__main__":
    startup = SafeStartup()
    startup.run()
