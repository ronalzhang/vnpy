#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧠 高级策略管理器 - 完整的策略生命周期管理系统
实现策略的自动进化、升级、淘汰、配置管理等功能
"""

import time
import json
import logging
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
import threading
import traceback
from db_config import get_db_config

class AdvancedStrategyManager:
    """🚀 高级策略管理器 - 全自动策略生命周期管理"""
    
    def __init__(self):
        self.db_config = get_db_config()
        self.logger = self._setup_logger()
        self.running = False
        
        # 🎯 默认配置（可被数据库配置覆盖）
        self.config = {
            # 策略数量控制
            'max_total_strategies': 150,           # 策略表最多保留150个策略
            'optimal_strategy_count': 100,         # 最优策略数量
            'display_strategy_count': 20,          # 前端显示数量
            'real_trading_count': 3,               # 真实交易策略数量
            
            # 进化和淘汰配置
            'evolution_interval_minutes': 15,      # 进化检查间隔
            'elimination_cycle_hours': 24,         # 淘汰周期
            'score_improvement_threshold': Decimal('5.0'),    # 评分提升门槛
            
            # 质量标准
            'real_trading_score_threshold': Decimal('65.0'),  # 真实交易门槛
            'elimination_score_threshold': Decimal('30.0'),   # 淘汰门槛
            'min_trades_for_evaluation': 10,       # 最少交易次数
            'min_win_rate': Decimal('0.6'),                   # 最低胜率
            
            # 风险控制
            'max_position_size': Decimal('200.0'),            # 最大仓位
            'stop_loss_percent': Decimal('5.0'),              # 止损百分比
            'take_profit_percent': Decimal('4.0'),            # 止盈百分比
            
            # 自动管理
            'auto_management_enabled': True,        # 启用全自动管理
            'strategy_rotation_enabled': True,      # 启用策略轮换
            'auto_optimization_enabled': True       # 启用自动优化
        }
        
        self.load_config_from_db()
        
    def _setup_logger(self):
        """设置日志"""
        logger = logging.getLogger('AdvancedStrategyManager')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(**self.db_config)
    
    def load_config_from_db(self):
        """从数据库加载配置"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 检查配置表是否存在
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'strategy_management_config'
                )
            """)
            
            if cursor.fetchone()[0]:
                cursor.execute("SELECT config_key, config_value FROM strategy_management_config")
                rows = cursor.fetchall()
                
                for key, value in rows:
                    if key in self.config:
                        # 根据类型转换值
                        if isinstance(self.config[key], bool):
                            self.config[key] = value.lower() == 'true'
                        elif isinstance(self.config[key], int):
                            self.config[key] = int(value)
                        elif isinstance(self.config[key], Decimal):
                            self.config[key] = Decimal(value)
                        elif isinstance(self.config[key], float):
                            # For backward compatibility if float is still stored
                            self.config[key] = Decimal(str(value))
                        else:
                            self.config[key] = value
                            
                self.logger.info("✅ 策略管理配置已从数据库加载")
            else:
                self.create_config_table()
                
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"❌ 加载配置失败: {e}")
    
    def create_config_table(self):
        """创建配置表"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_management_config (
                    config_key VARCHAR(100) PRIMARY KEY,
                    config_value TEXT NOT NULL,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 插入默认配置
            for key, value in self.config.items():
                cursor.execute("""
                    INSERT INTO strategy_management_config (config_key, config_value, description)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (config_key) DO NOTHING
                """, (key, str(value), f"策略管理配置: {key}"))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self.logger.info("✅ 策略管理配置表已创建")
            
        except Exception as e:
            self.logger.error(f"❌ 创建配置表失败: {e}")
    
    def update_config(self, config_updates: Dict):
        """更新配置到数据库"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            for key, value in config_updates.items():
                if key in self.config:
                    cursor.execute("""
                        INSERT INTO strategy_management_config (config_key, config_value, updated_at)
                        VALUES (%s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (config_key) DO UPDATE SET
                        config_value = EXCLUDED.config_value,
                        updated_at = EXCLUDED.updated_at
                    """, (key, str(value)))
                    
                    self.config[key] = value
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self.logger.info(f"✅ 配置已更新: {list(config_updates.keys())}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 更新配置失败: {e}")
            return False
    
    def get_strategy_statistics(self) -> Dict:
        """获取策略统计信息"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 获取总策略数
            cursor.execute("SELECT COUNT(*) FROM strategies WHERE id LIKE 'STRAT_%'")
            total_count = cursor.fetchone()[0]
            
            # 获取活跃策略数
            cursor.execute("""
                SELECT COUNT(*) FROM strategies 
                WHERE id LIKE 'STRAT_%' AND enabled = true
            """)
            active_count = cursor.fetchone()[0]
            
            # 获取真实交易策略数
            cursor.execute("""
                SELECT COUNT(*) FROM strategies 
                WHERE id LIKE 'STRAT_%' AND final_score >= %s AND enabled = true
            """, (self.config['real_trading_score_threshold'],))
            real_trading_count = cursor.fetchone()[0]
            
            # 获取验证交易策略数
            cursor.execute("""
                SELECT COUNT(*) FROM strategies 
                WHERE id LIKE 'STRAT_%' AND final_score >= 45 AND final_score < %s AND enabled = true
            """, (self.config['real_trading_score_threshold'],))
            validation_count = cursor.fetchone()[0]
            
            # 获取平均评分
            cursor.execute("""
                SELECT COALESCE(AVG(final_score), 0) FROM strategies 
                WHERE id LIKE 'STRAT_%' AND final_score > 0
            """)
            avg_score_raw = cursor.fetchone()[0]
            avg_score = Decimal(str(avg_score_raw)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            cursor.close()
            conn.close()
            
            return {
                'total_strategies': total_count,
                'active_strategies': active_count,
                'real_trading_strategies': real_trading_count,
                'validation_strategies': validation_count,
                'average_score': avg_score,
                'config': self.config
            }
            
        except Exception as e:
            self.logger.error(f"❌ 获取策略统计失败: {e}")
            return {}
    
    def eliminate_poor_strategies(self) -> int:
        """🗑️ 淘汰表现差的策略"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            current_time = datetime.now()
            elimination_threshold = current_time - timedelta(hours=self.config['elimination_cycle_hours'])
            
            # 获取需要淘汰的策略
            cursor.execute("""
                SELECT id, name, final_score, total_trades, win_rate, total_return 
                FROM strategies 
                WHERE id LIKE 'STRAT_%' 
                  AND (
                      final_score < %s 
                      OR (total_trades >= %s AND win_rate < %s)
                      OR created_at < %s
                  )
                  AND enabled = false
                ORDER BY final_score ASC
            """, (
                self.config['elimination_score_threshold'],
                self.config['min_trades_for_evaluation'],
                self.config['min_win_rate'],
                elimination_threshold
            ))
            
            poor_strategies = cursor.fetchall()
            
            # 检查总策略数，如果超过最大数量，淘汰更多策略
            cursor.execute("SELECT COUNT(*) FROM strategies WHERE id LIKE 'STRAT_%'")
            total_count = cursor.fetchone()[0]
            
            if total_count > self.config['max_total_strategies']:
                # 需要额外淘汰的数量
                extra_elimination = total_count - self.config['optimal_strategy_count']
                
                # 获取评分最低的策略
                cursor.execute("""
                    SELECT id, name, final_score 
                    FROM strategies 
                    WHERE id LIKE 'STRAT_%' AND enabled = false
                    ORDER BY final_score ASC, total_trades ASC
                    LIMIT %s
                """, (extra_elimination,))
                
                extra_poor_strategies = cursor.fetchall()
                poor_strategies.extend(extra_poor_strategies)
            
            # 去重
            strategies_to_eliminate = list(set([s[0] for s in poor_strategies]))
            
            eliminated_count = 0
            for strategy_id in strategies_to_eliminate:
                try:
                    # 记录淘汰日志
                    cursor.execute("""
                        INSERT INTO strategy_logs (strategy_id, log_type, message, timestamp)
                        VALUES (%s, 'elimination', %s, %s)
                    """, (
                        strategy_id,
                        f"策略因表现不佳被自动淘汰 - 评分过低或长期无改善",
                        current_time
                    ))
                    
                    # 删除策略
                    cursor.execute("DELETE FROM strategies WHERE id = %s", (strategy_id,))
                    eliminated_count += 1
                    
                except Exception as e:
                    self.logger.error(f"❌ 淘汰策略 {strategy_id} 失败: {e}")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            if eliminated_count > 0:
                self.logger.info(f"🗑️ 已淘汰 {eliminated_count} 个表现差的策略")
            
            return eliminated_count
            
        except Exception as e:
            self.logger.error(f"❌ 策略淘汰失败: {e}")
            return 0
    
    def select_top_strategies_for_trading(self) -> List[Dict]:
        """🏆 选择顶级策略进行真实交易"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 获取达到真实交易标准的策略
            cursor.execute("""
                SELECT id, name, symbol, type, final_score, total_trades, win_rate, total_return
                FROM strategies 
                WHERE id LIKE 'STRAT_%' 
                  AND final_score >= %s
                  AND total_trades >= %s
                  AND win_rate >= %s
                  AND enabled = true
                ORDER BY final_score DESC, total_return DESC, win_rate DESC
                LIMIT %s
            """, (
                self.config['real_trading_score_threshold'],
                self.config['min_trades_for_evaluation'],
                self.config['min_win_rate'],
                self.config['real_trading_count']
            ))
            
            top_strategies = []
            rows = cursor.fetchall()
            
            for row in rows:
                strategy = {
                    'id': row[0],
                    'name': row[1],
                    'symbol': row[2],
                    'type': row[3],
                    'final_score': float(row[4]) if row[4] else 0,
                    'total_trades': int(row[5]) if row[5] else 0,
                    'win_rate': float(row[6]) if row[6] else 0,
                    'total_return': float(row[7]) if row[7] else 0
                }
                top_strategies.append(strategy)
            
            cursor.close()
            conn.close()
            
            if top_strategies:
                self.logger.info(f"🏆 已选择 {len(top_strategies)} 个顶级策略进行真实交易")
            
            return top_strategies
            
        except Exception as e:
            self.logger.error(f"❌ 选择顶级策略失败: {e}")
            return []
    
    def optimize_strategy_parameters(self, strategy_id: str) -> bool:
        """🔧 优化策略参数"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 获取策略当前信息
            cursor.execute("""
                SELECT name, type, parameters, final_score, total_trades, win_rate
                FROM strategies WHERE id = %s
            """, (strategy_id,))
            
            result = cursor.fetchone()
            if not result:
                return False
            
            name, strategy_type, current_params, score, trades, win_rate = result
            
            # 解析当前参数
            try:
                params = json.loads(current_params) if current_params else {}
            except:
                params = {}
            
            # 根据策略表现决定优化方向
            if score < 40:  # 低分策略 - 激进优化
                optimization_factor = 0.3
                message = "低分策略激进优化"
            elif score < 55:  # 中等策略 - 温和优化
                optimization_factor = 0.2
                message = "中等策略温和优化"
            elif score < 70:  # 高分策略 - 保守优化
                optimization_factor = 0.1
                message = "高分策略保守优化"
            else:  # 顶级策略 - 微调
                optimization_factor = 0.05
                message = "顶级策略精细微调"
            
            # 优化参数
            optimized_params = self._apply_parameter_optimization(params, optimization_factor, win_rate)
            
            # 更新策略参数
            cursor.execute("""
                UPDATE strategies 
                SET parameters = %s, 
                    cycle = COALESCE(cycle, 0) + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (json.dumps(optimized_params), strategy_id))
            
            # 记录优化日志
            cursor.execute("""
                INSERT INTO strategy_logs (strategy_id, log_type, message, parameters_before, parameters_after, timestamp)
                VALUES (%s, 'optimization', %s, %s, %s, %s)
            """, (
                strategy_id,
                message,
                json.dumps(params),
                json.dumps(optimized_params),
                datetime.now()
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self.logger.info(f"🔧 策略 {strategy_id} 参数已优化")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 优化策略 {strategy_id} 失败: {e}")
            return False
    
    def _apply_parameter_optimization(self, params: Dict, factor: float, win_rate: float) -> Dict:
        """应用参数优化逻辑"""
        optimized = params.copy()
        
        # 根据胜率调整参数
        if win_rate < 0.5:  # 胜率太低
            # 降低交易频率，提高质量
            if 'threshold' in optimized:
                optimized['threshold'] = min(optimized['threshold'] * (1 + factor), 0.05)
            if 'lookback_period' in optimized:
                optimized['lookback_period'] = max(int(optimized['lookback_period'] * (1 + factor)), 5)
        
        elif win_rate > 0.8:  # 胜率很高
            # 适当增加交易频率
            if 'threshold' in optimized:
                optimized['threshold'] = max(optimized['threshold'] * (1 - factor * 0.5), 0.001)
            if 'quantity' in optimized:
                optimized['quantity'] = min(optimized['quantity'] * (1 + factor * 0.5), 1000)
        
        # 风险控制优化
        if 'stop_loss_pct' in optimized:
            optimized['stop_loss_pct'] = max(optimized['stop_loss_pct'] * (1 - factor * 0.1), 1.0)
        
        if 'take_profit_pct' in optimized:
            optimized['take_profit_pct'] = min(optimized['take_profit_pct'] * (1 + factor * 0.1), 10.0)
        
        return optimized
    
    def run_automatic_management(self):
        """🤖 运行全自动策略管理"""
        if not self.config['auto_management_enabled']:
            self.logger.info("🚫 全自动管理已禁用")
            return
        
        self.running = True
        self.logger.info("🚀 启动全自动策略管理系统")
        
        while self.running:
            try:
                start_time = time.time()
                
                # 1. 获取当前统计信息
                stats = self.get_strategy_statistics()
                self.logger.info(f"📊 当前策略统计: {stats}")
                
                # 2. 策略淘汰
                eliminated = self.eliminate_poor_strategies()
                
                # 3. 策略优化
                if self.config['auto_optimization_enabled']:
                    optimized = self._run_strategy_optimization()
                    self.logger.info(f"🔧 已优化 {optimized} 个策略")
            
                # 4. 选择顶级策略
                top_strategies = self.select_top_strategies_for_trading()
                
                # 5. 策略轮换
                if self.config['strategy_rotation_enabled']:
                    rotated = self._run_strategy_rotation()
                    self.logger.info(f"🔄 已轮换 {rotated} 个策略")
                
                execution_time = time.time() - start_time
                self.logger.info(f"⏱️ 管理周期完成，耗时 {execution_time:.2f}秒")
                
                # 等待下一个周期
                time.sleep(self.config['evolution_interval_minutes'] * 60)
                
            except Exception as e:
                self.logger.error(f"❌ 自动管理失败: {e}")
                traceback.print_exc()
                time.sleep(60)  # 出错后等待1分钟再试
    
    def _run_strategy_optimization(self) -> int:
        """运行策略优化"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 获取需要优化的策略
            cursor.execute("""
                SELECT id FROM strategies 
                WHERE id LIKE 'STRAT_%' 
                  AND enabled = true
                  AND (
                      final_score < 60 
                      OR total_trades >= 20
                  )
                ORDER BY final_score ASC
                LIMIT 10
            """)
            
            strategies = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            optimized_count = 0
            for strategy_id in strategies:
                if self.optimize_strategy_parameters(strategy_id):
                    optimized_count += 1
            
            return optimized_count
            
        except Exception as e:
            self.logger.error(f"❌ 策略优化失败: {e}")
            return 0
    
    def _run_strategy_rotation(self) -> int:
        """运行策略轮换 - 已禁用"""
        self.logger.info("🛡️ 策略轮换功能已禁用，使用现代化策略管理系统")
        return 0  # 直接返回，不执行轮换
    
    def stop(self):
        """停止自动管理"""
        self.running = False
        self.logger.info("🛑 全自动策略管理已停止")
    
    def get_config(self) -> Dict:
        """获取当前配置"""
        return self.config.copy()
    
    def get_display_strategies(self, limit: Optional[int] = None) -> List[Dict]:
        """获取用于前端显示的策略列表"""
        try:
            display_limit = limit or self.config['display_strategy_count']
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 首先检查表结构
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'strategies' 
                ORDER BY ordinal_position
            """)
            columns = [row[0] for row in cursor.fetchall()]
            self.logger.info(f"📋 strategies表字段: {columns}")
            
            # 安全查询，只选择存在的字段
            base_fields = ['id', 'name', 'symbol', 'type', 'enabled', 'final_score', 'total_trades', 'win_rate', 'total_return']
            optional_fields = ['generation', 'cycle', 'created_at', 'updated_at']
            
            # 构建查询字段列表
            select_fields = []
            for field in base_fields:
                if field in columns:
                    select_fields.append(field)
                else:
                    select_fields.append(f"NULL as {field}")
            
            for field in optional_fields:
                if field in columns:
                    select_fields.append(field)
                else:
                    if field in ['generation', 'cycle']:
                        select_fields.append(f"1 as {field}")
                    else:
                        select_fields.append(f"NULL as {field}")
            
            query = f"""
                SELECT {', '.join(select_fields)}
                FROM strategies 
                WHERE final_score IS NOT NULL
                ORDER BY final_score DESC, total_trades DESC
                LIMIT %s
            """
            
            self.logger.info(f"🔍 执行查询: {query}")
            cursor.execute(query, (display_limit,))
            
            strategies = []
            rows = cursor.fetchall()
            self.logger.info(f"📊 查询到 {len(rows)} 个策略")
            
            for i, row in enumerate(rows):
                try:
                    strategy = {
                        'id': row[0] if row[0] else f"STRAT_{i}",
                        'name': row[1] if row[1] else f"策略_{i}",
                        'symbol': row[2] if row[2] else 'BTC/USDT',
                        'type': row[3] if row[3] else 'momentum',
                        'enabled': bool(row[4]) if row[4] is not None else False,
                        'final_score': float(row[5]) if row[5] is not None else 0.0,
                        'total_trades': int(row[6]) if row[6] is not None else 0,
                        'win_rate': float(row[7]) if row[7] is not None else 0.0,
                        'total_return': float(row[8]) if row[8] is not None else 0.0,
                        'generation': int(row[9]) if len(row) > 9 and row[9] is not None else 1,
                        'cycle': int(row[10]) if len(row) > 10 and row[10] is not None else 1,
                        'created_at': row[11].isoformat() if len(row) > 11 and row[11] else None,
                        'updated_at': row[12].isoformat() if len(row) > 12 and row[12] else None
                    }
                    strategies.append(strategy)
                except Exception as row_error:
                    self.logger.error(f"❌ 处理策略行 {i} 失败: {row_error}, 行数据: {row}")
                    continue
            
            cursor.close()
            conn.close()
            
            self.logger.info(f"✅ 成功获取 {len(strategies)} 个显示策略")
            return strategies
                
        except Exception as e:
            self.logger.error(f"❌ 获取显示策略失败: {e}")
            import traceback
            traceback.print_exc()
            return []


# 全局实例
strategy_manager = AdvancedStrategyManager()
    
def start_strategy_management():
    """启动策略管理线程"""
    if not strategy_manager.running:
        management_thread = threading.Thread(
            target=strategy_manager.run_automatic_management,
            daemon=True
        )
        management_thread.start()
        return True
    return False

def stop_strategy_management():
    """停止策略管理"""
    strategy_manager.stop()

if __name__ == "__main__":
    # 测试运行
    print("🚀 测试高级策略管理器...")
        
    # 获取统计信息
    stats = strategy_manager.get_strategy_statistics()
    print(f"📊 策略统计: {stats}")
    
    # 淘汰表现差的策略
    eliminated = strategy_manager.eliminate_poor_strategies()
    print(f"🗑️ 已淘汰 {eliminated} 个策略")
    
    # 选择顶级策略
    top_strategies = strategy_manager.select_top_strategies_for_trading()
    print(f"🏆 顶级策略: {len(top_strategies)} 个")
    
    # 获取显示策略
    display_strategies = strategy_manager.get_display_strategies(5)
    print(f"📱 前端显示策略: {len(display_strategies)} 个") 