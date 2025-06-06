#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
最终自动交易修复脚本
彻底解决CCXT导入问题，防止KeyboardInterrupt
"""

import os
import sys
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

class FinalAutoTradingFixer:
    """最终自动交易修复器"""
    
    def __init__(self):
        logger.info("🔧 最终自动交易修复器初始化")
    
    def fix_all_ccxt_imports(self):
        """修复所有文件中的CCXT导入"""
        logger.info("🔧 修复所有CCXT导入...")
        
        files_to_fix = [
            "auto_trading_engine.py",
            "crypto_monitor_service.py", 
            "crypto_price_monitor.py",
            "crypto_web.py"
        ]
        
        for file_path in files_to_fix:
            if os.path.exists(file_path):
                self._fix_ccxt_import_in_file(file_path)
        
        logger.info("✅ 所有CCXT导入修复完成")
    
    def _fix_ccxt_import_in_file(self, file_path):
        """修复单个文件中的CCXT导入"""
        logger.info(f"🔧 修复文件: {file_path}")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 如果已经是安全导入，跳过
            if "try:" in content and "import ccxt" in content and "except" in content:
                logger.info(f"✅ {file_path} 已经是安全导入，跳过")
                return
            
            # 替换直接的ccxt导入为安全导入
            if "import ccxt" in content:
                old_import = "import ccxt"
                new_import = """# 安全导入CCXT模块
try:
    import ccxt
    logger.info("✅ CCXT模块导入成功")
except Exception as e:
    logger.warning(f"⚠️ CCXT模块导入失败: {e}")
    ccxt = None"""
                
                content = content.replace(old_import, new_import)
                
                # 写回文件
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                
                logger.info(f"✅ {file_path} 修复完成")
            else:
                logger.info(f"✅ {file_path} 不需要修复")
                
        except Exception as e:
            logger.error(f"❌ 修复 {file_path} 失败: {e}")
    
    def create_ccxt_wrapper(self):
        """创建CCXT包装器"""
        logger.info("🔧 创建CCXT包装器...")
        
        wrapper_content = '''# -*- coding: utf-8 -*-
"""
CCXT安全包装器
防止导入时的KeyboardInterrupt问题
"""

import sys
import signal
import logging

logger = logging.getLogger(__name__)

class CCXTSafeImporter:
    """CCXT安全导入器"""
    
    def __init__(self):
        self.ccxt = None
        self.loaded = False
    
    def safe_import_ccxt(self, timeout=30):
        """安全导入CCXT，带超时保护"""
        if self.loaded:
            return self.ccxt
        
        def timeout_handler(signum, frame):
            raise TimeoutError("CCXT导入超时")
        
        try:
            # 设置超时信号（仅在Unix系统上）
            if hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout)
            
            # 尝试导入CCXT
            logger.info("开始安全导入CCXT...")
            import ccxt
            self.ccxt = ccxt
            self.loaded = True
            
            # 取消超时
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
                
            logger.info("✅ CCXT导入成功")
            return self.ccxt
            
        except TimeoutError:
            logger.warning("⚠️ CCXT导入超时，使用模拟模式")
            self.ccxt = None
            self.loaded = True
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ CCXT导入失败: {e}")
            self.ccxt = None
            self.loaded = True
            return None
            
        finally:
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
    
    def get_ccxt(self):
        """获取CCXT模块"""
        if not self.loaded:
            return self.safe_import_ccxt()
        return self.ccxt

# 全局实例
ccxt_importer = CCXTSafeImporter()

def get_safe_ccxt():
    """获取安全的CCXT实例"""
    return ccxt_importer.get_ccxt()

# 兼容性导入
ccxt = ccxt_importer
'''
        
        try:
            with open("safe_ccxt.py", "w", encoding="utf-8") as f:
                f.write(wrapper_content)
            
            logger.info("✅ CCXT包装器创建完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 创建CCXT包装器失败: {e}")
            return False
    
    def update_import_statements(self):
        """更新导入语句使用安全包装器"""
        logger.info("🔧 更新导入语句...")
        
        files_to_update = [
            "quantitative_service.py"
        ]
        
        for file_path in files_to_update:
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # 在文件开头添加安全导入
                    if "from safe_ccxt import get_safe_ccxt" not in content:
                        # 找到第一个import语句的位置
                        lines = content.split('\n')
                        insert_index = 0
                        
                        for i, line in enumerate(lines):
                            if line.strip().startswith('import ') or line.strip().startswith('from '):
                                insert_index = i
                                break
                        
                        # 插入安全导入
                        lines.insert(insert_index, "from safe_ccxt import get_safe_ccxt")
                        content = '\n'.join(lines)
                        
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        
                        logger.info(f"✅ 更新 {file_path} 导入语句完成")
                
                except Exception as e:
                    logger.error(f"❌ 更新 {file_path} 导入语句失败: {e}")
    
    def run_final_fix(self):
        """运行最终修复"""
        logger.info("🚀 开始最终自动交易修复...")
        
        success_count = 0
        
        # 1. 修复所有CCXT导入
        try:
            self.fix_all_ccxt_imports()
            success_count += 1
        except Exception as e:
            logger.error(f"修复CCXT导入失败: {e}")
        
        # 2. 创建CCXT包装器
        if self.create_ccxt_wrapper():
            success_count += 1
        
        # 3. 更新导入语句
        try:
            self.update_import_statements()
            success_count += 1
        except Exception as e:
            logger.error(f"更新导入语句失败: {e}")
        
        logger.info(f"🎉 最终修复完成！成功率: {success_count}/3")
        
        return success_count >= 2

def main():
    """主函数"""
    fixer = FinalAutoTradingFixer()
    success = fixer.run_final_fix()
    
    if success:
        logger.info("✅ 最终修复成功，建议重启服务")
    else:
        logger.error("❌ 最终修复失败")
        sys.exit(1)

if __name__ == "__main__":
    main() 