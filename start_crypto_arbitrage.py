import json
import time
from pathlib import Path

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp

# 导入交易所网关
from vnpy_okex import OkexGateway
from vnpy_binance import BinanceSpotGateway

# 尝试导入Bitget网关
try:
    from vnpy_bitget import BitgetGateway
    has_bitget = True
except ImportError:
    has_bitget = False

# 导入应用模块
from vnpy_spreadtrading import SpreadTradingApp

# 导入套利策略
from crypto_arbitrage_strategy import CryptoArbitrageStrategy

def main():
    """主函数"""
    print("加密货币跨交易所套利系统启动中...")
    
    # 创建事件引擎
    event_engine = EventEngine()
    
    # 创建主引擎
    main_engine = MainEngine(event_engine)
    
    # 添加交易所网关
    main_engine.add_gateway(OkexGateway)             # OKX
    main_engine.add_gateway(BinanceSpotGateway)      # 币安
    if has_bitget:
        main_engine.add_gateway(BitgetGateway)       # Bitget
    
    # 添加应用
    main_engine.add_app(SpreadTradingApp)
    
    # 创建窗口
    main_window = MainWindow(main_engine, event_engine)
    
    # 获取SpreadTrading引擎
    spread_engine = main_engine.get_engine("spread_trading")
    
    # 注册套利策略
    spread_engine.register_strategy(CryptoArbitrageStrategy)
    
    # 自动连接交易所
    connect_exchanges(main_engine)
    
    # 显示窗口
    main_window.showMaximized()
    
    # 在应用程序事件循环中运行
    qapp = create_qapp()
    qapp.exec()

def connect_exchanges(main_engine):
    """连接交易所"""
    config_path = Path("crypto_config.json")
    if not config_path.exists():
        print(f"错误: 找不到配置文件 {config_path}")
        return
    
    # 加载API配置
    with open(config_path, "r") as f:
        config = json.load(f)
    
    # 连接OKX
    if "OKEX" in config:
        settings = config["OKEX"]
        main_engine.connect(settings, "OKEX")
        print("正在连接OKX...")
    
    # 连接币安
    if "BINANCE" in config:
        settings = config["BINANCE"]
        main_engine.connect(settings, "BINANCE")
        print("正在连接Binance...")
    
    # 连接Bitget
    if has_bitget and "BITGET" in config:
        settings = config["BITGET"]
        main_engine.connect(settings, "BITGET")
        print("正在连接Bitget...")
    
    print("交易所连接中，请稍候...")

if __name__ == "__main__":
    main() 