#!/usr/bin/env python3
"""
修复信号ID格式问题
将所有 f"signal_{int(time.time() * 1000)}" 改为 int(time.time() * 1000)
"""

import re
import os

def fix_signal_id_in_file(file_path):
    """修复单个文件中的信号ID格式"""
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 原始内容备份
        original_content = content
        
        # 修复信号ID生成格式：f"signal_{int(time.time() * 1000)}" -> int(time.time() * 1000)
        pattern = r'id=f"signal_\{int\(time\.time\(\) \* 1000\)\}"'
        replacement = 'id=int(time.time() * 1000)'
        content = re.sub(pattern, replacement, content)
        
        # 修复生成信号时的ID格式
        pattern2 = r"'id': f\"signal_\{int\(time\.time\(\) \* 1000\)\}\""
        replacement2 = "'id': int(time.time() * 1000)"
        content = re.sub(pattern2, replacement2, content)
        
        # 检查是否有更改
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            changes = len(re.findall(pattern, original_content)) + len(re.findall(pattern2, original_content))
            print(f"✅ 修复 {file_path}: {changes} 处信号ID格式")
            return True
        else:
            print(f"ℹ️ {file_path}: 无需修复")
            return False
            
    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 开始修复信号ID格式问题...")
    
    # 需要修复的文件列表
    files_to_fix = [
        'quantitative_service.py',
        'web_app.py',
        'real_trading_manager.py'
    ]
    
    total_fixed = 0
    
    for file_path in files_to_fix:
        if fix_signal_id_in_file(file_path):
            total_fixed += 1
    
    print(f"✅ 信号ID格式修复完成，共修复 {total_fixed} 个文件")
    
    # 同时修改TradingSignal数据类的id字段类型
    print("\n🔧 修复TradingSignal数据类的id字段类型...")
    
    try:
        with open('quantitative_service.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修复TradingSignal的id字段类型从str改为int
        pattern = r'class TradingSignal:[\s\S]*?id: str'
        if 'id: str' in content:
            content = content.replace('id: str', 'id: int')
            
            with open('quantitative_service.py', 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ 修复TradingSignal.id字段类型为int")
        else:
            print("ℹ️ TradingSignal.id字段类型无需修复")
            
    except Exception as e:
        print(f"❌ 修复TradingSignal字段类型失败: {e}")

if __name__ == "__main__":
    main() 