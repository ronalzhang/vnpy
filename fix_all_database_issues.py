#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整数据库修复脚本
修复所有数据库字段和类型问题
"""

import psycopg2

def fix_all_database_issues():
    conn = psycopg2.connect(
        host='localhost',
        database='quantitative',
        user='quant_user',
        password='chenfei0421'
    )
    conn.autocommit = True
    cursor = conn.cursor()
    
    print("🔧 ===== 修复所有数据库问题 =====")
    
    # 1. 修复 trading_signals 表的 priority 字段
    try:
        cursor.execute("""
            ALTER TABLE trading_signals 
            ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'normal'
        """)
        print("✅ trading_signals.priority 字段已添加")
    except Exception as e:
        print(f"⚠️ 添加 priority 字段失败: {e}")
    
    # 2. 修复 executed 字段类型问题
    try:
        cursor.execute("""
            ALTER TABLE trading_signals 
            ALTER COLUMN executed TYPE boolean 
            USING CASE 
                WHEN executed = 1 OR executed = '1' OR executed = 'true' OR executed = true THEN true 
                ELSE false 
            END
        """)
        print("✅ trading_signals.executed 字段类型已修复为 boolean")
    except Exception as e:
        print(f"⚠️ 修复 executed 字段失败: {e}")
    
    # 3. 检查和添加其他可能缺失的字段
    try:
        cursor.execute("""
            ALTER TABLE strategies 
            ADD COLUMN IF NOT EXISTS notes TEXT DEFAULT ''
        """)
        print("✅ strategies.notes 字段已添加")
    except Exception as e:
        print(f"⚠️ 添加 notes 字段失败: {e}")
    
    # 4. 检查策略表字段
    try:
        cursor.execute("""
            ALTER TABLE strategies 
            ADD COLUMN IF NOT EXISTS trade_type VARCHAR(20) DEFAULT 'simulation'
        """)
        print("✅ strategies.trade_type 字段已添加")
    except Exception as e:
        print(f"⚠️ 添加 trade_type 字段失败: {e}")
    
    # 5. 检查交易日志表
    try:
        cursor.execute("""
            ALTER TABLE strategy_trade_logs 
            ADD COLUMN IF NOT EXISTS trade_type VARCHAR(20) DEFAULT 'simulation'
        """)
        print("✅ strategy_trade_logs.trade_type 字段已添加")
    except Exception as e:
        print(f"⚠️ 添加 trade_type 字段失败: {e}")
    
    # 6. 创建余额历史表（如果不存在）
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS balance_history (
                id SERIAL PRIMARY KEY,
                exchange VARCHAR(50),
                currency VARCHAR(10),
                balance DECIMAL(20,8),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ balance_history 表已创建")
    except Exception as e:
        print(f"⚠️ 创建 balance_history 表失败: {e}")
    
    # 7. 验证修复结果
    print("\n🔍 验证修复结果:")
    
    try:
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'trading_signals'")
        columns = [row[0] for row in cursor.fetchall()]
        print(f"trading_signals 表字段: {', '.join(columns)}")
    except Exception as e:
        print(f"❌ 查询表结构失败: {e}")
    
    # 8. 测试信号查询
    try:
        cursor.execute("SELECT COUNT(*) FROM trading_signals WHERE executed = false")
        count = cursor.fetchone()[0]
        print(f"✅ executed 字段查询测试成功，未执行信号数: {count}")
    except Exception as e:
        print(f"❌ executed 字段查询测试失败: {e}")
    
    conn.close()
    print("\n✅ 数据库修复完成!")

if __name__ == "__main__":
    fix_all_database_issues() 