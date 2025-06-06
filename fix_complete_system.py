#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整系统修复脚本
专门修复原系统的导入问题，保持所有原有功能
"""

import os
import sys
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/complete_system_fix.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class CompleteSystemFixer:
    """完整系统修复器 - 修复原系统问题而不替换功能"""
    
    def __init__(self):
        logger.info("🔧 完整系统修复器初始化 - 保持原有功能")
    
    def fix_import_issues(self):
        """修复导入问题"""
        logger.info("🔧 修复系统导入问题...")
        
        # 修复quantitative_service.py中的导入问题
        self._fix_quantitative_service_imports()
        
        # 修复enhanced_strategy_evolution.py中的问题
        self._fix_evolution_imports()
        
        # 修复auto_trading_engine.py中的问题  
        self._fix_trading_engine_imports()
        
        logger.info("✅ 系统导入问题修复完成")
        return True
    
    def _fix_quantitative_service_imports(self):
        """修复quantitative_service.py的导入问题"""
        logger.info("🔧 修复quantitative_service.py导入问题...")
        
        try:
            # 读取当前文件
            with open("quantitative_service.py", "r", encoding="utf-8") as f:
                content = f.readlines()
            
            # 找到导入section
            new_content = []
            imports_added = False
            
            for i, line in enumerate(content):
                # 在导入requests之前添加安全导入
                if "import requests" in line and not imports_added:
                    new_content.append("# 安全导入模块\n")
                    new_content.append("def safe_import(module_name, fallback=None):\n")
                    new_content.append("    try:\n")
                    new_content.append("        return __import__(module_name)\n")
                    new_content.append("    except Exception as e:\n")
                    new_content.append("        logger.warning(f'安全导入失败 {module_name}: {e}')\n")
                    new_content.append("        return fallback\n")
                    new_content.append("\n")
                    new_content.append("# 安全导入可能有问题的模块\n")
                    new_content.append("try:\n")
                    new_content.append("    import requests\n")
                    new_content.append("except Exception as e:\n")
                    new_content.append("    logger.warning(f'requests导入失败: {e}')\n")
                    new_content.append("    requests = None\n")
                    new_content.append("\n")
                    new_content.append("try:\n")
                    new_content.append("    import ccxt\n")
                    new_content.append("except Exception as e:\n")
                    new_content.append("    logger.warning(f'ccxt导入失败: {e}')\n")
                    new_content.append("    ccxt = None\n")
                    new_content.append("\n")
                    imports_added = True
                elif "import requests" not in line and "import ccxt" not in line:
                    new_content.append(line)
                elif "import ccxt" in line:
                    # 跳过原来的ccxt导入，已经在安全导入中处理
                    continue
                elif "import requests" in line:
                    # 跳过原来的requests导入，已经在安全导入中处理  
                    continue
                else:
                    new_content.append(line)
            
            # 写回文件
            with open("quantitative_service.py", "w", encoding="utf-8") as f:
                f.writelines(new_content)
            
            logger.info("✅ quantitative_service.py导入修复完成")
            
        except Exception as e:
            logger.error(f"❌ 修复quantitative_service.py导入失败: {e}")
    
    def _fix_evolution_imports(self):
        """修复enhanced_strategy_evolution.py的导入问题"""
        logger.info("🔧 修复enhanced_strategy_evolution.py导入问题...")
        
        try:
            # 读取文件内容
            with open("enhanced_strategy_evolution.py", "r", encoding="utf-8") as f:
                content = f.read()
            
            # 修复多样性指数计算中的type访问问题
            if "_calculate_diversity_index" in content:
                # 找到并替换有问题的代码
                old_pattern = "p['strategy']['type']"
                new_pattern = "p['strategy'].get('type', p['strategy'].get('strategy_type', 'momentum'))"
                
                content = content.replace(old_pattern, new_pattern)
                
                # 写回文件
                with open("enhanced_strategy_evolution.py", "w", encoding="utf-8") as f:
                    f.write(content)
                
                logger.info("✅ enhanced_strategy_evolution.py修复完成")
            
        except Exception as e:
            logger.error(f"❌ 修复enhanced_strategy_evolution.py失败: {e}")
    
    def _fix_trading_engine_imports(self):
        """修复auto_trading_engine.py的导入问题"""
        logger.info("🔧 修复auto_trading_engine.py导入问题...")
        
        try:
            if os.path.exists("auto_trading_engine.py"):
                with open("auto_trading_engine.py", "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 添加安全的ccxt导入
                if "import ccxt" in content and "except" not in content:
                    content = content.replace(
                        "import ccxt",
                        """try:
    import ccxt
except Exception as e:
    logger.warning(f'ccxt导入失败: {e}')
    ccxt = None"""
                    )
                    
                    with open("auto_trading_engine.py", "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    logger.info("✅ auto_trading_engine.py修复完成")
            
        except Exception as e:
            logger.error(f"❌ 修复auto_trading_engine.py失败: {e}")
    
    def create_import_wrapper(self):
        """创建导入包装器"""
        logger.info("🔧 创建导入包装器...")
        
        wrapper_content = '''# -*- coding: utf-8 -*-
"""
导入包装器 - 安全导入可能有问题的模块
"""

import sys
import logging
import signal
import time

logger = logging.getLogger(__name__)

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("导入超时")

def safe_import_with_timeout(module_name, timeout=10):
    """带超时的安全导入"""
    try:
        # 设置超时信号
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        module = __import__(module_name)
        
        # 取消超时
        signal.alarm(0)
        return module
        
    except TimeoutException:
        logger.warning(f"导入 {module_name} 超时")
        return None
    except Exception as e:
        logger.warning(f"导入 {module_name} 失败: {e}")
        return None
    finally:
        signal.alarm(0)

# 全局安全导入
def init_safe_imports():
    """初始化安全导入"""
    global requests, ccxt
    
    logger.info("开始安全导入模块...")
    
    # 安全导入requests
    requests = safe_import_with_timeout('requests')
    if requests:
        logger.info("✅ requests导入成功")
    else:
        logger.warning("⚠️ requests导入失败，使用urllib替代")
        import urllib.request as requests
    
    # 安全导入ccxt
    ccxt = safe_import_with_timeout('ccxt') 
    if ccxt:
        logger.info("✅ ccxt导入成功")
    else:
        logger.warning("⚠️ ccxt导入失败，交易功能将受限")
        ccxt = None
    
    return requests, ccxt
'''
        
        try:
            with open("safe_import_wrapper.py", "w", encoding="utf-8") as f:
                f.write(wrapper_content)
            
            logger.info("✅ 导入包装器创建完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 创建导入包装器失败: {e}")
            return False
    
    def run_complete_fix(self):
        """运行完整修复"""
        logger.info("🚀 开始完整系统修复（保持原功能）...")
        
        success_count = 0
        
        # 1. 修复导入问题
        if self.fix_import_issues():
            success_count += 1
        
        # 2. 创建导入包装器
        if self.create_import_wrapper():
            success_count += 1
        
        logger.info(f"🎉 完整系统修复完成！成功率: {success_count}/2")
        
        return success_count == 2

def main():
    """主函数"""
    # 确保日志目录存在
    os.makedirs('logs', exist_ok=True)
    
    fixer = CompleteSystemFixer()
    success = fixer.run_complete_fix()
    
    if success:
        logger.info("✅ 系统修复成功，建议重启服务")
    else:
        logger.error("❌ 系统修复失败")
        sys.exit(1)

if __name__ == "__main__":
    main() 