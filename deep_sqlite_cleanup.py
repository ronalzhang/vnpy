#!/usr/bin/env python3
"""
深度清理SQLite语法，逐行检查和修复
"""

import re
import os

def fix_line(line, line_num):
    """修复单行的SQLite语法"""
    original = line
    
    # 1. 修复SQL占位符 ? -> %s（只在SQL语句中）
    if any(keyword in line.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WHERE', 'VALUES']):
        # 精确替换SQL中的?占位符
        line = re.sub(r'(?<=[\'\"]\s*)[?](?=\s*[\'\",\)\s])', '%s', line)
        line = re.sub(r'(?<=\s)[?](?=\s*[,\)\s])', '%s', line)
        line = re.sub(r'VALUES\s*\([^)]*\?', lambda m: m.group(0).replace('?', '%s'), line)
        line = re.sub(r'SET\s+\w+\s*=\s*\?', lambda m: m.group(0).replace('?', '%s'), line)
        line = re.sub(r'WHERE\s+\w+\s*=\s*\?', lambda m: m.group(0).replace('?', '%s'), line)
    
    # 2. 修复execute调用中的占位符
    if 'execute(' in line and '?' in line:
        line = re.sub(r'execute\s*\(\s*[\'\"](.*?)[\'\"]\s*,', 
                     lambda m: m.group(0).replace('?', '%s'), line)
    
    # 3. 修复cursor.execute中的问号
    if 'cursor.execute' in line and '?' in line:
        line = re.sub(r'cursor\.execute\s*\(\s*[\'\"](.*?)[\'\"]\s*,', 
                     lambda m: m.group(0).replace('?', '%s'), line)
    
    # 4. 修复datetime('now')
    line = re.sub(r"datetime\s*\(\s*['\"]now['\"]\s*\)", "NOW()", line)
    
    # 5. 修复INSERT OR IGNORE/REPLACE
    line = re.sub(r'INSERT\s+OR\s+IGNORE\s+INTO', 'INSERT INTO', line)
    line = re.sub(r'INSERT\s+OR\s+REPLACE\s+INTO', 'INSERT INTO', line)
    
    # 6. 修复rowid
    line = re.sub(r'\browid\b', 'id', line)
    
    if line != original:
        print(f"  修复第{line_num}行: {original.strip()[:50]}... -> {line.strip()[:50]}...")
        return line, True
    
    return line, False

def deep_clean_file(file_path):
    """深度清理单个文件"""
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    print(f"\n🔧 深度清理: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    fixed_lines = []
    changed = False
    
    for i, line in enumerate(lines, 1):
        fixed_line, line_changed = fix_line(line, i)
        fixed_lines.append(fixed_line)
        if line_changed:
            changed = True
    
    if changed:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)
        print(f"✅ 已修复: {file_path}")
        return True
    else:
        print(f"✅ 无需修复: {file_path}")
        return False

def main():
    """主函数"""
    print("🧹 开始深度清理SQLite语法...")
    
    files_to_clean = [
        'quantitative_service.py',
        'web_app.py'
    ]
    
    total_fixed = 0
    
    for file_path in files_to_clean:
        if deep_clean_file(file_path):
            total_fixed += 1
    
    print(f"\n🎯 深度清理完成！共修复 {total_fixed} 个文件")

if __name__ == "__main__":
    main() 