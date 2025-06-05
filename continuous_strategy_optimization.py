#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持续策略优化系统 - 解决策略只初始化模拟一次的问题
确保策略持续模拟交易优化，直到达到65分门槛才允许真实交易
"""
import time
import logging
import json
import threading
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import sqlite3
import random

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/continuous_optimization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SimulationResult:
    """模拟交易结果"""
    strategy_id: str
    timestamp: datetime
    win_rate: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int
    score: float
    success: bool

@dataclass
class OptimizationStep:
    """优化步骤记录"""
    strategy_id: str
    old_parameters: Dict
    new_parameters: Dict
    old_score: float
    new_score: float
    improvement: float
    timestamp: datetime

class ContinuousSimulationEngine:
    """持续模拟交易引擎 - 核心优化循环"""
    
    def __init__(self, quantitative_service):
        self.service = quantitative_service
        self.db_manager = quantitative_service.db_manager
        self.running = False
        self.simulation_interval = 300  # 5分钟一次模拟
        self.thread = None
        
        # 模拟交易配置
        self.simulation_config = {
            'days_per_simulation': 3,  # 每次模拟3天数据
            'min_trades_required': 5,  # 最少交易次数
            'score_update_weight': 0.3,  # 新结果权重
            'performance_window': 20,  # 性能评估窗口
        }
        
        self._init_simulation_tables()
    
    def _init_simulation_tables(self):
        """初始化模拟交易相关表"""
        try:
            # 模拟历史表
            self.db_manager.execute_query("""
                CREATE TABLE IF NOT EXISTS strategy_simulation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT NOT NULL,
                    simulation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    win_rate REAL,
                    total_return REAL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    total_trades INTEGER,
                    score REAL,
                    parameters TEXT,
                    success BOOLEAN
                )
            """)
            
            # 滚动性能指标表
            self.db_manager.execute_query("""
                CREATE TABLE IF NOT EXISTS strategy_rolling_metrics (
                    strategy_id TEXT PRIMARY KEY,
                    current_score REAL,
                    rolling_win_rate REAL,
                    rolling_return REAL,
                    recent_trend TEXT,
                    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    simulation_count INTEGER DEFAULT 0,
                    consecutive_improvements INTEGER DEFAULT 0,
                    ready_for_trading BOOLEAN DEFAULT FALSE
                )
            """)
            
            logger.info("✅ 模拟交易表初始化完成")
            
        except Exception as e:
            logger.error(f"初始化模拟表失败: {e}")
    
    def start_continuous_simulation(self):
        """开始持续模拟交易循环"""
        if self.running:
            logger.warning("持续模拟已在运行中")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self.thread.start()
        logger.info("🔄 持续模拟交易循环已启动")
    
    def stop_continuous_simulation(self):
        """停止持续模拟"""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("⏹️ 持续模拟交易循环已停止")
    
    def _simulation_loop(self):
        """主模拟循环"""
        logger.info("🚀 开始持续策略优化循环...")
        
        while self.running:
            try:
                # 获取所有策略
                strategies = self._get_active_strategies()
                
                if not strategies:
                    logger.warning("没有活跃策略进行模拟")
                    time.sleep(60)
                    continue
                
                logger.info(f"🔍 开始模拟 {len(strategies)} 个策略...")
                
                # 并行模拟所有策略
                simulation_results = []
                for strategy in strategies:
                    result = self._run_strategy_simulation(strategy)
                    if result:
                        simulation_results.append(result)
                
                # 更新策略评分和状态
                self._update_strategy_metrics(simulation_results)
                
                # 优化低分策略
                self._optimize_underperforming_strategies(simulation_results)
                
                # 更新交易资格
                self._update_trading_eligibility(simulation_results)
                
                logger.info(f"✅ 本轮模拟完成，成功模拟 {len(simulation_results)} 个策略")
                
                # 等待下次模拟
                time.sleep(self.simulation_interval)
                
            except Exception as e:
                logger.error(f"模拟循环出错: {e}")
                time.sleep(30)  # 出错后短暂等待
    
    def _get_active_strategies(self) -> List[Dict]:
        """获取所有活跃策略"""
        try:
            strategies_response = self.service.get_strategies()
            if not strategies_response.get('success', False):
                return []
            
            # 只返回启用的策略
            active_strategies = [
                s for s in strategies_response['data'] 
                if s.get('enabled', False)
            ]
            
            return active_strategies
            
        except Exception as e:
            logger.error(f"获取活跃策略失败: {e}")
            return []
    
    def _run_strategy_simulation(self, strategy: Dict) -> Optional[SimulationResult]:
        """运行单个策略的模拟交易"""
        try:
            strategy_id = strategy['id']
            logger.debug(f"🔬 模拟策略: {strategy.get('name', strategy_id)}")
            
            # 使用现有的模拟器
            simulator = self.service.simulator
            result = simulator.run_strategy_simulation(
                strategy_id, 
                days=self.simulation_config['days_per_simulation']
            )
            
            if not result or not result.get('success', False):
                logger.warning(f"策略 {strategy_id} 模拟失败")
                return None
            
            # 封装结果
            sim_result = SimulationResult(
                strategy_id=strategy_id,
                timestamp=datetime.now(),
                win_rate=result.get('combined_win_rate', 0),
                total_return=result.get('total_return', 0),
                sharpe_ratio=result.get('sharpe_ratio', 0),
                max_drawdown=result.get('max_drawdown', 0),
                total_trades=result.get('total_trades', 0),
                score=result.get('final_score', 0),
                success=True
            )
            
            # 保存到历史
            self._save_simulation_result(sim_result, strategy.get('parameters', {}))
            
            return sim_result
            
        except Exception as e:
            logger.error(f"策略 {strategy.get('id', 'unknown')} 模拟失败: {e}")
            return None
    
    def _save_simulation_result(self, result: SimulationResult, parameters: Dict):
        """保存模拟结果"""
        try:
            self.db_manager.execute_query("""
                INSERT INTO strategy_simulation_history 
                (strategy_id, win_rate, total_return, sharpe_ratio, max_drawdown, 
                 total_trades, score, parameters, success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.strategy_id,
                result.win_rate,
                result.total_return,
                result.sharpe_ratio,
                result.max_drawdown,
                result.total_trades,
                result.score,
                json.dumps(parameters),
                result.success
            ))
            
        except Exception as e:
            logger.error(f"保存模拟结果失败: {e}")
    
    def _update_strategy_metrics(self, results: List[SimulationResult]):
        """更新策略的滚动指标"""
        for result in results:
            try:
                strategy_id = result.strategy_id
                
                # 获取历史指标
                current_metrics = self.db_manager.execute_query("""
                    SELECT current_score, rolling_win_rate, rolling_return, 
                           simulation_count, consecutive_improvements
                    FROM strategy_rolling_metrics WHERE strategy_id = ?
                """, (strategy_id,), fetch_one=True)
                
                if current_metrics:
                    # 更新现有指标
                    old_score = current_metrics[0] or 0
                    old_win_rate = current_metrics[1] or 0
                    old_return = current_metrics[2] or 0
                    sim_count = current_metrics[3] or 0
                    consecutive_improvements = current_metrics[4] or 0
                    
                    # 计算滚动平均
                    weight = self.simulation_config['score_update_weight']
                    new_score = old_score * (1 - weight) + result.score * weight
                    new_win_rate = old_win_rate * (1 - weight) + result.win_rate * weight
                    new_return = old_return * (1 - weight) + result.total_return * weight
                    
                    # 检查是否有改进
                    if result.score > old_score:
                        consecutive_improvements += 1
                    else:
                        consecutive_improvements = 0
                    
                    # 判断趋势
                    if result.score > old_score + 2:
                        trend = "improving"
                    elif result.score < old_score - 2:
                        trend = "declining"
                    else:
                        trend = "stable"
                    
                    # 判断是否准备好进行真实交易
                    ready_for_trading = (
                        new_score >= 65.0 and 
                        new_win_rate >= 0.6 and 
                        consecutive_improvements >= 3
                    )
                    
                    # 更新数据库
                    self.db_manager.execute_query("""
                        UPDATE strategy_rolling_metrics SET
                            current_score = ?, rolling_win_rate = ?, rolling_return = ?,
                            recent_trend = ?, simulation_count = ?, 
                            consecutive_improvements = ?, ready_for_trading = ?
                        WHERE strategy_id = ?
                    """, (
                        new_score, new_win_rate, new_return, trend,
                        sim_count + 1, consecutive_improvements, ready_for_trading,
                        strategy_id
                    ))
                    
                else:
                    # 创建新记录
                    ready_for_trading = result.score >= 65.0 and result.win_rate >= 0.6
                    
                    self.db_manager.execute_query("""
                        INSERT INTO strategy_rolling_metrics 
                        (strategy_id, current_score, rolling_win_rate, rolling_return,
                         recent_trend, simulation_count, consecutive_improvements, ready_for_trading)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        strategy_id, result.score, result.win_rate, result.total_return,
                        "new", 1, 1 if result.score >= 65 else 0, ready_for_trading
                    ))
                
                logger.debug(f"📊 策略 {strategy_id} 指标已更新: 评分 {result.score:.1f}")
                
            except Exception as e:
                logger.error(f"更新策略指标失败 {result.strategy_id}: {e}")


class IntelligentParameterOptimizer:
    """智能参数优化器"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.optimization_history = []
    
    def optimize_strategy_parameters(self, strategy: Dict, recent_results: List[SimulationResult]) -> Dict:
        """基于最近表现优化策略参数"""
        try:
            strategy_id = strategy['id']
            current_params = strategy.get('parameters', {})
            strategy_type = strategy.get('type', 'unknown')
            
            logger.info(f"🔧 优化策略参数: {strategy.get('name', strategy_id)}")
            
            # 分析最近的表现趋势
            performance_analysis = self._analyze_performance_trend(recent_results)
            
            # 根据策略类型和表现调整参数
            optimized_params = self._optimize_by_strategy_type(
                strategy_type, current_params, performance_analysis
            )
            
            # 记录优化历史
            self._record_optimization(strategy_id, current_params, optimized_params)
            
            return optimized_params
            
        except Exception as e:
            logger.error(f"参数优化失败 {strategy.get('id', 'unknown')}: {e}")
            return strategy.get('parameters', {})
    
    def _analyze_performance_trend(self, results: List[SimulationResult]) -> Dict:
        """分析性能趋势"""
        if not results:
            return {'trend': 'unknown', 'volatility': 'high', 'consistency': 'low'}
        
        scores = [r.score for r in results]
        win_rates = [r.win_rate for r in results]
        returns = [r.total_return for r in results]
        
        # 计算趋势
        if len(scores) >= 3:
            recent_avg = np.mean(scores[-3:])
            earlier_avg = np.mean(scores[:-3]) if len(scores) > 3 else scores[0]
            
            if recent_avg > earlier_avg + 2:
                trend = 'improving'
            elif recent_avg < earlier_avg - 2:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'
        
        # 计算波动性
        score_std = np.std(scores) if len(scores) > 1 else 0
        volatility = 'high' if score_std > 10 else 'medium' if score_std > 5 else 'low'
        
        # 计算一致性
        win_rate_consistency = 'high' if np.std(win_rates) < 0.1 else 'medium' if np.std(win_rates) < 0.2 else 'low'
        
        return {
            'trend': trend,
            'volatility': volatility,
            'consistency': win_rate_consistency,
            'avg_score': np.mean(scores),
            'avg_win_rate': np.mean(win_rates),
            'avg_return': np.mean(returns)
        }
    
    def _optimize_by_strategy_type(self, strategy_type: str, current_params: Dict, analysis: Dict) -> Dict:
        """根据策略类型优化参数"""
        optimized = current_params.copy()
        
        try:
            if strategy_type == 'momentum':
                optimized = self._optimize_momentum_strategy(optimized, analysis)
            elif strategy_type == 'mean_reversion':
                optimized = self._optimize_mean_reversion_strategy(optimized, analysis)
            elif strategy_type == 'breakout':
                optimized = self._optimize_breakout_strategy(optimized, analysis)
            elif strategy_type == 'grid_trading':
                optimized = self._optimize_grid_strategy(optimized, analysis)
            elif strategy_type == 'high_frequency':
                optimized = self._optimize_hf_strategy(optimized, analysis)
            else:
                # 通用优化
                optimized = self._optimize_generic_strategy(optimized, analysis)
            
            return optimized
            
        except Exception as e:
            logger.error(f"策略类型 {strategy_type} 优化失败: {e}")
            return current_params
    
    def _optimize_momentum_strategy(self, params: Dict, analysis: Dict) -> Dict:
        """优化动量策略参数"""
        optimized = params.copy()
        
        # 根据表现调整RSI参数
        if analysis['avg_score'] < 50:
            # 表现较差，增加保守性
            optimized['rsi_overbought'] = min(optimized.get('rsi_overbought', 70) + 5, 85)
            optimized['rsi_oversold'] = max(optimized.get('rsi_oversold', 30) - 5, 15)
        elif analysis['trend'] == 'improving':
            # 表现改善，可以稍微激进
            optimized['rsi_overbought'] = max(optimized.get('rsi_overbought', 70) - 2, 65)
            optimized['rsi_oversold'] = min(optimized.get('rsi_oversold', 30) + 2, 35)
        
        # 调整周期参数
        if analysis['volatility'] == 'high':
            optimized['rsi_period'] = min(optimized.get('rsi_period', 14) + 2, 21)
        elif analysis['consistency'] == 'high':
            optimized['rsi_period'] = max(optimized.get('rsi_period', 14) - 1, 10)
        
        return optimized
    
    def _optimize_mean_reversion_strategy(self, params: Dict, analysis: Dict) -> Dict:
        """优化均值回归策略参数"""
        optimized = params.copy()
        
        # 调整布林带参数
        if analysis['avg_score'] < 50:
            # 增加标准差倍数，减少交易频率
            optimized['std_multiplier'] = min(optimized.get('std_multiplier', 2.0) + 0.2, 3.0)
        elif analysis['trend'] == 'improving':
            # 减少标准差倍数，增加交易机会
            optimized['std_multiplier'] = max(optimized.get('std_multiplier', 2.0) - 0.1, 1.5)
        
        # 调整回看周期
        if analysis['volatility'] == 'high':
            optimized['lookback_period'] = min(optimized.get('lookback_period', 20) + 5, 50)
        
        return optimized
    
    def _optimize_breakout_strategy(self, params: Dict, analysis: Dict) -> Dict:
        """优化突破策略参数"""
        optimized = params.copy()
        
        # 调整突破阈值
        if analysis['avg_win_rate'] < 0.5:
            # 胜率较低，提高突破阈值
            optimized['breakout_threshold'] = min(optimized.get('breakout_threshold', 0.02) + 0.005, 0.05)
        elif analysis['trend'] == 'improving':
            # 降低阈值以捕获更多机会
            optimized['breakout_threshold'] = max(optimized.get('breakout_threshold', 0.02) - 0.002, 0.01)
        
        return optimized
    
    def _optimize_grid_strategy(self, params: Dict, analysis: Dict) -> Dict:
        """优化网格策略参数"""
        optimized = params.copy()
        
        # 调整网格间距
        if analysis['avg_return'] < 0:
            # 收益为负，增加网格间距
            optimized['grid_spacing'] = min(optimized.get('grid_spacing', 0.01) + 0.002, 0.02)
        elif analysis['trend'] == 'improving':
            # 减少间距增加交易频率
            optimized['grid_spacing'] = max(optimized.get('grid_spacing', 0.01) - 0.001, 0.005)
        
        return optimized
    
    def _optimize_hf_strategy(self, params: Dict, analysis: Dict) -> Dict:
        """优化高频策略参数"""
        optimized = params.copy()
        
        # 调整最小利润要求
        if analysis['avg_score'] < 50:
            # 提高最小利润要求
            optimized['min_profit'] = min(optimized.get('min_profit', 0.01) + 0.005, 0.03)
        
        return optimized
    
    def _optimize_generic_strategy(self, params: Dict, analysis: Dict) -> Dict:
        """通用策略优化"""
        optimized = params.copy()
        
        # 通用的交易量调整
        if 'quantity' in optimized:
            if analysis['avg_score'] < 50:
                # 表现不佳，减少交易量
                optimized['quantity'] = max(optimized['quantity'] * 0.9, 1.0)
            elif analysis['trend'] == 'improving':
                # 表现改善，可以适当增加
                optimized['quantity'] = min(optimized['quantity'] * 1.1, 50.0)
        
        return optimized
    
    def _record_optimization(self, strategy_id: str, old_params: Dict, new_params: Dict):
        """记录优化历史"""
        try:
            self.db_manager.execute_query("""
                INSERT OR REPLACE INTO strategy_optimization_log
                (strategy_id, optimization_date, old_parameters, new_parameters, optimization_reason)
                VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?)
            """, (
                strategy_id,
                json.dumps(old_params),
                json.dumps(new_params),
                "continuous_optimization"
            ))
        except Exception as e:
            logger.error(f"记录优化历史失败: {e}")


class StrictTradingGatekeeper:
    """严格交易门控 - 确保只有65分以上策略能真实交易"""
    
    def __init__(self, quantitative_service):
        self.service = quantitative_service
        self.db_manager = quantitative_service.db_manager
        self.trading_threshold = 65.0
        self.min_win_rate = 0.60
        self.min_stable_periods = 5
    
    def check_trading_eligibility(self, strategy_id: str) -> Tuple[bool, str]:
        """检查策略是否有资格进行真实交易"""
        try:
            # 获取策略最新指标
            metrics = self.db_manager.execute_query("""
                SELECT current_score, rolling_win_rate, consecutive_improvements,
                       simulation_count, ready_for_trading
                FROM strategy_rolling_metrics WHERE strategy_id = ?
            """, (strategy_id,), fetch_one=True)
            
            if not metrics:
                return False, "策略指标数据不足"
            
            score, win_rate, improvements, sim_count, ready = metrics
            
            # 检查评分门槛
            if score < self.trading_threshold:
                return False, f"评分 {score:.1f} 低于门槛 {self.trading_threshold}"
            
            # 检查胜率
            if win_rate < self.min_win_rate:
                return False, f"胜率 {win_rate:.1%} 低于要求 {self.min_win_rate:.1%}"
            
            # 检查稳定性
            if improvements < 3:
                return False, f"连续改进次数 {improvements} 不足，需要至少3次"
            
            # 检查模拟次数
            if sim_count < self.min_stable_periods:
                return False, f"模拟次数 {sim_count} 不足，需要至少 {self.min_stable_periods} 次"
            
            return True, f"✅ 策略合格：评分 {score:.1f}，胜率 {win_rate:.1%}"
            
        except Exception as e:
            logger.error(f"检查交易资格失败 {strategy_id}: {e}")
            return False, f"检查失败: {e}"
    
    def update_trading_permissions(self):
        """更新所有策略的交易权限"""
        try:
            # 获取所有策略
            strategies_response = self.service.get_strategies()
            if not strategies_response.get('success', False):
                return
            
            qualified_count = 0
            disqualified_count = 0
            
            for strategy in strategies_response['data']:
                strategy_id = strategy['id']
                eligible, reason = self.check_trading_eligibility(strategy_id)
                
                # 更新数据库中的交易状态
                self.db_manager.execute_query("""
                    UPDATE strategies SET real_trading_enabled = ?, 
                                         last_eligibility_check = CURRENT_TIMESTAMP,
                                         eligibility_reason = ?
                    WHERE id = ?
                """, (eligible, reason, strategy_id))
                
                if eligible:
                    qualified_count += 1
                    logger.info(f"✅ 策略 {strategy.get('name', strategy_id)} 获得交易资格")
                else:
                    disqualified_count += 1
                    logger.debug(f"❌ 策略 {strategy.get('name', strategy_id)} 暂停交易: {reason}")
            
            logger.info(f"🎯 交易权限更新完成: {qualified_count} 个合格，{disqualified_count} 个不合格")
            
        except Exception as e:
            logger.error(f"更新交易权限失败: {e}")


class ContinuousOptimizationManager:
    """持续优化管理器 - 主控制器"""
    
    def __init__(self, quantitative_service):
        self.service = quantitative_service
        self.simulation_engine = ContinuousSimulationEngine(quantitative_service)
        self.parameter_optimizer = IntelligentParameterOptimizer(quantitative_service.db_manager)
        self.trading_gatekeeper = StrictTradingGatekeeper(quantitative_service)
        
        self.running = False
        self.optimization_thread = None
    
    def start_continuous_optimization(self):
        """启动持续优化系统"""
        if self.running:
            logger.warning("持续优化系统已在运行")
            return
        
        logger.info("🚀 启动持续策略优化系统...")
        
        # 启动模拟引擎
        self.simulation_engine.start_continuous_simulation()
        
        # 启动优化循环
        self.running = True
        self.optimization_thread = threading.Thread(target=self._optimization_loop, daemon=True)
        self.optimization_thread.start()
        
        logger.info("✅ 持续优化系统启动成功")
    
    def stop_continuous_optimization(self):
        """停止持续优化系统"""
        logger.info("🛑 停止持续优化系统...")
        
        # 停止模拟引擎
        self.simulation_engine.stop_continuous_simulation()
        
        # 停止优化循环
        self.running = False
        if self.optimization_thread:
            self.optimization_thread.join()
        
        logger.info("✅ 持续优化系统已停止")
    
    def _optimization_loop(self):
        """优化主循环"""
        logger.info("🔄 启动策略优化循环...")
        
        while self.running:
            try:
                # 每30分钟执行一次优化和权限检查
                time.sleep(1800)
                
                if not self.running:
                    break
                
                logger.info("🔧 开始策略优化周期...")
                
                # 1. 识别需要优化的策略
                underperforming_strategies = self._identify_underperforming_strategies()
                
                # 2. 优化参数
                if underperforming_strategies:
                    self._optimize_strategies(underperforming_strategies)
                
                # 3. 更新交易权限
                self.trading_gatekeeper.update_trading_permissions()
                
                # 4. 生成优化报告
                self._generate_optimization_report()
                
                logger.info("✅ 策略优化周期完成")
                
            except Exception as e:
                logger.error(f"优化循环出错: {e}")
                time.sleep(300)  # 出错后等待5分钟
    
    def _identify_underperforming_strategies(self) -> List[Dict]:
        """识别表现不佳的策略"""
        try:
            underperforming = []
            
            # 查询表现不佳的策略
            poor_strategies = self.service.db_manager.execute_query("""
                SELECT strategy_id, current_score, rolling_win_rate, recent_trend, simulation_count
                FROM strategy_rolling_metrics 
                WHERE current_score < 60 OR rolling_win_rate < 0.5 OR recent_trend = 'declining'
                ORDER BY current_score ASC
            """, fetch_all=True)
            
            for strategy_data in poor_strategies:
                strategy_id, score, win_rate, trend, sim_count = strategy_data
                
                # 获取策略详细信息
                strategy_response = self.service.get_strategy(strategy_id)
                if strategy_response.get('success', False):
                    strategy = strategy_response['data']
                    strategy['performance_metrics'] = {
                        'score': score,
                        'win_rate': win_rate,
                        'trend': trend,
                        'simulation_count': sim_count
                    }
                    underperforming.append(strategy)
            
            logger.info(f"🔍 发现 {len(underperforming)} 个需要优化的策略")
            return underperforming
            
        except Exception as e:
            logger.error(f"识别表现不佳策略失败: {e}")
            return []
    
    def _optimize_strategies(self, strategies: List[Dict]):
        """优化策略参数"""
        for strategy in strategies:
            try:
                strategy_id = strategy['id']
                logger.info(f"🔧 开始优化策略: {strategy.get('name', strategy_id)}")
                
                # 获取最近的模拟结果
                recent_results = self._get_recent_simulation_results(strategy_id, limit=10)
                
                if len(recent_results) < 3:
                    logger.warning(f"策略 {strategy_id} 模拟数据不足，跳过优化")
                    continue
                
                # 优化参数
                optimized_params = self.parameter_optimizer.optimize_strategy_parameters(
                    strategy, recent_results
                )
                
                # 应用优化后的参数
                if optimized_params != strategy.get('parameters', {}):
                    update_result = self.service.update_strategy(
                        strategy_id,
                        strategy.get('name', ''),
                        strategy.get('symbol', ''),
                        optimized_params
                    )
                    
                    if update_result.get('success', False):
                        logger.info(f"✅ 策略 {strategy_id} 参数优化完成")
                    else:
                        logger.error(f"❌ 策略 {strategy_id} 参数更新失败")
                
            except Exception as e:
                logger.error(f"优化策略失败 {strategy.get('id', 'unknown')}: {e}")
    
    def _get_recent_simulation_results(self, strategy_id: str, limit: int = 10) -> List[SimulationResult]:
        """获取策略最近的模拟结果"""
        try:
            results_data = self.service.db_manager.execute_query("""
                SELECT strategy_id, simulation_date, win_rate, total_return, sharpe_ratio,
                       max_drawdown, total_trades, score, success
                FROM strategy_simulation_history 
                WHERE strategy_id = ? AND success = 1
                ORDER BY simulation_date DESC LIMIT ?
            """, (strategy_id, limit), fetch_all=True)
            
            results = []
            for row in results_data:
                result = SimulationResult(
                    strategy_id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    win_rate=row[2],
                    total_return=row[3],
                    sharpe_ratio=row[4],
                    max_drawdown=row[5],
                    total_trades=row[6],
                    score=row[7],
                    success=bool(row[8])
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"获取模拟结果失败 {strategy_id}: {e}")
            return []
    
    def _generate_optimization_report(self):
        """生成优化报告"""
        try:
            # 统计数据
            total_strategies = self.service.db_manager.execute_query("""
                SELECT COUNT(*) FROM strategies WHERE enabled = 1
            """, fetch_one=True)[0]
            
            qualified_strategies = self.service.db_manager.execute_query("""
                SELECT COUNT(*) FROM strategy_rolling_metrics WHERE ready_for_trading = 1
            """, fetch_one=True)[0]
            
            avg_score = self.service.db_manager.execute_query("""
                SELECT AVG(current_score) FROM strategy_rolling_metrics
            """, fetch_one=True)[0] or 0
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'total_strategies': total_strategies,
                'qualified_for_trading': qualified_strategies,
                'qualification_rate': qualified_strategies / max(total_strategies, 1) * 100,
                'average_score': round(avg_score, 2),
                'optimization_active': True
            }
            
            logger.info(f"📊 优化报告: {qualified_strategies}/{total_strategies} 策略合格 "
                       f"({report['qualification_rate']:.1f}%)，平均分: {report['average_score']}")
            
            # 保存报告到文件
            with open('logs/optimization_report.json', 'w') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"生成优化报告失败: {e}")
    
    def get_optimization_status(self) -> Dict:
        """获取优化系统状态"""
        try:
            # 获取基本统计
            total_strategies = self.service.db_manager.execute_query("""
                SELECT COUNT(*) FROM strategies WHERE enabled = 1
            """, fetch_one=True)[0]
            
            qualified_strategies = self.service.db_manager.execute_query("""
                SELECT COUNT(*) FROM strategy_rolling_metrics WHERE current_score >= 65
            """, fetch_one=True)[0]
            
            # 获取表现分布
            score_distribution = self.service.db_manager.execute_query("""
                SELECT 
                    COUNT(CASE WHEN current_score >= 80 THEN 1 END) as excellent,
                    COUNT(CASE WHEN current_score >= 65 THEN 1 END) as good,
                    COUNT(CASE WHEN current_score >= 50 THEN 1 END) as fair,
                    COUNT(*) as total
                FROM strategy_rolling_metrics
            """, fetch_one=True)
            
            return {
                'system_running': self.running,
                'total_strategies': total_strategies,
                'qualified_strategies': qualified_strategies,
                'qualification_rate': qualified_strategies / max(total_strategies, 1) * 100,
                'score_distribution': {
                    'excellent': score_distribution[0] if score_distribution else 0,
                    'good': score_distribution[1] if score_distribution else 0,
                    'fair': score_distribution[2] if score_distribution else 0,
                    'total': score_distribution[3] if score_distribution else 0
                }
            }
            
        except Exception as e:
            logger.error(f"获取优化状态失败: {e}")
            return {'system_running': False, 'error': str(e)}


# 使用示例
if __name__ == "__main__":
    # 这里应该集成到主系统中
    logger.info("持续策略优化系统 - 准备就绪") 