#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复策略启用状态问题
- 启用所有前端显示的21个策略
- 禁用旧的策略轮换逻辑
- 确保现代化系统正常工作
"""

import psycopg2
import json
from datetime import datetime

def fix_strategy_enabled_status():
    """修复策略启用状态"""
    print("🔧 === 开始修复策略启用状态 ===")
    
    try:
        # 连接数据库
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        # 1. 直接从数据库获取前21个最佳策略作为前端显示策略
        print("\n📊 1. 获取前端显示策略列表...")
        cursor.execute("""
            SELECT id, name, final_score 
            FROM strategies 
            WHERE id LIKE 'STRAT_%' AND final_score IS NOT NULL
            ORDER BY final_score DESC
            LIMIT 21
        """)
        
        strategy_rows = cursor.fetchall()
        display_strategies = []
        
        if strategy_rows:
            for row in strategy_rows:
                display_strategies.append({
                    'id': row[0],
                    'name': row[1] or 'Unknown',
                    'final_score': float(row[2]) if row[2] else 0.0
                })
        
        print(f"选择了 {len(display_strategies)} 个前端显示策略:")
        for i, strategy in enumerate(display_strategies[:5]):  # 只显示前5个
            print(f"  {i+1}. {strategy['id']}: {strategy['name']} (评分: {strategy['final_score']:.1f})")
        if len(display_strategies) > 5:
            print(f"  ... 还有 {len(display_strategies) - 5} 个策略")
        
        # 2. 检查当前启用状态
        print("\n🔍 2. 检查当前策略启用状态...")
        cursor.execute("""
            SELECT id, name, enabled, final_score 
            FROM strategies 
            WHERE id LIKE 'STRAT_%'
            ORDER BY final_score DESC
        """)
        
        all_strategies = cursor.fetchall()
        enabled_count = 0
        disabled_count = 0
        
        if all_strategies:
            try:
                enabled_count = sum(1 for s in all_strategies if len(s) > 2 and s[2])
                disabled_count = sum(1 for s in all_strategies if len(s) > 2 and not s[2])
            except (IndexError, TypeError) as e:
                print(f"⚠️ 处理策略状态时出错: {e}")
                enabled_count = len(all_strategies)  # 保守估计
        
        print(f"当前状态: {enabled_count} 个启用, {disabled_count} 个停用")
        
        # 3. 启用所有前端显示策略
        if display_strategies:
            print("\n✅ 3. 启用所有前端显示策略...")
            display_strategy_ids = [s['id'] for s in display_strategies]
            
            # 批量启用前端显示策略
            cursor.execute("""
                UPDATE strategies 
                SET enabled = 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ANY(%s)
            """, (display_strategy_ids,))
            
            enabled_display_count = cursor.rowcount
            print(f"已启用 {enabled_display_count} 个前端显示策略")
            
            # 4. 停用其他策略（非前端显示的）
            print("\n🚫 4. 停用非前端显示策略...")
            cursor.execute("""
                UPDATE strategies 
                SET enabled = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id LIKE 'STRAT_%' AND id != ALL(%s)
            """, (display_strategy_ids,))
            
            disabled_other_count = cursor.rowcount
            print(f"已停用 {disabled_other_count} 个非前端显示策略")
        else:
            print("⚠️ 没有找到前端显示策略，跳过启用步骤")
            enabled_display_count = 0
            disabled_other_count = 0
        
        # 5. 添加配置禁用旧的策略轮换逻辑
        print("\n🔒 5. 禁用旧的策略轮换逻辑...")
        cursor.execute("""
            INSERT INTO strategy_management_config (config_key, config_value, updated_at)
            VALUES ('strategy_rotation_enabled', 'false', CURRENT_TIMESTAMP)
            ON CONFLICT (config_key) 
            DO UPDATE SET 
                config_value = 'false',
                updated_at = CURRENT_TIMESTAMP
        """)
        
        cursor.execute("""
            INSERT INTO strategy_management_config (config_key, config_value, updated_at)
            VALUES ('auto_disable_enabled', 'false', CURRENT_TIMESTAMP)
            ON CONFLICT (config_key) 
            DO UPDATE SET 
                config_value = 'false',
                updated_at = CURRENT_TIMESTAMP
        """)
        
        # 6. 验证修复结果
        print("\n🔍 6. 验证修复结果...")
        cursor.execute("""
            SELECT 
                COUNT(*) as total_strategies,
                COUNT(*) FILTER (WHERE enabled = 1) as enabled_strategies,
                COUNT(*) FILTER (WHERE enabled = 0) as disabled_strategies
            FROM strategies 
            WHERE id LIKE 'STRAT_%'
        """)
        
        stats = cursor.fetchone()
        if stats and len(stats) >= 3:
            total, enabled, disabled = stats[0], stats[1], stats[2]
        else:
            print("⚠️ 无法获取统计信息，使用默认值")
            total, enabled, disabled = 0, 0, 0
        
        print(f"修复后状态:")
        print(f"  总策略数: {total}")
        print(f"  启用策略: {enabled}")
        print(f"  停用策略: {disabled}")
        
        # 7. 记录修复日志
        print("\n📝 7. 记录修复日志...")
        
        # 记录到统一日志表
        cursor.execute("""
            INSERT INTO unified_strategy_logs 
            (log_type, message, data, timestamp)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
        """, (
            'system_maintenance',
            '策略启用状态修复完成',
            json.dumps({
                'total_strategies': total,
                'enabled_strategies': enabled,
                'disabled_strategies': disabled,
                'display_strategies_count': len(display_strategies),
                'action': 'fix_strategy_enabled_status'
            })
        ))
        
        conn.commit()
        conn.close()
        
        print("\n✅ === 策略启用状态修复完成 ===")
        print(f"🎯 结果: {enabled} 个策略已启用进化，系统将开始正常工作")
        
        return {
            'success': True,
            'total_strategies': total,
            'enabled_strategies': enabled,
            'display_strategies': len(display_strategies)
        }
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return {'success': False, 'error': str(e)}

def disable_old_rotation_logic():
    """禁用quantitative_service.py中的旧轮换逻辑"""
    print("\n🔧 禁用旧的策略轮换逻辑...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        # 添加控制标志
        configs = [
            ('modern_system_enabled', 'true'),
            ('legacy_rotation_disabled', 'true'),
            ('auto_disable_strategies', 'false'),
            ('enable_all_display_strategies', 'true')
        ]
        
        for config_key, config_value in configs:
            cursor.execute("""
                INSERT INTO strategy_management_config (config_key, config_value, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (config_key) 
                DO UPDATE SET 
                    config_value = %s,
                    updated_at = CURRENT_TIMESTAMP
            """, (config_key, config_value, config_value))
        
        conn.commit()
        conn.close()
        
        print("✅ 旧逻辑控制配置已设置")
        
    except Exception as e:
        print(f"❌ 设置控制配置失败: {e}")

if __name__ == "__main__":
    # 执行修复
    result = fix_strategy_enabled_status()
    
    # 禁用旧逻辑
    disable_old_rotation_logic()
    
    if result['success']:
        print(f"\n🎉 修复成功！")
        print(f"📊 {result['enabled_strategies']} 个策略已启用")
        print(f"🔄 {result['display_strategies']} 个前端显示策略将持续进化")
        print(f"💡 建议立即重启服务以应用配置变更")
    else:
        print(f"\n❌ 修复失败: {result['error']}") 