#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import sys
from pathlib import Path

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp

from vnpy_cryptoarbitrage import CryptoArbitrageApp


def main():
    """启动VeighNa加密货币套利应用"""
    # 创建Qt应用对象
    qapp = create_qapp()

    # 创建事件引擎
    event_engine = EventEngine()
    
    # 创建主引擎
    main_engine = MainEngine(event_engine)
    
    # 添加应用模块
    main_engine.add_app(CryptoArbitrageApp)  # 加密货币套利
    
    # 创建主窗口
    main_window = MainWindow(main_engine, event_engine)
    
    # 设置窗口标题
    main_window.setWindowTitle("VeighNa加密货币套利")
    
    # 显示窗口
    main_window.showMaximized()
    
    # 运行应用
    qapp.exec()


if __name__ == "__main__":
    # 解决多进程启动问题
    multiprocessing.freeze_support()
    main()
