#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实交易管理器 - 第一性原理：赚钱
核心功能：
1. 模拟交易验证和长期跟踪
2. 真实交易启动和管理
3. 盈亏分类统计和分析
4. 策略活跃度和多样性监控
5. 风险管理和收益优化
"""

import psycopg2
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class RealTradingManager:
    def __init__(self):
        self.conn = psycopg2.connect(
            host='localhost', 
            database='quantitative', 
            user='quant_user', 
            password='chenfei0421'
        )
        self.conn.autocommit = True
        self.setup_enhanced_tables()
        
    def setup_enhanced_tables(self):
        """建立完整的交易分析表结构"""
        cursor = self.conn.cursor()
        
        # 1. 确保交易日志表包含所有必要字段
        cursor.execute("""
            ALTER TABLE strategy_trade_logs 
            ADD COLUMN IF NOT EXISTS trade_type VARCHAR(20) DEFAULT 'simulation',
            ADD COLUMN IF NOT EXISTS is_real_money BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS exchange_order_id VARCHAR(100),
            ADD COLUMN IF NOT EXISTS strategy_name VARCHAR(200),
            ADD COLUMN IF NOT EXISTS symbol VARCHAR(50),
            ADD COLUMN IF NOT EXISTS action VARCHAR(20),
            ADD COLUMN IF NOT EXISTS quantity DECIMAL(15,8),
            ADD COLUMN IF NOT EXISTS real_pnl DECIMAL(15,8) DEFAULT 0;
        """)
        
        # 2. 创建策略验证表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_validation (
                id SERIAL PRIMARY KEY,
                strategy_id VARCHAR(100) NOT NULL,
                validation_start_date DATE DEFAULT CURRENT_DATE,
                simulation_days INTEGER DEFAULT 0,
                total_sim_trades INTEGER DEFAULT 0,
                successful_sim_trades INTEGER DEFAULT 0,
                sim_win_rate DECIMAL(5,2) DEFAULT 0,
                sim_total_pnl DECIMAL(15,8) DEFAULT 0,
                sim_daily_avg_pnl DECIMAL(15,8) DEFAULT 0,
                validation_status VARCHAR(20) DEFAULT 'testing',
                qualified_for_real BOOLEAN DEFAULT FALSE,
                real_trading_enabled BOOLEAN DEFAULT FALSE,
                last_validation_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(strategy_id)
            );
        """)
        
        # 3. 创建盈亏统计表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profit_loss_analysis (
                id SERIAL PRIMARY KEY,
                date DATE DEFAULT CURRENT_DATE,
                simulation_trades INTEGER DEFAULT 0,
                real_trades INTEGER DEFAULT 0,
                simulation_pnl DECIMAL(15,8) DEFAULT 0,
                real_pnl DECIMAL(15,8) DEFAULT 0,
                simulation_win_rate DECIMAL(5,2) DEFAULT 0,
                real_win_rate DECIMAL(5,2) DEFAULT 0,
                top_strategy_id VARCHAR(100),
                top_strategy_pnl DECIMAL(15,8) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date)
            );
        """)
        
        # 4. 创建真实交易控制表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS real_trading_control (
                id SERIAL PRIMARY KEY,
                real_trading_enabled BOOLEAN DEFAULT FALSE,
                min_simulation_days INTEGER DEFAULT 7,
                min_sim_win_rate DECIMAL(5,2) DEFAULT 65.0,
                min_sim_total_pnl DECIMAL(15,8) DEFAULT 5.0,
                max_risk_per_trade DECIMAL(5,2) DEFAULT 2.0,
                max_daily_risk DECIMAL(5,2) DEFAULT 10.0,
                qualified_strategies_count INTEGER DEFAULT 0,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 5. 插入初始控制记录
        cursor.execute("""
            INSERT INTO real_trading_control (id) 
            VALUES (1) 
            ON CONFLICT (id) DO NOTHING;
        """)
        
        print("✅ 真实交易管理表结构已建立")
    
    def analyze_strategy_performance(self) -> Dict:
        """分析策略表现，识别合格的真实交易策略"""
        cursor = self.conn.cursor()
        
        print("📊 ===== 策略表现分析 =====")
        
        cursor.execute("""
            SELECT 
                s.id, s.name, s.final_score,
                COUNT(t.id) as total_trades,
                COUNT(CASE WHEN t.pnl > 0 THEN 1 END) as winning_trades,
                SUM(t.pnl) as total_pnl
            FROM strategies s
            LEFT JOIN strategy_trade_logs t ON s.id = t.strategy_id
            WHERE s.enabled = 1 AND s.final_score >= 80
            GROUP BY s.id, s.name, s.final_score
            ORDER BY s.final_score DESC
            LIMIT 10
        """)
        
        strategies = cursor.fetchall()
        qualified_count = 0
        
        for strategy in strategies:
            sid, name, score, total_trades, winning_trades, total_pnl = strategy
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # 合格标准：评分≥80，至少5次交易，胜率≥60%，总盈利>0
            is_qualified = (score >= 80 and total_trades >= 5 and win_rate >= 60 and (total_pnl or 0) > 0)
            
            status = "✅合格" if is_qualified else "🔄验证中"
            if is_qualified:
                qualified_count += 1
                
            print(f"  {status} {name[:25]:<25}: {score:5.1f}分 | {total_trades:3d}次 | 胜率:{win_rate:5.1f}% | 盈亏:{total_pnl or 0:+6.2f}U")
        
        print(f"\n🎯 合格真实交易策略: {qualified_count} 个")
        return qualified_count
    
    def generate_pnl_statistics(self) -> Dict:
        """生成详细的盈亏统计"""
        cursor = self.conn.cursor()
        
        print("\n💰 ===== 盈亏统计分析 =====")
        
        # 今日统计
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN trade_type = 'simulation' THEN 1 END) as sim_trades,
                COUNT(CASE WHEN trade_type = 'real' THEN 1 END) as real_trades,
                SUM(CASE WHEN trade_type = 'simulation' THEN pnl ELSE 0 END) as sim_pnl,
                SUM(CASE WHEN trade_type = 'real' THEN pnl ELSE 0 END) as real_pnl,
                COUNT(CASE WHEN trade_type = 'simulation' AND pnl > 0 THEN 1 END) as sim_wins,
                COUNT(CASE WHEN trade_type = 'real' AND pnl > 0 THEN 1 END) as real_wins
            FROM strategy_trade_logs 
            WHERE DATE(timestamp) = CURRENT_DATE
        """)
        
        today_stats = cursor.fetchone()
        sim_trades, real_trades, sim_pnl, real_pnl, sim_wins, real_wins = today_stats
        
        sim_win_rate = (sim_wins / sim_trades * 100) if sim_trades > 0 else 0
        real_win_rate = (real_wins / real_trades * 100) if real_trades > 0 else 0
        
        # 本周统计
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN trade_type = 'simulation' THEN pnl ELSE 0 END) as week_sim_pnl,
                SUM(CASE WHEN trade_type = 'real' THEN pnl ELSE 0 END) as week_real_pnl,
                COUNT(CASE WHEN trade_type = 'simulation' THEN 1 END) as week_sim_trades,
                COUNT(CASE WHEN trade_type = 'real' THEN 1 END) as week_real_trades
            FROM strategy_trade_logs 
            WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
        """)
        
        week_stats = cursor.fetchone()
        week_sim_pnl, week_real_pnl, week_sim_trades, week_real_trades = week_stats
        
        stats = {
            'today': {
                'simulation_trades': sim_trades or 0,
                'real_trades': real_trades or 0,
                'simulation_pnl': float(sim_pnl or 0),
                'real_pnl': float(real_pnl or 0),
                'simulation_win_rate': round(sim_win_rate, 2),
                'real_win_rate': round(real_win_rate, 2)
            },
            'week': {
                'simulation_pnl': float(week_sim_pnl or 0),
                'real_pnl': float(week_real_pnl or 0),
                'simulation_trades': week_sim_trades or 0,
                'real_trades': week_real_trades or 0
            }
        }
        
        print(f"📅 今日统计:")
        print(f"  🎯 模拟交易: {stats['today']['simulation_trades']}次 | {stats['today']['simulation_pnl']:+.2f}U | 胜率:{stats['today']['simulation_win_rate']:.1f}%")
        print(f"  💰 真实交易: {stats['today']['real_trades']}次 | {stats['today']['real_pnl']:+.2f}U | 胜率:{stats['today']['real_win_rate']:.1f}%")
        
        print(f"📊 本周累计:")
        print(f"  🎯 模拟盈亏: {stats['week']['simulation_pnl']:+.2f}U ({stats['week']['simulation_trades']}次)")
        print(f"  💰 真实盈亏: {stats['week']['real_pnl']:+.2f}U ({stats['week']['real_trades']}次)")
        
        # 保存统计到数据库
        cursor.execute("""
            INSERT INTO profit_loss_analysis 
            (simulation_trades, real_trades, simulation_pnl, real_pnl, 
             simulation_win_rate, real_win_rate)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (date) DO UPDATE SET
                simulation_trades = EXCLUDED.simulation_trades,
                real_trades = EXCLUDED.real_trades,
                simulation_pnl = EXCLUDED.simulation_pnl,
                real_pnl = EXCLUDED.real_pnl,
                simulation_win_rate = EXCLUDED.simulation_win_rate,
                real_win_rate = EXCLUDED.real_win_rate
        """, (
            stats['today']['simulation_trades'], stats['today']['real_trades'],
            stats['today']['simulation_pnl'], stats['today']['real_pnl'],
            stats['today']['simulation_win_rate'], stats['today']['real_win_rate']
        ))
        
        return stats
    
    def enable_real_trading_for_qualified_strategies(self) -> Dict:
        """为合格策略启用真实交易"""
        cursor = self.conn.cursor()
        
        print("\n🚀 ===== 真实交易启用检查 =====")
        
        # 获取合格策略
        cursor.execute("""
            SELECT strategy_id, sim_win_rate, sim_total_pnl, total_sim_trades, simulation_days
            FROM strategy_validation 
            WHERE qualified_for_real = TRUE 
            ORDER BY sim_total_pnl DESC
            LIMIT 5
        """)
        
        qualified_strategies = cursor.fetchall()
        
        if not qualified_strategies:
            print("⚠️ 暂无策略通过真实交易验证")
            return {'enabled_count': 0, 'qualified_strategies': []}
        
        # 为合格策略标记真实交易
        enabled_strategies = []
        for strategy in qualified_strategies:
            sid, win_rate, total_pnl, trades, days = strategy
            
            cursor.execute("""
                UPDATE strategy_validation 
                SET real_trading_enabled = TRUE 
                WHERE strategy_id = %s
            """, (sid,))
            
            enabled_strategies.append({
                'strategy_id': sid,
                'win_rate': float(win_rate),
                'total_pnl': float(total_pnl),
                'trades': trades,
                'days': days
            })
            
            print(f"✅ 策略 {sid} 已启用真实交易 | 胜率:{win_rate:.1f}% | 盈利:{total_pnl:+.2f}U")
        
        # 更新控制表
        cursor.execute("""
            UPDATE real_trading_control 
            SET qualified_strategies_count = %s, last_update = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (len(enabled_strategies),))
        
        return {
            'enabled_count': len(enabled_strategies),
            'qualified_strategies': enabled_strategies
        }
    
    def check_real_trading_readiness(self) -> Dict:
        """检查真实交易准备状态"""
        cursor = self.conn.cursor()
        
        print("\n🔍 ===== 真实交易准备状态 =====")
        
        # 获取控制参数
        cursor.execute("SELECT * FROM real_trading_control WHERE id = 1")
        control = cursor.fetchone()
        
        if not control:
            return {'ready': False, 'reason': '控制参数未初始化'}
        
        # 检查合格策略数量
        cursor.execute("""
            SELECT COUNT(*) FROM strategy_validation 
            WHERE qualified_for_real = TRUE AND sim_total_pnl > 0
        """)
        qualified_count = cursor.fetchone()[0]
        
        # 检查最近模拟交易表现
        cursor.execute("""
            SELECT 
                COUNT(*) as recent_trades,
                SUM(pnl) as recent_pnl,
                COUNT(CASE WHEN pnl > 0 THEN 1 END) as recent_wins
            FROM strategy_trade_logs 
            WHERE trade_type = 'simulation' 
            AND timestamp >= CURRENT_DATE - INTERVAL '3 days'
        """)
        
        recent_stats = cursor.fetchone()
        recent_trades, recent_pnl, recent_wins = recent_stats
        recent_win_rate = (recent_wins / recent_trades * 100) if recent_trades > 0 else 0
        
        # 准备状态评估
        readiness = {
            'qualified_strategies': qualified_count,
            'min_required': 3,
            'recent_sim_trades': recent_trades or 0,
            'recent_sim_pnl': float(recent_pnl or 0),
            'recent_win_rate': round(recent_win_rate, 2),
            'ready': False,
            'recommendations': []
        }
        
        # 评估准备状态
        if qualified_count >= 3:
            readiness['recommendations'].append('✅ 合格策略数量充足')
        else:
            readiness['recommendations'].append(f'❌ 需要至少3个合格策略，当前仅{qualified_count}个')
        
        if recent_trades >= 20:
            readiness['recommendations'].append('✅ 近期模拟交易活跃')
        else:
            readiness['recommendations'].append(f'❌ 近3天模拟交易不足，仅{recent_trades}次')
        
        if recent_pnl > 0:
            readiness['recommendations'].append('✅ 近期模拟交易盈利')
        else:
            readiness['recommendations'].append(f'❌ 近期模拟交易亏损 {recent_pnl:.2f}U')
        
        if recent_win_rate >= 60:
            readiness['recommendations'].append('✅ 近期胜率合格')
        else:
            readiness['recommendations'].append(f'❌ 近期胜率不足，仅{recent_win_rate:.1f}%')
        
        # 综合评估
        readiness['ready'] = (
            qualified_count >= 3 and 
            recent_trades >= 20 and 
            recent_pnl > 0 and 
            recent_win_rate >= 60
        )
        
        print(f"📊 准备状态评估:")
        for rec in readiness['recommendations']:
            print(f"  {rec}")
        
        print(f"\n🎯 真实交易状态: {'✅ 准备就绪' if readiness['ready'] else '❌ 尚未准备'}")
        
        return readiness
    
    def force_generate_signals(self) -> bool:
        """强制触发信号生成"""
        cursor = self.conn.cursor()
        
        print("\n🔧 ===== 强制信号生成 =====")
        
        try:
            # 获取高分策略
            cursor.execute("""
                SELECT id, name, symbol, final_score 
                FROM strategies 
                WHERE enabled = 1 AND final_score >= 70
                ORDER BY final_score DESC 
                LIMIT 5
            """)
            
            top_strategies = cursor.fetchall()
            
            if not top_strategies:
                print("❌ 无可用的高分策略")
                return False
            
            signals_created = 0
            
            # 为每个策略创建模拟信号
            for strategy in top_strategies:
                sid, name, symbol, score = strategy
                
                # 模拟价格（实际应该从交易所获取）
                base_price = 0.15  # DOGE基准价格
                signal_type = 'buy' if (int(time.time()) % 2 == 0) else 'sell'
                quantity = min(10.0, 100.0 / base_price)  # 最多10U的交易
                confidence = min(95.0, score)
                
                # 🔧 修复：正确设置trade_type和is_validation字段
                # 🔧 修复：检查全局实盘交易开关，如果关闭则强制为验证交易
            try:
                cursor.execute("SELECT real_trading_enabled FROM real_trading_control WHERE id = 1")
                real_trading_control = cursor.fetchone()
                real_trading_enabled = real_trading_control[0] if real_trading_control else False
                
                # 如果实盘交易未启用，所有交易都应该是验证交易
                if not real_trading_enabled:
                    trade_type = "score_verification"
                else:
                    trade_type = "real_trading" if score >= 65.0 else "score_verification"
            except Exception as e:
                print(f"⚠️ 无法检查实盘交易开关，默认为验证交易: {e}")
                trade_type = "score_verification"
                is_validation = score < 65.0
                
                # 插入交易信号
                cursor.execute("""
                    INSERT INTO trading_signals 
                    (strategy_id, symbol, signal_type, price, quantity, confidence, 
                     timestamp, executed, trade_type, is_validation, strategy_score)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, 0, %s, %s, %s)
                """, (sid, symbol or 'DOGE/USDT', signal_type, base_price, quantity, confidence, 
                     trade_type, is_validation, score))
                
                signals_created += 1
                print(f"📡 创建信号: {name[:20]} | {signal_type.upper()} | {quantity:.2f} @ ${base_price}")
            
            print(f"✅ 成功创建 {signals_created} 个交易信号")
            return signals_created > 0
            
        except Exception as e:
            print(f"❌ 强制信号生成失败: {e}")
            return False

