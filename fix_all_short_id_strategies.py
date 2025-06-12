#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复所有短ID策略脚本
批量将短ID策略更新为完整UUID格式
"""

import psycopg2
import uuid
import json
from datetime import datetime

def fix_all_short_id_strategies():
    """批量修复所有短ID策略"""
    conn = psycopg2.connect(
        host='localhost',
        database='quantitative',
        user='quant_user',
        password='123abc74531'
    )
    cursor = conn.cursor()
    
    try:
        print("🔍 开始查找短ID策略...")
        
        # 查找所有长度<30的策略ID (标准UUID应该是36位)
        cursor.execute("""
            SELECT id, name, type, symbol 
            FROM strategies 
            WHERE LENGTH(id) < 30 
            ORDER BY LENGTH(id), id
        """)
        
        short_id_strategies = cursor.fetchall()
        total_count = len(short_id_strategies)
        
        if total_count == 0:
            print("✅ 没有发现短ID策略，全部使用完整格式")
            return
        
        print(f"🚨 发现 {total_count} 个短ID策略需要修复")
        
        # 显示修复计划
        for i, (old_id, name, strategy_type, symbol) in enumerate(short_id_strategies[:10]):
            print(f"  {i+1}. {old_id} ({len(old_id)}位) -> {name[:20]}...")
        
        if total_count > 10:
            print(f"  ... 还有 {total_count - 10} 个策略")
        
        print(f"\n🔧 开始批量修复...")
        
        updated_count = 0
        id_mapping = {}  # 存储旧ID到新ID的映射
        
        for old_id, name, strategy_type, symbol in short_id_strategies:
            try:
                # 生成新的完整UUID格式ID
                new_uuid = uuid.uuid4().hex[:8].upper()
                new_id = f"STRAT_{strategy_type.upper()}_{new_uuid}"
                
                # 检查新ID是否已存在
                cursor.execute("SELECT id FROM strategies WHERE id = %s", (new_id,))
                while cursor.fetchone():
                    new_uuid = uuid.uuid4().hex[:8].upper()
                    new_id = f"STRAT_{strategy_type.upper()}_{new_uuid}"
                    cursor.execute("SELECT id FROM strategies WHERE id = %s", (new_id,))
                
                # 更新策略表
                cursor.execute("""
                    UPDATE strategies 
                    SET id = %s, updated_at = %s 
                    WHERE id = %s
                """, (new_id, datetime.now(), old_id))
                
                # 更新所有相关表
                related_tables = [
                    'trading_signals',
                    'strategy_trade_logs', 
                    'strategy_optimization_logs',
                    'strategy_validation',
                    'strategy_initialization',
                    'strategy_initialization_validation',
                    'parameter_updated'
                ]
                
                for table in related_tables:
                    try:
                        cursor.execute(f"""
                            UPDATE {table} 
                            SET strategy_id = %s 
                            WHERE strategy_id = %s
                        """, (new_id, old_id))
                        print(f"    ✅ 更新表 {table}")
                    except Exception as e:
                        print(f"    ⚠️ 表 {table} 更新失败: {e}")
                
                id_mapping[old_id] = new_id
                updated_count += 1
                
                if updated_count % 50 == 0:
                    print(f"  📊 已处理 {updated_count}/{total_count} 个策略")
                    conn.commit()  # 每50个提交一次
                
            except Exception as e:
                print(f"❌ 修复策略 {old_id} 失败: {e}")
                continue
        
        # 最终提交
        conn.commit()
        
        print(f"\n🎉 修复完成!")
        print(f"✅ 成功修复 {updated_count}/{total_count} 个策略")
        print(f"📝 ID映射记录已创建，共 {len(id_mapping)} 条")
        
        # 验证修复结果
        cursor.execute("SELECT LENGTH(id), COUNT(*) FROM strategies GROUP BY LENGTH(id) ORDER BY LENGTH(id)")
        results = cursor.fetchall()
        
        print(f"\n📊 修复后策略ID长度分布:")
        for length, count in results:
            print(f"  {length}位: {count}个策略")
        
        # 保存映射记录到文件
        with open('strategy_id_mapping.json', 'w') as f:
            json.dump(id_mapping, f, indent=2)
        
        print(f"💾 ID映射记录已保存到 strategy_id_mapping.json")
        
    except Exception as e:
        print(f"❌ 修复过程失败: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    fix_all_short_id_strategies() 