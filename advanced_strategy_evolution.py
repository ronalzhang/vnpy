#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
🎯 完美全自动策略进化系统 v2.0
目标：100分+100%胜率+最大收益+最短持有时间

核心特性：
1. 多维度目标函数优化
2. 智能参数映射和协同优化  
3. 自适应进化算法
4. 实时反馈和动态调整
5. 策略类型专用优化方案
"""

import json
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
from decimal import Decimal
import logging

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
    
class IntelligentParameterMapper:
    """🧠 智能参数映射系统"""
    
    def __init__(self):
        self.strategy_type_mapping = {
            # 动量策略参数映射
            'momentum': {
                'rsi_overbought': {'target': 'rsi_upper', 'range': (60, 90), 'optimal': 75, 'importance': 0.9},
                'rsi_oversold': {'target': 'rsi_lower', 'range': (10, 40), 'optimal': 25, 'importance': 0.9},
                'momentum_period': {'target': 'period', 'range': (5, 25), 'optimal': 14, 'importance': 0.8},
                'momentum_threshold': {'target': 'threshold', 'range': (0.01, 0.1), 'optimal': 0.03, 'importance': 0.7}
            },
            
            # 均值回归策略参数映射
            'mean_reversion': {
                'bb_upper_mult': {'target': 'bollinger_std', 'range': (1.5, 3.0), 'optimal': 2.0, 'importance': 0.9},
                'bb_period': {'target': 'bollinger_period', 'range': (10, 30), 'optimal': 20, 'importance': 0.8},
                'mean_revert_threshold': {'target': 'threshold', 'range': (0.02, 0.08), 'optimal': 0.04, 'importance': 0.7}
            },
            
            # 突破策略参数映射
            'breakout': {
                'breakout_period': {'target': 'period', 'range': (10, 50), 'optimal': 20, 'importance': 0.9},
                'breakout_threshold': {'target': 'threshold', 'range': (0.02, 0.1), 'optimal': 0.05, 'importance': 0.8},
                'volume_threshold': {'target': 'volume_mult', 'range': (1.2, 3.0), 'optimal': 1.5, 'importance': 0.6}
            },
            
            # 高频策略参数映射
            'high_frequency': {
                'fast_ema_period': {'target': 'ema_fast_period', 'range': (3, 15), 'optimal': 8, 'importance': 0.9},
                'slow_ema_period': {'target': 'ema_slow_period', 'range': (15, 50), 'optimal': 21, 'importance': 0.9},
                'signal_threshold': {'target': 'threshold', 'range': (0.001, 0.01), 'optimal': 0.003, 'importance': 0.8},
                'max_hold_time': {'target': 'hold_time', 'range': (60, 600), 'optimal': 300, 'importance': 0.7}
            },
            
            # 趋势跟踪策略参数映射
            'trend_following': {
                'trend_period': {'target': 'period', 'range': (10, 50), 'optimal': 25, 'importance': 0.9},
                'trend_strength': {'target': 'strength', 'range': (0.02, 0.1), 'optimal': 0.05, 'importance': 0.8},
                'stop_loss_pct': {'target': 'stop_loss', 'range': (0.01, 0.05), 'optimal': 0.02, 'importance': 0.9}
            },
            
            # 网格交易策略参数映射
            'grid_trading': {
                'grid_size': {'target': 'grid_spacing', 'range': (0.005, 0.02), 'optimal': 0.01, 'importance': 0.9},
                'grid_levels': {'target': 'levels', 'range': (3, 10), 'optimal': 5, 'importance': 0.8},
                'profit_target': {'target': 'target', 'range': (0.01, 0.05), 'optimal': 0.02, 'importance': 0.7}
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
                # 未知参数使用默认设置
                current_val = float(param_value)
                parameter_specs.append(ParameterSpec(
                    name=param_name,
                    current_value=current_val,
                    min_value=max(0.001, current_val * 0.5),
                    max_value=current_val * 2.0,
                    step_size=current_val * 0.1,
                    importance=0.5,
                    optimization_type='optimize'
                ))
                
        return parameter_specs

class MultiObjectiveOptimizer:
    """🎯 多目标优化器"""
    
    def __init__(self, goals: EvolutionGoals):
        self.goals = goals
        
    def calculate_fitness(self, metrics: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
        """计算多维度适应度评分"""
        
        # 获取当前指标
        score = metrics.get('score', 0)
        win_rate = metrics.get('win_rate', 0)
        total_return = metrics.get('total_return', 0)
        avg_hold_time = metrics.get('avg_hold_time', 3600)  # 默认1小时
        
        # 计算各维度得分 (0-1)
        score_fitness = min(score / self.goals.target_score, 1.0)
        winrate_fitness = min(win_rate / self.goals.target_win_rate, 1.0)
        return_fitness = min(total_return / self.goals.target_return, 1.0) if self.goals.target_return > 0 else 1.0
        
        # 持有时间适应度：越短越好
        time_fitness = min(self.goals.target_hold_time / max(avg_hold_time, 1), 1.0)
        
        # 多维度权重配置
        weights = {
            'score': 0.3,      # 评分权重30%
            'win_rate': 0.35,  # 胜率权重35% (最重要)
            'return': 0.25,    # 收益权重25%
            'time': 0.1        # 时间权重10%
        }
        
        # 计算综合适应度
        total_fitness = (
            score_fitness * weights['score'] +
            winrate_fitness * weights['win_rate'] +
            return_fitness * weights['return'] +
            time_fitness * weights['time']
        )
        
        # 适应度加成机制
        if win_rate >= 0.8:  # 胜率超过80%给予额外加成
            total_fitness *= 1.1
        if total_return >= 0.1:  # 收益超过10%给予额外加成
            total_fitness *= 1.05
            
        component_scores = {
            'score_fitness': score_fitness,
            'winrate_fitness': winrate_fitness, 
            'return_fitness': return_fitness,
            'time_fitness': time_fitness,
            'total_fitness': total_fitness
        }
        
        return total_fitness, component_scores

class AdaptiveEvolutionEngine:
    """🧬 自适应进化引擎"""
    
    def __init__(self, parameter_mapper: IntelligentParameterMapper, 
                 optimizer: MultiObjectiveOptimizer):
        self.parameter_mapper = parameter_mapper
        self.optimizer = optimizer
        self.evolution_history = []
        
    def generate_parameter_mutations(self, strategy_type: str, current_params: Dict, 
                                   performance_metrics: Dict) -> List[Dict]:
        """生成智能参数突变方案"""
        
        param_specs = self.parameter_mapper.map_parameters(strategy_type, current_params)
        current_fitness, _ = self.optimizer.calculate_fitness(performance_metrics)
        
        mutations = []
        
        # 根据当前适应度决定突变策略
        if current_fitness < 0.3:
            # 低适应度：激进突变
            mutation_intensity = 'aggressive'
            mutation_count = 8
        elif current_fitness < 0.6:
            # 中等适应度：适度突变
            mutation_intensity = 'moderate'
            mutation_count = 5
        else:
            # 高适应度：微调突变
            mutation_intensity = 'fine_tune'
            mutation_count = 3
            
        for i in range(mutation_count):
            mutated_params = current_params.copy()
            
            # 按重要性排序参数，优先优化重要参数
            sorted_specs = sorted(param_specs, key=lambda x: x.importance, reverse=True)
            
            for spec in sorted_specs[:min(4, len(sorted_specs))]:  # 每次最多突变4个参数
                new_value = self._mutate_parameter(spec, mutation_intensity, i)
                mutated_params[spec.name] = new_value
                
            mutations.append({
                'params': mutated_params,
                'mutation_type': mutation_intensity,
                'expected_improvement': self._estimate_improvement(spec, current_fitness)
            })
            
        return mutations
    
    def _mutate_parameter(self, spec: ParameterSpec, intensity: str, iteration: int) -> float:
        """智能参数突变"""
        
        if intensity == 'aggressive':
            # 激进突变：大幅度随机变化
            mutation_factor = np.random.uniform(-0.5, 0.5)
            range_span = spec.max_value - spec.min_value
            new_value = spec.current_value + mutation_factor * range_span * 0.3
            
        elif intensity == 'moderate':
            # 适度突变：中等幅度变化
            mutation_factor = np.random.uniform(-0.3, 0.3)
            range_span = spec.max_value - spec.min_value
            new_value = spec.current_value + mutation_factor * range_span * 0.15
            
        else:  # fine_tune
            # 微调突变：小幅度精细调整
            mutation_factor = np.random.uniform(-0.1, 0.1)
            range_span = spec.max_value - spec.min_value
            new_value = spec.current_value + mutation_factor * range_span * 0.05
            
        # 确保在合法范围内
        new_value = max(spec.min_value, min(spec.max_value, new_value))
        
        # 按步长调整
        steps = round((new_value - spec.min_value) / spec.step_size)
        final_value = spec.min_value + steps * spec.step_size
        
        return round(final_value, 6)
    
    def _estimate_improvement(self, spec: ParameterSpec, current_fitness: float) -> float:
        """估算参数改变的预期改进"""
        # 基于参数重要性和当前适应度估算改进潜力
        base_improvement = spec.importance * (1.0 - current_fitness) * 0.1
        return min(base_improvement, 0.2)  # 最大20%改进

class PerfectStrategyEvolutionManager:
    """🏆 完美策略进化管理器"""
    
    def __init__(self, quantitative_service):
        self.quantitative_service = quantitative_service
        self.goals = EvolutionGoals()
        self.parameter_mapper = IntelligentParameterMapper()
        self.optimizer = MultiObjectiveOptimizer(self.goals)
        self.evolution_engine = AdaptiveEvolutionEngine(self.parameter_mapper, self.optimizer)
        
        # 进化配置
        self.evolution_config = {
            'max_concurrent_tests': 3,  # 最大并发测试数
            'min_test_duration': 300,   # 最小测试时长5分钟
            'convergence_threshold': 0.95,  # 收敛阈值95%
            'elite_preservation_rate': 0.2,  # 精英保留率20%
        }
        
    async def evolve_strategy_to_perfection(self, strategy_id: str) -> Dict:
        """将单个策略进化至完美状态"""
        
        print(f"🎯 开始策略完美化进化: {strategy_id}")
        
        # 获取策略当前状态
        strategy_info = await self._get_strategy_info(strategy_id)
        if not strategy_info:
            return {'success': False, 'error': 'Strategy not found'}
            
        strategy_type = strategy_info.get('type', 'momentum')
        current_params = strategy_info.get('parameters', {})
        
        # 评估当前表现
        current_metrics = await self._evaluate_strategy_performance(strategy_id)
        current_fitness, component_scores = self.optimizer.calculate_fitness(current_metrics)
        
        print(f"📊 当前适应度: {current_fitness:.3f}")
        print(f"   评分: {component_scores['score_fitness']:.3f}")
        print(f"   胜率: {component_scores['winrate_fitness']:.3f}")
        print(f"   收益: {component_scores['return_fitness']:.3f}")
        print(f"   时间: {component_scores['time_fitness']:.3f}")
        
        # 如果已经接近完美，进行微调
        if current_fitness >= self.evolution_config['convergence_threshold']:
            print(f"✨ 策略已接近完美状态，进行精细调优...")
            return await self._fine_tune_perfect_strategy(strategy_id, current_params, current_metrics)
        
        # 生成进化方案
        evolution_candidates = self.evolution_engine.generate_parameter_mutations(
            strategy_type, current_params, current_metrics
        )
        
        # 并行测试候选方案
        test_results = await self._parallel_test_candidates(strategy_id, evolution_candidates)
        
        # 选择最佳方案
        best_candidate = max(test_results, key=lambda x: x['fitness'])
        
        if best_candidate['fitness'] > current_fitness:
            # 应用最佳参数
            await self._apply_optimized_parameters(strategy_id, best_candidate['params'])
            
            improvement = best_candidate['fitness'] - current_fitness
            print(f"🚀 策略进化成功! 适应度提升: {improvement:.3f}")
            
            # 记录进化历史
            self._record_evolution_success(strategy_id, current_params, 
                                         best_candidate['params'], improvement)
            
            return {
                'success': True,
                'improvement': improvement,
                'new_fitness': best_candidate['fitness'],
                'optimized_params': best_candidate['params']
            }
        else:
            print(f"📉 当前进化方案未能改进策略，保持现有参数")
            return {'success': False, 'reason': 'No improvement found'}
    
    async def _parallel_test_candidates(self, strategy_id: str, candidates: List[Dict]) -> List[Dict]:
        """并行测试候选参数方案"""
        
        results = []
        semaphore = asyncio.Semaphore(self.evolution_config['max_concurrent_tests'])
        
        async def test_single_candidate(candidate):
            async with semaphore:
                # 模拟测试候选参数
                test_metrics = await self._simulate_parameter_test(strategy_id, candidate['params'])
                fitness, _ = self.optimizer.calculate_fitness(test_metrics)
                
                return {
                    'params': candidate['params'],
                    'fitness': fitness,
                    'metrics': test_metrics,
                    'mutation_type': candidate['mutation_type']
                }
        
        # 并发执行所有测试
        tasks = [test_single_candidate(candidate) for candidate in candidates]
        results = await asyncio.gather(*tasks)
        
        return results
    
    async def _simulate_parameter_test(self, strategy_id: str, test_params: Dict) -> Dict:
        """模拟测试参数效果"""
        
        # 这里应该实现真实的参数测试逻辑
        # 暂时使用模拟数据
        await asyncio.sleep(0.1)  # 模拟测试时间
        
        # 基于参数质量生成模拟结果
        simulated_score = np.random.uniform(45, 95)
        simulated_win_rate = np.random.uniform(0.4, 0.9)
        simulated_return = np.random.uniform(-0.05, 0.3)
        simulated_hold_time = np.random.uniform(180, 1800)
        
        return {
            'score': simulated_score,
            'win_rate': simulated_win_rate,
            'total_return': simulated_return,
            'avg_hold_time': simulated_hold_time
        }
    
    async def _get_strategy_info(self, strategy_id: str) -> Optional[Dict]:
        """获取策略信息"""
        try:
            # 这里应该从数据库获取真实策略信息
            # 暂时返回模拟数据
            return {
                'id': strategy_id,
                'type': 'momentum',
                'parameters': {
                    'rsi_overbought': 75.0,
                    'rsi_oversold': 25.0,
                    'momentum_period': 14,
                    'momentum_threshold': 0.03
                }
            }
        except Exception as e:
            logger.error(f"获取策略信息失败: {e}")
            return None
    
    async def _evaluate_strategy_performance(self, strategy_id: str) -> Dict:
        """评估策略表现"""
        try:
            # 这里应该获取真实的策略表现数据
            # 暂时返回模拟数据
            return {
                'score': 65.5,
                'win_rate': 0.72,
                'total_return': 0.08,
                'avg_hold_time': 480
            }
        except Exception as e:
            logger.error(f"评估策略表现失败: {e}")
            return {
                'score': 50.0,
                'win_rate': 0.5,
                'total_return': 0.0,
                'avg_hold_time': 3600
            }
    
    async def _apply_optimized_parameters(self, strategy_id: str, optimized_params: Dict):
        """应用优化后的参数"""
        try:
            # 这里应该实现真实的参数应用逻辑
            print(f"🔧 应用优化参数到策略 {strategy_id}: {optimized_params}")
            
            # 更新数据库中的策略参数
            # self.quantitative_service.db_manager.execute_query(
            #     "UPDATE strategies SET parameters = %s WHERE id = %s",
            #     (json.dumps(optimized_params), strategy_id)
            # )
            
        except Exception as e:
            logger.error(f"应用优化参数失败: {e}")
    
    def _record_evolution_success(self, strategy_id: str, old_params: Dict, 
                                new_params: Dict, improvement: float):
        """记录进化成功"""
        evolution_record = {
            'strategy_id': strategy_id,
            'timestamp': datetime.now().isoformat(),
            'old_parameters': old_params,
            'new_parameters': new_params,
            'fitness_improvement': improvement,
            'evolution_type': 'perfect_evolution'
        }
        
        self.evolution_engine.evolution_history.append(evolution_record)
        print(f"📝 进化记录已保存: 适应度提升 {improvement:.3f}")
    
    async def _fine_tune_perfect_strategy(self, strategy_id: str, params: Dict, metrics: Dict) -> Dict:
        """对接近完美的策略进行精细调优"""
        
        print(f"✨ 执行精细调优...")
        
        # 生成微调方案
        fine_tune_candidates = []
        param_specs = self.parameter_mapper.map_parameters('momentum', params)
        
        for spec in param_specs:
            if spec.importance > 0.7:  # 只调优重要参数
                # 微小调整
                for direction in [-1, 1]:
                    adjusted_params = params.copy()
                    adjustment = direction * spec.step_size * 0.1  # 非常小的调整
                    new_value = max(spec.min_value, 
                                  min(spec.max_value, spec.current_value + adjustment))
                    adjusted_params[spec.name] = new_value
                    fine_tune_candidates.append({'params': adjusted_params})
        
        if not fine_tune_candidates:
            return {'success': False, 'reason': 'No fine-tune candidates'}
        
        # 测试微调方案
        test_results = await self._parallel_test_candidates(strategy_id, fine_tune_candidates)
        current_fitness, _ = self.optimizer.calculate_fitness(metrics)
        
        best_candidate = max(test_results, key=lambda x: x['fitness'])
        
        if best_candidate['fitness'] > current_fitness:
            await self._apply_optimized_parameters(strategy_id, best_candidate['params'])
            improvement = best_candidate['fitness'] - current_fitness
            print(f"🎯 精细调优成功! 微提升: {improvement:.4f}")
            
            return {
                'success': True,
                'improvement': improvement,
                'new_fitness': best_candidate['fitness']
            }
        else:
            print(f"💎 策略已达到当前最优状态")
            return {'success': False, 'reason': 'Already optimal'}

    async def evolve_all_strategies_to_perfection(self) -> Dict:
        """进化所有策略至完美状态"""
        
        print(f"🚀 开始全策略完美化进化...")
        
        # 获取所有策略
        all_strategies = await self._get_all_strategies()
        
        results = {
            'total_strategies': len(all_strategies),
            'successful_evolutions': 0,
            'failed_evolutions': 0,
            'total_improvement': 0.0,
            'evolution_details': []
        }
        
        for strategy in all_strategies:
            try:
                evolution_result = await self.evolve_strategy_to_perfection(strategy['id'])
                
                if evolution_result['success']:
                    results['successful_evolutions'] += 1
                    results['total_improvement'] += evolution_result.get('improvement', 0)
                else:
                    results['failed_evolutions'] += 1
                    
                results['evolution_details'].append({
                    'strategy_id': strategy['id'],
                    'result': evolution_result
                })
                
            except Exception as e:
                logger.error(f"策略 {strategy['id']} 进化失败: {e}")
                results['failed_evolutions'] += 1
                
        print(f"✅ 全策略进化完成!")
        print(f"   成功: {results['successful_evolutions']}")
        print(f"   失败: {results['failed_evolutions']}")
        print(f"   总改进: {results['total_improvement']:.3f}")
        
        return results
    
    async def _get_all_strategies(self) -> List[Dict]:
        """获取所有策略"""
        # 这里应该从数据库获取所有策略
        # 暂时返回模拟数据
        return [
            {'id': 'STRAT_MOMENTUM_001', 'type': 'momentum'},
            {'id': 'STRAT_MEAN_REV_002', 'type': 'mean_reversion'},
            {'id': 'STRAT_BREAKOUT_003', 'type': 'breakout'},
        ]

# 使用示例
async def main():
    """演示完美策略进化系统"""
    
    # 初始化系统
    evolution_manager = PerfectStrategyEvolutionManager(None)
    
    # 进化单个策略
    result = await evolution_manager.evolve_strategy_to_perfection('STRAT_MOMENTUM_001')
    print(f"单策略进化结果: {result}")
    
    # 进化所有策略
    all_results = await evolution_manager.evolve_all_strategies_to_perfection()
    print(f"全策略进化结果: {all_results}")

if __name__ == "__main__":
    asyncio.run(main()) 