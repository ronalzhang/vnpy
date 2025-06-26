#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动交易系统启动脚本
提供便捷的启动、监控和管理功能

作者: 系统架构优化团队
日期: 2025年6月8日
"""

import os
import sys
import time
import argparse
import json
import logging
import signal
import subprocess
import psutil
from datetime import datetime
import traceback

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/launcher.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 主组件列表
CORE_COMPONENTS = [
    {
        "name": "市场环境分类器",
        "script": "market_environment_classifier.py",
        "required": False
    },
    {
        "name": "策略资源分配器",
        "script": "strategy_resource_allocator.py",
        "required": False
    },
    {
        "name": "自动交易引擎",
        "script": "auto_trading_engine.py",
        "required": True
    }
]

# 可选组件
OPTIONAL_COMPONENTS = [
    {
        "name": "稳定性监控",
        "script": "stability_monitor.py",
        "enable_flag": "monitor"
    },
    {
        "name": "交易状态监控",
        "script": "trading_monitor.py",
        "enable_flag": "monitor"
    }
]


def check_environment():
    """检查环境准备情况"""
    # 检查必要目录
    required_dirs = ['logs', 'data', 'backups']
    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            logger.info(f"创建目录: {dir_name}")
            os.makedirs(dir_name, exist_ok=True)
    
    # 检查配置文件
    required_configs = [
        'auto_trading_config.json',
        'market_classifier_config.json',
        'resource_allocator_config.json',
        'system_monitoring_config.json'
    ]
    
    missing_configs = []
    for config_file in required_configs:
        if not os.path.exists(config_file):
            missing_configs.append(config_file)
    
    if missing_configs:
        logger.warning(f"缺少配置文件: {', '.join(missing_configs)}")
        return False
    
    # 检查数据库
    db_file = "quantitative.db"
    if not os.path.exists(db_file):
        logger.warning(f"数据库文件不存在: {db_file}")
        return False
    
    logger.info("环境检查完成，一切就绪")
    return True


def check_process_status(process_name):
    """检查进程是否在运行"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if process_name in cmdline:
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None


def start_component(component, mode="background"):
    """启动组件"""
    script = component["script"]
    
    if check_process_status(script):
        logger.info(f"{component['name']}已经在运行")
        return True
    
    try:
        cmd = [sys.executable, script]
        
        if mode == "foreground":
            logger.info(f"前台启动 {component['name']}")
            return subprocess.call(cmd)
        else:
            logger.info(f"后台启动 {component['name']}")
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # 等待片刻，检查进程是否成功启动
            time.sleep(2)
            if proc.poll() is None:
                logger.info(f"{component['name']}启动成功 (PID: {proc.pid})")
                return True
            else:
                stdout, stderr = proc.communicate()
                logger.error(f"{component['name']}启动失败: {stderr}")
                return False
    except Exception as e:
        logger.error(f"启动{component['name']}时出错: {e}")
        return False


def stop_component(component):
    """停止组件"""
    script = component["script"]
    pid = check_process_status(script)
    
    if not pid:
        logger.info(f"{component['name']}没有运行")
        return True
    
    try:
        proc = psutil.Process(pid)
        logger.info(f"正在停止 {component['name']} (PID: {pid})")
        
        # 先尝试正常终止
        proc.terminate()
        
        # 等待进程结束
        gone, alive = psutil.wait_procs([proc], timeout=5)
        
        if alive:
            # 强制终止
            logger.warning(f"{component['name']}没有正常终止，强制终止")
            for p in alive:
                p.kill()
        
        logger.info(f"{component['name']}已停止")
        return True
    except Exception as e:
        logger.error(f"停止{component['name']}时出错: {e}")
        return False


