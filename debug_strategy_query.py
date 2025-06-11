#!/usr/bin/env python3
import psycopg2
import traceback

def test_strategy_query():
    conn = psycopg2.connect(host='localhost', database='quantitative', user='quant_user', password='123abc74531')
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT config_value FROM strategy_management_config WHERE config_key = %s', ('maxStrategies',))
        max_strategies_config = cursor.fetchone()
        max_display_strategies = int(max_strategies_config[0]) if max_strategies_config else 50
        print(f'Config fetch success: {max_display_strategies}')
    except Exception as e:
        print(f'Config fetch error: {e}')
        max_display_strategies = 50

    print(f'Final max_display_strategies: {max_display_strategies}')

    try:
        # 测试主查询
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
            GROUP BY s.id, s.name, s.symbol, s.type, s.parameters, s.enabled, s.final_score,
                     s.created_at, s.generation, s.cycle
            ORDER BY COUNT(t.id) DESC, s.final_score DESC, s.created_at DESC
            LIMIT %s
        ''', ('STRAT_%', max_display_strategies))
        
        rows = cursor.fetchall()
        print(f'Main query success: {len(rows)} rows')
        
        # 测试第一行的tuple解包
        if rows:
            row = rows[0]
            print(f'First row length: {len(row)}')
            print(f'First row content: {row}')
            try:
                sid, name, symbol, stype, params, enabled, score, created_at, generation, cycle, total_trades, wins, total_pnl, avg_pnl = row
                print(f'Tuple unpack success for {sid}')
            except Exception as unpack_error:
                print(f'Tuple unpack failed: {unpack_error}')
        
    except Exception as e:
        print(f'Main query error: {e}')
        traceback.print_exc()

    conn.close()

if __name__ == "__main__":
    test_strategy_query() 