#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
策略计算函数调试脚本
逐个测试策略API中的每个计算函数，找出tuple访问错误
"""

import psycopg2
import traceback
import json
from datetime import datetime

def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(
        host="localhost",
        database="quantitative", 
        user="quant_user",
        password="123abc74531"
    )

def test_strategy_query():
    """测试基本策略查询是否有tuple错误"""
    print("🔧 开始测试基本策略查询...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 基本策略查询
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
            LIMIT 5
        ''')
        
        rows = cursor.fetchall()
        print(f"✅ 查询成功，获得 {len(rows)} 条策略记录")
        
        # 测试每一行的解包
        for i, row in enumerate(rows):
            print(f"\n📊 测试第 {i+1} 行数据:")
            print(f"   行长度: {len(row)}")
            print(f"   数据: {row}")
            
            try:
                sid, name, symbol, stype, params, enabled, score, created_at, generation, cycle, \
                total_trades, wins, total_pnl, avg_pnl = row
                print(f"   ✅ 解包成功: {sid}")
                
                # 测试子查询
                print(f"   🔍 测试子查询...")
                cursor.execute("""
                    SELECT COUNT(*) as executed_trades,
                           COUNT(CASE WHEN pnl > 0 THEN 1 END) as wins
                    FROM strategy_trade_logs
                    WHERE strategy_id = %s AND executed = true
                """, (sid,))
                
                trade_stats = cursor.fetchone()
                print(f"   ✅ 子查询成功，统计: {trade_stats}")
                
                if trade_stats and len(trade_stats) >= 2:
                    calculated_total_trades = trade_stats[0]
                    calculated_wins = trade_stats[1]
                    win_rate = (calculated_wins / calculated_total_trades * 100) if calculated_total_trades > 0 else 0
                    print(f"   ✅ 计算成功率: {win_rate:.2f}%")
                
            except ValueError as ve:
                print(f"   ❌ 解包失败: {ve}")
                return {"status": "error", "message": f"解包失败: {ve}"}
            except Exception as e:
                print(f"   ❌ 处理失败: {e}")
                traceback.print_exc()
                return {"status": "error", "message": f"处理失败: {e}"}
        
        conn.close()
        return {"status": "success", "message": "基本查询测试通过"}
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        traceback.print_exc()
        return {"status": "error", "message": f"查询失败: {e}"}

def test_calculation_functions():
    """测试所有计算函数"""
    print("\n🔧 开始测试计算函数...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取一个有交易记录的策略ID进行测试
        cursor.execute("""
            SELECT DISTINCT strategy_id 
            FROM strategy_trade_logs 
            WHERE strategy_id LIKE 'STRAT_%'
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        if not result:
            print("⚠️ 没有找到有交易记录的策略，跳过计算函数测试")
            return {"status": "warning", "message": "没有交易记录"}
        
        test_strategy_id = result[0]
        print(f"🎯 使用策略 {test_strategy_id} 进行测试")
        
        # 测试1: calculate_strategy_sharpe_ratio
        print("\n📈 测试夏普比率计算...")
        try:
            sharpe_ratio = calculate_strategy_sharpe_ratio(test_strategy_id, 10)
            print(f"   ✅ 夏普比率: {sharpe_ratio}")
        except Exception as e:
            print(f"   ❌ 夏普比率计算失败: {e}")
            traceback.print_exc()
        
        # 测试2: calculate_strategy_max_drawdown
        print("\n📉 测试最大回撤计算...")
        try:
            max_drawdown = calculate_strategy_max_drawdown(test_strategy_id)
            print(f"   ✅ 最大回撤: {max_drawdown}")
        except Exception as e:
            print(f"   ❌ 最大回撤计算失败: {e}")
            traceback.print_exc()
        
        # 测试3: calculate_strategy_profit_factor
        print("\n💰 测试盈亏比计算...")
        try:
            profit_factor = calculate_strategy_profit_factor(test_strategy_id, 5, 3)
            print(f"   ✅ 盈亏比: {profit_factor}")
        except Exception as e:
            print(f"   ❌ 盈亏比计算失败: {e}")
            traceback.print_exc()
        
        # 测试4: calculate_strategy_volatility
        print("\n📊 测试波动率计算...")
        try:
            volatility = calculate_strategy_volatility(test_strategy_id)
            print(f"   ✅ 波动率: {volatility}")
        except Exception as e:
            print(f"   ❌ 波动率计算失败: {e}")
            traceback.print_exc()
        
        conn.close()
        return {"status": "success", "message": "计算函数测试完成"}
        
    except Exception as e:
        print(f"❌ 计算函数测试失败: {e}")
        traceback.print_exc()
        return {"status": "error", "message": f"计算函数测试失败: {e}"}

