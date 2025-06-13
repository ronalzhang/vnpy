#!/usr/bin/env python3
import psycopg2
import sys

def check_database_structure():
    try:
        # 连接数据库
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative',
            user='quant_user',
            password='123abc74531'
        )
        cur = conn.cursor()
        
        # 查看所有表
        print("=== 数据库中的所有表 ===")
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
        tables = cur.fetchall()
        for table in tables:
            print(f"  {table[0]}")
        
        print("\n=== 检查 trading_signals 表结构 ===")
        # 检查 trading_signals 表结构
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'trading_signals' 
            ORDER BY ordinal_position;
        """)
        columns = cur.fetchall()
        
        if columns:
            print("trading_signals 表字段:")
            for col in columns:
                print(f"  {col[0]}: {col[1]} (可空: {col[2]}, 默认: {col[3]})")
                
            # 检查新添加的字段是否存在
            new_fields = ['cycle_id', 'cycle_status', 'open_time', 'close_time', 'holding_minutes', 'mrot_score', 'paired_signal_id']
            existing_fields = [col[0] for col in columns]
            
            print("\n=== 新字段检查 ===")
            for field in new_fields:
                if field in existing_fields:
                    print(f"  ✅ {field} - 已存在")
                else:
                    print(f"  ❌ {field} - 缺失")
        else:
            print("❌ trading_signals 表不存在")
            
        # 检查索引
        print("\n=== 索引检查 ===")
        cur.execute("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'trading_signals';
        """)
        indexes = cur.fetchall()
        
        if indexes:
            for idx in indexes:
                print(f"  {idx[0]}: {idx[1]}")
        else:
            print("  没有找到相关索引")
            
        # 检查最近的交易记录
        print("\n=== 最近的交易记录 (前5条) ===")
        cur.execute("""
            SELECT strategy_id, signal_type, executed, cycle_id, cycle_status, mrot_score, timestamp 
            FROM trading_signals 
            ORDER BY timestamp DESC 
            LIMIT 5;
        """)
        recent_trades = cur.fetchall()
        
        if recent_trades:
            for trade in recent_trades:
                print(f"  策略{trade[0]}: {trade[1]} | 执行:{trade[2]} | 周期:{trade[3]} | 状态:{trade[4]} | MRoT:{trade[5]} | 时间:{trade[6]}")
        else:
            print("  没有找到交易记录")
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"数据库检查失败: {e}")
        return False

if __name__ == "__main__":
    check_database_structure() 