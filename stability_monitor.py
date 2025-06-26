#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统稳定性监控脚本 - 量化系统2.0版本升级
增强系统监控、自动恢复和资源管理功能
"""

import psutil
import time
import logging
import subprocess
import os
import json
import sys
import signal
import threading
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# 配置日志系统
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
    def __init__(self, config_file="system_monitoring_config.json"):
        """
        增强版系统稳定性监控
        :param config_file: 监控配置文件路径
        """
        self.config = self._load_config(config_file)
        
        # 关键进程配置
        self.process_names = self.config.get("monitored_processes", ['python', 'quantitative'])
        self.critical_services = self.config.get("critical_services", ['web_app.py', 'quantitative_service.py'])
        self.restart_count = {}  # 进程重启计数 {process_name: count}
        self.max_restarts = self.config.get("max_restarts", 5)
        
        # 资源限制阈值
        self.memory_threshold = self.config.get("memory_threshold", 90)
        self.cpu_threshold = self.config.get("cpu_threshold", 90)
        self.disk_threshold = self.config.get("disk_threshold", 90)
        
        # 检测时间间隔
        self.check_interval = self.config.get("check_interval", 30)
        self.detailed_check_interval = self.config.get("detailed_check_interval", 300)
        
        # 健康状态追踪
        self.health_status = {
            "overall": "healthy",
            "memory": "normal",
            "cpu": "normal",
            "disk": "normal",
            "processes": "normal",
            "last_check": datetime.now().isoformat(),
            "incidents": []
        }
        
        # 自动恢复措施历史
        self.recovery_history = []
        
        # 优化资源列表
        self.resource_trackers = {}
        
        logger.info("🚀 增强版系统稳定性监控已初始化")
        
    def _load_config(self, config_file: str) -> Dict:
        """加载监控配置"""
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"配置文件 {config_file} 不存在，使用默认配置")
                return {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def _save_health_status(self):
        """保存健康状态到文件"""
        try:
            with open('logs/system_health.json', 'w') as f:
                json.dump(self.health_status, f, indent=2)
        except Exception as e:
            logger.error(f"保存健康状态失败: {e}")
            
    def _log_incident(self, incident_type: str, severity: str, details: str):
        """记录系统异常事件"""
        incident = {
            "type": incident_type,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
            "details": details
        }
        self.health_status["incidents"].append(incident)
        
        # 保持最近50条记录
        if len(self.health_status["incidents"]) > 50:
            self.health_status["incidents"] = self.health_status["incidents"][-50:]
            
        # 更新整体健康状态
        if severity == "critical":
            self.health_status["overall"] = "critical"
        elif severity == "warning" and self.health_status["overall"] != "critical":
            self.health_status["overall"] = "warning"
    
    def check_processes(self) -> List[Dict]:
        """检查关键进程运行状态"""
        running_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_percent', 'cpu_percent']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                
                # 检查是否为监控目标进程
                if any(name in cmdline for name in self.process_names):
                    # 补充进程资源使用信息
                    proc_info = {
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': cmdline,
                        'memory_percent': proc.info['memory_percent'],
                        'cpu_percent': proc.info['cpu_percent'],
                        'start_time': datetime.fromtimestamp(proc.create_time()).isoformat()
                    }
                    
                    # 添加额外的资源跟踪
                    try:
                        process = psutil.Process(proc.info['pid'])
                        proc_info['open_files'] = len(process.open_files())
                        proc_info['connections'] = len(process.connections())
                        proc_info['threads'] = process.num_threads()
                    except:
                        pass
                        
                    running_processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return running_processes
    
    def check_critical_services(self) -> Dict[str, bool]:
        """检查关键服务是否运行"""
        services_status = {}
        processes = self.check_processes()
        
        for service in self.critical_services:
            services_status[service] = any(service in proc.get('cmdline', '') for proc in processes)
            
        return services_status
    
    def restart_service(self, service_name: str) -> bool:
        """尝试重启指定服务"""
        try:
            # 检查重启次数限制
            if self.restart_count.get(service_name, 0) >= self.max_restarts:
                logger.warning(f"⚠️ {service_name} 已达到最大重启次数 {self.max_restarts}，不再自动重启")
                self._log_incident("restart_limit", "critical", 
                                  f"服务 {service_name} 已达到最大重启次数 {self.max_restarts}")
                return False
            
            logger.info(f"🔄 尝试重启服务: {service_name}")
            
            # 根据服务名确定重启命令
            restart_cmd = None
            if "web_app.py" in service_name:
                restart_cmd = f"python3 {service_name} &"
            elif "quantitative_service.py" in service_name:
                restart_cmd = f"python3 {service_name} &"
            else:
                restart_cmd = f"python3 {service_name} &"
            
            # 执行重启
            subprocess.Popen(restart_cmd, shell=True)
            
            # 更新重启计数
            self.restart_count[service_name] = self.restart_count.get(service_name, 0) + 1
            
            # 记录恢复操作
            recovery_record = {
                "timestamp": datetime.now().isoformat(),
                "action": "restart",
                "service": service_name,
                "restart_count": self.restart_count[service_name],
                "success": True
            }
            self.recovery_history.append(recovery_record)
            
            logger.info(f"✅ 服务 {service_name} 重启命令已执行")
            return True
            
        except Exception as e:
            logger.error(f"❌ 重启服务 {service_name} 失败: {e}")
            # 记录恢复操作
            recovery_record = {
                "timestamp": datetime.now().isoformat(),
                "action": "restart",
                "service": service_name,
                "success": False,
                "error": str(e)
            }
            self.recovery_history.append(recovery_record)
            return False
    
    def check_resource_usage(self) -> Dict:
        """检查系统资源使用情况"""
        # 内存使用
        memory = psutil.virtual_memory()
        memory_usage = {
            "total": memory.total / (1024 ** 3),  # GB
            "available": memory.available / (1024 ** 3),  # GB
            "percent": memory.percent,
            "status": "normal"
        }
        
        if memory.percent > self.memory_threshold:
            memory_usage["status"] = "warning"
            logger.warning(f"⚠️ 内存使用率过高: {memory.percent}%")
            self._log_incident("high_memory", "warning", f"内存使用率: {memory.percent}%")
            self.health_status["memory"] = "warning"
        else:
            self.health_status["memory"] = "normal"
            
        # CPU使用
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_usage = {
            "percent": cpu_percent,
            "status": "normal",
            "cores": psutil.cpu_count(),
            "per_core": psutil.cpu_percent(percpu=True)
        }
        
        if cpu_percent > self.cpu_threshold:
            cpu_usage["status"] = "warning"
            logger.warning(f"⚠️ CPU使用率过高: {cpu_percent}%")
            self._log_incident("high_cpu", "warning", f"CPU使用率: {cpu_percent}%")
            self.health_status["cpu"] = "warning"
        else:
            self.health_status["cpu"] = "normal"
            
        # 磁盘空间
        disk = psutil.disk_usage('/')
        disk_usage = {
            "total": disk.total / (1024 ** 3),  # GB
            "free": disk.free / (1024 ** 3),  # GB
            "percent": disk.percent,
            "status": "normal"
        }
        
        if disk.percent > self.disk_threshold:
            disk_usage["status"] = "warning"
            logger.warning(f"⚠️ 磁盘使用率过高: {disk.percent}%")
            self._log_incident("high_disk", "warning", f"磁盘使用率: {disk.percent}%")
            self.health_status["disk"] = "warning"
        else:
            self.health_status["disk"] = "normal"
        
        # 返回综合信息
        return {
            "memory": memory_usage,
            "cpu": cpu_usage,
            "disk": disk_usage,
            "timestamp": datetime.now().isoformat()
        }
    
    def optimize_resources(self):
        """优化系统资源使用"""
        try:
            # 检查内存使用情况
            memory = psutil.virtual_memory()
            if memory.percent > self.memory_threshold:
                logger.info(f"🧹 开始内存优化清理")
                
                # 优化步骤1: 清理Python缓存
                import gc
                collected = gc.collect()
                logger.info(f"✅ 垃圾收集优化: 回收了 {collected} 个对象")
                
                # 优化步骤2: 清理系统缓存 (仅Linux系统有效)
                if os.name == 'posix' and os.path.exists('/proc/sys/vm/drop_caches'):
                    try:
                        os.system('sync')
                        # 建议通过更安全的方式清理缓存
                        logger.info("✅ 系统缓存已同步")
                    except:
                        logger.error("❌ 清理系统缓存失败")
            
            # 检查是否有长时间未使用的资源
            current_time = time.time()
            for resource_id, tracker in list(self.resource_trackers.items()):
                if current_time - tracker['last_accessed'] > 3600:  # 1小时未使用
                    logger.info(f"🧹 释放长时间未使用的资源: {resource_id}")
                    del self.resource_trackers[resource_id]
        
        except Exception as e:
            logger.error(f"❌ 资源优化失败: {e}")
    
    def perform_detailed_healthcheck(self) -> Dict:
        """执行详细的系统健康检查"""
        health_report = {
            "timestamp": datetime.now().isoformat(),
            "system_uptime": self._get_uptime(),
            "python_threads": threading.active_count(),
            "open_files": len(psutil.Process().open_files()),
            "network_connections": len(psutil.Process().connections()),
            "resource_usage": self.check_resource_usage(),
            "processes": self.check_processes(),
            "services": self.check_critical_services(),
            "recovery_actions": len(self.recovery_history),
            "overall_status": self.health_status["overall"]
        }
        
        # 检查服务状态并尝试恢复
        services = health_report["services"]
        for service, is_running in services.items():
            if not is_running:
                logger.warning(f"⚠️ 关键服务 {service} 未运行!")
                self._log_incident("service_down", "critical", f"服务 {service} 未运行")
                
                # 尝试自动恢复
                self.restart_service(service)
                
                # 更新进程状态
                self.health_status["processes"] = "warning"
            else:
                logger.info(f"✅ 服务 {service} 正常运行")
        
        # 检查日志文件大小
        log_dir = "logs"
        if os.path.exists(log_dir):
            for log_file in os.listdir(log_dir):
                if log_file.endswith(".log"):
                    file_path = os.path.join(log_dir, log_file)
                    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                    if file_size > 100:  # 大于100MB
                        logger.warning(f"⚠️ 日志文件 {log_file} 过大: {file_size:.2f}MB")
                        self._log_incident("large_log", "warning", f"日志文件 {log_file} 大小: {file_size:.2f}MB")
                        
                        # 可选: 日志轮转
                        self._rotate_log_file(file_path)
        
        # 将健康报告保存到文件
        try:
            # 保存基本健康状态
            self._save_health_status()
            
            # 保存详细报告
            with open('logs/system_health_report.json', 'w') as f:
                json.dump(health_report, f, indent=2)
        except Exception as e:
            logger.error(f"❌ 保存健康报告失败: {e}")
            
        return health_report
    
    def _get_uptime(self) -> str:
        """获取系统运行时间"""
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            
            # 格式化为天、时、分、秒
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            return f"{days}天 {hours}小时 {minutes}分 {seconds}秒"
        except:
            return "未知"
    
    def _rotate_log_file(self, log_path: str):
        """日志文件轮转"""
        try:
            if not os.path.exists(log_path):
                return
                
            # 创建带时间戳的备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{log_path}.{timestamp}"
            
            # 重命名当前日志文件
            os.rename(log_path, backup_path)
            
            # 创建新的空日志文件
            with open(log_path, 'w') as f:
                f.write("")
                
            logger.info(f"✅ 日志文件已轮转: {log_path} → {backup_path}")
            
        except Exception as e:
            logger.error(f"❌ 日志轮转失败: {e}")
    
    def monitor_system(self):
        """监控系统状态"""
        logger.info("🔍 开始增强版系统稳定性监控...")
        
        last_detailed_check = time.time()
        
        try:
            while True:
                try:
                    current_time = time.time()
                    
                    # 基本资源检查
                    resource_status = self.check_resource_usage()
                    
                    # 进程检查
                    processes = self.check_processes()
                    if not processes:
                        logger.warning("⚠️ 未检测到关键进程运行")
                        self._log_incident("no_processes", "critical", "未检测到关键进程运行")
                        
                    # 定期详细检查
                    if current_time - last_detailed_check > self.detailed_check_interval:
                        logger.info("🔬 执行详细系统健康检查...")
                        self.perform_detailed_healthcheck()
                        self.optimize_resources()
                        last_detailed_check = current_time
                    
                    # 更新健康状态
                    self.health_status["last_check"] = datetime.now().isoformat()
                    
                    time.sleep(self.check_interval)
                    
                except KeyboardInterrupt:
                    logger.info("👋 监控停止")
                    break
                except Exception as e:
                    logger.error(f"❌ 监控周期出错: {e}")
                    logger.error(traceback.format_exc())
                    time.sleep(10)  # 错误后短暂暂停
                    
        except Exception as e:
            logger.critical(f"❌❌ 监控系统严重错误: {e}")
            logger.critical(traceback.format_exc())
        finally:
            # 保存最终状态
            self._save_health_status()
            logger.info("👋 监控系统已退出")


if __name__ == "__main__":
    monitor = StabilityMonitor()
    monitor.monitor_system()
