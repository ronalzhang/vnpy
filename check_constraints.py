#!/usr/bin/env python3
"""
检查数据库表约束
"""
import psycopg2

def check_constraints():
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        print("=== 检查 trading_signals 表约束 ===")
        
        # 查看约束定义
        cursor.execute("""
            SELECT conname, pg_get_constraintdef(oid) 
            FROM pg_constraint 
            WHERE conrelid = 'trading_signals'::regclass 
            AND contype = 'c'
        """)
        constraints = cursor.fetchall()
        print("表约束:")
        for name, definition in constraints:
            print(f"  {name}: {definition}")
        
        # 查看允许的trade_type值
        cursor.execute("SELECT DISTINCT trade_type FROM trading_signals")
        trade_types = cursor.fetchall()
        print("\n现有trade_type值:")
        for tt in trade_types:
            print(f"  {tt[0]}")
            
        # 查看是否有CHECK约束限制trade_type
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'trading_signals' AND column_name = 'trade_type'
        """)
        column_info = cursor.fetchone()
        if column_info:
            print(f"\ntrade_type字段信息:")
            print(f"  类型: {column_info[1]}")
            print(f"  最大长度: {column_info[2]}")
            print(f"  可空: {column_info[3]}")
            print(f"  默认值: {column_info[4]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"检查失败: {e}")

if __name__ == "__main__":
    check_constraints() 