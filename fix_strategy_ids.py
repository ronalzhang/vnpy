#!/usr/bin/env python3
"""
策略ID格式修复脚本
解决数据库中策略ID格式不一致的问题，统一使用完整的STRAT_前缀格式
"""

import psycopg2
import uuid
from datetime import datetime
import json

class StrategyIDFixer:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'user': 'quant_user', 
            'password': '123abc74531',
            'database': 'quantitative'
        }
        
    def get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(**self.db_config)
    
    def analyze_strategy_ids(self):
        """分析策略ID格式分布"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 统计不同格式的策略ID
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN id LIKE 'STRAT_%' THEN 'STRAT_格式'
                        WHEN LENGTH(id) = 8 AND id ~ '^[0-9a-f]+$' THEN '8位十六进制'
                        WHEN LENGTH(id) = 36 AND id ~ '^[0-9a-f-]+$' THEN 'UUID格式'
                        ELSE '其他格式'
                    END as format_type,
                    COUNT(*) as count
                FROM strategies 
                GROUP BY format_type
                ORDER BY count DESC
            """)
            
            results = cursor.fetchall()
            print("📊 策略ID格式分布：")
            for format_type, count in results:
                print(f"   {format_type}: {count}个")
            
            # 获取需要修复的策略
            cursor.execute("""
                SELECT id, name, symbol, type, final_score
                FROM strategies 
                WHERE id NOT LIKE 'STRAT_%'
                ORDER BY final_score DESC
                LIMIT 10
            """)
            
            problematic_ids = cursor.fetchall()
            print(f"\n🔍 发现{len(problematic_ids)}个需要修复的策略ID (显示前10个)：")
            for old_id, name, symbol, strategy_type, score in problematic_ids:
                print(f"   {old_id} -> {name} ({symbol}, {strategy_type}, 评分:{score})")
                
            return problematic_ids
            
        finally:
            cursor.close()
            conn.close()
    
    def fix_strategy_ids(self, dry_run=True):
        """修复策略ID格式"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 获取所有需要修复的策略
            cursor.execute("""
                SELECT id, name, symbol, type, parameters, final_score, win_rate, 
                       total_return, total_trades, generation, cycle, created_at, updated_at
                FROM strategies 
                WHERE id NOT LIKE 'STRAT_%'
                ORDER BY final_score DESC
            """)
            
            strategies_to_fix = cursor.fetchall()
            print(f"🔧 准备修复{len(strategies_to_fix)}个策略ID...")
            
            if dry_run:
                print("🔍 [DRY RUN] 预览修复计划：")
            
            fixed_count = 0
            
            for strategy_data in strategies_to_fix:
                old_id = strategy_data[0]
                name = strategy_data[1]
                strategy_type = strategy_data[3]
                
                # 生成新的完整策略ID
                new_id = f"STRAT_{strategy_type.upper()}_{uuid.uuid4().hex.upper()[:8]}"
                
                if dry_run:
                    print(f"   {old_id} -> {new_id} ({name})")
                else:
                    # 实际执行修复
                    try:
                        # 更新strategies表
                        cursor.execute("""
                            UPDATE strategies 
                            SET id = %s, updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (new_id, old_id))
                        
                        # 更新相关表的外键引用
                        self._update_foreign_key_references(cursor, old_id, new_id)
                        
                        print(f"✅ 已修复: {old_id} -> {new_id}")
                        fixed_count += 1
                        
                    except Exception as e:
                        print(f"❌ 修复失败 {old_id}: {e}")
                        conn.rollback()
                        continue
            
            if not dry_run:
                conn.commit()
                print(f"🎯 修复完成！共修复{fixed_count}个策略ID")
            else:
                print(f"🎯 预览完成！计划修复{len(strategies_to_fix)}个策略ID")
                print("💡 使用 fix_strategy_ids(dry_run=False) 执行实际修复")
                
        except Exception as e:
            print(f"❌ 修复过程发生错误: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    def _update_foreign_key_references(self, cursor, old_id, new_id):
        """更新其他表中的外键引用"""
        # 更新交易信号表
        cursor.execute("""
            UPDATE trading_signals 
            SET strategy_id = %s 
            WHERE strategy_id = %s
        """, (new_id, old_id))
        
        # 更新策略进化历史表
        cursor.execute("""
            UPDATE strategy_evolution_history 
            SET strategy_id = %s 
            WHERE strategy_id = %s
        """, (new_id, old_id))
        
        # 更新策略优化日志表
        cursor.execute("""
            UPDATE strategy_optimization_logs 
            SET strategy_id = %s 
            WHERE strategy_id = %s
        """, (new_id, old_id))
        
        # 更新父策略引用
        cursor.execute("""
            UPDATE strategies 
            SET parent_id = %s 
            WHERE parent_id = %s
        """, (new_id, old_id))

    def verify_fix(self):
        """验证修复结果"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 检查是否还有不完整的ID
            cursor.execute("""
                SELECT COUNT(*) 
                FROM strategies 
                WHERE id NOT LIKE 'STRAT_%'
            """)
            
            remaining_count = cursor.fetchone()[0]
            
            if remaining_count == 0:
                print("✅ 验证通过！所有策略ID已使用STRAT_格式")
            else:
                print(f"⚠️ 仍有{remaining_count}个策略ID需要修复")
                
            # 检查完整格式的数量
            cursor.execute("""
                SELECT COUNT(*) 
                FROM strategies 
                WHERE id LIKE 'STRAT_%'
            """)
            
            fixed_count = cursor.fetchone()[0]
            print(f"📊 当前使用STRAT_格式的策略: {fixed_count}个")
            
        finally:
            cursor.close()
            conn.close()

def main():
    print("🔧 策略ID格式修复工具")
    print("=" * 50)
    
    fixer = StrategyIDFixer()
    
    # 分析当前状况
    fixer.analyze_strategy_ids()
    
    print("\n" + "=" * 50)
    
    # 预览修复计划
    fixer.fix_strategy_ids(dry_run=True)
    
    print("\n" + "=" * 50)
    
    # 询问是否执行实际修复
    user_input = input("是否执行实际修复？(y/N): ").strip().lower()
    
    if user_input == 'y':
        print("开始执行实际修复...")
        fixer.fix_strategy_ids(dry_run=False)
        
        print("\n验证修复结果...")
        fixer.verify_fix()
    else:
        print("🛑 取消修复操作")

if __name__ == "__main__":
    main() 