#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易监控系统 - 区分模拟交易和真实交易，监控策略活跃度
"""

import psycopg2
from datetime import datetime, timedelta
import json

class TradingMonitor:
    def __init__(self):
        self.conn = psycopg2.connect(
            host='localhost', 
            database='quantitative', 
            user='quant_user', 
            password='chenfei0421'
        )
        self.conn.autocommit = True
        self.setup_trading_type_tables()
    
    def setup_trading_type_tables(self):
        """建立区分模拟交易和真实交易的表结构"""
        cursor = self.conn.cursor()
        
        # 为交易日志表添加交易类型字段（如果不存在）
        try:
            cursor.execute("""
                ALTER TABLE strategy_trade_logs 
                ADD COLUMN IF NOT EXISTS trade_type VARCHAR(20) DEFAULT 'simulation';
            """)
            cursor.execute("""
                ALTER TABLE strategy_trade_logs 
                ADD COLUMN IF NOT EXISTS is_real_money BOOLEAN DEFAULT FALSE;
            """)
            cursor.execute("""
                ALTER TABLE strategy_trade_logs 
                ADD COLUMN IF NOT EXISTS exchange_order_id VARCHAR(100);
            """)
            print("✅ 交易类型字段已添加")
        except Exception as e:
            print(f"⚠️ 字段可能已存在: {e}")
        
        # 创建交易统计表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trading_statistics (
                id SERIAL PRIMARY KEY,
                date DATE DEFAULT CURRENT_DATE,
                simulation_trades INTEGER DEFAULT 0,
                real_trades INTEGER DEFAULT 0,
                simulation_pnl DECIMAL(15,8) DEFAULT 0,
                real_pnl DECIMAL(15,8) DEFAULT 0,
                active_strategies INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 创建策略活跃度监控表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_activity_monitor (
                id SERIAL PRIMARY KEY,
                strategy_id VARCHAR(100) NOT NULL,
                last_signal_time TIMESTAMP,
                last_trade_time TIMESTAMP,
                simulation_trades_today INTEGER DEFAULT 0,
                real_trades_today INTEGER DEFAULT 0,
                inactive_hours INTEGER DEFAULT 0,
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(strategy_id)
            );
        """)
        print("✅ 监控表结构已建立")
    
    def check_trading_activity(self):
        """检查交易活跃度"""
        cursor = self.conn.cursor()
        
        print("🔍 ===== 交易活跃度检查 =====")
        print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. 检查最近各时间段的交易活动
        time_periods = [
            ('最近5分钟', 5),
            ('最近15分钟', 15), 
            ('最近30分钟', 30),
            ('最近1小时', 60),
            ('最近3小时', 180)
        ]
        
        for period_name, minutes in time_periods:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_logs,
                    COUNT(CASE WHEN trade_type = 'simulation' THEN 1 END) as sim_trades,
                    COUNT(CASE WHEN trade_type = 'real' THEN 1 END) as real_trades,
                    COUNT(CASE WHEN executed = true THEN 1 END) as executed_trades
                FROM strategy_trade_logs 
                WHERE timestamp > NOW() - INTERVAL '%s minutes'
            """ % minutes)
            
            result = cursor.fetchone()
            print(f"{period_name}: 总日志{result[0]}条 | 模拟{result[1]}次 | 真实{result[2]}次 | 已执行{result[3]}次")
        
        # 2. 检查策略活跃状态
        cursor.execute("""
            SELECT s.id, s.name, s.enabled, s.final_score,
                   MAX(t.timestamp) as last_trade,
                   COUNT(t.id) as total_trades
            FROM strategies s
            LEFT JOIN strategy_trade_logs t ON s.id = t.strategy_id
            WHERE s.enabled = 1 AND s.final_score >= 60
            GROUP BY s.id, s.name, s.enabled, s.final_score
            ORDER BY s.final_score DESC
            LIMIT 10
        """)
        
        active_strategies = cursor.fetchall()
        print(f"\n📊 前10名活跃策略状态:")
        for sid, name, enabled, score, last_trade, total_trades in active_strategies:
            last_trade_str = last_trade.strftime('%H:%M:%S') if last_trade else '从未交易'
            status = "🟢活跃" if last_trade and last_trade > datetime.now() - timedelta(hours=1) else "🔴停滞"
            print(f"  {status} {name[:20]:<20}: {score:5.1f}分 | {total_trades:2d}次交易 | 最后交易:{last_trade_str}")
        
        # 3. 检查信号生成情况
        cursor.execute("""
            SELECT 
                COUNT(*) as total_signals,
                COUNT(CASE WHEN executed = true THEN 1 END) as executed_signals,
                COUNT(CASE WHEN timestamp > NOW() - INTERVAL '1 hour' THEN 1 END) as recent_signals
            FROM trading_signals
        """)
        
        signal_result = cursor.fetchone()
        if signal_result:
            print(f"\n📡 信号生成统计:")
            print(f"  总信号数: {signal_result[0]}")
            print(f"  已执行信号: {signal_result[1]}")
            print(f"  最近1小时: {signal_result[2]}")
        
        return active_strategies
    
    def diagnose_trading_problems(self):
        """诊断交易问题"""
        cursor = self.conn.cursor()
        
        print("\n🔧 ===== 交易问题诊断 =====")
        
        # 检查是否有策略在生成信号
        cursor.execute("""
            SELECT COUNT(*) FROM trading_signals 
            WHERE timestamp > NOW() - INTERVAL '30 minutes'
        """)
        recent_signals = cursor.fetchone()[0]
        
        if recent_signals == 0:
            print("❌ 问题1: 最近30分钟没有生成任何交易信号")
            
            # 检查策略是否启用
            cursor.execute("SELECT COUNT(*) FROM strategies WHERE enabled = 1")
            enabled_strategies = cursor.fetchone()[0]
            print(f"   启用的策略数量: {enabled_strategies}")
            
            # 检查自动交易是否开启
            cursor.execute("SELECT auto_trading_enabled FROM system_status ORDER BY updated_at DESC LIMIT 1")
            auto_trading = cursor.fetchone()
            auto_status = auto_trading[0] if auto_trading else False
            print(f"   自动交易状态: {'开启' if auto_status else '关闭'}")
            
        # 检查交易执行情况
        cursor.execute("""
            SELECT 
                COUNT(*) as pending_signals,
                COUNT(CASE WHEN timestamp < NOW() - INTERVAL '10 minutes' THEN 1 END) as old_pending
            FROM trading_signals 
            WHERE executed = false
        """)
        pending_result = cursor.fetchone()
        
        if pending_result[0] > 0:
            print(f"❌ 问题2: 有{pending_result[0]}个未执行的信号")
            if pending_result[1] > 0:
                print(f"   其中{pending_result[1]}个信号已超过10分钟未执行")
        
        # 检查余额是否充足
        cursor.execute("""
            SELECT total_balance, available_balance 
            FROM balance_history 
            ORDER BY timestamp DESC LIMIT 1
        """)
        balance_result = cursor.fetchone()
        if balance_result:
            total, available = balance_result
            print(f"💰 当前余额: 总额{total}U, 可用{available}U")
            if available and available < 10:
                print("❌ 问题3: 可用余额不足10U，可能影响交易")
    
    def update_strategy_activity_status(self):
        """更新策略活跃度状态"""
        cursor = self.conn.cursor()
        
        # 更新或插入策略活跃度记录
        cursor.execute("""
            INSERT INTO strategy_activity_monitor (strategy_id, last_signal_time, last_trade_time, updated_at)
            SELECT 
                s.id,
                (SELECT MAX(timestamp) FROM trading_signals WHERE strategy_id = s.id),
                (SELECT MAX(timestamp) FROM strategy_trade_logs WHERE strategy_id = s.id),
                CURRENT_TIMESTAMP
            FROM strategies s
            ON CONFLICT (strategy_id) DO UPDATE SET
                last_signal_time = EXCLUDED.last_signal_time,
                last_trade_time = EXCLUDED.last_trade_time,
                updated_at = CURRENT_TIMESTAMP
        """)
        
        # 计算非活跃小时数
        cursor.execute("""
            UPDATE strategy_activity_monitor 
            SET 
                inactive_hours = EXTRACT(EPOCH FROM (NOW() - COALESCE(last_trade_time, created_at))) / 3600,
                status = CASE 
                    WHEN last_trade_time > NOW() - INTERVAL '1 hour' THEN 'active'
                    WHEN last_trade_time > NOW() - INTERVAL '6 hours' THEN 'slow'
                    ELSE 'inactive'
                END
        """)
        
        print("✅ 策略活跃度状态已更新")
    
    def generate_optimization_suggestions(self):
        """生成优化建议"""
        cursor = self.conn.cursor()
        
        print("\n💡 ===== 优化建议 =====")
        
        suggestions = []
        
        # 建议1: 检查信号生成频率
        cursor.execute("""
            SELECT COUNT(*) FROM trading_signals 
            WHERE timestamp > NOW() - INTERVAL '1 hour'
        """)
        recent_signals = cursor.fetchone()[0]
        
        if recent_signals < 5:
            suggestions.append("1. 信号生成频率过低，建议：")
            suggestions.append("   - 降低策略信号阈值")
            suggestions.append("   - 增加市场监控频率")
            suggestions.append("   - 检查网络连接和数据获取")
        
        # 建议2: 检查策略多样性
        cursor.execute("""
            SELECT COUNT(DISTINCT strategy_type) as types, COUNT(*) as total
            FROM strategies WHERE enabled = 1 AND final_score >= 60
        """)
        strategy_diversity = cursor.fetchone()
        
        if strategy_diversity and strategy_diversity[0] < 3:
            suggestions.append("2. 策略类型单一，建议：")
            suggestions.append("   - 启用更多不同类型的策略")
            suggestions.append("   - 平衡动量、均值回归、网格等策略")
        
        # 建议3: 检查交易执行率
        cursor.execute("""
            SELECT 
                COUNT(*) as total_signals,
                COUNT(CASE WHEN executed = 1 THEN 1 END) as executed
            FROM trading_signals
        """)
        execution_stats = cursor.fetchone()
        
        if execution_stats and execution_stats[0] > 0:
            execution_rate = execution_stats[1] / execution_stats[0] * 100
            if execution_rate < 80:
                suggestions.append(f"3. 信号执行率偏低({execution_rate:.1f}%)，建议：")
                suggestions.append("   - 检查交易所连接状态")
                suggestions.append("   - 增加订单重试机制")
                suggestions.append("   - 优化订单执行逻辑")
        
        # 建议4: 实时交易建议
        suggestions.append("4. 启动真实交易准备：")
        suggestions.append("   - 确保至少有3-5个有真实模拟交易记录的策略")
        suggestions.append("   - 设置合理的风险管理参数")
        suggestions.append("   - 建立模拟交易和真实交易的完整记录体系")
        
        for suggestion in suggestions:
            print(suggestion)
    
    def force_activate_strategies(self):
        """强制激活策略生成信号"""
        cursor = self.conn.cursor()
        
        print("\n🚀 ===== 强制激活策略 =====")
        
        # 重置系统状态，确保自动交易开启
        cursor.execute("""
            UPDATE system_status 
            SET 
                auto_trading_enabled = TRUE,
                quantitative_running = TRUE,
                system_health = 'good',
                updated_at = CURRENT_TIMESTAMP
        """)
        
        # 启用所有高分策略
        cursor.execute("""
            UPDATE strategies 
            SET enabled = 1, updated_at = CURRENT_TIMESTAMP
            WHERE final_score >= 50
        """)
        
        enabled_count = cursor.rowcount
        print(f"✅ 已启用 {enabled_count} 个高分策略")
        
        return enabled_count

def main():
    """主函数"""
    monitor = TradingMonitor()
    
    # 检查交易活跃度
    monitor.check_trading_activity()
    
    # 诊断问题
    monitor.diagnose_trading_problems()
    
    # 更新活跃度状态
    monitor.update_strategy_activity_status()
    
    # 生成优化建议
    monitor.generate_optimization_suggestions()
    
    # 强制激活策略
    monitor.force_activate_strategies()
    
    print("\n✅ 交易监控检查完成")

if __name__ == "__main__":
    main() 