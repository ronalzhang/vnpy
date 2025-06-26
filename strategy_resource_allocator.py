#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略资源分配器
基于Kelly准则的资金动态分配与策略组合优化

作者: 系统架构优化团队
日期: 2025年6月8日
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Union, Optional
import logging
import json
import os
from datetime import datetime
from collections import defaultdict
import sqlite3
import math
from decimal import Decimal

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/resource_allocator.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 尝试导入市场环境分类器
try:
    from market_environment_classifier import get_market_classifier
except ImportError:
    logger.warning("市场环境分类器未找到，部分功能将受限")
    get_market_classifier = None


class StrategyResourceAllocator:
    """策略资源分配器 - 基于Kelly准则的资金动态分配与策略组合优化"""
    
    def __init__(self, config_file="resource_allocator_config.json"):
        """初始化策略资源分配器"""
        self.config = self._load_config(config_file)
        
        # 资金分配记录
        self.allocation_history = []
        
        # 策略表现记录
        self.strategy_performance = {}
        
        # 策略相关性矩阵
        self.correlation_matrix = {}
        
        # 最近一次分配结果缓存
        self.last_allocation = {}
        
        # 连接数据库
        self.db_connection = self._connect_database()
        
        # 加载市场分类器
        self.market_classifier = get_market_classifier() if get_market_classifier else None
        
        # 初始化完成
        logger.info("🚀 策略资源分配器初始化完成")
    
    def _load_config(self, config_file: str) -> Dict:
        """加载配置文件"""
        default_config = {
            "min_allocation": 0.05,        # 最小资金分配比例
            "max_allocation": 0.7,         # 最大资金分配比例
            "reserve_ratio": 0.1,          # 保留资金比例
            "performance_window": 30,      # 性能评估窗口(天)
            "kelly_fraction": 0.5,         # Kelly系数 (半Kelly更保守)
            "correlation_threshold": 0.7,  # 相关性阈值
            "diversity_weight": 0.3,       # 多样性权重
            "min_trades": 10,              # 最少交易次数要求
            "high_score_threshold": 70,    # 高分策略阈值
            "low_score_threshold": 50,     # 低分策略阈值
            "max_strategies": 5,           # 最大同时运行策略数
            "database_path": "quantitative.db",  # 数据库路径
            "dynamic_adjustment": True,    # 是否根据市场状态动态调整
            "adjustment_frequency": "daily" # 调整频率: daily, weekly, monthly
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                # 合并配置与默认值
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            else:
                logger.warning(f"配置文件 {config_file} 不存在，使用默认配置")
                return default_config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return default_config
    
    def _connect_database(self):
        """连接到数据库"""
        try:
            db_path = self.config["database_path"]
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return None
    
    def save_state(self, filepath="data/resource_allocator_state.json"):
        """保存分配器状态"""
        try:
            state = {
                "allocation_history": self.allocation_history[-50:],  # 只保留最近50条记录
                "strategy_performance": self.strategy_performance,
                "correlation_matrix": self.correlation_matrix,
                "last_allocation": self.last_allocation,
                "timestamp": datetime.now().isoformat()
            }
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            logger.info(f"资源分配器状态已保存到 {filepath}")
            return True
        except Exception as e:
            logger.error(f"保存状态失败: {e}")
            return False
    
    def load_state(self, filepath="data/resource_allocator_state.json"):
        """加载分配器状态"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    state = json.load(f)
                
                self.allocation_history = state.get("allocation_history", [])
                self.strategy_performance = state.get("strategy_performance", {})
                self.correlation_matrix = state.get("correlation_matrix", {})
                self.last_allocation = state.get("last_allocation", {})
                
                logger.info(f"资源分配器状态已从 {filepath} 加载")
                return True
            else:
                logger.warning(f"状态文件 {filepath} 不存在")
                return False
        except Exception as e:
            logger.error(f"加载状态失败: {e}")
            return False
    
    def update_strategy_performance(self, strategy_id: str, metrics: Dict) -> None:
        """更新策略性能指标"""
        if strategy_id not in self.strategy_performance:
            self.strategy_performance[strategy_id] = []
        
        # 添加时间戳
        metrics["timestamp"] = datetime.now().isoformat()
        
        # 确保字段存在
        required_fields = ["win_rate", "profit_factor", "sharpe_ratio", "max_drawdown", "total_pnl"]
        for field in required_fields:
            if field not in metrics:
                metrics[field] = 0.0
        
        # 添加记录
        self.strategy_performance[strategy_id].append(metrics)
        
        # 保持记录在合理范围内
        max_records = 100
        if len(self.strategy_performance[strategy_id]) > max_records:
            self.strategy_performance[strategy_id] = self.strategy_performance[strategy_id][-max_records:]
            
        logger.info(f"策略 {strategy_id} 性能指标已更新")
    
    def update_strategy_performances_from_db(self) -> None:
        """从数据库更新全部策略性能指标"""
        if not self.db_connection:
            logger.error("数据库未连接，无法更新策略性能")
            return
        
        try:
            cursor = self.db_connection.cursor()
            
            # 获取活跃策略
            cursor.execute("""
                SELECT id, name, final_score, created_at 
                FROM strategies 
                WHERE enabled = 1
            """)
            
            strategies = cursor.fetchall()
            logger.info(f"从数据库获取到 {len(strategies)} 个活跃策略")
            
            for strategy in strategies:
                strategy_id = strategy["id"]
                
                # 获取策略交易记录
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                        SUM(pnl) as total_pnl,
                        AVG(pnl) as avg_pnl,
                        MAX(pnl) as max_pnl,
                        MIN(pnl) as min_pnl
                    FROM strategy_trade_logs 
                    WHERE strategy_id = ? AND timestamp > datetime('now', '-30 days')
                """, (strategy_id,))
                
                trade_stats = cursor.fetchone()
                
                if not trade_stats or trade_stats["total_trades"] == 0:
                    logger.warning(f"策略 {strategy_id} 没有近期交易记录")
                    continue
                
                # 计算各项指标
                total_trades = trade_stats["total_trades"]
                winning_trades = trade_stats["winning_trades"] or 0
                win_rate = winning_trades / total_trades if total_trades > 0 else 0
                
                # 计算盈亏比
                profit_factor = 1.0
                cursor.execute("""
                    SELECT 
                        SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) as gross_profit,
                        ABS(SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END)) as gross_loss
                    FROM strategy_trade_logs 
                    WHERE strategy_id = ? AND timestamp > datetime('now', '-30 days')
                """, (strategy_id,))
                
                pnl_stats = cursor.fetchone()
                if pnl_stats and pnl_stats["gross_loss"] > 0:
                    profit_factor = (pnl_stats["gross_profit"] or 0) / pnl_stats["gross_loss"]
                
                # 获取回撤数据
                cursor.execute("""
                    SELECT MAX(drawdown) as max_drawdown
                    FROM strategy_statistics
                    WHERE strategy_id = ? AND timestamp > datetime('now', '-30 days')
                """, (strategy_id,))
                
                drawdown_stats = cursor.fetchone()
                max_drawdown = drawdown_stats["max_drawdown"] if drawdown_stats else 0.05
                
                # 计算夏普比率 (简化版)
                cursor.execute("""
                    SELECT pnl FROM strategy_trade_logs 
                    WHERE strategy_id = ? AND timestamp > datetime('now', '-30 days')
                    ORDER BY timestamp
                """, (strategy_id,))
                
                pnl_values = [row["pnl"] for row in cursor.fetchall()]
                sharpe_ratio = 0.0
                if pnl_values:
                    returns = np.array(pnl_values)
                    if len(returns) > 1 and np.std(returns) > 0:
                        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)  # 年化
                
                # 组合指标
                metrics = {
                    "win_rate": win_rate,
                    "profit_factor": profit_factor,
                    "sharpe_ratio": sharpe_ratio,
                    "max_drawdown": max_drawdown,
                    "total_pnl": trade_stats["total_pnl"] or 0,
                    "total_trades": total_trades,
                    "score": strategy["final_score"] or 50
                }
                
                # 更新策略性能记录
                self.update_strategy_performance(strategy_id, metrics)
                
            # 计算策略相关性
            self._calculate_strategy_correlations()
                
            logger.info("策略性能指标已从数据库更新")
            
        except Exception as e:
            logger.error(f"从数据库更新策略性能失败: {e}")
    
    def _calculate_strategy_correlations(self) -> None:
        """计算策略收益相关性矩阵"""
        if not self.db_connection:
            logger.error("数据库未连接，无法计算相关性")
            return
        
        try:
            cursor = self.db_connection.cursor()
            
            # 获取活跃策略列表
            cursor.execute("SELECT id FROM strategies WHERE enabled = 1")
            strategies = [row["id"] for row in cursor.fetchall()]
            
            if len(strategies) <= 1:
                logger.warning("活跃策略不足，无法计算相关性")
                return
            
            # 初始化结果矩阵
            self.correlation_matrix = {}
            
            # 获取每个策略的每日收益
            strategy_returns = {}
            for strategy_id in strategies:
                cursor.execute("""
                    SELECT DATE(timestamp) as date, SUM(pnl) as daily_pnl
                    FROM strategy_trade_logs
                    WHERE strategy_id = ? AND timestamp > datetime('now', '-60 days')
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                """, (strategy_id,))
                
                daily_returns = {}
                for row in cursor.fetchall():
                    daily_returns[row["date"]] = row["daily_pnl"] or 0
                
                strategy_returns[strategy_id] = daily_returns
            
            # 将每日收益转换为DataFrame进行相关性计算
            dates = set()
            for returns in strategy_returns.values():
                dates.update(returns.keys())
            
            dates = sorted(list(dates))
            if not dates:
                logger.warning("没有足够的历史数据计算相关性")
                return
                
            # 构建DataFrame
            data = {}
            for strategy_id, returns in strategy_returns.items():
                data[strategy_id] = [returns.get(date, 0) for date in dates]
            
            df = pd.DataFrame(data, index=dates)
            
            # 计算相关性矩阵
            if df.shape[1] > 1:  # 至少需要两个策略才能计算相关性
                correlation = df.corr()
                
                # 转换为字典格式
                for i in range(len(strategies)):
                    for j in range(i+1, len(strategies)):
                        id1 = strategies[i]
                        id2 = strategies[j]
                        if id1 in correlation.index and id2 in correlation.columns:
                            corr_value = correlation.loc[id1, id2]
                            if not pd.isna(corr_value):
                                key = f"{id1}:{id2}"
                                self.correlation_matrix[key] = float(corr_value)
            
            logger.info(f"已计算 {len(self.correlation_matrix)} 对策略的相关性")
            
        except Exception as e:
            logger.error(f"计算策略相关性失败: {e}")
    
    def get_correlation(self, strategy1: str, strategy2: str) -> float:
        """获取两个策略的相关性"""
        key1 = f"{strategy1}:{strategy2}"
        key2 = f"{strategy2}:{strategy1}"
        
        if key1 in self.correlation_matrix:
            return self.correlation_matrix[key1]
        elif key2 in self.correlation_matrix:
            return self.correlation_matrix[key2]
        else:
            # 默认相关性为0.5
            return 0.5
    
    def get_strategy_metrics(self, strategy_id: str) -> Dict:
        """获取策略的最新性能指标"""
        if strategy_id in self.strategy_performance and self.strategy_performance[strategy_id]:
            return self.strategy_performance[strategy_id][-1]
        else:
            # 没有性能记录时的默认值
            return {
                "win_rate": 0.5,
                "profit_factor": 1.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.05,
                "total_pnl": 0.0,
                "total_trades": 0,
                "score": 50.0
            }
    
    def calculate_kelly_position(self, strategy_id: str) -> float:
        """使用Kelly准则计算策略最优仓位"""
        metrics = self.get_strategy_metrics(strategy_id)
        
        win_rate = metrics["win_rate"]
        profit_factor = metrics["profit_factor"]
        
        # 如果没有交易记录或利润因子为0，返回最小分配
        if metrics["total_trades"] < self.config["min_trades"] or profit_factor <= 0:
            return self.config["min_allocation"]
        
        # 计算赔率
        if profit_factor > 1:
            odds = profit_factor
        else:
            odds = 1.0
        
        # Kelly公式: K = (p*(b+1)-1)/b，其中p为胜率，b为赔率
        kelly = (win_rate * (odds + 1) - 1) / odds
        
        # 应用Kelly分数并限制范围
        kelly_fraction = self.config["kelly_fraction"]
        position = kelly * kelly_fraction
        
        # 限制最大最小值
        position = max(self.config["min_allocation"], 
                     min(self.config["max_allocation"], position))
        
        logger.info(f"策略 {strategy_id} Kelly仓位: {position:.4f} (胜率: {win_rate:.2f}, 赔率: {odds:.2f})")
        return position
    
    def _apply_market_adjustment(self, allocations: Dict[str, float], 
                               market_state: str = None) -> Dict[str, float]:
        """根据市场状态调整分配"""
        if not market_state or not self.market_classifier:
            return allocations
        
        # 获取当前市场状态
        if market_state == "auto" and self.market_classifier:
            market_info = self.market_classifier.get_current_market_state()
            market_state = market_info["state"]
        
        # 获取该市场状态下的推荐策略
        recommended = []
        if self.market_classifier:
            recommended = self.market_classifier.get_best_strategies_for_state(market_state, 3)
        
        # 如果没有推荐，不作调整
        if not recommended:
            return allocations
        
        # 基于推荐调整分配
        adjusted = allocations.copy()
        
        for strategy_id in allocations:
            # 检查策略类型是否在推荐列表中
            strategy_type = strategy_id.split('_')[0] if '_' in strategy_id else strategy_id
            
            if strategy_type in recommended:
                # 增加推荐策略的分配
                boost_factor = 1.5 if strategy_type == recommended[0] else 1.3
                adjusted[strategy_id] = adjusted[strategy_id] * boost_factor
            else:
                # 减少非推荐策略的分配
                adjusted[strategy_id] = adjusted[strategy_id] * 0.7
        
        # 重新归一化
        total = sum(adjusted.values())
        if total > 0:
            for strategy_id in adjusted:
                adjusted[strategy_id] = adjusted[strategy_id] / total
        
        return adjusted
    
    def optimize_allocations(self, eligible_strategies: List[str],
                           total_capital: float,
                           market_state: str = "auto") -> Dict:
        """
        优化策略资金分配
        :param eligible_strategies: 可选策略列表
        :param total_capital: 总资金量
        :param market_state: 市场状态，"auto"表示自动检测
        :return: 分配结果
        """
        # 如果没有可用策略，返回空分配
        if not eligible_strategies:
            logger.warning("没有可用策略，无法进行分配优化")
            return {"allocations": {}, "total": 0, "reserve": total_capital}
        
        # 更新策略性能数据
        self.update_strategy_performances_from_db()
        
        # 计算每个策略的初始Kelly仓位
        initial_allocations = {}
        scores = {}
        
        for strategy_id in eligible_strategies:
            metrics = self.get_strategy_metrics(strategy_id)
            
            # 检查交易量是否满足要求
            if metrics["total_trades"] < self.config["min_trades"]:
                logger.info(f"策略 {strategy_id} 交易量不足 ({metrics['total_trades']}), 分配最低资金")
                initial_allocations[strategy_id] = self.config["min_allocation"]
            else:
                # 使用Kelly计算
                kelly_position = self.calculate_kelly_position(strategy_id)
                initial_allocations[strategy_id] = kelly_position
            
            # 记录策略分数
            scores[strategy_id] = metrics["score"]
        
        # 应用策略分数调整
        score_adjusted = {}
        for strategy_id, allocation in initial_allocations.items():
            score = scores[strategy_id]
            
            # 分数调整因子
            if score >= self.config["high_score_threshold"]:
                # 高分策略增加分配
                factor = 1.0 + (score - self.config["high_score_threshold"]) / 100
            elif score <= self.config["low_score_threshold"]:
                # 低分策略减少分配
                factor = 0.5 + (score / self.config["low_score_threshold"]) * 0.5
            else:
                factor = 1.0
                
            score_adjusted[strategy_id] = allocation * factor
        
        # 应用相关性调整，降低高相关策略的权重
        correlation_adjusted = score_adjusted.copy()
        
        # 只有当有多个策略时才进行相关性调整
        if len(eligible_strategies) > 1:
            for i, strategy1 in enumerate(eligible_strategies):
                correlation_penalty = 0.0
                
                # 计算与其他策略的平均相关性
                for j, strategy2 in enumerate(eligible_strategies):
                    if i != j:
                        correlation = abs(self.get_correlation(strategy1, strategy2))
                        # 高相关性施加惩罚
                        if correlation > self.config["correlation_threshold"]:
                            correlation_penalty += (correlation - self.config["correlation_threshold"]) * 0.5
                
                # 相关性权重惩罚，最多降低30%
                correlation_penalty = min(correlation_penalty, 0.3)
                correlation_adjusted[strategy1] *= (1 - correlation_penalty)
        
        # 应用市场状态调整
        if market_state and self.config["dynamic_adjustment"]:
            correlation_adjusted = self._apply_market_adjustment(correlation_adjusted, market_state)
        
        # 归一化并应用最大策略数限制
        sorted_strategies = sorted(correlation_adjusted.items(), 
                                 key=lambda x: x[1], reverse=True)
        
        max_strategies = min(self.config["max_strategies"], len(eligible_strategies))
        selected_strategies = sorted_strategies[:max_strategies]
        
        # 计算最终分配
        final_allocations = {s[0]: s[1] for s in selected_strategies}
        total_weight = sum(final_allocations.values())
        
        normalized_allocations = {}
        for strategy_id, weight in final_allocations.items():
            normalized_allocations[strategy_id] = weight / total_weight if total_weight > 0 else 0
        
        # 计算资金分配
        capital_allocations = {}
        available_capital = total_capital * (1 - self.config["reserve_ratio"])
        reserve = total_capital * self.config["reserve_ratio"]
        
        for strategy_id, ratio in normalized_allocations.items():
            capital_allocations[strategy_id] = available_capital * ratio
        
        # 记录分配历史
        allocation_record = {
            "timestamp": datetime.now().isoformat(),
            "market_state": market_state if market_state != "auto" else None,
            "total_capital": total_capital,
            "reserve": reserve,
            "allocations": capital_allocations
        }
        self.allocation_history.append(allocation_record)
        
        # 更新最近分配记录
        self.last_allocation = {
            "normalized": normalized_allocations,
            "capital": capital_allocations,
            "timestamp": datetime.now().isoformat(),
            "reserve": reserve,
            "total": total_capital
        }
        
        # 保存状态
        self.save_state()
        
        result = {
            "allocations": capital_allocations,
            "normalized": normalized_allocations,
            "total": available_capital,
            "reserve": reserve,
            "market_state": market_state if market_state != "auto" else None,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"策略资金分配优化完成，共分配 {len(capital_allocations)} 个策略，保留资金 {reserve:.2f}")
        return result
    
    def get_optimal_strategy_mix(self, available_strategies: List[Dict], 
                               max_strategies: int = None) -> List[str]:
        """
        获取最优策略组合
        :param available_strategies: 可用策略列表，包含策略ID和性能指标
        :param max_strategies: 最大策略数量，默认使用配置值
        :return: 最优策略ID列表
        """
        if not available_strategies:
            return []
        
        # 使用配置中的最大策略数
        if max_strategies is None:
            max_strategies = self.config["max_strategies"]
        
        # 如果可用策略少于等于最大数量，直接返回全部
        if len(available_strategies) <= max_strategies:
            return [s["id"] for s in available_strategies]
        
        # 按分数排序
        strategies_by_score = sorted(available_strategies, 
                                  key=lambda x: x.get("score", 0), 
                                  reverse=True)
        
        # 获取市场状态
        market_state = None
        if self.market_classifier:
            market_info = self.market_classifier.get_current_market_state()
            market_state = market_info["state"]
            
            # 获取该市场状态下的推荐策略类型
            recommended_types = self.market_classifier.get_best_strategies_for_state(market_state)
            
            # 优先选择推荐的策略类型
            prioritized = []
            for s in strategies_by_score:
                strategy_type = s["id"].split('_')[0] if '_' in s["id"] else s["id"]
                if strategy_type in recommended_types:
                    s["priority_boost"] = True
                    prioritized.append(s)
            
            # 如果有推荐策略，确保至少选择一个
            if prioritized and max_strategies > 1:
                selected = [prioritized[0]["id"]]
                # 剩余的策略按照其他标准选择
                remaining = [s for s in strategies_by_score if s["id"] != prioritized[0]["id"]]
                max_strategies -= 1
            else:
                selected = []
                remaining = strategies_by_score
        else:
            selected = []
            remaining = strategies_by_score
        
        # 计算策略间相关性矩阵
        correlations = {}
        for i, s1 in enumerate(remaining):
            for j, s2 in enumerate(remaining):
                if i < j:
                    correlations[(s1["id"], s2["id"])] = self.get_correlation(s1["id"], s2["id"])
        
        # 贪婪选择策略组合
        while len(selected) < max_strategies and remaining:
            best_addition = None
            best_score = -float('inf')
            
            for candidate in remaining:
                # 计算候选策略的得分
                base_score = candidate.get("score", 50)
                
                # 与已选策略的平均相关性
                avg_correlation = 0
                if selected:
                    corrs = []
                    for selected_id in selected:
                        key = (candidate["id"], selected_id) if candidate["id"] < selected_id else (selected_id, candidate["id"])
                        corrs.append(abs(correlations.get(key, 0.5)))
                    avg_correlation = sum(corrs) / len(corrs) if corrs else 0
                
                # 多样性奖励
                diversity_score = (1 - avg_correlation) * 100 * self.config["diversity_weight"]
                
                # 市场适应性奖励
                market_bonus = 10 if candidate.get("priority_boost", False) else 0
                
                # 总分
                total_score = base_score + diversity_score + market_bonus
                
                if total_score > best_score:
                    best_score = total_score
                    best_addition = candidate
            
            if best_addition:
                selected.append(best_addition["id"])
                remaining.remove(best_addition)
            else:
                break
        
        logger.info(f"最优策略组合选择完成: {selected}")
        return selected
    
    def get_allocation_history(self, days: int = 7) -> List[Dict]:
        """获取历史分配记录"""
        if not self.allocation_history:
            return []
        
        # 计算截止日期
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()
        
        # 过滤记录
        recent_history = [
            record for record in self.allocation_history
            if record["timestamp"] > cutoff_str
        ]
        
        return recent_history
    
    def get_portfolio_metrics(self, allocations: Dict[str, float] = None) -> Dict:
        """计算组合策略的性能指标"""
        # 如果没有提供分配，使用最近的分配
        if allocations is None:
            if not self.last_allocation:
                return {
                    "expected_return": 0.0,
                    "expected_risk": 0.05,
                    "sharpe_ratio": 0.0,
                    "win_rate": 0.5,
                    "correlation": 0.5,
                    "diversification": 0.5
                }
            allocations = self.last_allocation.get("normalized", {})
        
        # 如果没有分配，返回默认指标
        if not allocations:
            return {
                "expected_return": 0.0,
                "expected_risk": 0.05,
                "sharpe_ratio": 0.0,
                "win_rate": 0.5,
                "correlation": 0.5,
                "diversification": 0.5
            }
        
        # 收集各策略指标
        strategy_metrics = {}
        for strategy_id in allocations:
            strategy_metrics[strategy_id] = self.get_strategy_metrics(strategy_id)
        
        # 计算加权收益
        weighted_return = 0.0
        weighted_sharpe = 0.0
        weighted_win_rate = 0.0
        
        for strategy_id, allocation in allocations.items():
            metrics = strategy_metrics[strategy_id]
            weighted_return += metrics.get("total_pnl", 0) * allocation
            weighted_sharpe += metrics.get("sharpe_ratio", 0) * allocation
            weighted_win_rate += metrics.get("win_rate", 0.5) * allocation
        
        # 计算平均相关性
        avg_correlation = 0.0
        correlation_count = 0
        
        strategies = list(allocations.keys())
        for i in range(len(strategies)):
            for j in range(i+1, len(strategies)):
                correlation = abs(self.get_correlation(strategies[i], strategies[j]))
                avg_correlation += correlation
                correlation_count += 1
        
        if correlation_count > 0:
            avg_correlation /= correlation_count
        else:
            avg_correlation = 0.5  # 默认值
        
        # 计算分散度指标 (低相关性 = 高分散度)
        diversification = 1.0 - avg_correlation
        
        # 计算组合波动性 (简化模型，假设策略间有一定相关性)
        portfolio_risk = 0.0
        for strategy_id, allocation in allocations.items():
            metrics = strategy_metrics[strategy_id]
            strategy_risk = metrics.get("max_drawdown", 0.05)
            portfolio_risk += (strategy_risk * allocation) ** 2
        
        # 考虑相关性影响
        portfolio_risk = math.sqrt(portfolio_risk) * (0.5 + 0.5 * avg_correlation)
        
        # 组合指标
        return {
            "expected_return": weighted_return,
            "expected_risk": portfolio_risk,
            "sharpe_ratio": weighted_sharpe,
            "win_rate": weighted_win_rate,
            "correlation": avg_correlation,
            "diversification": diversification
        }


