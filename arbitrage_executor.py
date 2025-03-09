"""
综合套利执行器

本模块整合了跨交易所套利和三角套利功能，提供统一的套利执行接口，包括：
1. 套利机会发现与管理
2. 优先级排序
3. 资金分配
4. 风险控制
5. 执行监控

可同时管理不同类型的套利策略，并根据收益率、风险和时效性协调资源分配。
"""

import time
import logging
import threading
from typing import Dict, List, Tuple, Any
from datetime import datetime, timedelta
import json

# 导入套利模块
from transfer_assets import get_asset_transfer, AssetTransfer
from triangle_arbitrage import get_triangle_arbitrage, TriangleArbitrage

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("arbitrage_executor")

# 套利类型常量
ARBITRAGE_TYPE_CROSS_EXCHANGE = "cross_exchange"
ARBITRAGE_TYPE_TRIANGLE = "triangle"

# 套利状态常量
STATUS_PENDING = "pending"
STATUS_EXECUTING = "executing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# 资金分配比例
ALLOCATION_RATIO = {
    ARBITRAGE_TYPE_CROSS_EXCHANGE: 0.6,  # 跨所套利占总资金60%
    ARBITRAGE_TYPE_TRIANGLE: 0.4         # 三角套利占总资金40%
}

class ArbitrageExecutor:
    """套利执行器"""
    
    def __init__(self, exchange_configs=None, total_funds=10000):
        """初始化套利执行器"""
        self.exchange_configs = exchange_configs
        self.total_funds = total_funds
        self.allocated_funds = {
            ARBITRAGE_TYPE_CROSS_EXCHANGE: total_funds * ALLOCATION_RATIO[ARBITRAGE_TYPE_CROSS_EXCHANGE],
            ARBITRAGE_TYPE_TRIANGLE: total_funds * ALLOCATION_RATIO[ARBITRAGE_TYPE_TRIANGLE]
        }
        
        # 可用资金
        self.available_funds = self.allocated_funds.copy()
        
        # 交易所列表
        self.exchanges = ["binance", "okx", "bitget"]
        
        # 监控的交易对
        self.symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT", 
                        "ADA/USDT", "DOT/USDT", "MATIC/USDT", "AVAX/USDT", "SHIB/USDT"]
        
        # 初始化套利模块
        self.asset_transfer = get_asset_transfer(exchange_configs)
        self.triangle_arbitrage = get_triangle_arbitrage(exchange_configs)
        
        # 套利机会队列
        self.arbitrage_opportunities = {
            ARBITRAGE_TYPE_CROSS_EXCHANGE: [],
            ARBITRAGE_TYPE_TRIANGLE: []
        }
        
        # 活跃套利任务
        self.active_tasks = {}
        
        # 套利历史
        self.arbitrage_history = []
        
        # 同步锁
        self.lock = threading.Lock()
        
        # 运行状态
        self.running = False
        self.last_update = datetime.now()
    
    def start(self):
        """启动套利执行器"""
        if self.running:
            logger.info("套利执行器已经在运行")
            return False
        
        self.running = True
        
        # 启动监控线程
        threading.Thread(target=self._monitoring_thread, daemon=True).start()
        logger.info("套利执行器已启动")
        return True
    
    def stop(self):
        """停止套利执行器"""
        self.running = False
        logger.info("套利执行器已停止")
        return True
    
    def _monitoring_thread(self):
        """套利机会监控线程"""
        while self.running:
            try:
                # 更新套利机会
                self._update_cross_exchange_opportunities()
                self._update_triangle_opportunities()
                
                # 执行套利
                self._execute_pending_opportunities()
                
                # 检查转账状态
                self._check_transfer_status()
                
                # 更新时间
                self.last_update = datetime.now()
                
                # 等待下次更新
                time.sleep(5)  # 每5秒更新一次
                
            except Exception as e:
                logger.error(f"监控线程异常: {e}")
                time.sleep(10)  # 出现异常时等待较长时间
    
    def _update_cross_exchange_opportunities(self):
        """更新跨所套利机会"""
        opportunities = []
        
        # 遍历所有交易对
        for symbol in self.symbols:
            coin = symbol.split('/')[0]
            quote = symbol.split('/')[1]  # 通常是USDT
            
            # 遍历所有交易所对
            for buy_exchange in self.exchanges:
                for sell_exchange in self.exchanges:
                    if buy_exchange == sell_exchange:
                        continue
                    
                    try:
                        # 获取买入和卖出价格
                        buy_price = self._get_price(buy_exchange, symbol, "ask")
                        sell_price = self._get_price(sell_exchange, symbol, "bid")
                        
                        if not buy_price or not sell_price:
                            continue
                        
                        # 计算价差
                        price_diff = sell_price - buy_price
                        price_diff_pct = price_diff / buy_price
                        
                        # 计算转账成本
                        transfer_cost = self.asset_transfer.calculate_transfer_cost(
                            buy_exchange, sell_exchange, coin, 1.0
                        )
                        
                        # 计算净收益率（扣除转账成本）
                        net_profit_pct = price_diff_pct - (transfer_cost["fee_percent"] / 100)
                        
                        # 只保留有盈利的机会
                        if net_profit_pct > 0.002:  # 至少0.2%的净利润
                            opportunity = {
                                "type": ARBITRAGE_TYPE_CROSS_EXCHANGE,
                                "symbol": symbol,
                                "buy_exchange": buy_exchange,
                                "sell_exchange": sell_exchange,
                                "buy_price": buy_price,
                                "sell_price": sell_price,
                                "price_diff": price_diff,
                                "price_diff_pct": price_diff_pct,
                                "transfer_cost": transfer_cost,
                                "net_profit_pct": net_profit_pct,
                                "estimated_time_minutes": transfer_cost["estimated_time_minutes"],
                                "timestamp": datetime.now().timestamp()
                            }
                            opportunities.append(opportunity)
                    
                    except Exception as e:
                        logger.error(f"更新跨所套利机会出错: {e}")
        
        # 按净收益率排序
        opportunities.sort(key=lambda x: x["net_profit_pct"], reverse=True)
        
        # 更新套利机会队列
        with self.lock:
            self.arbitrage_opportunities[ARBITRAGE_TYPE_CROSS_EXCHANGE] = opportunities
        
        logger.info(f"更新了 {len(opportunities)} 个跨所套利机会")
    
    def _update_triangle_opportunities(self):
        """更新三角套利机会"""
        opportunities = []
        
        # 遍历所有交易所
        for exchange_id in self.exchanges:
            try:
                # 查找三角套利路径
                profitable_paths = self.triangle_arbitrage.find_profitable_paths(
                    exchange_id, "USDT", 0.1  # 至少0.1%的利润
                )
                
                # 转换为标准格式
                for path in profitable_paths:
                    opportunity = {
                        "type": ARBITRAGE_TYPE_TRIANGLE,
                        "exchange_id": exchange_id,
                        "path": path["path"],
                        "profit_percent": path["profit_percent"],
                        "steps": path["steps"],
                        "start_amount": path["start_amount"],
                        "end_amount": path["end_amount"],
                        "estimated_time_minutes": 1,  # 三角套利通常在1分钟内完成
                        "timestamp": datetime.now().timestamp()
                    }
                    opportunities.append(opportunity)
            
            except Exception as e:
                logger.error(f"更新三角套利机会出错: {e}")
        
        # 按收益率排序
        opportunities.sort(key=lambda x: x["profit_percent"], reverse=True)
        
        # 更新套利机会队列
        with self.lock:
            self.arbitrage_opportunities[ARBITRAGE_TYPE_TRIANGLE] = opportunities
        
        logger.info(f"更新了 {len(opportunities)} 个三角套利机会")
    
    def _execute_pending_opportunities(self):
        """执行等待中的套利机会"""
        # 首先执行三角套利（因为速度快）
        with self.lock:
            triangle_opportunities = self.arbitrage_opportunities[ARBITRAGE_TYPE_TRIANGLE][:5]  # 最多取前5个
        
        for opportunity in triangle_opportunities:
            if self._can_allocate_funds(opportunity):
                # 执行三角套利
                self._execute_triangle_arbitrage(opportunity)
        
        # 然后执行跨所套利
        with self.lock:
            cross_opportunities = self.arbitrage_opportunities[ARBITRAGE_TYPE_CROSS_EXCHANGE][:3]  # 最多取前3个
        
        for opportunity in cross_opportunities:
            if self._can_allocate_funds(opportunity):
                # 执行跨所套利
                self._execute_cross_exchange_arbitrage(opportunity)
    
    def _execute_triangle_arbitrage(self, opportunity):
        """执行三角套利"""
        # 分配资金
        amount = min(opportunity["start_amount"], self.available_funds[ARBITRAGE_TYPE_TRIANGLE])
        if amount < 10:  # 最小交易额
            logger.warning(f"可用资金不足: {amount} < 10")
            return False
        
        # 更新可用资金
        with self.lock:
            self.available_funds[ARBITRAGE_TYPE_TRIANGLE] -= amount
        
        task_id = f"triangle_{int(time.time())}"
        
        # 创建任务记录
        task = {
            "id": task_id,
            "type": ARBITRAGE_TYPE_TRIANGLE,
            "opportunity": opportunity,
            "amount": amount,
            "status": STATUS_EXECUTING,
            "start_time": datetime.now(),
            "steps": [],
            "result": None
        }
        
        # 添加到活跃任务
        self.active_tasks[task_id] = task
        
        try:
            # 调用三角套利执行
            path_result = {
                "path": opportunity["path"],
                "start_amount": amount
            }
            result = self.triangle_arbitrage.execute_arbitrage(opportunity["exchange_id"], path_result)
            
            # 更新任务状态
            task["result"] = result
            task["status"] = STATUS_COMPLETED if result["status"] == "success" else STATUS_FAILED
            
            # 如果成功，计算实际收益
            if result["status"] == "success":
                profit = result["actual_profit"]
                profit_percent = result["actual_profit_percent"]
                
                # 更新资金
                with self.lock:
                    self.available_funds[ARBITRAGE_TYPE_TRIANGLE] += (amount + profit)
                
                logger.info(f"三角套利成功: {task_id}, 收益: {profit:.2f} ({profit_percent:.2f}%)")
            else:
                # 套利失败，返还资金
                with self.lock:
                    self.available_funds[ARBITRAGE_TYPE_TRIANGLE] += amount
                
                logger.warning(f"三角套利失败: {task_id}, 原因: {result.get('message')}")
        
        except Exception as e:
            logger.error(f"执行三角套利出错: {e}")
            
            # 出错返还资金
            with self.lock:
                self.available_funds[ARBITRAGE_TYPE_TRIANGLE] += amount
            
            task["status"] = STATUS_FAILED
            task["result"] = {"status": "failed", "message": str(e)}
        
        # 将完成的任务添加到历史记录
        if task["status"] in [STATUS_COMPLETED, STATUS_FAILED]:
            task["end_time"] = datetime.now()
            self.arbitrage_history.append(task)
            del self.active_tasks[task_id]
        
        return task["status"] == STATUS_COMPLETED
    
    def _execute_cross_exchange_arbitrage(self, opportunity):
        """执行跨所套利"""
        # 计算交易量
        symbol = opportunity["symbol"]
        coin = symbol.split('/')[0]
        buy_exchange = opportunity["buy_exchange"]
        sell_exchange = opportunity["sell_exchange"]
        buy_price = opportunity["buy_price"]
        
        # 分配资金
        max_funds = self.available_funds[ARBITRAGE_TYPE_CROSS_EXCHANGE]
        amount_usdt = min(1000, max_funds)  # 最多使用1000USDT
        
        if amount_usdt < 100:  # 最小交易额
            logger.warning(f"可用资金不足: {amount_usdt} < 100")
            return False
        
        # 计算买入数量
        amount_coin = amount_usdt / buy_price
        
        # 更新可用资金
        with self.lock:
            self.available_funds[ARBITRAGE_TYPE_CROSS_EXCHANGE] -= amount_usdt
        
        task_id = f"cross_{int(time.time())}"
        
        # 创建任务记录
        task = {
            "id": task_id,
            "type": ARBITRAGE_TYPE_CROSS_EXCHANGE,
            "opportunity": opportunity,
            "amount_usdt": amount_usdt,
            "amount_coin": amount_coin,
            "status": STATUS_EXECUTING,
            "start_time": datetime.now(),
            "steps": [],
            "transfers": [],
            "result": None
        }
        
        # 添加到活跃任务
        self.active_tasks[task_id] = task
        
        try:
            # 步骤1: 在低价交易所买入币种
            buy_result = self._execute_buy(buy_exchange, symbol, amount_usdt)
            task["steps"].append({
                "action": "buy",
                "exchange": buy_exchange,
                "symbol": symbol,
                "amount_usdt": amount_usdt,
                "result": buy_result
            })
            
            if buy_result["status"] != "success":
                raise Exception(f"买入失败: {buy_result.get('message', '')}")
            
            actual_amount = buy_result.get("amount", amount_coin)
            
            # 步骤2: 将币转移到高价交易所
            transfer_result = self.asset_transfer.withdraw(
                buy_exchange, sell_exchange, coin, actual_amount
            )
            task["transfers"].append(transfer_result)
            
            if transfer_result["status"] == "failed":
                raise Exception(f"转账失败: {transfer_result.get('message', '')}")
            
            # 步骤3: 等待转账确认
            # 这一步由_check_transfer_status函数处理
            
            # 将任务标记为等待转账
            task["status"] = STATUS_PENDING
            task["transfer_id"] = transfer_result.get("id")
            
            logger.info(f"跨所套利任务创建成功: {task_id}, 等待转账确认")
            
        except Exception as e:
            logger.error(f"执行跨所套利出错: {e}")
            
            # 出错返还资金
            with self.lock:
                self.available_funds[ARBITRAGE_TYPE_CROSS_EXCHANGE] += amount_usdt
            
            task["status"] = STATUS_FAILED
            task["result"] = {"status": "failed", "message": str(e)}
            
            # 将失败的任务添加到历史记录
            task["end_time"] = datetime.now()
            self.arbitrage_history.append(task)
            del self.active_tasks[task_id]
        
        return True
    
    def _check_transfer_status(self):
        """检查转账状态并处理后续步骤"""
        for task_id, task in list(self.active_tasks.items()):
            if task["type"] == ARBITRAGE_TYPE_CROSS_EXCHANGE and task["status"] == STATUS_PENDING and "transfer_id" in task:
                transfer_id = task["transfer_id"]
                
                # 检查转账状态
                transfer_status = self.asset_transfer.check_transfer_status(transfer_id)
                
                # 更新任务中的转账状态
                for transfer in task["transfers"]:
                    if transfer.get("id") == transfer_id:
                        transfer["status"] = transfer_status["status"]
                
                # 如果转账完成，继续下一步
                if transfer_status["status"] == "confirmed":
                    self._complete_cross_exchange_arbitrage(task)
                elif transfer_status["status"] == "failed":
                    # 转账失败，终止套利
                    self._handle_failed_transfer(task)
    
    def _complete_cross_exchange_arbitrage(self, task):
        """完成跨所套利（转账确认后的卖出操作）"""
        try:
            opportunity = task["opportunity"]
            symbol = opportunity["symbol"]
            sell_exchange = opportunity["sell_exchange"]
            amount_coin = task["amount_coin"]
            
            # 从转账记录中获取实际转账金额
            for transfer in task["transfers"]:
                if transfer.get("status") == "confirmed":
                    amount_coin = transfer.get("amount", amount_coin)
            
            # 在高价交易所卖出
            sell_result = self._execute_sell(sell_exchange, symbol, amount_coin)
            task["steps"].append({
                "action": "sell",
                "exchange": sell_exchange,
                "symbol": symbol,
                "amount_coin": amount_coin,
                "result": sell_result
            })
            
            if sell_result["status"] != "success":
                raise Exception(f"卖出失败: {sell_result.get('message', '')}")
            
            # 计算实际收益
            buy_step = next((step for step in task["steps"] if step["action"] == "buy"), None)
            initial_amount = buy_step["amount_usdt"] if buy_step else task["amount_usdt"]
            final_amount = sell_result.get("amount_usdt", 0)
            
            profit = final_amount - initial_amount
            profit_percent = (profit / initial_amount) * 100 if initial_amount > 0 else 0
            
            # 更新任务状态
            task["status"] = STATUS_COMPLETED
            task["result"] = {
                "status": "success",
                "initial_amount": initial_amount,
                "final_amount": final_amount,
                "profit": profit,
                "profit_percent": profit_percent
            }
            
            # 更新可用资金
            with self.lock:
                self.available_funds[ARBITRAGE_TYPE_CROSS_EXCHANGE] += final_amount
            
            logger.info(f"跨所套利完成: {task['id']}, 收益: {profit:.2f} USDT ({profit_percent:.2f}%)")
            
        except Exception as e:
            logger.error(f"完成跨所套利出错: {e}")
            task["status"] = STATUS_FAILED
            task["result"] = {"status": "failed", "message": str(e)}
            
            # 返还估计资金（不准确但至少有所返还）
            with self.lock:
                self.available_funds[ARBITRAGE_TYPE_CROSS_EXCHANGE] += task["amount_usdt"]
        
        # 将完成的任务添加到历史记录
        task["end_time"] = datetime.now()
        self.arbitrage_history.append(task)
        del self.active_tasks[task["id"]]
    
    def _handle_failed_transfer(self, task):
        """处理转账失败的情况"""
        logger.warning(f"转账失败，终止套利任务: {task['id']}")
        
        # 更新任务状态
        task["status"] = STATUS_FAILED
        task["result"] = {"status": "failed", "message": "转账失败"}
        
        # 返还资金
        with self.lock:
            self.available_funds[ARBITRAGE_TYPE_CROSS_EXCHANGE] += task["amount_usdt"]
        
        # 将失败的任务添加到历史记录
        task["end_time"] = datetime.now()
        self.arbitrage_history.append(task)
        del self.active_tasks[task["id"]]
    
    def _execute_buy(self, exchange_id: str, symbol: str, amount_usdt: float) -> Dict:
        """在指定交易所买入指定交易对"""
        try:
            exchange = self.triangle_arbitrage.exchanges.get(exchange_id)
            if not exchange:
                return {"status": "failed", "message": f"交易所 {exchange_id} 未初始化"}
            
            # 获取当前价格
            ticker = self.triangle_arbitrage.get_ticker_price(exchange_id, symbol)
            if not ticker:
                return {"status": "failed", "message": f"获取 {symbol} 价格失败"}
            
            # 计算买入数量
            price = ticker["ask"]
            amount = amount_usdt / price
            
            # 执行买入
            order = exchange.create_market_buy_order(symbol, amount)
            
            return {
                "status": "success",
                "price": price,
                "amount": amount,
                "order": order
            }
            
        except Exception as e:
            logger.error(f"买入 {exchange_id} {symbol} 失败: {e}")
            return {"status": "failed", "message": str(e)}
    
    def _execute_sell(self, exchange_id: str, symbol: str, amount: float) -> Dict:
        """在指定交易所卖出指定交易对"""
        try:
            exchange = self.triangle_arbitrage.exchanges.get(exchange_id)
            if not exchange:
                return {"status": "failed", "message": f"交易所 {exchange_id} 未初始化"}
            
            # 获取当前价格
            ticker = self.triangle_arbitrage.get_ticker_price(exchange_id, symbol)
            if not ticker:
                return {"status": "failed", "message": f"获取 {symbol} 价格失败"}
            
            # 获取卖出价格
            price = ticker["bid"]
            
            # 执行卖出
            order = exchange.create_market_sell_order(symbol, amount)
            
            # 计算获得的USDT
            amount_usdt = amount * price
            
            return {
                "status": "success",
                "price": price,
                "amount": amount,
                "amount_usdt": amount_usdt,
                "order": order
            }
            
        except Exception as e:
            logger.error(f"卖出 {exchange_id} {symbol} 失败: {e}")
            return {"status": "failed", "message": str(e)}
    
    def _get_price(self, exchange_id: str, symbol: str, price_type: str) -> float:
        """获取指定交易所、指定交易对的价格"""
        try:
            ticker = self.triangle_arbitrage.get_ticker_price(exchange_id, symbol)
            if not ticker:
                return None
            
            if price_type == "bid":
                return ticker["bid"]
            elif price_type == "ask":
                return ticker["ask"]
            else:
                return None
        
        except Exception as e:
            logger.error(f"获取 {exchange_id} {symbol} 价格失败: {e}")
            return None
    
    def _can_allocate_funds(self, opportunity: Dict) -> bool:
        """检查是否可以为套利机会分配资金"""
        opportunity_type = opportunity["type"]
        
        with self.lock:
            if opportunity_type == ARBITRAGE_TYPE_TRIANGLE:
                return self.available_funds[opportunity_type] >= opportunity["start_amount"]
            else:  # ARBITRAGE_TYPE_CROSS_EXCHANGE
                # 至少需要100 USDT
                return self.available_funds[opportunity_type] >= 100
    
    def get_status(self) -> Dict:
        """获取套利执行器状态"""
        active_tasks = len(self.active_tasks)
        cross_opportunities = len(self.arbitrage_opportunities[ARBITRAGE_TYPE_CROSS_EXCHANGE])
        triangle_opportunities = len(self.arbitrage_opportunities[ARBITRAGE_TYPE_TRIANGLE])
        
        return {
            "running": self.running,
            "last_update": self.last_update.strftime("%Y-%m-%d %H:%M:%S"),
            "total_funds": self.total_funds,
            "available_funds": self.available_funds,
            "active_tasks": active_tasks,
            "cross_opportunities": cross_opportunities,
            "triangle_opportunities": triangle_opportunities,
            "history_count": len(self.arbitrage_history)
        }
    
    def get_opportunities(self, arbitrage_type=None, limit=10) -> List[Dict]:
        """获取套利机会列表"""
        if arbitrage_type:
            opportunities = self.arbitrage_opportunities.get(arbitrage_type, [])
            return opportunities[:limit]
        else:
            # 合并两种类型的机会并按收益率排序
            all_opportunities = []
            for opp in self.arbitrage_opportunities[ARBITRAGE_TYPE_CROSS_EXCHANGE]:
                all_opportunities.append({
                    **opp,
                    "profit_percent": opp["net_profit_pct"] * 100  # 转换为与三角套利相同的百分比格式
                })
            
            all_opportunities.extend(self.arbitrage_opportunities[ARBITRAGE_TYPE_TRIANGLE])
            
            # 按收益率排序
            all_opportunities.sort(key=lambda x: x["profit_percent"], reverse=True)
            
            return all_opportunities[:limit]
    
    def get_active_tasks(self) -> List[Dict]:
        """获取活跃任务列表"""
        return list(self.active_tasks.values())
    
    def get_history(self, limit=20) -> List[Dict]:
        """获取套利历史"""
        # 按时间倒序
        history = sorted(self.arbitrage_history, key=lambda x: x["end_time"], reverse=True)
        return history[:limit]
    
    def save_state(self, filename="arbitrage_state.json"):
        """保存执行器状态到文件"""
        state = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_funds": self.total_funds,
            "allocated_funds": self.allocated_funds,
            "available_funds": self.available_funds,
            "active_tasks": {k: self._serialize_task(v) for k, v in self.active_tasks.items()},
            "history": [self._serialize_task(task) for task in self.arbitrage_history]
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(state, f, indent=2)
            logger.info(f"状态已保存到 {filename}")
            return True
        except Exception as e:
            logger.error(f"保存状态失败: {e}")
            return False
    
    def _serialize_task(self, task):
        """序列化任务对象（处理不可JSON序列化的字段）"""
        result = {}
        for k, v in task.items():
            if k in ["start_time", "end_time"] and isinstance(v, datetime):
                result[k] = v.strftime("%Y-%m-%d %H:%M:%S")
            elif k == "steps":
                result[k] = [self._serialize_step(step) for step in v]
            elif k == "opportunity":
                result[k] = {kk: vv for kk, vv in v.items() if kk != "transfer_cost"}
            else:
                result[k] = v
        return result
    
    def _serialize_step(self, step):
        """序列化交易步骤（处理不可JSON序列化的字段）"""
        result = {}
        for k, v in step.items():
            if k == "result" and "order" in v:
                order_copy = {kk: vv for kk, vv in v["order"].items() if isinstance(vv, (str, int, float, bool, list, dict)) or vv is None}
                result[k] = {**v, "order": order_copy}
            else:
                result[k] = v
        return result
    
    def load_state(self, filename="arbitrage_state.json"):
        """从文件加载执行器状态"""
        try:
            with open(filename, 'r') as f:
                state = json.load(f)
            
            self.total_funds = state.get("total_funds", self.total_funds)
            self.allocated_funds = state.get("allocated_funds", self.allocated_funds)
            self.available_funds = state.get("available_funds", self.available_funds)
            
            # 历史记录不需要反序列化DateTime，因为不会再使用
            self.arbitrage_history = state.get("history", [])
            
            logger.info(f"状态已从 {filename} 加载")
            return True
        except Exception as e:
            logger.error(f"加载状态失败: {e}")
            return False

