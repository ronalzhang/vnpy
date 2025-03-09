from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp

# 导入应用模块
from vnpy_spreadtrading import SpreadTradingApp

# 导入自定义套利策略
try:
    from crypto_arbitrage_strategy import CryptoArbitrageStrategy
    has_strategy = True
except ImportError:
    has_strategy = False

def main():
    """主函数 - 简化版启动脚本"""
    print("加密货币跨交易所套利系统启动中...")
    
    # 创建QApplication
    qapp = create_qapp()
    
    # 创建事件引擎
    event_engine = EventEngine()
    
    # 创建主引擎
    main_engine = MainEngine(event_engine)
    
    # 尝试加载交易所网关
    try:
        from vnpy_okex import OkexGateway
        main_engine.add_gateway(OkexGateway)
        print("OKX交易所网关已加载")
    except ImportError:
        print("警告: OKX交易所网关未安装，请使用pip install vnpy_okex安装")
    
    try:
        from vnpy_binance import BinanceSpotGateway
        main_engine.add_gateway(BinanceSpotGateway)
        print("Binance交易所网关已加载")
    except ImportError:
        print("警告: Binance交易所网关未安装，请使用pip install vnpy_binance安装")
    
    # 添加应用
    main_engine.add_app(SpreadTradingApp)
    print("价差交易应用已加载")
    
    # 获取SpreadTrading引擎
    spread_engine = main_engine.get_engine("spread_trading")
    
    # 注册套利策略
    if has_strategy:
        spread_engine.register_strategy(CryptoArbitrageStrategy)
        print("加密货币套利策略已注册")
    else:
        print("警告: 无法加载套利策略，请检查crypto_arbitrage_strategy.py文件")
    
    # 创建窗口
    main_window = MainWindow(main_engine, event_engine)
    
    # 显示窗口
    main_window.showMaximized()
    
    # 在应用程序事件循环中运行
    qapp.exec()

if __name__ == "__main__":
    main() 