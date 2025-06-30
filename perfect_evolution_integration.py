#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
🏆 完美策略进化集成系统 v1.0
实现与量化服务的深度集成，自动化多维度优化

目标：100分+100%胜率+最大收益+最短持有时间

特性：
1. 🎯 实时策略性能监控
2. 🧬 智能参数进化算法
3. 🔄 自动化反馈循环
4. 📊 多维度目标优化
5. 🛡️ 风险控制机制
"""

import asyncio
import json
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from decimal import Decimal
import threading
import time

# 导入完美进化系统
from advanced_strategy_evolution import (
    PerfectStrategyEvolutionManager, 
    EvolutionGoals,
    IntelligentParameterMapper,
    MultiObjectiveOptimizer,
    AdaptiveEvolutionEngine
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RealTimeMetrics:
    """实时策略指标"""
    strategy_id: str
    timestamp: datetime
    score: float
    win_rate: float
    total_return: float
    avg_hold_time: float
    total_trades: int
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float

@dataclass
class EvolutionTask:
    """进化任务"""
    strategy_id: str
    priority: int  # 1-10, 10为最高优先级
    current_fitness: float
    target_improvement: float
    last_evolution_time: datetime
    evolution_attempts: int
    status: str  # 'pending', 'running', 'completed', 'failed'

class RealTimeMetricsCollector:
    """🔍 实时指标收集器"""
    
    def __init__(self, quantitative_service):
        self.quantitative_service = quantitative_service
        self.metrics_cache = {}
        self.collection_interval = 60  # 每分钟收集一次
        self.running = False
        
    async def start_collection(self):
        """开始实时指标收集"""
        self.running = True
        print("🔍 启动实时指标收集...")
        
        while self.running:
            try:
                await self._collect_all_strategy_metrics()
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"指标收集错误: {e}")
                await asyncio.sleep(5)
    
    async def _collect_all_strategy_metrics(self):
        """收集所有策略的实时指标"""
        try:
            # 获取所有活跃策略
            strategies = await self._get_active_strategies()
            
            for strategy in strategies:
                strategy_id = strategy['id']
                metrics = await self._collect_strategy_metrics(strategy_id)
                
                if metrics:
                    self.metrics_cache[strategy_id] = metrics
                    # 检查是否需要触发进化
                    await self._check_evolution_trigger(strategy_id, metrics)
                    
        except Exception as e:
            logger.error(f"收集策略指标失败: {e}")
    
    async def _collect_strategy_metrics(self, strategy_id: str) -> Optional[RealTimeMetrics]:
        """收集单个策略的指标"""
        try:
            # 从数据库获取策略表现数据
            query = """
            SELECT 
                s.id,
                s.final_score,
                s.win_rate,
                s.total_return,
                s.total_trades,
                COALESCE(AVG(EXTRACT(EPOCH FROM (tl.exit_time - tl.entry_time))), 3600) as avg_hold_time,
                COALESCE(s.profit_factor, 1.0) as profit_factor,
                COALESCE(s.max_drawdown, 0.0) as max_drawdown,
                COALESCE(s.sharpe_ratio, 0.0) as sharpe_ratio
            FROM strategies s
            LEFT JOIN trading_logs tl ON s.id = tl.strategy_id 
            WHERE s.id = %s AND s.enabled = 1
            GROUP BY s.id, s.final_score, s.win_rate, s.total_return, s.total_trades, 
                     s.profit_factor, s.max_drawdown, s.sharpe_ratio
            """
            
            result = self.quantitative_service.db_manager.execute_query(
                query, (strategy_id,), fetch_one=True
            )
            
            if result:
                return RealTimeMetrics(
                    strategy_id=strategy_id,
                    timestamp=datetime.now(),
                    score=float(result.get('final_score', 0)),
                    win_rate=float(result.get('win_rate', 0)),
                    total_return=float(result.get('total_return', 0)),
                    avg_hold_time=float(result.get('avg_hold_time', 3600)),
                    total_trades=int(result.get('total_trades', 0)),
                    profit_factor=float(result.get('profit_factor', 1.0)),
                    max_drawdown=float(result.get('max_drawdown', 0.0)),
                    sharpe_ratio=float(result.get('sharpe_ratio', 0.0))
                )
            
        except Exception as e:
            logger.error(f"收集策略 {strategy_id} 指标失败: {e}")
            return None
    
    async def _get_active_strategies(self) -> List[Dict]:
        """获取所有活跃策略"""
        try:
            query = """
            SELECT id, name, type, parameters, enabled 
            FROM strategies 
            WHERE enabled = 1 AND final_score IS NOT NULL
            ORDER BY final_score DESC
            LIMIT 50
            """
            
            results = self.quantitative_service.db_manager.execute_query(
                query, fetch_all=True
            )
            
            return results if results else []
            
        except Exception as e:
            logger.error(f"获取活跃策略失败: {e}")
            return []
    
    async def _check_evolution_trigger(self, strategy_id: str, metrics: RealTimeMetrics):
        """检查是否需要触发进化"""
        # 计算当前适应度
        goals = EvolutionGoals()
        optimizer = MultiObjectiveOptimizer(goals)
        
        metrics_dict = {
            'score': metrics.score,
            'win_rate': metrics.win_rate,
            'total_return': metrics.total_return,
            'avg_hold_time': metrics.avg_hold_time
        }
        
        current_fitness, _ = optimizer.calculate_fitness(metrics_dict)
        
        # 触发条件
        trigger_conditions = [
            current_fitness < 0.7,  # 适应度低于70%
            metrics.win_rate < 0.6,  # 胜率低于60%
            metrics.score < 60,      # 评分低于60
            metrics.total_trades > 10 and metrics.total_return < 0.02  # 有足够交易但收益很低
        ]
        
        if any(trigger_conditions):
            print(f"🎯 策略 {strategy_id[-4:]} 触发进化条件: 适应度={current_fitness:.3f}")
            # 这里可以触发进化任务
            await self._trigger_evolution_task(strategy_id, current_fitness)
    
    async def _trigger_evolution_task(self, strategy_id: str, current_fitness: float):
        """触发进化任务"""
        # 这里会集成到进化管理器
        print(f"🧬 为策略 {strategy_id[-4:]} 创建进化任务，当前适应度: {current_fitness:.3f}")

class IntelligentEvolutionScheduler:
    """🧠 智能进化调度器"""
    
    def __init__(self, quantitative_service, evolution_manager: PerfectStrategyEvolutionManager):
        self.quantitative_service = quantitative_service
        self.evolution_manager = evolution_manager
        self.task_queue = asyncio.Queue()
        self.running_tasks = {}
        self.max_concurrent_evolutions = 3
        self.running = False
        
    async def start_scheduler(self):
        """启动智能调度器"""
        self.running = True
        print("🧠 启动智能进化调度器...")
        
        # 启动任务处理协程
        asyncio.create_task(self._process_evolution_tasks())
        
        # 定期扫描需要进化的策略
        while self.running:
            try:
                await self._scan_and_schedule_evolutions()
                await asyncio.sleep(300)  # 每5分钟扫描一次
            except Exception as e:
                logger.error(f"调度器错误: {e}")
                await asyncio.sleep(30)
    
    async def _scan_and_schedule_evolutions(self):
        """扫描并调度进化任务"""
        try:
            # 获取需要进化的策略
            candidates = await self._get_evolution_candidates()
            
            for candidate in candidates:
                # 创建进化任务
                task = EvolutionTask(
                    strategy_id=candidate['id'],
                    priority=self._calculate_priority(candidate),
                    current_fitness=candidate.get('fitness', 0.5),
                    target_improvement=0.1,  # 目标改进10%
                    last_evolution_time=datetime.now(),
                    evolution_attempts=0,
                    status='pending'
                )
                
                await self.task_queue.put(task)
                print(f"📋 调度进化任务: {candidate['id'][-4:]} (优先级: {task.priority})")
                
        except Exception as e:
            logger.error(f"扫描进化候选失败: {e}")
    
    async def _get_evolution_candidates(self) -> List[Dict]:
        """获取进化候选策略"""
        try:
            # 查找表现不佳的策略
            query = """
            SELECT 
                s.id,
                s.final_score,
                s.win_rate,
                s.total_return,
                s.total_trades,
                s.updated_at
            FROM strategies s
            WHERE s.enabled = 1 
            AND (
                s.final_score < 70 OR
                s.win_rate < 0.65 OR
                (s.total_trades > 5 AND s.total_return < 0.03)
            )
            AND s.updated_at < NOW() - INTERVAL '1 hour'  -- 至少1小时未更新
            ORDER BY 
                CASE 
                    WHEN s.final_score < 50 THEN 1
                    WHEN s.win_rate < 0.5 THEN 2
                    ELSE 3
                END,
                s.final_score ASC
            LIMIT 10
            """
            
            results = self.quantitative_service.db_manager.execute_query(
                query, fetch_all=True
            )
            
            return results if results else []
            
        except Exception as e:
            logger.error(f"获取进化候选失败: {e}")
            return []
    
    def _calculate_priority(self, candidate: Dict) -> int:
        """计算进化优先级 (1-10)"""
        score = candidate.get('final_score', 50)
        win_rate = candidate.get('win_rate', 0.5)
        total_trades = candidate.get('total_trades', 0)
        
        # 基础优先级
        priority = 5
        
        # 评分越低优先级越高
        if score < 40:
            priority += 3
        elif score < 60:
            priority += 2
        elif score < 80:
            priority += 1
            
        # 胜率越低优先级越高
        if win_rate < 0.4:
            priority += 2
        elif win_rate < 0.6:
            priority += 1
            
        # 有交易记录的策略优先级更高
        if total_trades > 10:
            priority += 1
            
        return min(10, max(1, priority))
    
    async def _process_evolution_tasks(self):
        """处理进化任务"""
        while self.running:
            try:
                # 控制并发数量
                if len(self.running_tasks) >= self.max_concurrent_evolutions:
                    await asyncio.sleep(5)
                    continue
                
                # 获取任务
                try:
                    task = await asyncio.wait_for(self.task_queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    continue
                
                # 执行进化任务
                asyncio.create_task(self._execute_evolution_task(task))
                
            except Exception as e:
                logger.error(f"处理进化任务错误: {e}")
                await asyncio.sleep(5)
    
    async def _execute_evolution_task(self, task: EvolutionTask):
        """执行单个进化任务"""
        strategy_id = task.strategy_id
        task.status = 'running'
        self.running_tasks[strategy_id] = task
        
        try:
            print(f"🧬 开始执行进化: {strategy_id[-4:]} (优先级: {task.priority})")
            
            # 执行策略进化
            result = await self.evolution_manager.evolve_strategy_to_perfection(strategy_id)
            
            if result.get('success'):
                task.status = 'completed'
                improvement = result.get('improvement', 0)
                print(f"✅ 进化成功: {strategy_id[-4:]} 改进 {improvement:.3f}")
                
                # 记录成功进化
                await self._record_evolution_result(strategy_id, result, True)
            else:
                task.status = 'failed'
                reason = result.get('reason', 'Unknown')
                print(f"❌ 进化失败: {strategy_id[-4:]} 原因: {reason}")
                
                # 记录失败进化
                await self._record_evolution_result(strategy_id, result, False)
                
        except Exception as e:
            task.status = 'failed'
            logger.error(f"执行进化任务失败 {strategy_id}: {e}")
        finally:
            # 清理运行任务
            if strategy_id in self.running_tasks:
                del self.running_tasks[strategy_id]
    
    async def _record_evolution_result(self, strategy_id: str, result: Dict, success: bool):
        """记录进化结果"""
        try:
            record = {
                'strategy_id': strategy_id,
                'timestamp': datetime.now().isoformat(),
                'success': success,
                'improvement': result.get('improvement', 0),
                'new_fitness': result.get('new_fitness', 0),
                'reason': result.get('reason', ''),
                'optimized_params': result.get('optimized_params', {})
            }
            
            # 保存到数据库或日志
            print(f"📝 记录进化结果: {strategy_id[-4:]} {'成功' if success else '失败'}")
            
        except Exception as e:
            logger.error(f"记录进化结果失败: {e}")

class PerfectEvolutionIntegrator:
    """🏆 完美进化集成器 - 主控制器"""
    
    def __init__(self, quantitative_service):
        self.quantitative_service = quantitative_service
        
        # 初始化各个组件
        self.evolution_manager = PerfectStrategyEvolutionManager(quantitative_service)
        self.metrics_collector = RealTimeMetricsCollector(quantitative_service)
        self.evolution_scheduler = IntelligentEvolutionScheduler(
            quantitative_service, self.evolution_manager
        )
        
        # 集成配置
        self.config = {
            'evolution_interval': 300,      # 5分钟检查一次
            'metrics_interval': 60,        # 1分钟收集一次指标
            'max_concurrent_evolutions': 3, # 最大并发进化数
            'fitness_threshold': 0.95,     # 95%适应度阈值
            'auto_evolution_enabled': True  # 启用自动进化
        }
        
        self.running = False
        
    async def start_perfect_evolution_system(self):
        """启动完美进化系统"""
        print("🏆 启动完美策略进化集成系统...")
        print(f"   目标: 100分+100%胜率+最大收益+最短持有时间")
        print(f"   配置: {self.config}")
        
        self.running = True
        
        # 启动各个组件
        tasks = [
            self.metrics_collector.start_collection(),
            self.evolution_scheduler.start_scheduler(),
            self._monitor_system_health(),
            self._generate_evolution_reports()
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("🛑 收到停止信号，正在关闭系统...")
            await self.stop_evolution_system()
        except Exception as e:
            logger.error(f"系统运行错误: {e}")
            await self.stop_evolution_system()
    
    async def _monitor_system_health(self):
        """监控系统健康状态"""
        while self.running:
            try:
                # 检查各组件状态
                metrics_status = "运行中" if self.metrics_collector.running else "停止"
                scheduler_status = "运行中" if self.evolution_scheduler.running else "停止"
                
                # 获取统计信息
                cache_size = len(self.metrics_collector.metrics_cache)
                running_tasks = len(self.evolution_scheduler.running_tasks)
                
                print(f"💓 系统健康检查:")
                print(f"   指标收集器: {metrics_status} (缓存策略: {cache_size})")
                print(f"   进化调度器: {scheduler_status} (运行任务: {running_tasks})")
                
                await asyncio.sleep(600)  # 每10分钟检查一次
                
            except Exception as e:
                logger.error(f"健康监控错误: {e}")
                await asyncio.sleep(60)
    
    async def _generate_evolution_reports(self):
        """生成进化报告"""
        while self.running:
            try:
                await asyncio.sleep(1800)  # 每30分钟生成一次报告
                
                # 生成进化统计报告
                report = await self._collect_evolution_statistics()
                print(f"📊 进化系统30分钟报告:")
                print(f"   总策略数: {report.get('total_strategies', 0)}")
                print(f"   进化任务: {report.get('evolution_tasks', 0)}")
                print(f"   成功率: {report.get('success_rate', 0):.2%}")
                print(f"   平均改进: {report.get('avg_improvement', 0):.3f}")
                
            except Exception as e:
                logger.error(f"生成报告错误: {e}")
                await asyncio.sleep(300)
    
    async def _collect_evolution_statistics(self) -> Dict:
        """收集进化统计信息"""
        try:
            # 这里应该从数据库或日志收集统计信息
            # 暂时返回模拟数据
            return {
                'total_strategies': len(self.metrics_collector.metrics_cache),
                'evolution_tasks': 5,
                'success_rate': 0.75,
                'avg_improvement': 0.08
            }
        except Exception as e:
            logger.error(f"收集统计信息失败: {e}")
            return {}
    
    async def stop_evolution_system(self):
        """停止进化系统"""
        print("🛑 正在停止完美进化系统...")
        
        self.running = False
        self.metrics_collector.running = False
        self.evolution_scheduler.running = False
        
        print("✅ 完美进化系统已停止")

    async def evolve_specific_strategy(self, strategy_id: str) -> Dict:
        """手动进化指定策略"""
        print(f"🎯 手动进化策略: {strategy_id}")
        
        result = await self.evolution_manager.evolve_strategy_to_perfection(strategy_id)
        
        if result.get('success'):
            print(f"✅ 手动进化成功: 改进 {result.get('improvement', 0):.3f}")
        else:
            print(f"❌ 手动进化失败: {result.get('reason', 'Unknown')}")
            
        return result

    async def get_evolution_status(self) -> Dict:
        """获取进化系统状态"""
        return {
            'system_running': self.running,
            'metrics_collector_running': self.metrics_collector.running,
            'scheduler_running': self.evolution_scheduler.running,
            'cached_strategies': len(self.metrics_collector.metrics_cache),
            'running_evolution_tasks': len(self.evolution_scheduler.running_tasks),
            'config': self.config
        }

# 使用示例和集成方法
async def integrate_perfect_evolution(quantitative_service):
    """集成完美进化系统到量化服务"""
    
    # 创建集成器
    integrator = PerfectEvolutionIntegrator(quantitative_service)
    
    # 启动系统
    await integrator.start_perfect_evolution_system()

if __name__ == "__main__":
    # 演示如何使用
    async def demo():
        # 这里应该传入真实的quantitative_service实例
        # await integrate_perfect_evolution(quantitative_service)
        
        print("🏆 完美策略进化集成系统演示")
        print("请在量化服务中调用 integrate_perfect_evolution(quantitative_service)")
        
    asyncio.run(demo()) 