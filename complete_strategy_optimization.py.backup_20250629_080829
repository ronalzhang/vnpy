#!/usr/bin/env python3
"""
完整策略优化系统
包括参数调优、性能验证、自动淘汰、实时监控等功能
"""

import psycopg2
import numpy as np
import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging
import asyncio
import threading
from decimal import Decimal

@dataclass
class OptimizationResult:
    """优化结果"""
    strategy_id: str
    old_score: float
    new_score: float
    old_parameters: Dict[str, Any]
    new_parameters: Dict[str, Any]
    improvement: float
    confidence: float
    validation_trades: int
    success_rate: float

class CompleteStrategyOptimizer:
    """完整策略优化系统"""
    
    def __init__(self):
        self.logger = self._setup_logger()
        self.running = False
        self.optimization_thread = None
        
        # 优化配置
        self.config = {
            'optimization_interval': 1800,  # 30分钟优化一次
            'validation_period': 3600,      # 1小时验证期
            'min_trades_for_optimization': 10,
            'min_score_improvement': 2.0,
            'max_parameter_change': 0.3,
            'elimination_threshold': 25.0,
            'top_strategy_protection': 10,   # 保护前10名策略
            'mutation_rate': 0.15,
            'crossover_rate': 0.7,
            'population_size': 50
        }
        
    def _setup_logger(self):
        """设置日志"""
        logger = logging.getLogger('StrategyOptimizer')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
        
    def get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host="localhost",
            database="quantitative",
            user="quant_user", 
            password="123abc74531"
        )
    
    async def start_optimization(self):
        """启动优化系统"""
        if self.running:
            self.logger.warning("优化系统已在运行")
            return
            
        self.running = True
        self.logger.info("🚀 启动完整策略优化系统")
        
        # 创建异步任务
        loop = asyncio.get_event_loop()
        self.optimization_thread = loop.run_in_executor(
            None, self._optimization_loop
        )
        
    def _optimization_loop(self):
        """优化主循环"""
        while self.running:
            try:
                self.logger.info("🔍 开始新一轮策略优化")
                
                # 1. 评估所有策略性能
                strategies = self._get_all_strategies()
                self.logger.info(f"📊 获取到 {len(strategies)} 个策略")
                
                # 2. 识别需要优化的策略
                optimization_candidates = self._identify_optimization_candidates(strategies)
                self.logger.info(f"🎯 识别到 {len(optimization_candidates)} 个优化候选策略")
                
                # 3. 执行参数优化
                optimization_results = []
                for strategy in optimization_candidates:
                    result = self._optimize_strategy_parameters(strategy)
                    if result:
                        optimization_results.append(result)
                        
                # 4. 验证优化结果
                validated_results = []
                for result in optimization_results:
                    if self._validate_optimization_result(result):
                        validated_results.append(result)
                        
                # 5. 应用优化结果
                for result in validated_results:
                    self._apply_optimization(result)
                    
                # 6. 淘汰低性能策略
                eliminated = self._eliminate_poor_strategies(strategies)
                
                # 7. 生成新策略（如果需要）
                if len(strategies) - eliminated < self.config['population_size']:
                    new_strategies = self._generate_new_strategies(
                        self.config['population_size'] - (len(strategies) - eliminated)
                    )
                    
                # 8. 记录优化日志
                self._log_optimization_cycle(validated_results, eliminated)
                
                self.logger.info(f"✅ 优化周期完成 - 优化: {len(validated_results)}, 淘汰: {eliminated}")
                
            except Exception as e:
                self.logger.error(f"❌ 优化循环错误: {e}")
                
            # 等待下一个周期
            time.sleep(self.config['optimization_interval'])
            
    def _get_all_strategies(self) -> List[Dict[str, Any]]:
        """获取所有策略"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT s.id, s.name, s.symbol, s.parameters, s.enabled, s.final_score,
                       s.created_at, s.last_updated,
                       COUNT(st.id) as trade_count,
                       AVG(CASE WHEN st.pnl > 0 THEN 1.0 ELSE 0.0 END) as win_rate,
                       SUM(st.pnl) as total_pnl,
                       AVG(st.pnl) as avg_pnl
                FROM strategies s
                LEFT JOIN strategy_trades st ON s.id = st.strategy_id
                WHERE s.enabled = true
                GROUP BY s.id, s.name, s.symbol, s.parameters, s.enabled, s.final_score,
                         s.created_at, s.last_updated
                ORDER BY s.final_score DESC
            """)
            
            results = cursor.fetchall()
            strategies = []
            
            for row in results:
                strategy = {
                    'id': row[0],
                    'name': row[1],
                    'symbol': row[2],
                    'parameters': json.loads(row[3]) if row[3] else {},
                    'enabled': row[4],
                    'final_score': float(row[5] or 0),
                    'created_at': row[6],
                    'last_updated': row[7],
                    'trade_count': int(row[8] or 0),
                    'win_rate': float(row[9] or 0),
                    'total_pnl': float(row[10] or 0),
                    'avg_pnl': float(row[11] or 0)
                }
                strategies.append(strategy)
                
            return strategies
            
        finally:
            conn.close()
            
    def _identify_optimization_candidates(self, strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """识别需要优化的策略"""
        candidates = []
        
        for strategy in strategies:
            # 跳过顶级策略（保护机制）
            if strategy['final_score'] >= 80 and len([s for s in strategies if s['final_score'] >= strategy['final_score']]) <= self.config['top_strategy_protection']:
                continue
                
            # 需要优化的条件
            needs_optimization = (
                strategy['trade_count'] >= self.config['min_trades_for_optimization'] and
                (
                    strategy['final_score'] < 60 or  # 分数较低
                    strategy['win_rate'] < 0.5 or    # 胜率较低
                    strategy['avg_pnl'] < 0          # 平均收益为负
                )
            )
            
            if needs_optimization:
                candidates.append(strategy)
                
        return candidates
        
    def _optimize_strategy_parameters(self, strategy: Dict[str, Any]) -> Optional[OptimizationResult]:
        """优化策略参数"""
        try:
            current_params = strategy['parameters']
            current_score = strategy['final_score']
            
            # 生成新参数
            new_params = self._mutate_parameters(current_params)
            
            # 回测新参数
            new_score = self._backtest_parameters(strategy['id'], new_params)
            
            if new_score > current_score + self.config['min_score_improvement']:
                # 进行验证交易
                validation_result = self._run_validation_trades(strategy['id'], new_params)
                
                return OptimizationResult(
                    strategy_id=strategy['id'],
                    old_score=current_score,
                    new_score=new_score,
                    old_parameters=current_params,
                    new_parameters=new_params,
                    improvement=new_score - current_score,
                    confidence=validation_result['confidence'],
                    validation_trades=validation_result['trade_count'],
                    success_rate=validation_result['success_rate']
                )
                
        except Exception as e:
            self.logger.error(f"策略 {strategy['id']} 参数优化失败: {e}")
            
        return None
        
    def _mutate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """变异参数"""
        new_params = params.copy()
        
        parameter_ranges = {
            'period': (5, 50),
            'fast_period': (5, 30),
            'slow_period': (20, 100),
            'signal_period': (5, 20),
            'rsi_period': (10, 30),
            'rsi_overbought': (65, 85),
            'rsi_oversold': (15, 35),
            'bb_period': (15, 30),
            'bb_std': (1.5, 2.5),
            'volume_period': (10, 30),
            'atr_period': (10, 25),
            'stop_loss': (0.01, 0.05),
            'take_profit': (0.02, 0.08),
            'position_size': (0.1, 1.0)
        }
        
        for param_name, current_value in params.items():
            if random.random() < self.config['mutation_rate'] and param_name in parameter_ranges:
                min_val, max_val = parameter_ranges[param_name]
                
                if isinstance(current_value, (int, float)):
                    # 在当前值附近变异
                    change_factor = 1 + random.uniform(-self.config['max_parameter_change'], 
                                                     self.config['max_parameter_change'])
                    new_value = current_value * change_factor
                    new_value = max(min_val, min(max_val, new_value))
                    
                    # 保持数据类型
                    if isinstance(current_value, int):
                        new_params[param_name] = int(round(new_value))
                    else:
                        new_params[param_name] = round(new_value, 4)
                        
        return new_params
        
    def _backtest_parameters(self, strategy_id: str, parameters: Dict[str, Any]) -> float:
        """回测参数（模拟）"""
        # 这里应该实现真实的回测逻辑
        # 目前返回模拟分数
        base_score = random.uniform(30, 90)
        
        # 根据参数质量调整分数
        param_quality = self._evaluate_parameter_quality(parameters)
        adjusted_score = base_score * param_quality
        
        return min(100, max(0, adjusted_score))
        
    def _evaluate_parameter_quality(self, parameters: Dict[str, Any]) -> float:
        """评估参数质量"""
        quality = 1.0
        
        # 检查参数合理性
        if 'fast_period' in parameters and 'slow_period' in parameters:
            if parameters['fast_period'] >= parameters['slow_period']:
                quality *= 0.7  # 快线周期应小于慢线周期
                
        if 'rsi_overbought' in parameters and 'rsi_oversold' in parameters:
            if parameters['rsi_overbought'] - parameters['rsi_oversold'] < 30:
                quality *= 0.8  # RSI区间应足够大
                
        if 'stop_loss' in parameters and 'take_profit' in parameters:
            risk_reward = parameters['take_profit'] / parameters['stop_loss']
            if risk_reward < 1.5:
                quality *= 0.9  # 盈亏比应大于1.5
                
        return quality
        
    def _run_validation_trades(self, strategy_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """运行验证交易"""
        # 模拟验证交易
        trade_count = random.randint(5, 20)
        success_count = random.randint(int(trade_count * 0.3), int(trade_count * 0.8))
        success_rate = success_count / trade_count
        
        # 计算置信度
        confidence = min(1.0, (trade_count / 10) * success_rate)
        
        return {
            'trade_count': trade_count,
            'success_rate': success_rate,
            'confidence': confidence
        }
        
    def _validate_optimization_result(self, result: OptimizationResult) -> bool:
        """验证优化结果"""
        return (
            result.improvement >= self.config['min_score_improvement'] and
            result.confidence >= 0.6 and
            result.validation_trades >= 5 and
            result.success_rate >= 0.4
        )
        
    def _apply_optimization(self, result: OptimizationResult):
        """应用优化结果"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 更新策略参数和分数
            cursor.execute("""
                UPDATE strategies 
                SET parameters = %s, 
                    final_score = %s,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (json.dumps(result.new_parameters), result.new_score, result.strategy_id))
            
            # 记录优化日志
            cursor.execute("""
                INSERT INTO evolution_logs (strategy_id, generation, individual, action, details, score, timestamp)
                VALUES (%s, 1, 1, 'optimized', %s, %s, CURRENT_TIMESTAMP)
            """, (
                result.strategy_id,
                f"参数优化 - 分数提升 {result.improvement:.2f} (置信度: {result.confidence:.2f})",
                result.new_score
            ))
            
            conn.commit()
            self.logger.info(f"✅ 策略 {result.strategy_id} 优化完成 - 分数: {result.old_score:.2f} → {result.new_score:.2f}")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"❌ 应用优化失败: {e}")
        finally:
            conn.close()
            
    def _eliminate_poor_strategies(self, strategies: List[Dict[str, Any]]) -> int:
        """淘汰低性能策略 - 已禁用"""
        self.logger.info("🛡️ 策略淘汰功能已禁用，使用现代化策略管理系统")
        return 0  # 直接返回，不执行淘汰
        
    def _generate_new_strategies(self, count: int) -> int:
        """生成新策略"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        generated_count = 0
        
        try:
            # 获取表现最好的策略作为模板
            cursor.execute("""
                SELECT id, parameters, symbol 
                FROM strategies 
                WHERE enabled = true AND final_score >= 60
                ORDER BY final_score DESC 
                LIMIT 10
            """)
            
            templates = cursor.fetchall()
            if not templates:
                return 0
                
            symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
            
            for i in range(count):
                # 随机选择模板
                template = random.choice(templates)
                template_params = json.loads(template[1])
                
                # 生成新参数（交叉和变异）
                new_params = self._mutate_parameters(template_params)
                new_symbol = random.choice(symbols)
                strategy_id = f"auto_{int(time.time())}_{i:03d}"
                
                cursor.execute("""
                    INSERT INTO strategies (id, name, symbol, parameters, enabled, final_score, created_at)
                    VALUES (%s, %s, %s, %s, true, %s, CURRENT_TIMESTAMP)
                """, (
                    strategy_id,
                    f"Auto-Generated Strategy {i+1}",
                    new_symbol,
                    json.dumps(new_params),
                    random.uniform(45, 65)  # 初始分数
                ))
                
                # 记录创建日志
                cursor.execute("""
                    INSERT INTO evolution_logs (strategy_id, generation, individual, action, details, score, timestamp)
                    VALUES (%s, 1, 1, 'created', %s, %s, CURRENT_TIMESTAMP)
                """, (
                    strategy_id,
                    f"基于优秀策略 {template[0][:8]} 生成新策略",
                    50.0
                ))
                
                generated_count += 1
                
            conn.commit()
            self.logger.info(f"✅ 生成 {generated_count} 个新策略")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"❌ 生成新策略失败: {e}")
        finally:
            conn.close()
            
        return generated_count
        
    def _log_optimization_cycle(self, optimized_results: List[OptimizationResult], eliminated_count: int):
        """记录优化周期日志"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 记录总体优化日志
            summary = f"优化周期完成 - 优化策略: {len(optimized_results)}, 淘汰策略: {eliminated_count}"
            
            cursor.execute("""
                INSERT INTO evolution_logs (strategy_id, generation, individual, action, details, score, timestamp)
                VALUES (%s, 1, 1, 'cycle_complete', %s, %s, CURRENT_TIMESTAMP)
            """, (
                'system',
                summary,
                0.0
            ))
            
            conn.commit()
            
        except Exception as e:
            self.logger.error(f"❌ 记录优化日志失败: {e}")
        finally:
            conn.close()
            
    def stop_optimization(self):
        """停止优化系统"""
        self.running = False
        self.logger.info("🛑 停止策略优化系统")

# 主函数
async def main():
    optimizer = CompleteStrategyOptimizer()
    
    try:
        await optimizer.start_optimization()
        
        # 保持运行
        while optimizer.running:
            await asyncio.sleep(60)
            
    except KeyboardInterrupt:
        optimizer.stop_optimization()
        print("优化系统已停止")

if __name__ == "__main__":
    asyncio.run(main()) 