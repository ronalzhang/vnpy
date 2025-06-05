#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复数据库表名不匹配问题
"""

import sqlite3

def fix_table_names():
    """修复表名不匹配问题"""
    print("🔧 修复数据库表名...")
    
    conn = sqlite3.connect('quantitative.db')
    cursor = conn.cursor()
    
    try:
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trading_logs'")
        if cursor.fetchone():
            print("1. 重命名trading_logs为strategy_trade_logs...")
            
            # 创建正确的表结构
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_trade_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT NOT NULL,
                    signal_type TEXT,
                    price REAL,
                    quantity REAL,
                    confidence REAL,
                    executed BOOLEAN DEFAULT 1,
                    pnl REAL DEFAULT 0.0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 迁移数据
            cursor.execute('''
                INSERT INTO strategy_trade_logs (strategy_id, signal_type, price, quantity, confidence, executed, pnl, timestamp)
                SELECT strategy_id, signal_type, price, quantity, confidence, 
                       CASE WHEN execution_status = 'EXECUTED' THEN 1 ELSE 0 END,
                       pnl, timestamp
                FROM trading_logs
            ''')
            
            # 删除旧表
            cursor.execute('DROP TABLE trading_logs')
            print("   ✅ 表重命名完成")
        
        # 2. 修复优化日志表名
        print("2. 创建strategy_optimization_logs表...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_optimization_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT NOT NULL,
                optimization_type TEXT,
                before_params TEXT,
                after_params TEXT,
                trigger_reason TEXT,
                target_success_rate REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 迁移进化日志到优化日志
        cursor.execute('''
            INSERT OR IGNORE INTO strategy_optimization_logs 
            (strategy_id, optimization_type, before_params, after_params, trigger_reason, target_success_rate, timestamp)
            SELECT strategy_id, action_type, old_parameters, new_parameters, trigger_reason, improvement_target, timestamp
            FROM strategy_evolution_logs 
            WHERE strategy_id IS NOT NULL
        ''')
        
        conn.commit()
        print("✅ 表名修复完成！")
        
        # 验证
        cursor.execute("SELECT COUNT(*) FROM strategy_trade_logs")
        trade_count = cursor.fetchone()[0]
        print(f"  - 交易日志: {trade_count} 条")
        
        cursor.execute("SELECT COUNT(*) FROM strategy_optimization_logs")
        opt_count = cursor.fetchone()[0]
        print(f"  - 优化日志: {opt_count} 条")
        
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    fix_table_names() 