def calculate_strategy_sharpe_ratio(strategy_id, total_trades):
    """计算策略夏普比率"""
    try:
        if total_trades < 5:
            return 0.0
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pnl FROM strategy_trade_logs 
            WHERE strategy_id = %s 
            ORDER BY timestamp DESC 
            LIMIT 100
        """, (strategy_id,))
        
        rows = cursor.fetchall()
        print(f"       🔍 获取到 {len(rows)} 条PnL记录")
        
        pnl_data = []
        for row in rows:
            if len(row) >= 1:
                pnl_data.append(row[0])
            else:
                print(f"       ⚠️ 行数据长度不足: {row}")
        
        conn.close()
        
        if len(pnl_data) < 5:
            return 0.0
        
        import statistics
        mean_return = statistics.mean(pnl_data)
        if len(pnl_data) > 1:
            std_return = statistics.stdev(pnl_data)
            if std_return > 0:
                return mean_return / std_return
        
        return 0.0
        
    except Exception as e:
        print(f"       ❌ 夏普比率计算异常: {e}")
        traceback.print_exc()
        return 0.0

def calculate_strategy_max_drawdown(strategy_id):
    """计算策略最大回撤"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pnl FROM strategy_trade_logs 
            WHERE strategy_id = %s 
            ORDER BY timestamp ASC
        """, (strategy_id,))
        
        rows = cursor.fetchall()
        print(f"       🔍 获取到 {len(rows)} 条PnL记录（按时间排序）")
        
        pnl_data = []
        for row in rows:
            if len(row) >= 1:
                pnl_data.append(row[0])
            else:
                print(f"       ⚠️ 行数据长度不足: {row}")
        
        conn.close()
        
        if len(pnl_data) < 2:
            return 0.0
        
        cumulative_pnl = []
        running_total = 0
        for pnl in pnl_data:
            running_total += pnl
            cumulative_pnl.append(running_total)
        
        max_drawdown = 0.0
        peak = cumulative_pnl[0]
        
        for value in cumulative_pnl:
            if value > peak:
                peak = value
            if peak > 0:
                drawdown = (peak - value) / peak
                max_drawdown = max(max_drawdown, drawdown)
            
        return max_drawdown
        
    except Exception as e:
        print(f"       ❌ 最大回撤计算异常: {e}")
        traceback.print_exc()
        return 0.0

def calculate_strategy_profit_factor(strategy_id, winning_trades, losing_trades):
    """计算策略盈亏比"""
    try:
        if losing_trades == 0:
            return 999.0 if winning_trades > 0 else 0.0
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) as total_profit,
                SUM(CASE WHEN pnl < 0 THEN ABS(pnl) ELSE 0 END) as total_loss
            FROM strategy_trade_logs 
            WHERE strategy_id = %s
        """, (strategy_id,))
        
        result = cursor.fetchone()
        print(f"       🔍 盈亏查询结果: {result}")
        
        conn.close()
        
        # 🔥 安全访问tuple元素
        if result and len(result) >= 2:
            total_profit = result[0] if result[0] is not None else 0.0
            total_loss = result[1] if result[1] is not None else 0.0
            
            print(f"       💰 总盈利: {total_profit}, 总亏损: {total_loss}")
            
            if total_loss > 0:
                return float(total_profit) / float(total_loss)
        
        return 0.0
        
    except Exception as e:
        print(f"       ❌ 盈亏比计算异常: {e}")
        traceback.print_exc()
        return 0.0

