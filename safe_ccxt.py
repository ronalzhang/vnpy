# -*- coding: utf-8 -*-
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
