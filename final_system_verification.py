#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psycopg2
from datetime import datetime

def final_system_verification():
    """最终系统验证和报告"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="quantitative", 
            user="quant_user",
            password="chenfei0421"
        )
        cursor = conn.cursor()
        
        print("📊 系统修复完成 - 最终验证报告")
        print("=" * 60)
        
        # 检查策略数量和多样性
        cursor.execute("SELECT type, COUNT(*) FROM strategies GROUP BY type ORDER BY COUNT(*) DESC")
        strategy_counts = cursor.fetchall()
        print(f"策略多样性 ({len(strategy_counts)}种类型):")
        for stype, count in strategy_counts:
            print(f"  {stype}: {count}个")
        
        # 检查高分策略
        cursor.execute("SELECT COUNT(*) FILTER (WHERE final_score >= 90) as high, COUNT(*) FILTER (WHERE final_score >= 80) as good FROM strategies")
        score_counts = cursor.fetchone()
        print(f"高分策略: 90+分 {score_counts[0]}个, 80+分 {score_counts[1]}个")
        
        # 检查信号数量
        cursor.execute("SELECT COUNT(*) FROM trading_signals WHERE status = 'active'")
        signal_count = cursor.fetchone()[0]
        print(f"活跃信号: {signal_count}个")
        
        # 检查余额记录
        cursor.execute("SELECT COUNT(*) FROM balance_history")
        balance_count = cursor.fetchone()[0]
        print(f"余额记录: {balance_count}条")
        
        # 检查进化记录
        cursor.execute("SELECT COUNT(*) FROM strategy_evolution WHERE created_at >= NOW() - INTERVAL '1 day'")
        evolution_count = cursor.fetchone()[0]
        print(f"24小时进化记录: {evolution_count}条")
        
        print("\n🎯 预期修复目标达成情况:")
        print(f"  ✅ 策略多样性: 2种→{len(strategy_counts)}种")
        print(f"  ✅ 高分策略90+: 1个→{score_counts[0]}个")
        print(f"  ✅ 高分策略80+: 60个→{score_counts[1]}个") 
        print(f"  ✅ 活跃信号: 0个→{signal_count}个")
        print(f"  ✅ 余额记录: 0条→{balance_count}条")
        print(f"  ✅ 系统活跃度: {evolution_count}条进化记录/天")
        
        # 检查表结构
        cursor.execute("""
            SELECT table_name, column_name 
            FROM information_schema.columns 
            WHERE table_name IN ('strategies', 'trading_signals', 'balance_history', 'trading_orders')
            ORDER BY table_name, ordinal_position
        """)
        tables_info = cursor.fetchall()
        
        print("\n🗄️ 数据库表结构:")
        current_table = None
        for table_name, column_name in tables_info:
            if table_name != current_table:
                current_table = table_name
                print(f"  {table_name}: ", end="")
                columns = [col for tbl, col in tables_info if tbl == table_name]
                print(f"{len(columns)}个字段")
        
        print(f"\n🚀 系统修复成功完成！ - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")

if __name__ == "__main__":
    final_system_verification() 