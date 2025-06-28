#!/usr/bin/env python3
"""
检查交易日志系统的所有问题
"""
import psycopg2
from datetime import datetime, timedelta

def check_trading_logs_issues():
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        print("=== 🔍 交易日志系统问题诊断 ===\n")
        
        # 1. 检查交易记录的标记冲突
        print("1. 📊 检查实盘/验证交易标记冲突:")
        cursor.execute("""
            SELECT 
                trade_type, 
                is_validation, 
                COUNT(*) as count,
                COUNT(CASE WHEN executed = 1 THEN 1 END) as executed_count
            FROM trading_signals 
            WHERE timestamp >= NOW() - INTERVAL '1 day'
            GROUP BY trade_type, is_validation
            ORDER BY count DESC
        """)
        conflicts = cursor.fetchall()
        for row in conflicts:
            print(f"   类型: {row[0]}, 验证标记: {row[1]}, 总数: {row[2]}, 已执行: {row[3]}")
        
        # 2. 检查各种日志表的数据量
        print("\n2. 📈 检查各种日志表数据量:")
        
        # 策略优化日志
        cursor.execute("SELECT COUNT(*) FROM strategy_optimization_logs WHERE timestamp >= NOW() - INTERVAL '1 day'")
        opt_result = cursor.fetchone()
        opt_count = opt_result[0] if opt_result else 0
        print(f"   今日策略优化日志: {opt_count} 条")
        
        # 交易日志
        cursor.execute("SELECT COUNT(*) FROM strategy_trade_logs WHERE timestamp >= NOW() - INTERVAL '1 day'")
        trade_result = cursor.fetchone()
        trade_log_count = trade_result[0] if trade_result else 0
        print(f"   今日策略交易日志: {trade_log_count} 条")
        
        # 进化日志
        cursor.execute("SELECT COUNT(*) FROM strategy_evolution_history WHERE created_time >= NOW() - INTERVAL '1 day'")
        evo_result = cursor.fetchone()
        evo_count = evo_result[0] if evo_result else 0
        print(f"   今日策略进化日志: {evo_count} 条")
        
        # 3. 检查字段默认值问题
        print("\n3. ⚠️  字段默认值检查:")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM trading_signals 
            WHERE is_validation = true AND trade_type = 'real_trading'
            AND timestamp >= NOW() - INTERVAL '1 day'
        """)
        conflict_result = cursor.fetchone()
        conflict_count = conflict_result[0] if conflict_result else 0
        print(f"   冲突记录(验证=true但类型=实盘): {conflict_count} 条")
        
        # 4. 检查缺失的周期ID
        cursor.execute("""
            SELECT COUNT(*) 
            FROM trading_signals 
            WHERE cycle_id IS NULL AND timestamp >= NOW() - INTERVAL '1 day'
        """)
        null_cycle_result = cursor.fetchone()
        null_cycle_count = null_cycle_result[0] if null_cycle_result else 0
        print(f"   缺失周期ID的记录: {null_cycle_count} 条")
        
        # 5. 检查策略分数缺失
        cursor.execute("""
            SELECT COUNT(*) 
            FROM trading_signals 
            WHERE strategy_score IS NULL AND timestamp >= NOW() - INTERVAL '1 day'
        """)
        null_score_result = cursor.fetchone()
        null_score_count = null_score_result[0] if null_score_result else 0
        print(f"   缺失策略分数的记录: {null_score_count} 条")
        
        # 6. 检查最近的错误记录样本
        print("\n4. 🔍 最近的问题记录样本:")
        cursor.execute("""
            SELECT strategy_id, signal_type, trade_type, is_validation, executed, cycle_id, strategy_score
            FROM trading_signals 
            WHERE timestamp >= NOW() - INTERVAL '2 hours'
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        samples = cursor.fetchall()
        for i, row in enumerate(samples, 1):
            print(f"   {i}. {row[0]} | {row[1]} | 类型:{row[2]} | 验证:{row[3]} | 执行:{row[4]} | 周期:{row[5]} | 分数:{row[6]}")
            
        # 7. 检查unified_strategy_logs表是否存在
        print("\n5. 📋 统一日志表检查:")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'unified_strategy_logs'
            )
        """)
        unified_result = cursor.fetchone()
        unified_exists = unified_result[0] if unified_result else False
        print(f"   unified_strategy_logs表存在: {unified_exists}")
        
        if unified_exists:
            cursor.execute("SELECT COUNT(*) FROM unified_strategy_logs WHERE created_at >= NOW() - INTERVAL '1 day'")
            unified_count_result = cursor.fetchone()
            unified_count = unified_count_result[0] if unified_count_result else 0
            print(f"   今日统一日志记录: {unified_count} 条")
        
        cursor.close()
        conn.close()
        
        print("\n=== 🎯 问题总结 ===")
        print("1. 实盘/验证交易标记冲突 - 需要修复字段逻辑")
        print("2. 多个日志表数据不一致 - 需要统一日志记录机制") 
        print("3. 周期ID和分数字段缺失 - 需要修复数据写入逻辑")
        print("4. 需要创建统一的日志记录系统")
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")

if __name__ == "__main__":
    check_trading_logs_issues() 