def calculate_strategy_volatility(strategy_id):
    """计算策略波动率"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pnl FROM strategy_trade_logs 
            WHERE strategy_id = %s 
            ORDER BY timestamp DESC 
            LIMIT 50
        """, (strategy_id,))
        
        rows = cursor.fetchall()
        print(f"       🔍 获取到 {len(rows)} 条PnL记录（最近50条）")
        
        pnl_data = []
        for row in rows:
            if len(row) >= 1:
                pnl_data.append(row[0])
            else:
                print(f"       ⚠️ 行数据长度不足: {row}")
        
        conn.close()
        
        if len(pnl_data) < 3:
            return 0.0
        
        import statistics
        if len(pnl_data) > 1:
            return statistics.stdev(pnl_data)
        
        return 0.0
        
    except Exception as e:
        print(f"       ❌ 波动率计算异常: {e}")
        traceback.print_exc()
        return 0.0

def test_full_strategy_api_simulation():
    """完整模拟策略API调用"""
    print("\n🎯 开始完整策略API模拟测试...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        max_display_strategies = 30
        
        print("🔧 准备执行主查询...")
        try:
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
            print("✅ 主查询执行成功")
        except Exception as query_error:
            print(f"❌ 主查询执行失败: {query_error}")
            traceback.print_exc()
            return {"status": "error", "message": f"主查询失败: {query_error}"}
        
        try:
            rows = cursor.fetchall()
            print(f"✅ 主查询结果获取成功，共 {len(rows)} 条记录")
        except Exception as fetch_error:
            print(f"❌ 主查询结果获取失败: {fetch_error}")
            traceback.print_exc()
            return {"status": "error", "message": f"结果获取失败: {fetch_error}"}
        
        strategies = []
        print(f"🔧 开始处理 {len(rows)} 个策略...")
        
        for i, row in enumerate(rows):
            print(f"\n   策略 {i+1}/{len(rows)}:")
            print(f"     🔍 行数据长度: {len(row)}")
            print(f"     🔍 行数据类型: {type(row)}")
            
            try:
                print("     🔧 开始解包主查询结果...")
                if len(row) < 14:
                    print(f"     ❌ 行数据长度不足: 期望14，实际{len(row)}")
                    print(f"     🔍 实际数据: {row}")
                    continue
                
                sid, name, symbol, stype, params, enabled, score, created_at, generation, cycle, \
                total_trades, wins, total_pnl, avg_pnl = row
                
                print(f"     ✅ 基本数据解包成功: {sid}")
                
                # 子查询测试
                print("     🔧 开始执行子查询...")
                try:
                    cursor.execute("""
                        SELECT COUNT(*) as executed_trades,
                               COUNT(CASE WHEN pnl > 0 THEN 1 END) as wins
                        FROM strategy_trade_logs
                        WHERE strategy_id = %s AND executed = true
                    """, (sid,))
                    print("     ✅ 子查询执行成功")
                except Exception as subquery_error:
                    print(f"     ❌ 子查询执行失败: {subquery_error}")
                    traceback.print_exc()
                    continue
                
                try:
                    trade_stats = cursor.fetchone()
                    print(f"     ✅ 子查询结果获取成功: {trade_stats}")
                except Exception as subfetch_error:
                    print(f"     ❌ 子查询结果获取失败: {subfetch_error}")
                    traceback.print_exc()
                    continue
                
                if trade_stats and len(trade_stats) >= 2:
                    calculated_total_trades = trade_stats[0]
                    calculated_wins = trade_stats[1] 
                    win_rate = (calculated_wins / calculated_total_trades * 100) if calculated_total_trades > 0 else 0
                    print(f"     ✅ 子查询数据解析成功: 交易={calculated_total_trades}, 胜率={win_rate:.2f}%")
                else:
                    calculated_total_trades = 0
                    calculated_wins = 0
                    win_rate = 0
                    print(f"     ⚠️ 子查询无数据或数据长度不足")
                
                # 计算函数测试
                print(f"     🔧 开始计算函数测试...")
                try:
                    sharpe_ratio = calculate_strategy_sharpe_ratio(sid, calculated_total_trades)
                    print(f"     ✅ 夏普比率计算完成: {sharpe_ratio}")
                except Exception as sharpe_error:
                    print(f"     ❌ 夏普比率计算失败: {sharpe_error}")
                    sharpe_ratio = 0.0
                
                try:
                    max_drawdown = calculate_strategy_max_drawdown(sid)
                    print(f"     ✅ 最大回撤计算完成: {max_drawdown}")
                except Exception as drawdown_error:
                    print(f"     ❌ 最大回撤计算失败: {drawdown_error}")
                    max_drawdown = 0.0
                
                try:
                    profit_factor = calculate_strategy_profit_factor(sid, calculated_wins, calculated_total_trades - calculated_wins)
                    print(f"     ✅ 盈亏比计算完成: {profit_factor}")
                except Exception as profit_error:
                    print(f"     ❌ 盈亏比计算失败: {profit_error}")
                    profit_factor = 0.0
                
                try:
                    volatility = calculate_strategy_volatility(sid)
                    print(f"     ✅ 波动率计算完成: {volatility}")
                except Exception as vol_error:
                    print(f"     ❌ 波动率计算失败: {vol_error}")
                    volatility = 0.0
                
                print(f"     ✅ 所有计算完成: 夏普={sharpe_ratio:.4f}, 回撤={max_drawdown:.4f}, 盈亏比={profit_factor:.2f}, 波动率={volatility:.4f}")
                
                # 构建策略对象
                print("     🔧 开始构建策略对象...")
                try:
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
                        'avg_pnl': float(avg_pnl) if avg_pnl else 0.0,
                        'sharpe_ratio': round(sharpe_ratio, 4),
                        'max_drawdown': round(max_drawdown, 4),
                        'profit_factor': round(profit_factor, 2),
                        'volatility': round(volatility, 4)
                    }
                    
                    strategies.append(strategy)
                    print(f"     ✅ 策略对象构建成功")
                except Exception as build_error:
                    print(f"     ❌ 策略对象构建失败: {build_error}")
                    traceback.print_exc()
                    continue
                
            except Exception as e:
                print(f"     ❌ 策略处理失败: {e}")
                traceback.print_exc()
                continue
        
        conn.close()
        
        print(f"\n🎉 完整测试完成！成功处理 {len(strategies)} 个策略")
        return {
            "status": "success", 
            "message": f"完整测试成功，处理了{len(strategies)}个策略",
            "strategies_count": len(strategies)
        }
        
    except Exception as e:
        print(f"❌ 完整测试失败: {e}")
        traceback.print_exc()
        return {"status": "error", "message": f"完整测试失败: {e}"}

