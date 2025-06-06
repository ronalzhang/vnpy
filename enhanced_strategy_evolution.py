#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
增强策略进化系统
支持透明的进化过程记录和自动化策略优化
"""

import time
import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from enhanced_logging_system import get_enhanced_logger, log_evolution, log_system
import numpy as np

class EvolutionPhase(Enum):
    """进化阶段"""
    INITIALIZATION = "初始化"
    MUTATION = "突变"
    CROSSOVER = "交叉"
    SELECTION = "选择"
    OPTIMIZATION = "优化"
    VALIDATION = "验证"
    DEPLOYMENT = "部署"

@dataclass
class StrategyGene:
    """策略基因"""
    parameter_name: str
    value: float
    min_value: float
    max_value: float
    mutation_rate: float = 0.1

@dataclass
class StrategyDNA:
    """策略DNA"""
    strategy_id: str
    generation: int
    genes: Dict[str, StrategyGene]
    fitness_score: float = 0.0
    parent_ids: List[str] = None
    creation_time: datetime = None

@dataclass
class EvolutionRecord:
    """进化记录"""
    generation: int
    timestamp: datetime
    phase: EvolutionPhase
    strategy_id: str
    action: str
    details: Dict
    result: str

class EnhancedStrategyEvolution:
    """增强策略进化系统"""
    
    def __init__(self, quantitative_service):
        self.service = quantitative_service
        self.logger = get_enhanced_logger()
        self.current_generation = 0
        self.population_size = 20
        self.elite_ratio = 0.2
        self.mutation_rate = 0.15
        self.crossover_rate = 0.6
        self.evolution_cycles = 0  # 进化周期计数
        
        # 进化历史记录
        self.evolution_history: List[EvolutionRecord] = []
        self.strategy_dna_pool: Dict[str, StrategyDNA] = {}
        self.fitness_trends: Dict[str, List[float]] = {}
        
        # 进化配置
        self.evolution_config = {
            'min_fitness_improvement': 0.05,  # 最小适应性改进
            'stagnation_generations': 5,      # 停滞世代数
            'max_generations': 100,           # 最大世代数
            'elite_preservation': True,       # 精英保护
            'adaptive_mutation': True,        # 自适应突变
            'diversity_maintenance': True     # 多样性维护
        }
        
        log_system("INFO", "增强策略进化系统初始化完成")
        self._record_evolution("SYSTEM_INIT", "系统初始化", "初始化", {"population_size": self.population_size})
    
    def start_evolution_cycle(self) -> Dict:
        """启动进化周期"""
        try:
            self.current_generation += 1
            self.evolution_cycles += 1  # 增加进化周期计数
            
            log_evolution(
                strategy_id="EVOLUTION_SYSTEM",
                action_type="START_GENERATION",
                reason=f"开始第 {self.current_generation} 代进化 (第 {self.evolution_cycles} 轮)",
                generation=self.current_generation
            )
            
            # 1. 评估当前种群
            population_fitness = self._evaluate_population()
            
            # 2. 选择精英
            elites = self._select_elites(population_fitness)
            
            # 3. 生成新个体
            new_individuals = self._generate_new_generation(elites, population_fitness)
            
            # 4. 突变操作
            mutated_individuals = self._apply_mutations(new_individuals)
            
            # 5. 验证和部署
            deployment_results = self._validate_and_deploy(mutated_individuals)
            
            # 6. 更新种群
            self._update_population(elites + mutated_individuals)
            
            # 7. 生成进化报告
            evolution_report = self._generate_evolution_report(population_fitness, deployment_results)
            
            log_evolution(
                strategy_id="EVOLUTION_SYSTEM",
                action_type="COMPLETE_GENERATION",
                reason=f"完成第 {self.current_generation} 代进化",
                generation=self.current_generation,
                score_after=evolution_report['avg_fitness']
            )
            
            return evolution_report
            
        except Exception as e:
            log_system("ERROR", f"进化周期失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _evaluate_population(self) -> Dict[str, Dict]:
        """评估种群适应性"""
        try:
            log_system("INFO", f"开始评估第 {self.current_generation} 代种群")
            
            strategies_response = self.service.get_strategies()
            if not strategies_response.get('success', False):
                return {}
            
            population_fitness = {}
            
            for strategy in strategies_response['data']:
                strategy_id = strategy['id']
                
                # 计算适应性分数
                fitness_score = self._calculate_fitness(strategy)
                
                # 更新适应性趋势
                if strategy_id not in self.fitness_trends:
                    self.fitness_trends[strategy_id] = []
                self.fitness_trends[strategy_id].append(fitness_score)
                
                # 创建或更新DNA
                if strategy_id not in self.strategy_dna_pool:
                    self.strategy_dna_pool[strategy_id] = self._create_strategy_dna(strategy)
                else:
                    self.strategy_dna_pool[strategy_id].fitness_score = fitness_score
                
                population_fitness[strategy_id] = {
                    'strategy': strategy,
                    'fitness': fitness_score,
                    'trend': self._calculate_fitness_trend(strategy_id),
                    'dna': self.strategy_dna_pool[strategy_id]
                }
                
                log_evolution(
                    strategy_id=strategy_id,
                    action_type="FITNESS_EVALUATION",
                    reason=f"适应性评估完成",
                    score_after=fitness_score,
                    generation=self.current_generation
                )
            
            log_system("INFO", f"种群评估完成，评估了 {len(population_fitness)} 个策略")
            return population_fitness
            
        except Exception as e:
            log_system("ERROR", f"种群评估失败: {e}")
            return {}
    
    def _calculate_fitness(self, strategy: Dict) -> float:
        """计算策略适应性分数"""
        try:
            # 基础指标
            total_return = strategy.get('total_return', 0)
            win_rate = strategy.get('win_rate', 0)
            total_trades = strategy.get('total_trades', 0)
            sharpe_ratio = strategy.get('sharpe_ratio', 0)
            max_drawdown = strategy.get('max_drawdown', 0)
            
            # 权重配置
            weights = {
                'return': 0.3,
                'win_rate': 0.25,
                'sharpe': 0.2,
                'stability': 0.15,
                'activity': 0.1
            }
            
            # 收益率分数 (0-100)
            return_score = min(max(total_return * 100, 0), 100)
            
            # 胜率分数 (0-100)
            win_rate_score = win_rate * 100
            
            # 夏普比率分数 (0-100)
            sharpe_score = min(max(sharpe_ratio * 20, 0), 100)
            
            # 稳定性分数 (基于最大回撤)
            stability_score = max(100 - abs(max_drawdown) * 200, 0)
            
            # 活跃度分数 (基于交易次数)
            activity_score = min(total_trades * 5, 100)
            
            # 综合适应性分数
            fitness = (
                return_score * weights['return'] +
                win_rate_score * weights['win_rate'] +
                sharpe_score * weights['sharpe'] +
                stability_score * weights['stability'] +
                activity_score * weights['activity']
            )
            
            # 奖励持续表现
            strategy_id = strategy['id']
            if strategy_id in self.fitness_trends and len(self.fitness_trends[strategy_id]) > 3:
                recent_trend = np.mean(self.fitness_trends[strategy_id][-3:])
                if recent_trend > fitness:
                    fitness += min((recent_trend - fitness) * 0.1, 10)
            
            return round(fitness, 2)
            
        except Exception as e:
            log_system("ERROR", f"计算适应性失败: {e}")
            return 0.0
    
    def _calculate_fitness_trend(self, strategy_id: str) -> str:
        """计算适应性趋势"""
        if strategy_id not in self.fitness_trends or len(self.fitness_trends[strategy_id]) < 3:
            return "新策略"
        
        recent_scores = self.fitness_trends[strategy_id][-3:]
        if recent_scores[-1] > recent_scores[0]:
            return "上升"
        elif recent_scores[-1] < recent_scores[0]:
            return "下降"
        else:
            return "稳定"
    
    def _create_strategy_dna(self, strategy: Dict) -> StrategyDNA:
        """创建策略DNA"""
        try:
            parameters = strategy.get('parameters', {})
            genes = {}
            
            # 根据策略类型创建基因
            strategy_type = strategy.get('type', 'momentum')
            
            if strategy_type == 'momentum':
                genes = {
                    'rsi_period': StrategyGene('rsi_period', parameters.get('rsi_period', 14), 5, 30, 0.1),
                    'rsi_overbought': StrategyGene('rsi_overbought', parameters.get('rsi_overbought', 70), 60, 90, 0.05),
                    'rsi_oversold': StrategyGene('rsi_oversold', parameters.get('rsi_oversold', 30), 10, 40, 0.05),
                    'volume_threshold': StrategyGene('volume_threshold', parameters.get('volume_threshold', 1.5), 1.0, 3.0, 0.1)
                }
            elif strategy_type == 'mean_reversion':
                genes = {
                    'lookback_period': StrategyGene('lookback_period', parameters.get('lookback_period', 20), 10, 50, 0.1),
                    'std_multiplier': StrategyGene('std_multiplier', parameters.get('std_multiplier', 2.0), 1.0, 4.0, 0.1),
                    'mean_reversion_threshold': StrategyGene('mean_reversion_threshold', parameters.get('mean_reversion_threshold', 0.02), 0.01, 0.1, 0.01)
                }
            elif strategy_type == 'breakout':
                genes = {
                    'breakout_threshold': StrategyGene('breakout_threshold', parameters.get('breakout_threshold', 0.02), 0.01, 0.05, 0.005),
                    'volume_confirmation': StrategyGene('volume_confirmation', parameters.get('volume_confirmation', 1.5), 1.0, 3.0, 0.1),
                    'momentum_period': StrategyGene('momentum_period', parameters.get('momentum_period', 10), 5, 20, 0.1)
                }
            
            return StrategyDNA(
                strategy_id=strategy['id'],
                generation=self.current_generation,
                genes=genes,
                fitness_score=0.0,
                creation_time=datetime.now()
            )
            
        except Exception as e:
            log_system("ERROR", f"创建策略DNA失败: {e}")
            return None
    
    def _select_elites(self, population_fitness: Dict) -> List[Dict]:
        """选择精英个体"""
        try:
            sorted_population = sorted(
                population_fitness.values(),
                key=lambda x: x['fitness'],
                reverse=True
            )
            
            elite_count = max(1, int(len(sorted_population) * self.elite_ratio))
            elites = sorted_population[:elite_count]
            
            for elite in elites:
                log_evolution(
                    strategy_id=elite['strategy']['id'],
                    action_type="ELITE_SELECTION",
                    reason=f"精英选择 (适应性: {elite['fitness']:.1f})",
                    score_after=elite['fitness'],
                    generation=self.current_generation
                )
            
            log_system("INFO", f"选择了 {len(elites)} 个精英策略")
            return elites
            
        except Exception as e:
            log_system("ERROR", f"精英选择失败: {e}")
            return []
    
    def _generate_new_generation(self, elites: List[Dict], population_fitness: Dict) -> List[Dict]:
        """生成新一代个体"""
        try:
            new_individuals = []
            target_count = max(5, self.population_size - len(elites))
            
            for i in range(target_count):
                if random.random() < self.crossover_rate and len(elites) >= 2:
                    # 交叉生成
                    parent1, parent2 = random.sample(elites, 2)
                    offspring = self._crossover_strategies(parent1, parent2)
                    if offspring:
                        new_individuals.append(offspring)
                        
                        log_evolution(
                            strategy_id=offspring['strategy']['id'],
                            action_type="CROSSOVER_CREATION",
                            reason=f"交叉生成 (父代: {parent1['strategy']['id'][:8]}, {parent2['strategy']['id'][:8]})",
                            generation=self.current_generation
                        )
                else:
                    # 随机生成
                    new_individual = self._create_random_strategy()
                    if new_individual:
                        new_individuals.append(new_individual)
                        
                        log_evolution(
                            strategy_id=new_individual['strategy']['id'],
                            action_type="RANDOM_CREATION",
                            reason="随机生成新策略",
                            generation=self.current_generation
                        )
            
            log_system("INFO", f"生成了 {len(new_individuals)} 个新个体")
            return new_individuals
            
        except Exception as e:
            log_system("ERROR", f"生成新一代失败: {e}")
            return []
    
    def _crossover_strategies(self, parent1: Dict, parent2: Dict) -> Optional[Dict]:
        """策略交叉"""
        try:
            # 创建新策略ID
            new_strategy_id = f"cross_{uuid.uuid4().hex[:8]}"
            
            # 获取父代DNA
            dna1 = parent1['dna']
            dna2 = parent2['dna']
            
            if not dna1 or not dna2:
                return None
            
            # 基础策略模板 - 包含进化信息的命名
            strategy_name = f"交叉策略G{self.current_generation}代-C{self.evolution_cycles}轮"
            parent_info = f"({parent1['strategy']['id'][:6]}×{parent2['strategy']['id'][:6]})"
            
            new_strategy = {
                'id': new_strategy_id,
                'name': f"{strategy_name}{parent_info}",
                'type': parent1['strategy']['type'],  # 继承类型
                'symbol': parent1['strategy']['symbol'],
                'enabled': False,
                'parameters': {},
                'evolution_info': {
                    'generation': self.current_generation,
                    'cycle': self.evolution_cycles,
                    'creation_method': 'crossover',
                    'parent_ids': [dna1.strategy_id, dna2.strategy_id],
                    'created_at': datetime.now().isoformat()
                }
            }
            
            # 基因交叉
            new_genes = {}
            for gene_name in dna1.genes.keys():
                if gene_name in dna2.genes:
                    # 随机选择父代基因或取平均值
                    if random.random() < 0.5:
                        new_genes[gene_name] = dna1.genes[gene_name]
                    else:
                        # 取平均值
                        gene1 = dna1.genes[gene_name]
                        gene2 = dna2.genes[gene_name]
                        avg_value = (gene1.value + gene2.value) / 2
                        new_genes[gene_name] = StrategyGene(
                            gene_name, avg_value, gene1.min_value, gene1.max_value, gene1.mutation_rate
                        )
                else:
                    new_genes[gene_name] = dna1.genes[gene_name]
            
            # 更新策略参数
            for gene_name, gene in new_genes.items():
                new_strategy['parameters'][gene_name] = gene.value
            
            # 创建新DNA
            new_dna = StrategyDNA(
                strategy_id=new_strategy_id,
                generation=self.current_generation,
                genes=new_genes,
                parent_ids=[dna1.strategy_id, dna2.strategy_id],
                creation_time=datetime.now()
            )
            
            return {
                'strategy': new_strategy,
                'dna': new_dna,
                'fitness': 0.0,
                'trend': "新策略"
            }
            
        except Exception as e:
            log_system("ERROR", f"策略交叉失败: {e}")
            return None
    
    def _create_random_strategy(self) -> Optional[Dict]:
        """创建随机策略"""
        try:
            new_strategy_id = f"rand_{uuid.uuid4().hex[:8]}"
            
            # 随机选择策略类型
            strategy_types = ['momentum', 'mean_reversion', 'breakout', 'grid_trading']
            strategy_type = random.choice(strategy_types)
            
            # 随机选择交易对
            symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT']
            symbol = random.choice(symbols)
            
            # 创建包含进化信息的策略名称
            type_names = {
                'momentum': '动量策略',
                'mean_reversion': '均值回归',
                'breakout': '突破策略',
                'grid_trading': '网格策略'
            }
            
            strategy_name = f"{type_names.get(strategy_type, strategy_type)}G{self.current_generation}代-R{int(time.time())%10000}"
            
            # 创建基础策略
            new_strategy = {
                'id': new_strategy_id,
                'name': strategy_name,
                'type': strategy_type,
                'symbol': symbol,
                'enabled': False,
                'parameters': {},
                'evolution_info': {
                    'generation': self.current_generation,
                    'cycle': self.evolution_cycles,
                    'creation_method': 'random',
                    'parent_ids': [],
                    'created_at': datetime.now().isoformat()
                }
            }
            
            # 生成随机参数
            if strategy_type == 'momentum':
                new_strategy['parameters'] = {
                    'rsi_period': random.randint(10, 25),
                    'rsi_overbought': random.uniform(65, 85),
                    'rsi_oversold': random.uniform(15, 35),
                    'volume_threshold': random.uniform(1.2, 2.5)
                }
            elif strategy_type == 'mean_reversion':
                new_strategy['parameters'] = {
                    'lookback_period': random.randint(15, 40),
                    'std_multiplier': random.uniform(1.5, 3.5),
                    'mean_reversion_threshold': random.uniform(0.015, 0.08)
                }
            elif strategy_type == 'breakout':
                new_strategy['parameters'] = {
                    'breakout_threshold': random.uniform(0.015, 0.04),
                    'volume_confirmation': random.uniform(1.2, 2.8),
                    'momentum_period': random.randint(6, 18)
                }
            
            # 创建DNA
            dna = self._create_strategy_dna(new_strategy)
            
            return {
                'strategy': new_strategy,
                'dna': dna,
                'fitness': 0.0,
                'trend': "新策略"
            }
            
        except Exception as e:
            log_system("ERROR", f"创建随机策略失败: {e}")
            return None
    
    def _apply_mutations(self, individuals: List[Dict]) -> List[Dict]:
        """应用突变"""
        try:
            mutated_individuals = []
            
            for individual in individuals:
                if random.random() < self.mutation_rate:
                    mutated = self._mutate_strategy(individual)
                    if mutated:
                        mutated_individuals.append(mutated)
                        
                        log_evolution(
                            strategy_id=mutated['strategy']['id'],
                            action_type="MUTATION",
                            reason=f"策略突变 (突变率: {self.mutation_rate:.1%})",
                            generation=self.current_generation
                        )
                else:
                    mutated_individuals.append(individual)
            
            log_system("INFO", f"完成突变操作，突变了 {len([i for i in individuals if random.random() < self.mutation_rate])} 个个体")
            return mutated_individuals
            
        except Exception as e:
            log_system("ERROR", f"突变操作失败: {e}")
            return individuals
    
    def _mutate_strategy(self, individual: Dict) -> Optional[Dict]:
        """突变单个策略"""
        try:
            strategy = individual['strategy'].copy()
            dna = individual['dna']
            
            if not dna:
                return individual
            
            # 更新策略名称以反映突变
            original_name = strategy['name']
            if "突变" not in original_name:
                strategy['name'] = f"{original_name}-M{int(time.time())%1000}"
                
                # 更新进化信息
                if 'evolution_info' not in strategy:
                    strategy['evolution_info'] = {}
                
                strategy['evolution_info'].update({
                    'mutation_generation': self.current_generation,
                    'mutation_time': datetime.now().isoformat(),
                    'has_mutation': True
                })
            
            # 突变基因
            mutated_genes = {}
            mutation_count = 0
            
            for gene_name, gene in dna.genes.items():
                if random.random() < gene.mutation_rate:
                    # 高斯突变
                    mutation_strength = (gene.max_value - gene.min_value) * 0.1
                    new_value = gene.value + random.gauss(0, mutation_strength)
                    new_value = max(gene.min_value, min(gene.max_value, new_value))
                    
                    mutated_genes[gene_name] = StrategyGene(
                        gene_name, new_value, gene.min_value, gene.max_value, gene.mutation_rate
                    )
                    
                    # 更新策略参数
                    strategy['parameters'][gene_name] = new_value
                    mutation_count += 1
                else:
                    mutated_genes[gene_name] = gene
            
            # 记录突变详情
            if mutation_count > 0:
                log_evolution(
                    strategy_id=strategy['id'],
                    action_type="MUTATION_DETAIL",
                    reason=f"突变了 {mutation_count} 个基因",
                    generation=self.current_generation,
                    old_params=individual['strategy']['parameters'],
                    new_params=strategy['parameters']
                )
            
            # 更新DNA
            new_dna = StrategyDNA(
                strategy_id=strategy['id'],
                generation=self.current_generation,
                genes=mutated_genes,
                fitness_score=dna.fitness_score,
                parent_ids=dna.parent_ids,
                creation_time=datetime.now()
            )
            
            return {
                'strategy': strategy,
                'dna': new_dna,
                'fitness': individual['fitness'],
                'trend': individual['trend']
            }
            
        except Exception as e:
            log_system("ERROR", f"策略突变失败: {e}")
            return individual
    
    def _validate_and_deploy(self, individuals: List[Dict]) -> Dict:
        """验证和部署策略"""
        try:
            deployment_results = {
                'successful': 0,
                'failed': 0,
                'errors': []
            }
            
            for individual in individuals:
                try:
                    strategy = individual['strategy']
                    
                    # 创建策略
                    result = self.service.create_strategy(
                        name=strategy['name'],
                        symbol=strategy['symbol'],
                        strategy_type=strategy['type'],
                        parameters=strategy['parameters']
                    )
                    
                    if result.get('success', False):
                        deployment_results['successful'] += 1
                        
                        # 更新策略ID
                        strategy['id'] = result['strategy_id']
                        individual['dna'].strategy_id = result['strategy_id']
                        
                        log_evolution(
                            strategy_id=strategy['id'],
                            action_type="DEPLOYMENT",
                            reason="策略部署成功",
                            generation=self.current_generation
                        )
                    else:
                        deployment_results['failed'] += 1
                        deployment_results['errors'].append(result.get('message', '未知错误'))
                        
                        log_evolution(
                            strategy_id=strategy['id'],
                            action_type="DEPLOYMENT_FAILED",
                            reason=f"策略部署失败: {result.get('message', '未知错误')}",
                            generation=self.current_generation
                        )
                        
                except Exception as e:
                    deployment_results['failed'] += 1
                    deployment_results['errors'].append(str(e))
            
            log_system("INFO", f"部署完成: 成功 {deployment_results['successful']}, 失败 {deployment_results['failed']}")
            return deployment_results
            
        except Exception as e:
            log_system("ERROR", f"验证和部署失败: {e}")
            return {'successful': 0, 'failed': len(individuals), 'errors': [str(e)]}
    
    def _update_population(self, new_population: List[Dict]):
        """更新种群"""
        try:
            # 更新DNA池
            for individual in new_population:
                strategy_id = individual['strategy']['id']
                self.strategy_dna_pool[strategy_id] = individual['dna']
            
            # 清理老旧策略
            if len(self.strategy_dna_pool) > self.population_size * 2:
                self._cleanup_old_strategies()
            
            log_system("INFO", f"种群更新完成，当前种群大小: {len(self.strategy_dna_pool)}")
            
        except Exception as e:
            log_system("ERROR", f"种群更新失败: {e}")
    
    def _cleanup_old_strategies(self):
        """清理老旧策略"""
        try:
            # 按适应性排序，移除表现最差的策略
            sorted_strategies = sorted(
                self.strategy_dna_pool.items(),
                key=lambda x: x[1].fitness_score,
                reverse=True
            )
            
            # 保留前N个策略
            keep_count = self.population_size
            strategies_to_keep = dict(sorted_strategies[:keep_count])
            
            # 移除的策略
            removed_strategies = set(self.strategy_dna_pool.keys()) - set(strategies_to_keep.keys())
            
            for strategy_id in removed_strategies:
                # 停用策略
                try:
                    self.service.stop_strategy(strategy_id)
                except Exception as e:
                    pass
                
                # 从DNA池移除
                del self.strategy_dna_pool[strategy_id]
                
                log_evolution(
                    strategy_id=strategy_id,
                    action_type="ELIMINATION",
                    reason="适应性低，被淘汰",
                    generation=self.current_generation
                )
            
            self.strategy_dna_pool = strategies_to_keep
            log_system("INFO", f"清理了 {len(removed_strategies)} 个老旧策略")
            
        except Exception as e:
            log_system("ERROR", f"清理老旧策略失败: {e}")
    
    def _generate_evolution_report(self, population_fitness: Dict, deployment_results: Dict) -> Dict:
        """生成进化报告"""
        try:
            if not population_fitness:
                return {'success': False, 'message': '没有有效的种群数据'}
            
            fitness_values = [p['fitness'] for p in population_fitness.values()]
            
            report = {
                'success': True,
                'generation': self.current_generation,
                'timestamp': datetime.now().isoformat(),
                'population_size': len(population_fitness),
                'avg_fitness': np.mean(fitness_values),
                'max_fitness': np.max(fitness_values),
                'min_fitness': np.min(fitness_values),
                'fitness_std': np.std(fitness_values),
                'deployment': deployment_results,
                'top_strategies': sorted(
                    population_fitness.values(),
                    key=lambda x: x['fitness'],
                    reverse=True
                )[:5],
                'diversity_index': self._calculate_diversity_index(population_fitness),
                'improvement_trend': self._calculate_improvement_trend()
            }
            
            log_system("INFO", f"第 {self.current_generation} 代进化报告生成完成")
            return report
            
        except Exception as e:
            log_system("ERROR", f"生成进化报告失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _calculate_diversity_index(self, population_fitness: Dict) -> float:
        """计算种群多样性指数"""
        try:
            if len(population_fitness) < 2:
                return 0.0
            
            # 基于策略类型的多样性
            strategy_types = {}
            for p in population_fitness.values():
                # 安全获取策略类型
                strategy = p.get('strategy', {})
                strategy_type = strategy.get('type') or strategy.get('strategy_type', 'momentum')
                strategy_types[strategy_type] = strategy_types.get(strategy_type, 0) + 1
            
            # 计算香农多样性指数
            total = len(population_fitness)
            diversity = 0.0
            for count in strategy_types.values():
                if count > 0:
                    p = count / total
                    diversity -= p * np.log2(p)
            
            return round(diversity, 3)
            
        except Exception as e:
            log_system("ERROR", f"计算多样性指数失败: {e}")
            return 0.0
    
    def _calculate_improvement_trend(self) -> str:
        """计算改进趋势"""
        try:
            if self.current_generation < 3:
                return "数据不足"
            
            # 获取最近几代的平均适应性
            recent_generations = []
            for gen in range(max(1, self.current_generation - 2), self.current_generation + 1):
                gen_fitness = []
                for trends in self.fitness_trends.values():
                    if len(trends) >= gen:
                        gen_fitness.append(trends[gen - 1])
                
                if gen_fitness:
                    recent_generations.append(np.mean(gen_fitness))
            
            if len(recent_generations) >= 2:
                if recent_generations[-1] > recent_generations[0]:
                    return "上升"
                elif recent_generations[-1] < recent_generations[0]:
                    return "下降"
                else:
                    return "稳定"
            
            return "未知"
            
        except Exception as e:
            log_system("ERROR", f"计算改进趋势失败: {e}")
            return "计算失败"
    
    def _record_evolution(self, strategy_id: str, action: str, phase: str, details: Dict):
        """记录进化过程"""
        try:
            record = EvolutionRecord(
                generation=self.current_generation,
                timestamp=datetime.now(),
                phase=EvolutionPhase(phase) if phase in [p.value for p in EvolutionPhase] else EvolutionPhase.OPTIMIZATION,
                strategy_id=strategy_id,
                action=action,
                details=details,
                result="成功"
            )
            
            self.evolution_history.append(record)
            
            # 保持历史记录在合理范围内
            if len(self.evolution_history) > 1000:
                self.evolution_history = self.evolution_history[-500:]
                
        except Exception as e:
            log_system("ERROR", f"记录进化过程失败: {e}")
    
    def get_evolution_status(self) -> Dict:
        """获取进化状态"""
        try:
            return {
                'current_generation': self.current_generation,
                'population_size': len(self.strategy_dna_pool),
                'active_strategies': len([dna for dna in self.strategy_dna_pool.values() if dna.fitness_score > 0]),
                'avg_fitness': np.mean([dna.fitness_score for dna in self.strategy_dna_pool.values()]) if self.strategy_dna_pool else 0,
                'evolution_config': self.evolution_config,
                'recent_activity': len([r for r in self.evolution_history if r.timestamp > datetime.now() - timedelta(hours=1)]),
                'last_evolution': self.evolution_history[-1].timestamp.isoformat() if self.evolution_history else None
            }
            
        except Exception as e:
            log_system("ERROR", f"获取进化状态失败: {e}")
            return {'error': str(e)}
    
    def get_evolution_logs(self, limit: int = 100) -> List[Dict]:
        """获取进化日志"""
        try:
            recent_records = self.evolution_history[-limit:] if self.evolution_history else []
            return [asdict(record) for record in recent_records]
            
        except Exception as e:
            log_system("ERROR", f"获取进化日志失败: {e}")
            return []

# 全局进化引擎实例
_evolution_engine = None

def get_enhanced_evolution_engine(quantitative_service):
    """获取增强进化引擎实例"""
    global _evolution_engine
    if _evolution_engine is None:
        _evolution_engine = EnhancedStrategyEvolution(quantitative_service)
    return _evolution_engine 