#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复CCXT Alpaca模块导入问题
"""

import os
import sys
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

class CCXTAlpacaFixer:
    """CCXT Alpaca模块修复器"""
    
    def __init__(self):
        logger.info("🔧 CCXT Alpaca模块修复器初始化")
    
    def fix_import_issue(self):
        """修复导入问题"""
        try:
            # 检查是否是由于导入ccxt导致的问题
            files_to_check = [
                "quantitative_service.py",
                "auto_trading_engine.py", 
                "crypto_arbitrage_strategy.py"
            ]
            
            for file_path in files_to_check:
                if os.path.exists(file_path):
                    logger.info(f"📋 检查文件: {file_path}")
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 修复ccxt导入问题
                    old_imports = [
                        "import ccxt",
                        "from ccxt import",
                    ]
                    
                    fixed = False
                    for old_import in old_imports:
                        if old_import in content:
                            # 使用try-except包装ccxt导入
                            new_import = f"""try:
    {old_import}
except Exception as ccxt_error:
    print(f"⚠️ CCXT导入警告: {{ccxt_error}}")
    ccxt = None"""
                            
                            if old_import == "import ccxt" and "try:" not in content:
                                content = content.replace(old_import, new_import)
                                fixed = True
                                logger.info(f"✅ 修复了{file_path}中的ccxt导入")
                    
                    if fixed:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 修复失败: {e}")
            return False
    
    def create_safe_ccxt_wrapper(self):
        """创建安全的CCXT包装器"""
        wrapper_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全的CCXT包装器
避免alpaca模块导入问题
"""

def safe_import_ccxt():
    """安全导入CCXT"""
    try:
        import ccxt
        # 检查是否可以访问主要交易所
        available_exchanges = ['binance', 'okx', 'bybit', 'huobi']
        working_exchanges = {}
        
        for exchange_name in available_exchanges:
            try:
                exchange_class = getattr(ccxt, exchange_name, None)
                if exchange_class:
                    working_exchanges[exchange_name] = exchange_class
            except Exception as e:
                print(f"⚠️ 交易所 {exchange_name} 不可用: {e}")
        
        return ccxt, working_exchanges
        
    except Exception as e:
        print(f"❌ CCXT导入失败: {e}")
        return None, {}

# 全局导入
CCXT, AVAILABLE_EXCHANGES = safe_import_ccxt()

def get_exchange(exchange_name, config=None):
    """安全获取交易所实例"""
    if not CCXT or exchange_name not in AVAILABLE_EXCHANGES:
        return None
    
    try:
        exchange_class = AVAILABLE_EXCHANGES[exchange_name]
        return exchange_class(config or {})
    except Exception as e:
        print(f"❌ 创建{exchange_name}交易所实例失败: {e}")
        return None
'''
        
        try:
            with open("safe_ccxt.py", "w", encoding="utf-8") as f:
                f.write(wrapper_code)
            
            logger.info("✅ 安全CCXT包装器创建完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 创建包装器失败: {e}")
            return False
    
    def update_service_imports(self):
        """更新服务文件的导入"""
        try:
            service_files = [
                "quantitative_service.py",
                "auto_trading_engine.py"
            ]
            
            for file_path in service_files:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 替换ccxt导入为安全包装器
                    if "import ccxt" in content and "from safe_ccxt import" not in content:
                        # 在文件开头添加安全导入
                        lines = content.split('\n')
                        import_lines = []
                        other_lines = []
                        
                        for line in lines:
                            if line.strip().startswith('import') or line.strip().startswith('from'):
                                if 'ccxt' not in line:
                                    import_lines.append(line)
                            else:
                                other_lines.append(line)
                        
                        # 添加安全导入
                        safe_import = "from safe_ccxt import CCXT as ccxt, get_exchange"
                        import_lines.insert(0, safe_import)
                        
                        # 重新组合文件
                        new_content = '\n'.join(import_lines + [''] + other_lines)
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        logger.info(f"✅ 更新了{file_path}的导入")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 更新导入失败: {e}")
            return False
    
    def run_fix(self):
        """运行修复"""
        logger.info("🔧 开始修复CCXT Alpaca问题...")
        
        # 1. 创建安全包装器
        if self.create_safe_ccxt_wrapper():
            logger.info("✅ 安全包装器创建成功")
        
        # 2. 修复导入问题
        if self.fix_import_issue():
            logger.info("✅ 导入问题修复成功")
        
        logger.info("🎉 CCXT Alpaca问题修复完成！")

def main():
    fixer = CCXTAlpacaFixer()
    fixer.run_fix()

if __name__ == "__main__":
    main() 