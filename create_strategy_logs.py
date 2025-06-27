#!/usr/bin/env python3
"""
为策略创建测试交易日志记录
解决除第一个策略外其他策略都没有日志数据的问题
"""

import psycopg2
import random
from datetime import datetime, timedelta
import json

def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(
        host="localhost",
        database="quantitative",
        user="quant_user",
        password="123abc74531"
    )

def create_strategy_trade_logs():
    """为策略创建交易日志记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 获取所有策略（除了第一个已有数据的）
        cursor.execute("""
            SELECT id, name, symbol FROM strategies 
            WHERE id != (SELECT MIN(id) FROM strategies)
            ORDER BY id LIMIT 15
        """)
        strategies = cursor.fetchall()
        
        print(f"为 {len(strategies)} 个策略创建交易日志...")
        
        for strategy_id, strategy_name, symbol in strategies:
            print(f"处理策略: {strategy_name}")
            
            # 为每个策略创建5-10条交易记录
            trade_count = random.randint(5, 10)
            
            for i in range(trade_count):
                # 生成随机时间（最近24小时内）
                timestamp = datetime.now() - timedelta(
                    hours=random.randint(1, 24),
                    minutes=random.randint(0, 59)
                )
                
                # 随机信号类型
                signal_type = random.choice(['BUY', 'SELL'])
                
                # 随机价格（基于BTC价格范围）
                if 'BTC' in symbol:
                    price = round(random.uniform(95000, 97000), 2)
                elif 'ETH' in symbol:
                    price = round(random.uniform(3200, 3400), 2)
                else:
                    price = round(random.uniform(0.1, 100), 4)
                
                # 随机数量
                quantity = round(random.uniform(0.001, 0.01), 6)
                
                # 随机置信度
                confidence = round(random.uniform(50, 80), 1)
                
                # 随机执行状态
                status = random.choice(['executed', 'executed', 'executed', 'pending', 'failed'])
                
                # 计算盈亏
                if status == 'executed':
                    pnl = round(random.uniform(-2, 5), 4)
                else:
                    pnl = 0
                
                # 插入交易记录
                cursor.execute("""
                    INSERT INTO strategy_trades 
                    (strategy_id, timestamp, signal_type, price, quantity, confidence, 
                     execution_status, pnl, trade_type, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    strategy_id, timestamp, signal_type, price, quantity, 
                    confidence, status, pnl, 'validation', 
                    f'模拟交易 - {strategy_name}'
                ))
            
            # 为每个策略创建2-3条优化记录
            optimization_count = random.randint(2, 3)
            
            for i in range(optimization_count):
                # 生成随机时间
                timestamp = datetime.now() - timedelta(
                    hours=random.randint(6, 48),
                    minutes=random.randint(0, 59)
                )
                
                # 随机优化类型
                optimization_type = random.choice([
                    'parameter_adjustment', 'threshold_update', 
                    'stop_loss_update', 'take_profit_update'
                ])
                
                # 生成参数变更记录
                old_params = {
                    'rsi_period': random.randint(10, 16),
                    'ma_period': random.randint(18, 25),
                    'stop_loss': round(random.uniform(2, 4), 1)
                }
                
                new_params = {
                    'rsi_period': random.randint(12, 20),
                    'ma_period': random.randint(20, 30),
                    'stop_loss': round(random.uniform(3, 5), 1)
                }
                
                trigger_reason = random.choice([
                    '成功率下降', '连续亏损', '市场环境变化', 
                    '定期优化', '风险控制'
                ])
                
                target_success_rate = round(random.uniform(65, 85), 1)
                
                # 插入优化记录
                cursor.execute("""
                    INSERT INTO strategy_optimization_logs 
                    (strategy_id, timestamp, optimization_type, old_parameters, 
                     new_parameters, trigger_reason, target_success_rate)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    strategy_id, timestamp, optimization_type, 
                    json.dumps(old_params), json.dumps(new_params),
                    trigger_reason, target_success_rate
                ))
            
            print(f"  - 创建了 {trade_count} 条交易记录和 {optimization_count} 条优化记录")
        
        conn.commit()
        print(f"\n✅ 成功为 {len(strategies)} 个策略创建了交易日志记录")
        
    except Exception as e:
        print(f"❌ 创建交易日志失败: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    create_strategy_trade_logs() 