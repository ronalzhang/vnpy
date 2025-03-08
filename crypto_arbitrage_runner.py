import json
import os
import time
from pathlib import Path

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
from vnpy.trader.object import ContractData, SubscribeRequest

# 导入交易所网关
from vnpy_okex import OkexGateway
from vnpy_binance import BinanceSpotGateway

# 尝试导入Bitget网关
try:
    import vnpy_bitget
    from vnpy_bitget import BitgetGateway
    has_bitget = True
except ImportError:
    has_bitget = False

# 导入应用模块
from vnpy_spreadtrading import SpreadTradingApp
from vnpy_spreadtrading.base import SpreadData, LegData

# 导入自定义套利策略
from crypto_arbitrage_strategy import CryptoArbitrageStrategy

# 目标交易对配置
TARGET_SYMBOLS = [
    "BTC/USDT",    # 比特币
    "ETH/USDT",    # 以太坊
    "SOL/USDT",    # 索拉纳
    "BNB/USDT"     # 币安币
]

# 交易所名称映射
EXCHANGE_NAME_MAP = {
    "OKEX": "OKX",
    "BINANCE": "Binance",
    "BITGET": "Bitget"
}

class CryptoArbitrageRunner:
    """加密货币套利运行器"""
    
    def __init__(self):
        """构造函数"""
        self.main_engine = None
        self.event_engine = None
        self.spread_engine = None
        self.gateway_names = []
        self.vt_symbols = {}  # 交易所: [交易对列表]
    
    def run(self):
        """运行"""
        # 创建事件引擎和主引擎
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)
        
        # 添加交易所网关
        self.main_engine.add_gateway(OkexGateway)
        self.main_engine.add_gateway(BinanceSpotGateway)
        if has_bitget:
            self.main_engine.add_gateway(BitgetGateway)
        
        # 添加套利交易应用
        self.main_engine.add_app(SpreadTradingApp)
        self.spread_engine = self.main_engine.get_engine("spread_trading")
        
        # 注册套利策略
        self.spread_engine.register_strategy(CryptoArbitrageStrategy)
        
        # 连接交易所
        self.connect_exchanges()
        
        # 等待连接完成
        print("等待交易所连接完成...")
        time.sleep(5)
        
        # 查询合约
        self.query_contracts()
        
        # 订阅行情
        self.subscribe_ticks()
        
        # 创建价差套利合约
        self.create_spread_contracts()
        
        # 创建并启动策略
        self.start_strategy()
        
        # 创建GUI
        qapp = create_qapp()
        main_window = MainWindow(self.main_engine, self.event_engine)
        main_window.showMaximized()
        qapp.exec()
    
    def connect_exchanges(self):
        """连接交易所"""
        # 加载API配置
        config_path = Path("crypto_config.json")
        if not config_path.exists():
            print(f"错误: 找不到配置文件 {config_path}")
            return
        
        with open(config_path, "r") as f:
            config = json.load(f)
        
        # 连接OKEX
        if "OKEX" in config:
            settings = config["OKEX"]
            self.main_engine.connect(settings, "OKEX")
            self.gateway_names.append("OKEX")
            print("已连接到OKEX")
        
        # 连接币安
        if "BINANCE" in config:
            settings = config["BINANCE"]
            self.main_engine.connect(settings, "BINANCE")
            self.gateway_names.append("BINANCE")
            print("已连接到Binance")
        
        # 连接Bitget (如果可用)
        if has_bitget and "BITGET" in config:
            settings = config["BITGET"]
            self.main_engine.connect(settings, "BITGET")
            self.gateway_names.append("BITGET")
            print("已连接到Bitget")
    
    def query_contracts(self):
        """查询合约"""
        for gateway_name in self.gateway_names:
            self.vt_symbols[gateway_name] = []
            
            all_contracts = self.main_engine.get_all_contracts()
            for contract in all_contracts:
                if contract.gateway_name == gateway_name and contract.symbol in [s.split('/')[0] for s in TARGET_SYMBOLS]:
                    vt_symbol = f"{contract.vt_symbol}"
                    self.vt_symbols[gateway_name].append(vt_symbol)
                    print(f"找到合约: {vt_symbol}")
    
    def subscribe_ticks(self):
        """订阅行情"""
        for gateway_name, symbols in self.vt_symbols.items():
            for vt_symbol in symbols:
                req = SubscribeRequest(
                    symbol=vt_symbol.split(".")[0],
                    exchange=vt_symbol.split(".")[1]
                )
                self.main_engine.subscribe(req, gateway_name)
                print(f"订阅行情: {vt_symbol}")
    
    def create_spread_contracts(self):
        """创建价差套利合约"""
        # 按交易对创建跨交易所价差合约
        spread_count = 0
        
        for target in TARGET_SYMBOLS:
            symbol = target.split('/')[0]
            
            # 获取此交易对在各交易所的合约
            exchange_contracts = {}
            for gateway_name in self.gateway_names:
                for vt_symbol in self.vt_symbols.get(gateway_name, []):
                    if vt_symbol.split(".")[0] == symbol:
                        exchange_contracts[gateway_name] = vt_symbol
            
            # 如果至少有2个交易所有此合约，创建价差
            if len(exchange_contracts) >= 2:
                exchange_list = list(exchange_contracts.keys())
                
                # 创建所有可能的交易所组合价差
                for i in range(len(exchange_list)):
                    for j in range(i+1, len(exchange_list)):
                        ex1 = exchange_list[i]
                        ex2 = exchange_list[j]
                        
                        # 创建价差名称
                        spread_name = f"{symbol}_{EXCHANGE_NAME_MAP.get(ex1, ex1)}_{EXCHANGE_NAME_MAP.get(ex2, ex2)}"
                        
                        # 创建主动腿和被动腿
                        active_leg = LegData(
                            vt_symbol=exchange_contracts[ex1],
                            trading_direction=1,
                            price_multiplier=1.0
                        )
                        
                        passive_leg = LegData(
                            vt_symbol=exchange_contracts[ex2],
                            trading_direction=-1,
                            price_multiplier=1.0
                        )
                        
                        # 创建价差对象
                        spread = SpreadData(
                            name=spread_name,
                            legs=[active_leg, passive_leg],
                            price_formula="leg1.mid_price - leg2.mid_price"
                        )
                        
                        # 添加到引擎
                        self.spread_engine.add_spread(spread)
                        print(f"创建价差合约: {spread_name}")
                        spread_count += 1
        
        print(f"已创建{spread_count}个价差合约")
    
    def start_strategy(self):
        """启动套利策略"""
        # 获取所有价差合约
        spreads = self.spread_engine.get_all_spreads()
        if not spreads:
            print("错误: 没有可用的价差合约")
            return
        
        # 为每个交易对的第一个价差合约创建策略
        target_symbol_map = {}
        for spread in spreads:
            # 提取基础交易对
            symbol = spread.name.split("_")[0]
            
            # 如果这个交易对还没有创建策略，则创建
            if symbol not in target_symbol_map:
                strategy_name = f"{symbol}_Arbitrage"
                
                # 创建策略参数
                setting = {
                    "open_threshold": 0.005,  # 0.5%
                    "close_threshold": 0.001,  # 0.1%
                    "max_pos": 0.01,          # 最大持仓
                    "min_volume": 0.001,      # 最小交易量
                    "max_orders": 10          # 最大挂单数
                }
                
                # 创建策略
                self.spread_engine.add_strategy(
                    strategy_class_name="CryptoArbitrageStrategy",
                    strategy_name=strategy_name,
                    spread_name=spread.name,
                    setting=setting
                )
                
                # 初始化并启动策略
                self.spread_engine.init_strategy(strategy_name)
                self.spread_engine.start_strategy(strategy_name)
                
                print(f"已创建并启动套利策略: {strategy_name} (价差: {spread.name})")
                target_symbol_map[symbol] = True

# 主函数
def main():
    """主函数"""
    runner = CryptoArbitrageRunner()
    runner.run()

if __name__ == "__main__":
    main() 