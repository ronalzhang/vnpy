#!/usr/bin/env python3

def fix_boolean_values():
    """修复quantitative_service.py中的boolean值为integer"""
    
    with open('quantitative_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复executed字段的boolean值
    boolean_fixes = [
        ("'executed': False", "'executed': 0"),
        ("'executed': True", "'executed': 1"),
        ("executed=False", "executed=0"),
        ("executed=True", "executed=1"),
        ("executed = true", "executed = 1"),
        ("executed = false", "executed = 0"),
    ]
    
    for old, new in boolean_fixes:
        content = content.replace(old, new)
    
    with open('quantitative_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 修复完成：boolean值转换为integer")

if __name__ == "__main__":
    fix_boolean_values() 