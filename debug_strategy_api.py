#!/usr/bin/env python3
import psycopg2
import json
import traceback

def get_db_connection():
    return psycopg2.connect(
        host='localhost',
        database='quantitative',
        user='quant_user',
        password='123abc74531'
    )

def test_strategy_api():
    try:
        print("🔍 开始调试策略API...")
        
        # 获取策略列表 - 直接从数据库获取
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 测试基本查询
        max_display_strategies = 1  # 先测试单个策略
        print(f"📊 最大显示策略数: {max_display_strategies}")
        
        # 首先测试简单查询
        print("🔧 测试基本查询...")
        cursor.execute("SELECT COUNT(*) FROM strategies WHERE id LIKE 'STRAT_%'")
        count = cursor.fetchone()[0]
        print(f"✅ 策略总数: {count}")
        
        # 测试单个策略查询
        print("🔧 测试单个策略查询...")
        cursor.execute("SELECT id, name, symbol FROM strategies WHERE id LIKE 'STRAT_%' LIMIT 1")
        basic_row = cursor.fetchone()
        print(f"✅ 基本查询结果: {basic_row}")
        
        # 测试完整查询
        print("🔧 测试完整的JOIN查询...")
        cursor.execute('''
            SELECT s.id, s.name, s.symbol, s.type, s.parameters, s.enabled, s.final_score,
                   s.created_at, s.generation, s.cycle,
                   COUNT(t.id) as total_trades,
                   COUNT(CASE WHEN t.pnl > 0 THEN 1 END) as wins,
                   SUM(t.pnl) as total_pnl,
                   AVG(t.pnl) as avg_pnl
            FROM strategies s
            LEFT JOIN strategy_trade_logs t ON s.id = t.strategy_id
            WHERE s.id LIKE %s
            GROUP BY s.id, s.name, s.symbol, s.type, s.parameters, s.enabled, 
                     s.final_score, s.created_at, s.generation, s.cycle
            ORDER BY COUNT(t.id) DESC, s.final_score DESC, s.created_at DESC
            LIMIT %s
        ''', ('STRAT_%', max_display_strategies))
        
        rows = cursor.fetchall()
        print(f"✅ JOIN查询成功，获得 {len(rows)} 行数据")
        
        if len(rows) > 0:
            row = rows[0]
            print(f"🔧 测试第一行数据: length = {len(row)}")
            print(f"Row data: {row}")
            
            # 尝试解包
            try:
                sid, name, symbol, stype, params, enabled, score, created_at, generation, cycle, \
                total_trades, wins, total_pnl, avg_pnl = row
                print(f"✅ 解包成功！策略ID: {sid}")
                
                return {
                    "status": "success", 
                    "message": "调试成功，没有tuple错误",
                    "strategy_count": len(rows),
                    "first_strategy": sid
                }
                
            except ValueError as e:
                print(f"❌ 解包失败: {e}")
                return {"status": "error", "message": f"解包失败: {e}"}
        else:
            return {"status": "error", "message": "没有找到策略数据"}
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e)
        }
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    result = test_strategy_api()
    print("\n📋 最终结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False)) 