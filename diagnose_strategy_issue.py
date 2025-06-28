#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
诊断策略启用状态问题的确切位置
"""

import psycopg2
import traceback

def diagnose_issue():
    """诊断问题"""
    print("🔍 === 开始诊断策略启用状态问题 ===")
    
    try:
        # 连接数据库
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        # 检查1：前21个策略
        print("\n1️⃣ 检查前21个策略...")
        cursor.execute("""
            SELECT id, name, final_score 
            FROM strategies 
            WHERE id LIKE 'STRAT_%' AND final_score IS NOT NULL
            ORDER BY final_score DESC
            LIMIT 21
        """)
        
        top_strategies = cursor.fetchall()
        print(f"找到 {len(top_strategies)} 个策略")
        
        if top_strategies:
            strategy_ids = [s[0] for s in top_strategies]
            print(f"策略ID列表: {strategy_ids[:3]}...")  # 只显示前3个
            
            # 检查2：启用这些策略
            print("\n2️⃣ 尝试启用前21个策略...")
            cursor.execute("""
                UPDATE strategies 
                SET enabled = 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ANY(%s)
            """, (strategy_ids,))
            
            print(f"✅ 已启用 {cursor.rowcount} 个策略")
            
            # 检查3：统计启用状态
            print("\n3️⃣ 检查启用状态统计...")
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_strategies,
                    COUNT(*) FILTER (WHERE enabled = 1) as enabled_strategies,
                    COUNT(*) FILTER (WHERE enabled = 0) as disabled_strategies
                FROM strategies 
                WHERE id LIKE 'STRAT_%'
            """)
            
            stats = cursor.fetchone()
            print(f"统计结果类型: {type(stats)}")
            print(f"统计结果内容: {stats}")
            
            if stats:
                total, enabled, disabled = stats
                print(f"总策略: {total}, 启用: {enabled}, 停用: {disabled}")
            
            # 检查4：提交事务
            print("\n4️⃣ 提交数据库事务...")
            conn.commit()
            print("✅ 事务已提交")
            
        conn.close()
        print("\n✅ 诊断完成，没有发现错误")
        
    except Exception as e:
        print(f"❌ 诊断过程中出错: {e}")
        print("错误详细信息:")
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_issue()
