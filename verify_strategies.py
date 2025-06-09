#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略真实性验证脚本
检查高分策略的可信度和系统实际运行情况
"""

import psycopg2
from datetime import datetime, timedelta

def verify_strategy_authenticity():
    conn = psycopg2.connect(
        host='localhost', 
        database='quantitative', 
        user='quant_user', 
        password='chenfei0421'
    )
    cursor = conn.cursor()
    
    print("🔍 ===== 策略真实性深度验证 =====")
    print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 检查高分策略的详细信息
    cursor.execute("""
        SELECT s.id, s.name, s.final_score, s.created_at,
               COUNT(t.id) as trades,
               MIN(t.timestamp) as first_trade,
               MAX(t.timestamp) as last_trade,
               SUM(t.pnl) as total_pnl,
               AVG(t.pnl) as avg_pnl
        FROM strategies s
        LEFT JOIN strategy_trade_logs t ON s.id = t.strategy_id
        WHERE s.final_score >= 90
        GROUP BY s.id, s.name, s.final_score, s.created_at
        ORDER BY s.final_score DESC
        LIMIT 15
    """)
    
    high_score_strategies = cursor.fetchall()
    
    print(f"\n📊 发现 {len(high_score_strategies)} 个90+分策略:")
    print("ID        策略名                     评分   交易次数  创建时间差    交易时间跨度   总盈亏     可信度")
    print("-" * 95)
    
    suspicious_count = 0
    for row in high_score_strategies:
        sid, name, score, created, trades, first_trade, last_trade, total_pnl, avg_pnl = row
        
        # 计算策略存在时间
        if created:
            age_hours = (datetime.now() - created).total_seconds() / 3600
        else:
            age_hours = 999  # 很老的策略
        
        # 计算交易时间跨度
        if first_trade and last_trade:
            trade_span_hours = (last_trade - first_trade).total_seconds() / 3600
        else:
            trade_span_hours = 0
        
        # 可信度评估
        credibility = "✅真实"
        if trades == 0:
            credibility = "❌无交易"
            suspicious_count += 1
        elif trades < 5 and score >= 95:
            credibility = "🚨可疑-交易太少"
            suspicious_count += 1
        elif age_hours < 0.5 and score >= 95:
            credibility = "🚨可疑-太新"
            suspicious_count += 1
        elif trades > 0 and trade_span_hours < 0.1:
            credibility = "🚨可疑-交易集中"
            suspicious_count += 1
        elif avg_pnl and avg_pnl > 50:
            credibility = "🚨可疑-盈利过高"
            suspicious_count += 1
        
        print(f"{sid:<8} {name[:25]:<25} {score:5.1f}  {trades:6d}次   {age_hours:7.1f}h    {trade_span_hours:8.1f}h    {total_pnl or 0:+7.2f}U  {credibility}")
    
    print(f"\n⚠️  可疑策略数量: {suspicious_count}/{len(high_score_strategies)}")
    
    # 2. 检查策略进化活跃度
    print(f"\n🔄 ===== 策略进化活跃度检查 =====")
    
    # 最近创建的策略
    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN created_at >= NOW() - INTERVAL '1 hour' THEN 1 END) as last_hour,
               COUNT(CASE WHEN created_at >= NOW() - INTERVAL '30 minutes' THEN 1 END) as last_30min,
               COUNT(CASE WHEN created_at >= NOW() - INTERVAL '10 minutes' THEN 1 END) as last_10min
        FROM strategies
    """)
    
    strategy_activity = cursor.fetchone()
    total_strategies, last_hour, last_30min, last_10min = strategy_activity
    
    print(f"策略创建活跃度:")
    print(f"  📈 总策略数: {total_strategies}")
    print(f"  🕐 最近1小时: {last_hour}个新策略")
    print(f"  🕕 最近30分钟: {last_30min}个新策略") 
    print(f"  🕙 最近10分钟: {last_10min}个新策略")
    
    if last_10min == 0:
        print("  ❌ 警告: 最近10分钟无新策略，进化可能停止")
    else:
        print(f"  ✅ 进化正常: 平均{10/last_10min:.1f}分钟创建1个策略" if last_10min > 0 else "")
    
    # 3. 检查交易执行活跃度
    print(f"\n📈 ===== 交易执行活跃度检查 =====")
    
    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN timestamp >= NOW() - INTERVAL '1 hour' THEN 1 END) as last_hour,
               COUNT(CASE WHEN timestamp >= NOW() - INTERVAL '30 minutes' THEN 1 END) as last_30min,
               COUNT(CASE WHEN timestamp >= NOW() - INTERVAL '10 minutes' THEN 1 END) as last_10min,
               SUM(CASE WHEN timestamp >= NOW() - INTERVAL '1 hour' THEN pnl ELSE 0 END) as hour_pnl
        FROM strategy_trade_logs
    """)
    
    trade_activity = cursor.fetchone()
    total_trades, hour_trades, min30_trades, min10_trades, hour_pnl = trade_activity
    
    print(f"交易执行活跃度:")
    print(f"  📊 总交易数: {total_trades}")
    print(f"  🕐 最近1小时: {hour_trades}次交易，盈亏{hour_pnl or 0:+.2f}U")
    print(f"  🕕 最近30分钟: {min30_trades}次交易")
    print(f"  🕙 最近10分钟: {min10_trades}次交易")
    
    if min10_trades == 0:
        print("  ❌ 警告: 最近10分钟无交易执行")
    else:
        print("  ✅ 交易执行正常")
    
    # 4. 获取前20优质策略
    print(f"\n🏆 ===== 前20优质策略（真实可信）=====")
    
    cursor.execute("""
        SELECT s.id, s.name, s.final_score,
               COUNT(t.id) as trades,
               SUM(t.pnl) as total_pnl,
               COUNT(CASE WHEN t.pnl > 0 THEN 1 END) as wins,
               s.created_at
        FROM strategies s
        LEFT JOIN strategy_trade_logs t ON s.id = t.strategy_id
        WHERE s.enabled = 1
        GROUP BY s.id, s.name, s.final_score, s.created_at
        HAVING COUNT(t.id) >= 3  -- 至少3次交易
        ORDER BY 
            CASE 
                WHEN COUNT(t.id) >= 10 THEN s.final_score 
                ELSE s.final_score * 0.8  -- 交易少的策略降权
            END DESC
        LIMIT 20
    """)
    
    top_strategies = cursor.fetchall()
    
    print("排名  策略ID      策略名                     评分   交易  胜率   盈亏      推荐度")
    print("-" * 85)
    
    for i, row in enumerate(top_strategies, 1):
        sid, name, score, trades, total_pnl, wins, created = row
        win_rate = (wins / trades * 100) if trades > 0 else 0
        
        # 推荐度评估
        if trades >= 10 and win_rate >= 60 and (total_pnl or 0) > 0:
            recommendation = "🌟推荐真实交易"
        elif trades >= 5 and win_rate >= 50:
            recommendation = "⭐继续验证"
        else:
            recommendation = "📊模拟观察"
        
        print(f"{i:2d}.   {sid:<10} {name[:25]:<25} {score:5.1f}  {trades:4d}  {win_rate:5.1f}% {total_pnl or 0:+7.2f}U  {recommendation}")
    
    print(f"\n✅ 发现 {len(top_strategies)} 个真实可信的优质策略")
    
    # 5. 推荐真实交易策略
    qualified_for_real = [s for s in top_strategies if s[3] >= 10 and (s[5]/s[3]*100 >= 60) and (s[4] or 0) > 0]
    
    print(f"\n💰 ===== 真实交易推荐 =====")
    print(f"符合真实交易条件的策略: {len(qualified_for_real)}个")
    
    if len(qualified_for_real) >= 3:
        print("🚀 系统已准备好启动真实交易！")
        print("推荐选择前3个策略进行真实自动交易:")
        for i, strategy in enumerate(qualified_for_real[:3], 1):
            sid, name, score, trades, total_pnl, wins, created = strategy
            win_rate = wins / trades * 100
            print(f"  {i}. {name[:30]} - {score:.1f}分, {trades}次交易, {win_rate:.1f}%胜率, {total_pnl:+.2f}U")
    else:
        print("⏳ 需要更多验证，建议继续模拟交易")
    
    conn.close()
    
    return {
        'suspicious_count': suspicious_count,
        'total_high_score': len(high_score_strategies),
        'qualified_for_real': len(qualified_for_real),
        'top_strategies': top_strategies[:20]
    }

if __name__ == "__main__":
    result = verify_strategy_authenticity()
    print(f"\n📋 验证总结:")
    print(f"  🚨 可疑高分策略: {result['suspicious_count']}/{result['total_high_score']}")
    print(f"  ✅ 真实优质策略: {len(result['top_strategies'])}个")
    print(f"  💰 合格真实交易: {result['qualified_for_real']}个") 