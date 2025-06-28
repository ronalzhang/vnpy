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
from decimal import Decimal, getcontext

# 设置Decimal的精度
getcontext().prec = 10


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
        "mutation_strength": Decimal("0.2"), # 变异强度
        "type": "int"
    },
    "momentum_threshold": {
        "range": [Decimal("0.01"), Decimal("0.3")],
        "optimal": Decimal("0.05"),
        "step": Decimal("0.01"),
        "profit_logic": "direct", # 参数调整逻辑：收益越高，参数越接近最优
        "description": "动量阈值",
        "market_adaption": {
            "TRENDING_UP": [Decimal("0.03"), Decimal("0.1")],
            "TRENDING_DOWN": [Decimal("0.03"), Decimal("0.1")],
            "SIDEWAYS": [Decimal("0.01"), Decimal("0.05")],
            "VOLATILE": [Decimal("0.05"), Decimal("0.15")],
            "LOW_VOLATILITY": [Decimal("0.01"), Decimal("0.03")]
        },
        "mutation_strength": Decimal("0.1"),
        "type": "decimal"
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
        "mutation_strength": Decimal("0.2"),
        "type": "int"
    },
    "std_dev_multiplier": {
        "range": [Decimal("1.0"), Decimal("3.0")],
        "optimal": Decimal("2.0"),
        "step": Decimal("0.1"),
        "profit_logic": "direct",
        "description": "标准差倍数",
        "market_adaption": {
            "TRENDING_UP": [Decimal("1.5"), Decimal("2.5")],
            "TRENDING_DOWN": [Decimal("1.5"), Decimal("2.5")],
            "SIDEWAYS": [Decimal("1.8"), Decimal("2.2")],
            "VOLATILE": [Decimal("2.0"), Decimal("3.0")],
            "LOW_VOLATILITY": [Decimal("1.0"), Decimal("2.0")]
        },
        "mutation_strength": Decimal("0.15"),
        "type": "decimal"
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
        "mutation_strength": Decimal("0.25"),
        "type": "int"
    },
    "breakout_threshold": {
        "range": [Decimal("0.005"), Decimal("0.05")],
        "optimal": Decimal("0.01"),
        "step": Decimal("0.001"),
        "profit_logic": "direct",
        "description": "突破阈值",
        "market_adaption": {
            "TRENDING_UP": [Decimal("0.01"), Decimal("0.02")],
            "TRENDING_DOWN": [Decimal("0.01"), Decimal("0.02")],
            "SIDEWAYS": [Decimal("0.005"), Decimal("0.01")],
            "VOLATILE": [Decimal("0.02"), Decimal("0.05")],
            "BREAKOUT": [Decimal("0.01"), Decimal("0.03")],
            "REVERSAL": [Decimal("0.015"), Decimal("0.035")]
        },
        "mutation_strength": Decimal("0.2"),
        "type": "decimal"
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
        "mutation_strength": Decimal("0.3"),
        "type": "int"
    },
    "grid_spacing": {
        "range": [Decimal("0.002"), Decimal("0.05")],
        "optimal": Decimal("0.01"),
        "step": Decimal("0.001"),
        "profit_logic": "direct",
        "description": "网格间距",
        "market_adaption": {
            "TRENDING_UP": [Decimal("0.01"), Decimal("0.02")],
            "TRENDING_DOWN": [Decimal("0.01"), Decimal("0.02")],
            "SIDEWAYS": [Decimal("0.005"), Decimal("0.015")],
            "VOLATILE": [Decimal("0.02"), Decimal("0.05")],
            "LOW_VOLATILITY": [Decimal("0.002"), Decimal("0.01")],
            "RANGING": [Decimal("0.008"), Decimal("0.025")]
        },
        "mutation_strength": Decimal("0.2"),
        "type": "decimal"
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
        "mutation_strength": Decimal("0.25"),
        "type": "int"
    },
    "trend_threshold": {
        "range": [Decimal("0.01"), Decimal("0.1")],
        "optimal": Decimal("0.03"),
        "step": Decimal("0.005"),
        "profit_logic": "direct",
        "description": "趋势确认阈值",
        "market_adaption": {
            "TRENDING_UP": [Decimal("0.02"), Decimal("0.05")],
            "TRENDING_DOWN": [Decimal("0.02"), Decimal("0.05")],
            "SIDEWAYS": [Decimal("0.01"), Decimal("0.03")],
            "VOLATILE": [Decimal("0.04"), Decimal("0.1")],
            "LOW_VOLATILITY": [Decimal("0.01"), Decimal("0.03")],
        },
        "mutation_strength": Decimal("0.15"),
        "type": "decimal"
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
        "mutation_strength": Decimal("0.3"),
        "type": "int"
    },
    "hf_threshold": {
        "range": [Decimal("0.001"), Decimal("0.01")],
        "optimal": Decimal("0.002"),
        "step": Decimal("0.0005"),
        "profit_logic": "direct",
        "description": "高频交易阈值",
        "market_adaption": {
            "TRENDING_UP": [Decimal("0.001"), Decimal("0.003")],
            "TRENDING_DOWN": [Decimal("0.001"), Decimal("0.003")],
            "SIDEWAYS": [Decimal("0.0015"), Decimal("0.004")],
            "VOLATILE": [Decimal("0.003"), Decimal("0.01")],
            "LOW_VOLATILITY": [Decimal("0.001"), Decimal("0.002")]
        },
        "mutation_strength": Decimal("0.25"),
        "type": "decimal"
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
        "mutation_strength": Decimal("0.3"),
        "type": "int"
    },
    "profit_target": {
        "range": [Decimal("0.001"), Decimal("0.02")],
        "optimal": Decimal("0.005"),
        "step": Decimal("0.001"),
        "profit_logic": "direct",
        "description": "利润目标",
        "market_adaption": {
            "TRENDING_UP": [Decimal("0.003"), Decimal("0.01")],
            "TRENDING_DOWN": [Decimal("0.003"), Decimal("0.01")],
            "SIDEWAYS": [Decimal("0.001"), Decimal("0.005")],
            "VOLATILE": [Decimal("0.005"), Decimal("0.02")],
            "LOW_VOLATILITY": [Decimal("0.001"), Decimal("0.003")]
        },
        "mutation_strength": Decimal("0.2"),
        "type": "decimal"
    },
    
    # 套利策略参数
    "price_diff_threshold": {
        "range": [Decimal("0.001"), Decimal("0.05")],
        "optimal": Decimal("0.01"),
        "step": Decimal("0.001"),
        "profit_logic": "direct",
        "description": "价格差异阈值",
        "market_adaption": {
            "TRENDING_UP": [Decimal("0.005"), Decimal("0.02")],
            "TRENDING_DOWN": [Decimal("0.005"), Decimal("0.02")],
            "SIDEWAYS": [Decimal("0.002"), Decimal("0.01")],
            "VOLATILE": [Decimal("0.01"), Decimal("0.05")],
            "LOW_VOLATILITY": [Decimal("0.001"), Decimal("0.008")]
        },
        "mutation_strength": Decimal("0.2"),
        "type": "decimal"
    },
    
    # 风控参数
    "max_position_size": {
        "range": [Decimal("0.01"), Decimal("0.5")],
        "optimal": Decimal("0.1"),
        "step": Decimal("0.01"),
        "profit_logic": "risk_adjusted", # 根据风险调整收益
        "description": "最大仓位比例",
        "market_adaption": {
            "TRENDING_UP": [Decimal("0.05"), Decimal("0.2")],
            "TRENDING_DOWN": [Decimal("0.05"), Decimal("0.15")],
            "SIDEWAYS": [Decimal("0.03"), Decimal("0.1")],
            "VOLATILE": [Decimal("0.01"), Decimal("0.08")],
            "LOW_VOLATILITY": [Decimal("0.05"), Decimal("0.3")]
        },
        "mutation_strength": Decimal("0.1"),
        "type": "decimal"
    },
    "stop_loss": {
        "range": [Decimal("0.01"), Decimal("0.1")],
        "optimal": Decimal("0.03"),
        "step": Decimal("0.005"),
        "profit_logic": "risk_adjusted",
        "description": "止损比例",
        "market_adaption": {
            "TRENDING_UP": [Decimal("0.02"), Decimal("0.05")],
            "TRENDING_DOWN": [Decimal("0.02"), Decimal("0.05")],
            "SIDEWAYS": [Decimal("0.01"), Decimal("0.03")],
            "VOLATILE": [Decimal("0.03"), Decimal("0.1")],
            "LOW_VOLATILITY": [Decimal("0.01"), Decimal("0.03")]
        },
        "mutation_strength": Decimal("0.15"),
        "type": "decimal"
    },
    "take_profit": {
        "range": [Decimal("0.01"), Decimal("0.2")],
        "optimal": Decimal("0.05"),
        "step": Decimal("0.01"),
        "profit_logic": "risk_adjusted",
        "description": "止盈比例",
        "market_adaption": {
            "TRENDING_UP": [Decimal("0.03"), Decimal("0.1")],
            "TRENDING_DOWN": [Decimal("0.03"), Decimal("0.1")],
            "SIDEWAYS": [Decimal("0.01"), Decimal("0.05")],
            "VOLATILE": [Decimal("0.05"), Decimal("0.2")],
            "LOW_VOLATILITY": [Decimal("0.02"), Decimal("0.08")]
        },
        "mutation_strength": Decimal("0.2"),
        "type": "decimal"
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
            "total_return": Decimal("0.30"),  # 总收益率
            "win_rate": Decimal("0.25"),      # 胜率
            "sharpe_ratio": Decimal("0.20"),  # 夏普比率
            "max_drawdown": Decimal("0.15"),  # 最大回撤
            "profit_factor": Decimal("0.10")  # 盈亏比
        }
        
        try:
            weights_file = "strategy_scoring_weights.json"
            if os.path.exists(weights_file):
                with open(weights_file, "r") as f:
                    weights_str = json.load(f)
                    weights = {k: Decimal(v) for k, v in weights_str.items()}
                return weights
            else:
                return default_weights
        except Exception:
            return default_weights
    
    def save_scoring_weights(self, weights: Dict):
        """保存评分权重配置"""
        try:
            with open("strategy_scoring_weights.json", "w") as f:
                weights_str = {k: str(v) for k, v in weights.items()}
                json.dump(weights_str, f, indent=2)
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
                    "range": [Decimal(str(v)) for v in adapted_range] if isinstance(config["type"], str) and config["type"] == "decimal" else adapted_range,
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
            # 🔧 修复：确保mutation_strength类型一致，避免Decimal * float错误
            config_mutation_strength = config.get("mutation_strength", 0.2)
            if isinstance(config_mutation_strength, Decimal):
                config_mutation_strength = float(config_mutation_strength)
            mutation_rate = config_mutation_strength * mutation_strength
            
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
            elif config["type"] == "decimal":
                param_range_dec = [Decimal(str(v)) for v in param_range]
                range_size = param_range_dec[1] - param_range_dec[0]
                # 🔧 修复：确保mutation_rate也是Decimal类型
                mutation_rate_dec = Decimal(str(mutation_rate))
                mutation_size = range_size * mutation_rate_dec
                
                # 生成一个Decimal类型的随机数
                random_decimal = Decimal(str(random.uniform(-1, 1)))
                mutation = mutation_size * random_decimal

                new_value = Decimal(str(value)) + mutation
                # 确保在范围内
                new_value = max(param_range_dec[0], min(new_value, param_range_dec[1]))
                
                # 四舍五入到指定精度
                step_str = str(config["step"])
                if "." in step_str:
                    decimal_places = len(step_str.split('.')[-1])
                    mutated_params[param_name] = new_value.quantize(Decimal(step_str))
                else:
                    mutated_params[param_name] = new_value.quantize(Decimal('1'))
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
    
    def calculate_strategy_score(self, stats: Dict, market_state: Optional[str] = None) -> Decimal:
        """
        计算策略评分 - 2.0增强版
        根据市场状态动态调整评分权重
        
        :param stats: 策略统计数据
        :param market_state: 市场状态
        :return: 综合评分(0-100)
        """
        # 获取基础统计数据并转换为Decimal
        total_return = Decimal(str(stats.get('total_return', '0')))
        win_rate = Decimal(str(stats.get('win_rate', '0')))
        sharpe_ratio = Decimal(str(stats.get('sharpe_ratio', '1.0')))
        max_drawdown = abs(Decimal(str(stats.get('max_drawdown', '0.05'))))
        profit_factor = Decimal(str(stats.get('profit_factor', '1.5')))
        total_trades = int(stats.get('total_trades', 0))
        
        # 根据市场状态调整权重
        weights = self.scoring_weights.copy()
        
        if market_state:
            # 在不同市场状态下调整权重
            if market_state == "TRENDING_UP" or market_state == "TRENDING_DOWN":
                # 趋势市场更看重总收益和夏普比率
                weights["total_return"] *= Decimal("1.2")
                weights["sharpe_ratio"] *= Decimal("1.2")
                weights["win_rate"] *= Decimal("0.8")
            elif market_state == "SIDEWAYS" or market_state == "RANGING":
                # 震荡市场更看重胜率和盈亏比
                weights["win_rate"] *= Decimal("1.2")
                weights["profit_factor"] *= Decimal("1.2")
                weights["total_return"] *= Decimal("0.8")
            elif market_state == "VOLATILE":
                # 高波动市场更看重最大回撤控制
                weights["max_drawdown"] *= Decimal("1.5")
                weights["sharpe_ratio"] *= Decimal("1.2")
            
            # 归一化权重
            weight_sum = sum(weights.values())
            if weight_sum > 0:
                for k in weights:
                    weights[k] = weights[k] / weight_sum
        
        # 各项指标评分计算
        
        # 收益率分数 (指数函数，高收益更高分) - np.tanh需要float
        return_score = Decimal("50") + Decimal("50") * Decimal(str(np.tanh(float(total_return) * 2)))
        return_score = min(Decimal("100"), max(Decimal("0"), return_score))

        # 胜率分数 (线性，胜率越高分数越高)
        win_rate_score = win_rate * Decimal("100")
        
        # 夏普比率分数 (指数函数，高夏普更高分) - np.tanh需要float
        sharpe_score = Decimal("50") * Decimal(str(np.tanh(float(sharpe_ratio))))
        sharpe_score = min(Decimal("100"), max(Decimal("0"), sharpe_score))
        
        # 最大回撤分数 (反比例，回撤越小分数越高)
        drawdown_score = max(Decimal("0"), Decimal("100") - max_drawdown * Decimal("500"))
        
        # 盈亏比分数 (指数函数，高盈亏比更高分) - np.tanh需要float
        profit_factor_score = Decimal("50") * Decimal(str(np.tanh(float(profit_factor - 1) * 2)))
        profit_factor_score = min(Decimal("100"), max(Decimal("0"), profit_factor_score))
        
        # 交易次数调整因子
        trade_count_factor = Decimal("1.0")
        total_trades_dec = Decimal(str(total_trades))  # 🔧 修复：转换为Decimal类型
        if total_trades < 10:
            trade_count_factor = Decimal("0.7") + Decimal("0.03") * total_trades_dec
        elif total_trades > 50:
            trade_count_factor = min(Decimal("1.2"), Decimal("1.0") + Decimal("0.004") * (total_trades_dec - Decimal("50")))
        
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
        return min(Decimal("100"), max(Decimal("0"), final_score))
    
    def get_evolution_direction(self, param_name: str, performance_change: Decimal, 
                              market_state: Optional[str] = None) -> Decimal:
        """
        确定参数进化方向
        :param param_name: 参数名称
        :param performance_change: 性能变化(正数表示改善，负数表示恶化)
        :param market_state: 市场状态
        :return: 进化方向系数(-1.0到1.0)
        """
        if param_name not in self.parameter_rules:
            return Decimal("0.0")
            
        config = self.parameter_rules[param_name]
        logic = config.get("profit_logic", "direct")
        
        # 性能未改变，返回0
        if abs(performance_change) < Decimal("0.0001"):
            return Decimal("0.0")
        
        # 根据不同的参数调整逻辑确定方向    
        if logic == "direct":
            # 性能提升则沿同方向调整，恶化则反向
            return Decimal("0.5") if performance_change > 0 else Decimal("-0.5")
            
        elif logic == "inverse":
            # 与direct相反
            return Decimal("-0.5") if performance_change > 0 else Decimal("0.5")
            
        elif logic == "dynamic":
            # 根据市场状态动态决定
            if not market_state or market_state in ["TRENDING_UP", "TRENDING_DOWN"]:
                # 趋势市场中，性能提升则增加参数
                return Decimal("0.7") if performance_change > 0 else Decimal("-0.7")
            else:
                # 其他市场中，性能提升则减小参数
                return Decimal("-0.5") if performance_change > 0 else Decimal("0.5")
                
        elif logic == "risk_adjusted":
            # 风险控制参数，考虑风险和收益的平衡
            if market_state == "VOLATILE":
                # 高波动市场，优先考虑风险控制
                return Decimal("-0.6") if performance_change > 0 else Decimal("0.4")
            else:
                # 其他市场，平衡风险和收益
                return Decimal("0.4") if performance_change > 0 else Decimal("-0.4")
                
        elif logic == "moderate":
            # 缓和的调整
            return Decimal("0.3") if performance_change > 0 else Decimal("-0.3")
            
        return Decimal("0.0")
    
    def detect_market_state(self, price_data: List[float], volume_data: Optional[List[float]] = None) -> str:
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

