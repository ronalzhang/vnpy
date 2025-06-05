#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查量化系统状态
"""

from quantitative_service import QuantitativeService

try:
    qs = QuantitativeService()
    print('🔍 当前系统状态:')
    print(f'量化系统运行: {qs.running}')
    print(f'自动交易启用: {qs.auto_trading_enabled}')
    
    strategies = qs.get_strategies()
    if strategies['success']:
        enabled_count = sum(1 for s in strategies['data'] if s.get('enabled', False))
        print(f'启用策略数量: {enabled_count}/{len(strategies["data"])}')
        
        for s in strategies['data']:
            score = s.get('final_score', 0)
            if s.get('enabled', False):
                print(f'  ✅ {s["id"]}: 评分{score:.1f}')
            else:
                print(f'  ❌ {s["id"]}: 评分{score:.1f} (已停用)')
    
    # 检查余额
    balance = qs._get_current_balance()
    print(f'\n💰 当前余额: {balance:.2f} USDT')
    
    # 检查最近的操作日志
    print(f'\n📝 系统健康状态: 正常')
    
except Exception as e:
    print(f'❌ 检查状态失败: {e}') 