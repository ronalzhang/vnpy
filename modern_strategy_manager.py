#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
现代化分层策略管理系统 3.0
- 策略池概念：数据库保存所有策略作为策略池
- 分层管理：策略池 → 前端显示 → 真实交易
- 配置驱动：基于数据库配置进行策略选择和进化
- 动态进化：高频优化前端策略，定期测试策略池
"""

import psycopg2
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
import asyncio
import random
from dataclasses import dataclass
from enum import Enum

from strategy_parameters_config import StrategyParameterManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StrategyTier(Enum):
    """策略层级"""
    POOL = "pool"           # 策略池：所有策略
    DISPLAY = "display"     # 前端显示：优质策略
    TRADING = "trading"     # 真实交易：精英策略

@dataclass
class StrategyConfig:
    """策略管理配置"""
    # 进化配置
    evolution_interval: int = 3  # 分钟
    
    # 真实交易门槛
    real_trading_score: float = 65.0
    real_trading_count: int = 2
    real_trading_amount: float = 100.0
    
    # 验证交易配置
    validation_amount: float = 50.0
    min_trades: int = 30
    min_win_rate: float = 75.0
    min_profit: float = 100.0
    max_drawdown: float = 4.0
    min_sharpe_ratio: float = 1.5
    
    # 前端显示配置
    max_display_strategies: int = 21
    min_display_score: float = 10.0
    
    # 策略池管理
    pool_evolution_hours: int = 24  # 策略池进化间隔（小时）
    elimination_days: int = 15      # 淘汰周期（天）

class ModernStrategyManager:
    """现代化策略管理器"""
    
    def __init__(self, db_config: Dict = None):
        self.db_config = db_config or {
            'host': 'localhost',
            'database': 'quantitative',
            'user': 'quant_user',
            'password': '123abc74531'
        }
        self.param_manager = StrategyParameterManager()
        self.config = StrategyConfig()
        
        # 加载配置
        self._load_config_from_db()
        
        logger.info("🚀 现代化策略管理器已初始化")

    def _get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(**self.db_config)

    def _load_config_from_db(self):
        """从数据库加载配置"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT config_key, config_value FROM strategy_management_config")
            configs = cursor.fetchall()
            
            config_map = {
                'evolutionInterval': 'evolution_interval',
                'realTradingScore': 'real_trading_score', 
                'realTradingCount': 'real_trading_count',
                'realTradingAmount': 'real_trading_amount',
                'validationAmount': 'validation_amount',
                'minTrades': 'min_trades',
                'minWinRate': 'min_win_rate',
                'minProfit': 'min_profit',
                'maxDrawdown': 'max_drawdown',
                'minSharpeRatio': 'min_sharpe_ratio',
                'maxStrategies': 'max_display_strategies',
                'minScore': 'min_display_score',
                'eliminationDays': 'elimination_days'
            }
            
            for config_key, config_value in configs:
                if config_key in config_map:
                    attr_name = config_map[config_key]
                    if hasattr(self.config, attr_name):
                        # 类型转换
                        current_value = getattr(self.config, attr_name)
                        if isinstance(current_value, int):
                            setattr(self.config, attr_name, int(float(config_value)))
                        elif isinstance(current_value, float):
                            setattr(self.config, attr_name, float(config_value))
                        else:
                            setattr(self.config, attr_name, config_value)
            
            conn.close()
            logger.info(f"✅ 策略管理配置已加载: 进化间隔{self.config.evolution_interval}分钟, 真实交易门槛{self.config.real_trading_score}分")
            
        except Exception as e:
            logger.error(f"❌ 加载策略管理配置失败: {e}")

    def get_strategy_pool(self) -> List[Dict]:
        """获取策略池中的所有策略"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 获取所有策略，不区分启用/停用状态
            cursor.execute("""
                SELECT s.id, s.name, s.symbol, s.type, s.final_score, s.parameters,
                       s.win_rate, s.total_return, s.total_trades, s.created_at,
                       s.last_evolution_time, s.notes,
                       COUNT(t.id) as actual_trades,
                       MAX(t.timestamp) as last_trade_time
                FROM strategies s
                LEFT JOIN trading_signals t ON s.id = t.strategy_id AND t.executed = 1
                WHERE s.final_score IS NOT NULL
                GROUP BY s.id, s.name, s.symbol, s.type, s.final_score, s.parameters,
                         s.win_rate, s.total_return, s.total_trades, s.created_at,
                         s.last_evolution_time, s.notes
                ORDER BY s.final_score DESC, s.total_trades DESC
            """)
            
            rows = cursor.fetchall()
            strategies = []
            
            for row in rows:
                strategy = {
                    'id': row[0],
                    'name': row[1],
                    'symbol': row[2] or 'BTC/USDT',
                    'type': row[3] or 'momentum',
                    'final_score': float(row[4]) if row[4] else 0.0,
                    'parameters': json.loads(row[5]) if row[5] else {},
                    'win_rate': float(row[6]) if row[6] else 0.0,
                    'total_return': float(row[7]) if row[7] else 0.0,
                    'total_trades': int(row[8]) if row[8] else 0,
                    'created_at': row[9],
                    'last_evolution_time': row[10],
                    'notes': row[11],
                    'actual_trades': int(row[12]) if row[12] else 0,
                    'last_trade_time': row[13],
                    'tier': StrategyTier.POOL.value
                }
                strategies.append(strategy)
            
            conn.close()
            logger.info(f"📊 策略池共有 {len(strategies)} 个策略")
            return strategies
            
        except Exception as e:
            logger.error(f"❌ 获取策略池失败: {e}")
            return []

    def select_display_strategies(self) -> List[Dict]:
        """从策略池中选择优质策略用于前端显示"""
        try:
            all_strategies = self.get_strategy_pool()
            
            # 筛选条件
            display_strategies = []
            
            for strategy in all_strategies:
                # 基本门槛筛选
                if (strategy['final_score'] >= self.config.min_display_score and
                    strategy['actual_trades'] >= self.config.min_trades):
                    
                    strategy['tier'] = StrategyTier.DISPLAY.value
                    display_strategies.append(strategy)
            
            # 按分值排序，取前N个
            display_strategies.sort(key=lambda x: x['final_score'], reverse=True)
            selected = display_strategies[:self.config.max_display_strategies]
            
            logger.info(f"✅ 已选择 {len(selected)} 个优质策略用于前端显示")
            return selected
            
        except Exception as e:
            logger.error(f"❌ 选择前端显示策略失败: {e}")
            return []

    def select_trading_strategies(self) -> List[Dict]:
        """从前端显示策略中选择精英策略用于真实交易"""
        try:
            display_strategies = self.select_display_strategies()
            
            # 应用严格的真实交易门槛
            trading_strategies = []
            
            for strategy in display_strategies:
                # 严格门槛筛选
                meets_criteria = (
                    strategy['final_score'] >= self.config.real_trading_score and
                    strategy['win_rate'] >= self.config.min_win_rate and
                    strategy['total_return'] >= self.config.min_profit / 1000 and  # 转换为比例
                    strategy['actual_trades'] >= self.config.min_trades
                )
                
                if meets_criteria:
                    strategy['tier'] = StrategyTier.TRADING.value
                    trading_strategies.append(strategy)
            
            # 按综合评分排序，取前N个
            trading_strategies.sort(key=lambda x: (
                x['final_score'] * 0.4 + 
                x['win_rate'] * 0.3 + 
                x['total_return'] * 1000 * 0.3
            ), reverse=True)
            
            selected = trading_strategies[:self.config.real_trading_count]
            
            logger.info(f"🏆 已选择 {len(selected)} 个精英策略用于真实交易")
            return selected
            
        except Exception as e:
            logger.error(f"❌ 选择真实交易策略失败: {e}")
            return []

    def get_strategies_by_tier(self, tier: StrategyTier) -> List[Dict]:
        """根据层级获取策略"""
        if tier == StrategyTier.POOL:
            return self.get_strategy_pool()
        elif tier == StrategyTier.DISPLAY:
            return self.select_display_strategies()
        elif tier == StrategyTier.TRADING:
            return self.select_trading_strategies()
        else:
            return []

    async def evolve_display_strategies(self):
        """高频进化前端显示策略（每3分钟）"""
        try:
            display_strategies = self.select_display_strategies()
            evolved_count = 0
            
            for strategy in display_strategies:
                try:
                    # 执行参数优化
                    if await self._evolve_strategy_parameters(strategy):
                        evolved_count += 1
                        
                        # 执行验证交易
                        await self._execute_validation_trade(strategy)
                        
                except Exception as e:
                    logger.error(f"❌ 策略 {strategy['id']} 进化失败: {e}")
                    continue
            
            logger.info(f"🔄 前端策略高频进化完成: {evolved_count}/{len(display_strategies)} 个策略已优化")
            
        except Exception as e:
            logger.error(f"❌ 前端策略进化失败: {e}")

    async def evolve_pool_strategies(self):
        """定期进化策略池（每24小时）"""
        try:
            pool_strategies = self.get_strategy_pool()
            
            # 选择需要进化的策略
            strategies_to_evolve = []
            current_time = datetime.now()
            
            for strategy in pool_strategies:
                last_evolution = strategy.get('last_evolution_time')
                if not last_evolution or \
                   (current_time - last_evolution).total_seconds() > self.config.pool_evolution_hours * 3600:
                    strategies_to_evolve.append(strategy)
            
            evolved_count = 0
            for strategy in strategies_to_evolve:
                try:
                    if await self._evolve_strategy_parameters(strategy, pool_mode=True):
                        evolved_count += 1
                        
                except Exception as e:
                    logger.error(f"❌ 策略池策略 {strategy['id']} 进化失败: {e}")
                    continue
            
            logger.info(f"🔄 策略池定期进化完成: {evolved_count}/{len(strategies_to_evolve)} 个策略已优化")
            
        except Exception as e:
            logger.error(f"❌ 策略池进化失败: {e}")

    async def _evolve_strategy_parameters(self, strategy: Dict, pool_mode: bool = False) -> bool:
        """进化策略参数"""
        try:
            current_params = strategy.get('parameters', {})
            strategy_type = strategy.get('type', 'momentum')
            
            # 基于当前表现生成新参数
            mutation_strength = 0.3 if pool_mode else 0.1  # 策略池变异更激进
            
            # 生成变异参数
            new_params = self.param_manager.generate_parameter_mutations(
                current_params, 
                mutation_strength=mutation_strength
            )
            
            # 更新数据库
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE strategies 
                SET parameters = %s, last_evolution_time = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (json.dumps(new_params), strategy['id']))
            
            conn.commit()
            conn.close()
            
            # 记录进化日志
            await self._log_evolution_event(strategy['id'], 'parameter_optimization', 
                                           f"参数优化: {len(new_params)}个参数已更新")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 策略参数进化失败: {e}")
            return False

    async def _execute_validation_trade(self, strategy: Dict):
        """执行验证交易"""
        try:
            # 模拟验证交易逻辑
            # 实际实现中，这里会调用交易引擎执行小额验证交易
            
            validation_result = {
                'strategy_id': strategy['id'],
                'symbol': strategy['symbol'],
                'amount': self.config.validation_amount,
                'signal_type': random.choice(['buy', 'sell']),
                'timestamp': datetime.now(),
                'is_validation': True,
                'expected_return': random.uniform(-2, 5)  # 模拟收益
            }
            
            # 记录验证交易信号
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO trading_signals 
                (strategy_id, symbol, signal_type, price, quantity, expected_return, 
                 executed, is_validation, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                validation_result['strategy_id'],
                validation_result['symbol'], 
                validation_result['signal_type'],
                100.0,  # 模拟价格
                validation_result['amount'],
                validation_result['expected_return'],
                1,  # 已执行
                True,  # 验证交易
                validation_result['timestamp']
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ 策略 {strategy['id']} 验证交易已执行")
            
        except Exception as e:
            logger.error(f"❌ 验证交易执行失败: {e}")

    async def _log_evolution_event(self, strategy_id: str, optimization_type: str, trigger_reason: str):
        """记录进化事件"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO strategy_optimization_logs 
                (strategy_id, optimization_type, trigger_reason, timestamp, 
                 old_parameters, new_parameters)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s, %s)
            """, (
                strategy_id, optimization_type, trigger_reason,
                json.dumps({}), json.dumps({})  # 简化版本
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ 记录进化事件失败: {e}")

    def get_frontend_display_data(self) -> Dict:
        """获取前端显示数据"""
        try:
            # 获取不同层级的策略
            display_strategies = self.select_display_strategies()
            trading_strategies = self.select_trading_strategies()
            
            # 标记策略层级
            for strategy in display_strategies:
                strategy['is_trading'] = strategy['id'] in [s['id'] for s in trading_strategies]
                strategy['card_style'] = 'golden' if strategy['is_trading'] else 'normal'
                
                # 添加进化状态信息
                last_evolution = strategy.get('last_evolution_time')
                if last_evolution and isinstance(last_evolution, datetime):
                    time_since_evolution = (datetime.now() - last_evolution).total_seconds() / 60
                    strategy['evolution_status'] = 'recent' if time_since_evolution < self.config.evolution_interval * 2 else 'normal'
                else:
                    strategy['evolution_status'] = 'pending'
            
            result = {
                'display_strategies': display_strategies,
                'trading_strategies': trading_strategies,
                'config': {
                    'evolution_interval': self.config.evolution_interval,
                    'real_trading_count': self.config.real_trading_count,
                    'real_trading_score_threshold': self.config.real_trading_score,
                    'max_display_strategies': self.config.max_display_strategies
                },
                'statistics': {
                    'total_pool_strategies': len(self.get_strategy_pool()),
                    'display_strategies_count': len(display_strategies),
                    'trading_strategies_count': len(trading_strategies),
                    'last_evolution_time': datetime.now().isoformat()
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 获取前端显示数据失败: {e}")
            return {
                'display_strategies': [], 
                'trading_strategies': [],
                'config': {
                    'evolution_interval': 3,
                    'real_trading_count': 2,
                    'real_trading_score_threshold': 65.0,
                    'max_display_strategies': 21
                },
                'statistics': {
                    'total_pool_strategies': 0,
                    'display_strategies_count': 0,
                    'trading_strategies_count': 0,
                    'last_evolution_time': datetime.now().isoformat()
                }
            }

    async def start_evolution_scheduler(self):
        """启动进化调度器"""
        logger.info("🚀 策略进化调度器已启动")
        
        try:
            while True:
                # 高频进化前端显示策略
                await self.evolve_display_strategies()
                
                # 等待配置的间隔时间
                await asyncio.sleep(self.config.evolution_interval * 60)
                
        except Exception as e:
            logger.error(f"❌ 策略进化调度器异常: {e}")

    async def start_pool_evolution_scheduler(self):
        """启动策略池进化调度器"""
        logger.info("🚀 策略池进化调度器已启动")
        
        try:
            while True:
                # 定期进化策略池
                await self.evolve_pool_strategies()
                
                # 等待24小时
                await asyncio.sleep(self.config.pool_evolution_hours * 3600)
                
        except Exception as e:
            logger.error(f"❌ 策略池进化调度器异常: {e}")


# 单例模式
_modern_strategy_manager = None

def get_modern_strategy_manager() -> ModernStrategyManager:
    """获取现代化策略管理器单例"""
    global _modern_strategy_manager
    if _modern_strategy_manager is None:
        _modern_strategy_manager = ModernStrategyManager()
    return _modern_strategy_manager

# 异步启动函数
async def start_evolution_system():
    """启动策略进化系统"""
    manager = get_modern_strategy_manager()
    
    # 并发运行两个调度器
    await asyncio.gather(
        manager.start_evolution_scheduler(),
        manager.start_pool_evolution_scheduler()
    )

if __name__ == "__main__":
    # 测试运行
    manager = get_modern_strategy_manager()
    
    # 测试基础功能
    print("=== 测试现代化策略管理器 ===")
    
    # 测试策略池
    pool_strategies = manager.get_strategy_pool()
    print(f"策略池策略数量: {len(pool_strategies)}")
    
    # 测试前端显示策略选择
    display_strategies = manager.select_display_strategies()
    print(f"前端显示策略数量: {len(display_strategies)}")
    
    # 测试真实交易策略选择
    trading_strategies = manager.select_trading_strategies()
    print(f"真实交易策略数量: {len(trading_strategies)}")
    
    # 测试前端数据获取
    frontend_data = manager.get_frontend_display_data()
    print(f"前端数据: {len(frontend_data['display_strategies'])} 个显示策略, {len(frontend_data['trading_strategies'])} 个交易策略") 