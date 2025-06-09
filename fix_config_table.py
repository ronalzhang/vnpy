#!/usr/bin/env python3
import psycopg2

try:
    conn = psycopg2.connect(
        host='localhost',
        database='quantitative', 
        user='quant_user',
        password='quant123'
    )
    cursor = conn.cursor()
    
    # 创建策略管理配置表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS strategy_management_config (
            id SERIAL PRIMARY KEY,
            config_key VARCHAR(50) UNIQUE NOT NULL,
            config_value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 插入默认配置
    default_configs = [
        ('evolutionInterval', '10'),
        ('maxStrategies', '20'),
        ('minTrades', '10'),
        ('minWinRate', '65'),
        ('minProfit', '0'),
        ('maxDrawdown', '10'),
        ('minSharpeRatio', '1.0'),
        ('maxPositionSize', '100'),
        ('stopLossPercent', '5'),
        ('eliminationDays', '7'),
        ('minScore', '50')
    ]
    
    for key, value in default_configs:
        cursor.execute('''
            INSERT INTO strategy_management_config (config_key, config_value)
            VALUES (%s, %s)
            ON CONFLICT (config_key) DO NOTHING
        ''', (key, value))
    
    conn.commit()
    print('策略管理配置表创建成功')
    print('默认配置插入完成')
    
    # 验证创建结果
    cursor.execute('SELECT config_key, config_value FROM strategy_management_config')
    rows = cursor.fetchall()
    print(f'当前配置数量: {len(rows)}')
    for row in rows:
        print(f'  {row[0]}: {row[1]}')
    
    conn.close()
    
except Exception as e:
    print(f'数据库操作失败: {e}') 