#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快速修复缩进问题
"""

def fix_indentation():
    """修复quantitative_service.py的缩进问题"""
    
    try:
        with open("quantitative_service.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 删除多余的try和docstring
        content = content.replace(
            '''        try:
        """保存策略配置到数据库"""
        try:''',
            '''        try:'''
        )
        
        # 修复缩进错误
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # 修复数据库操作部分的缩进
            if i >= 4820 and i <= 4850:
                if line.strip().startswith('# 立即提交每个策略'):
                    fixed_lines.append('            ' + line.strip())
                elif line.strip().startswith('self.conn.commit()') and 'for strategy_id' in lines[i-5]:
                    fixed_lines.append('            ' + line.strip())
                elif line.strip().startswith('except Exception as e:') and 'strategy_id' in line:
                    fixed_lines.append('        ' + line.strip())
                elif line.strip().startswith('print(f"保存策略 {strategy_id}'):
                    fixed_lines.append('            ' + line.strip())
                elif line.strip().startswith('continue'):
                    fixed_lines.append('            ' + line.strip())
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        
        # 写回文件
        with open("quantitative_service.py", "w", encoding="utf-8") as f:
            f.write('\n'.join(fixed_lines))
        
        print("✅ 缩进问题修复完成")
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False

if __name__ == "__main__":
    fix_indentation() 