#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略评分修正脚本
修正虚假高分策略，确保评分基于真实交易表现
"""

import psycopg2
from datetime import datetime

def fix_strategy_scores():
    conn = psycopg2.connect(
        host='localhost', 
        database='quantitative', 
        user='quant_user', 
        password='chenfei0421'
    )
    conn.autocommit = True
    cursor = conn.cursor()
    
    print("🔧 ===== 修正策略评分系统 =====")
    
    # 1. 重新计算所有策略的真实评分
    cursor.execute("""
        SELECT s.id, s.name, s.final_score,
               COUNT(t.id) as actual_trades,
               COUNT(CASE WHEN t.pnl > 0 THEN 1 END) as wins,
               SUM(t.pnl) as total_pnl,
               AVG(t.pnl) as avg_pnl,
               s.created_at
        FROM strategies s
        LEFT JOIN strategy_trade_logs t ON s.id = t.strategy_id
        GROUP BY s.id, s.name, s.final_score, s.created_at
        ORDER BY s.final_score DESC
    """)
    
    strategies = cursor.fetchall()
    
    fixed_count = 0
    
    print("修正策略评分:")
    print("策略ID        旧评分  新评分  交易次数  胜率    总盈亏    修正原因")
    print("-" * 80)
    
    for row in strategies:
        sid, name, old_score, trades, wins, total_pnl, avg_pnl, created = row
        
        # 计算真实评分
        win_rate = (wins / trades * 100) if trades > 0 else 0
        total_pnl = total_pnl or 0
        
        # 基础分数：根据真实交易表现
        if trades == 0:
            new_score = 30.0  # 无交易记录
            reason = "无交易记录"
        elif trades < 5:
            # 交易太少，最高只能60分
            base_score = 40.0
            trade_bonus = trades * 3  # 每次交易+3分
            win_bonus = win_rate * 0.2  # 胜率加分
            pnl_bonus = min(10, total_pnl * 2)  # PNL加分，最多10分
            new_score = min(60.0, base_score + trade_bonus + win_bonus + pnl_bonus)
            reason = f"交易太少({trades}次)"
        elif trades < 10:
            # 中等交易量，最高75分
            base_score = 50.0
            win_bonus = win_rate * 0.3
            pnl_bonus = min(15, total_pnl * 1.5)
            consistency_bonus = 5.0 if win_rate >= 60 else 0
            new_score = min(75.0, base_score + win_bonus + pnl_bonus + consistency_bonus)
            reason = f"中等验证({trades}次)"
        else:
            # 充分交易量，可以高分
            base_score = 60.0
            win_bonus = win_rate * 0.4
            pnl_bonus = min(25, total_pnl * 1.0)
            consistency_bonus = 10.0 if win_rate >= 70 else 5.0 if win_rate >= 60 else 0
            volume_bonus = min(5, (trades - 10) * 0.5)  # 交易量奖励
            new_score = min(95.0, base_score + win_bonus + pnl_bonus + consistency_bonus + volume_bonus)
            reason = f"充分验证({trades}次)"
        
        # 特殊情况：亏损策略严重降分
        if total_pnl < -5:
            new_score = max(20.0, new_score - 20)
            reason += "+亏损惩罚"
        
        # 如果评分变化超过5分，进行修正
        if abs(new_score - old_score) > 5:
            cursor.execute("""
                UPDATE strategies 
                SET final_score = %s 
                WHERE id = %s
            """, (new_score, sid))
            
            print(f"{sid:<12} {old_score:6.1f}  {new_score:6.1f}  {trades:6d}次   {win_rate:5.1f}%  {total_pnl:+7.2f}U  {reason}")
            fixed_count += 1
    
    print(f"\n✅ 修正了 {fixed_count} 个策略的评分")
    
    # 2. 获取修正后的前20优质策略（真实排名）
    print(f"\n🏆 ===== 修正后前20优质策略 =====")
    
    cursor.execute("""
        SELECT s.id, s.name, s.final_score,
               COUNT(t.id) as trades,
               COUNT(CASE WHEN t.pnl > 0 THEN 1 END) as wins,
               SUM(t.pnl) as total_pnl
        FROM strategies s
        LEFT JOIN strategy_trade_logs t ON s.id = t.strategy_id
        WHERE s.enabled = 1
        GROUP BY s.id, s.name, s.final_score
        ORDER BY s.final_score DESC
        LIMIT 20
    """)
    
    top_strategies = cursor.fetchall()
    
    print("排名  策略ID      策略名                     评分   交易  胜率   盈亏      状态")
    print("-" * 85)
    
    qualified_for_real = 0
    
    for i, row in enumerate(top_strategies, 1):
        sid, name, score, trades, wins, total_pnl = row
        win_rate = (wins / trades * 100) if trades > 0 else 0
        total_pnl = total_pnl or 0
        
        # 状态评估
        if trades >= 10 and win_rate >= 60 and total_pnl > 0:
            status = "🌟可真实交易"
            qualified_for_real += 1
        elif trades >= 5 and win_rate >= 50:
            status = "⭐继续验证"
        elif trades >= 3:
            status = "📊模拟观察"
        else:
            status = "🔍待激活"
        
        print(f"{i:2d}.   {sid:<10} {name[:25]:<25} {score:5.1f}  {trades:4d}  {win_rate:5.1f}% {total_pnl:+7.2f}U  {status}")
    
    print(f"\n💰 符合真实交易条件: {qualified_for_real}个")
    
    # 3. 激活交易信号生成
    if qualified_for_real == 0:
        print(f"\n🚀 ===== 激活交易验证 =====")
        print("由于暂无合格真实交易策略，激活更多模拟交易验证...")
        
        # 为前10个策略强制生成信号
        cursor.execute("""
            SELECT id, name, symbol, final_score 
            FROM strategies 
            WHERE enabled = 1 AND final_score >= 40
            ORDER BY final_score DESC 
            LIMIT 10
        """)
        
        active_strategies = cursor.fetchall()
        signals_created = 0
        
        for strategy in active_strategies:
            sid, name, symbol, score = strategy
            
            # 为每个策略创建2个信号
            for i in range(2):
                signal_type = 'buy' if i == 0 else 'sell'
                price = 0.15 if not symbol or 'DOGE' in symbol.upper() else 105000
                quantity = 50.0 if price < 1 else 0.001
                confidence = min(90.0, score)
                
                cursor.execute("""
                    INSERT INTO trading_signals 
                    (strategy_id, symbol, signal_type, price, quantity, confidence, timestamp, executed)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, 0)
                """, (sid, symbol or 'DOGE/USDT', signal_type, price, quantity, confidence))
                
                signals_created += 1
        
        print(f"✅ 为验证创建了 {signals_created} 个新信号")
    
    conn.close()
    
    return {
        'fixed_count': fixed_count,
        'top_strategies': len(top_strategies),
        'qualified_for_real': qualified_for_real
    }

if __name__ == "__main__":
    result = fix_strategy_scores()
    print(f"\n📋 修正总结:")
    print(f"  🔧 修正策略数: {result['fixed_count']}")
    print(f"  🏆 优质策略数: {result['top_strategies']}")
    print(f"  💰 真实交易就绪: {result['qualified_for_real']}个") 