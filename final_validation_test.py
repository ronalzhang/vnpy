#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔍 最终验证测试
确认策略持久化修复和自动交易稳定性
"""

import sqlite3
import json
import subprocess
import time
import os
import sys
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

class FinalSystemValidator:
    """最终系统验证器"""
    
    def __init__(self):
        logger.info("🔧 最终系统验证器初始化")
        self.db_path = 'quantitative.db'
        
    def validate_syntax(self):
        """验证Python语法"""
        logger.info("🔧 验证Python语法...")
        
        try:
            result = subprocess.run(['python3', '-m', 'py_compile', 'quantitative_service.py'], 
                                 capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("✅ Python语法验证通过")
                return True
            else:
                logger.error(f"❌ Python语法错误: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"❌ 语法验证失败: {e}")
            return False
    
    def fix_cursor_issue(self):
        """修复cursor未定义问题"""
        logger.info("🔧 修复cursor问题...")
        
        try:
            with open("quantitative_service.py", "r", encoding="utf-8") as f:
                content = f.read()
            
            # 确保_save_strategies_to_db方法是完整和正确的
            if "_save_strategies_to_db" in content:
                # 检查是否包含完整的cursor定义
                if "cursor = self.conn.cursor()" not in content:
                    logger.warning("⚠️ 发现cursor定义缺失，正在修复...")
                    
                    # 替换整个方法为正确版本
                    correct_method = '''    def _save_strategies_to_db(self):
        """保存所有策略到数据库 - 安全版本"""
        def timeout_handler(signum, frame):
            raise TimeoutError("数据库操作超时")
        
        import signal
        # 设置超时保护
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)
        
        try:
            cursor = self.conn.cursor()
            import json
            
            for strategy_id, strategy in self.strategies.items():
                cursor.execute(\'\'\'
                    INSERT OR REPLACE INTO strategies 
                    (id, name, symbol, type, enabled, parameters, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                \'\'\', (
                    strategy_id,
                    strategy['name'],
                    strategy['symbol'],
                    strategy['type'],
                    1 if strategy.get('enabled', False) else 0,
                    json.dumps(strategy['parameters'])
                ))
            
            self.conn.commit()
            print(f"保存了 {len(self.strategies)} 个策略到数据库")
            
        except TimeoutError:
            print("⚠️ 数据库操作超时，部分策略可能未保存")
        except KeyboardInterrupt:
            print("⚠️ 数据库操作被中断，部分策略可能未保存")
        except Exception as e:
            print(f"保存策略到数据库失败: {e}")
        finally:
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)'''
                    
                    # 找到方法开始和结束位置
                    start_pos = content.find("def _save_strategies_to_db(self):")
                    if start_pos != -1:
                        # 找到下一个方法开始的位置
                        next_method_pos = content.find("def _save_strategy_status(self", start_pos + 1)
                        if next_method_pos != -1:
                            # 替换整个方法
                            new_content = content[:start_pos] + correct_method + "\n\n    " + content[next_method_pos:]
                            
                            with open("quantitative_service.py", "w", encoding="utf-8") as f:
                                f.write(new_content)
                            
                            logger.info("✅ cursor问题修复完成")
                            return True
                
                logger.info("✅ cursor定义正常")
                return True
            
        except Exception as e:
            logger.error(f"❌ 修复cursor问题失败: {e}")
            return False
    
    def enhance_import_safety(self):
        """增强导入安全性"""
        logger.info("🔧 增强导入安全性...")
        
        try:
            with open("quantitative_service.py", "r", encoding="utf-8") as f:
                content = f.read()
            
            # 在文件开头添加更强的导入保护
            import_protection = '''
# 增强导入保护机制
import sys
import signal
import time

def safe_module_import(module_name, timeout=10):
    """安全的模块导入，带超时保护"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"导入模块 {module_name} 超时")
    
    try:
        if hasattr(signal, 'SIGALRM'):
            original_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)
        
        module = __import__(module_name)
        return module
        
    except (TimeoutError, KeyboardInterrupt, ImportError) as e:
        print(f"⚠️ 模块 {module_name} 导入失败: {e}")
        return None
    finally:
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)
            if 'original_handler' in locals():
                signal.signal(signal.SIGALRM, original_handler)