def calculate_score(stats, market_state: Optional[str] = None):
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


def get_strategy_default_parameters(strategy_type):
    """
    🔧 修复：获取策略的默认参数配置
    根据策略类型返回对应的默认参数
    """
    # 定义各种策略类型的默认参数
    default_params = {
        'momentum': {
            # 基础参数
            'lookback_period': 20, 'threshold': 0.02, 'quantity': 100,
            'momentum_threshold': 0.01, 'volume_threshold': 2.0,
            # 技术指标参数 - RSI
            'rsi_period': 14, 'rsi_oversold': 30, 'rsi_overbought': 70,
            # MACD指标参数
            'macd_fast_period': 12, 'macd_slow_period': 26, 'macd_signal_period': 9,
            # 价格动量参数
            'price_momentum_period': 10, 'volume_momentum_period': 20,
            # 风险控制参数
            'stop_loss_pct': 2.0, 'take_profit_pct': 4.0, 'max_drawdown_pct': 5.0,
            'position_sizing': 0.1, 'max_position_risk': 0.05,
            # 时间管理参数
            'min_hold_time': 300, 'max_hold_time': 3600,
            'trade_start_hour': 0, 'trade_end_hour': 24
        },
        'mean_reversion': {
            # 基础参数
            'lookback_period': 30, 'std_multiplier': 2.0, 'quantity': 100,
            'reversion_threshold': 0.02, 'min_deviation': 0.01,
            # 布林带参数
            'bb_period': 20, 'bb_std_dev': 2.0, 'bb_squeeze_threshold': 0.1,
            # 均值回归指标
            'z_score_threshold': 2.0, 'correlation_threshold': 0.7,
            'volatility_threshold': 0.02, 'mean_lookback': 50,
            # Bollinger Bands扩展参数
            'bb_upper_threshold': 0.9, 'bb_lower_threshold': 0.1,
            # 风险控制
            'stop_loss_pct': 1.5, 'take_profit_pct': 3.0, 'max_positions': 3,
            'min_profit_target': 0.5, 'position_scaling': 0.8,
            # 时间控制
            'entry_cooldown': 600, 'max_trade_duration': 7200,
            'avoid_news_hours': True, 'weekend_trading': False
        },
        'grid_trading': {
            # 网格基础参数
            'grid_spacing': 1.0, 'grid_count': 10, 'quantity': 1000,
            'lookback_period': 100, 'min_profit': 0.5,
            # 网格高级参数
            'upper_price_limit': 110000, 'lower_price_limit': 90000,
            'grid_density': 0.5, 'rebalance_threshold': 5.0,
            'profit_taking_ratio': 0.8, 'grid_spacing_type': 'arithmetic',
            # 动态调整参数
            'volatility_adjustment': True, 'trend_filter_enabled': True,
            'volume_weighted': True, 'dynamic_spacing': True,
            # 网格优化参数
            'grid_adaptation_period': 24, 'price_range_buffer': 0.1,
            # 风险管理
            'max_grid_exposure': 10000, 'emergency_stop_loss': 10.0,
            'grid_pause_conditions': True, 'liquidity_threshold': 1000000,
            'single_grid_risk': 0.02
        },
        'breakout': {
            # 突破基础参数
            'lookback_period': 20, 'breakout_threshold': 1.5, 'quantity': 50,
            'volume_threshold': 2.0, 'confirmation_periods': 3,
            # 技术指标确认
            'atr_period': 14, 'atr_multiplier': 2.0,
            'volume_ma_period': 20, 'price_ma_period': 50,
            'momentum_confirmation': True, 'volume_confirmation': True,
            # 假突破过滤
            'false_breakout_filter': True, 'pullback_tolerance': 0.3,
            'breakout_strength_min': 1.2, 'minimum_breakout_volume': 1.5,
            # 突破确认参数
            'breakout_confirmation_candles': 2, 'resistance_support_buffer': 0.1,
            # 风险控制
            'stop_loss_atr_multiple': 2.0, 'take_profit_atr_multiple': 4.0,
            'trailing_stop_enabled': True, 'max_holding_period': 14400,
            'position_risk_limit': 0.03
        },
        'high_frequency': {
            # 高频基础参数
            'quantity': 100, 'min_profit': 0.05, 'volatility_threshold': 0.001,
            'lookback_period': 10, 'signal_interval': 30,
            # 微观结构参数
            'bid_ask_spread_threshold': 0.01, 'order_book_depth_min': 1000,
            'tick_size_multiple': 1.0, 'latency_threshold': 100,
            'market_impact_limit': 0.001, 'slippage_tolerance': 0.002,
            # 高频交易优化
            'order_book_levels': 5, 'imbalance_threshold': 0.3,
            'tick_rule_filter': True, 'momentum_timeframe': 60,
            # 风险和执行
            'max_order_size': 1000, 'inventory_limit': 5000,
            'pnl_stop_loss': 100, 'correlation_hedge': True,
            'max_drawdown_hf': 2.0, 'daily_loss_limit': 500,
            # 时间控制
            'trading_session_length': 3600, 'cooldown_period': 60,
            'avoid_rollover': True, 'market_hours_only': True
        },
        'trend_following': {
            # 趋势基础参数
            'lookback_period': 50, 'trend_threshold': 1.0, 'quantity': 100,
            'trend_strength_min': 0.3, 'trend_duration_min': 30,
            # 趋势识别参数
            'ema_fast_period': 12, 'ema_slow_period': 26,
            'adx_period': 14, 'adx_threshold': 25,
            'slope_threshold': 0.001, 'trend_angle_min': 15,
            # 趋势确认指标
            'macd_confirmation': True, 'volume_confirmation': True,
            'momentum_confirmation': True, 'multi_timeframe': True,
            'ichimoku_enabled': True, 'parabolic_sar_enabled': True,
            # 趋势过滤参数
            'noise_filter_enabled': True, 'trend_quality_min': 0.7,
            # 风险和退出
            'trailing_stop_pct': 3.0, 'trend_reversal_exit': True,
            'profit_lock_pct': 2.0, 'max_adverse_excursion': 4.0,
            'trend_exhaustion_exit': True, 'position_pyramid': False
        }
    }
    
    # 返回对应策略类型的参数，如果不存在则返回动量策略的参数作为默认值
    return default_params.get(strategy_type, default_params.get('momentum', {}))


if __name__ == "__main__":
    # 测试功能
    manager = StrategyParameterManager()
    
    # 测试市场状态检测
    import random
    test_prices = [100.0]
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