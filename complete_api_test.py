#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psycopg2
import json
import traceback
from datetime import datetime
import statistics

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
        
        pnl_data = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if len(pnl_data) < 5:
            return 0.0
        
        mean_return = statistics.mean(pnl_data)
        if len(pnl_data) > 1:
            std_return = statistics.stdev(pnl_data)
            if std_return > 0:
                return mean_return / std_return
        
        return 0.0
        
    except Exception as e:
        print(f"计算夏普比率失败: {e}")
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
        
        pnl_data = [row[0] for row in cursor.fetchall()]
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
        print(f"计算最大回撤失败: {e}")
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
        conn.close()
        
        if result and len(result) >= 2:
            total_profit = float(result[0]) if result[0] else 0.0
            total_loss = float(result[1]) if result[1] else 0.0
            if total_loss > 0:
                return total_profit / total_loss
                
        return 0.0
        
    except Exception as e:
        print(f"计算盈亏比失败: {e}")
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
        
        pnl_data = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if len(pnl_data) < 3:
            return 0.0
        
        if len(pnl_data) > 1:
            return statistics.stdev(pnl_data)
        
        return 0.0
        
    except Exception as e:
        print(f"计算波动率失败: {e}")
        return 0.0

def get_strategy_default_parameters(strategy_type):
    """获取策略默认参数"""
    defaults = {
        'trend_following': {
            'lookback_period': 20,
            'trade_amount': 100.0,
            'max_position_size': 0.2,
            'stop_loss': 0.02,
            'take_profit': 0.05
        },
        'breakout': {
            'breakout_period': 20,
            'trade_amount': 100.0,
            'stop_loss': 0.02,
            'take_profit': 0.04
        }
    }
    return defaults.get(strategy_type, {})

def complete_api_simulation():
    """完整API模拟测试"""
    print("🎯 开始完整策略API模拟...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 步骤1: 获取配置
        max_display_strategies = 50
        try:
            cursor.execute("SELECT config_value FROM strategy_management_config WHERE config_key = 'maxStrategies'")
            max_strategies_config = cursor.fetchone()
            if max_strategies_config:
                max_display_strategies = int(float(max_strategies_config[0]))
                print(f"🔧 策略显示数量从配置获取: {max_display_strategies}")
        except Exception as e:
            print(f"获取maxStrategies配置失败，使用默认值: {e}")
        
        # 步骤2: 主查询
        print("🔧 执行主查询...")
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
        strategies = []
        print(f"✅ 主查询成功，获得 {len(rows)} 行数据")
        
        # 步骤3: 处理每个策略
        for i, row in enumerate(rows[:5]):  # 只处理前5个
            try:
                print(f"\\n处理策略 {i+1}/{min(5, len(rows))}...")
                
                # tuple解包
                sid, name, symbol, stype, params, enabled, score, created_at, generation, cycle, \
                total_trades, wins, total_pnl, avg_pnl = row
                print(f"  ✅ 策略 {sid} 解包成功")
                
                # 交易统计查询
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
                print(f"  📊 交易统计: 执行={calculated_total_trades}, 盈利={calculated_wins}, 成功率={win_rate:.2f}%")
                
                # 进化历史查询
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
                except Exception as e:
                    print(f"  ⚠️ 获取策略{sid}进化历史失败: {e}")
                    if generation and generation > 0:
                        evolution_display = f"第{generation}代第{cycle or 1}轮"
                    else:
                        evolution_display = "初代策略"
                
                print(f"  📈 进化信息: {evolution_display}")
                
                # 计算指标
                print("  🧮 计算各项指标...")
                sharpe_ratio = calculate_strategy_sharpe_ratio(sid, total_trades)
                max_drawdown = calculate_strategy_max_drawdown(sid)
                profit_factor = calculate_strategy_profit_factor(sid, wins, total_trades - wins if total_trades > 0 else 0)
                volatility = calculate_strategy_volatility(sid)
                print(f"     夏普比率: {sharpe_ratio:.4f}")
                print(f"     最大回撤: {max_drawdown:.4f}")
                print(f"     盈亏比: {profit_factor:.2f}")
                print(f"     波动率: {volatility:.4f}")
                
                # 参数解析
                try:
                    if isinstance(params, str):
                        parsed_params = json.loads(params)
                    elif isinstance(params, dict):
                        parsed_params = params
                    else:
                        parsed_params = get_strategy_default_parameters(stype)
                    print(f"  📋 参数解析成功: {len(parsed_params)} 个参数")
                except Exception as e:
                    print(f"  ⚠️ 解析策略{sid}参数失败: {e}, 使用默认参数")
                    parsed_params = get_strategy_default_parameters(stype)
                
                # 构建策略对象
                strategy = {
                    'id': sid,
                    'name': name,
                    'symbol': symbol,
                    'type': stype,
                    'parameters': parsed_params,
                    'enabled': bool(enabled),
                    'final_score': float(score) if score else 0.0,
                    'created_at': created_at.isoformat() if created_at else '',
                    'generation': generation,
                    'cycle': cycle,
                    'total_trades': calculated_total_trades,
                    'win_rate': round(win_rate, 2),
                    'total_pnl': float(total_pnl) if total_pnl else 0.0,
                    'avg_pnl': float(avg_pnl) if avg_pnl else 0.0,
                    'sharpe_ratio': round(sharpe_ratio, 4),
                    'max_drawdown': round(max_drawdown, 4),
                    'profit_factor': round(profit_factor, 2),
                    'volatility': round(volatility, 4),
                    'evolution_display': evolution_display,
                    'trade_mode': '真实交易' if enabled else '模拟中'
                }
                
                strategies.append(strategy)
                print(f"  ✅ 策略 {sid} 处理完成")
                
            except Exception as e:
                print(f"  ❌ 策略 {i+1} 处理失败: {e}")
                traceback.print_exc()
        
        conn.close()
        
        print(f"\\n🎉 完整API模拟完成！成功处理 {len(strategies)} 个策略")
        
        # 输出JSON结果样例
        if strategies:
            print(f"\\n📄 第一个策略JSON示例:")
            print(json.dumps(strategies[0], indent=2, ensure_ascii=False)[:500] + "...")
        
        return {
            "status": "success",
            "data": strategies
        }
        
    except Exception as e:
        print(f"❌ 完整API模拟失败: {e}")
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"获取策略列表失败: {str(e)}"
        }

if __name__ == "__main__":
    result = complete_api_simulation()
    print(f"\\n🏁 最终结果: {result['status']}")
    if result['status'] == 'success':
        print(f"   数据条数: {len(result['data'])}")
    else:
        print(f"   错误信息: {result['message']}") 