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
        max_display_strategies = 30
        print(f"📊 最大显示策略数: {max_display_strategies}")
        
        cursor.execute('''
            SELECT s.id, s.name, s.symbol, s.type, s.parameters, s.enabled, s.final_score,
                   s.created_at, s.generation, s.cycle,
                   COUNT(t.id) as total_trades,
                   COUNT(CASE WHEN t.pnl > 0 THEN 1 END) as wins,
                   SUM(t.pnl) as total_pnl,
                   AVG(t.pnl) as avg_pnl
            FROM strategies s
            LEFT JOIN strategy_trade_logs t ON s.id = t.strategy_id
            WHERE s.id LIKE 'STRAT_%'
            GROUP BY s.id, s.name, s.symbol, s.type, s.parameters, s.enabled, 
                     s.final_score, s.created_at, s.generation, s.cycle
            ORDER BY COUNT(t.id) DESC, s.final_score DESC, s.created_at DESC
            LIMIT %s
        ''', (max_display_strategies,))
        
        rows = cursor.fetchall()
        print(f"✅ 查询成功，获得 {len(rows)} 行数据")
        
        strategies = []
        
        for i, row in enumerate(rows):
            print(f"\n🔧 处理策略 {i+1}: row length = {len(row)}")
            print(f"Row data: {row}")
            
            try:
                # 尝试解包
                sid, name, symbol, stype, params, enabled, score, created_at, generation, cycle, \
                total_trades, wins, total_pnl, avg_pnl = row
                
                print(f"✅ 策略 {sid} 解包成功")
                
                # 测试计算统计
                cursor.execute("""
                    SELECT COUNT(*) as executed_trades,
                           COUNT(CASE WHEN pnl > 0 THEN 1 END) as wins
                    FROM strategy_trade_logs
                    WHERE strategy_id = %s AND executed = true
                """, (sid,))
                
                trade_stats = cursor.fetchone()
                calculated_total_trades = trade_stats[0] if trade_stats else 0
                calculated_wins = trade_stats[1] if trade_stats else 0
                win_rate = (calculated_wins / calculated_total_trades * 100) if calculated_total_trades > 0 else 0
                
                print(f"📊 策略 {sid}: 已执行={calculated_total_trades}, 盈利={calculated_wins}, 成功率={win_rate:.2f}%")
                
                strategy = {
                    'id': sid,
                    'name': name,
                    'symbol': symbol,
                    'type': stype,
                    'enabled': bool(enabled),
                    'final_score': float(score) if score else 0.0,
                    'total_trades': calculated_total_trades,
                    'win_rate': round(win_rate, 2),
                    'total_pnl': float(total_pnl) if total_pnl else 0.0,
                    'avg_pnl': float(avg_pnl) if avg_pnl else 0.0
                }
                
                strategies.append(strategy)
                print(f"✅ 策略 {sid} 处理完成")
                
            except ValueError as e:
                print(f"❌ 解包策略数据失败: {e}")
                print(f"Row: {row}")
                continue
            except Exception as e:
                print(f"❌ 处理策略时出错: {e}")
                traceback.print_exc()
                continue
        
        conn.close()
        
        print(f"\n🎉 调试完成！成功处理 {len(strategies)} 个策略")
        return {
            "status": "success",
            "data": strategies
        }
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    result = test_strategy_api()
    print("\n📋 最终结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False)) 