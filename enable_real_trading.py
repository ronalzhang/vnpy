#!/usr/bin/env python3
"""
启用实盘交易模式
将符合条件的策略从验证模式切换到实盘交易模式
"""
import psycopg2
import json
import os
from datetime import datetime
from decimal import Decimal

def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(
        host="localhost",
        database="quantitative",
        user="quant_user",
        password="123abc74531"
    )

def check_api_keys():
    """检查API密钥是否配置"""
    api_key = os.getenv('BINANCE_API_KEY')
    secret_key = os.getenv('BINANCE_SECRET_KEY')
    
    if not api_key or not secret_key:
        print("❌ Binance API密钥未配置")
        return False
    
    print("✅ Binance API密钥已配置")
    return True

def test_api_connection():
    """测试API连接"""
    try:
        import ccxt
        exchange = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'sandbox': False,
            'enableRateLimit': True,
        })
        
        # 测试连接
        balance = exchange.fetch_balance()
        print(f"✅ API连接成功，USDT余额: {balance.get('USDT', {}).get('total', 0)}")
        return True, balance
        
    except Exception as e:
        print(f"❌ API连接失败: {e}")
        return False, None

def enable_real_trading():
    """启用实盘交易"""
    print("🚀 启用实盘交易模式")
    print("=" * 50)
    
    # 1. 检查API密钥
    if not check_api_keys():
        return False
    
    # 2. 测试API连接
    api_ok, balance = test_api_connection()
    if not api_ok:
        return False
    
    # 3. 检查账户余额
    usdt_total = balance.get('USDT', {}).get('total', 0) if balance else 0
    usdt_balance = float(usdt_total) if usdt_total is not None else 0.0
    if usdt_balance < 100.0:  # 最低100 USDT
        print(f"⚠️ USDT余额不足，当前: {usdt_balance}, 建议最低: 100")
        return False
    
    # 4. 更新数据库中的交易模式
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 获取符合实盘交易条件的策略
        cursor.execute("""
            SELECT id, name, final_score, total_trades 
            FROM strategies 
            WHERE enabled = 1 
            AND qualified_for_trading = 1 
            AND final_score >= 60
            ORDER BY final_score DESC
            LIMIT 10
        """)
        
        qualified_strategies = cursor.fetchall()
        
        if not qualified_strategies:
            print("❌ 没有符合实盘交易条件的策略")
            return False
        
        print(f"📊 找到 {len(qualified_strategies)} 个符合条件的策略:")
        for strategy in qualified_strategies:
            print(f"   - {strategy[1]} (评分: {strategy[2]}, 交易次数: {strategy[3]})")
        
        # 5. 选择前5个最佳策略启用实盘交易
        top_strategies = qualified_strategies[:5]
        
        for strategy in top_strategies:
            strategy_id = strategy[0]
            strategy_name = strategy[1]
            
            # 更新策略为实盘交易模式
            cursor.execute("""
                UPDATE strategies 
                SET trade_type = 'real', 
                    capital_allocation = %s,
                    notes = 'Real trading enabled at ' || %s
                WHERE id = %s
            """, (
                min(1000.0, usdt_balance / 5),  # 平均分配资金
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                strategy_id
            ))
            
            print(f"✅ 策略 {strategy_name} 已启用实盘交易")
        
        # 6. 插入实盘交易启用日志
        cursor.execute("""
            INSERT INTO strategy_optimization_logs 
            (strategy_id, action, details, timestamp, parameters)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            'SYSTEM',
            'enable_real_trading',
            f'启用 {len(top_strategies)} 个策略的实盘交易模式',
            datetime.now(),
            json.dumps({
                'strategies_count': len(top_strategies),
                'total_balance': float(usdt_balance),
                'allocation_per_strategy': float(min(1000.0, usdt_balance / 5))
            })
        ))
        
        conn.commit()
        print(f"\n🎉 实盘交易启用成功!")
        print(f"   - 启用策略数量: {len(top_strategies)}")
        print(f"   - 可用余额: {usdt_balance:.2f} USDT")
        print(f"   - 每策略分配: {min(1000.0, usdt_balance / 5):.2f} USDT")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 启用实盘交易失败: {e}")
        return False
        
    finally:
        cursor.close()
        conn.close()

def disable_real_trading():
    """关闭实盘交易，切换回验证模式"""
    print("🛑 关闭实盘交易模式")
    print("=" * 50)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 将所有实盘交易策略切换回验证模式
        cursor.execute("""
            UPDATE strategies 
            SET trade_type = 'validation',
                notes = 'Switched back to validation at ' || %s
            WHERE trade_type = 'real'
        """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),))
        
        affected_rows = cursor.rowcount
        
        # 记录日志
        cursor.execute("""
            INSERT INTO strategy_optimization_logs 
            (strategy_id, action, details, timestamp, parameters)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            'SYSTEM',
            'disable_real_trading',
            f'关闭 {affected_rows} 个策略的实盘交易模式',
            datetime.now(),
            json.dumps({'affected_strategies': affected_rows})
        ))
        
        conn.commit()
        print(f"✅ 已关闭 {affected_rows} 个策略的实盘交易")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 关闭实盘交易失败: {e}")
        return False
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--disable':
        disable_real_trading()
    else:
        enable_real_trading() 