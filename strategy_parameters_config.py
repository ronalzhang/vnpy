#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
策略参数配置 - 2.0升级版
增强策略参数优化与进化配置
"""

from typing import Dict, List, Any, Tuple, Optional
import json
import os
import random
from datetime import datetime
import numpy as np


# 市场状态定义
MARKET_STATES = {
    "TRENDING_UP": "趋势上涨",
    "TRENDING_DOWN": "趋势下跌",
    "SIDEWAYS": "横盘震荡",
    "VOLATILE": "高波动",
    "LOW_VOLATILITY": "低波动",
    "BREAKOUT": "突破",
    "REVERSAL": "反转",
    "RANGING": "区间震荡",
}

# 策略类型定义
STRATEGY_TYPES = [
    "momentum",          # 动量策略
    "mean_reversion",    # 均值回归策略
    "breakout",          # 突破策略
    "grid_trading",      # 网格交易策略
    "trend_following",   # 趋势跟踪策略
    "high_frequency",    # 高频交易策略
    "scalping",          # 短线策略
    "arbitrage",         # 套利策略
    "pattern_recognition", # 形态识别策略
]

# 全局参数规则
PARAMETER_RULES = {
    # 动量策略参数
    "momentum_period": {
        "range": [5, 120],
        "optimal": 14,
        "step": 1,
        "profit_logic": "dynamic", # 参数调整逻辑：根据市场状态动态调整
        "description": "动量计算周期",
        "market_adaption": {
            "TRENDING_UP": [10, 30],
            "TRENDING_DOWN": [10, 30],
            "SIDEWAYS": [5, 15],
            "VOLATILE": [3, 20],
            "LOW_VOLATILITY": [20, 60]
        },
        "mutation_strength": 0.2, # 变异强度
        "type": "int"
    },
    "momentum_threshold": {
        "range": [0.01, 0.3],
        "optimal": 0.05,
        "step": 0.01,
        "profit_logic": "direct", # 参数调整逻辑：收益越高，参数越接近最优
        "description": "动量阈值",
        "market_adaption": {
            "TRENDING_UP": [0.03, 0.1],
            "TRENDING_DOWN": [0.03, 0.1],
            "SIDEWAYS": [0.01, 0.05],
            "VOLATILE": [0.05, 0.15],
            "LOW_VOLATILITY": [0.01, 0.03]
        },
        "mutation_strength": 0.1,
        "type": "float"
    },
    
    # 均值回归策略参数
    "mean_window": {
        "range": [10, 200],
        "optimal": 50,
        "step": 5,
        "profit_logic": "inverse", # 参数调整逻辑：收益越高，参数越远离当前值
        "description": "均值计算窗口",
        "market_adaption": {
            "TRENDING_UP": [50, 100],
            "TRENDING_DOWN": [50, 100],
            "SIDEWAYS": [20, 50],
            "VOLATILE": [30, 80],
            "LOW_VOLATILITY": [80, 150]
        },
        "mutation_strength": 0.2,
        "type": "int"
    },
    "std_dev_multiplier": {
        "range": [1.0, 3.0],
        "optimal": 2.0,
        "step": 0.1,
        "profit_logic": "direct",
        "description": "标准差倍数",
        "market_adaption": {
            "TRENDING_UP": [1.5, 2.5],
            "TRENDING_DOWN": [1.5, 2.5],
            "SIDEWAYS": [1.8, 2.2],
            "VOLATILE": [2.0, 3.0],
            "LOW_VOLATILITY": [1.0, 2.0]
        },
        "mutation_strength": 0.15,
        "type": "float"
    },
    
    # 突破策略参数
    "breakout_period": {
        "range": [5, 100],
        "optimal": 20,
        "step": 1,
        "profit_logic": "dynamic",
        "description": "突破计算周期",
        "market_adaption": {
            "TRENDING_UP": [15, 30],
            "TRENDING_DOWN": [15, 30],
            "SIDEWAYS": [5, 15],
            "VOLATILE": [10, 25],
            "BREAKOUT": [5, 20],
            "REVERSAL": [10, 30]
        },
        "mutation_strength": 0.25,
        "type": "int"
    },
    "breakout_threshold": {
        "range": [0.005, 0.05],
        "optimal": 0.01,
        "step": 0.001,
        "profit_logic": "direct",
        "description": "突破阈值",
        "market_adaption": {
            "TRENDING_UP": [0.01, 0.02],
            "TRENDING_DOWN": [0.01, 0.02],
            "SIDEWAYS": [0.005, 0.01],
            "VOLATILE": [0.02, 0.05],
            "BREAKOUT": [0.01, 0.03],
            "REVERSAL": [0.015, 0.035]
        },
        "mutation_strength": 0.2,
        "type": "float"
    },
    
    # 网格交易策略参数
    "grid_levels": {
        "range": [3, 50],
        "optimal": 10,
        "step": 1,
        "profit_logic": "moderate",
        "description": "网格级别数量",
        "market_adaption": {
            "TRENDING_UP": [5, 10],
            "TRENDING_DOWN": [5, 10],
            "SIDEWAYS": [8, 20],
            "VOLATILE": [10, 30],
            "LOW_VOLATILITY": [5, 15],
            "RANGING": [10, 40]
        },
        "mutation_strength": 0.3,
        "type": "int"
    },
    "grid_spacing": {
        "range": [0.002, 0.05],
        "optimal": 0.01,
        "step": 0.001,
        "profit_logic": "direct",
        "description": "网格间距",
        "market_adaption": {
            "TRENDING_UP": [0.01, 0.02],
            "TRENDING_DOWN": [0.01, 0.02],
            "SIDEWAYS": [0.005, 0.015],
            "VOLATILE": [0.02, 0.05],
            "LOW_VOLATILITY": [0.002, 0.01],
            "RANGING": [0.008, 0.025]
        },
        "mutation_strength": 0.2,
        "type": "float"
    },
    
    # 趋势跟踪策略参数
    "trend_period": {
        "range": [10, 200],
        "optimal": 50,
        "step": 5,
        "profit_logic": "dynamic",
        "description": "趋势计算周期",
        "market_adaption": {
            "TRENDING_UP": [30, 80],
            "TRENDING_DOWN": [30, 80],
            "SIDEWAYS": [20, 50],
            "VOLATILE": [40, 100],
            "LOW_VOLATILITY": [50, 150],
        },
        "mutation_strength": 0.25,
        "type": "int"
    },
    "trend_threshold": {
        "range": [0.01, 0.1],
        "optimal": 0.03,
        "step": 0.005,
        "profit_logic": "direct",
        "description": "趋势确认阈值",
        "market_adaption": {
            "TRENDING_UP": [0.02, 0.05],
            "TRENDING_DOWN": [0.02, 0.05],
            "SIDEWAYS": [0.01, 0.03],
            "VOLATILE": [0.04, 0.1],
            "LOW_VOLATILITY": [0.01, 0.03],
        },
        "mutation_strength": 0.15,
        "type": "float"
    },
    
    # 高频交易策略参数
    "hf_window": {
        "range": [2, 30],
        "optimal": 5,
        "step": 1,
        "profit_logic": "direct",
        "description": "高频交易窗口",
        "market_adaption": {
            "TRENDING_UP": [3, 8],
            "TRENDING_DOWN": [3, 8],
            "SIDEWAYS": [2, 5],
            "VOLATILE": [3, 10],
            "LOW_VOLATILITY": [5, 15]
        },
        "mutation_strength": 0.3,
        "type": "int"
    },
    "hf_threshold": {
        "range": [0.001, 0.01],
        "optimal": 0.002,
        "step": 0.0005,
        "profit_logic": "direct",
        "description": "高频交易阈值",
        "market_adaption": {
            "TRENDING_UP": [0.001, 0.003],
            "TRENDING_DOWN": [0.001, 0.003],
            "SIDEWAYS": [0.0015, 0.004],
            "VOLATILE": [0.003, 0.01],
            "LOW_VOLATILITY": [0.001, 0.002]
        },
        "mutation_strength": 0.25,
        "type": "float"
    },
    
    # 短线策略参数
    "scalping_period": {
        "range": [1, 15],
        "optimal": 3,
        "step": 1,
        "profit_logic": "direct", 
        "description": "短线交易周期",
        "market_adaption": {
            "TRENDING_UP": [2, 5],
            "TRENDING_DOWN": [2, 5],
            "SIDEWAYS": [1, 3],
            "VOLATILE": [2, 8],
            "LOW_VOLATILITY": [3, 10]
        },
        "mutation_strength": 0.3,
        "type": "int"
    },
    "profit_target": {
        "range": [0.001, 0.02],
        "optimal": 0.005,
        "step": 0.001,
        "profit_logic": "direct",
        "description": "利润目标",
        "market_adaption": {
            "TRENDING_UP": [0.003, 0.01],
            "TRENDING_DOWN": [0.003, 0.01],
            "SIDEWAYS": [0.001, 0.005],
            "VOLATILE": [0.005, 0.02],
            "LOW_VOLATILITY": [0.001, 0.003]
        },
        "mutation_strength": 0.2,
        "type": "float"
    },
    
    # 套利策略参数
    "price_diff_threshold": {
        "range": [0.001, 0.05],
        "optimal": 0.01,
        "step": 0.001,
        "profit_logic": "direct",
        "description": "价格差异阈值",
        "market_adaption": {
            "TRENDING_UP": [0.005, 0.02],
            "TRENDING_DOWN": [0.005, 0.02],
            "SIDEWAYS": [0.002, 0.01],
            "VOLATILE": [0.01, 0.05],
            "LOW_VOLATILITY": [0.001, 0.008]
        },
        "mutation_strength": 0.2,
        "type": "float"
    },
    
    # 风控参数
    "max_position_size": {
        "range": [0.01, 0.5],
        "optimal": 0.1,
        "step": 0.01,
        "profit_logic": "risk_adjusted", # 根据风险调整收益
        "description": "最大仓位比例",
        "market_adaption": {
            "TRENDING_UP": [0.05, 0.2],
            "TRENDING_DOWN": [0.05, 0.15],
            "SIDEWAYS": [0.03, 0.1],
            "VOLATILE": [0.01, 0.08],
            "LOW_VOLATILITY": [0.05, 0.3]
        },
        "mutation_strength": 0.1,
        "type": "float"
    },
    "stop_loss": {
        "range": [0.01, 0.1],
        "optimal": 0.03,
        "step": 0.005,
        "profit_logic": "risk_adjusted",
        "description": "止损比例",
        "market_adaption": {
            "TRENDING_UP": [0.02, 0.05],
            "TRENDING_DOWN": [0.02, 0.05],
            "SIDEWAYS": [0.01, 0.03],
            "VOLATILE": [0.03, 0.1],
            "LOW_VOLATILITY": [0.01, 0.03]
        },
        "mutation_strength": 0.15,
        "type": "float"
    },
    "take_profit": {
        "range": [0.01, 0.2],
        "optimal": 0.05,
        "step": 0.01,
        "profit_logic": "risk_adjusted",
        "description": "止盈比例",
        "market_adaption": {
            "TRENDING_UP": [0.03, 0.1],
            "TRENDING_DOWN": [0.03, 0.1],
            "SIDEWAYS": [0.01, 0.05],
            "VOLATILE": [0.05, 0.2],
            "LOW_VOLATILITY": [0.02, 0.08]
        },
        "mutation_strength": 0.2,
        "type": "float"
    }
}


class StrategyParameterManager:
    """增强版策略参数管理器"""
    
    def __init__(self):
        self.parameter_rules = PARAMETER_RULES
        self.strategy_types = STRATEGY_TYPES
        self.market_states = MARKET_STATES
        # 加载权重配置
        self.scoring_weights = self._load_scoring_weights()
        
    def _load_scoring_weights(self) -> Dict:
        """加载评分权重配置"""
        default_weights = {
            "total_return": 0.30,  # 总收益率
            "win_rate": 0.25,      # 胜率
            "sharpe_ratio": 0.20,  # 夏普比率
            "max_drawdown": 0.15,  # 最大回撤
            "profit_factor": 0.10  # 盈亏比
        }
        
        try:
            weights_file = "strategy_scoring_weights.json"
            if os.path.exists(weights_file):
                with open(weights_file, "r") as f:
                    weights = json.load(f)
                return weights
            else:
                return default_weights
        except Exception:
            return default_weights
    
    def save_scoring_weights(self, weights: Dict):
        """保存评分权重配置"""
        try:
            with open("strategy_scoring_weights.json", "w") as f:
                json.dump(weights, f, indent=2)
        except Exception as e:
            print(f"保存评分权重配置失败: {e}")
    
    def adapt_parameters_to_market(self, strategy_type: str, market_state: str) -> Dict:
        """根据市场状态调整参数范围"""
        adapted_params = {}
        
        for param_name, config in self.parameter_rules.items():
            # 检查参数是否适用于当前策略类型
            if not param_name.startswith(strategy_type.split("_")[0]):
                # 风控参数适用于所有策略
                if not param_name in ["max_position_size", "stop_loss", "take_profit"]:
                    continue
            
            # 获取市场适应性设置
            market_adaption = config.get("market_adaption", {})
            
            # 如果有针对当前市场状态的适应性范围，则使用
            if market_state in market_adaption:
                adapted_range = market_adaption[market_state]
                adapted_params[param_name] = {
                    "range": adapted_range,
                    "step": config["step"],
                    "type": config["type"]
                }
            else:
                # 否则使用默认范围
                adapted_params[param_name] = {
                    "range": config["range"],
                    "step": config["step"],
                    "type": config["type"]
                }
        
        return adapted_params
    
    def generate_parameter_mutations(self, base_params: Dict, mutation_strength: float = 1.0,
                               market_state: str = "SIDEWAYS") -> Dict:
        """
        生成参数变异
        :param base_params: 基础参数
        :param mutation_strength: 变异强度，范围0-1
        :param market_state: 市场状态
        :return: 变异后的参数
        """
        mutated_params = {}
        
        for param_name, value in base_params.items():
            if param_name not in self.parameter_rules:
                mutated_params[param_name] = value
                continue
                
            config = self.parameter_rules[param_name]
            param_range = config["range"]
            param_step = config["step"]
            mutation_rate = config.get("mutation_strength", 0.2) * mutation_strength
            
            # 根据市场状态调整参数范围
            market_adaption = config.get("market_adaption", {})
            if market_state in market_adaption:
                param_range = market_adaption[market_state]
            
            # 计算变异
            if config["type"] == "int":
                range_size = param_range[1] - param_range[0]
                mutation_size = int(range_size * mutation_rate)
                mutation = random.randint(-mutation_size, mutation_size)
                new_value = int(value) + mutation
                # 确保在范围内
                new_value = max(param_range[0], min(new_value, param_range[1]))
                mutated_params[param_name] = new_value
            elif config["type"] == "float":
                range_size = param_range[1] - param_range[0]
                mutation_size = range_size * mutation_rate
                mutation = random.uniform(-mutation_size, mutation_size)
                new_value = float(value) + mutation
                # 确保在范围内
                new_value = max(param_range[0], min(new_value, param_range[1]))
                # 四舍五入到指定精度
                decimal_places = len(str(param_step).split(".")[-1]) if "." in str(param_step) else 0
                mutated_params[param_name] = round(new_value, decimal_places)
            else:
                mutated_params[param_name] = value
        
        return mutated_params
    
    def parameter_crossover(self, parent1_params: Dict, parent2_params: Dict,
                     crossover_rate: float = 0.7) -> Dict:
        """
        参数交叉
        :param parent1_params: 父代1参数
        :param parent2_params: 父代2参数
        :param crossover_rate: 交叉率
        :return: 交叉后的参数
        """
        child_params = {}
        
        # 获取两个父代共有的参数
        common_params = set(parent1_params.keys()).intersection(set(parent2_params.keys()))
        
        for param in common_params:
            # 按照交叉率决定是否交换参数
            if random.random() < crossover_rate:
                # 50%概率选择父代1或父代2的参数
                child_params[param] = parent1_params[param] if random.random() < 0.5 else parent2_params[param]
            else:
                # 不交换，随机选择一个父代的参数
                source = random.choice([parent1_params, parent2_params])
                child_params[param] = source[param]
        
        # 处理非共有参数
        for param in set(parent1_params.keys()) - common_params:
            child_params[param] = parent1_params[param]
            
        for param in set(parent2_params.keys()) - common_params:
            child_params[param] = parent2_params[param]
        
        return child_params
    
    def calculate_strategy_score(self, stats: Dict, market_state: str = None) -> float:
        """
        计算策略评分 - 2.0增强版
        根据市场状态动态调整评分权重
        
        :param stats: 策略统计数据
        :param market_state: 市场状态
        :return: 综合评分(0-100)
        """
        # 获取基础统计数据
        total_return = float(stats.get('total_return', 0))
        win_rate = float(stats.get('win_rate', 0))
        sharpe_ratio = float(stats.get('sharpe_ratio', 1.0))
        max_drawdown = abs(float(stats.get('max_drawdown', 0.05)))
        profit_factor = float(stats.get('profit_factor', 1.5))
        total_trades = int(stats.get('total_trades', 0))
        
        # 根据市场状态调整权重
        weights = self.scoring_weights.copy()
        
        if market_state:
            # 在不同市场状态下调整权重
            if market_state == "TRENDING_UP" or market_state == "TRENDING_DOWN":
                # 趋势市场更看重总收益和夏普比率
                weights["total_return"] = weights["total_return"] * 1.2
                weights["sharpe_ratio"] = weights["sharpe_ratio"] * 1.2
                weights["win_rate"] = weights["win_rate"] * 0.8
            elif market_state == "SIDEWAYS" or market_state == "RANGING":
                # 震荡市场更看重胜率和盈亏比
                weights["win_rate"] = weights["win_rate"] * 1.2
                weights["profit_factor"] = weights["profit_factor"] * 1.2
                weights["total_return"] = weights["total_return"] * 0.8
            elif market_state == "VOLATILE":
                # 高波动市场更看重最大回撤控制
                weights["max_drawdown"] = weights["max_drawdown"] * 1.5
                weights["sharpe_ratio"] = weights["sharpe_ratio"] * 1.2
            
            # 归一化权重
            weight_sum = sum(weights.values())
            for k in weights:
                weights[k] = weights[k] / weight_sum
        
        # 各项指标评分计算
        
        # 收益率分数 (指数函数，高收益更高分)
        return_score = min(100, max(0, 50 + 50 * np.tanh(total_return * 2)))
        
        # 胜率分数 (线性，胜率越高分数越高)
        win_rate_score = win_rate * 100
        
        # 夏普比率分数 (指数函数，高夏普更高分)
        sharpe_score = min(100, max(0, 50 * np.tanh(sharpe_ratio)))
        
        # 最大回撤分数 (反比例，回撤越小分数越高)
        drawdown_score = max(0, 100 - max_drawdown * 500)
        
        # 盈亏比分数 (指数函数，高盈亏比更高分)
        profit_factor_score = min(100, max(0, 50 * np.tanh((profit_factor - 1) * 2)))
        
        # 交易次数调整因子
        trade_count_factor = 1.0
        if total_trades < 10:
            trade_count_factor = 0.7 + 0.03 * total_trades  # 交易次数少，降低评分
        elif total_trades > 50:
            trade_count_factor = min(1.2, 1.0 + 0.004 * (total_trades - 50))  # 交易次数多，提高评分
        
        # 计算加权总分
        weighted_score = (
            return_score * weights["total_return"] +
            win_rate_score * weights["win_rate"] +
            sharpe_score * weights["sharpe_ratio"] +
            drawdown_score * weights["max_drawdown"] +
            profit_factor_score * weights["profit_factor"]
        )
        
        # 应用交易次数调整
        final_score = weighted_score * trade_count_factor
        
        # 将分数限制在0-100范围内
        return min(100, max(0, final_score))
    
    def get_evolution_direction(self, param_name: str, performance_change: float, 
                              market_state: str = None) -> float:
        """
        确定参数进化方向
        :param param_name: 参数名称
        :param performance_change: 性能变化(正数表示改善，负数表示恶化)
        :param market_state: 市场状态
        :return: 进化方向系数(-1.0到1.0)
        """
        if param_name not in self.parameter_rules:
            return 0.0
            
        config = self.parameter_rules[param_name]
        logic = config.get("profit_logic", "direct")
        
        # 性能未改变，返回0
        if abs(performance_change) < 0.0001:
            return 0.0
        
        # 根据不同的参数调整逻辑确定方向    
        if logic == "direct":
            # 性能提升则沿同方向调整，恶化则反向
            return 0.5 if performance_change > 0 else -0.5
            
        elif logic == "inverse":
            # 与direct相反
            return -0.5 if performance_change > 0 else 0.5
            
        elif logic == "dynamic":
            # 根据市场状态动态决定
            if not market_state or market_state in ["TRENDING_UP", "TRENDING_DOWN"]:
                # 趋势市场中，性能提升则增加参数
                return 0.7 if performance_change > 0 else -0.7
            else:
                # 其他市场中，性能提升则减小参数
                return -0.5 if performance_change > 0 else 0.5
                
        elif logic == "risk_adjusted":
            # 风险控制参数，考虑风险和收益的平衡
            if market_state == "VOLATILE":
                # 高波动市场，优先考虑风险控制
                return -0.6 if performance_change > 0 else 0.4
            else:
                # 其他市场，平衡风险和收益
                return 0.4 if performance_change > 0 else -0.4
                
        elif logic == "moderate":
            # 缓和的调整
            return 0.3 if performance_change > 0 else -0.3
            
        return 0.0
    
    def detect_market_state(self, price_data: List[float], volume_data: List[float] = None) -> str:
        """
        检测当前市场状态
        :param price_data: 价格数据
        :param volume_data: 成交量数据(可选)
        :return: 市场状态
        """
        if len(price_data) < 20:
            return "SIDEWAYS"  # 默认状态
            
        # 计算最近的价格变化
        recent_prices = price_data[-20:]
        price_changes = [recent_prices[i] / recent_prices[i-1] - 1 for i in range(1, len(recent_prices))]
        
        # 计算趋势指标
        price_mean = np.mean(recent_prices)
        price_std = np.std(recent_prices)
        price_volatility = price_std / price_mean
        
        # 计算趋势强度
        trend_strength = np.abs(recent_prices[-1] - recent_prices[0]) / (price_std * np.sqrt(len(recent_prices)))
        
        # 判断是否处于突破状态
        is_breakout = False
        if len(price_data) > 50:
            long_term_std = np.std(price_data[-50:])
            recent_move = abs(price_data[-1] - price_data[-5])
            if recent_move > 2.5 * long_term_std:
                is_breakout = True
        
        # 根据指标判断市场状态
        if is_breakout:
            return "BREAKOUT"
        elif trend_strength > 2.0:
            if price_data[-1] > price_data[-10]:
                return "TRENDING_UP"
            else:
                return "TRENDING_DOWN"
        elif price_volatility > 0.02:
            return "VOLATILE"
        elif price_volatility < 0.005:
            return "LOW_VOLATILITY"
        elif np.max(recent_prices) - np.min(recent_prices) < 0.03 * np.mean(recent_prices):
            return "SIDEWAYS"
        else:
            return "RANGING"


# 全局参数管理器实例
parameter_manager = StrategyParameterManager()

def get_parameter_rules():
    """获取参数规则"""
    return PARAMETER_RULES

def get_strategy_types():
    """获取支持的策略类型"""
    return STRATEGY_TYPES

def get_market_states():
    """获取市场状态类型"""
    return MARKET_STATES

def calculate_score(stats, market_state=None):
    """计算策略评分"""
    return parameter_manager.calculate_strategy_score(stats, market_state)

def get_parameter_manager():
    """获取参数管理器实例"""
    return parameter_manager

def get_strategy_parameter_ranges(strategy_type=None):
    """
    获取策略参数范围配置
    :param strategy_type: 策略类型，如果提供则返回该策略类型的参数，否则返回所有参数
    :return: 参数范围配置字典
    """
    if strategy_type is None:
        return PARAMETER_RULES
    
    # 根据策略类型过滤参数
    filtered_params = {}
    strategy_prefix = strategy_type.split("_")[0].lower()
    
    for param_name, config in PARAMETER_RULES.items():
        # 检查参数是否适用于当前策略类型
        param_prefix = param_name.split("_")[0].lower()
        
        # 包含策略特定参数和通用风控参数
        if (param_prefix == strategy_prefix or 
            param_name in ["max_position_size", "stop_loss", "take_profit"] or
            param_prefix in ["max", "stop", "take", "profit"]):
            filtered_params[param_name] = config
    
    # 如果没有找到特定参数，返回一些基础参数
    if not filtered_params:
        # 返回通用参数
        basic_params = ["max_position_size", "stop_loss", "take_profit"]
        for param in basic_params:
            if param in PARAMETER_RULES:
                filtered_params[param] = PARAMETER_RULES[param]
    
    return filtered_params

def get_all_strategy_types():
    """获取所有策略类型列表"""
    return STRATEGY_TYPES


if __name__ == "__main__":
    # 测试功能
    manager = StrategyParameterManager()
    
    # 测试市场状态检测
    import random
    test_prices = [100]
    for i in range(100):
        change = random.normalvariate(0.001, 0.01)
        test_prices.append(test_prices[-1] * (1 + change))
    
    market = manager.detect_market_state(test_prices)
    print(f"检测到的市场状态: {market}")
    
    # 测试评分计算
    test_stats = {
        'total_return': 0.35,
        'win_rate': 0.65,
        'sharpe_ratio': 2.1,
        'max_drawdown': 0.12,
        'profit_factor': 1.8,
        'total_trades': 45
    }
    
    score = manager.calculate_strategy_score(test_stats, market)
    print(f"策略评分: {score:.2f}")
    
    # 测试参数调整
    base_params = {
        "trend_period": 50,
        "trend_threshold": 0.03
    }
    
    # 生成变异
    mutated = manager.generate_parameter_mutations(base_params, 0.5, market)
    print(f"基础参数: {base_params}")
    print(f"变异参数: {mutated}") 