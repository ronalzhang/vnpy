#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
全面修复自动停用策略逻辑
- 禁用所有自动停用策略的代码
- 确保前21个优质策略持续启用
- 保护前端显示策略不被错误停用
"""

import psycopg2
import json
from datetime import datetime

def fix_all_auto_disable_logic():
    """全面修复所有自动停用策略的逻辑"""
    print("🔧 === 开始全面修复自动停用策略逻辑 ===")
    
    try:
        # 连接数据库
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        # 1. 强制启用所有前21个优质策略
        print("\n✅ 1. 强制启用前21个优质策略...")
        cursor.execute("""
            UPDATE strategies 
            SET enabled = 1, 
                notes = 'top21_protected',
                updated_at = CURRENT_TIMESTAMP
            WHERE id IN (
                SELECT id FROM strategies 
                WHERE id LIKE 'STRAT_%' AND final_score IS NOT NULL
                ORDER BY final_score DESC 
                LIMIT 21
            )
        """)
        
        enabled_count = cursor.rowcount
        print(f"已强制启用 {enabled_count} 个前21优质策略")
        
        # 2. 添加保护标记配置
        print("\n🛡️ 2. 添加策略保护配置...")
        protection_configs = [
            ('disable_validation_failed_logic', 'true', '禁用验证失败自动停用逻辑'),
            ('disable_auto_rotation_logic', 'true', '禁用自动轮换停用逻辑'),
            ('protect_top21_strategies', 'true', '保护前21个策略不被停用'),
            ('modern_evolution_only', 'true', '只使用现代化进化系统'),
            ('legacy_disable_functions_off', 'true', '关闭所有旧版停用功能')
        ]
        
        for config_key, config_value, description in protection_configs:
            cursor.execute("""
                INSERT INTO strategy_management_config (config_key, config_value, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (config_key) 
                DO UPDATE SET 
                    config_value = %s,
                    updated_at = CURRENT_TIMESTAMP
            """, (config_key, config_value, config_value))
        
        print(f"已添加 {len(protection_configs)} 个保护配置")
        
        # 3. 检查并修复最近被错误停用的策略
        print("\n🔄 3. 检查最近被错误停用的策略...")
        cursor.execute("""
            SELECT id, name, final_score, notes 
            FROM strategies 
            WHERE id LIKE 'STRAT_%' 
            AND final_score >= 45.0
            AND enabled = 0 
            AND updated_at >= NOW() - INTERVAL '2 hours'
            ORDER BY final_score DESC
        """)
        
        recently_disabled = cursor.fetchall()
        recently_disabled = recently_disabled or []  # 确保不是None
        print(f"发现 {len(recently_disabled)} 个最近被错误停用的优质策略")
        
        if recently_disabled:
            strategy_ids = [s[0] for s in recently_disabled]
            
            # 重新启用这些策略
            cursor.execute("""
                UPDATE strategies 
                SET enabled = 1, 
                    notes = 'restored_after_fix',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ANY(%s)
            """, (strategy_ids,))
            
            restored_count = cursor.rowcount
            print(f"已恢复 {restored_count} 个被错误停用的优质策略")
            
            # 显示恢复的策略
            for strategy in recently_disabled[:5]:
                print(f"  ✅ {strategy[0]}: {strategy[1]} (评分: {strategy[2]:.1f})")
        
        # 4. 设置前端显示策略的特殊保护
        print("\n🔒 4. 设置前端显示策略特殊保护...")
        cursor.execute("""
            UPDATE strategies 
            SET notes = CASE 
                    WHEN final_score >= 60 THEN 'frontend_display_top_protected'
                    WHEN final_score >= 50 THEN 'frontend_display_mid_protected'
                    ELSE 'frontend_display_low_protected'
                END,
                enabled = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id IN (
                SELECT id FROM strategies 
                WHERE id LIKE 'STRAT_%' AND final_score IS NOT NULL
                ORDER BY final_score DESC 
                LIMIT 30  -- 保护前30个策略，确保前21个一定在保护范围内
            )
        """)
        
        protected_count = cursor.rowcount
        print(f"已设置 {protected_count} 个策略的特殊保护")
        
        # 5. 验证修复结果
        print("\n📊 5. 验证修复结果...")
        cursor.execute("""
            SELECT 
                COUNT(*) as total_strategies,
                COUNT(*) FILTER (WHERE enabled = 1) as enabled_strategies,
                COUNT(*) FILTER (WHERE enabled = 1 AND final_score >= 50) as enabled_good_strategies,
                COUNT(*) FILTER (WHERE notes LIKE '%protected%') as protected_strategies
            FROM strategies 
            WHERE id LIKE 'STRAT_%' AND final_score IS NOT NULL
        """)
        
        stats = cursor.fetchone()
        total, enabled, enabled_good, protected = stats
        
        print(f"修复后统计:")
        print(f"  总策略数: {total}")
        print(f"  启用策略: {enabled} ({enabled/total*100:.1f}%)")
        print(f"  启用优质策略(≥50分): {enabled_good}")
        print(f"  受保护策略: {protected}")
        
        # 6. 检查前21个策略状态
        print("\n🎯 6. 检查前21个策略最终状态:")
        cursor.execute("""
            SELECT id, enabled, final_score, notes
            FROM strategies 
            WHERE id LIKE 'STRAT_%' AND final_score IS NOT NULL
            ORDER BY final_score DESC
            LIMIT 21
        """)
        
        top21_final = cursor.fetchall()
        enabled_top21 = sum(1 for s in top21_final if s[1])
        
        print(f"前21个策略启用状态: {enabled_top21}/21")
        
        if enabled_top21 < 21:
            print("⚠️ 仍有策略未启用，列出详情:")
            for i, strategy in enumerate(top21_final):
                status = '✅' if strategy[1] else '❌'
                print(f"  {i+1}. {strategy[0]}: {status} | 评分:{strategy[2]:.1f} | 状态:{strategy[3]}")
        
        # 7. 记录修复日志
        print("\n📝 7. 记录修复日志...")
        cursor.execute("""
            INSERT INTO unified_strategy_logs 
            (log_type, message, data, timestamp)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
        """, (
            'system_maintenance',
            '全面修复自动停用策略逻辑完成',
            json.dumps({
                'total_strategies': total,
                'enabled_strategies': enabled,
                'enabled_good_strategies': enabled_good,
                'protected_strategies': protected,
                'top21_enabled': enabled_top21,
                'action': 'fix_all_auto_disable_logic'
            })
        ))
        
        conn.commit()
        conn.close()
        
        print("\n✅ === 全面修复自动停用策略逻辑完成 ===")
        print(f"🎯 结果: {enabled_top21}/21 个前端策略已启用并受保护")
        
        return {
            'success': True,
            'enabled_strategies': enabled,
            'top21_enabled': enabled_top21,
            'protected_strategies': protected
        }
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return {'success': False, 'error': str(e)}

def create_strategy_protection_mechanism():
    """创建策略保护机制，防止未来被错误停用"""
    print("\n🛡️ 创建策略保护机制...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        # 创建策略保护表（如果不存在）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_protection (
                id SERIAL PRIMARY KEY,
                strategy_id VARCHAR(50) UNIQUE,
                protection_level INTEGER DEFAULT 1,
                protection_reason TEXT,
                protected_since TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 为前21个策略添加保护记录
        cursor.execute("""
            INSERT INTO strategy_protection (strategy_id, protection_level, protection_reason)
            SELECT id, 3, 'Frontend display top 21 strategy'
            FROM strategies 
            WHERE id LIKE 'STRAT_%' AND final_score IS NOT NULL
            ORDER BY final_score DESC 
            LIMIT 21
            ON CONFLICT (strategy_id) 
            DO UPDATE SET 
                protection_level = 3,
                protection_reason = 'Frontend display top 21 strategy',
                last_check = CURRENT_TIMESTAMP
        """)
        
        protection_count = cursor.rowcount
        print(f"已为 {protection_count} 个策略添加保护记录")
        
        conn.commit()
        conn.close()
        
        print("✅ 策略保护机制创建完成")
        
    except Exception as e:
        print(f"❌ 创建保护机制失败: {e}")

if __name__ == "__main__":
    # 执行全面修复
    result = fix_all_auto_disable_logic()
    
    # 创建保护机制
    create_strategy_protection_mechanism()
    
    if result['success']:
        print(f"\n🎉 修复成功！")
        print(f"📊 {result['enabled_strategies']} 个策略已启用")
        print(f"🎯 {result['top21_enabled']}/21 个前端策略正常启用")
        print(f"🛡️ {result['protected_strategies']} 个策略受到保护")
        print(f"💡 建议立即检查策略活动情况")
    else:
        print(f"\n❌ 修复失败: {result['error']}") 