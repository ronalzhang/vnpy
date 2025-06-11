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

def calculate_strategy_sharpe_ratio(strategy_id, total_trades):
    """计算策略夏普比率"""
    try:
        if total_trades < 5:  # 交易次数太少无法计算准确的夏普比率
            return 0.0
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取策略的PnL数据
        cursor.execute("""
            SELECT pnl FROM strategy_trade_logs 
            WHERE strategy_id = %s 
            ORDER BY timestamp DESC 
            LIMIT 100
        """, (strategy_id,))
        
        pnl_data = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if len(pnl_data) < 5:
            return 0.0
        
        # 计算收益率的平均值和标准差
        import statistics
        mean_return = statistics.mean(pnl_data)
        if len(pnl_data) > 1:
            std_return = statistics.stdev(pnl_data)
            if std_return > 0:
                return mean_return / std_return
        
        return 0.0
        
    except Exception as e:
        print(f"计算夏普比率失败: {e}")
        return 0.0

def calculate_strategy_profit_factor(strategy_id, winning_trades, losing_trades):
    """计算策略盈亏比"""
    try:
        if losing_trades == 0:  # 没有亏损交易
            return 999.0 if winning_trades > 0 else 0.0
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取盈利和亏损总额
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) as total_profit,
                SUM(CASE WHEN pnl < 0 THEN ABS(pnl) ELSE 0 END) as total_loss
            FROM strategy_trade_logs 
            WHERE strategy_id = %s
        """, (strategy_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        # 🔥 修复：安全访问tuple元素，防止index out of range错误
        if result and len(result) >= 2:
            total_profit = float(result[0]) if result[0] else 0.0
            total_loss = float(result[1]) if result[1] else 0.0
            if total_loss > 0:
                return total_profit / total_loss
                
        return 0.0
        
    except Exception as e:
        print(f"计算盈亏比失败: {e}")
        return 0.0

def test_calculation_functions():
    """测试计算函数"""
    print("\n步骤6: 测试计算函数...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取第一个策略进行测试
        cursor.execute("SELECT id FROM strategies WHERE id LIKE 'STRAT_%' LIMIT 1")
        strategy_result = cursor.fetchone()
        
        if not strategy_result:
            print("    ❌ 没有找到策略进行测试")
            return
            
        test_strategy_id = strategy_result[0]
        print(f"    🔍 测试策略: {test_strategy_id}")
        
        # 获取交易统计数据
        cursor.execute("""
            SELECT COUNT(*) as total_trades,
                   COUNT(CASE WHEN pnl > 0 THEN 1 END) as wins,
                   COUNT(CASE WHEN pnl <= 0 THEN 1 END) as losses
            FROM strategy_trade_logs
            WHERE strategy_id = %s AND executed = true
        """, (test_strategy_id,))
        
        trade_stats = cursor.fetchone()
        total_trades = trade_stats[0] if trade_stats else 0
        wins = trade_stats[1] if trade_stats and len(trade_stats) > 1 else 0
        losses = trade_stats[2] if trade_stats and len(trade_stats) > 2 else 0
        
        print(f"    📊 交易统计: 总数={total_trades}, 盈利={wins}, 亏损={losses}")
        
        # 测试夏普比率计算
        try:
            sharpe_ratio = calculate_strategy_sharpe_ratio(test_strategy_id, total_trades)
            print(f"    ✅ 夏普比率计算成功: {sharpe_ratio}")
        except Exception as e:
            print(f"    ❌ 夏普比率计算失败: {e}")
            traceback.print_exc()
        
        # 测试盈亏比计算
        try:
            profit_factor = calculate_strategy_profit_factor(test_strategy_id, wins, losses)
            print(f"    ✅ 盈亏比计算成功: {profit_factor}")
        except Exception as e:
            print(f"    ❌ 盈亏比计算失败: {e}")
            traceback.print_exc()
        
        conn.close()
        
    except Exception as e:
        print(f"    ❌ 计算函数测试失败: {e}")
        traceback.print_exc()

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
        
        # 新增：测试计算函数
        test_calculation_functions()
        
        conn.close()
        print("\n🎉 测试完成！")
        
    except Exception as e:
        print(f"❌ 整体测试失败: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_strategies_api_step_by_step() 