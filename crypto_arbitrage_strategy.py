from typing import Dict, List
from vnpy.trader.utility import round_to
from vnpy_spreadtrading import SpreadStrategyTemplate, SpreadAlgoTemplate
from vnpy_spreadtrading.base import SpreadData, LegData

class CryptoArbitrageStrategy(SpreadStrategyTemplate):
    """
    加密货币跨交易所套利策略
    
    该策略监控多个交易所间的价格差异，当差价超过设定阈值时，
    在低价交易所买入并在高价交易所卖出，实现套利。
    """
    
    author = "VeighNa Crypto Arbitrage"
    
    # 策略参数
    open_threshold = 0.005  # 开仓价差阈值（0.5%）
    close_threshold = 0.001  # 平仓价差阈值（0.1%）
    max_pos = 0.01           # 最大持仓（BTC数量）
    min_volume = 0.001       # 最小交易量（BTC数量）
    max_orders = 10          # 最大挂单数量
    
    # 策略变量
    spread_data = {}         # 价差数据字典
    active_spreads = []      # 活跃价差列表
    spread_pos = {}          # 价差持仓字典
    
    def __init__(
        self,
        strategy_engine,
        strategy_name: str,
        spread: SpreadData,
        setting: dict
    ):
        """构造函数"""
        super().__init__(strategy_engine, strategy_name, spread, setting)
    
    def on_init(self):
        """策略初始化"""
        self.write_log("策略初始化")
        
        # 获取所有已创建的价差
        all_spreads = self.spread_engine.get_all_spreads()
        self.active_spreads = [s for s in all_spreads]
        
        # 初始化价差数据字典
        for spread in self.active_spreads:
            self.spread_data[spread.name] = {
                "bid_price": 0,
                "ask_price": 0,
                "mid_price": 0,
                "exchange": self._get_exchange_from_spread(spread)
            }
            self.spread_pos[spread.name] = 0
        
        self.write_log(f"已加载价差合约: {[s.name for s in self.active_spreads]}")
        
        # 订阅价差行情
        self.subscribe_spread()
    
    def on_start(self):
        """策略启动"""
        self.write_log("策略启动")
    
    def on_stop(self):
        """策略停止"""
        self.write_log("策略停止")
    
    def on_spread_data(self):
        """价差数据更新回调"""
        spread = self.spread
        
        # 更新价差数据
        self.spread_data[spread.name] = {
            "bid_price": spread.bid_price,
            "ask_price": spread.ask_price,
            "mid_price": spread.mid_price,
            "exchange": self._get_exchange_from_spread(spread)
        }
        
        # 检查是否所有价差数据都已更新
        if all(v["bid_price"] > 0 for v in self.spread_data.values()):
            self.check_arbitrage_opportunity()
    
    def check_arbitrage_opportunity(self):
        """检查套利机会"""
        # 找出最高买价和最低卖价
        max_bid = max(self.spread_data.items(), key=lambda x: x[1]["bid_price"])
        min_ask = min(self.spread_data.items(), key=lambda x: x[1]["ask_price"])
        
        max_bid_name, max_bid_data = max_bid
        min_ask_name, min_ask_data = min_ask
        
        # 计算价差比例
        spread_ratio = (max_bid_data["bid_price"] - min_ask_data["ask_price"]) / min_ask_data["ask_price"]
        
        # 如果价差超过开仓阈值且未持仓
        if spread_ratio > self.open_threshold and sum(self.spread_pos.values()) == 0:
            self.write_log(f"发现套利机会: 买入{min_ask_name}(¥{min_ask_data['ask_price']:.2f})，"
                          f"卖出{max_bid_name}(¥{max_bid_data['bid_price']:.2f})，"
                          f"价差比例: {spread_ratio:.4%}")
            
            # 计算交易量
            volume = min(self.max_pos, max_bid_data["bid_price"] * self.min_volume)
            volume = round_to(volume, 0.001)  # 调整为合适的精度
            
            # 在最低卖价交易所买入
            min_ask_spread = next((s for s in self.active_spreads if s.name == min_ask_name), None)
            if min_ask_spread:
                self.buy(min_ask_spread, min_ask_data["ask_price"] * 1.001, volume)
                self.spread_pos[min_ask_name] = volume
                self.write_log(f"买入订单提交: {min_ask_name}, 价格: {min_ask_data['ask_price'] * 1.001:.2f}, 数量: {volume}")
            
            # 在最高买价交易所卖出
            max_bid_spread = next((s for s in self.active_spreads if s.name == max_bid_name), None)
            if max_bid_spread:
                self.sell(max_bid_spread, max_bid_data["bid_price"] * 0.999, volume)
                self.spread_pos[max_bid_name] = -volume
                self.write_log(f"卖出订单提交: {max_bid_name}, 价格: {max_bid_data['bid_price'] * 0.999:.2f}, 数量: {volume}")
        
        # 检查是否需要平仓
        elif sum(abs(pos) for pos in self.spread_pos.values()) > 0:
            # 如果价差低于平仓阈值则平仓
            if spread_ratio < self.close_threshold:
                for spread_name, pos in self.spread_pos.items():
                    if pos != 0:
                        spread = next((s for s in self.active_spreads if s.name == spread_name), None)
                        if spread:
                            if pos > 0:  # 持有多头，需要卖出平仓
                                self.sell(spread, self.spread_data[spread_name]["bid_price"] * 0.999, abs(pos))
                                self.write_log(f"平仓卖出: {spread_name}, 价格: {self.spread_data[spread_name]['bid_price'] * 0.999:.2f}, 数量: {abs(pos)}")
                            else:  # 持有空头，需要买入平仓
                                self.buy(spread, self.spread_data[spread_name]["ask_price"] * 1.001, abs(pos))
                                self.write_log(f"平仓买入: {spread_name}, 价格: {self.spread_data[spread_name]['ask_price'] * 1.001:.2f}, 数量: {abs(pos)}")
                        
                        self.spread_pos[spread_name] = 0
                
                self.write_log(f"套利平仓完成，价差比例: {spread_ratio:.4%}")
    
    def on_spread_pos(self):
        """价差持仓更新回调"""
        self.write_log(f"价差持仓更新: {self.spread.name}, 多头: {self.spread.long_pos}, 空头: {self.spread.short_pos}")
        
        # 更新持仓信息
        self.spread_pos[self.spread.name] = self.spread.net_pos
    
    def on_spread_traded(self, trade):
        """价差成交回调"""
        self.write_log(f"价差成交: {trade.spread_name}, 方向: {'多' if trade.direction > 0 else '空'}, "
                      f"价格: {trade.price:.2f}, 数量: {trade.volume}")
    
    def on_order(self, order):
        """委托更新回调"""
        self.write_log(f"委托状态更新: {order.vt_symbol}, 方向: {'买入' if order.direction == '多' else '卖出'}, "
                      f"价格: {order.price:.2f}, 数量: {order.volume}, 状态: {order.status}")
    
    def _get_exchange_from_spread(self, spread):
        """从价差对象中提取交易所名称"""
        if not spread.legs:
            return ""
        
        leg = spread.legs[0]
        if not leg.vt_symbol:
            return ""
        
        parts = leg.vt_symbol.split(".")
        if len(parts) < 2:
            return ""
        
        return parts[0] 