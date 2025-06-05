#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
快速修复quantitative_service.py中的缩进错误
"""

def fix_indentation_error():
    """修复缩进错误"""
    print("🔧 修复缩进错误...")
    
    with open('quantitative_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复错误的调试日志行
    old_text = '''        try:
        # 调试：记录策略数据类型
        logger.debug(f"策略数据类型: {type(strategy)}, 内容预览: {list(strategy.keys()) if isinstance(strategy, dict) else 'not dict'}")

            # 1. 评估所有策略表现'''
    
    new_text = '''        try:
            # 1. 评估所有策略表现'''
    
    content = content.replace(old_text, new_text)
    
    with open('quantitative_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 缩进错误修复完成")

if __name__ == "__main__":
    fix_indentation_error() 