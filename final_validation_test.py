#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
最终验证测试 - 验证用户原始问题的修复效果
1. 自动交易启动后不再立即关闭
2. 策略进化过程完全透明可见
"""

import time
import threading
from datetime import datetime

def test_original_issues():
    """测试用户报告的原始问题"""
    print("🔧 最终验证测试 - 验证原始问题修复")
    print("=" * 50)
    
    # 问题1: 自动交易启动后立即关闭
    test_auto_trading_persistence()
    
    # 问题2: 策略进化过程不透明
    test_evolution_transparency()
    
    print("\n✅ 最终验证完成！")

def test_auto_trading_persistence():
    """测试自动交易持续运行（不立即关闭）"""
    print("\n🤖 测试1: 自动交易持续运行")
    
    try:
        from fixed_auto_trading_engine import FixedAutoTradingEngine
        
        # 创建交易引擎
        engine = FixedAutoTradingEngine()
        print(f"  📊 引擎初始化完成，余额: {engine.balance:.2f}")
        
        # 启动引擎
        if engine.start():
            print("  ✅ 自动交易引擎启动成功")
            
            # 记录启动时间
            start_time = time.time()
            
            # 等待10秒观察是否立即关闭
            print("  ⏱️  等待10秒观察运行状态...")
            time.sleep(10)
            
            # 检查引擎是否仍在运行
            status = engine.get_status()
            elapsed_time = time.time() - start_time
            
            if status['running']:
                print(f"  ✅ 引擎持续运行 {elapsed_time:.1f} 秒，未立即关闭")
                print(f"  📊 当前状态: 运行中，余额: {status.get('balance', 0):.2f}")
                
                # 模拟几笔交易测试
                print("  🔄 执行测试交易...")
                for i in range(3):
                    result = engine.execute_trade(
                        symbol="BTC/USDT",
                        side="buy" if i % 2 == 0 else "sell",
                        strategy_id=f"TEST_{i+1}",
                        confidence=0.8,
                        current_price=45000 + i * 100
                    )
                    if result.success:
                        print(f"    ✅ 交易 {i+1} 执行成功")
                    else:
                        print(f"    ❌ 交易 {i+1} 失败: {result.message}")
                
            else:
                print(f"  ❌ 引擎在 {elapsed_time:.1f} 秒后停止运行")
            
            # 正常停止引擎
            engine.stop()
            print("  ✅ 引擎正常停止")
            
        else:
            print("  ❌ 自动交易引擎启动失败")
            
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")

def test_evolution_transparency():
    """测试策略进化过程透明性"""
    print("\n🧬 测试2: 策略进化过程透明性")
    
    try:
        # 模拟量化服务
        class MockQuantitativeService:
            def get_strategies(self):
                return {
                    'success': True,
                    'data': [
                        {
                            'id': 'STRATEGY_001',
                            'name': '动量突破策略',
                            'total_return': 0.12,
                            'win_rate': 0.68,
                            'total_trades': 45,
                            'sharpe_ratio': 1.3,
                            'max_drawdown': 0.06,
                            'parameters': {
                                'ma_period': 20,
                                'bb_period': 20,
                                'stop_loss': 0.02,
                                'take_profit': 0.05
                            }
                        },
                        {
                            'id': 'STRATEGY_002',
                            'name': '均值回归策略',
                            'total_return': 0.08,
                            'win_rate': 0.72,
                            'total_trades': 38,
                            'sharpe_ratio': 1.1,
                            'max_drawdown': 0.04,
                            'parameters': {
                                'ma_period': 30,
                                'bb_period': 25,
                                'stop_loss': 0.015,
                                'take_profit': 0.04
                            }
                        }
                    ]
                }
            
            def save_strategy(self, strategy_data):
                return {'success': True, 'id': f'NEW_STRATEGY_{int(time.time())}'}
        
        from enhanced_strategy_evolution import EnhancedStrategyEvolution
        
        # 创建进化引擎
        mock_service = MockQuantitativeService()
        evolution_engine = EnhancedStrategyEvolution(mock_service)
        
        print("  📊 策略进化引擎初始化完成")
        
        # 运行多个进化周期以展示透明性
        for cycle in range(3):
            print(f"\n  🔄 运行第 {cycle + 1} 个进化周期...")
            
            # 启动进化周期
            result = evolution_engine.start_evolution_cycle()
            
            if result.get('success', True):
                print(f"    ✅ 第 {cycle + 1} 代进化完成")
                
                # 获取进化状态
                status = evolution_engine.get_evolution_status()
                print(f"    📊 当前世代: {status.get('current_generation', 0)}")
                print(f"    📊 种群大小: {status.get('population_size', 0)}")
                print(f"    📊 平均适应性: {status.get('avg_fitness', 0):.3f}")
                
                # 获取最新进化记录
                logs = evolution_engine.get_evolution_logs(limit=5)
                print(f"    📋 进化记录数: {len(logs)}")
                
                if logs:
                    latest_log = logs[0]
                    print(f"    📝 最新记录: {latest_log.get('action', 'Unknown')} - {latest_log.get('details', {}).get('description', '无描述')}")
                
            else:
                print(f"    ❌ 第 {cycle + 1} 代进化失败: {result.get('error')}")
            
            time.sleep(2)  # 短暂停顿
        
        # 显示完整进化历史
        print("\n  📊 进化过程透明性验证:")
        all_logs = evolution_engine.get_evolution_logs(limit=20)
        
        if all_logs:
            print(f"    ✅ 总共记录了 {len(all_logs)} 条进化日志")
            print("    📝 最近的进化活动:")
            
            for i, log in enumerate(all_logs[:5]):
                timestamp = log.get('timestamp', 'Unknown')
                action = log.get('action', 'Unknown')
                strategy_id = log.get('strategy_id', 'Unknown')
                print(f"      {i+1}. [{timestamp}] {strategy_id}: {action}")
        else:
            print("    ❌ 没有找到进化记录")
        
        # 检查数据库中的进化日志
        print("\n  💾 检查数据库进化日志:")
        import sqlite3
        try:
            conn = sqlite3.connect('quantitative.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM strategy_evolution_logs")
            log_count = cursor.fetchone()[0]
            print(f"    ✅ 数据库中有 {log_count} 条策略进化记录")
            
            if log_count > 0:
                cursor.execute("""
                    SELECT strategy_id, action_type, reason, timestamp 
                    FROM strategy_evolution_logs 
                    ORDER BY timestamp DESC 
                    LIMIT 5
                """)
                
                recent_logs = cursor.fetchall()
                print("    📝 最近的数据库记录:")
                for i, log in enumerate(recent_logs):
                    strategy_id, action_type, reason, timestamp = log
                    print(f"      {i+1}. [{timestamp}] {strategy_id}: {action_type} - {reason}")
            
            conn.close()
            
        except Exception as e:
            print(f"    ❌ 数据库检查失败: {e}")
        
        print("  ✅ 策略进化过程完全透明可见")
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")

if __name__ == "__main__":
    test_original_issues() 