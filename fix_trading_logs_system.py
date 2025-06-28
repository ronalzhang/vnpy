#!/usr/bin/env python3
"""
全面修复交易日志系统的所有问题
"""
import psycopg2
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

def fix_trading_logs_system():
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        print("=== 🔧 开始修复交易日志系统 ===\n")
        
        # 1. 修复实盘/验证交易标记冲突
        print("1. 🎯 修复实盘/验证交易标记冲突:")
        
        # 修复trade_type为real_trading但is_validation=true的记录
        cursor.execute("""
            UPDATE trading_signals 
            SET is_validation = false 
            WHERE trade_type = 'real_trading' AND is_validation = true
        """)
        fixed_real_trading = cursor.rowcount
        print(f"   ✅ 修复了 {fixed_real_trading} 条实盘交易记录的标记")
        
        # 确保score_verification类型的记录标记为验证交易
        cursor.execute("""
            UPDATE trading_signals 
            SET is_validation = true, trade_type = 'score_verification'
            WHERE trade_type = 'score_verification'
        """)
        fixed_validation = cursor.rowcount
        print(f"   ✅ 统一了 {fixed_validation} 条验证交易记录的标记")
        
        # 2. 创建统一日志表
        print("\n2. 📋 创建统一日志表:")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS unified_strategy_logs (
                id BIGSERIAL PRIMARY KEY,
                strategy_id TEXT NOT NULL,
                log_type TEXT NOT NULL, -- 'real_trading', 'validation', 'evolution', 'system_operation'
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                symbol TEXT,
                signal_type TEXT, -- 'buy', 'sell', 'optimization', 'evolution'
                price DECIMAL(15,8),
                quantity DECIMAL(15,8),
                pnl DECIMAL(15,8) DEFAULT 0,
                executed BOOLEAN DEFAULT false,
                confidence DECIMAL(5,2) DEFAULT 0,
                cycle_id TEXT,
                strategy_score DECIMAL(5,2) DEFAULT 50.0,
                
                -- 进化相关字段
                evolution_type TEXT,
                old_parameters JSONB,
                new_parameters JSONB,
                trigger_reason TEXT,
                target_success_rate DECIMAL(5,2),
                improvement DECIMAL(8,4),
                success BOOLEAN,
                
                -- 额外信息
                notes TEXT,
                metadata JSONB
            )
        """)
        print("   ✅ 统一日志表 unified_strategy_logs 创建完成")
        
        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_unified_logs_strategy_id ON unified_strategy_logs(strategy_id)",
            "CREATE INDEX IF NOT EXISTS idx_unified_logs_log_type ON unified_strategy_logs(log_type)",  
            "CREATE INDEX IF NOT EXISTS idx_unified_logs_timestamp ON unified_strategy_logs(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_unified_logs_cycle_id ON unified_strategy_logs(cycle_id)"
        ]
        for idx_sql in indexes:
            cursor.execute(idx_sql)
        print("   ✅ 统一日志表索引创建完成")
        
        # 3. 迁移现有数据到统一日志表
        print("\n3. 📦 迁移现有数据到统一日志表:")
        
        # 迁移交易信号数据
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
                CONCAT('来源: trading_signals, 交易类型: ', trade_type) as notes
            FROM trading_signals 
            WHERE timestamp >= NOW() - INTERVAL '7 days'
            ON CONFLICT DO NOTHING
        """)
        migrated_signals = cursor.rowcount
        print(f"   ✅ 迁移了 {migrated_signals} 条交易信号记录")
        
        # 迁移进化历史数据
        cursor.execute("""
            INSERT INTO unified_strategy_logs 
            (strategy_id, log_type, timestamp, signal_type, evolution_type, 
             old_parameters, new_parameters, trigger_reason, improvement, success, notes)
            SELECT 
                strategy_id,
                'evolution' as log_type,
                created_time,
                'evolution' as signal_type,
                evolution_type,
                old_parameters::jsonb,
                new_parameters::jsonb,
                evolution_reason,
                improvement,
                success,
                CONCAT('世代进化: ', notes) as notes
            FROM strategy_evolution_history 
            WHERE created_time >= NOW() - INTERVAL '7 days'
            ON CONFLICT DO NOTHING
        """)
        migrated_evolution = cursor.rowcount
        print(f"   ✅ 迁移了 {migrated_evolution} 条进化历史记录")
        
        # 迁移策略优化日志数据
        cursor.execute("""
            INSERT INTO unified_strategy_logs 
            (strategy_id, log_type, timestamp, notes, strategy_score)
            SELECT 
                strategy_id,
                'optimization' as log_type,
                timestamp,
                CONCAT('优化结果: ', optimization_result) as notes,
                COALESCE(new_score, 50.0) as strategy_score
            FROM strategy_optimization_logs 
            WHERE timestamp >= NOW() - INTERVAL '7 days'
            ON CONFLICT DO NOTHING
        """)
        migrated_optimization = cursor.rowcount
        print(f"   ✅ 迁移了 {migrated_optimization} 条策略优化记录")
        
        # 4. 生成缺失的周期ID
        print("\n4. 🔗 生成缺失的周期ID:")
        cursor.execute("""
            SELECT id, strategy_id, timestamp 
            FROM trading_signals 
            WHERE cycle_id IS NULL 
            AND timestamp >= NOW() - INTERVAL '7 days'
            ORDER BY strategy_id, timestamp
        """)
        null_cycle_records = cursor.fetchall()
        
        updated_cycles = 0
        for record in null_cycle_records:
            signal_id, strategy_id, timestamp = record
            cycle_id = f"CYCLE_{strategy_id}_{int(timestamp.timestamp() * 1000)}"
            
            cursor.execute("""
                UPDATE trading_signals 
                SET cycle_id = %s 
                WHERE id = %s
            """, (cycle_id, signal_id))
            updated_cycles += 1
            
        print(f"   ✅ 为 {updated_cycles} 条记录生成了周期ID")
        
        # 5. 修复策略评分
        print("\n5. 📊 修复策略评分:")
        cursor.execute("""
            UPDATE trading_signals ts
            SET strategy_score = COALESCE(s.final_score, 50.0)
            FROM strategies s 
            WHERE ts.strategy_id = s.id 
            AND ts.strategy_score = 50.0
            AND s.final_score IS NOT NULL
            AND s.final_score != 50.0
        """)
        updated_scores = cursor.rowcount
        print(f"   ✅ 更新了 {updated_scores} 条记录的策略评分")
        
        # 6. 创建日志记录函数
        print("\n6. 🛠️ 创建日志记录存储过程:")
        cursor.execute("""
            CREATE OR REPLACE FUNCTION log_strategy_action(
                p_strategy_id TEXT,
                p_log_type TEXT,
                p_signal_type TEXT DEFAULT NULL,
                p_symbol TEXT DEFAULT NULL,
                p_price DECIMAL DEFAULT NULL,
                p_quantity DECIMAL DEFAULT NULL,
                p_pnl DECIMAL DEFAULT 0,
                p_executed BOOLEAN DEFAULT false,
                p_confidence DECIMAL DEFAULT 0,
                p_cycle_id TEXT DEFAULT NULL,
                p_notes TEXT DEFAULT NULL
            ) RETURNS BIGINT AS $$
            DECLARE
                log_id BIGINT;
            BEGIN
                INSERT INTO unified_strategy_logs 
                (strategy_id, log_type, signal_type, symbol, price, quantity, 
                 pnl, executed, confidence, cycle_id, notes)
                VALUES 
                (p_strategy_id, p_log_type, p_signal_type, p_symbol, p_price, 
                 p_quantity, p_pnl, p_executed, p_confidence, p_cycle_id, p_notes)
                RETURNING id INTO log_id;
                
                RETURN log_id;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ 日志记录存储过程创建完成")
        
        # 7. 验证修复结果
        print("\n7. ✅ 验证修复结果:")
        
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
        unified_result = cursor.fetchone()
        unified_log_count = unified_result[0] if unified_result else 0
        print(f"   统一日志表记录数: {unified_log_count} 条")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n=== 🎉 修复完成 ===")
        print("✅ 实盘/验证交易标记冲突已解决")
        print("✅ 统一日志表已创建并迁移数据")
        print("✅ 缺失的周期ID已生成")
        print("✅ 策略评分已修复")
        print("✅ 日志记录函数已创建")
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        if 'conn' in locals():
            conn.rollback()

if __name__ == "__main__":
    fix_trading_logs_system() 