# 单例实例
_allocator_instance = None

def get_resource_allocator():
    """获取策略资源分配器实例"""
    global _allocator_instance
    if _allocator_instance is None:
        _allocator_instance = StrategyResourceAllocator()
    return _allocator_instance


if __name__ == "__main__":
    # 测试代码
    allocator = StrategyResourceAllocator()
    
    # 测试策略性能数据更新
    try:
        allocator.update_strategy_performances_from_db()
        print("策略性能数据更新完成")
    except Exception as e:
        print(f"更新性能数据失败: {e}")
    
    # 测试资金分配
    test_strategies = ["momentum_1", "mean_reversion_1", "breakout_1", "grid_trading_1", "trend_following_1"]
    
    try:
        result = allocator.optimize_allocations(test_strategies, 10000.0)
        
        print("\n资金分配结果:")
        for strategy, amount in result["allocations"].items():
            print(f"{strategy}: {amount:.2f} USDT ({result['normalized'][strategy]:.2%})")
        
        print(f"\n保留资金: {result['reserve']:.2f} USDT")
        
        # 计算组合指标
        metrics = allocator.get_portfolio_metrics(result["normalized"])
        print("\n组合指标:")
        print(f"期望收益: {metrics['expected_return']:.2%}")
        print(f"预期风险: {metrics['expected_risk']:.2%}")
        print(f"夏普比率: {metrics['sharpe_ratio']:.2f}")
        print(f"胜率: {metrics['win_rate']:.2%}")
        print(f"平均相关性: {metrics['correlation']:.2f}")
        print(f"分散度: {metrics['diversification']:.2f}")
        
        # 保存状态
        allocator.save_state()
        
    except Exception as e:
        print(f"资金分配测试失败: {e}")
        import traceback
        traceback.print_exc() 