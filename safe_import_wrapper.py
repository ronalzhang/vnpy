# -*- coding: utf-8 -*-
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
