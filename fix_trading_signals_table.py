#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psycopg2
from datetime import datetime

def fix_trading_signals_table():
    """修复trading_signals表结构"""
    try:
        # 连接数据库
        conn = psycopg2.connect(
            host="localhost",
            database="quantitative",
            user="quant_user",
            password="chenfei0421"
        )
        cursor = conn.cursor()
        
        print("🔧 修复trading_signals表结构...")
        
        # 检查表是否存在并获取现有列
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'trading_signals'
        """)
        existing_columns = {row[0] for row in cursor.fetchall()}
        print(f"现有列: {existing_columns}")
        
        # 需要添加的列
        new_columns = {
            'side': "VARCHAR(10) DEFAULT 'buy'",
            'price': "DECIMAL(20,8) DEFAULT 0",
            'quantity': "DECIMAL(20,8) DEFAULT 0",
            'confidence': "DECIMAL(5,4) DEFAULT 0.5",
            'expected_return': "DECIMAL(10,6) DEFAULT 0",
            'risk_level': "VARCHAR(20) DEFAULT 'medium'",
            'strategy_score': "DECIMAL(10,6) DEFAULT 50.0"
        }
        
        # 添加缺失的列
        for col_name, col_def in new_columns.items():
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE trading_signals ADD COLUMN {col_name} {col_def}")
                    print(f"  ✅ 添加列: {col_name}")
                except Exception as e:
                    print(f"  ❌ 添加列失败 {col_name}: {e}")
        
        # 确保有正确的索引
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trading_signals_status ON trading_signals(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trading_signals_timestamp ON trading_signals(timestamp)")
            print("  ✅ 添加索引")
        except Exception as e:
            print(f"  ❌ 添加索引失败: {e}")
            
        conn.commit()
        print("✅ trading_signals表结构修复完成")
        
        # 验证表结构
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'trading_signals'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        print(f"修复后的表结构: {len(columns)}个字段")
        for col_name, col_type in columns:
            print(f"  - {col_name}: {col_type}")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")

if __name__ == "__main__":
    fix_trading_signals_table() 