def main():
    """主函数 - 完整的真实交易管理流程"""
    manager = RealTradingManager()
    
    print("🎯 ===== 真实交易管理系统启动 =====")
    print("第一性原理：确保系统能够稳定盈利赚钱")
    
    # 1. 分析策略表现
    strategy_analysis = manager.analyze_strategy_performance()
    
    # 2. 生成盈亏统计
    pnl_stats = manager.generate_pnl_statistics()
    
    # 3. 检查真实交易准备状态
    readiness = manager.check_real_trading_readiness()
    
    # 4. 如果没有交易信号，强制生成一些
    if pnl_stats['today']['simulation_trades'] == 0:
        print("\n⚠️ 检测到无交易信号，强制生成测试信号...")
        manager.force_generate_signals()
    
    # 5. 为合格策略启用真实交易
    if readiness['ready']:
        real_trading_result = manager.enable_real_trading_for_qualified_strategies()
        print(f"🚀 已为 {real_trading_result['enabled_count']} 个策略启用真实交易")
    else:
        print("⏳ 系统尚未准备好真实交易，继续模拟验证...")
    
    print("\n✅ 真实交易管理检查完成")
    
    return {
        'strategy_analysis': strategy_analysis,
        'pnl_stats': pnl_stats,
        'readiness': readiness
    }

if __name__ == "__main__":
    main() 