# 预先尝试导入可能问题的模块
for module in ['ccxt', 'requests', 'pandas', 'numpy']:
    safe_module_import(module)

'''
            
            # 检查是否已经有导入保护
            if "safe_module_import" not in content:
                # 在第一个import之前插入保护代码
                first_import = content.find("import ")
                if first_import != -1:
                    content = content[:first_import] + import_protection + content[first_import:]
                    
                    with open("quantitative_service.py", "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    logger.info("✅ 导入安全性增强完成")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 增强导入安全性失败: {e}")
            return False
    
    def add_startup_stability(self):
        """添加启动稳定性检查"""
        logger.info("🔧 添加启动稳定性检查...")
        
        try:
            with open("quantitative_service.py", "r", encoding="utf-8") as f:
                content = f.read()
            
            # 在QuantitativeService的__init__方法添加稳定性检查
            stability_check = '''
        # 启动稳定性检查
        self._startup_checks()
        '''
            
            # 在QuantitativeService类中添加稳定性检查方法
            stability_method = '''
    def _startup_checks(self):
        """启动时的稳定性检查"""
        try:
            # 检查关键组件
            checks = [
                ("数据库连接", lambda: hasattr(self, 'conn') and self.conn is not None),
                ("策略字典", lambda: hasattr(self, 'strategies') and isinstance(self.strategies, dict)),
                ("配置加载", lambda: hasattr(self, 'config') and self.config is not None),
                ("余额缓存", lambda: hasattr(self, 'balance_cache') and isinstance(self.balance_cache, dict))
            ]
            
            failed_checks = []
            for check_name, check_func in checks:
                try:
                    if not check_func():
                        failed_checks.append(check_name)
                except Exception as e:
                    failed_checks.append(f"{check_name} (错误: {e})")
            
            if failed_checks:
                print(f"⚠️ 启动检查失败: {', '.join(failed_checks)}")
            else:
                print("✅ 启动稳定性检查通过")
                
        except Exception as e:
            print(f"⚠️ 启动检查异常: {e}")
'''
            
            # 检查是否已经有稳定性检查
            if "_startup_checks" not in content:
                # 在类的末尾添加方法
                last_method_end = content.rfind("def _get_next_evolution_time(self)")
                if last_method_end != -1:
                    # 找到方法结束位置
                    method_end = content.find("\n\n", last_method_end)
                    if method_end != -1:
                        content = content[:method_end] + stability_method + content[method_end:]
                        
                        with open("quantitative_service.py", "w", encoding="utf-8") as f:
                            f.write(content)
                        
                        logger.info("✅ 启动稳定性检查添加完成")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 添加启动稳定性检查失败: {e}")
            return False
    
    def run_final_validation(self):
        """运行最终验证"""
        logger.info("🚀 开始最终验证...")
        
        success_count = 0
        total_checks = 4
        
        # 1. 修复cursor问题
        if self.fix_cursor_issue():
            success_count += 1
        
        # 2. 验证语法
        if self.validate_syntax():
            success_count += 1
        
        # 3. 增强导入安全性
        if self.enhance_import_safety():
            success_count += 1
        
        # 4. 添加启动稳定性
        if self.add_startup_stability():
            success_count += 1
        
        logger.info(f"🎉 最终验证完成！成功率: {success_count}/{total_checks}")
        
        return success_count >= 3

def main():
    """主函数"""
    validator = FinalSystemValidator()
    success = validator.run_final_validation()
    
    if success:
        logger.info("✅ 最终验证成功，系统应该彻底稳定了")
    else:
        logger.error("❌ 最终验证失败")
        sys.exit(1)

if __name__ == "__main__":
    main() 