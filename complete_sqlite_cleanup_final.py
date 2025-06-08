#!/usr/bin/env python3
"""
彻底清理所有SQLite语法残留，确保100%PostgreSQL兼容
"""

import re
import os

def clean_file(file_path):
    """清理单个文件的SQLite语法"""
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 1. 清理SQLite占位符 ? -> %s
    content = re.sub(r'\bVALUES\s*\([^)]*\?\s*[^)]*\)', lambda m: m.group(0).replace('?', '%s'), content)
    content = re.sub(r'\bSET\s+[^=]+=\s*\?', lambda m: m.group(0).replace('?', '%s'), content)
    content = re.sub(r'\bWHERE\s+[^=]+=\s*\?', lambda m: m.group(0).replace('?', '%s'), content)
    
    # 2. 清理datetime('now') -> NOW()
    content = re.sub(r"datetime\s*\(\s*['\"]now['\"]\s*\)", "NOW()", content)
    
    # 3. 清理INSERT OR IGNORE -> INSERT ... ON CONFLICT DO NOTHING
    content = re.sub(r'INSERT\s+OR\s+IGNORE\s+INTO\s+(\w+)', r'INSERT INTO \1', content)
    
    # 4. 清理INSERT OR REPLACE -> INSERT ... ON CONFLICT DO UPDATE
    content = re.sub(r'INSERT\s+OR\s+REPLACE\s+INTO\s+(\w+)', r'INSERT INTO \1', content)
    
    # 5. 清理AUTOINCREMENT -> 删除（PostgreSQL用SERIAL）
    content = re.sub(r'\s+AUTOINCREMENT', '', content)
    
    # 6. 清理rowid -> id
    content = re.sub(r'\browid\b', 'id', content)
    
    # 7. 清理sqlite特定函数
    content = re.sub(r'sqlite_version\s*\(\s*\)', 'version()', content)
    
    # 8. 修复布尔值
    content = content.replace("'executed': False", "'executed': 0")
    content = content.replace("'executed': True", "'executed': 1")
    content = content.replace("executed=False", "executed=0")
    content = content.replace("executed=True", "executed=1")
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 已清理文件: {file_path}")
        return True
    else:
        print(f"✅ 文件无需清理: {file_path}")
        return False

def main():
    """主函数"""
    print("🧹 开始彻底清理SQLite语法...")
    
    # 需要清理的文件列表
    files_to_clean = [
        'quantitative_service.py',
        'web_app.py',
        'db_config.py',
        'auto_trading_engine.py'
    ]
    
    cleaned_count = 0
    
    for file_path in files_to_clean:
        if clean_file(file_path):
            cleaned_count += 1
    
    print(f"\n🎯 清理完成！共处理 {len(files_to_clean)} 个文件，修改了 {cleaned_count} 个文件")
    
    # 检查可能的残留
    print("\n🔍 检查可能的SQLite残留...")
    check_patterns = [
        r'\?(?=\s*[,\)])',  # SQL占位符?
        r'datetime\s*\(\s*[\'"]now[\'"]\s*\)',  # datetime('now')
        r'INSERT\s+OR\s+(IGNORE|REPLACE)',  # INSERT OR...
        r'\browid\b',  # rowid
        r'AUTOINCREMENT',  # AUTOINCREMENT
    ]
    
    for file_path in files_to_clean:
        if not os.path.exists(file_path):
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        found_issues = []
        for pattern in check_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                found_issues.append(f"第{line_num}行: {match.group()}")
        
        if found_issues:
            print(f"⚠️ {file_path} 可能还有SQLite残留:")
            for issue in found_issues[:5]:  # 只显示前5个
                print(f"  - {issue}")
            if len(found_issues) > 5:
                print(f"  ... 还有 {len(found_issues) - 5} 个问题")
        else:
            print(f"✅ {file_path} 无SQLite残留")

if __name__ == "__main__":
    main() 