#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
自动交易系统启动脚本
一键启动100U→1万U投资计划
"""

import os
import sys
import time
import json
import threading
from datetime import datetime
from loguru import logger

def setup_logging():
    """设置日志配置"""
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    
    logger.configure(
        handlers=[
            {"sink": sys.stdout, "format": log_format, "level": "INFO"},
            {"sink": "logs/auto_trading_{time}.log", "format": log_format, "level": "DEBUG", "rotation": "1 day"}
        ]
    )

def check_dependencies():
    """检查依赖包"""
    try:
        import ccxt
        import pandas
        import numpy
        logger.success("✅ 依赖包检查通过")
        return True
    except ImportError as e:
        logger.error(f"❌ 缺少依赖包: {e}")
        logger.info("请运行: pip install -r requirements.txt")
        return False

def check_config():
    """检查配置文件"""
    if not os.path.exists('crypto_config.json'):
        logger.error("❌ 未找到配置文件 crypto_config.json")
        return False
    
    try:
        with open('crypto_config.json', 'r') as f:
            config = json.load(f)
        
        binance_config = config.get('binance', {})
        if not binance_config.get('api_key') or not binance_config.get('secret_key'):
            logger.error("❌ 币安API配置不完整")
            return False
        
        logger.success("✅ 配置文件检查通过")
        return True
    except Exception as e:
        logger.error(f"❌ 配置文件错误: {e}")
        return False

def start_web_service():
    """启动Web服务"""
    try:
        from web_app import app
        
        # 在后台线程启动Flask应用
        def run_flask():
            app.run(host='0.0.0.0', port=8888, debug=False, use_reloader=False)
        
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        logger.success("✅ Web服务已启动 (端口8888)")
        return True
    except Exception as e:
        logger.error(f"❌ Web服务启动失败: {e}")
        return False

def start_auto_trading():
    """启动自动交易"""
    try:
        from auto_trading_engine import get_trading_engine
        
        # 初始化交易引擎
        trading_engine = get_trading_engine()
        status = trading_engine.get_status()
        
        logger.info(f"💰 当前余额: {status['balance']:.2f} USDT")
        
        if status['balance'] < 100:
            logger.warning(f"⚠️ 余额不足100U，当前: {status['balance']:.2f} USDT")
            logger.info("建议先充值到100U以上再启动投资计划")
            return False
        
        logger.success("✅ 自动交易引擎已初始化")
        return True
    except Exception as e:
        logger.error(f"❌ 自动交易引擎启动失败: {e}")
        return False

def start_investment_plan():
    """启动投资计划"""
    try:
        from investment_plan import InvestmentPlan
        
        # 创建投资计划
        plan = InvestmentPlan()
        
        # 启动计划
        if plan.start_plan():
            logger.success("🚀 100U→1万U投资计划已启动")
            
            # 显示当前阶段信息
            phase = plan.get_current_phase()
            logger.info(f"🎯 当前阶段: {phase['name']}")
            logger.info(f"📈 目标收益: {phase['daily_target']*100:.1f}%/日")
            logger.info(f"⚡ 激进模式: 最大仓位{phase['max_risk']*100:.0f}%")
            
            return plan
        else:
            logger.error("❌ 投资计划启动失败")
            return None
    except Exception as e:
        logger.error(f"❌ 投资计划启动失败: {e}")
        return None

def display_status(plan):
    """显示实时状态"""
    try:
        while True:
            # 清屏
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print("=" * 60)
            print("🚀 100U→1万U 自动交易系统")
            print("=" * 60)
            
            # 获取整体进展
            overall = plan.get_overall_progress()
            phase_progress = plan.check_phase_progress()
            
            # 显示核心信息
            print(f"💰 当前余额: {overall['current_balance']:.2f} USDT")
            print(f"📈 总体增长: +{overall['total_growth']:.2f} USDT ({overall['total_growth_ratio']*100:.1f}%)")
            print(f"🎯 完成进度: {overall['overall_completion']*100:.1f}%")
            print(f"⏰ 运行天数: {overall['total_days']} 天")
            print()
            
            # 当前阶段信息
            print(f"🔥 {phase_progress['phase_name']}")
            print(f"   目标: {phase_progress['start_balance']:.0f}U → {phase_progress['target_balance']:.0f}U")
            print(f"   进展: {phase_progress['completion_ratio']*100:.1f}%")
            print(f"   用时: {phase_progress['phase_days']}/{phase_progress['target_days']} 天")
            
            if phase_progress['ahead_of_schedule']:
                print("   ✅ 超前进度！")
            else:
                print("   ⏳ 按计划进行")
            
            print()
            print("💡 提示: 按 Ctrl+C 停止程序")
            print("🌐 Web界面: http://47.236.39.134:8888/quantitative.html")
            print("=" * 60)
            
            # 等待60秒更新
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("📴 用户手动停止程序")
    except Exception as e:
        logger.error(f"状态显示错误: {e}")

def main():
    """主函数"""
    print("🚀 启动100U→1万U自动交易系统...")
    print()
    
    # 设置日志
    setup_logging()
    
    # 创建日志目录
    os.makedirs('logs', exist_ok=True)
    
    logger.info("🔧 系统初始化中...")
    
    # 1. 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 2. 检查配置
    if not check_config():
        sys.exit(1)
    
    # 3. 启动Web服务
    if not start_web_service():
        logger.warning("⚠️ Web服务启动失败，但可以继续运行")
    
    # 等待Web服务启动
    time.sleep(3)
    
    # 4. 启动自动交易
    if not start_auto_trading():
        sys.exit(1)
    
    # 5. 启动投资计划
    plan = start_investment_plan()
    if not plan:
        sys.exit(1)
    
    logger.success("🎉 所有服务启动成功！")
    print()
    print("=" * 60)
    print("🚀 100U→1万U 自动交易系统已启动")
    print("🌐 Web管理界面: http://47.236.39.134:8888/quantitative.html")
    print("📊 实时监控界面: http://47.236.39.134:8888")
    print("💡 建议保持程序运行，系统将自动执行交易")
    print("=" * 60)
    print()
    
    # 显示实时状态
    display_status(plan)

if __name__ == "__main__":
    main() 