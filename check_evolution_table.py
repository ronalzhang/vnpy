#!/usr/bin/env python3
"""
检查strategy_evolution_history表结构
"""
import psycopg2

def check_evolution_table():
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        print("=== 检查 strategy_evolution_history 表结构 ===")
        
        # 检查表是否存在
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'strategy_evolution_history'
            )
        """)
        table_result = cursor.fetchone()
        table_exists = table_result[0] if table_result else False
        
        if table_exists:
            # 查看字段结构
            cursor.execute("""
                SELECT column_name, data_type, character_maximum_length, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'strategy_evolution_history'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            print("表字段:")
            for col in columns:
                print(f"  {col[0]}: {col[1]} (长度:{col[2]}, 可空:{col[3]}, 默认:{col[4]})")
                
            # 查看数据样本
            cursor.execute("SELECT COUNT(*) FROM strategy_evolution_history")
            count_result = cursor.fetchone()
            count = count_result[0] if count_result else 0
            print(f"\n总记录数: {count}")
            
            if count > 0:
                cursor.execute("""
                    SELECT * FROM strategy_evolution_history 
                    ORDER BY timestamp DESC LIMIT 3
                """)
                samples = cursor.fetchall()
                print("\n样本数据:")
                for i, sample in enumerate(samples):
                    print(f"  记录{i+1}: {sample}")
        else:
            print("表不存在")
            
        # 同样检查 strategy_optimization_logs 表
        print("\n=== 检查 strategy_optimization_logs 表结构 ===")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'strategy_optimization_logs'
            )
        """)
        opt_result = cursor.fetchone()
        opt_table_exists = opt_result[0] if opt_result else False
        
        if opt_table_exists:
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'strategy_optimization_logs'
                ORDER BY ordinal_position
            """)
            opt_columns = cursor.fetchall()
            print("表字段:")
            for col in opt_columns:
                print(f"  {col[0]}: {col[1]}")
        else:
            print("表不存在")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"检查失败: {e}")

if __name__ == "__main__":
    check_evolution_table() 