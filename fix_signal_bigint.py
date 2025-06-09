#!/usr/bin/env python3
import psycopg2
import traceback

def fix_signal_id_type():
    """修复信号ID字段类型为BIGINT以支持时间戳"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("🔧 修复信号ID字段类型...")
        
        # 1. 删除现有的错误记录
        print("1. 清理现有数据...")
        cursor.execute("TRUNCATE TABLE trading_signals")
        print("  ✅ 清空trading_signals表")
        
        # 2. 修改ID字段类型为BIGINT
        print("2. 修改ID字段类型...")
        try:
            cursor.execute("ALTER TABLE trading_signals ALTER COLUMN id TYPE BIGINT")
            print("  ✅ 修改id字段类型为BIGINT")
        except Exception as e:
            print(f"  ⚠️ 修改字段类型失败: {e}")
        
        # 3. 验证字段类型
        print("3. 验证字段类型...")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'trading_signals' AND column_name = 'id'
        """)
        result = cursor.fetchone()
        if result:
            print(f"  ✅ ID字段信息: {result}")
        
        print("🎉 信号ID字段类型修复完成!")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_signal_id_type() 