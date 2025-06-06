#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统稳定性监控脚本
"""

import psutil
import time
import logging
import subprocess
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/stability_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class StabilityMonitor:
    def __init__(self):
        self.process_names = ['python', 'quantitative']
        self.restart_count = 0
        self.max_restarts = 5
        
    def check_processes(self):
        """检查关键进程"""
        running_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if any(name in ' '.join(proc.info['cmdline'] or []) for name in self.process_names):
                    running_processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return running_processes
    
    def monitor_system(self):
        """监控系统状态"""
        logger.info("🔍 开始系统稳定性监控...")
        
        while True:
            try:
                # 检查内存使用
                memory = psutil.virtual_memory()
                if memory.percent > 90:
                    logger.warning(f"⚠️ 内存使用率过高: {memory.percent}%")
                
                # 检查CPU使用
                cpu_percent = psutil.cpu_percent(interval=1)
                if cpu_percent > 90:
                    logger.warning(f"⚠️ CPU使用率过高: {cpu_percent}%")
                
                # 检查磁盘空间
                disk = psutil.disk_usage('/')
                if disk.percent > 90:
                    logger.warning(f"⚠️ 磁盘使用率过高: {disk.percent}%")
                
                # 检查关键进程
                processes = self.check_processes()
                if not processes:
                    logger.warning("⚠️ 未检测到关键进程运行")
                
                time.sleep(30)  # 每30秒检查一次
                
            except KeyboardInterrupt:
                logger.info("👋 监控停止")
                break
            except Exception as e:
                logger.error(f"❌ 监控出错: {e}")
                time.sleep(10)

if __name__ == "__main__":
    monitor = StabilityMonitor()
    monitor.monitor_system()
