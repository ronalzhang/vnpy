"""
三角套利模块

本模块实现了交易所内部的三角套利功能，包括：
1. 套利环路发现
2. 套利收益计算
3. 套利交易执行
4. 套利风险管理

三角套利是在同一交易所内部，通过三个交易对形成一个交易环路，例如:
BTC/USDT -> ETH/BTC -> ETH/USDT -> BTC/USDT

当环路完成后，如果最终获得的BTC数量大于起始数量，则存在套利机会。
"""

import time
import logging
import itertools
from typing import Dict, List, Tuple, Set, Any
import ccxt
import math

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("triangle_arbitrage")

# 交易所配置（示例）
EXCHANGE_CONFIGS = {
    "binance": {
        "api_key": "",
        "api_secret": "",
        "trade_fee": 0.1  # 交易手续费百分比
    },
    "okx": {
        "api_key": "",
        "api_secret": "",
        "passphrase": "",
        "trade_fee": 0.1
    },
    "bitget": {
        "api_key": "",
        "api_secret": "",
        "trade_fee": 0.1
    }
}

class TriangleArbitrage:
    """三角套利管理器"""
    
    def __init__(self, exchange_configs=None):
        """初始化三角套利管理器"""
        self.exchange_configs = exchange_configs or EXCHANGE_CONFIGS
        self.exchanges = {}
        self.markets = {}
        self.arbitrage_paths = {}
        self.active_trades = {}
        
        # 初始化交易所连接
        self._init_exchanges()
    
    def _init_exchanges(self):
        """初始化交易所连接"""
        for exchange_id, config in self.exchange_configs.items():
            try:
                exchange_class = getattr(ccxt, exchange_id)
                self.exchanges[exchange_id] = exchange_class({
                    'apiKey': config.get('api_key', ''),
                    'secret': config.get('api_secret', ''),
                    'password': config.get('passphrase', ''),
                    'enableRateLimit': True,
                })
                logger.info(f"初始化交易所 {exchange_id} 成功")
            except Exception as e:
                logger.error(f"初始化交易所 {exchange_id} 失败: {e}")
    
    def load_markets(self, exchange_id: str):
        """加载交易所市场数据"""
        try:
            exchange = self.exchanges.get(exchange_id)
            if not exchange:
                logger.error(f"交易所 {exchange_id} 未初始化")
                return False
            
            # 加载市场
            markets = exchange.load_markets()
            self.markets[exchange_id] = markets
            
            logger.info(f"加载交易所 {exchange_id} 市场数据成功，共 {len(markets)} 个交易对")
            return True
        except Exception as e:
            logger.error(f"加载交易所 {exchange_id} 市场数据失败: {e}")
            return False
    
    def find_arbitrage_paths(self, exchange_id: str, base_currency: str = "USDT"):
        """发现可能的三角套利路径"""
        if exchange_id not in self.exchanges or exchange_id not in self.markets:
            if not self.load_markets(exchange_id):
                logger.error(f"无法加载交易所 {exchange_id} 市场数据")
                return []
        
        markets = self.markets[exchange_id]
        
        # 构建交易对图
        graph = {}
        for symbol, market in markets.items():
            base = market['base']
            quote = market['quote']
            
            if base not in graph:
                graph[base] = []
            graph[base].append({"currency": quote, "symbol": symbol, "direction": "sell"})
            
            if quote not in graph:
                graph[quote] = []
            graph[quote].append({"currency": base, "symbol": symbol, "direction": "buy"})
        
        # 查找三角套利路径
        paths = []
        
        # 从基础货币出发
        if base_currency in graph:
            # 找出所有可能的两步路径
            for first_step in graph[base_currency]:
                first_currency = first_step["currency"]
                
                if first_currency in graph:
                    for second_step in graph[first_currency]:
                        second_currency = second_step["currency"]
                        
                        # 检查是否能回到基础货币
                        if second_currency in graph:
                            for third_step in graph[second_currency]:
                                if third_step["currency"] == base_currency:
                                    # 找到一个三角套利路径
                                    path = [
                                        first_step,
                                        second_step,
                                        third_step
                                    ]
                                    paths.append(path)
        
        # 保存找到的路径
        self.arbitrage_paths[exchange_id] = paths
        
        logger.info(f"在交易所 {exchange_id} 找到 {len(paths)} 个可能的三角套利路径")
        return paths
    
    def get_ticker_price(self, exchange_id: str, symbol: str) -> Dict:
        """获取交易对的买卖价格"""
        try:
            exchange = self.exchanges.get(exchange_id)
            if not exchange:
                logger.error(f"交易所 {exchange_id} 未初始化")
                return {}
            
            ticker = exchange.fetch_ticker(symbol)
            return {
                "bid": ticker['bid'],  # 买一价
                "ask": ticker['ask'],  # 卖一价
                "last": ticker['last'],  # 最新成交价
                "volume": ticker['baseVolume']  # 24小时成交量
            }
        except Exception as e:
            logger.error(f"获取交易所 {exchange_id} 的 {symbol} 价格失败: {e}")
            return {}
    
    def calculate_path_profit(self, exchange_id: str, path: List[Dict], start_amount: float = 100.0) -> Dict:
        """计算套利路径的预期收益"""
        result = {
            "exchange": exchange_id,
            "path": path,
            "start_amount": start_amount,
            "end_amount": 0,
            "profit_percent": 0,
            "steps": [],
            "status": "failed",
            "message": ""
        }
        
        try:
            exchange = self.exchanges.get(exchange_id)
            if not exchange:
                result["message"] = f"交易所 {exchange_id} 未初始化"
                return result
            
            # 获取交易手续费
            fee_percent = self.exchange_configs.get(exchange_id, {}).get("trade_fee", 0.1) / 100
            
            # 模拟执行路径
            current_amount = start_amount
            steps_info = []
            
            for step in path:
                symbol = step["symbol"]
                direction = step["direction"]
                
                # 获取价格
                ticker = self.get_ticker_price(exchange_id, symbol)
                if not ticker:
                    result["message"] = f"无法获取 {symbol} 价格"
                    return result
                
                # 根据方向计算交易金额
                if direction == "buy":
                    # 买入: 用当前货币购买目标货币
                    price = ticker["ask"]  # 使用卖一价（对我们来说是买入价）
                    # 扣除手续费
                    amount_after_fee = current_amount * (1 - fee_percent)
                    # 买入后获得的数量
                    next_amount = amount_after_fee / price
                else:  # direction == "sell"
                    # 卖出: 卖出当前货币获得目标货币
                    price = ticker["bid"]  # 使用买一价（对我们来说是卖出价）
                    # 卖出获得的金额
                    next_amount = current_amount * price
                    # 扣除手续费
                    next_amount = next_amount * (1 - fee_percent)
                
                # 记录步骤信息
                step_info = {
                    "symbol": symbol,
                    "direction": direction,
                    "price": price,
                    "before_amount": current_amount,
                    "after_amount": next_amount
                }
                steps_info.append(step_info)
                
                # 更新当前金额
                current_amount = next_amount
            
            # 计算收益率
            profit = current_amount - start_amount
            profit_percent = (profit / start_amount) * 100
            
            # 更新结果
            result["end_amount"] = current_amount
            result["profit"] = profit
            result["profit_percent"] = profit_percent
            result["steps"] = steps_info
            result["status"] = "success" if profit > 0 else "no_profit"
            
            return result
        
        except Exception as e:
            logger.error(f"计算套利路径收益失败: {e}")
            result["message"] = str(e)
            return result
    
    def find_profitable_paths(self, exchange_id: str, base_currency: str = "USDT", min_profit_percent: float = 0.1) -> List[Dict]:
        """寻找所有有利可图的套利路径"""
        # 首先确保已经找到所有可能的路径
        if exchange_id not in self.arbitrage_paths:
            self.find_arbitrage_paths(exchange_id, base_currency)
        
        paths = self.arbitrage_paths.get(exchange_id, [])
        profitable_paths = []
        
        for path in paths:
            # 计算收益
            result = self.calculate_path_profit(exchange_id, path)
            if result["status"] == "success" and result["profit_percent"] >= min_profit_percent:
                profitable_paths.append(result)
        
        # 按收益率排序
        profitable_paths.sort(key=lambda x: x["profit_percent"], reverse=True)
        
        logger.info(f"在交易所 {exchange_id} 找到 {len(profitable_paths)} 个有利可图的三角套利路径")
        return profitable_paths
    
    def execute_arbitrage(self, exchange_id: str, path_result: Dict) -> Dict:
        """执行三角套利交易"""
        try:
            exchange = self.exchanges.get(exchange_id)
            if not exchange:
                return {"status": "failed", "message": f"交易所 {exchange_id} 未初始化"}
            
            # 验证收益是否仍然存在
            updated_result = self.calculate_path_profit(exchange_id, path_result["path"], path_result["start_amount"])
            if updated_result["profit_percent"] <= 0:
                return {"status": "failed", "message": "收益消失，不执行交易"}
            
            # 为了安全，检查余额是否足够
            start_currency = path_result["path"][0]["currency"]
            required_amount = path_result["start_amount"]
            
            balance = exchange.fetch_balance()
            available = balance.get('free', {}).get(start_currency, 0)
            
            if available < required_amount:
                return {"status": "failed", "message": f"余额不足: {available} < {required_amount}"}
            
            # 执行交易路径中的每一步
            trade_id = f"{exchange_id}_{int(time.time())}"
            trades = []
            current_amount = required_amount
            
            for step_info in updated_result["steps"]:
                symbol = step_info["symbol"]
                direction = step_info["direction"]
                
                # 创建订单
                order = None
                if direction == "buy":
                    order = exchange.create_market_buy_order(symbol, current_amount)
                else:  # direction == "sell"
                    order = exchange.create_market_sell_order(symbol, current_amount)
                
                trades.append({
                    "symbol": symbol,
                    "direction": direction,
                    "amount": current_amount,
                    "order": order
                })
                
                # 更新下一步的金额
                # 注意：实际交易中应该从订单结果获取实际成交量
                if order and 'amount' in order:
                    current_amount = order['amount']
            
            # 记录交易结果
            trade_result = {
                "id": trade_id,
                "exchange": exchange_id,
                "path": path_result["path"],
                "start_amount": required_amount,
                "expected_end_amount": updated_result["end_amount"],
                "expected_profit_percent": updated_result["profit_percent"],
                "actual_end_amount": current_amount if trades else 0,
                "actual_profit": (current_amount - required_amount) if trades else 0,
                "actual_profit_percent": ((current_amount - required_amount) / required_amount * 100) if trades and required_amount > 0 else 0,
                "trades": trades,
                "status": "success" if trades else "failed",
                "timestamp": time.time()
            }
            
            # 保存执行结果
            self.active_trades[trade_id] = trade_result
            
            logger.info(f"三角套利执行成功: {trade_id}, 预期收益: {updated_result['profit_percent']:.2f}%, 实际收益: {trade_result['actual_profit_percent']:.2f}%")
            return trade_result
        
        except Exception as e:
            logger.error(f"执行三角套利失败: {e}")
            return {"status": "failed", "message": str(e)}
    
    def get_trade_history(self) -> List[Dict]:
        """获取历史交易记录"""
        return list(self.active_trades.values())

