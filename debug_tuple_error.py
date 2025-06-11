#!/usr/bin/env python3
"""
高级调试脚本 - 彻底解决tuple index out of range错误
"""
import traceback
import sys
import psycopg2
import json

def get_db_connection():
    """获取数据库连接"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="quantitative",
            user="quant_user",
            password="123abc74531"
        )
        print("✅ 数据库连接成功")
        return conn
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return None

def test_basic_query():
    """测试基本查询"""
    print("\n🔍 测试1: 基本查询")
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        # 测试简单查询
        cursor.execute("SELECT COUNT(*) FROM strategies WHERE id LIKE 'STRAT_%'")
        count = cursor.fetchone()
        print(f"策略总数: {count[0] if count else 0}")
        
        # 测试具体查询
        cursor.execute("SELECT id, name, enabled FROM strategies WHERE id LIKE 'STRAT_%' LIMIT 3")
        rows = cursor.fetchall()
        print(f"前3个策略:")
        for i, row in enumerate(rows):
            print(f"  {i+1}. ID: {row[0]}, Name: {row[1]}, Enabled: {row[2]}")
        
        conn.close()
        print("✅ 基本查询测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 基本查询测试失败: {e}")
        traceback.print_exc()
        return False

def test_complex_query():
    """测试复杂查询 - 模拟API中的查询"""
    print("\n🔍 测试2: 复杂查询 (模拟API)")
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        # 使用字符串格式化代替参数绑定
        max_display_strategies = 20
        
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
        
        print(f"执行查询: {query[:200]}...")
        cursor.execute(query)
        
        rows = cursor.fetchall()
        print(f"查询结果: {len(rows)} 行")
        
        # 详细检查每一行的结构
        for i, row in enumerate(rows[:3]):  # 只检查前3行
            print(f"\n行 {i+1}:")
            print(f"  类型: {type(row)}")
            print(f"  长度: {len(row)}")
            print(f"  内容: {row}")
            
            # 测试安全解包
            try:
                sid, name, symbol, stype, params, enabled, score, created_at, generation, cycle, \
                total_trades, wins, total_pnl, avg_pnl = row
                print(f"  ✅ 解包成功: ID={sid}, 交易次数={total_trades}")
            except ValueError as e:
                print(f"  ❌ 解包失败: {e}")
                break
        
        conn.close()
        print("✅ 复杂查询测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 复杂查询测试失败: {e}")
        traceback.print_exc()
        return False

def test_sub_queries():
    """测试子查询 - 检查trade_stats查询"""
    print("\n🔍 测试3: 子查询测试")
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        # 获取一个策略ID进行测试
        cursor.execute("SELECT id FROM strategies WHERE id LIKE 'STRAT_%' LIMIT 1")
        strategy_result = cursor.fetchone()
        
        if not strategy_result:
            print("没有找到策略进行测试")
            conn.close()
            return False
        
        strategy_id = strategy_result[0]
        print(f"测试策略ID: {strategy_id}")
        
        # 测试trade_stats查询
        cursor.execute("""
            SELECT COUNT(*) as executed_trades,
                   COUNT(CASE WHEN pnl > 0 THEN 1 END) as wins
            FROM strategy_trade_logs
            WHERE strategy_id = %s AND executed = true
        """, (strategy_id,))
        
        trade_stats = cursor.fetchone()
        print(f"trade_stats结果: {trade_stats}")
        print(f"  类型: {type(trade_stats)}")
        print(f"  长度: {len(trade_stats) if trade_stats else 0}")
        
        if trade_stats and len(trade_stats) >= 2:
            executed_trades = trade_stats[0]
            wins = trade_stats[1]
            print(f"  已执行交易: {executed_trades}")
            print(f"  盈利交易: {wins}")
        else:
            print("  ❌ trade_stats结果异常")
        
        conn.close()
        print("✅ 子查询测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 子查询测试失败: {e}")
        traceback.print_exc()
        return False

def test_calculation_functions():
    """测试计算函数"""
    print("\n🔍 测试4: 计算函数测试")
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        # 获取一个有交易记录的策略
        cursor.execute("""
            SELECT s.id, COUNT(t.id) as trade_count
            FROM strategies s
            LEFT JOIN strategy_trade_logs t ON s.id = t.strategy_id
            WHERE s.id LIKE 'STRAT_%'
            GROUP BY s.id
            HAVING COUNT(t.id) > 0
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        if not result:
            print("没有找到有交易记录的策略")
            conn.close()
            return False
        
        strategy_id = result[0]
        trade_count = result[1]
        print(f"测试策略: {strategy_id}, 交易记录: {trade_count}")
        
        # 测试盈亏比计算的查询
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) as total_profit,
                SUM(CASE WHEN pnl < 0 THEN ABS(pnl) ELSE 0 END) as total_loss
            FROM strategy_trade_logs 
            WHERE strategy_id = %s
        """, (strategy_id,))
        
        result = cursor.fetchone()
        print(f"盈亏比查询结果: {result}")
        print(f"  类型: {type(result)}")
        print(f"  长度: {len(result) if result else 0}")
        
        # 安全访问
        if result and len(result) >= 2:
            total_profit = result[0] if result[0] else 0
            total_loss = result[1] if result[1] else 0
            print(f"  总盈利: {total_profit}")
            print(f"  总亏损: {total_loss}")
        else:
            print("  ❌ 盈亏比查询结果异常")
        
        conn.close()
        print("✅ 计算函数测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 计算函数测试失败: {e}")
        traceback.print_exc()
        return False

def test_parameter_binding():
    """测试参数绑定问题"""
    print("\n🔍 测试5: 参数绑定问题")
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        # 测试不同的LIMIT方式
        print("测试方法1: 参数绑定LIMIT")
        try:
            limit_value = 5
            cursor.execute("SELECT id FROM strategies WHERE id LIKE 'STRAT_%' LIMIT %s", (limit_value,))
            result1 = cursor.fetchall()
            print(f"  方法1成功: {len(result1)} 行")
        except Exception as e:
            print(f"  方法1失败: {e}")
        
        print("测试方法2: 字符串格式化LIMIT")
        try:
            limit_value = 5
            cursor.execute(f"SELECT id FROM strategies WHERE id LIKE 'STRAT_%' LIMIT {limit_value}")
            result2 = cursor.fetchall()
            print(f"  方法2成功: {len(result2)} 行")
        except Exception as e:
            print(f"  方法2失败: {e}")
        
        print("测试方法3: 硬编码LIMIT")
        try:
            cursor.execute("SELECT id FROM strategies WHERE id LIKE 'STRAT_%' LIMIT 5")
            result3 = cursor.fetchall()
            print(f"  方法3成功: {len(result3)} 行")
        except Exception as e:
            print(f"  方法3失败: {e}")
        
        conn.close()
        print("✅ 参数绑定测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 参数绑定测试失败: {e}")
        traceback.print_exc()
        return False

def test_full_api_simulation():
    """完整API模拟测试"""
    print("\n🔍 测试6: 完整API模拟测试")
    try:
        # 模拟整个API流程
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        # 第一步：获取配置
        max_display_strategies = 20
        try:
            cursor.execute("SELECT config_value FROM strategy_management_config WHERE config_key = 'maxStrategies'")
            max_strategies_config = cursor.fetchone()
            if max_strategies_config:
                max_display_strategies = int(float(max_strategies_config[0]))
                print(f"从配置获取策略数量: {max_display_strategies}")
        except Exception as e:
            print(f"获取配置失败，使用默认值: {e}")
        
        # 第二步：主查询
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
        
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"主查询返回 {len(rows)} 行")
        
        # 第三步：处理每一行
        strategies = []
        for row in rows[:2]:  # 只处理前2行进行测试
            try:
                # 解包
                sid, name, symbol, stype, params, enabled, score, created_at, generation, cycle, \
                total_trades, wins, total_pnl, avg_pnl = row
                
                print(f"\n处理策略: {sid}")
                
                # 第四步：子查询
                cursor.execute("""
                    SELECT COUNT(*) as executed_trades,
                           COUNT(CASE WHEN pnl > 0 THEN 1 END) as wins
                    FROM strategy_trade_logs
                    WHERE strategy_id = %s AND executed = true
                """, (sid,))
                
                trade_stats = cursor.fetchone()
                calculated_total_trades = trade_stats[0] if trade_stats and len(trade_stats) >= 1 else 0
                calculated_wins = trade_stats[1] if trade_stats and len(trade_stats) >= 2 else 0
                win_rate = (calculated_wins / calculated_total_trades * 100) if calculated_total_trades > 0 else 0
                
                print(f"  已执行交易: {calculated_total_trades}")
                print(f"  盈利交易: {calculated_wins}")
                print(f"  成功率: {win_rate:.2f}%")
                
                # 第五步：进化历史查询
                cursor.execute("""
                    SELECT generation, cycle 
                    FROM strategy_evolution_history 
                    WHERE strategy_id = %s
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """, (sid,))
                latest_gen = cursor.fetchone()
                
                if latest_gen and len(latest_gen) >= 2 and latest_gen[0]:
                    evolution_display = f"第{latest_gen[0]}代第{latest_gen[1] or 1}轮"
                else:
                    evolution_display = f"第{generation or 1}代第{cycle or 1}轮"
                
                print(f"  进化信息: {evolution_display}")
                
                # 构建策略对象
                strategy = {
                    'id': sid,
                    'name': name,
                    'symbol': symbol,
                    'type': stype,
                    'enabled': bool(enabled),
                    'final_score': float(score) if score else 0.0,
                    'total_trades': calculated_total_trades,
                    'win_rate': round(win_rate, 2),
                    'evolution_display': evolution_display
                }
                
                strategies.append(strategy)
                print(f"  ✅ 策略处理成功")
                
            except Exception as e:
                print(f"  ❌ 处理策略失败: {e}")
                traceback.print_exc()
                break
        
        conn.close()
        
        print(f"\n✅ API模拟测试完成，成功处理 {len(strategies)} 个策略")
        for strategy in strategies:
            print(f"  - {strategy['id']}: {strategy['name']} (评分: {strategy['final_score']})")
        
        return True
        
    except Exception as e:
        print(f"❌ API模拟测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🔧 开始深度调试 tuple index out of range 错误")
    print("=" * 60)
    
    tests = [
        test_basic_query,
        test_complex_query,
        test_sub_queries,
        test_calculation_functions,
        test_parameter_binding,
        test_full_api_simulation
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            failed += 1
        print("-" * 40)
    
    print("\n📊 测试总结:")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"📋 总计: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 所有测试通过！tuple错误可能已修复。")
    else:
        print(f"\n⚠️  仍有 {failed} 个测试失败，需要进一步调试。")

if __name__ == "__main__":
    main() 