#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试高级策略管理器
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from quantitative_service import QuantitativeService
    from advanced_strategy_manager import get_advanced_manager
    
    print("🧪 开始测试高级策略管理器...")
    
    # 创建量化服务实例
    service = QuantitativeService()
    
    # 测试余额获取修复
    print("\n💰 测试余额获取修复...")
    balance = service._get_current_balance()
    print(f"当前余额: {balance} USDT (期望: 15.25U)")
    
    # 创建高级管理器
    print("\n🚀 创建高级策略管理器...")
    advanced_manager = get_advanced_manager(service)
    
    # 运行管理周期
    print("\n🔄 运行高级管理周期...")
    advanced_manager.run_advanced_management_cycle()
    
    # 检查验证记录
    print(f"\n📊 验证记录数量: {len(advanced_manager.validation_records)}")
    
    # 显示策略状态分布
    status_counts = {}
    for record in advanced_manager.validation_records.values():
        status = record.status.value
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("\n📋 策略状态分布:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}个策略")
    
    # 检查自动交易决策
    should_enable = advanced_manager._should_enable_auto_trading()
    print(f"\n🤖 自动交易建议: {'启用' if should_enable else '禁用'}")
    print(f"   当前状态: {'启用' if service.auto_trading_enabled else '禁用'}")
    
    # 显示Top策略
    top_strategies = sorted(
        advanced_manager.validation_records.values(),
        key=lambda x: x.score,
        reverse=True
    )[:3]
    
    print("\n🏆 Top 3 策略:")
    for i, record in enumerate(top_strategies, 1):
        print(f"  {i}. {record.strategy_id}: {record.score:.1f}分 [{record.status.value}]")
    
    print("\n✅ 高级策略管理器测试完成！")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc() 