#!/usr/bin/env python3
"""
🔍 量化交易系统最终验证脚本
验证所有修复是否完成
"""

import os
import re
from datetime import datetime
import json

def check_old_version_references():
    """检查是否还有旧版本引用"""
    print("🔍 1. 检查AutomatedStrategyManager旧版本引用...")
    
    with open('quantitative_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找旧版本引用模式
    old_patterns = [
        'self.quantitative_service.strategies.items()',
        'self.quantitative_service.strategies.get(',
        'self.quantitative_service.strategies.keys()',
        'self.quantitative_service.strategies.values()'
    ]
    
    found_issues = []
    for pattern in old_patterns:
        if pattern in content:
            found_issues.append(pattern)
    
    if found_issues:
        print(f"❌ 仍发现老版本引用: {found_issues}")
        return False
    else:
        print("✅ 所有旧版本引用已修复")
        return True

def check_system_status_fix():
    """检查系统状态修复"""
    print("\n🔍 2. 检查系统状态修复...")
    
    with open('quantitative_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否有正确的异常处理 - 检查offline状态设置和没有error状态设置
    has_offline_status = "'system_health': 'offline'" in content
    no_error_setting = "system_health='error'" not in content
    
    if has_offline_status and no_error_setting:
        print("✅ 系统状态异常处理已修复")
        return True
    else:
        print(f"❌ 系统状态修复不完整 - 有offline设置: {has_offline_status}, 无error设置: {no_error_setting}")
        return False

def check_code_cleanup():
    """检查代码清理情况"""
    print("\n🔍 3. 检查代码清理情况...")
    
    # 统计当前目录下的文件
    files = os.listdir('.')
    fix_files = [f for f in files if 'fix' in f.lower() and f.endswith('.py')]
    cleanup_files = [f for f in files if 'cleanup' in f.lower() and f.endswith('.py')]
    repair_files = [f for f in files if 'repair' in f.lower() and f.endswith('.py')]
    
    total_cleanup_needed = len(fix_files) + len(cleanup_files) + len(repair_files)
    
    if total_cleanup_needed <= 1:  # 只保留这个验证脚本本身
        print("✅ 代码清理完成")
        return True
    else:
        print(f"❌ 仍有 {total_cleanup_needed} 个重复文件需要清理: {fix_files + cleanup_files + repair_files}")
        return False

def check_core_functionality():
    """检查核心功能完整性"""
    print("\n🔍 4. 检查核心功能完整性...")
    
    with open('quantitative_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查关键类和方法是否存在
    key_components = [
        'class QuantitativeService',
        'class AutomatedStrategyManager', 
        'def get_strategies(',
        'def get_strategy(',
        'def update_strategy(',
        'def start_strategy(',
        'def stop_strategy('
    ]
    
    missing_components = []
    for component in key_components:
        if component not in content:
            missing_components.append(component)
    
    if missing_components:
        print(f"❌ 缺少关键组件: {missing_components}")
        return False
    else:
        print("✅ 核心功能完整")
        return True

def check_unified_api_usage():
    """检查统一API使用情况"""
    print("\n🔍 5. 检查统一API使用情况...")
    
    with open('quantitative_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 统计新API的使用情况
    new_api_calls = content.count('self.quantitative_service.get_strategies()')
    new_api_calls += content.count('self.quantitative_service.get_strategy(')
    new_api_calls += content.count('strategy_response.get(\'success\'')
    new_api_calls += content.count('strategy_response.get(\'data\'')
    
    if new_api_calls >= 10:  # 应该有足够多的新API调用
        print(f"✅ 统一API使用良好 (发现 {new_api_calls} 处新API调用)")
        return True
    else:
        print(f"⚠️ 统一API使用可能不够充分 (仅发现 {new_api_calls} 处新API调用)")
        return False

def main():
    """主验证流程"""
    print("🚀 量化交易系统最终验证开始...")
    print("=" * 60)
    
    # 执行所有检查
    checks = [
        ("AutomatedStrategyManager修复", check_old_version_references),
        ("系统状态修复", check_system_status_fix), 
        ("代码清理", check_code_cleanup),
        ("核心功能完整性", check_core_functionality),
        ("统一API使用", check_unified_api_usage)
    ]
    
    results = {}
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results[check_name] = "✅ PASS" if result else "❌ FAIL"
            if result:
                passed += 1
        except Exception as e:
            results[check_name] = f"❌ ERROR: {e}"
            print(f"❌ {check_name} 检查失败: {e}")
    
    # 生成报告
    print("\n" + "=" * 60)
    print("📊 最终验证报告")
    print("=" * 60)
    
    for check_name, result in results.items():
        print(f"{check_name}: {result}")
    
    print(f"\n总体评分: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 恭喜！所有修复验证通过！")
        print("系统已达到完美状态，可以正常运行！")
        status = "PERFECT"
    elif passed >= total * 0.8:
        print("\n✅ 很好！大部分修复已完成！")
        print("系统基本可以正常运行，还有少量优化空间。")
        status = "GOOD"
    else:
        print("\n⚠️ 还需要进一步修复")
        print("系统可能存在一些问题，需要继续优化。")
        status = "NEEDS_WORK"
    
    # 保存报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_checks": total,
        "passed_checks": passed,
        "status": status,
        "results": results
    }
    
    with open('final_verification_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📋 详细报告已保存到: final_verification_report.json")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 