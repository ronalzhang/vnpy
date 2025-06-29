#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🛡️ 终极策略保护脚本 - 确保前21个策略永远不被停用
"""

import psycopg2
from datetime import datetime

def apply_ultimate_protection():
    """应用终极策略保护"""
    try:
        conn = psycopg2.connect(
            host='localhost', 
            database='quantitative', 
            user='quant_user', 
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        print('🛡️ === 应用终极策略保护 ===')
        
        # 1. 强制启用前21个策略并设置保护标记
        cursor.execute('''
            UPDATE strategies 
            SET enabled = 1, 
                notes = 'ULTIMATE_PROTECTION_ACTIVE',
                protected_status = 999,
                is_persistent = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id IN (
                SELECT id FROM strategies 
                WHERE id LIKE 'STRAT_%' AND final_score IS NOT NULL
                ORDER BY final_score DESC 
                LIMIT 21
            )
        ''')
        
        protected_count = cursor.rowcount
        print(f'✅ 已对 {protected_count} 个策略应用终极保护')
        
        # 2. 创建保护触发器，防止任何UPDATE停用前21个策略
        trigger_sql = """
        CREATE OR REPLACE FUNCTION prevent_top21_disable()
        RETURNS TRIGGER AS $$
        BEGIN
            -- 检查是否是前21个策略
            IF NEW.id IN (
                SELECT id FROM strategies 
                WHERE id LIKE 'STRAT_%' AND final_score IS NOT NULL
                ORDER BY final_score DESC 
                LIMIT 21
            ) THEN
                -- 如果试图停用前21个策略，强制保持启用
                IF NEW.enabled = 0 THEN
                    NEW.enabled = 1;
                    NEW.notes = 'AUTO_PROTECTION_BLOCKED_DISABLE';
                    RAISE NOTICE '🛡️ 策略 % 受到终极保护，阻止停用操作', NEW.id;
                END IF;
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        cursor.execute(trigger_sql)
        
        # 删除旧触发器（如果存在）
        cursor.execute("DROP TRIGGER IF EXISTS protect_top21_strategies ON strategies")
        
        # 创建新触发器
        cursor.execute("""
            CREATE TRIGGER protect_top21_strategies 
            BEFORE UPDATE ON strategies 
            FOR EACH ROW 
            EXECUTE FUNCTION prevent_top21_disable()
        """)
        
        print('✅ 数据库保护触发器已创建')
        
        # 3. 记录保护历史
        cursor.execute('''
            INSERT INTO strategy_evolution_history 
            (strategy_id, generation, cycle, evolution_type, new_parameters, created_time, notes)
            SELECT id, 1, 1, 'ultimate_protection', '{}', CURRENT_TIMESTAMP, 
                   'Ultimate protection applied - strategy cannot be disabled'
            FROM strategies 
            WHERE id IN (
                SELECT id FROM strategies 
                WHERE id LIKE 'STRAT_%' AND final_score IS NOT NULL
                ORDER BY final_score DESC 
                LIMIT 21
            )
        ''')
        
        # 4. 验证保护效果
        cursor.execute('''
            SELECT 
                COUNT(*) FILTER (WHERE enabled = 1) as enabled_count,
                COUNT(*) as total_count,
                COUNT(*) FILTER (WHERE protected_status = 999) as protected_count
            FROM strategies 
            WHERE id IN (
                SELECT id FROM strategies 
                WHERE id LIKE 'STRAT_%' AND final_score IS NOT NULL
                ORDER BY final_score DESC 
                LIMIT 21
            )
        ''')
        
        result = cursor.fetchone()
        if result:
            enabled, total, protected = result
        else:
            enabled, total, protected = 0, 0, 0
        
        print(f'🎯 保护结果验证:')
        print(f'  - 前21个策略: {total}个')
        print(f'  - 已启用: {enabled}个')
        print(f'  - 已保护: {protected}个')
        
        if enabled == 21 and protected == 21:
            print('🎉 终极保护完全成功！')
        else:
            print('⚠️ 保护可能不完整，请检查')
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f'❌ 应用终极保护失败: {e}')
        return False

def test_protection():
    """测试保护机制"""
    try:
        conn = psycopg2.connect(
            host='localhost', 
            database='quantitative', 
            user='quant_user', 
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        print('🧪 === 测试保护机制 ===')
        
        # 获取一个前21的策略ID进行测试
        cursor.execute('''
            SELECT id FROM strategies 
            WHERE id LIKE 'STRAT_%' AND final_score IS NOT NULL
            ORDER BY final_score DESC 
            LIMIT 1
        ''')
        
        test_strategy = cursor.fetchone()
        if not test_strategy:
            print('❌ 没有找到测试策略')
            return False
        
        strategy_id = test_strategy[0]
        print(f'🎯 使用策略 {strategy_id[-8:]} 进行保护测试')
        
        # 尝试停用策略（应该被触发器阻止）
        cursor.execute('''
            UPDATE strategies 
            SET enabled = 0, notes = 'TEST_DISABLE_ATTEMPT' 
            WHERE id = %s
        ''', (strategy_id,))
        
        # 检查策略是否仍然启用
        cursor.execute('''
            SELECT enabled, notes FROM strategies WHERE id = %s
        ''', (strategy_id,))
        
        result = cursor.fetchone()
        if result:
            enabled, notes = result
        else:
            enabled, notes = 0, 'NO_DATA'
        
        if enabled == 1 and 'AUTO_PROTECTION_BLOCKED_DISABLE' in str(notes):
            print('✅ 保护测试成功！策略停用操作被阻止')
        else:
            print(f'❌ 保护测试失败！策略状态: enabled={enabled}, notes={notes}')
        
        conn.commit()
        conn.close()
        
        return enabled == 1
        
    except Exception as e:
        print(f'❌ 保护测试失败: {e}')
        return False

if __name__ == "__main__":
    print('🚀 启动终极策略保护系统')
    
    if apply_ultimate_protection():
        print('✅ 终极保护已应用')
        
        if test_protection():
            print('🎉 保护机制测试通过')
        else:
            print('⚠️ 保护机制测试失败')
    else:
        print('❌ 终极保护应用失败') 