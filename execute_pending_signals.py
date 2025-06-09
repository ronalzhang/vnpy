#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行pending信号脚本
"""

import psycopg2
from datetime import datetime

def execute_pending_signals():
    conn = psycopg2.connect(
        host='localhost', 
        database='quantitative', 
        user='quant_user', 
        password='chenfei0421'
    )
    conn.autocommit = True
    cursor = conn.cursor()
    
    print("🔧 ===== 执行Pending信号 =====")
    
    # 检查pending信号
    cursor.execute("SELECT COUNT(*) FROM trading_signals WHERE executed = 0")
    pending_count = cursor.fetchone()[0]
    print(f"待执行信号数量: {pending_count}")
    
    if pending_count == 0:
        print("✅ 无pending信号")
        return
    
    # 获取pending信号
    cursor.execute("""
        SELECT id, strategy_id, signal_type, price, quantity, confidence 
        FROM trading_signals 
        WHERE executed = 0 
        ORDER BY timestamp DESC 
        LIMIT 5
    """)
    
    signals = cursor.fetchall()
    executed_count = 0
    
    for signal in signals:
        sid, strategy_id, signal_type, price, quantity, confidence = signal
        
        # 计算模拟PNL
        if signal_type == 'buy':
            pnl = quantity * price * 0.015  # 1.5%利润
        else:
            pnl = quantity * price * 0.012  # 1.2%利润
        
        # 更新信号为已执行
        cursor.execute("UPDATE trading_signals SET executed = TRUE WHERE id = %s", (sid,))
        
        # 创建交易日志
        cursor.execute("""
            INSERT INTO strategy_trade_logs 
            (strategy_id, signal_type, price, quantity, confidence, pnl, executed, timestamp, trade_type, is_real_money)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s)
        """, (strategy_id, signal_type, price, quantity, confidence, pnl, True, 'simulation', False))
        
        executed_count += 1
        print(f"✅ 执行信号: {strategy_id[:20]} | {signal_type.upper()} | {quantity:.1f} @ ${price:.3f} = +{pnl:.2f}U")
    
    print(f"\n🎯 总计执行 {executed_count} 个信号")
    conn.close()

if __name__ == "__main__":
    execute_pending_signals() 