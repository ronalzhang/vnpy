#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psycopg2
import json
import traceback
from datetime import datetime

def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(
        host='localhost',
        database='quantitative',
        user='quant_user',
        password='123abc74531'
    )

def test_strategies_api_step_by_step():
    """逐步测试策略API的每个步骤"""
    print("🔧 开始逐步测试策略API...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 步骤1：测试配置获取
        print("步骤1: 测试配置获取...")
        try:
            cursor.execute("SELECT config_value FROM strategy_management_config WHERE config_key = 'maxStrategies'")
            max_strategies_config = cursor.fetchone()
            print(f"✅ 配置获取成功: {max_strategies_config}")
        except Exception as e:
            print(f"❌ 配置获取失败: {e}")
            traceback.print_exc()
        
        # 步骤2：测试主查询
        print("\n步骤2: 测试主查询...")
        max_display_strategies = 50
        try:
            query = f'''
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
                LIMIT {max_display_strategies}
            '''
            print(f"🔍 执行查询: {query[:200]}...")
            cursor.execute(query)
            rows = cursor.fetchall()
            print(f"✅ 主查询成功，获得 {len(rows)} 行数据")
            if rows:
                print(f"🔍 第一行数据: {rows[0][:5]}...")  # 只显示前5个字段
        except Exception as e:
            print(f"❌ 主查询失败: {e}")
            traceback.print_exc()
            return
        
        # 步骤3：测试tuple解包
        print("\n步骤3: 测试tuple解包...")
        strategies = []
        for i, row in enumerate(rows[:3]):  # 只测试前3条
            try:
                print(f"  处理策略 {i+1}: 数据长度={len(row)}")
                sid, name, symbol, stype, params, enabled, score, created_at, generation, cycle, \
                total_trades, wins, total_pnl, avg_pnl = row
                print(f"  ✅ 策略 {sid} 解包成功")
                
                # 步骤4：测试子查询（交易统计）
                print(f"  步骤4: 测试 {sid} 的交易统计查询...")
                try:
                    cursor.execute("""
                        SELECT COUNT(*) as executed_trades,
                               COUNT(CASE WHEN pnl > 0 THEN 1 END) as wins
                        FROM strategy_trade_logs
                        WHERE strategy_id = %s AND executed = true
                    """, (sid,))
                    
                    trade_stats = cursor.fetchone()
                    print(f"    ✅ 交易统计查询成功: {trade_stats}")
                except Exception as e:
                    print(f"    ❌ 交易统计查询失败: {e}")
                    traceback.print_exc()
                
                # 步骤5：测试进化历史查询
                print(f"  步骤5: 测试 {sid} 的进化历史查询...")
                try:
                    cursor.execute("""
                        SELECT generation, cycle 
                        FROM strategy_evolution_history 
                        WHERE strategy_id = %s
                        ORDER BY timestamp DESC 
                        LIMIT 1
                    """, (sid,))
                    latest_gen = cursor.fetchone()
                    print(f"    ✅ 进化历史查询成功: {latest_gen}")
                except Exception as e:
                    print(f"    ❌ 进化历史查询失败: {e}")
                    traceback.print_exc()
                
                # 只测试前3个策略，避免输出过多
                if i >= 2:
                    break
                    
            except ValueError as e:
                print(f"  ❌ 策略 {i+1} tuple解包失败: {e}")
                print(f"  🔍 数据内容: {row}")
                traceback.print_exc()
            except Exception as e:
                print(f"  ❌ 策略 {i+1} 处理失败: {e}")
                traceback.print_exc()
        
        conn.close()
        print("\n🎉 测试完成！")
        
    except Exception as e:
        print(f"❌ 整体测试失败: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_strategies_api_step_by_step() 