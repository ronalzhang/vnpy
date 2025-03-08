#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
from pathlib import Path
from time import sleep

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
from vnpy.trader.setting import SETTINGS

# 尝试导入交易所网关，如果导入失败则提供安装提示
try:
    from vnpy_okex import OkexGateway
    has_okex = True
except ImportError:
    has_okex = False
    print("未安装OKX交易所接口，请运行 pip install vnpy_okex")

try:
    from vnpy_binance import BinanceSpotGateway
    has_binance = True
except ImportError:
    has_binance = False
    print("未安装Binance交易所接口，请运行 pip install vnpy_binance")

try:
    from vnpy_bitget import BitgetGateway
    has_bitget = True
except ImportError:
    has_bitget = False
    print("未安装Bitget交易所接口，请运行 pip install vnpy_bitget")

# 导入套利交易应用
from vnpy_spreadtrading import SpreadTradingApp

# 导入自定义套利策略
try:
    from crypto_arbitrage_strategy import CryptoArbitrageStrategy
    has_strategy = True
except ImportError:
    has_strategy = False
    print("未找到套利策略文件 crypto_arbitrage_strategy.py")

# 配置文件名称
CONFIG_FILE = "crypto_config.json"
CONFIG_PATH = Path("/Users/godfather/Downloads/program/VNPY").joinpath(CONFIG_FILE)


def connect_exchanges():
    """连接交易所"""
    # 打印当前工作目录，帮助调试配置文件路径问题
    current_dir = Path.cwd()
    print(f"当前工作目录: {current_dir}")
    
    print(f"使用配置文件: {CONFIG_PATH}")
    
    if not CONFIG_PATH.exists():
        print(f"错误：找不到配置文件 {CONFIG_PATH}")
        print("请确保配置文件存在，包含API密钥信息")
        return False
    
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # 连接各交易所
    if has_okex and "okex" in config:
        print("正在连接 OKX 交易所...")
        main_engine.connect(config["okex"], "OKEX")
        sleep(1)
    
    if has_binance and "binance" in config:
        print("正在连接 Binance 交易所...")
        main_engine.connect(config["binance"], "BINANCE")
        sleep(1)
    
    if has_bitget and "bitget" in config:
        print("正在连接 Bitget 交易所...")
        main_engine.connect(config["bitget"], "BITGET")
        sleep(1)
    
    return True


def main():
    """主函数"""
    # 创建Qt应用和事件引擎
    qapp = create_qapp()
    
    # 创建事件引擎
    event_engine = EventEngine()
    
    # 创建主引擎
    global main_engine
    main_engine = MainEngine(event_engine)
    
    # 添加交易所网关
    if has_okex:
        main_engine.add_gateway(OkexGateway)
    
    if has_binance:
        main_engine.add_gateway(BinanceSpotGateway)
    
    if has_bitget:
        main_engine.add_gateway(BitgetGateway)
    
    # 添加套利交易应用
    spread_engine = main_engine.add_app(SpreadTradingApp)
    
    # 加载套利策略
    # 注意：先启动系统，之后通过UI手动添加策略
    if has_strategy:
        print("已找到加密货币跨交易所套利策略，请通过UI手动添加")
    
    # 创建主窗口
    main_window = MainWindow(main_engine, event_engine)
    main_window.showMaximized()
    
    # 在启动界面后连接交易所
    connect_exchanges()
    
    # 运行Qt应用
    qapp.exec()


if __name__ == "__main__":
    print("==========================================================")
    print("         加密货币跨交易所套利系统 (Crypto Arbitrage)")
    print("==========================================================")
    print("系统启动中...")
    main() 