# 单例模式
_arbitrage_executor_instance = None

def get_arbitrage_executor(exchange_configs=None, total_funds=10000):
    """获取套利执行器单例"""
    global _arbitrage_executor_instance
    if _arbitrage_executor_instance is None:
        _arbitrage_executor_instance = ArbitrageExecutor(exchange_configs, total_funds)
    return _arbitrage_executor_instance

# 使用示例
if __name__ == "__main__":
    # 初始化套利执行器
    executor = get_arbitrage_executor()
    
    # 启动执行器
    executor.start()
    
    try:
        # 等待一段时间，让执行器收集套利机会
        time.sleep(20)
        
        # 获取当前套利机会
        cross_opportunities = executor.get_opportunities(ARBITRAGE_TYPE_CROSS_EXCHANGE, 5)
        triangle_opportunities = executor.get_opportunities(ARBITRAGE_TYPE_TRIANGLE, 5)
        
        print(f"跨所套利机会: {len(cross_opportunities)}")
        for i, opp in enumerate(cross_opportunities):
            print(f"{i+1}. {opp['symbol']}: {opp['buy_exchange']} -> {opp['sell_exchange']}, "
                 f"净收益: {opp['net_profit_pct']*100:.2f}%")
        
        print(f"三角套利机会: {len(triangle_opportunities)}")
        for i, opp in enumerate(triangle_opportunities):
            path_str = " -> ".join([step['symbol'] for step in opp['steps']])
            print(f"{i+1}. {opp['exchange_id']}: {path_str}, 收益: {opp['profit_percent']:.2f}%")
        
        # 获取执行器状态
        status = executor.get_status()
        print(f"状态: {status}")
        
        # 运行一段时间后保存状态
        time.sleep(60)
        executor.save_state()
        
    finally:
        # 停止执行器
        executor.stop() 