#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复trading_orders表结构
添加缺失的realized_pnl等关键列，解决自动交易引擎崩溃问题
"""

import sqlite3

def fix_trading_orders_table():
    """修复trading_orders表结构"""
    print("🔧 修复trading_orders表结构...")
    
    conn = sqlite3.connect('quantitative.db')
    cursor = conn.cursor()
    
    try:
        # 检查当前表结构
        cursor.execute("PRAGMA table_info(trading_orders)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"📋 当前表列: {columns}")
        
        # 需要添加的列
        required_columns = {
            'realized_pnl': 'REAL DEFAULT 0.0',
            'unrealized_pnl': 'REAL DEFAULT 0.0',
            'commission': 'REAL DEFAULT 0.0',
            'net_pnl': 'REAL DEFAULT 0.0',
            'updated_time': 'TEXT DEFAULT CURRENT_TIMESTAMP'
        }
        
        # 添加缺失的列
        for column_name, column_def in required_columns.items():
            if column_name not in columns:
                print(f"  ➕ 添加列: {column_name}")
                cursor.execute(f'ALTER TABLE trading_orders ADD COLUMN {column_name} {column_def}')
            else:
                print(f"  ✅ 列已存在: {column_name}")
        
        # 为现有订单计算realized_pnl
        print("💰 计算现有订单的realized_pnl...")
        
        # 获取已执行的订单
        cursor.execute("""
            SELECT id, strategy_id, symbol, side, quantity, price, execution_price 
            FROM trading_orders 
            WHERE status = 'executed' AND execution_price IS NOT NULL
        """)
        
        executed_orders = cursor.fetchall()
        print(f"📊 找到 {len(executed_orders)} 个已执行订单")
        
        for order in executed_orders:
            order_id, strategy_id, symbol, side, quantity, price, execution_price = order
            
            # 简单的PnL计算
            if side.upper() == 'BUY':
                # 买单：执行价格低于预期价格为正收益
                realized_pnl = (price - execution_price) * quantity
            else:  # SELL
                # 卖单：执行价格高于预期价格为正收益  
                realized_pnl = (execution_price - price) * quantity
            
            # 更新realized_pnl
            cursor.execute("""
                UPDATE trading_orders 
                SET realized_pnl = ?, net_pnl = ? 
                WHERE id = ?
            """, (realized_pnl, realized_pnl, order_id))
        
        # 创建交易订单视图，方便查询
        print("📋 创建交易订单视图...")
        cursor.execute('''
            CREATE VIEW IF NOT EXISTS order_performance AS
            SELECT 
                o.id,
                o.strategy_id,
                o.symbol,
                o.side,
                o.quantity,
                o.price as expected_price,
                o.execution_price,
                o.realized_pnl,
                o.commission,
                o.net_pnl,
                o.status,
                o.created_time,
                o.executed_time,
                s.name as strategy_name
            FROM trading_orders o
            LEFT JOIN strategies s ON o.strategy_id = s.id
            WHERE o.status = 'executed'
            ORDER BY o.executed_time DESC
        ''')
        
        conn.commit()
        print("✅ trading_orders表修复完成！")
        
        # 验证修复结果
        cursor.execute("PRAGMA table_info(trading_orders)")
        new_columns = [col[1] for col in cursor.fetchall()]
        print(f"📋 修复后表列: {new_columns}")
        
        cursor.execute("SELECT COUNT(*) FROM trading_orders WHERE realized_pnl IS NOT NULL")
        pnl_count = cursor.fetchone()[0]
        print(f"💰 已设置PnL的订单: {pnl_count} 个")
        
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    fix_trading_orders_table() 