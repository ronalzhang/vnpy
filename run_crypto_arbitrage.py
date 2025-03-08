#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
VeighNa框架的加密货币套利应用启动脚本
"""

import multiprocessing
import sys
from datetime import datetime
from pathlib import Path

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp

# 添加VNPY套利应用
from vnpy_spreadtrading import SpreadTradingApp
# 加载我们自己的加密货币套利应用
from vnpy_cryptoarbitrage import CryptoArbitrageApp

# 导入需要的网关
try:
    from vnpy_binance import BinanceSpotGateway
except ImportError:
    BinanceSpotGateway = None

try:
    from vnpy_okex import OkexGateway
except ImportError:
    OkexGateway = None

try:
    from vnpy_bitget import BitgetGateway
except ImportError:
    BitgetGateway = None


def main():
    """启动VeighNa加密货币套利系统"""
    # 创建Qt应用对象
    qapp = create_qapp()

    # 创建事件引擎
    event_engine = EventEngine()
    
    # 创建主引擎
    main_engine = MainEngine(event_engine)
    
    # 添加交易所网关（如果安装了的话）
    if OkexGateway:
        main_engine.add_gateway(OkexGateway)
        print("OKX交易所网关已加载")
    else:
        print("OKX交易所网关未安装，请运行: pip install vnpy_okex")
    
    if BinanceSpotGateway:
        main_engine.add_gateway(BinanceSpotGateway)
        print("Binance交易所网关已加载")
    else:
        print("Binance交易所网关未安装，请运行: pip install vnpy_binance")
    
    if BitgetGateway:
        main_engine.add_gateway(BitgetGateway)
        print("Bitget交易所网关已加载")
    else:
        print("Bitget交易所网关未安装，请运行: pip install vnpy_bitget")
    
    # 添加应用模块
    main_engine.add_app(SpreadTradingApp)  # 价差交易
    main_engine.add_app(CryptoArbitrageApp)  # 加密货币套利
    
    # 创建主窗口
    main_window = MainWindow(main_engine, event_engine)
    
    # 设置窗口标题
    main_window.setWindowTitle("VeighNa加密货币套利平台")
    
    # 最大化显示窗口
    main_window.showMaximized()
    
    # 运行应用
    qapp.exec()


if __name__ == "__main__":
    # 解决多进程启动问题
    multiprocessing.freeze_support()
    main() 