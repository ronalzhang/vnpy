#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
紧急清理fake数据脚本
删除所有虚假的90+分策略，重置评分系统
"""

import psycopg2
import json
from datetime import datetime

def emergency_cleanup():
    """紧急清理假数据"""
    
    print("🚨 开始紧急清理fake数据...")
    
    # 连接数据库
    conn = psycopg2.connect(
        host='localhost',
        database='quantitative', 
        user='quant_user',
        password='quant_password_2025'
    )
    cursor = conn.cursor()
    
    try:
        # 1. 找出所有可疑的高分策略（没有交易记录但有高分）
        print("🔍 识别fake策略...")
        cursor.execute("""
            SELECT s.id, s.name, s.final_score, s.total_trades, s.created_at
            FROM strategies s
            LEFT JOIN strategy_trade_logs t ON s.id = t.strategy_id
            WHERE s.final_score >= 85 
            AND t.strategy_id IS NULL
            ORDER BY s.final_score DESC
        """)
        fake_strategies = cursor.fetchall()
        
        print(f"发现 {len(fake_strategies)} 个fake策略:")
        for strategy in fake_strategies:
            print(f"  - {strategy[0]}: {strategy[1]} (评分:{strategy[2]}, 声称交易:{strategy[3]})")
        
        # 2. 删除fake策略
        if fake_strategies:
            fake_ids = [s[0] for s in fake_strategies]
            cursor.execute("DELETE FROM strategies WHERE id = ANY(%s)", (fake_ids,))
            print(f"✅ 删除了 {len(fake_strategies)} 个fake策略")
        
        # 3. 重置所有演化历史的错误评分
        print("🔧 修复演化历史评分...")
        cursor.execute("""
            UPDATE strategy_evolution_history 
            SET score_before = 0, score_after = 0, new_score = 0
            WHERE score_before = 0 AND score_after = 0
        """)
        
        # 4. 为真实策略重新计算评分
        print("💯 重新计算真实策略评分...")
        cursor.execute("""
            SELECT DISTINCT s.id 
            FROM strategies s
            INNER JOIN strategy_trade_logs t ON s.id = t.strategy_id
        """)
        real_strategies = cursor.fetchall()
        
        for (strategy_id,) in real_strategies:
            # 计算真实交易数据
            cursor.execute("""
                SELECT COUNT(*), 
                       AVG(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as win_rate,
                       AVG(pnl) as avg_return
                FROM strategy_trade_logs 
                WHERE strategy_id = %s AND executed = true
            """, (strategy_id,))
            
            trade_data = cursor.fetchone()
            if trade_data and trade_data[0] > 0:
                trade_count = trade_data[0]
                win_rate = trade_data[1] or 0
                avg_return = trade_data[2] or 0
                
                # 基于真实数据计算评分 (转换数据类型)
                avg_return = float(avg_return) if avg_return else 0.0
                win_rate = float(win_rate) if win_rate else 0.0
                trade_count = int(trade_count) if trade_count else 0
                
                real_score = (avg_return * 40) + (win_rate * 40) + (min(trade_count/10, 10) * 2)
                real_score = max(0, min(100, real_score))
                
                # 更新策略评分
                cursor.execute("""
                    UPDATE strategies 
                    SET final_score = %s, 
                        total_trades = %s,
                        win_rate = %s,
                        total_return = %s
                    WHERE id = %s
                """, (real_score, trade_count, win_rate, avg_return, strategy_id))
                
                print(f"  ✅ {strategy_id}: {trade_count}交易, {win_rate:.2%}胜率, 评分:{real_score:.1f}")
        
        # 5. 创建数据清理报告
        cleanup_report = {
            "cleanup_time": datetime.now().isoformat(),
            "fake_strategies_removed": len(fake_strategies),
            "fake_strategy_details": [
                {
                    "id": s[0],
                    "name": s[1], 
                    "fake_score": s[2],
                    "claimed_trades": s[3],
                    "created_at": s[4].isoformat() if s[4] else None
                }
                for s in fake_strategies
            ],
            "real_strategies_count": len(real_strategies),
            "message": "所有fake数据已清理，只保留有真实交易记录的策略"
        }
        
        with open('fake_data_cleanup_report.json', 'w', encoding='utf-8') as f:
            json.dump(cleanup_report, f, ensure_ascii=False, indent=2)
        
        conn.commit()
        print("✅ 数据清理完成！")
        print("📄 清理报告已保存至 fake_data_cleanup_report.json")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 清理过程出错: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    emergency_cleanup() 