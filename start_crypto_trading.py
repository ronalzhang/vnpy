#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
加密货币套利交易系统启动脚本
"""

import sys
import json
import argparse
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from PySide6.QtWidgets import QApplication, QMessageBox

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import create_qapp, QtCore

# 添加项目路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

# 导入自定义模块
from vnpy_cryptoarbitrage.ui import CryptoArbitrageWidget
from vnpy_cryptoarbitrage.engine import CryptoArbitrageEngine
from vnpy_cryptoarbitrage.utility import load_json, save_json

# 配置文件路径
CONFIG_FILE = "crypto_config.json"
CONFIG_PATH = Path(current_dir).joinpath(CONFIG_FILE)


def create_qapp():
    """创建QT应用程序实例"""
    # 创建Qt应用
    qapp = QApplication([])
    qapp.setStyleSheet("""
        QTableWidget {
            alternate-background-color: #f2f2f2;
            border: 1px solid #d3d3d3;
        }
        QHeaderView::section {
            background-color: #e6e6e6;
            padding: 4px;
            border: 1px solid #d3d3d3;
            font-weight: bold;
        }
    """)
    return qapp


def prepare_config(api_keys_required: bool = True) -> Dict[str, Any]:
    """准备配置文件"""
    # 创建默认配置
    if not CONFIG_PATH.exists():
        default_config = {
            "api_keys": {
                "okex": {
                    "key": "",
                    "secret": "",
                    "passphrase": ""
                },
                "binance": {
                    "key": "",
                    "secret": ""
                },
                "bitget": {
                    "key": "",
                    "secret": "",
                    "passphrase": ""
                }
            },
            "proxy": {
                "enabled": False,
                "host": "127.0.0.1",
                "port": 7890
            },
            "update_interval": 10,
            "trade_amount": {
                "BTC/USDT": 0.001,
                "ETH/USDT": 0.01,
                "SOL/USDT": 0.1,
                "XRP/USDT": 100,
                "BNB/USDT": 0.1,
                "ADA/USDT": 100,
                "DOGE/USDT": 1000,
                "DOT/USDT": 10
            },
            "symbols": [
                "BTC/USDT",
                "ETH/USDT",
                "SOL/USDT"
            ],
            "arbitrage_threshold": 0.5,
            "close_threshold": 0.2
        }
        save_json(CONFIG_PATH, default_config)
        print(f"已创建默认配置文件: {CONFIG_PATH}")
    
    # 加载配置
    config = load_json(CONFIG_PATH)
    print(f"已加载配置文件: {CONFIG_PATH}")
    
    # 检查API配置
    if api_keys_required:
        api_configured = False
        for exchange, api_info in config.get("api_keys", {}).items():
            if api_info.get("key") and api_info.get("secret"):
                api_configured = True
                break
        
        if not api_configured:
            print("警告: 未配置任何交易所API密钥，将无法获取实时数据")
    
    return config


def main(use_real_api: bool = False, verbose: bool = False, enable_trading: bool = False, auto_start: bool = False, simulate: bool = False):
    """主函数"""
    print("\n========================================")
    print("     加密货币跨交易所套利系统启动     ")
    print("========================================\n")
    
    # 打印启动参数
    mode_str = "模拟模式" if simulate else "真实API模式" if use_real_api else "仅监控模式"
    trade_str = "已启用交易" if enable_trading else "仅监控"
    verbose_str = "详细日志" if verbose else "简洁日志"
    auto_str = "自动开始监控" if auto_start else "手动开始监控"
    
    print(f"运行模式: {mode_str}")
    print(f"交易状态: {trade_str}")
    print(f"日志模式: {verbose_str}")
    print(f"监控模式: {auto_str}\n")
    
    try:
        # 创建Qt应用
        qapp = create_qapp()
        
        # 准备配置
        if use_real_api and not simulate:
            print("加载API配置...")
            config = prepare_config(api_keys_required=True)
        else:
            print("加载基本配置（无需API密钥）...")
            config = prepare_config(api_keys_required=False)
        
        # 创建事件引擎
        event_engine = EventEngine()
        
        # 创建套利引擎
        engine = CryptoArbitrageEngine(event_engine)
        init_result = engine.init_engine(
            settings=config, 
            verbose=verbose, 
            enable_trading=enable_trading,
            simulate=simulate
        )
        
        if not init_result and use_real_api and not simulate:
            msg = "初始化交易所API连接失败，请检查配置和网络。\n\n是否切换到模拟模式继续？"
            reply = QMessageBox.question(
                None, 
                "连接失败", 
                msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                print("切换到模拟模式...")
                engine = CryptoArbitrageEngine(event_engine)
                engine.init_engine(
                    settings=config, 
                    verbose=verbose, 
                    enable_trading=False,  # 模拟模式禁用交易
                    simulate=True
                )
            else:
                print("用户取消启动")
                sys.exit(1)
        
        # 创建主窗口
        # 注意：由于我们没有使用MainEngine，我们需要调整CryptoArbitrageWidget的使用方式
        main_engine = MainEngine(event_engine)
        main_window = CryptoArbitrageWidget(main_engine, event_engine)
        
        # 手动设置引擎实例
        main_window.crypto_engine = engine
        main_window.show()
        
        # 自动开始监控
        if auto_start:
            main_window.start_monitor()
        
        # 运行应用
        sys.exit(qapp.exec())
        
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="加密货币交易套利系统")
    parser.add_argument("--real", action="store_true", help="使用真实API连接")
    parser.add_argument("--auto-start", action="store_true", help="自动开始监控")
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")
    parser.add_argument("--trade", action="store_true", help="启用交易功能")
    parser.add_argument("--simulate", action="store_true", help="使用模拟数据（无需API连接）")
    
    args = parser.parse_args()
    
    # 确定是使用真实API还是模拟模式
    use_real_api = args.real and not args.simulate
    use_simulate = args.simulate or not args.real  # 默认使用模拟模式
    
    # 如果没有提供参数，显示使用说明
    if len(sys.argv) == 1:
        print("\n加密货币套利交易系统使用说明:")
        print("------------------------------")
        print("默认模式 (不带参数): 模拟数据模式\n")
        print("常用启动命令示例:")
        print("1. 模拟数据模式: python start_crypto_trading.py --simulate --auto-start")
        print("2. 真实API连接: python start_crypto_trading.py --real --auto-start")
        print("3. 启用交易模式: python start_crypto_trading.py --real --auto-start --trade")
        print("4. 详细日志模式: python start_crypto_trading.py --real --auto-start --verbose")
        print("\n全部命令行参数:")
        parser.print_help()
        print("\n")
    
    main(
        use_real_api=use_real_api,
        verbose=args.verbose,
        enable_trading=args.trade,
        auto_start=args.auto_start,
        simulate=use_simulate
    ) 