#!/usr/bin/env python3
"""
检查新生成的日志是否修复了trade_type问题
"""
import psycopg2
from datetime import datetime

def check_new_logs():
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        print("=== 检查最新生成的交易日志 ===")
        
        # 检查最近5分钟的日志
        cursor.execute("""
            SELECT strategy_id, trade_type, is_validation, signal_type, timestamp, strategy_score
            FROM trading_signals 
            WHERE timestamp >= NOW() - INTERVAL '5 minutes' 
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        recent_logs = cursor.fetchall()
        
        print(f"最近5分钟新增日志: {len(recent_logs)} 条")
        for i, log in enumerate(recent_logs, 1):
            strategy_id, trade_type, is_validation, signal_type, timestamp, strategy_score = log
            print(f"  {i}. {strategy_id} | {trade_type} | 验证:{is_validation} | {signal_type} | 评分:{strategy_score} | {timestamp}")
        
        # 检查是否还有新的冲突
        cursor.execute("""
            SELECT COUNT(*) 
            FROM trading_signals 
            WHERE is_validation = true AND trade_type = 'real_trading' 
            AND timestamp >= NOW() - INTERVAL '5 minutes'
        """)
        new_conflicts_result = cursor.fetchone()
        new_conflicts = new_conflicts_result[0] if new_conflicts_result else 0
        
        print(f"\n新产生的冲突记录: {new_conflicts} 条")
        
        # 检查统一日志表是否同步更新
        cursor.execute("""
            SELECT COUNT(*) 
            FROM unified_strategy_logs 
            WHERE timestamp >= NOW() - INTERVAL '5 minutes'
        """)
        unified_logs_result = cursor.fetchone()
        unified_logs_count = unified_logs_result[0] if unified_logs_result else 0
        
        print(f"统一日志表新增记录: {unified_logs_count} 条")
        
        # 总体数据质量评估
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(CASE WHEN is_validation = true AND trade_type = 'real_trading' THEN 1 END) as conflicts,
                COUNT(CASE WHEN trade_type IS NULL THEN 1 END) as missing_trade_type,
                COUNT(CASE WHEN cycle_id IS NULL THEN 1 END) as missing_cycle_id
            FROM trading_signals 
            WHERE timestamp >= NOW() - INTERVAL '1 day'
        """)
        quality_result = cursor.fetchone()
        if quality_result:
            total, conflicts, missing_type, missing_cycle = quality_result
            print(f"\n📊 今日数据质量评估:")
            print(f"  总记录: {total} 条")
            print(f"  冲突记录: {conflicts} 条 ({conflicts/total*100:.1f}%)" if total > 0 else "  冲突记录: 0 条")
            print(f"  缺失trade_type: {missing_type} 条")
            print(f"  缺失cycle_id: {missing_cycle} 条")
        
        cursor.close()
        conn.close()
        
        # 修复效果评估
        if new_conflicts == 0:
            print("\n✅ 修复成功！新生成的日志没有冲突问题")
        else:
            print(f"\n❌ 仍有问题！新生成了 {new_conflicts} 条冲突记录")
            
        return new_conflicts == 0
        
    except Exception as e:
        print(f"检查失败: {e}")
        return False

if __name__ == "__main__":
    check_new_logs() 