# 单例模式
_triangle_arbitrage_instance = None

def get_triangle_arbitrage(exchange_configs=None):
    """获取三角套利管理器单例"""
    global _triangle_arbitrage_instance
    if _triangle_arbitrage_instance is None:
        _triangle_arbitrage_instance = TriangleArbitrage(exchange_configs)
    return _triangle_arbitrage_instance

# 使用示例
if __name__ == "__main__":
    # 初始化三角套利管理器
    arbitrage_manager = get_triangle_arbitrage()
    
    # 加载市场数据
    exchange_id = "binance"
    arbitrage_manager.load_markets(exchange_id)
    
    # 寻找套利路径
    paths = arbitrage_manager.find_arbitrage_paths(exchange_id, "USDT")
    print(f"找到 {len(paths)} 个可能的套利路径")
    
    # 计算收益
    profitable_paths = arbitrage_manager.find_profitable_paths(exchange_id, "USDT", 0.1)
    print(f"找到 {len(profitable_paths)} 个有利可图的套利路径")
    
    # 打印最高收益路径
    if profitable_paths:
        best_path = profitable_paths[0]
        print(f"最佳路径收益率: {best_path['profit_percent']:.2f}%")
        for i, step in enumerate(best_path["steps"]):
            print(f"步骤 {i+1}: {step['direction']} {step['symbol']} @ {step['price']}, 金额: {step['before_amount']:.6f} -> {step['after_amount']:.6f}") 