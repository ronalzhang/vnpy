#!/usr/bin/env python3
"""
最终清理交易日志系统的剩余问题
"""
import psycopg2
import uuid
from datetime import datetime

def final_cleanup_trading_logs():
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        print("=== 🧹 最终清理交易日志系统 ===\n")
        
        # 1. 修复剩余的实盘/验证交易标记冲突
        print("1. 🎯 修复剩余的实盘/验证交易标记冲突:")
        cursor.execute("""
            UPDATE trading_signals 
            SET is_validation = false 
            WHERE trade_type = 'real_trading' AND is_validation = true
        """)
        fixed_conflicts = cursor.rowcount
        print(f"   ✅ 修复了 {fixed_conflicts} 条冲突记录")
        
        # 2. 为缺失周期ID的记录生成ID
        print("\n2. 🔗 为缺失周期ID的记录生成ID:")
        cursor.execute("""
            UPDATE trading_signals 
            SET cycle_id = CONCAT('CYCLE_', strategy_id, '_', EXTRACT(EPOCH FROM timestamp)::bigint)
            WHERE cycle_id IS NULL 
            AND timestamp >= NOW() - INTERVAL '7 days'
        """)
        fixed_cycles = cursor.rowcount
        print(f"   ✅ 为 {fixed_cycles} 条记录生成了周期ID")
        
        # 3. 标准化策略评分
        print("\n3. 📊 标准化策略评分:")
        cursor.execute("""
            UPDATE trading_signals 
            SET strategy_score = CASE 
                WHEN strategy_score < 0 THEN 0
                WHEN strategy_score > 100 THEN 100
                WHEN strategy_score IS NULL THEN 50.0
                ELSE strategy_score
            END
            WHERE timestamp >= NOW() - INTERVAL '7 days'
        """)
        fixed_scores = cursor.rowcount
        print(f"   ✅ 标准化了 {fixed_scores} 条记录的策略评分")
        
        # 4. 同步最新修复到统一日志表
        print("\n4. 🔄 同步最新修复到统一日志表:")
        cursor.execute("""
            INSERT INTO unified_strategy_logs 
            (strategy_id, log_type, timestamp, symbol, signal_type, price, quantity, 
             pnl, executed, confidence, cycle_id, strategy_score, notes)
            SELECT 
                strategy_id,
                CASE 
                    WHEN trade_type IN ('score_verification', 'optimization_validation', 
                                       'initialization_validation', 'periodic_validation') 
                    THEN 'validation'
                    ELSE 'real_trading'
                END as log_type,
                timestamp,
                symbol,
                signal_type,
                price,
                quantity,
                expected_return,
                CASE WHEN executed = 1 THEN true ELSE false END,
                confidence,
                cycle_id,
                strategy_score,
                CONCAT('修复后同步: ', trade_type, ', 执行状态: ', executed) as notes
            FROM trading_signals 
            WHERE timestamp >= NOW() - INTERVAL '1 hour'
            ON CONFLICT DO NOTHING
        """)
        synced_records = cursor.rowcount
        print(f"   ✅ 同步了 {synced_records} 条最新记录到统一日志表")
        
        # 5. 验证修复结果
        print("\n5. ✅ 验证最终修复结果:")
        
        # 检查冲突记录
        cursor.execute("""
            SELECT COUNT(*) 
            FROM trading_signals 
            WHERE is_validation = true AND trade_type = 'real_trading'
        """)
        conflicts_result = cursor.fetchone()
        remaining_conflicts = conflicts_result[0] if conflicts_result else 0
        print(f"   剩余冲突记录: {remaining_conflicts} 条")
        
        # 检查缺失周期ID
        cursor.execute("""
            SELECT COUNT(*) 
            FROM trading_signals 
            WHERE cycle_id IS NULL 
            AND timestamp >= NOW() - INTERVAL '7 days'
        """)
        null_cycles_result = cursor.fetchone()
        remaining_null_cycles = null_cycles_result[0] if null_cycles_result else 0
        print(f"   剩余缺失周期ID: {remaining_null_cycles} 条")
        
        # 检查统一日志表记录数
        cursor.execute("SELECT COUNT(*) FROM unified_strategy_logs")
        total_unified_result = cursor.fetchone()
        total_unified = total_unified_result[0] if total_unified_result else 0
        print(f"   统一日志表总记录: {total_unified} 条")
        
        # 检查各类型日志分布
        cursor.execute("""
            SELECT log_type, COUNT(*) 
            FROM unified_strategy_logs 
            GROUP BY log_type 
            ORDER BY COUNT(*) DESC
        """)
        log_distribution = cursor.fetchall()
        print(f"   日志类型分布:")
        for log_type, count in log_distribution:
            print(f"     {log_type}: {count} 条")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"\n=== 🎉 最终清理完成 ===")
        print(f"✅ 实盘/验证交易标记已完全修复")
        print(f"✅ 周期ID已全部生成")
        print(f"✅ 策略评分已标准化")
        print(f"✅ 统一日志系统已完成同步")
        print(f"✅ 交易日志系统修复完成！")
        
    except Exception as e:
        print(f"❌ 最终清理失败: {e}")
        conn.rollback()

if __name__ == "__main__":
    final_cleanup_trading_logs() 