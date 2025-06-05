#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试资产历史数据功能
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from quantitative_service import QuantitativeService
    
    print("🧪 开始测试资产历史数据功能...")
    
    # 创建量化服务实例
    service = QuantitativeService()
    
    # 测试获取资产历史
    print("\n📊 测试获取资产历史数据...")
    history = service.get_balance_history(days=30)
    
    if history:
        print(f"✅ 成功获取 {len(history)} 条历史记录")
        print("\n📋 最新5条记录:")
        for i, record in enumerate(history[-5:], 1):
            print(f"  {i}. 时间: {record['timestamp']}")
            print(f"     总余额: {record['total_balance']:.2f}")
            print(f"     可用余额: {record['available_balance']:.2f}")
            print(f"     冻结余额: {record['frozen_balance']:.2f}")
            print(f"     日收益: {record['daily_pnl']:.2f}")
            print(f"     日收益率: {record['daily_return']:.3f}")
            if record['milestone_note']:
                print(f"     备注: {record['milestone_note']}")
            print()
    else:
        print("❌ 未获取到历史数据")
    
    # 测试策略日志功能
    print("\n📝 测试策略日志功能...")
    
    # 测试记录交易日志
    service.log_strategy_trade(
        strategy_id="DOGE_momentum",
        signal_type="buy",
        price=0.35,
        quantity=100.0,
        confidence=0.85,
        executed=True
    )
    
    # 获取交易日志
    trade_logs = service.get_strategy_trade_logs("DOGE_momentum", limit=10)
    print(f"✅ 策略交易日志数量: {len(trade_logs)}")
    if trade_logs:
        print("最新交易日志:")
        for log in trade_logs[:3]:
            print(f"  - {log['timestamp']}: {log['signal_type']} 价格:{log['price']} 数量:{log['quantity']}")
    
    # 获取策略优化日志
    optimization_logs = service.get_strategy_optimization_logs("DOGE_momentum", limit=10)
    print(f"✅ 策略优化日志数量: {len(optimization_logs)}")
    
    print("\n🎉 测试完成!")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc() 