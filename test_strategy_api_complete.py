#!/usr/bin/env python3
import traceback
import psycopg2

def get_db_connection():
    return psycopg2.connect(
        host='localhost',
        database='quantitative',
        user='quant_user',
        password='123abc74531'
    )

def test_complete_strategy_api():
    try:
        print("🔍 开始完整策略API测试...")
        
        # 获取策略列表 - 模拟web_app.py的exact逻辑
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 🔧 模拟从前端配置获取最大显示策略数
        try:
            cursor.execute("""
                SELECT config_value FROM strategy_management_config 
                WHERE config_key = 'maxStrategies'
            """)
            max_strategies_config = cursor.fetchone()
            max_display_strategies = int(max_strategies_config[0]) if max_strategies_config else 50
        except Exception:
            # 如果配置表不存在，使用默认值
            max_display_strategies = 50
        print(f"🔧 策略显示数量从配置获取: {max_display_strategies}")
        
        # 主查询
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
        print(f"✅ 主查询成功，获得 {len(rows)} 行数据")
        
        strategies = []
        
        for row in rows:
            print(f"\n🔧 处理策略: row length = {len(row)}")
            
            # 🔥 修复：安全解包tuple，防止index out of range错误
            try:
                sid, name, symbol, stype, params, enabled, score, created_at, generation, cycle, \
                total_trades, wins, total_pnl, avg_pnl = row
                print(f"✅ 策略 {sid} 主数据解包成功")
            except ValueError as e:
                print(f"❌ 解包策略数据失败: {e}, row: {row}")
                continue
            
            # 测试子查询
            try:
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
                print(f"✅ 策略 {sid} 子查询成功: 交易={calculated_total_trades}, 盈利={calculated_wins}")
            except Exception as e:
                print(f"❌ 策略 {sid} 子查询失败: {e}")
                traceback.print_exc()
                continue
            
            # 测试进化历史查询
            try:
                cursor.execute("""
                    SELECT generation, cycle 
                    FROM strategy_evolution_history 
                    WHERE strategy_id = %s
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """, (sid,))
                latest_gen = cursor.fetchone()
                if latest_gen and len(latest_gen) >= 2 and latest_gen[0]:
                    latest_generation = latest_gen[0]
                    latest_cycle = latest_gen[1] or 1
                    evolution_display = f"第{latest_generation}代第{latest_cycle}轮"
                elif generation and generation > 0:
                    evolution_display = f"第{generation}代第{cycle or 1}轮"
                else:
                    evolution_display = "初代策略"
                print(f"✅ 策略 {sid} 进化历史查询成功: {evolution_display}")
            except Exception as e:
                print(f"❌ 策略 {sid} 进化历史查询失败: {e}")
                if generation and generation > 0:
                    evolution_display = f"第{generation}代第{cycle or 1}轮"
                else:
                    evolution_display = "初代策略"
            
            print(f"✅ 策略 {sid} 处理完成")
            break  # 只测试第一个策略
        
        conn.close()
        print("\n🎉 完整策略API测试成功！")
        return {"status": "success", "message": "测试成功"}
        
    except Exception as e:
        print(f"❌ 完整策略API测试失败: {e}")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    result = test_complete_strategy_api()
    print(f"\n�� 最终结果: {result}") 