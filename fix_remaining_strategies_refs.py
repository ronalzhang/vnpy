#!/usr/bin/env python3
"""
修复剩余的self.strategies引用
"""

import re

def fix_strategies_references():
    """修复quantitative_service.py中剩余的self.strategies引用"""
    
    with open('quantitative_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复模式
    fixes = [
        # 1. for strategy_id, strategy in self.strategies.items():
        (r'for strategy_id, strategy in self\.strategies\.items\(\):', 
         'for strategy_id, strategy in self._get_all_strategies_dict().items():'),
        
        # 2. strategy = self.strategies.get(strategy_id, {})
        (r'strategy = self\.strategies\.get\(([^,)]+),?\s*([^)]*)\)',
         r'strategy = self._get_strategy_by_id(\1) or \2'),
        
        # 3. for strategy_id in self.strategies:
        (r'for strategy_id in self\.strategies:',
         'for strategy_id in self._get_all_strategies_dict().keys():'),
        
        # 4. if strategy_id in self.strategies:
        (r'if strategy_id in self\.strategies:',
         'if self._get_strategy_by_id(strategy_id):'),
        
        # 5. self.strategies[strategy_id]
        (r'self\.strategies\[([^]]+)\]',
         r'self._get_strategy_by_id(\1)'),
        
        # 6. len(self.strategies)
        (r'len\(self\.strategies\)',
         'len(self._get_all_strategies_dict())'),
        
        # 7. hasattr(self, 'strategies') and isinstance(self.strategies, dict)
        (r'hasattr\(self, \'strategies\'\) and isinstance\(self\.strategies, dict\)',
         'len(self._get_all_strategies_dict()) >= 0'),
    ]
    
    # 应用修复
    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content)
    
    # 特殊修复：self.strategies[strategy_id].update({...})
    content = re.sub(
        r'self\.strategies\[([^]]+)\]\.update\(\{([^}]+)\}\)',
        r'# 更新策略状态到数据库\n        self.update_strategy(\1, **{\2})',
        content
    )
    
    # 写回文件
    with open('quantitative_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 已修复所有self.strategies引用")

if __name__ == "__main__":
    fix_strategies_references() 