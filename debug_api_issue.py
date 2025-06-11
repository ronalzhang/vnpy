#!/usr/bin/env python3
"""
调试API问题 - 为什么SQL查询有数据但API返回空
"""
import psycopg2
from flask import Flask

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="quantitative", 
        user="quant_user",
        password="123abc74531"
    )

def debug_api_query():
    """调试API查询问题"""
    strategy_id = 'STRAT_0798'
    limit = 200
    
    print(f"🔍 调试策略 {strategy_id} 的交易日志查询问题...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 使用与API完全相同的查询
        query = f"""
            SELECT timestamp, symbol, signal_type, price, quantity, 
                   expected_return as pnl, executed, id, strategy_id, signal_type as action, expected_return as real_pnl,
                   confidence
            FROM trading_signals 
            WHERE strategy_id = %s
            ORDER BY timestamp DESC
            LIMIT {limit}
        """
        
        print(f"📝 执行查询: {query}")
        print(f"📋 参数: ({strategy_id},)")
        
        cursor.execute(query, (strategy_id,))
        rows = cursor.fetchall()
        
        print(f"🔢 查询返回 {len(rows)} 条记录")
        
        if rows:
            print("📊 前3条记录:")
            for i, row in enumerate(rows[:3]):
                print(f"  记录{i+1}: 长度={len(row)}, 内容={row}")
        else:
            print("❌ 没有返回任何记录")
            
        # 测试处理逻辑
        logs = []
        for row in rows:
            try:
                # 复制API中的处理逻辑
                trade_type = 'verification'
                is_real_money = False
                confidence = row[11] if len(row) > 11 and row[11] else 0.75
                
                log_entry = {
                    'timestamp': row[0].strftime('%Y-%m-%d %H:%M:%S') if row[0] else '',
                    'symbol': row[1] or '',
                    'signal_type': row[2] or '',
                    'price': float(row[3]) if row[3] else 0.0,
                    'quantity': float(row[4]) if row[4] else 0.0,
                    'pnl': float(row[5]) if row[5] else 0.0,
                    'executed': bool(row[6]) if row[6] is not None else False,
                    'confidence': float(confidence),
                    'id': row[7],
                    'strategy_name': row[8] or '',
                    'action': row[9] or '',
                    'real_pnl': float(row[10]) if row[10] else 0.0,
                    'trade_type': trade_type,
                    'is_real_money': is_real_money,
                    'validation_id': str(row[7])[:8] if row[7] else None
                }
                
                logs.append(log_entry)
                print(f"✅ 成功处理记录 {len(logs)}: {log_entry['timestamp']} {log_entry['signal_type']}")
                
            except Exception as e:
                print(f"❌ 处理记录 {len(logs)+1} 时出错: {e}")
                print(f"   行数据: {row}")
                break
        
        print(f"🎯 最终处理结果: {len(logs)} 条日志记录")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 调试查询失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_api_query() 