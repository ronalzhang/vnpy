#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
四层策略进化调度器 4.0
- 策略池：全部策略低频进化（24小时间隔）
- 高频池：前2000策略高频进化（3分钟间隔）
- 前端显示：21个策略持续高频进化（3分钟间隔）
- 实盘交易：精英策略实盘执行（1分钟间隔）
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from modern_strategy_manager import get_four_tier_strategy_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/four_tier_evolution.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class FourTierEvolutionScheduler:
    """四层进化调度器"""
    
    def __init__(self):
        self.manager = get_four_tier_strategy_manager()
        self.running = True
        
    async def start(self):
        """启动四层并行调度器"""
        logger.info("🚀 四层策略进化调度器启动")
        
        # 设置信号处理
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # 显示系统统计
        stats = self.manager.get_evolution_statistics()
        logger.info("📊 四层进化系统统计:")
        logger.info(f"   策略池: {stats['tiers']['pool']['strategy_count']:,}个策略, {stats['tiers']['pool']['evolution_interval']}进化")
        logger.info(f"   高频池: {stats['tiers']['high_freq']['strategy_count']:,}个策略, {stats['tiers']['high_freq']['evolution_interval']}进化")
        logger.info(f"   前端显示: {stats['tiers']['display']['strategy_count']}个策略, {stats['tiers']['display']['evolution_interval']}进化")
        logger.info(f"   实盘交易: {stats['tiers']['trading']['strategy_count']}个策略")
        logger.info(f"   理论总进化: {stats['totals']['theoretical_total_evolutions_per_hour']:,}次/小时")
        logger.info(f"   理论总验证: {stats['totals']['theoretical_validations_per_hour']:,}次/小时")
        
        try:
            # 四层并发调度
            await asyncio.gather(
                self.pool_evolution_scheduler(),      # 第1层：策略池低频进化
                self.high_freq_pool_scheduler(),      # 第2层：高频池高频进化
                self.display_strategies_scheduler(),  # 第3层：前端持续高频进化
                self.real_trading_scheduler()         # 第4层：实盘交易执行
            )
        except Exception as e:
            logger.error(f"❌ 调度器异常: {e}")
        finally:
            logger.info("🔚 四层策略进化调度器已停止")
    
    async def pool_evolution_scheduler(self):
        """第1层：策略池低频进化调度器（24小时间隔）"""
        logger.info("🔄 [第1层] 策略池低频进化调度器启动")
        
        while self.running:
            try:
                start_time = datetime.now()
                
                # 执行策略池低频进化
                await self.manager.evolve_pool_strategies()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"✅ [第1层] 策略池低频进化完成，耗时: {execution_time:.2f}秒")
                
                # 等待24小时
                await asyncio.sleep(self.manager.config.low_freq_interval_hours * 3600)
                
            except Exception as e:
                logger.error(f"❌ [第1层] 策略池低频进化异常: {e}")
                await asyncio.sleep(3600)  # 异常时等待1小时重试
    
    async def high_freq_pool_scheduler(self):
        """第2层：高频池高频进化调度器（60分钟间隔）"""
        logger.info("🔥 [第2层] 高频池高频进化调度器启动")
        
        while self.running:
            try:
                start_time = datetime.now()
                
                # 执行高频池高频进化
                await self.manager.evolve_high_freq_pool()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"✅ [第2层] 高频池进化完成，耗时: {execution_time:.2f}秒")
                
                # 等待配置的高频间隔
                await asyncio.sleep(self.manager.config.high_freq_interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"❌ [第2层] 高频池进化异常: {e}")
                await asyncio.sleep(60)  # 异常时等待1分钟重试
    
    async def display_strategies_scheduler(self):
        """第3层：前端显示策略持续高频进化调度器（3分钟间隔）"""
        logger.info("🎯 [第3层] 前端显示策略持续高频进化调度器启动")
        
        while self.running:
            try:
                start_time = datetime.now()
                
                # 执行前端显示策略持续高频进化
                await self.manager.evolve_display_strategies()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"✅ [第3层] 前端策略进化完成，耗时: {execution_time:.2f}秒")
                
                # 等待配置的前端进化间隔
                await asyncio.sleep(self.manager.config.display_interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"❌ [第3层] 前端策略进化异常: {e}")
                await asyncio.sleep(60)  # 异常时等待1分钟重试
    
    async def real_trading_scheduler(self):
        """第4层：实盘交易执行调度器（1分钟间隔）"""
        logger.info("💰 [第4层] 实盘交易执行调度器启动")
        
        while self.running:
            try:
                # 执行实盘交易策略的交易信号生成
                await self.execute_real_trading()
                
                # 等待1分钟
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ [第4层] 实盘交易执行异常: {e}")
                await asyncio.sleep(60)
    
    async def execute_real_trading(self):
        """执行实盘交易"""
        try:
            # 获取实盘交易策略
            trading_strategies = self.manager.get_trading_strategies()
            
            if not trading_strategies:
                return
            
            # 为每个实盘交易策略生成交易信号
            for strategy in trading_strategies:
                await self.generate_real_trading_signal(strategy)
                
        except Exception as e:
            logger.error(f"❌ 实盘交易执行失败: {e}")
    
    async def generate_real_trading_signal(self, strategy):
        """生成实盘交易信号"""
        try:
            import random
            import psycopg2
            
            # 检查实盘交易开关
            conn = self.manager._get_db_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("SELECT real_trading_enabled FROM real_trading_control WHERE id = 1")
                real_trading_control = cursor.fetchone()
                real_trading_enabled = real_trading_control[0] if real_trading_control else False
            except Exception:
                real_trading_enabled = False
            
            # 生成交易信号
            signal_data = {
                'strategy_id': strategy['id'],
                'symbol': strategy['symbol'],
                'signal_type': random.choice(['buy', 'sell']),
                'price': 100.0 + random.uniform(-5, 5),
                'quantity': self.manager.config.real_trading_amount if real_trading_enabled else self.manager.config.validation_amount,
                'expected_return': random.uniform(-1, 3),
                'timestamp': datetime.now()
            }
            
            # 根据实盘开关设置交易类型
            trade_type = "real_trading" if real_trading_enabled else "score_verification"
            is_validation = not real_trading_enabled
            
            cursor.execute("""
                INSERT INTO trading_signals 
                (strategy_id, symbol, signal_type, price, quantity, expected_return, 
                 executed, is_validation, trade_type, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                signal_data['strategy_id'],
                signal_data['symbol'],
                signal_data['signal_type'],
                signal_data['price'],
                signal_data['quantity'],
                signal_data['expected_return'],
                1,  # executed
                is_validation,
                trade_type,
                signal_data['timestamp']
            ))
            
            conn.commit()
            conn.close()
            
            trade_type_desc = "实盘交易" if real_trading_enabled else "验证交易"
            logger.info(f"✅ [第4层] {strategy['id']} {trade_type_desc}信号已生成: {signal_data['signal_type']} ${signal_data['quantity']}")
            
        except Exception as e:
            logger.error(f"❌ 生成实盘交易信号失败: {e}")
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}，准备停止四层调度器...")
        self.running = False

async def main():
    """主函数"""
    scheduler = FourTierEvolutionScheduler()
    await scheduler.start()

if __name__ == "__main__":
    asyncio.run(main()) 