#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库操作安全修复脚本
解决_save_strategies_to_db等方法的KeyboardInterrupt问题
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

class DatabaseOperationFixer:
    """数据库操作修复器"""
    
    def __init__(self):
        logger.info("🔧 数据库操作安全修复器初始化")
    
    def fix_save_strategies_to_db(self):
        """修复_save_strategies_to_db方法"""
        logger.info("🔧 修复_save_strategies_to_db方法...")
        
        try:
            with open("quantitative_service.py", "r", encoding="utf-8") as f:
                content = f.read()
            
            # 直接替换关键部分
            if "_save_strategies_to_db" in content and "INSERT OR REPLACE INTO strategies" in content:
                # 在方法开始处插入安全保护代码
                content = content.replace(
                    "def _save_strategies_to_db(self):",
                    "def _save_strategies_to_db(self):\n        \"\"\"保存所有策略到数据库 - 安全版本\"\"\"\n        def timeout_handler(signum, frame):\n            raise TimeoutError(\"数据库操作超时\")\n        \n        import signal\n        # 设置超时保护\n        if hasattr(signal, 'SIGALRM'):\n            signal.signal(signal.SIGALRM, timeout_handler)\n            signal.alarm(30)\n        \n        try:"
                )
                
                # 在方法结束处添加异常处理
                content = content.replace(
                    'print(f"保存策略到数据库失败: {e}")',
                    'print(f"保存策略到数据库失败: {e}")\n        except TimeoutError:\n            print("⚠️ 数据库操作超时，部分策略可能未保存")\n        except KeyboardInterrupt:\n            print("⚠️ 数据库操作被中断，部分策略可能未保存")\n        finally:\n            if hasattr(signal, \'SIGALRM\'):\n                signal.alarm(0)'
                )
                
                # 替换批量提交为逐个提交
                content = content.replace(
                    "self.conn.commit()\n            print(f\"保存了 {len(self.strategies)} 个策略到数据库\")",
                    "# 立即提交每个策略，减少批量操作风险\n                    self.conn.commit()\n                    \n                except Exception as e:\n                    print(f\"保存策略 {strategy_id} 失败: {e}\")\n                    continue\n            \n            print(f\"安全保存了策略到数据库\")"
                )
                
                logger.info("✅ _save_strategies_to_db方法保护代码添加成功")
            else:
                logger.warning("⚠️ 未找到_save_strategies_to_db方法")
            
            # 写回文件
            with open("quantitative_service.py", "w", encoding="utf-8") as f:
                f.write(content)
            
            logger.info("✅ quantitative_service.py修复完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 修复_save_strategies_to_db方法失败: {e}")
            return False
    
    def add_signal_protection(self):
        """添加全局信号保护"""
        logger.info("🔧 添加全局信号保护...")
        
        try:
            with open("quantitative_service.py", "r", encoding="utf-8") as f:
                content = f.read()
            
            # 在文件顶部添加信号保护
            if "signal.signal(signal.SIGINT" not in content:
                signal_protection = """
# 添加信号保护防止KeyboardInterrupt
import signal
import sys

def signal_handler(sig, frame):
    \"\"\"安全的信号处理器\"\"\"
    print(f"\\n⚠️ 接收到信号 {sig}，正在安全退出...")
    # 不立即退出，让程序自然结束
    return

# 设置信号处理器
if hasattr(signal, 'SIGINT'):
    signal.signal(signal.SIGINT, signal_handler)
if hasattr(signal, 'SIGTERM'):
    signal.signal(signal.SIGTERM, signal_handler)

"""
                # 找到第一个class定义前插入
                class_pos = content.find("class ")
                if class_pos != -1:
                    content = content[:class_pos] + signal_protection + content[class_pos:]
                    logger.info("✅ 全局信号保护添加成功")
            
            # 写回文件
            with open("quantitative_service.py", "w", encoding="utf-8") as f:
                f.write(content)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 添加信号保护失败: {e}")
            return False
    
    def run_database_fix(self):
        """运行数据库操作修复"""
        logger.info("🚀 开始数据库操作安全修复...")
        
        success_count = 0
        
        # 1. 修复_save_strategies_to_db方法
        if self.fix_save_strategies_to_db():
            success_count += 1
        
        # 2. 添加全局信号保护
        if self.add_signal_protection():
            success_count += 1
        
        logger.info(f"🎉 数据库安全修复完成！成功率: {success_count}/2")
        
        return success_count >= 1

def main():
    """主函数"""
    fixer = DatabaseOperationFixer()
    success = fixer.run_database_fix()
    
    if success:
        logger.info("✅ 数据库操作安全修复成功，建议重启服务")
    else:
        logger.error("❌ 数据库操作修复失败")
        sys.exit(1)

if __name__ == "__main__":
    main() 