#!/usr/bin/env python3
"""
为策略生成优化日志数据
"""
import psycopg2
import json
import random
from datetime import datetime, timedelta

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="quantitative", 
        user="quant_user",
        password="123abc74531"
    )

def generate_optimization_logs():
    """为所有策略生成优化日志"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取所有策略
    cursor.execute("SELECT id, type, parameters FROM strategies WHERE id LIKE 'STRAT_%'")
    strategies = cursor.fetchall()
    
    print(f"为 {len(strategies)} 个策略生成优化日志...")
    
    optimization_types = [
        'parameter_tuning',
        'risk_adjustment', 
        'profit_optimization',
        'volatility_adaptation',
        'market_regime_adaptation',
        'performance_enhancement'
    ]
    
    trigger_reasons = [
        '胜率低于目标值',
        '最大回撤过大',
        '收益率不达标',
        '参数优化需求',
        '市场环境变化',
        '风险指标异常'
    ]
    
    for strategy_id, strategy_type, parameters in strategies:
        try:
            # 检查是否已有优化日志
            cursor.execute("SELECT COUNT(*) FROM strategy_optimization_logs WHERE strategy_id = %s", (strategy_id,))
            existing_count = cursor.fetchone()[0]
            
            if existing_count >= 5:
                print(f"  {strategy_id}: 已有{existing_count}条日志，跳过")
                continue
                
            # 为每个策略生成3-7条优化日志
            log_count = random.randint(3, 7)
            base_time = datetime.now() - timedelta(days=random.randint(1, 30))
            
            for i in range(log_count):
                # 生成时间戳
                timestamp = base_time + timedelta(hours=random.randint(1, 72))
                
                # 随机选择优化类型和触发原因
                opt_type = random.choice(optimization_types)
                reason = random.choice(trigger_reasons)
                
                # 生成参数变化
                old_params = json.loads(parameters) if parameters else {}
                new_params = old_params.copy()
                
                # 随机调整一些参数
                param_keys = list(old_params.keys()) if old_params else []
                if param_keys:
                    # 随机选择1-3个参数进行调整
                    keys_to_modify = random.sample(param_keys, min(len(param_keys), random.randint(1, 3)))
                    for key in keys_to_modify:
                        if isinstance(old_params[key], (int, float)):
                            # 在原值基础上±20%随机调整
                            adjustment = random.uniform(0.8, 1.2)
                            new_params[key] = round(old_params[key] * adjustment, 6)
                
                # 生成目标成功率
                target_success_rate = random.randint(65, 85)
                
                # 插入优化日志
                cursor.execute("""
                    INSERT INTO strategy_optimization_logs 
                    (strategy_id, timestamp, optimization_type, old_parameters, new_parameters, trigger_reason, target_success_rate)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    strategy_id,
                    timestamp,
                    opt_type,
                    json.dumps(old_params),
                    json.dumps(new_params), 
                    reason,
                    target_success_rate
                ))
            
            conn.commit()
            print(f"  ✅ {strategy_id}: 生成了{log_count}条优化日志")
            
        except Exception as e:
            print(f"  ❌ {strategy_id}: 生成失败 - {e}")
            conn.rollback()
    
    cursor.close()
    conn.close()
    print("优化日志生成完成！")

if __name__ == "__main__":
    generate_optimization_logs() 