def check_status():
    """检查所有组件状态"""
    print("\n系统组件状态:\n" + "="*50)
    print(f"{'组件名称':<20} {'状态':<10} {'PID':<10} {'运行时间'}")
    print("-"*50)
    
    all_components = CORE_COMPONENTS + OPTIONAL_COMPONENTS
    
    for component in all_components:
        script = component["script"]
        pid = check_process_status(script)
        
        if pid:
            try:
                proc = psutil.Process(pid)
                start_time = datetime.fromtimestamp(proc.create_time())
                uptime = datetime.now() - start_time
                hours, remainder = divmod(uptime.total_seconds(), 3600)
                minutes, seconds = divmod(remainder, 60)
                uptime_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
                
                status = "运行中"
            except:
                status = "错误"
                uptime_str = "N/A"
        else:
            status = "未运行"
            pid = "N/A"
            uptime_str = "N/A"
        
        print(f"{component['name']:<20} {status:<10} {pid:<10} {uptime_str}")
    
    # 检查自动交易引擎状态
    try:
        status_file = "data/auto_trading_status.json"
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                engine_status = json.load(f)
                
            print("\n自动交易引擎详细状态:\n" + "="*50)
            print(f"状态: {engine_status.get('status', 'unknown')}")
            print(f"市场状态: {engine_status.get('market_state', 'unknown')}")
            print(f"活跃策略数: {engine_status.get('active_strategies', 0)}")
            print(f"运行时间: {engine_status.get('uptime', 0)} 小时")
            print(f"最后交易时间: {engine_status.get('last_trade_time', 'N/A')}")
            
            # 显示性能指标
            performance = engine_status.get('performance', {})
            if performance:
                print("\n性能指标:")
                print(f"预期收益: {performance.get('expected_return', 0)}")
                print(f"预期风险: {performance.get('expected_risk', 0)}")
                print(f"夏普比率: {performance.get('sharpe_ratio', 0)}")
                print(f"胜率: {performance.get('win_rate', 0)}")
                print(f"分散度: {performance.get('diversification', 0)}")
            
            # 显示错误信息
            errors = engine_status.get('errors', [])
            if errors:
                print("\n最近错误:")
                for error in errors[-3:]:  # 只显示最近3个错误
                    print(f"- {error.get('time', '')}: {error.get('error', '')}")
    except Exception as e:
        print(f"\n获取引擎状态失败: {e}")


def start_all(args):
    """启动所有组件"""
    logger.info("准备启动全部组件...")
    
    # 检查环境
    if not args.force and not check_environment():
        logger.error("环境检查未通过，启动终止")
        return False
    
    # 先启动核心组件
    for component in CORE_COMPONENTS:
        if component["required"] or not args.minimal:
            start_component(component)
            # 等待一下，确保组件有序启动
            time.sleep(2)
    
    # 启动可选组件
    if args.monitor:
        for component in OPTIONAL_COMPONENTS:
            if component.get("enable_flag") == "monitor":
                start_component(component)
                time.sleep(1)
    
    logger.info("所有组件已启动")
    return True


def stop_all():
    """停止所有组件"""
    logger.info("准备停止所有组件...")
    
    # 按相反顺序停止组件
    all_components = OPTIONAL_COMPONENTS + CORE_COMPONENTS
    all_components.reverse()
    
    for component in all_components:
        stop_component(component)
        # 等待进程完全结束
        time.sleep(1)
    
    logger.info("所有组件已停止")
    return True


def restart_all(args):
    """重启所有组件"""
    logger.info("准备重启所有组件...")
    
    stop_all()
    time.sleep(2)
    start_all(args)
    
    logger.info("所有组件已重启")
    return True


def backup_data():
    """备份数据"""
    try:
        import shutil
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"backups/backup_{timestamp}"
        os.makedirs(backup_dir, exist_ok=True)
        
        # 备份数据库
        if os.path.exists("quantitative.db"):
            shutil.copy2("quantitative.db", f"{backup_dir}/quantitative.db")
        
        # 备份配置文件
        for config_file in ['auto_trading_config.json', 'market_classifier_config.json', 
                          'resource_allocator_config.json', 'system_monitoring_config.json']:
            if os.path.exists(config_file):
                shutil.copy2(config_file, f"{backup_dir}/{config_file}")
        
        # 备份状态文件
        if os.path.exists("data/auto_trading_status.json"):
            os.makedirs(f"{backup_dir}/data", exist_ok=True)
            shutil.copy2("data/auto_trading_status.json", f"{backup_dir}/data/auto_trading_status.json")
        
        logger.info(f"数据已备份到: {backup_dir}")
        return True
    except Exception as e:
        logger.error(f"备份数据失败: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="自动交易系统管理工具")
    
    # 主要命令
    command_group = parser.add_mutually_exclusive_group(required=True)
    command_group.add_argument('--start', action='store_true', help='启动系统')
    command_group.add_argument('--stop', action='store_true', help='停止系统')
    command_group.add_argument('--restart', action='store_true', help='重启系统')
    command_group.add_argument('--status', action='store_true', help='查看系统状态')
    command_group.add_argument('--backup', action='store_true', help='备份数据')
    
    # 额外选项
    parser.add_argument('--force', action='store_true', help='强制启动，跳过环境检查')
    parser.add_argument('--minimal', action='store_true', help='仅启动必需组件')
    parser.add_argument('--monitor', action='store_true', help='启用监控组件')
    
    args = parser.parse_args()
    
    # 设置工作目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # 创建必要的目录
    os.makedirs("logs", exist_ok=True)
    
    try:
        if args.start:
            start_all(args)
        elif args.stop:
            stop_all()
        elif args.restart:
            restart_all(args)
        elif args.status:
            check_status()
        elif args.backup:
            backup_data()
    except Exception as e:
        logger.error(f"操作失败: {e}")
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 