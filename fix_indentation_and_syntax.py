#!/usr/bin/env python3
"""
修复quantitative_service.py中的缩进和语法问题
"""

def fix_quantitative_service():
    """修复quantitative_service.py文件"""
    
    # 读取文件内容
    with open('quantitative_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复缩进问题 - _save_system_status方法
    content = content.replace(
        '        if \'lookback_period\' in params:\n'
        '            params[\'lookback_period\'] = max(5, min(100, params[\'lookback_period\']))  # 限制在5-100\n'
        '    \n'
        '        def _save_system_status(self):',
        '        if \'lookback_period\' in params:\n'
        '            params[\'lookback_period\'] = max(5, min(100, params[\'lookback_period\']))  # 限制在5-100\n'
        '    \n'
        '    def _save_system_status(self):'
    )
    
    # 修复剩余的SQLite语法问题
    fixes = [
        # 修复 datetime('now') 为 NOW()
        ("datetime('now')", "NOW()"),
        
        # 修复 ? 占位符为 %s
        ("VALUES (?, ?, ?, datetime('now'))", "VALUES (%s, %s, %s, NOW())"),
        ("VALUES (?, ?, ?, ?, ?)", "VALUES (%s, %s, %s, %s, %s)"),
        ("VALUES (?, ?)", "VALUES (%s, %s)"),
        ("LIMIT ?", "LIMIT %s"),
        
        # 修复 INSERT OR REPLACE
        ("INSERT OR REPLACE INTO", "INSERT INTO"),
        
        # 修复 PostgreSQL 时间函数
        ("datetime('now', '-{} days')", "NOW() - INTERVAL '{} days'"),
    ]
    
    for old, new in fixes:
        content = content.replace(old, new)
    
    # 写回文件
    with open('quantitative_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 修复完成！")

if __name__ == "__main__":
    fix_quantitative_service() 