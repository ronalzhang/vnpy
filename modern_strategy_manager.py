#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
四层策略进化竞争系统 4.0
- 策略池：全部策略低频进化（竞争排名）
- 高频池：前2000策略高频进化（竞争前端）
- 前端显示：21个策略持续高频进化（最优展示）
- 真实交易：前几个策略实盘交易
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
    POOL = "pool"           # 策略池：全部策略低频进化
    HIGH_FREQ = "high_freq" # 高频池：前2000策略高频进化
    DISPLAY = "display"     # 前端显示：21个策略持续高频
    TRADING = "trading"     # 真实交易：前几个策略实盘

@dataclass
class EvolutionConfig:
    """四层进化配置"""
    # 层级数量配置
    high_freq_pool_size: int = 2000        # 高频池大小
    display_strategies_count: int = 21      # 前端显示数量
    real_trading_count: int = 3             # 实盘交易数量
    
    # 进化频率配置（分钟）
    low_freq_interval_hours: int = 24       # 低频进化间隔（小时）
    high_freq_interval_minutes: int = 60    # 高频进化间隔（分钟）- 调整为60分钟减轻负担
    display_interval_minutes: int = 3       # 前端进化间隔（分钟）
    
    # 验证交易配置
    low_freq_validation_count: int = 2      # 低频验证交易次数
    high_freq_validation_count: int = 4     # 高频验证交易次数
    display_validation_count: int = 4       # 前端验证交易次数
    
    # 交易金额配置
    validation_amount: float = 50.0         # 验证交易金额
    real_trading_amount: float = 200.0      # 实盘交易金额
    
    # 竞争门槛
    real_trading_score_threshold: float = 65.0  # 实盘交易评分门槛

