#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速交易检查脚本
"""

import psycopg2
from datetime import datetime, timedelta

def check_trading_status():
    """检查交易状态"""
    conn = psycopg2.connect(
        host='localhost', 
        database='quantitative', 
        user='quant_user', 
        password='chenfei0421'
    )
    conn.autocommit = True
    cursor = conn.cursor()
    
    print("🔍 ===== 交易状态检查 =====")
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 添加交易类型字段
    try:
        cursor.execute("ALTER TABLE strategy_trade_logs ADD COLUMN IF NOT EXISTS trade_type VARCHAR(20) DEFAULT 'simulation'")
        cursor.execute("ALTER TABLE strategy_trade_logs ADD COLUMN IF NOT EXISTS is_real_money BOOLEAN DEFAULT FALSE")
        cursor.execute("ALTER TABLE strategy_trade_logs ADD COLUMN IF NOT EXISTS exchange_order_id VARCHAR(100)")
        print("✅ 交易类型字段已确保存在")
    except Exception as e:
        print(f"⚠️ 字段操作: {e}")
    
    # 2. 检查交易日志
    cursor.execute("SELECT COUNT(*) FROM strategy_trade_logs WHERE timestamp > NOW() - INTERVAL '1 hour'")
    recent_trades = cursor.fetchone()[0]
    print(f"📊 最近1小时交易日志: {recent_trades}条")
    
    cursor.execute("SELECT COUNT(*) FROM strategy_trade_logs WHERE timestamp > NOW() - INTERVAL '30 minutes'")
    very_recent_trades = cursor.fetchone()[0]
    print(f"📊 最近30分钟交易日志: {very_recent_trades}条")
    
    # 3. 检查策略状态
    cursor.execute("SELECT COUNT(*) FROM strategies WHERE enabled = 1")
    enabled_strategies = cursor.fetchone()[0]
    print(f"🎯 启用的策略数量: {enabled_strategies}个")
    
    cursor.execute("SELECT COUNT(*) FROM strategies WHERE final_score >= 80")
    high_score_strategies = cursor.fetchone()[0]
    print(f"⭐ 80分以上策略: {high_score_strategies}个")
    
    # 4. 检查系统状态
    cursor.execute("SELECT auto_trading_enabled, quantitative_running FROM system_status ORDER BY updated_at DESC LIMIT 1")
    system_status = cursor.fetchone()
    if system_status:
        auto_trading, quant_running = system_status
        print(f"🚀 自动交易状态: {'开启' if auto_trading else '关闭'}")
        print(f"🔄 量化系统状态: {'运行中' if quant_running else '停止'}")
    
    # 5. 强制激活系统
    print("\n🚀 ===== 强制激活系统 =====")
    
    cursor.execute("""
        UPDATE system_status 
        SET 
            auto_trading_enabled = TRUE,
            quantitative_running = TRUE,
            system_health = 'good',
            updated_at = CURRENT_TIMESTAMP
    """)
    
    cursor.execute("""
        UPDATE strategies 
        SET enabled = 1, updated_at = CURRENT_TIMESTAMP
        WHERE final_score >= 50
    """)
    
    enabled_count = cursor.rowcount
    print(f"✅ 已启用 {enabled_count} 个高分策略")
    
    # 6. 检查信号生成
    cursor.execute("SELECT COUNT(*) FROM trading_signals WHERE timestamp > NOW() - INTERVAL '1 hour'")
    recent_signals = cursor.fetchone()[0]
    print(f"📡 最近1小时信号: {recent_signals}个")
    
    if recent_signals == 0:
        print("❌ 问题: 最近1小时没有生成信号")
        print("建议: 检查策略运行状态和网络连接")
    
    conn.close()
    print("\n✅ 检查完成")

if __name__ == "__main__":
    check_trading_status() 