#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略验证脚本 - 检测并清理虚假高分策略
"""

import psycopg2
from datetime import datetime

def verify_and_clean_strategies():
    """验证并清理虚假的高分策略"""
    try:
        print("🔍 开始验证策略真实性...")
        
        # 连接数据库
        conn = psycopg2.connect(
            host='localhost', 
            database='quantitative', 
            user='quant_user', 
            password='chenfei0421'
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # 1. 检查声称有交易但实际没有交易记录的策略
        cursor.execute('''
            SELECT s.id, s.name, s.final_score, s.total_trades, s.win_rate, s.total_return,
                   COUNT(t.id) as actual_trades
            FROM strategies s
            LEFT JOIN strategy_trade_logs t ON s.id = t.strategy_id
            WHERE s.final_score >= 85 AND s.total_trades > 0
            GROUP BY s.id, s.name, s.final_score, s.total_trades, s.win_rate, s.total_return
            HAVING COUNT(t.id) = 0 OR COUNT(t.id) < s.total_trades / 10
        ''')
        
        fake_strategies = cursor.fetchall()
        
        if fake_strategies:
            print(f"🚨 发现 {len(fake_strategies)} 个可疑的虚假高分策略:")
            for sid, name, score, claimed_trades, win_rate, return_val, actual_trades in fake_strategies:
                print(f"  ❌ {name}: {score}分, 声称{claimed_trades}次交易但实际只有{actual_trades}次")
            
            # 2. 将虚假策略降分并标记
            for sid, name, score, claimed_trades, win_rate, return_val, actual_trades in fake_strategies:
                # 根据实际交易数据重新计算合理分数
                if actual_trades == 0:
                    new_score = 30.0  # 没有实际交易记录的策略降到30分
                    new_trades = 0
                    new_win_rate = 0.0
                    new_return = 0.0
                else:
                    # 有少量交易记录的，给予基础分数
                    new_score = min(50.0, 40.0 + actual_trades)
                    new_trades = actual_trades
                    new_win_rate = win_rate
                    new_return = return_val
                
                cursor.execute('''
                    UPDATE strategies 
                    SET final_score = %s, total_trades = %s, win_rate = %s, total_return = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (new_score, new_trades, new_win_rate, new_return, sid))
                
                print(f"  🔧 修正策略 {name}: {score}分 → {new_score}分")
        else:
            print("✅ 所有高分策略验证通过")
        
        # 3. 显示验证后的优质策略
        cursor.execute('''
            SELECT s.id, s.name, s.final_score, s.total_trades, s.win_rate, s.total_return,
                   COUNT(t.id) as actual_trades,
                   s.created_at, s.updated_at
            FROM strategies s
            LEFT JOIN strategy_trade_logs t ON s.id = t.strategy_id
            WHERE s.final_score >= 40
            GROUP BY s.id, s.name, s.final_score, s.total_trades, s.win_rate, s.total_return,
                     s.created_at, s.updated_at
            ORDER BY 
                CASE 
                    WHEN COUNT(t.id) > 0 THEN s.final_score + 10  -- 有真实交易记录的策略优先
                    ELSE s.final_score
                END DESC,
                s.updated_at DESC
            LIMIT 30
        ''')
        
        frontend_strategies = cursor.fetchall()
        
        print(f"\n📺 验证后前端将显示 {len(frontend_strategies)} 个验证过的优质策略")
        print("前10名策略:")
        for i, (sid, name, score, trades, win_rate, return_val, actual_trades, created, updated) in enumerate(frontend_strategies[:10]):
            real_flag = "✅真实" if actual_trades > 0 else "⚠️模拟"
            print(f"  {i+1:2d}. {name[:25]:<25}: {score:5.1f}分 {real_flag} (实际交易:{actual_trades:2d}次)")
        
        # 4. 获取用于自动交易的前2名策略
        cursor.execute('''
            SELECT s.id, s.name, s.final_score, s.total_trades, s.win_rate, s.total_return,
                   COUNT(t.id) as actual_trades,
                   SUM(CASE WHEN t.pnl > 0 THEN 1 ELSE 0 END) as actual_wins
            FROM strategies s
            LEFT JOIN strategy_trade_logs t ON s.id = t.strategy_id
            WHERE s.enabled = 1 AND s.final_score >= 50
            GROUP BY s.id, s.name, s.final_score, s.total_trades, s.win_rate, s.total_return
            HAVING COUNT(t.id) > 0  -- 必须有真实交易记录
            ORDER BY 
                (COUNT(t.id) * 0.3 + s.final_score * 0.7) DESC,  -- 综合真实交易数和评分
                s.final_score DESC
            LIMIT 2
        ''')
        
        top_strategies = cursor.fetchall()
        
        print(f"\n🎯 自动交易推荐前 {len(top_strategies)} 名策略(基于真实交易记录):")
        for i, (sid, name, score, trades, win_rate, return_val, actual_trades, actual_wins) in enumerate(top_strategies):
            real_win_rate = (actual_wins / actual_trades * 100) if actual_trades > 0 else 0
            print(f"  {i+1}. {name}: {score:.1f}分 | 真实交易:{actual_trades}次 | 真实胜率:{real_win_rate:.1f}%")
        
        if len(top_strategies) == 0:
            print("⚠️ 没有找到有真实交易记录的策略，建议等待系统生成更多真实交易数据")
        
        conn.close()
        print("\n✅ 策略验证和清理完成")
        return True
        
    except Exception as e:
        print(f"❌ 策略验证失败: {e}")
        return False

if __name__ == "__main__":
    verify_and_clean_strategies() 