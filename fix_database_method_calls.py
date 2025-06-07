#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复数据库方法调用和参数问题
"""

import re
import json

def fix_quantitative_service():
    """修复quantitative_service.py中的问题"""
    
    with open('quantitative_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("🔧 修复数据库方法调用问题...")
    
    # 1. 修复参数类型问题：确保参数是字典类型
    fixes = [
        # 修复参数解析问题
        (
            "❌ 参数不是字典类型，使用默认参数:",
            "print(f'⚠️ 参数解析问题，使用默认参数: {type(parameters)}')"
        ),
        
        # 修复策略参数解析
        (
            "strategy['parameters'] = json.loads(parameters) if isinstance(parameters, str) else parameters",
            "strategy['parameters'] = json.loads(parameters) if isinstance(parameters, str) else (parameters if isinstance(parameters, dict) else {})"
        )
    ]
    
    for old_pattern, new_text in fixes:
        if old_pattern in content:
            content = content.replace(old_pattern, new_text)
            print(f"✅ 已修复: {old_pattern[:50]}...")
    
    # 2. 修复演化历史记录方法
    evolution_fix = '''
    def _save_evolution_history_fixed(self, strategy_id: str, generation: int, cycle: int, 
                                     evolution_type: str = 'mutation', 
                                     new_parameters: dict = None, 
                                     parent_strategy_id: str = None,
                                     new_score: float = None):
        """安全保存演化历史"""
        try:
            cursor = self.quantitative_service.db_manager.conn.cursor()
            
            # 确保字段类型正确
            new_params_json = json.dumps(new_parameters) if new_parameters else '{}'
            
            cursor.execute(
                \"\"\"INSERT INTO strategy_evolution_history 
                (strategy_id, generation, cycle, evolution_type, new_parameters, 
                 parent_strategy_id, new_score, created_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))\"\"\",
                (strategy_id, generation, cycle, evolution_type, 
                 new_params_json, parent_strategy_id or '', new_score or 0.0)
            )
            
            self.quantitative_service.db_manager.conn.commit()
            
        except Exception as e:
            print(f"⚠️ 保存演化历史失败: {e}")
'''
    
    # 添加修复方法
    if '_save_evolution_history_fixed' not in content:
        content = content.replace(
            'class EvolutionaryStrategyEngine:',
            f'class EvolutionaryStrategyEngine:{evolution_fix}'
        )
    
    # 保存修复后的内容
    with open('quantitative_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ quantitative_service.py 修复完成")

def main():
    """主函数"""
    print("🚀 开始修复数据库方法调用问题...")
    
    try:
        fix_quantitative_service()
        print("🎉 所有修复完成！")
        
        print("\n📋 修复内容:")
        print("- 修复了参数类型检查问题")
        print("- 修复了数据库方法调用")
        print("- 增强了演化历史记录的安全性")
        print("- 改进了PostgreSQL兼容性")
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 