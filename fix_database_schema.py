#!/usr/bin/env python3
"""
数据库Schema修复脚本
修复缺失的列和表结构问题
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json

def get_db_connection():
    """获取数据库连接"""
    try:
        # 使用硬编码的PostgreSQL配置
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='quantitative',
            user='quant_user',
            password='chenfei0421',
            cursor_factory=RealDictCursor
        )
        
        return conn
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None

def check_column_exists(cursor, table_name, column_name):
    """检查列是否存在"""
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name=%s AND column_name=%s
    """, (table_name, column_name))
    
    return cursor.fetchone() is not None

def add_missing_columns(conn):
    """添加缺失的列"""
    cursor = conn.cursor()
    
    columns_to_add = [
        {
            'table': 'system_status',
            'column': 'last_evolution_time',
            'definition': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        },
        {
            'table': 'system_status', 
            'column': 'last_update_time',
            'definition': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
    ]
    
    for col_info in columns_to_add:
        try:
            # 检查列是否存在
            if not check_column_exists(cursor, col_info['table'], col_info['column']):
                sql = f"ALTER TABLE {col_info['table']} ADD COLUMN {col_info['column']} {col_info['definition']}"
                cursor.execute(sql)
                print(f"✅ 添加列: {col_info['table']}.{col_info['column']}")
            else:
                print(f"✅ 列已存在: {col_info['table']}.{col_info['column']}")
                
        except Exception as e:
            print(f"❌ 添加列失败 {col_info['table']}.{col_info['column']}: {e}")
    
    conn.commit()

def fix_boolean_constraints(conn):
    """修复boolean字段约束问题"""
    cursor = conn.cursor()
    
    try:
        # 确保executed列是boolean类型
        cursor.execute("""
            ALTER TABLE strategy_trade_logs 
            ALTER COLUMN executed TYPE BOOLEAN 
            USING executed::boolean
        """)
        print("✅ 修复strategy_trade_logs.executed列类型")
        
        cursor.execute("""
            ALTER TABLE trading_signals 
            ALTER COLUMN executed TYPE BOOLEAN 
            USING executed::boolean
        """)
        print("✅ 修复trading_signals.executed列类型")
        
        conn.commit()
        
    except Exception as e:
        print(f"❌ 修复boolean字段失败: {e}")
        conn.rollback()

def create_missing_tables(conn):
    """创建缺失的表"""
    cursor = conn.cursor()
    
    # 检查并创建必要的表
    required_tables = {
        'account_info': """
            CREATE TABLE IF NOT EXISTS account_info (
                id SERIAL PRIMARY KEY,
                balance DECIMAL(20, 8) DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        'strategy_optimization_logs': """
            CREATE TABLE IF NOT EXISTS strategy_optimization_logs (
                id SERIAL PRIMARY KEY,
                strategy_id VARCHAR(50),
                optimization_type VARCHAR(50),
                old_parameters TEXT,
                new_parameters TEXT,
                trigger_reason TEXT,
                target_success_rate DECIMAL(5, 4),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        'operation_logs': """
            CREATE TABLE IF NOT EXISTS operation_logs (
                id SERIAL PRIMARY KEY,
                operation_type VARCHAR(100),
                operation_detail TEXT,
                result TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
    }
    
    for table_name, create_sql in required_tables.items():
        try:
            cursor.execute(create_sql)
            print(f"✅ 确保表存在: {table_name}")
        except Exception as e:
            print(f"❌ 创建表失败 {table_name}: {e}")
    
    conn.commit()

def main():
    """主函数"""
    print("🔧 开始修复数据库Schema...")
    
    # 获取数据库连接
    conn = get_db_connection()
    if not conn:
        print("❌ 无法连接数据库，修复失败")
        return
    
    try:
        # 1. 创建缺失的表
        print("\n📋 检查并创建缺失的表...")
        create_missing_tables(conn)
        
        # 2. 添加缺失的列
        print("\n🔧 添加缺失的列...")
        add_missing_columns(conn)
        
        # 3. 修复boolean字段类型问题
        print("\n🔧 修复boolean字段类型...")
        fix_boolean_constraints(conn)
        
        print("\n✅ 数据库Schema修复完成！")
        
    except Exception as e:
        print(f"❌ 修复过程出错: {e}")
        conn.rollback()
        
    finally:
        conn.close()

if __name__ == "__main__":
    main() 