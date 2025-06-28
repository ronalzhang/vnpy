#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
彻底禁用所有自动停用逻辑的终极修复脚本
- 禁用 _auto_select_strategies 中的自动停用
- 禁用 _disable_strategy 自动调用
- 禁用 validation_failed 自动停用逻辑  
- 保护现代化策略管理系统不被旧逻辑干扰
"""

import os
import re
import shutil
from datetime import datetime

def backup_file(file_path):
    """备份文件"""
    backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"📄 已备份: {backup_path}")
    return backup_path

def fix_quantitative_service():
    """修复quantitative_service.py中的所有自动停用逻辑"""
    file_path = "quantitative_service.py"
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    backup_file(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    fixes_made = []
    
    # 修复1: 彻底禁用 _auto_select_strategies 中的自动停用逻辑
    pattern1 = r'(\s+for strategy_id in low_score_strategies:\s*\n\s+self\._disable_strategy\(strategy_id\))'
    if re.search(pattern1, content, re.MULTILINE):
        replacement1 = """            # ❌ 已禁用自动停用逻辑 - 与现代化策略管理系统冲突
            # for strategy_id in low_score_strategies:
            #     self._disable_strategy(strategy_id)
            print(f"🛡️ 跳过自动停用 {len(low_score_strategies)} 个低分策略 - 现代化管理系统接管")"""
        
        content = re.sub(pattern1, replacement1, content, flags=re.MULTILINE)
        fixes_made.append("禁用 _auto_select_strategies 自动停用逻辑")
    
    # 修复2: 保护 _disable_strategy 方法，添加保护检查
    pattern2 = r'(def _disable_strategy\(self, strategy_id: str\):\s*\n\s*"""停用策略"""\s*\n\s*try:)'
    if re.search(pattern2, content, re.MULTILINE):
        replacement2 = '''def _disable_strategy(self, strategy_id: str):
        """停用策略 - 已禁用自动调用"""
        try:
            # 🛡️ 保护机制：禁止自动停用前端策略
            print(f"⚠️ _disable_strategy 被调用，但已禁用自动停用功能: {strategy_id}")
            print("🛡️ 如需停用策略，请使用前端界面或 stop_strategy() 方法")
            return  # 直接返回，不执行停用操作'''
        
        content = re.sub(pattern2, replacement2, content, flags=re.MULTILINE)
        fixes_made.append("禁用 _disable_strategy 自动停用功能")
    
    # 修复3: 禁用 validation_failed 自动停用逻辑
    pattern3 = r'(\s+self\.quantitative_service\.db_manager\.execute_query\(\s*"UPDATE strategies SET notes = \'validation_failed_non_frontend\' WHERE id = %s",\s*\(strategy_id,\)\s*\))'
    if re.search(pattern3, content, re.MULTILINE | re.DOTALL):
        replacement3 = '''                    # ❌ 已禁用验证失败自动停用逻辑
                    # self.quantitative_service.db_manager.execute_query(
                    #     "UPDATE strategies SET notes = 'validation_failed_non_frontend' WHERE id = %s",
                    #     (strategy_id,)
                    # )
                    print(f"🛡️ 跳过验证失败自动停用: {strategy_id} - 现代化管理系统接管")'''
        
        content = re.sub(pattern3, replacement3, content, flags=re.MULTILINE | re.DOTALL)
        fixes_made.append("禁用 validation_failed 自动停用逻辑")
    
    # 修复4: 彻底禁用自动策略管理配置
    pattern4 = r"('enabled': False,  # 默认禁用，需手动启用全自动管理)"
    if re.search(pattern4, content):
        replacement4 = "'enabled': False,  # ❌ 已彻底禁用自动管理，防止与现代化系统冲突"
        content = re.sub(pattern4, replacement4, content)
        fixes_made.append("彻底禁用自动策略管理配置")
    
    # 修复5: 添加现代化策略管理保护机制
    pattern5 = r'(# 🚀 启动全自动策略管理线程\s*\n\s*if self\.auto_strategy_management\[\'enabled\'\]:)'
    if re.search(pattern5, content):
        replacement5 = '''# ❌ 已禁用全自动策略管理线程 - 与现代化系统冲突
        # if self.auto_strategy_management['enabled']:
        if False:  # 强制禁用'''
        content = re.sub(pattern5, replacement5, content)
        fixes_made.append("禁用全自动策略管理线程启动")
    
    # 修复6: 禁用策略轮换功能
    pattern6 = r'(def _auto_rotate_strategies\(self\):)'
    if re.search(pattern6, content):
        replacement6 = '''def _auto_rotate_strategies(self):
        """策略轮换 - 已禁用"""
        print("🛡️ 策略轮换功能已禁用，使用现代化策略管理系统")
        return  # 直接返回，不执行轮换
        
        # 原始轮换逻辑已禁用
        def _original_auto_rotate_strategies(self):'''
        content = re.sub(pattern6, replacement6, content)
        fixes_made.append("禁用策略轮换功能")
    
    # 修复7: 禁用性能评估自动停用
    pattern7 = r'(def _auto_review_strategy_performance\(self\):)'
    if re.search(pattern7, content):
        replacement7 = '''def _auto_review_strategy_performance(self):
        """策略性能评估 - 已禁用自动停用"""
        print("🛡️ 策略性能评估自动停用功能已禁用")
        return  # 直接返回，不执行自动停用
        
        # 原始性能评估逻辑已禁用  
        def _original_auto_review_strategy_performance(self):'''
        content = re.sub(pattern7, replacement7, content)
        fixes_made.append("禁用性能评估自动停用")
    
    # 检查是否有修改
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 修复完成: {file_path}")
        for fix in fixes_made:
            print(f"   ✓ {fix}")
        return True
    else:
        print(f"⚠️ 文件无需修改: {file_path}")
        return False

def main():
    """主函数"""
    print("🚀 === 彻底禁用所有自动停用逻辑 ===")
    print("⚠️ 这将完全禁用旧的自动策略管理逻辑")
    print("✅ 保护现代化策略管理系统不被干扰")
    print()
    
    # 修复主文件
    success = fix_quantitative_service()
    
    if success:
        print()
        print("🎉 === 修复完成 ===")
        print("✅ 所有自动停用逻辑已彻底禁用")
        print("🛡️ 现代化策略管理系统受到保护")
        print("📊 前端策略将保持启用状态")
        print()
        print("⚡ 下一步：重启服务器上的应用")
        print("   ssh -i baba.pem root@47.236.39.134 'cd /root/VNPY && pm2 restart all'")
    else:
        print("❌ 修复失败或无需修改")

if __name__ == "__main__":
    main() 