def test_sql_parameter_issue():
    """测试SQL查询参数问题"""
    print("\n🔧 开始测试SQL查询参数问题...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 测试1: 简单查询
        print("   测试1: 简单无参数查询...")
        try:
            cursor.execute("SELECT COUNT(*) FROM strategies WHERE id LIKE 'STRAT_%'")
            result = cursor.fetchone()
            print(f"   ✅ 简单查询成功: {result}")
        except Exception as e:
            print(f"   ❌ 简单查询失败: {e}")
            traceback.print_exc()
        
        # 测试2: 带参数查询（元组方式）
        print("   测试2: 带参数查询（元组方式）...")
        try:
            max_strategies = 30
            print(f"   🔍 参数值: {max_strategies}")
            print(f"   🔍 参数类型: {type(max_strategies)}")
            print(f"   🔍 参数元组: {(max_strategies,)}")
            print(f"   🔍 参数元组类型: {type((max_strategies,))}")
            
            cursor.execute("SELECT COUNT(*) FROM strategies WHERE id LIKE 'STRAT_%' LIMIT %s", (max_strategies,))
            result = cursor.fetchone()
            print(f"   ✅ 带参数查询（元组）成功: {result}")
        except Exception as e:
            print(f"   ❌ 带参数查询（元组）失败: {e}")
            traceback.print_exc()
        
        # 测试2.1: 带参数查询（列表方式）
        print("   测试2.1: 带参数查询（列表方式）...")
        try:
            max_strategies = 30
            cursor.execute("SELECT COUNT(*) FROM strategies WHERE id LIKE 'STRAT_%' LIMIT %s", [max_strategies])
            result = cursor.fetchone()
            print(f"   ✅ 带参数查询（列表）成功: {result}")
        except Exception as e:
            print(f"   ❌ 带参数查询（列表）失败: {e}")
            traceback.print_exc()
        
        # 测试2.2: 硬编码查询
        print("   测试2.2: 硬编码查询...")
        try:
            cursor.execute("SELECT COUNT(*) FROM strategies WHERE id LIKE 'STRAT_%' LIMIT 30")
            result = cursor.fetchone()
            print(f"   ✅ 硬编码查询成功: {result}")
        except Exception as e:
            print(f"   ❌ 硬编码查询失败: {e}")
            traceback.print_exc()
            
        # 测试2.3: 字符串格式化
        print("   测试2.3: 字符串格式化查询...")
        try:
            max_strategies = 30
            query = f"SELECT COUNT(*) FROM strategies WHERE id LIKE 'STRAT_%' LIMIT {max_strategies}"
            cursor.execute(query)
            result = cursor.fetchone()
            print(f"   ✅ 字符串格式化查询成功: {result}")
        except Exception as e:
            print(f"   ❌ 字符串格式化查询失败: {e}")
            traceback.print_exc()
        
        # 测试3: 完整主查询（不带参数）
        print("   测试3: 完整主查询（不带参数）...")
        try:
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
                LIMIT 5
            ''')
            result = cursor.fetchall()
            print(f"   ✅ 完整查询(无参数)成功: 获得{len(result)}条记录")
        except Exception as e:
            print(f"   ❌ 完整查询(无参数)失败: {e}")
            traceback.print_exc()
        
        # 测试4: 完整主查询（字符串格式化）
        print("   测试4: 完整主查询（字符串格式化）...")
        try:
            max_strategies = 30
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
                LIMIT {max_strategies}
            '''
            cursor.execute(query)
            result = cursor.fetchall()
            print(f"   ✅ 完整查询(字符串格式化)成功: 获得{len(result)}条记录")
        except Exception as e:
            print(f"   ❌ 完整查询(字符串格式化)失败: {e}")
            traceback.print_exc()
        
        # 测试5: 完整主查询（带参数）
        print("   测试5: 完整主查询（带参数）...")
        try:
            max_strategies = 30
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
            ''', (max_strategies,))
            result = cursor.fetchall()
            print(f"   ✅ 完整查询(带参数)成功: 获得{len(result)}条记录")
        except Exception as e:
            print(f"   ❌ 完整查询(带参数)失败: {e}")
            traceback.print_exc()
        
        conn.close()
        
        return {"status": "success", "message": "SQL参数测试完成"}
        
    except Exception as e:
        print(f"❌ SQL参数测试失败: {e}")
        traceback.print_exc()
        return {"status": "error", "message": f"SQL参数测试失败: {e}"}

if __name__ == "__main__":
    print("🚀 开始策略计算函数深度调试...")
    
    # 测试0: SQL参数问题
    result0 = test_sql_parameter_issue()
    print(f"\nSQL参数测试结果: {result0}")
    
    # 测试1: 基本查询
    result1 = test_strategy_query()
    print(f"\n基本查询测试结果: {result1}")
    
    # 测试2: 计算函数
    result2 = test_calculation_functions()
    print(f"\n计算函数测试结果: {result2}")
    
    # 测试3: 完整API模拟
    result3 = test_full_strategy_api_simulation()
    print(f"\n完整API测试结果: {result3}")
    
    print("\n🏁 所有测试完成！") 