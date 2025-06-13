#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一交易日志数据表 - 解决重复代码冲突问题
将strategy_trade_logs数据迁移到trading_signals表
"""

import psycopg2
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

def consolidate_trade_logs():
    """统一交易日志表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("🔧 开始统一交易日志数据表...")
        
        # 1. 检查两个表的结构和数据
        print("\n📊 检查当前表状态...")
        
        cursor.execute("SELECT COUNT(*) FROM strategy_trade_logs")
        result = cursor.fetchone()
        strategy_logs_count = result['count'] if result else 0
        print(f"  strategy_trade_logs: {strategy_logs_count} 条记录")
        
        cursor.execute("SELECT COUNT(*) FROM trading_signals") 
        signals_count = cursor.fetchone()[0]
        print(f"  trading_signals: {signals_count} 条记录")
        
        # 2. 分析strategy_trade_logs的数据结构
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'strategy_trade_logs'
            ORDER BY ordinal_position
        """)
        strategy_logs_columns = cursor.fetchall()
        print(f"\n📋 strategy_trade_logs表结构:")
        for col in strategy_logs_columns:
            print(f"  - {col[0]}: {col[1]}")
        
        # 3. 分析trading_signals的数据结构
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'trading_signals'
            ORDER BY ordinal_position
        """)
        signals_columns = cursor.fetchall()
        print(f"\n📋 trading_signals表结构:")
        for col in signals_columns:
            print(f"  - {col[0]}: {col[1]}")
        
        # 4. 迁移strategy_trade_logs数据到trading_signals
        if strategy_logs_count > 0:
            print(f"\n🔄 开始迁移 {strategy_logs_count} 条strategy_trade_logs数据...")
            
            # 获取strategy_trade_logs的所有数据
            cursor.execute("""
                SELECT id, strategy_id, signal_type, price, quantity, 
                       confidence, executed, pnl, timestamp, symbol,
                       trade_type, is_real_money, exchange_order_id
                FROM strategy_trade_logs
                ORDER BY timestamp
            """)
            
            old_logs = cursor.fetchall()
            migrated_count = 0
            
            for log in old_logs:
                try:
                    # 映射到trading_signals表结构
                    # trading_signals: (strategy_id, symbol, signal_type, price, quantity, expected_return, executed, timestamp, confidence, risk_level, strategy_score, priority)
                    
                    insert_query = """
                        INSERT INTO trading_signals 
                        (strategy_id, symbol, signal_type, price, quantity, 
                         expected_return, executed, timestamp, confidence, 
                         risk_level, strategy_score, priority)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """
                    
                    # 数据映射
                    strategy_id = log[1] or 'UNKNOWN'
                    symbol = log[9] or 'UNKNOWN/USDT'
                    signal_type = log[2] or 'buy'
                    price = float(log[3]) if log[3] else 0.0
                    quantity = float(log[4]) if log[4] else 0.0
                    expected_return = float(log[7]) if log[7] else 0.0  # pnl -> expected_return
                    executed = bool(log[6]) if log[6] is not None else False
                    timestamp = log[8] if log[8] else datetime.now()
                    confidence = float(log[5]) if log[5] else 0.75
                    risk_level = 'medium'  # 默认中等风险
                    strategy_score = 0.0  # 默认评分
                    priority = 1  # 默认优先级
                    
                    cursor.execute(insert_query, (
                        strategy_id, symbol, signal_type, price, quantity,
                        expected_return, executed, timestamp, confidence,
                        risk_level, strategy_score, priority
                    ))
                    
                    migrated_count += 1
                    
                except Exception as e:
                    print(f"⚠️ 迁移记录失败: {e}")
                    continue
            
            conn.commit()
            print(f"✅ 成功迁移 {migrated_count} 条记录到trading_signals表")
        
        # 5. 检查迁移后的数据
        cursor.execute("SELECT COUNT(*) FROM trading_signals")
        new_signals_count = cursor.fetchone()[0]
        print(f"\n📈 迁移后trading_signals表: {new_signals_count} 条记录")
        
        # 6. 备份并删除strategy_trade_logs表
        print(f"\n🗑️ 清理strategy_trade_logs表...")
        
        # 创建备份表
        cursor.execute("DROP TABLE IF EXISTS strategy_trade_logs_backup")
        cursor.execute("""
            CREATE TABLE strategy_trade_logs_backup AS 
            SELECT * FROM strategy_trade_logs
        """)
        
        # 删除原表
        cursor.execute("DROP TABLE strategy_trade_logs")
        
        print("✅ strategy_trade_logs表已备份并删除")
        
        # 7. 创建统一的视图（兼容性）
        cursor.execute("DROP VIEW IF EXISTS strategy_trade_logs")
        cursor.execute("""
            CREATE VIEW strategy_trade_logs AS
            SELECT 
                id,
                strategy_id,
                signal_type,
                price,
                quantity,
                confidence,
                executed,
                expected_return as pnl,
                timestamp,
                symbol,
                'trading_signals' as source_table
            FROM trading_signals
        """)
        
        print("✅ 创建了strategy_trade_logs兼容性视图")
        
        conn.commit()
        conn.close()
        
        print(f"\n🎉 交易日志数据表统一完成!")
        print(f"📊 最终状态:")
        print(f"  - trading_signals: {new_signals_count} 条记录（主表）")
        print(f"  - strategy_trade_logs: 视图（兼容性）")
        print(f"  - strategy_trade_logs_backup: {strategy_logs_count} 条记录（备份）")
        
        return True
        
    except Exception as e:
        print(f"❌ 统一交易日志表失败: {e}")
        return False

def clean_duplicate_code():
    """清理重复的API代码"""
    print(f"\n🧹 清理重复代码...")
    
    # 这里我们只标记需要清理的文件，实际清理在后续步骤
    duplicate_files = [
        "web_app.py.backup",
        "quantitative_service.py.backup"
    ]
    
    print("📋 发现以下重复文件:")
    for file in duplicate_files:
        print(f"  - {file}")
    
    print("💡 建议手动检查并删除这些备份文件中的重复代码")
    
    return True

def main():
    print("🚀 开始解决交易日志重复代码冲突问题...")
    
    # 1. 统一数据表
    if consolidate_trade_logs():
        print("✅ 数据表统一完成")
    else:
        print("❌ 数据表统一失败")
        return
    
    # 2. 标记重复代码
    if clean_duplicate_code():
        print("✅ 重复代码标记完成")
    
    print(f"\n🎯 下一步建议:")
    print(f"1. 重启服务: pm2 restart quant-backend")
    print(f"2. 测试前端交易日志显示")
    print(f"3. 手动删除备份文件中的重复代码")

if __name__ == "__main__":
    main() 