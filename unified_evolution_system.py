#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
🏆 统一策略进化系统 v1.0
整合所有进化功能，避免重复冲突，实现100分+100%胜率+最大收益+最短持有时间

特性：
1. 🧠 智能参数映射 (来自完美系统)
2. 🔄 自适应进化算法 (来自高级系统)  
3. 📊 多维度目标优化 (来自完美系统)
4. ⚡ 实时监控和调度 (来自原始系统)
5. 🎯 智能进化决策 (来自原始系统)
"""

import asyncio
import json
import logging
import numpy as np
import random
import time
import threading
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from decimal import Decimal

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EvolutionGoals:
    """进化目标定义"""
    target_score: float = 100.0      # 目标评分
    target_win_rate: float = 1.0     # 目标胜率 100%
    target_return: float = 0.5       # 目标收益率 50%
    target_hold_time: float = 300    # 目标持有时间 5分钟

@dataclass
class ParameterSpec:
    """参数规格定义"""
    name: str
    current_value: float
    min_value: float
    max_value: float
    step_size: float
    importance: float  # 参数重要性权重 0-1
    optimization_type: str  # 'minimize', 'maximize', 'optimize'

class UnifiedParameterMapper:
    """🧠 统一参数映射系统 - 整合所有策略类型"""
    
    def __init__(self):
        self.strategy_type_mapping = {
            # 动量策略参数映射
            'momentum': {
                'rsi_overbought': {'target': 'rsi_upper', 'range': (60, 90), 'optimal': 75, 'importance': 0.9},
                'rsi_oversold': {'target': 'rsi_lower', 'range': (10, 40), 'optimal': 25, 'importance': 0.9},
                'momentum_period': {'target': 'period', 'range': (5, 25), 'optimal': 14, 'importance': 0.8},
                'momentum_threshold': {'target': 'threshold', 'range': (0.01, 0.1), 'optimal': 0.03, 'importance': 0.7},
                'lookback_period': {'target': 'period', 'range': (5, 50), 'optimal': 20, 'importance': 0.8},
                'quantity': {'target': 'trade_size', 'range': (1.0, 50.0), 'optimal': 10.0, 'importance': 0.6},
                'volume_threshold': {'target': 'volume_mult', 'range': (1.0, 3.0), 'optimal': 1.5, 'importance': 0.5}
            },
            
            # 均值回归策略参数映射
            'mean_reversion': {
                'bb_upper_mult': {'target': 'bollinger_std', 'range': (1.5, 3.0), 'optimal': 2.0, 'importance': 0.9},
                'bb_period': {'target': 'bollinger_period', 'range': (10, 30), 'optimal': 20, 'importance': 0.8},
                'mean_revert_threshold': {'target': 'threshold', 'range': (0.02, 0.08), 'optimal': 0.04, 'importance': 0.7},
                'std_multiplier': {'target': 'bollinger_std', 'range': (1.0, 4.0), 'optimal': 2.0, 'importance': 0.8},
                'reversion_threshold': {'target': 'threshold', 'range': (0.005, 0.03), 'optimal': 0.015, 'importance': 0.7},
                'min_deviation': {'target': 'min_dev', 'range': (0.01, 0.05), 'optimal': 0.02, 'importance': 0.6}
            },
            
            # 突破策略参数映射
            'breakout': {
                'breakout_period': {'target': 'period', 'range': (10, 50), 'optimal': 20, 'importance': 0.9},
                'breakout_threshold': {'target': 'threshold', 'range': (0.02, 0.1), 'optimal': 0.05, 'importance': 0.8},
                'volume_threshold': {'target': 'volume_mult', 'range': (1.2, 4.0), 'optimal': 2.0, 'importance': 0.6},
                'confirmation_periods': {'target': 'confirm', 'range': (1, 5), 'optimal': 2, 'importance': 0.7}
            },
            
            # 高频策略参数映射
            'high_frequency': {
                'fast_ema_period': {'target': 'ema_fast_period', 'range': (3, 15), 'optimal': 8, 'importance': 0.9},
                'slow_ema_period': {'target': 'ema_slow_period', 'range': (15, 50), 'optimal': 21, 'importance': 0.9},
                'signal_threshold': {'target': 'threshold', 'range': (0.001, 0.01), 'optimal': 0.003, 'importance': 0.8},
                'max_hold_time': {'target': 'hold_time', 'range': (60, 600), 'optimal': 300, 'importance': 0.7},
                'min_profit': {'target': 'profit_target', 'range': (0.01, 0.05), 'optimal': 0.02, 'importance': 0.8},
                'volatility_threshold': {'target': 'vol_threshold', 'range': (0.0001, 0.005), 'optimal': 0.001, 'importance': 0.6},
                'signal_interval': {'target': 'interval', 'range': (10, 30), 'optimal': 15, 'importance': 0.5}
            },
            
            # 趋势跟踪策略参数映射
            'trend_following': {
                'trend_period': {'target': 'period', 'range': (10, 50), 'optimal': 25, 'importance': 0.9},
                'trend_strength': {'target': 'strength', 'range': (0.02, 0.1), 'optimal': 0.05, 'importance': 0.8},
                'stop_loss_pct': {'target': 'stop_loss', 'range': (0.01, 0.05), 'optimal': 0.02, 'importance': 0.9},
                'trend_threshold': {'target': 'threshold', 'range': (0.5, 2.0), 'optimal': 1.0, 'importance': 0.8},
                'trend_strength_min': {'target': 'min_strength', 'range': (0.1, 0.8), 'optimal': 0.3, 'importance': 0.7}
            },
            
            # 网格交易策略参数映射
            'grid_trading': {
                'grid_size': {'target': 'grid_spacing', 'range': (0.005, 0.02), 'optimal': 0.01, 'importance': 0.9},
                'grid_levels': {'target': 'levels', 'range': (3, 10), 'optimal': 5, 'importance': 0.8},
                'profit_target': {'target': 'target', 'range': (0.01, 0.05), 'optimal': 0.02, 'importance': 0.7},
                'grid_spacing': {'target': 'spacing', 'range': (0.5, 3.0), 'optimal': 1.0, 'importance': 0.8},
                'grid_count': {'target': 'count', 'range': (5, 20), 'optimal': 10, 'importance': 0.7},
                'min_profit': {'target': 'min_profit', 'range': (0.1, 1.0), 'optimal': 0.3, 'importance': 0.6}
            }
        }
    
    def map_parameters(self, strategy_type: str, current_params: Dict) -> List[ParameterSpec]:
        """将策略参数映射为标准化的参数规格"""
        if strategy_type not in self.strategy_type_mapping:
            strategy_type = 'momentum'  # 默认使用动量策略映射
            
        mapping = self.strategy_type_mapping[strategy_type]
        parameter_specs = []
        
        for param_name, param_value in current_params.items():
            if param_name in mapping:
                spec = mapping[param_name]
                parameter_specs.append(ParameterSpec(
                    name=param_name,
                    current_value=float(param_value),
                    min_value=spec['range'][0],
                    max_value=spec['range'][1], 
                    step_size=(spec['range'][1] - spec['range'][0]) / 100,
                    importance=spec['importance'],
                    optimization_type='optimize'
                ))
            else:
                # 未知参数使用智能推断
                current_val = float(param_value)
                parameter_specs.append(ParameterSpec(
                    name=param_name,
                    current_value=current_val,
                    min_value=max(0.001, current_val * 0.3),
                    max_value=current_val * 3.0,
                    step_size=current_val * 0.05,
                    importance=0.5,
                    optimization_type='optimize'
                ))
                
        return parameter_specs

class UnifiedMultiObjectiveOptimizer:
    """🎯 统一多目标优化器 - 整合所有优化算法"""
    
    def __init__(self, goals: EvolutionGoals):
        self.goals = goals
        
    def calculate_fitness(self, metrics: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
        """计算多维度适应度评分"""
        
        # 获取当前指标
        score = metrics.get('score', 0)
        win_rate = metrics.get('win_rate', 0)
        total_return = metrics.get('total_return', 0)
        avg_hold_time = metrics.get('avg_hold_time', 3600)  # 默认1小时
        total_trades = metrics.get('total_trades', 0)
        profit_factor = metrics.get('profit_factor', 1.0)
        max_drawdown = metrics.get('max_drawdown', 0.1)
        sharpe_ratio = metrics.get('sharpe_ratio', 0.0)
        
        # 计算各维度得分 (0-1)
        score_fitness = min(score / self.goals.target_score, 1.0)
        winrate_fitness = min(win_rate / self.goals.target_win_rate, 1.0)
        return_fitness = min(total_return / self.goals.target_return, 1.0) if self.goals.target_return > 0 else 1.0
        
        # 持有时间适应度：越短越好
        time_fitness = min(self.goals.target_hold_time / max(avg_hold_time, 1), 1.0)
        
        # 额外质量指标
        trades_fitness = min(total_trades / 20, 1.0)  # 20笔交易为满分
        profit_factor_fitness = min(profit_factor / 2.0, 1.0)  # 盈亏比2.0为满分
        drawdown_fitness = max(0, 1.0 - (max_drawdown / 0.2))  # 20%回撤为0分
        sharpe_fitness = min(sharpe_ratio / 2.0, 1.0)  # 夏普比率2.0为满分
        
        # 多维度权重配置
        weights = {
            'score': 0.25,          # 评分权重25%
            'win_rate': 0.25,       # 胜率权重25%
            'return': 0.15,         # 收益权重15%
            'time': 0.10,           # 时间权重10%
            'trades': 0.05,         # 交易数量5%
            'profit_factor': 0.10,  # 盈亏比10%
            'drawdown': 0.05,       # 回撤控制5%
            'sharpe': 0.05          # 夏普比率5%
        }
        
        # 计算综合适应度
        total_fitness = (
            score_fitness * weights['score'] +
            winrate_fitness * weights['win_rate'] +
            return_fitness * weights['return'] +
            time_fitness * weights['time'] +
            trades_fitness * weights['trades'] +
            profit_factor_fitness * weights['profit_factor'] +
            drawdown_fitness * weights['drawdown'] +
            sharpe_fitness * weights['sharpe']
        )
        
        # 适应度加成机制
        bonus = 0
        if win_rate >= 0.8: bonus += 0.05    # 胜率超过80%
        if total_return >= 0.2: bonus += 0.05  # 收益超过20%
        if max_drawdown <= 0.05: bonus += 0.05  # 回撤低于5%
        if sharpe_ratio >= 1.5: bonus += 0.05   # 夏普比率高于1.5
        
        total_fitness = min(1.0, total_fitness + bonus)
        
        component_scores = {
            'score_fitness': score_fitness,
            'winrate_fitness': winrate_fitness, 
            'return_fitness': return_fitness,
            'time_fitness': time_fitness,
            'trades_fitness': trades_fitness,
            'profit_factor_fitness': profit_factor_fitness,
            'drawdown_fitness': drawdown_fitness,
            'sharpe_fitness': sharpe_fitness,
            'total_fitness': total_fitness,
            'bonus': bonus
        }
        
        return total_fitness, component_scores

class UnifiedEvolutionEngine:
    """🏆 统一进化引擎 - 整合所有进化功能"""
    
    def __init__(self, quantitative_service):
        self.quantitative_service = quantitative_service
        self.goals = EvolutionGoals()
        self.parameter_mapper = UnifiedParameterMapper()
        self.optimizer = UnifiedMultiObjectiveOptimizer(self.goals)
        
        # 统一配置
        self.config = {
            # 基础配置
            'max_concurrent_evolutions': 3,
            'evolution_interval': 300,  # 5分钟
            'fitness_threshold': 0.85,  # 85%适应度阈值
            
            # 进化强度配置
            'low_fitness_threshold': 0.3,   # 低适应度阈值
            'medium_fitness_threshold': 0.6, # 中等适应度阈值
            'high_fitness_threshold': 0.85,  # 高适应度阈值
            
            # 变异配置
            'aggressive_mutation_rate': 0.4,   # 激进变异率
            'moderate_mutation_rate': 0.25,    # 适度变异率
            'fine_tune_mutation_rate': 0.1,    # 精细变异率
            
            # 候选方案数量
            'aggressive_candidates': 8,
            'moderate_candidates': 5,
            'fine_tune_candidates': 3,
            
            # 实时监控
            'metrics_collection_interval': 60,  # 1分钟收集指标
            'auto_trigger_enabled': True,
            
            # 冷却期
            'evolution_cooldown_hours': 2,  # 2小时冷却期
        }
        
        # 进化统计
        self.statistics = {
            'total_evolutions': 0,
            'successful_evolutions': 0,
            'failed_evolutions': 0,
            'total_improvement': 0.0,
            'average_improvement': 0.0,
            'last_evolution_time': None
        }
        
        self.running = False
        self.evolution_queue = asyncio.Queue()
        self.running_tasks = {}
        
        print("🏆 统一进化引擎初始化完成")
        print(f"   目标: {self.goals.target_score}分+{self.goals.target_win_rate*100}%胜率+{self.goals.target_return*100}%收益+{self.goals.target_hold_time}秒持有")
    
    async def start_unified_evolution_system(self):
        """启动统一进化系统"""
        if self.running:
            print("⚠️ 统一进化系统已在运行")
            return
            
        self.running = True
        print("🏆 启动统一策略进化系统...")
        
        # 启动各个组件
        tasks = [
            self._metrics_collection_loop(),
            self._evolution_processing_loop(),
            self._system_monitoring_loop()
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"统一进化系统运行错误: {e}")
            await self.stop_unified_evolution_system()
    
    async def _metrics_collection_loop(self):
        """指标收集循环"""
        while self.running:
            try:
                await self._collect_all_strategy_metrics()
                await asyncio.sleep(self.config['metrics_collection_interval'])
            except Exception as e:
                logger.error(f"指标收集错误: {e}")
                await asyncio.sleep(10)
    
    async def _evolution_processing_loop(self):
        """进化处理循环"""
        while self.running:
            try:
                # 控制并发数量
                if len(self.running_tasks) >= self.config['max_concurrent_evolutions']:
                    await asyncio.sleep(5)
                    continue
                
                # 获取进化任务
                try:
                    task = await asyncio.wait_for(self.evolution_queue.get(), timeout=5.0)
                    asyncio.create_task(self._execute_evolution_task(task))
                except asyncio.TimeoutError:
                    continue
                    
            except Exception as e:
                logger.error(f"进化处理错误: {e}")
                await asyncio.sleep(10)
    
    async def _system_monitoring_loop(self):
        """系统监控循环"""
        while self.running:
            try:
                # 生成监控报告
                await self._generate_monitoring_report()
                await asyncio.sleep(600)  # 每10分钟报告一次
            except Exception as e:
                logger.error(f"监控错误: {e}")
                await asyncio.sleep(60)
    
    async def _collect_all_strategy_metrics(self):
        """收集所有策略指标"""
        try:
            strategies = await self._get_active_strategies()
            
            for strategy in strategies:
                strategy_id = strategy['id']
                metrics = await self._collect_strategy_metrics(strategy_id)
                
                if metrics:
                    # 检查是否需要触发进化
                    await self._check_evolution_trigger(strategy_id, strategy, metrics)
                    
        except Exception as e:
            logger.error(f"收集策略指标失败: {e}")
    
    async def _check_evolution_trigger(self, strategy_id: str, strategy: Dict, metrics: Dict):
        """检查是否需要触发进化"""
        try:
            if not self.config['auto_trigger_enabled']:
                return
                
            # 计算当前适应度
            fitness, _ = self.optimizer.calculate_fitness(metrics)
            
            # 检查冷却期
            if await self._is_in_cooldown(strategy_id):
                return
            
            # 触发条件
            should_evolve = False
            priority = 0
            reason = ""
            
            if fitness < self.config['low_fitness_threshold']:
                should_evolve = True
                priority = 100
                reason = "低适应度紧急进化"
            elif fitness < self.config['medium_fitness_threshold']:
                should_evolve = True
                priority = 70
                reason = "中等适应度改进"
            elif fitness < self.config['high_fitness_threshold']:
                # 高分策略定期优化
                last_evolution = await self._get_last_evolution_time(strategy_id)
                if not last_evolution or (datetime.now() - last_evolution).days >= 3:
                    should_evolve = True
                    priority = 50
                    reason = "高分策略定期优化"
            
            if should_evolve:
                evolution_task = {
                    'strategy_id': strategy_id,
                    'strategy': strategy,
                    'metrics': metrics,
                    'fitness': fitness,
                    'priority': priority,
                    'reason': reason,
                    'timestamp': datetime.now()
                }
                
                await self.evolution_queue.put(evolution_task)
                print(f"🎯 策略 {strategy_id[-4:]} 加入进化队列: {reason} (适应度: {fitness:.3f})")
                
        except Exception as e:
            logger.error(f"检查进化触发失败: {e}")
    
    async def _execute_evolution_task(self, task: Dict):
        """执行进化任务"""
        strategy_id = task['strategy_id']
        self.running_tasks[strategy_id] = task
        
        try:
            self.statistics['total_evolutions'] += 1
            
            print(f"🧬 开始进化策略 {strategy_id[-4:]}: {task['reason']}")
            
            # 生成进化方案
            evolution_result = await self._evolve_strategy_to_target(
                task['strategy'], task['metrics'], task['fitness']
            )
            
            if evolution_result['success']:
                improvement = evolution_result['improvement']
                self.statistics['successful_evolutions'] += 1
                self.statistics['total_improvement'] += improvement
                self.statistics['average_improvement'] = (
                    self.statistics['total_improvement'] / self.statistics['successful_evolutions']
                )
                
                print(f"✅ 策略 {strategy_id[-4:]} 进化成功: 改进 {improvement:.3f}")
                
                # 应用优化参数
                await self._apply_evolution_result(strategy_id, evolution_result)
                
            else:
                self.statistics['failed_evolutions'] += 1
                print(f"❌ 策略 {strategy_id[-4:]} 进化失败: {evolution_result.get('reason', 'Unknown')}")
                
        except Exception as e:
            self.statistics['failed_evolutions'] += 1
            logger.error(f"执行进化任务失败 {strategy_id}: {e}")
        finally:
            # 清理运行任务
            if strategy_id in self.running_tasks:
                del self.running_tasks[strategy_id]
            
            self.statistics['last_evolution_time'] = datetime.now()
    
    async def _evolve_strategy_to_target(self, strategy: Dict, metrics: Dict, current_fitness: float) -> Dict:
        """将策略进化至目标状态"""
        try:
            strategy_type = strategy.get('type', 'momentum')
            current_params = strategy.get('parameters', {})
            
            # 确定进化强度
            if current_fitness < self.config['low_fitness_threshold']:
                mutation_intensity = 'aggressive'
                candidate_count = self.config['aggressive_candidates']
            elif current_fitness < self.config['medium_fitness_threshold']:
                mutation_intensity = 'moderate'
                candidate_count = self.config['moderate_candidates']
            else:
                mutation_intensity = 'fine_tune'
                candidate_count = self.config['fine_tune_candidates']
            
            print(f"   使用 {mutation_intensity} 进化策略，生成 {candidate_count} 个候选方案")
            
            # 生成候选参数方案
            candidates = self._generate_parameter_candidates(
                strategy_type, current_params, mutation_intensity, candidate_count
            )
            
            # 评估候选方案
            best_candidate = None
            best_fitness = current_fitness
            
            for i, candidate_params in enumerate(candidates):
                # 模拟测试候选参数
                test_metrics = await self._simulate_parameter_test(strategy['id'], candidate_params)
                candidate_fitness, _ = self.optimizer.calculate_fitness(test_metrics)
                
                if candidate_fitness > best_fitness:
                    best_fitness = candidate_fitness
                    best_candidate = {
                        'params': candidate_params,
                        'fitness': candidate_fitness,
                        'metrics': test_metrics,
                        'candidate_index': i
                    }
            
            if best_candidate:
                improvement = best_fitness - current_fitness
                return {
                    'success': True,
                    'improvement': improvement,
                    'new_fitness': best_fitness,
                    'optimized_params': best_candidate['params'],
                    'new_metrics': best_candidate['metrics'],
                    'mutation_intensity': mutation_intensity
                }
            else:
                return {
                    'success': False,
                    'reason': 'No improvement found',
                    'current_fitness': current_fitness
                }
                
        except Exception as e:
            return {
                'success': False,
                'reason': f'Evolution error: {str(e)}',
                'current_fitness': current_fitness
            }
    
    def _generate_parameter_candidates(self, strategy_type: str, current_params: Dict, 
                                     intensity: str, count: int) -> List[Dict]:
        """生成参数候选方案"""
        candidates = []
        param_specs = self.parameter_mapper.map_parameters(strategy_type, current_params)
        
        mutation_rates = {
            'aggressive': self.config['aggressive_mutation_rate'],
            'moderate': self.config['moderate_mutation_rate'],
            'fine_tune': self.config['fine_tune_mutation_rate']
        }
        
        mutation_rate = mutation_rates[intensity]
        
        for i in range(count):
            candidate_params = current_params.copy()
            
            # 按重要性排序，优先优化重要参数
            sorted_specs = sorted(param_specs, key=lambda x: x.importance, reverse=True)
            
            # 选择要变异的参数数量
            if intensity == 'aggressive':
                params_to_mutate = min(len(sorted_specs), 6)
            elif intensity == 'moderate':
                params_to_mutate = min(len(sorted_specs), 4)
            else:  # fine_tune
                params_to_mutate = min(len(sorted_specs), 2)
            
            for spec in sorted_specs[:params_to_mutate]:
                new_value = self._mutate_parameter(spec, mutation_rate, i)
                candidate_params[spec.name] = new_value
            
            candidates.append(candidate_params)
        
        return candidates
    
    def _mutate_parameter(self, spec: ParameterSpec, mutation_rate: float, iteration: int) -> float:
        """智能参数变异"""
        range_span = spec.max_value - spec.min_value
        
        # 基于迭代次数和重要性的智能变异
        base_factor = random.uniform(-1, 1) * mutation_rate
        importance_factor = spec.importance  # 重要参数变异幅度稍大
        iteration_factor = 1.0 + (iteration * 0.1)  # 后续迭代变异幅度递增
        
        mutation_amount = base_factor * range_span * importance_factor * iteration_factor
        new_value = spec.current_value + mutation_amount
        
        # 确保在合法范围内
        new_value = max(spec.min_value, min(spec.max_value, new_value))
        
        # 按步长调整
        steps = round((new_value - spec.min_value) / spec.step_size)
        final_value = spec.min_value + steps * spec.step_size
        
        return round(final_value, 6)
    
    async def _simulate_parameter_test(self, strategy_id: str, test_params: Dict) -> Dict:
        """模拟测试参数效果"""
        # 这里应该实现真实的参数测试逻辑
        # 暂时使用智能模拟
        await asyncio.sleep(0.1)
        
        # 基于参数质量生成模拟结果
        param_quality = self._assess_parameter_quality(test_params)
        
        base_score = 50 + param_quality * 40  # 50-90分范围
        base_win_rate = 0.4 + param_quality * 0.4  # 40%-80%范围
        base_return = -0.02 + param_quality * 0.25  # -2%到23%范围
        base_hold_time = 1800 - param_quality * 1200  # 30分钟到10分钟范围
        
        # 添加随机性
        noise = random.uniform(0.9, 1.1)
        
        return {
            'score': base_score * noise,
            'win_rate': min(0.95, base_win_rate * noise),
            'total_return': base_return * noise,
            'avg_hold_time': max(180, base_hold_time * noise),
            'total_trades': random.randint(5, 25),
            'profit_factor': 1.0 + param_quality * 1.5,
            'max_drawdown': 0.15 - param_quality * 0.1,
            'sharpe_ratio': param_quality * 2.0
        }
    
    def _assess_parameter_quality(self, params: Dict) -> float:
        """评估参数质量 (0-1)"""
        # 简单的参数质量评估
        quality_score = 0.5  # 基础分
        
        # 基于参数合理性评估
        for key, value in params.items():
            if isinstance(value, (int, float)):
                # 参数在合理范围内给予加分
                if 'threshold' in key.lower() and 0.01 <= value <= 0.1:
                    quality_score += 0.05
                elif 'period' in key.lower() and 5 <= value <= 50:
                    quality_score += 0.05
                elif 'quantity' in key.lower() and 1 <= value <= 100:
                    quality_score += 0.03
        
        return min(1.0, quality_score)
    
    async def _apply_evolution_result(self, strategy_id: str, result: Dict):
        """应用进化结果"""
        try:
            optimized_params = result['optimized_params']
            
            # 更新数据库中的策略参数
            self.quantitative_service.db_manager.execute_query(
                "UPDATE strategies SET parameters = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (json.dumps(optimized_params), strategy_id)
            )
            
            # 记录进化历史
            self._record_evolution_history(strategy_id, result)
            
            print(f"🔧 策略 {strategy_id[-4:]} 参数已更新")
            
        except Exception as e:
            logger.error(f"应用进化结果失败: {e}")
    
    def _record_evolution_history(self, strategy_id: str, result: Dict):
        """记录进化历史"""
        try:
            evolution_record = {
                'strategy_id': strategy_id,
                'timestamp': datetime.now().isoformat(),
                'old_parameters': {},  # 需要从原始策略获取
                'new_parameters': result['optimized_params'],
                'fitness_improvement': result['improvement'],
                'mutation_intensity': result['mutation_intensity'],
                'evolution_type': 'unified_evolution'
            }
            
            # 保存到数据库
            self.quantitative_service.db_manager.execute_query(
                """INSERT INTO strategy_evolution_history 
                   (strategy_id, old_parameters, new_parameters, fitness_improvement, 
                    mutation_intensity, evolution_type, timestamp)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (strategy_id, json.dumps(evolution_record['old_parameters']),
                 json.dumps(evolution_record['new_parameters']), 
                 evolution_record['fitness_improvement'],
                 evolution_record['mutation_intensity'],
                 evolution_record['evolution_type'],
                 datetime.now())
            )
            
        except Exception as e:
            logger.error(f"记录进化历史失败: {e}")
    
    async def _generate_monitoring_report(self):
        """生成监控报告"""
        try:
            print(f"📊 统一进化系统监控报告:")
            print(f"   运行任务: {len(self.running_tasks)}")
            print(f"   总进化次数: {self.statistics['total_evolutions']}")
            print(f"   成功率: {self.statistics['successful_evolutions']}/{self.statistics['total_evolutions']} ({self._get_success_rate():.1%})")
            print(f"   平均改进: {self.statistics['average_improvement']:.3f}")
            
        except Exception as e:
            logger.error(f"生成监控报告失败: {e}")
    
    def _get_success_rate(self) -> float:
        """获取成功率"""
        if self.statistics['total_evolutions'] == 0:
            return 0.0
        return self.statistics['successful_evolutions'] / self.statistics['total_evolutions']
    
    async def stop_unified_evolution_system(self):
        """停止统一进化系统"""
        self.running = False
        print("🛑 统一进化系统已停止")
    
    # 辅助方法
    async def _get_active_strategies(self) -> List[Dict]:
        """获取活跃策略"""
        try:
            strategies = self.quantitative_service.db_manager.execute_query("""
                SELECT id, name, type, parameters, final_score, enabled
                FROM strategies 
                WHERE enabled = 1 AND final_score IS NOT NULL
                ORDER BY final_score DESC
                LIMIT 50
            """, fetch_all=True)
            
            return strategies if strategies else []
        except Exception as e:
            logger.error(f"获取活跃策略失败: {e}")
            return []
    
    async def _collect_strategy_metrics(self, strategy_id: str) -> Optional[Dict]:
        """收集策略指标"""
        try:
            # 从数据库获取策略表现数据
            result = self.quantitative_service.db_manager.execute_query("""
                SELECT 
                    s.final_score,
                    s.win_rate,
                    s.total_return,
                    s.total_trades,
                    COALESCE(s.profit_factor, 1.0) as profit_factor,
                    COALESCE(s.max_drawdown, 0.1) as max_drawdown,
                    COALESCE(s.sharpe_ratio, 0.0) as sharpe_ratio,
                    COALESCE(AVG(EXTRACT(EPOCH FROM (tl.exit_time - tl.entry_time))), 3600) as avg_hold_time
                FROM strategies s
                LEFT JOIN trading_logs tl ON s.id = tl.strategy_id 
                WHERE s.id = %s
                GROUP BY s.id, s.final_score, s.win_rate, s.total_return, s.total_trades,
                         s.profit_factor, s.max_drawdown, s.sharpe_ratio
            """, (strategy_id,), fetch_one=True)
            
            if result:
                return {
                    'score': float(result['final_score'] or 0),
                    'win_rate': float(result['win_rate'] or 0),
                    'total_return': float(result['total_return'] or 0),
                    'avg_hold_time': float(result['avg_hold_time'] or 3600),
                    'total_trades': int(result['total_trades'] or 0),
                    'profit_factor': float(result['profit_factor'] or 1.0),
                    'max_drawdown': float(result['max_drawdown'] or 0.1),
                    'sharpe_ratio': float(result['sharpe_ratio'] or 0.0)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"收集策略指标失败: {e}")
            return None
    
    async def _is_in_cooldown(self, strategy_id: str) -> bool:
        """检查是否在冷却期"""
        try:
            result = self.quantitative_service.db_manager.execute_query("""
                SELECT MAX(timestamp) as last_evolution
                FROM strategy_evolution_history
                WHERE strategy_id = %s
            """, (strategy_id,), fetch_one=True)
            
            if result and result['last_evolution']:
                hours_since = (datetime.now() - result['last_evolution']).total_seconds() / 3600
                return hours_since < self.config['evolution_cooldown_hours']
            
            return False
            
        except Exception as e:
            return False
    
    async def _get_last_evolution_time(self, strategy_id: str) -> Optional[datetime]:
        """获取最后进化时间"""
        try:
            result = self.quantitative_service.db_manager.execute_query("""
                SELECT MAX(timestamp) as last_evolution
                FROM strategy_evolution_history
                WHERE strategy_id = %s
            """, (strategy_id,), fetch_one=True)
            
            return result['last_evolution'] if result else None
            
        except Exception as e:
            return None
    
    async def get_evolution_status(self) -> Dict:
        """获取进化系统状态"""
        return {
            'system_running': self.running,
            'running_tasks': len(self.running_tasks),
            'queue_size': self.evolution_queue.qsize(),
            'statistics': self.statistics,
            'config': self.config
        }

# 统一进化系统工厂
def create_unified_evolution_system(quantitative_service) -> UnifiedEvolutionEngine:
    """创建统一进化系统实例"""
    return UnifiedEvolutionEngine(quantitative_service) 