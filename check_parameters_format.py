#!/usr/bin/env python3
"""
检查参数字段的数据格式
"""
import psycopg2

def check_parameters_format():
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        print("=== 检查参数字段数据格式 ===")
        
        # 查看参数字段的实际数据
        cursor.execute("""
            SELECT parameters, new_parameters 
            FROM strategy_evolution_history 
            WHERE parameters IS NOT NULL 
            LIMIT 3
        """)
        samples = cursor.fetchall()
        print("参数样本数据:")
        for i, (params, new_params) in enumerate(samples):
            print(f"记录{i+1}: parameters={params}")
            print(f"          new_parameters={new_params}")
            print()
            
        # 检查parameters字段是否已经是JSON格式
        cursor.execute("""
            SELECT 
                COUNT(*) as total_count,
                COUNT(CASE WHEN parameters::text LIKE '{%' THEN 1 END) as json_like_count
            FROM strategy_evolution_history 
            WHERE parameters IS NOT NULL
        """)
        result = cursor.fetchone()
        if result:
            total, json_like = result
            print(f"总参数记录: {total}")
            print(f"JSON格式记录: {json_like}")
            print(f"JSON比例: {json_like/total*100:.1f}%")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"检查失败: {e}")

if __name__ == "__main__":
    check_parameters_format() 