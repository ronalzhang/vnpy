#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
策略进化调度器启动脚本
- 每3分钟进化前端显示策略
- 执行验证交易和真实交易
- 更新策略参数和评分
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from modern_strategy_manager import get_modern_strategy_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/evolution_scheduler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class EvolutionScheduler:
    """进化调度器"""
    
    def __init__(self):
        self.manager = get_modern_strategy_manager()
        self.running = True
        
    async def start(self):
        """启动调度器"""
        logger.info("🚀 策略进化调度器启动")
        
        # 设置信号处理
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        try:
            # 并发运行两个调度器
            await asyncio.gather(
                self.frontend_evolution_scheduler(),
                self.pool_evolution_scheduler(),
                self.trading_executor_scheduler()
            )
        except Exception as e:
            logger.error(f"❌ 调度器异常: {e}")
        finally:
            logger.info("🔚 策略进化调度器已停止")
    
    async def frontend_evolution_scheduler(self):
        """前端策略高频进化调度器（每3分钟）"""
        logger.info("🔄 前端策略高频进化调度器启动")
        
        while self.running:
            try:
                start_time = datetime.now()
                
                # 执行前端策略进化
                await self.manager.evolve_display_strategies()
                
                # 记录执行时间
                execution_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"✅ 前端策略进化完成，耗时: {execution_time:.2f}秒")
                
                # 等待3分钟
                await asyncio.sleep(self.manager.config.evolution_interval * 60)
                
            except Exception as e:
                logger.error(f"❌ 前端策略进化异常: {e}")
                await asyncio.sleep(60)  # 异常时等待1分钟重试
    
    async def pool_evolution_scheduler(self):
        """策略池定期进化调度器（每24小时）"""
        logger.info("🔄 策略池定期进化调度器启动")
        
        while self.running:
            try:
                start_time = datetime.now()
                
                # 执行策略池进化
                await self.manager.evolve_pool_strategies()
                
                # 记录执行时间
                execution_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"✅ 策略池进化完成，耗时: {execution_time:.2f}秒")
                
                # 等待24小时
                await asyncio.sleep(self.manager.config.pool_evolution_hours * 3600)
                
            except Exception as e:
                logger.error(f"❌ 策略池进化异常: {e}")
                await asyncio.sleep(3600)  # 异常时等待1小时重试
    
    async def trading_executor_scheduler(self):
        """交易执行调度器（每分钟检查）"""
        logger.info("💰 交易执行调度器启动")
        
        while self.running:
            try:
                # 执行真实交易策略的交易
                await self.execute_real_trading()
                
                # 等待1分钟
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ 交易执行异常: {e}")
                await asyncio.sleep(60)
    
    async def execute_real_trading(self):
        """执行真实交易"""
        try:
            # 获取真实交易策略
            trading_strategies = self.manager.select_trading_strategies()
            
            if not trading_strategies:
                return
            
            # 为每个真实交易策略生成交易信号
            for strategy in trading_strategies:
                await self.generate_trading_signal(strategy, is_real=True)
                
        except Exception as e:
            logger.error(f"❌ 真实交易执行失败: {e}")
    
    async def generate_trading_signal(self, strategy, is_real=False):
        """生成交易信号"""
        try:
            import random
            import psycopg2
            
            # 生成交易信号
            signal_data = {
                'strategy_id': strategy['id'],
                'symbol': strategy['symbol'],
                'signal_type': random.choice(['buy', 'sell']),
                'price': 100.0 + random.uniform(-5, 5),  # 模拟价格
                'quantity': self.manager.config.real_trading_amount if is_real else self.manager.config.validation_amount,
                'expected_return': random.uniform(-1, 3),  # 模拟收益
                'is_validation': not is_real,
                'executed': 1,
                'timestamp': datetime.now()
            }
            
            # 保存到数据库
            conn = self.manager._get_db_connection()
            cursor = conn.cursor()
            
            # 🔧 修复：正确设置trade_type和is_validation字段
            # 🔧 修复：检查全局实盘交易开关，如果关闭则强制为验证交易
            try:
                cursor.execute("SELECT real_trading_enabled FROM real_trading_control WHERE id = 1")
                real_trading_control = cursor.fetchone()
                real_trading_enabled = real_trading_control[0] if real_trading_control else False
                
                # 如果实盘交易未启用，所有交易都应该是验证交易
                if not real_trading_enabled:
                    trade_type = "score_verification"
                    is_real = False  # 强制设为验证交易
                else:
                    trade_type = "real_trading" if is_real else "score_verification"
            except Exception as e:
                print(f"⚠️ 无法检查实盘交易开关，默认为验证交易: {e}")
                trade_type = "score_verification"
                is_real = False
            is_validation = not is_real
            
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
                signal_data['executed'],
                is_validation,
                trade_type,
                signal_data['timestamp']
            ))
            
            conn.commit()
            conn.close()
            
            trade_type = "真实交易" if is_real else "验证交易"
            logger.info(f"✅ {strategy['id']} {trade_type}信号已生成: {signal_data['signal_type']} ${signal_data['quantity']}")
            
        except Exception as e:
            logger.error(f"❌ 生成交易信号失败: {e}")
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}，准备停止调度器...")
        self.running = False

async def main():
    """主函数"""
    scheduler = EvolutionScheduler()
    await scheduler.start()

if __name__ == "__main__":
    asyncio.run(main()) 