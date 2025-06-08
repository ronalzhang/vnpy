#!/usr/bin/env python3
"""
简单直接的SQLite语法修复
"""

import os

def fix_sql_placeholders(content):
    """修复SQL占位符"""
    # 先修复常见的SQL语句模式
    fixes = [
        ('VALUES (?, ?, ?)', 'VALUES (%s, %s, %s)'),
        ('VALUES (?, ?)', 'VALUES (%s, %s)'),
        ('SET score = ?', 'SET score = %s'),
        ('WHERE strategy_id = ?', 'WHERE strategy_id = %s'),
        ('WHERE id = ?', 'WHERE id = %s'),
        ("datetime('now')", "NOW()"),
        ('INSERT OR IGNORE INTO', 'INSERT INTO'),
        ('INSERT OR REPLACE INTO', 'INSERT INTO'),
    ]
    
    for old, new in fixes:
        content = content.replace(old, new)
    
    return content

def simple_fix_file(file_path):
    """简单修复文件"""
    if not os.path.exists(file_path):
        return False
    
    print(f"🔧 修复: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    content = fix_sql_placeholders(content)
    
    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 已修复: {file_path}")
        return True
    else:
        print(f"✅ 无需修复: {file_path}")
        return False

def main():
    """主函数"""
    print("🧹 开始简单SQLite修复...")
    
    files = ['quantitative_service.py', 'web_app.py']
    
    for file_path in files:
        simple_fix_file(file_path)
    
    print("🎯 修复完成！")

if __name__ == "__main__":
    main() 