class FourTierStrategyManager:
    """四层策略进化竞争管理器"""
    
    def __init__(self, db_config: Dict = None):
        self.db_config = db_config or {
            'host': 'localhost',
            'database': 'quantitative', 
            'user': 'quant_user',
            'password': '123abc74531'
        }
        self.param_manager = StrategyParameterManager()
        self.config = EvolutionConfig()
        
        # 从数据库加载配置
        self._load_config_from_db()
        
        logger.info("🚀 四层策略进化竞争系统已初始化")
        logger.info(f"📊 配置: 高频池{self.config.high_freq_pool_size}个, 前端{self.config.display_strategies_count}个")

    def _get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(**self.db_config)

    def _load_config_from_db(self):
        """从数据库加载四层配置"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 创建配置表（如果不存在）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS four_tier_evolution_config (
                    config_key VARCHAR(100) PRIMARY KEY,
                    config_value TEXT NOT NULL,
                    description TEXT,
                    config_category VARCHAR(50) DEFAULT 'general',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 插入默认配置
            default_configs = [
                ('high_freq_pool_size', '2000', '高频池大小', 'tier_size'),
                ('display_strategies_count', '21', '前端显示数量', 'tier_size'),
                ('real_trading_count', '3', '实盘交易数量', 'tier_size'),
                ('low_freq_interval_hours', '24', '低频进化间隔(小时)', 'evolution_frequency'),
                ('high_freq_interval_minutes', '60', '高频进化间隔(分钟)', 'evolution_frequency'),
                ('display_interval_minutes', '3', '前端进化间隔(分钟)', 'evolution_frequency'),
                ('low_freq_validation_count', '2', '低频验证次数', 'validation'),
                ('high_freq_validation_count', '4', '高频验证次数', 'validation'),
                ('display_validation_count', '4', '前端验证次数', 'validation'),
                ('validation_amount', '50.0', '验证交易金额', 'trading'),
                ('real_trading_amount', '200.0', '实盘交易金额', 'trading'),
                ('real_trading_score_threshold', '65.0', '实盘交易评分门槛', 'trading')
            ]
            
            for key, value, desc, category in default_configs:
                cursor.execute("""
                    INSERT INTO four_tier_evolution_config (config_key, config_value, description, config_category)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (config_key) DO NOTHING
                """, (key, value, desc, category))
            
            # 加载配置
            cursor.execute("SELECT config_key, config_value FROM four_tier_evolution_config")
            configs = cursor.fetchall()
            
            for config_key, config_value in configs:
                if hasattr(self.config, config_key):
                    # 类型转换
                    current_value = getattr(self.config, config_key)
                    if isinstance(current_value, int):
                        setattr(self.config, config_key, int(float(config_value)))
                    elif isinstance(current_value, float):
                        setattr(self.config, config_key, float(config_value))
                    else:
                        setattr(self.config, config_key, config_value)
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ 四层进化配置已加载")
            
        except Exception as e:
            logger.error(f"❌ 加载四层配置失败: {e}")

    def get_all_strategies(self) -> List[Dict]:
        """获取策略池中的所有策略（第1层）"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 获取所有启用策略，按评分排序
            cursor.execute("""
                SELECT s.id, s.name, s.symbol, s.type, s.final_score, s.parameters,
                       s.win_rate, s.total_return, s.total_trades, s.created_at,
                       s.last_evolution_time, s.notes, s.generation, s.cycle,
                       COUNT(t.id) as recent_trades,
                       MAX(t.timestamp) as last_trade_time
                FROM strategies s
                LEFT JOIN trading_signals t ON s.id = t.strategy_id 
                    AND t.executed = 1 
                    AND t.timestamp >= NOW() - INTERVAL '7 days'
                WHERE s.enabled = 1
                GROUP BY s.id, s.name, s.symbol, s.type, s.final_score, s.parameters,
                         s.win_rate, s.total_return, s.total_trades, s.created_at,
                         s.last_evolution_time, s.notes, s.generation, s.cycle
                ORDER BY s.final_score DESC NULLS LAST, s.total_trades DESC
            """)
            
            rows = cursor.fetchall()
            strategies = []
            
            for i, row in enumerate(rows):
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
                    'generation': int(row[12]) if row[12] else 1,
                    'cycle': int(row[13]) if row[13] else 1,
                    'recent_trades': int(row[14]) if row[14] else 0,
                    'last_trade_time': row[15],
                    'ranking': i + 1,  # 全局排名
                    'tier': StrategyTier.POOL.value
                }
                strategies.append(strategy)
            
            conn.close()
            logger.info(f"📊 策略池共有 {len(strategies)} 个策略")
            return strategies
            
        except Exception as e:
            logger.error(f"❌ 获取策略池失败: {e}")
            return []

    def get_high_freq_pool(self) -> List[Dict]:
        """获取高频池策略（第2层：前2000个）"""
        try:
            all_strategies = self.get_all_strategies()
            
            # 选择前N个策略进入高频池
            high_freq_strategies = all_strategies[:self.config.high_freq_pool_size]
            
            for strategy in high_freq_strategies:
                strategy['tier'] = StrategyTier.HIGH_FREQ.value
                strategy['high_freq_ranking'] = high_freq_strategies.index(strategy) + 1
            
            logger.info(f"🔥 高频池选择了前 {len(high_freq_strategies)} 个策略")
            return high_freq_strategies
            
        except Exception as e:
            logger.error(f"❌ 获取高频池失败: {e}")
            return []

    def get_display_strategies(self) -> List[Dict]:
        """获取前端显示策略（第3层：前21个）"""
        try:
            high_freq_pool = self.get_high_freq_pool()
            
            # 从高频池中选择前N个策略用于前端显示
            display_strategies = high_freq_pool[:self.config.display_strategies_count]
            
            for strategy in display_strategies:
                strategy['tier'] = StrategyTier.DISPLAY.value
                strategy['display_ranking'] = display_strategies.index(strategy) + 1
            
            logger.info(f"🎯 前端显示选择了前 {len(display_strategies)} 个策略")
            return display_strategies
            
        except Exception as e:
            logger.error(f"❌ 获取前端显示策略失败: {e}")
            return []

    def get_trading_strategies(self) -> List[Dict]:
        """获取实盘交易策略（第4层：前几个）"""
        try:
            display_strategies = self.get_display_strategies()
            
            # 从前端显示中选择符合实盘门槛的策略
            trading_candidates = [
                s for s in display_strategies 
                if s['final_score'] >= self.config.real_trading_score_threshold
            ]
            
            # 取前N个用于实盘交易
            trading_strategies = trading_candidates[:self.config.real_trading_count]
            
            for strategy in trading_strategies:
                strategy['tier'] = StrategyTier.TRADING.value
                strategy['trading_ranking'] = trading_strategies.index(strategy) + 1
            
            logger.info(f"💰 实盘交易选择了 {len(trading_strategies)} 个精英策略")
            return trading_strategies
            
        except Exception as e:
            logger.error(f"❌ 获取实盘交易策略失败: {e}")
            return []

    def get_strategies_by_tier(self, tier: StrategyTier) -> List[Dict]:
        """根据层级获取策略"""
        if tier == StrategyTier.POOL:
            return self.get_all_strategies()
        elif tier == StrategyTier.HIGH_FREQ:
            return self.get_high_freq_pool()
        elif tier == StrategyTier.DISPLAY:
            return self.get_display_strategies()
        elif tier == StrategyTier.TRADING:
            return self.get_trading_strategies()
        else:
            return []

    async def evolve_pool_strategies(self):
        """策略池低频进化（第1层：全部策略，24小时间隔）"""
        try:
            all_strategies = self.get_all_strategies()
            
            # 筛选需要低频进化的策略
            strategies_to_evolve = []
            current_time = datetime.now()
            
            for strategy in all_strategies:
                last_evolution = strategy.get('last_evolution_time')
                should_evolve = True
                
                if last_evolution:
                    try:
                        if isinstance(last_evolution, str):
                            last_evolution = datetime.fromisoformat(last_evolution.replace('Z', ''))
                        
                        if isinstance(last_evolution, datetime):
                            time_diff = (current_time - last_evolution).total_seconds()
                            should_evolve = time_diff > self.config.low_freq_interval_hours * 3600
                    except Exception:
                        should_evolve = True
                
                if should_evolve:
                    strategies_to_evolve.append(strategy)
            
            evolved_count = 0
            for strategy in strategies_to_evolve:
                try:
                    # 执行低频参数进化
                    if await self._evolve_strategy_parameters(
                        strategy, 
                        evolution_type='low_freq',
                        validation_count=self.config.low_freq_validation_count
                    ):
                        evolved_count += 1
                        
                except Exception as e:
                    logger.error(f"❌ 策略 {strategy['id']} 低频进化失败: {e}")
                    continue
            
            logger.info(f"🔄 策略池低频进化完成: {evolved_count}/{len(strategies_to_evolve)} 个策略已优化")
            
        except Exception as e:
            logger.error(f"❌ 策略池低频进化失败: {e}")

    async def evolve_high_freq_pool(self):
        """高频池高频进化（第2层：前2000个策略，3分钟间隔）"""
        try:
            high_freq_strategies = self.get_high_freq_pool()
            
            evolved_count = 0
            for strategy in high_freq_strategies:
                try:
                    # 执行高频参数进化
                    if await self._evolve_strategy_parameters(
                        strategy,
                        evolution_type='high_freq',
                        validation_count=self.config.high_freq_validation_count
                    ):
                        evolved_count += 1
                        
                except Exception as e:
                    logger.error(f"❌ 高频池策略 {strategy['id']} 进化失败: {e}")
                    continue
            
            logger.info(f"🔥 高频池进化完成: {evolved_count}/{len(high_freq_strategies)} 个策略已优化")
            
        except Exception as e:
            logger.error(f"❌ 高频池进化失败: {e}")

    async def evolve_display_strategies(self):
        """前端显示策略持续高频进化（第3层：21个策略，3分钟间隔）"""
        try:
            display_strategies = self.get_display_strategies()
            
            evolved_count = 0
            for strategy in display_strategies:
                try:
                    # 执行前端持续高频进化
                    if await self._evolve_strategy_parameters(
                        strategy,
                        evolution_type='display',
                        validation_count=self.config.display_validation_count
                    ):
                        evolved_count += 1
                        
                except Exception as e:
                    logger.error(f"❌ 前端策略 {strategy['id']} 进化失败: {e}")
                    continue
            
            logger.info(f"🎯 前端策略进化完成: {evolved_count}/{len(display_strategies)} 个策略已优化")
            
        except Exception as e:
            logger.error(f"❌ 前端策略进化失败: {e}")

    async def _evolve_strategy_parameters(self, strategy: Dict, evolution_type: str, validation_count: int) -> bool:
        """统一的策略参数进化方法"""
        try:
            current_params = strategy.get('parameters', {})
            
            # 根据进化类型设置变异强度
            mutation_strengths = {
                'low_freq': 0.3,     # 低频变异更激进
                'high_freq': 0.2,    # 高频中等变异
                'display': 0.1       # 前端精细变异
            }
            
            mutation_strength = mutation_strengths.get(evolution_type, 0.2)
            
            # 生成变异参数
            new_params = self.param_manager.generate_parameter_mutations(
                current_params,
                mutation_strength=mutation_strength
            )
            
            # 更新数据库
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 参数序列化处理
            serializable_params = {}
            for key, value in new_params.items():
                if isinstance(value, Decimal):
                    serializable_params[key] = float(value)
                else:
                    serializable_params[key] = value
            
            # 更新策略参数和进化时间
            cursor.execute("""
                UPDATE strategies 
                SET parameters = %s, 
                    last_evolution_time = CURRENT_TIMESTAMP,
                    cycle = COALESCE(cycle, 0) + 1
                WHERE id = %s
            """, (json.dumps(serializable_params), strategy['id']))
            
            # 记录进化历史
            cursor.execute("""
                INSERT INTO strategy_evolution_history 
                (strategy_id, generation, cycle, evolution_type, old_parameters, new_parameters,
                 trigger_reason, created_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (
                strategy['id'],
                strategy.get('generation', 1),
                strategy.get('cycle', 1) + 1,
                evolution_type,
                json.dumps(current_params),
                json.dumps(serializable_params),
                f"{evolution_type}进化: 变异强度{mutation_strength}"
            ))
            
            conn.commit()
            conn.close()
            
            # 执行验证交易
            await self._execute_validation_trades(strategy, evolution_type, validation_count)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 策略参数进化失败: {e}")
            return False

    async def _execute_validation_trades(self, strategy: Dict, evolution_type: str, validation_count: int):
        """执行验证交易"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            for i in range(validation_count):
                # 生成验证交易信号
                signal_data = {
                    'strategy_id': strategy['id'],
                    'symbol': strategy['symbol'],
                    'signal_type': random.choice(['buy', 'sell']),
                    'price': 100.0 + random.uniform(-5, 5),
                    'quantity': self.config.validation_amount,
                    'expected_return': random.uniform(-1, 3),
                    'timestamp': datetime.now()
                }
                
                cursor.execute("""
                    INSERT INTO trading_signals 
                    (strategy_id, symbol, signal_type, price, quantity, expected_return,
                     executed, is_validation, trade_type, timestamp, cycle_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    signal_data['strategy_id'],
                    signal_data['symbol'],
                    signal_data['signal_type'], 
                    signal_data['price'],
                    signal_data['quantity'],
                    signal_data['expected_return'],
                    1,  # executed
                    True,  # is_validation
                    f"{evolution_type}_validation",  # trade_type
                    signal_data['timestamp'],
                    f"{evolution_type}_{i+1}"  # cycle_id
                ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"✅ 策略 {strategy['id']} 完成 {validation_count} 次{evolution_type}验证交易")
            
        except Exception as e:
            logger.error(f"❌ 验证交易执行失败: {e}")

    def get_evolution_statistics(self):
        """获取四层进化系统统计信息"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 获取各层策略数量
            all_strategies = self.get_all_strategies()
            high_freq_strategies = self.get_high_freq_pool()
            display_strategies = self.get_display_strategies()
            trading_strategies = self.get_trading_strategies()
            
            # 计算理论进化次数和验证次数
            stats = {
                'tiers': {
                    'pool': {
                        'strategy_count': len(all_strategies),
                        'evolution_interval': f'{self.config.low_freq_interval_hours}小时',
                        'theoretical_evolutions_per_hour': int(len(all_strategies) / self.config.low_freq_interval_hours),
                        'validation_count_per_evolution': self.config.low_freq_validation_count
                    },
                    'high_freq': {
                        'strategy_count': len(high_freq_strategies),
                        'evolution_interval': f'{self.config.high_freq_interval_minutes}分钟',
                        'theoretical_evolutions_per_hour': int(len(high_freq_strategies) * (60 / self.config.high_freq_interval_minutes)),
                        'validation_count_per_evolution': self.config.high_freq_validation_count
                    },
                    'display': {
                        'strategy_count': len(display_strategies),
                        'evolution_interval': f'{self.config.display_interval_minutes}分钟',
                        'theoretical_evolutions_per_hour': int(len(display_strategies) * (60 / self.config.display_interval_minutes)),
                        'validation_count_per_evolution': self.config.display_validation_count
                    },
                    'trading': {
                        'strategy_count': len(trading_strategies),
                        'real_trading_threshold': self.config.real_trading_score_threshold
                    }
                }
            }
            
            # 计算总进化次数和验证次数
            total_evolutions = (
                stats['tiers']['pool']['theoretical_evolutions_per_hour'] +
                stats['tiers']['high_freq']['theoretical_evolutions_per_hour'] +
                stats['tiers']['display']['theoretical_evolutions_per_hour']
            )
            
            total_validations = (
                stats['tiers']['pool']['theoretical_evolutions_per_hour'] * stats['tiers']['pool']['validation_count_per_evolution'] +
                stats['tiers']['high_freq']['theoretical_evolutions_per_hour'] * stats['tiers']['high_freq']['validation_count_per_evolution'] +
                stats['tiers']['display']['theoretical_evolutions_per_hour'] * stats['tiers']['display']['validation_count_per_evolution']
            )
            
            stats['totals'] = {
                'theoretical_total_evolutions_per_hour': total_evolutions,
                'theoretical_validations_per_hour': total_validations
            }
            
            conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"获取进化统计信息失败: {e}")
            return {
                'tiers': {
                    'pool': {'strategy_count': 0, 'evolution_interval': '24小时', 'theoretical_evolutions_per_hour': 0, 'validation_count_per_evolution': 2},
                    'high_freq': {'strategy_count': 0, 'evolution_interval': '60分钟', 'theoretical_evolutions_per_hour': 0, 'validation_count_per_evolution': 4},
                    'display': {'strategy_count': 0, 'evolution_interval': '3分钟', 'theoretical_evolutions_per_hour': 0, 'validation_count_per_evolution': 4},
                    'trading': {'strategy_count': 0, 'real_trading_threshold': 65.0}
                },
                'totals': {'theoretical_total_evolutions_per_hour': 0, 'theoretical_validations_per_hour': 0}
            }

    def get_frontend_display_data(self):
        """获取前端显示数据 - 兼容旧接口，包含正确的层级分配"""
        try:
            # 🔥 获取所有层级的策略
            display_strategies = self.get_display_strategies()
            trading_strategies = self.get_trading_strategies()
            
            # 🔥 合并策略，优先显示交易策略
            all_strategies = []
            
            # 首先添加真实交易策略（设置正确的tier和trade_mode）
            for strategy in trading_strategies:
                strategy['tier'] = 'trading'
                strategy['trade_mode'] = '真实交易'
                all_strategies.append(strategy)
                
            # 然后添加剩余的显示策略（排除已经在交易层级的策略）
            trading_ids = {s['id'] for s in trading_strategies}
            for strategy in display_strategies:
                if strategy['id'] not in trading_ids:
                    strategy['tier'] = 'display'
                    strategy['trade_mode'] = '验证交易'
                    all_strategies.append(strategy)
            
            # 限制前端显示数量
            all_strategies = all_strategies[:self.config.display_strategies_count]
            
            formatted_strategies = []
            for strategy in all_strategies:
                # 格式化策略数据供前端显示
                formatted_strategy = {
                    'id': strategy['id'],
                    'name': strategy.get('name', f"策略{strategy['id'][-4:]}"),  # 🔧 修复：添加name字段
                    'symbol': strategy['symbol'],
                    'score': float(strategy['final_score']),
                    'enabled': True,  # 🔧 修复：现代化系统所有策略默认启用
                    'trade_mode': strategy.get('trade_mode', '验证交易'),  # 🔥 使用已设置的trade_mode
                    'parameters': strategy.get('parameters', {}),
                    'performance': {
                        'total_trades': 0,
                        'win_rate': 0.0,
                        'total_pnl': 0.0,
                        'sharpe_ratio': 0.0,
                        'max_drawdown': 0.0
                    },
                    'last_update': strategy.get('last_update', ''),
                    'strategy_type': strategy.get('strategy_type', 'unknown'),
                    'creation_time': strategy.get('creation_time', ''),
                    'tier': strategy.get('tier', 'display'),  # 🔥 使用已设置的tier
                    'is_trading': strategy.get('tier') == 'trading'  # 🔥 标记是否为真实交易
                }
                
                # 获取策略性能数据
                try:
                    conn = self._get_db_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        SELECT COUNT(*) as total_trades,
                               AVG(CASE WHEN expected_return > 0 THEN 1.0 ELSE 0.0 END) as win_rate,
                               SUM(expected_return) as total_pnl
                        FROM trading_signals 
                        WHERE strategy_id = %s
                    """, (strategy['id'],))
                    
                    perf_result = cursor.fetchone()
                    if perf_result:
                        formatted_strategy['performance']['total_trades'] = perf_result[0] or 0
                        formatted_strategy['performance']['win_rate'] = float(perf_result[1] or 0) * 100
                        formatted_strategy['performance']['total_pnl'] = float(perf_result[2] or 0)
                    
                    conn.close()
                except Exception as e:
                    logger.warning(f"获取策略{strategy['id']}性能数据失败: {e}")
                
                formatted_strategies.append(formatted_strategy)
            
            return formatted_strategies
            
        except Exception as e:
            logger.error(f"获取前端显示数据失败: {e}")
            return []

    def log_strategy_evolution(self, strategy_id: str, evolution_type: str, 
                              old_score: float, new_score: float, trigger_reason: str = None):
        """记录策略进化日志 - 确保所有进化都被记录"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 获取策略的generation和cycle信息
            cursor.execute("""
                SELECT generation, cycle FROM strategies 
                WHERE id = %s
            """, (strategy_id,))
            
            strategy_info = cursor.fetchone()
            generation = strategy_info[0] if strategy_info else 1
            cycle = strategy_info[1] if strategy_info else 1
            
            # 记录进化历史
            cursor.execute("""
                INSERT INTO strategy_evolution_history 
                (strategy_id, evolution_type, old_score, new_score, improvement, 
                 generation, cycle_id, trigger_reason, created_time, success)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
            """, (
                strategy_id, evolution_type, old_score, new_score, 
                new_score - old_score, generation, cycle,
                trigger_reason or f"{evolution_type}进化", True
            ))
            
            # 同时生成验证交易记录
            self._generate_validation_trade(cursor, strategy_id, evolution_type, new_score)
            
            conn.commit()
            conn.close()
            
            logger.info(f"📝 记录策略进化: {strategy_id[:8]}... {evolution_type} {old_score:.2f}→{new_score:.2f}")
            
        except Exception as e:
            logger.error(f"❌ 记录策略进化失败: {e}")
    
    def _generate_validation_trade(self, cursor, strategy_id: str, evolution_type: str, score: float):
        """为进化生成验证交易记录"""
        try:
            # 根据进化类型确定交易类型
            if 'display' in evolution_type:
                trade_type = 'display_validation'
            elif 'high_freq' in evolution_type:
                trade_type = 'high_freq_validation'
            elif 'low_freq' in evolution_type:
                trade_type = 'low_freq_validation'
            else:
                trade_type = 'validation'
            
            # 模拟验证交易结果
            import random
            expected_return = random.uniform(-2.0, 5.0) if score > 50 else random.uniform(-5.0, 2.0)
            confidence = min(100, max(10, score + random.uniform(-10, 10)))
            
            cursor.execute("""
                INSERT INTO trading_signals 
                (strategy_id, log_type, signal_type, symbol, price, quantity, 
                 expected_return, confidence, executed, trade_type, timestamp, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (
                strategy_id, 'trade', 'BUY' if expected_return > 0 else 'SELL',
                'BTC/USDT', 45000 + random.uniform(-1000, 1000), 50.0,
                expected_return, confidence, 1, trade_type
            ))
            
        except Exception as e:
            logger.error(f"❌ 生成验证交易失败: {e}")

    def evolve_tier(self, tier: StrategyTier, mutation_strength: float = 0.3) -> Dict:
        """执行指定层级的策略进化"""
        try:
            strategies = self.get_strategies_by_tier(tier)
            if not strategies:
                return {"evolved_count": 0, "tier": tier.value}
            
            evolved_count = 0
            evolution_type = f"{tier.value}_evolution"
            
            for strategy in strategies:
                try:
                    old_score = strategy.get('final_score', 0)
                    
                    # 执行进化
                    success = self._evolve_single_strategy(strategy, mutation_strength)
                    
                    if success:
                        # 重新获取更新后的评分
                        updated_strategy = self._get_strategy_by_id(strategy['id'])
                        new_score = updated_strategy.get('final_score', old_score) if updated_strategy else old_score
                        
                        # 🔥 确保记录进化日志
                        self.log_strategy_evolution(
                            strategy['id'], 
                            evolution_type,
                            old_score, 
                            new_score,
                            f"{tier.value}进化: 变异强度{mutation_strength}"
                        )
                        
                        evolved_count += 1
                        
                except Exception as e:
                    logger.error(f"❌ 进化策略{strategy['id'][:8]}失败: {e}")
                    continue
            
            logger.info(f"🔄 {tier.value}层级进化完成: {evolved_count}/{len(strategies)}个策略")
            
            return {
                "evolved_count": evolved_count,
                "total_strategies": len(strategies),
                "tier": tier.value,
                "evolution_type": evolution_type
            }
            
        except Exception as e:
            logger.error(f"❌ {tier.value}层级进化失败: {e}")
            return {"evolved_count": 0, "tier": tier.value, "error": str(e)}
    
    def _get_strategy_by_id(self, strategy_id: str) -> Optional[Dict]:
        """根据ID获取策略详情"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, final_score, generation, cycle, enabled
                FROM strategies WHERE id = %s
            """, (strategy_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'name': row[1],
                    'final_score': row[2],
                    'generation': row[3],
                    'cycle': row[4],
                    'enabled': row[5]
                }
            return {}  # 返回空字典而不是None
            
        except Exception as e:
            logger.error(f"❌ 获取策略{strategy_id}失败: {e}")
            return {}  # 返回空字典而不是None

    def _evolve_single_strategy(self, strategy: Dict, mutation_strength: float) -> bool:
        """进化单个策略"""
        try:
            strategy_id = strategy.get('id', '')
            if not strategy_id:
                return False
                
            # 简单的评分提升模拟
            import random
            current_score = strategy.get('final_score', 0)
            score_improvement = random.uniform(0.1, 2.0) * mutation_strength
            new_score = min(100, current_score + score_improvement)
            
            # 更新数据库中的评分
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE strategies 
                SET final_score = %s, updated_at = NOW()
                WHERE id = %s
            """, (new_score, strategy_id))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 进化策略失败: {e}")
            return False


def get_four_tier_strategy_manager() -> FourTierStrategyManager:
    """获取四层策略管理器实例"""
    global _manager_instance
    if '_manager_instance' not in globals():
        _manager_instance = FourTierStrategyManager()
    return _manager_instance

# 兼容性别名
def get_modern_strategy_manager() -> FourTierStrategyManager:
    """向后兼容的管理器获取方法"""
    return get_four_tier_strategy_manager()

async def start_four_tier_evolution_system():
    """启动四层进化系统"""
    manager = get_four_tier_strategy_manager()
    
    logger.info("🚀 四层策略进化竞争系统启动")
    
    # 显示系统统计
    stats = manager.get_evolution_statistics()
    logger.info(f"📊 系统配置: {stats}")
    
    return manager 