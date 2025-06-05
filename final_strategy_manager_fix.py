#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
🛠️ 修复自动策略管理器中的数据类型错误
解决 'dict' object has no attribute 'config' 问题
"""

import re

def fix_strategy_manager_data_type_errors():
    """修复自动策略管理器中的数据类型错误"""
    
    print("🔧 修复自动策略管理器数据类型错误...")
    
    # 读取当前文件内容
    with open('quantitative_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 修复所有 strategy.config 的引用
    replacements = [
        # 修复参数访问
        (r'strategy\.config\.parameters\.get\(', 'strategy.get("parameters", {}).get('),
        (r'strategy\.config\.parameters\.copy\(\)', 'strategy.get("parameters", {}).copy()'),
        (r'strategy\.config\.name', 'strategy.get("name", "")'),
        (r'strategy\.config\.symbol', 'strategy.get("symbol", "")'),
        (r'strategy\.config\.id', 'strategy.get("id", "")'),
    ]
    
    # 应用所有替换
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    # 2. 修复策略对象实例化问题
    # 在 _optimize_strategy_parameters 和相关方法中，确保正确处理策略字典
    
    # 查找并修复策略实例化的地方
    # 将所有策略对象访问改为字典访问
    
    optimization_fixes = [
        # 修复参数优化中的策略访问
        (r'for strategy in self\.strategies\.values\(\):', 
         'for strategy_id, strategy in performances.items():'),
        (r'strategy_obj = self\.strategies\.get\(strategy_id\)',
         'strategy_obj = performances.get(strategy_id)')
    ]
    
    for pattern, replacement in optimization_fixes:
        content = re.sub(pattern, replacement, content)
    
    # 3. 添加防护代码以确保数据完整性
    defensive_code = '''
    def _safe_get_strategy_attr(self, strategy, attr_path, default=None):
        """安全获取策略属性，支持嵌套路径"""
        try:
            # 如果是字典，使用字典访问
            if isinstance(strategy, dict):
                keys = attr_path.split('.')
                value = strategy
                for key in keys:
                    if isinstance(value, dict):
                        value = value.get(key, {})
                    else:
                        return default
                return value if value != {} else default
            else:
                # 如果是对象，使用属性访问
                return getattr(strategy, attr_path, default)
        except Exception:
            return default
'''
    
    # 在 AutomatedStrategyManager 类定义后添加防护方法
    if '_safe_get_strategy_attr' not in content:
        class_match = re.search(r'(class AutomatedStrategyManager:.*?\n)', content, re.DOTALL)
        if class_match:
            insert_pos = class_match.end()
            content = content[:insert_pos] + defensive_code + content[insert_pos:]
    
    # 4. 修复具体的错误行
    specific_fixes = [
        # 修复第1821行附近
        (r'base_quantity = strategy\.config\.parameters\.get\(\'quantity\', 1\.0\)',
         'base_quantity = strategy.get("parameters", {}).get("quantity", 1.0)'),
        
        # 修复第1826行附近
        (r'new_params = strategy\.config\.parameters\.copy\(\)',
         'new_params = strategy.get("parameters", {}).copy()'),
        
        # 修复第1831-1832行附近
        (r'strategy\.config\.name,\s*strategy\.config\.symbol,',
         'strategy.get("name", ""), strategy.get("symbol", ""),'),
        
        # 修复第1840行附近
        (r'quantity = strategy\.config\.parameters\.get\(\'quantity\', 0\)',
         'quantity = strategy.get("parameters", {}).get("quantity", 0)'),
        
        # 修复第1851行附近
        (r'quantity = strategy\.config\.parameters\.get\(\'quantity\', 0\)',
         'quantity = strategy.get("parameters", {}).get("quantity", 0)'),
        
        # 修复第1857-1858行附近
        (r'current_quantity = strategy\.config\.parameters\.get\(\'quantity\', 1\.0\)\s*new_params = strategy\.config\.parameters\.copy\(\)',
         'current_quantity = strategy.get("parameters", {}).get("quantity", 1.0)\n        new_params = strategy.get("parameters", {}).copy()'),
        
        # 修复第1862-1864行附近
        (r'strategy\.config\.id,\s*strategy\.config\.name,\s*strategy\.config\.symbol,',
         'strategy.get("id", ""), strategy.get("name", ""), strategy.get("symbol", ""),'),
        
        # 修复第1872行附近
        (r'new_params = strategy\.config\.parameters\.copy\(\)',
         'new_params = strategy.get("parameters", {}).copy()'),
        
        # 修复第1877-1878行附近
        (r'strategy\.config\.name,\s*strategy\.config\.symbol,',
         'strategy.get("name", ""), strategy.get("symbol", ""),'),
        
        # 修复第1966行附近
        (r'current_params = strategy\.config\.parameters\.copy\(\)',
         'current_params = strategy.get("parameters", {}).copy()'),
        
        # 修复第1989-1990行附近
        (r'strategy\.config\.name,\s*strategy\.config\.symbol,',
         'strategy.get("name", ""), strategy.get("symbol", ""),'),
        
        # 修复第2002行附近
        (r'current_params = strategy\.config\.parameters\.copy\(\)',
         'current_params = strategy.get("parameters", {}).copy()'),
        
        # 修复第2028-2029行附近
        (r'strategy\.config\.name,\s*strategy\.config\.symbol,',
         'strategy.get("name", ""), strategy.get("symbol", ""),'),
    ]
    
    for pattern, replacement in specific_fixes:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    # 5. 添加调试日志以便追踪问题
    debug_logging = '''
        # 调试：记录策略数据类型
        logger.debug(f"策略数据类型: {type(strategy)}, 内容预览: {list(strategy.keys()) if isinstance(strategy, dict) else 'not dict'}")
'''
    
    # 在自动管理方法开始处添加调试日志
    content = re.sub(
        r'(def auto_manage_strategies\(self\):.*?\n.*?try:)',
        r'\1' + debug_logging,
        content,
        flags=re.DOTALL
    )
    
    # 保存修复后的文件
    with open('quantitative_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 自动策略管理器数据类型错误修复完成")
    print("   - 修复了所有 strategy.config 访问")
    print("   - 添加了防护代码")
    print("   - 加入了调试日志")
    
    return True

def verify_fix():
    """验证修复结果"""
    print("\n🔍 验证修复结果...")
    
    with open('quantitative_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否还有未修复的 strategy.config 引用
    remaining_errors = re.findall(r'strategy\.config\.[^"\']*', content)
    
    if remaining_errors:
        print(f"⚠️ 发现 {len(remaining_errors)} 个未修复的引用:")
        for error in remaining_errors[:5]:  # 只显示前5个
            print(f"   - {error}")
    else:
        print("✅ 所有 strategy.config 引用已修复")
    
    # 检查是否添加了防护方法
    if '_safe_get_strategy_attr' in content:
        print("✅ 防护方法已添加")
    else:
        print("⚠️ 防护方法未添加")
    
    return len(remaining_errors) == 0

if __name__ == "__main__":
    print("🛠️ 修复自动策略管理器数据类型错误")
    print("=" * 50)
    
    # 执行修复
    success = fix_strategy_manager_data_type_errors()
    
    if success:
        # 验证修复
        verify_success = verify_fix()
        
        if verify_success:
            print("\n✅ 修复成功！自动交易引擎崩溃问题应该已解决")
            print("请重新部署到服务器测试")
        else:
            print("\n⚠️ 修复可能不完整，请检查验证结果")
    else:
        print("\n❌ 修复失败，请手动检查代码") 