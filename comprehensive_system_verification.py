#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化交易系统 - 全面系统验证脚本
检查所有组件的完整性和兼容性

作者: 系统架构优化团队
日期: 2025年6月8日
"""

import os
import sys
import sqlite3
import importlib
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
import subprocess
import signal
import inspect
import pkgutil
import time
import psycopg2
import requests

# 创建日志目录
os.makedirs('logs', exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/system_verification.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SystemVerification:
    """系统全面验证类"""
    
    def __init__(self):
        """初始化验证器"""
        self.start_time = datetime.now()
        self.results = {
            "timestamp": self.start_time.isoformat(),
            "overall_status": "pending",
            "components": {},
            "database": {},
            "compatibility": {},
            "config": {},
            "issues": [],
            "recommendations": []
        }
        
        # 要检查的核心组件列表
        self.core_components = [
            {
                "name": "市场环境分类器",
                "file": "market_environment_classifier.py",
                "config": "market_classifier_config.json",
                "required": True
            },
            {
                "name": "策略资源分配器",
                "file": "strategy_resource_allocator.py",
                "config": "resource_allocator_config.json",
                "required": True
            },
            {
                "name": "自动交易引擎",
                "file": "auto_trading_engine.py",
                "config": "auto_trading_config.json",
                "required": True
            },
            {
                "name": "稳定性监控",
                "file": "stability_monitor.py",
                "config": "system_monitoring_config.json",
                "required": False
            },
            {
                "name": "参数管理器",
                "file": "strategy_parameters_config.py",
                "config": None,
                "required": True
            }
        ]
        
        # 要检查的数据库表
        self.required_db_tables = [
            "strategies", 
            "strategy_trade_logs", 
            "market_data", 
            "account_balance", 
            "strategy_statistics",
            "strategy_allocations"
        ]
        
        # 要检查的配置文件
        self.config_files = [
            "auto_trading_config.json",
            "market_classifier_config.json",
            "resource_allocator_config.json",
            "system_monitoring_config.json"
        ]
        
        # 要检查的依赖包
        self.required_packages = [
            "numpy", "pandas", "sqlite3", "talib", "psutil", 
            "matplotlib", "scipy", "json", "logging", "datetime"
        ]
        
        logger.info("系统验证初始化完成")
    
    def run_verification(self):
        """运行所有验证检查"""
        try:
            logger.info("开始全面系统验证...")
            
            # 检查依赖包
            self.check_dependencies()
            
            # 检查核心组件
            self.check_core_components()
            
            # 检查数据库
            self.check_database()
            
            # 检查配置文件
            self.check_config_files()
            
            # 检查文件夹结构
            self.check_directory_structure()
            
            # 检查组件兼容性
            self.check_component_compatibility()
            
            # 生成最终报告
            self._generate_final_report()
            
            logger.info("系统验证完成")
            
            # 保存结果
            self.save_results()
            
            # 返回验证结果
            return self.results
            
        except Exception as e:
            logger.error(f"验证过程中出错: {e}")
            logger.error(traceback.format_exc())
            
            self.results["overall_status"] = "failed"
            self.results["issues"].append({
                "component": "verification_system",
                "severity": "critical",
                "message": f"验证过程出错: {str(e)}",
                "details": traceback.format_exc()
            })
            
            # 保存结果
            self.save_results()
            
            return self.results
    
    def check_dependencies(self):
        """检查依赖包"""
        logger.info("检查依赖包...")
        
        dependencies_result = {
            "status": "pass",
            "checked": [],
            "missing": []
        }
        
        for package_name in self.required_packages:
            try:
                if package_name == "talib":
                    # 特殊处理TA-Lib
                    try:
                        import talib
                        dependencies_result["checked"].append(package_name)
                    except ImportError:
                        dependencies_result["missing"].append(package_name)
                        dependencies_result["status"] = "warning"
                else:
                    # 常规包检查
                    importlib.import_module(package_name)
                    dependencies_result["checked"].append(package_name)
            except ImportError:
                dependencies_result["missing"].append(package_name)
                dependencies_result["status"] = "warning"
        
        if dependencies_result["missing"]:
            logger.warning(f"缺少依赖包: {', '.join(dependencies_result['missing'])}")
            self.results["issues"].append({
                "component": "dependencies",
                "severity": "warning",
                "message": f"缺少依赖包: {', '.join(dependencies_result['missing'])}",
                "details": "这些包可能会影响系统的正常运行"
            })
            
            # 添加安装建议
            self.results["recommendations"].append({
                "type": "install_packages",
                "message": f"安装缺失的依赖包: pip install {' '.join(dependencies_result['missing'])}"
            })
        else:
            logger.info("所有依赖包检查通过")
        
        self.results["dependencies"] = dependencies_result
    
    def check_core_components(self):
        """检查核心组件完整性"""
        logger.info("检查核心组件...")
        
        for component in self.core_components:
            component_name = component["name"]
            file_path = component["file"]
            
            result = {
                "status": "pass",
                "file_exists": False,
                "import_status": False,
                "functionalities": []
            }
            
            # 检查文件是否存在
            if os.path.exists(file_path):
                result["file_exists"] = True
                
                # 尝试导入模块
                try:
                    # 获取无扩展名的模块名
                    module_name = file_path.replace(".py", "")
                    
                    # 导入模块
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    result["import_status"] = True
                    
                    # 检查关键功能
                    self._check_module_functionalities(module, component_name, result)
                    
                except Exception as e:
                    logger.error(f"{component_name} 导入失败: {e}")
                    result["status"] = "fail"
                    result["error"] = str(e)
                    
                    self.results["issues"].append({
                        "component": component_name,
                        "severity": "critical" if component["required"] else "warning",
                        "message": f"{component_name} 导入失败",
                        "details": str(e)
                    })
            else:
                logger.warning(f"{component_name} 文件不存在")
                result["status"] = "fail"
                
                self.results["issues"].append({
                    "component": component_name,
                    "severity": "critical" if component["required"] else "warning",
                    "message": f"{component_name} 文件不存在: {file_path}",
                    "details": "该组件是系统正常运行所必需的"
                })
            
            self.results["components"][component_name] = result
            
            # 检查配置文件
            if component["config"]:
                self._check_component_config(component["config"], component_name)
    
    def _check_module_functionalities(self, module, component_name, result):
        """检查模块的关键功能"""
        # 获取模块中的所有类
        classes = inspect.getmembers(module, inspect.isclass)
        
        if not classes:
            logger.warning(f"{component_name} 中没有找到类定义")
            result["functionalities"].append({
                "name": "类定义",
                "status": "warning",
                "message": "未找到类定义"
            })
            return
        
        # 记录找到的类
        for class_name, class_obj in classes:
            if class_name.startswith('_'):
                continue  # 跳过私有类
                
            # 记录类信息
            class_info = {
                "name": class_name,
                "methods": []
            }
            
            # 获取类的方法
            methods = inspect.getmembers(class_obj, inspect.isfunction)
            for method_name, method in methods:
                if method_name.startswith('_') and method_name != '__init__':
                    continue  # 跳过大多数私有方法，但保留__init__
                
                class_info["methods"].append(method_name)
            
            result["functionalities"].append(class_info)
    
    def _check_component_config(self, config_file, component_name):
        """检查组件配置文件"""
        if not os.path.exists(config_file):
            logger.warning(f"{component_name} 的配置文件不存在: {config_file}")
            self.results["issues"].append({
                "component": component_name,
                "severity": "warning",
                "message": f"配置文件不存在: {config_file}",
                "details": "组件可能无法正常工作或使用默认配置"
            })
            
            if component_name not in self.results["config"]:
                self.results["config"][component_name] = {"status": "fail", "file": config_file}
            return
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # 配置文件存在且格式正确
            if component_name not in self.results["config"]:
                self.results["config"][component_name] = {"status": "pass", "file": config_file}
                
            logger.info(f"{component_name} 配置文件正常")
            
        except json.JSONDecodeError as e:
            logger.error(f"{component_name} 配置文件格式错误: {e}")
            self.results["issues"].append({
                "component": component_name,
                "severity": "error",
                "message": f"配置文件格式错误: {config_file}",
                "details": str(e)
            })
            
            if component_name not in self.results["config"]:
                self.results["config"][component_name] = {"status": "fail", "file": config_file, "error": str(e)}
    
    def check_database(self):
        """检查数据库结构"""
        logger.info("检查数据库...")
        
        db_path = "quantitative.db"
        db_result = {
            "status": "pass",
            "exists": False,
            "tables": {},
            "integrity": True
        }
        
        # 检查数据库文件是否存在
        if not os.path.exists(db_path):
            logger.warning(f"数据库文件不存在: {db_path}")
            db_result["status"] = "fail"
            db_result["exists"] = False
            
            self.results["issues"].append({
                "component": "database",
                "severity": "critical",
                "message": f"数据库文件不存在: {db_path}",
                "details": "数据库是系统正常运行所必需的"
            })
            
            self.results["database"] = db_result
            return
        
        db_result["exists"] = True
        
        # 连接数据库并检查表结构
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            # 检查必要的表
            for table_name in self.required_db_tables:
                if table_name in tables:
                    # 获取表结构
                    cursor.execute(f"PRAGMA table_info({table_name});")
                    columns = cursor.fetchall()
                    
                    # 记录表信息
                    db_result["tables"][table_name] = {
                        "exists": True,
                        "columns": len(columns),
                        "status": "pass"
                    }
                else:
                    logger.warning(f"数据库缺少表: {table_name}")
                    db_result["tables"][table_name] = {
                        "exists": False,
                        "status": "fail"
                    }
                    db_result["integrity"] = False
                    
                    self.results["issues"].append({
                        "component": "database",
                        "severity": "error",
                        "message": f"数据库缺少表: {table_name}",
                        "details": "这可能会影响系统的某些功能"
                    })
            
            # 检查表的数据量
            for table_name in tables:
                if table_name in self.required_db_tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                    count = cursor.fetchone()[0]
                    db_result["tables"][table_name]["records"] = count
            
            conn.close()
            
            # 如果完整性检查失败，更新状态
            if not db_result["integrity"]:
                db_result["status"] = "warning"
                
            logger.info(f"数据库检查完成，状态: {db_result['status']}")
            
        except sqlite3.Error as e:
            logger.error(f"数据库检查失败: {e}")
            db_result["status"] = "fail"
            db_result["error"] = str(e)
            
            self.results["issues"].append({
                "component": "database",
                "severity": "critical",
                "message": "数据库检查失败",
                "details": str(e)
            })
        
        self.results["database"] = db_result
    
    def check_config_files(self):
        """检查配置文件完整性"""
        logger.info("检查配置文件...")
        
        config_result = {
            "status": "pass",
            "files": {}
        }
        
        for file_name in self.config_files:
            if os.path.exists(file_name):
                try:
                    with open(file_name, 'r') as f:
                        config = json.load(f)
                    
                    # 文件存在且格式正确
                    config_result["files"][file_name] = {
                        "exists": True,
                        "format": "valid",
                        "status": "pass",
                        "keys": list(config.keys())
                    }
                except json.JSONDecodeError as e:
                    logger.warning(f"配置文件格式错误: {file_name} - {e}")
                    config_result["files"][file_name] = {
                        "exists": True,
                        "format": "invalid",
                        "status": "fail",
                        "error": str(e)
                    }
                    config_result["status"] = "warning"
                    
                    self.results["issues"].append({
                        "component": "config",
                        "severity": "warning",
                        "message": f"配置文件格式错误: {file_name}",
                        "details": str(e)
                    })
            else:
                logger.warning(f"配置文件不存在: {file_name}")
                config_result["files"][file_name] = {
                    "exists": False,
                    "status": "fail"
                }
                config_result["status"] = "warning"
                
                self.results["issues"].append({
                    "component": "config",
                    "severity": "warning",
                    "message": f"配置文件不存在: {file_name}",
                    "details": "系统可能会使用默认配置"
                })
        
        self.results["config_files"] = config_result
    
    def check_directory_structure(self):
        """检查目录结构"""
        logger.info("检查目录结构...")
        
        directory_result = {
            "status": "pass",
            "directories": {}
        }
        
        required_dirs = ['logs', 'data', 'backups']
        
        for dir_name in required_dirs:
            if os.path.exists(dir_name) and os.path.isdir(dir_name):
                directory_result["directories"][dir_name] = {
                    "exists": True,
                    "status": "pass"
                }
            else:
                logger.warning(f"目录不存在: {dir_name}")
                directory_result["directories"][dir_name] = {
                    "exists": False,
                    "status": "warning"
                }
                directory_result["status"] = "warning"
                
                self.results["issues"].append({
                    "component": "directory_structure",
                    "severity": "warning",
                    "message": f"目录不存在: {dir_name}",
                    "details": "将会在运行时自动创建"
                })
        
        self.results["directory_structure"] = directory_result
    
    def check_component_compatibility(self):
        """检查组件间的兼容性"""
        logger.info("检查组件兼容性...")
        
        compatibility_result = {
            "status": "pass",
            "checks": []
        }
        
        # 检查市场环境分类器和资源分配器的兼容性
        if (os.path.exists("market_environment_classifier.py") and 
            os.path.exists("strategy_resource_allocator.py")):
            try:
                # 尝试导入两个模块
                spec1 = importlib.util.spec_from_file_location(
                    "market_classifier", "market_environment_classifier.py")
                classifier_module = importlib.util.module_from_spec(spec1)
                spec1.loader.exec_module(classifier_module)
                
                spec2 = importlib.util.spec_from_file_location(
                    "resource_allocator", "strategy_resource_allocator.py")
                allocator_module = importlib.util.module_from_spec(spec2)
                spec2.loader.exec_module(allocator_module)
                
                # 检查关键函数和类
                classifier_has_get = hasattr(classifier_module, "get_market_classifier")
                allocator_has_get = hasattr(allocator_module, "get_resource_allocator")
                
                if classifier_has_get and allocator_has_get:
                    compatibility_result["checks"].append({
                        "components": ["市场环境分类器", "策略资源分配器"],
                        "status": "pass",
                        "message": "接口兼容性检查通过"
                    })
                else:
                    compatibility_result["checks"].append({
                        "components": ["市场环境分类器", "策略资源分配器"],
                        "status": "warning",
                        "message": "接口可能不兼容",
                        "details": f"缺少必要接口: classifier.get_market_classifier={classifier_has_get}, allocator.get_resource_allocator={allocator_has_get}"
                    })
                    compatibility_result["status"] = "warning"
            except Exception as e:
                logger.warning(f"市场环境分类器和资源分配器兼容性检查失败: {e}")
                compatibility_result["checks"].append({
                    "components": ["市场环境分类器", "策略资源分配器"],
                    "status": "fail",
                    "message": "兼容性检查失败",
                    "details": str(e)
                })
                compatibility_result["status"] = "warning"
        
        # 检查自动交易引擎和其他组件的兼容性
        if os.path.exists("auto_trading_engine.py"):
            try:
                # 导入自动交易引擎
                spec = importlib.util.spec_from_file_location(
                    "trading_engine", "auto_trading_engine.py")
                engine_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(engine_module)
                
                # 检查是否引用了其他组件
                engine_code = open("auto_trading_engine.py", "r").read()
                references_classifier = "market_environment_classifier" in engine_code
                references_allocator = "strategy_resource_allocator" in engine_code
                
                if references_classifier and references_allocator:
                    compatibility_result["checks"].append({
                        "components": ["自动交易引擎", "其他组件"],
                        "status": "pass",
                        "message": "引擎正确引用了其他组件"
                    })
                else:
                    compatibility_result["checks"].append({
                        "components": ["自动交易引擎", "其他组件"],
                        "status": "warning",
                        "message": "引擎可能缺少对其他组件的引用",
                        "details": f"引用检查: classifier={references_classifier}, allocator={references_allocator}"
                    })
                    compatibility_result["status"] = "warning"
                    
                    self.results["issues"].append({
                        "component": "compatibility",
                        "severity": "warning",
                        "message": "自动交易引擎可能缺少对其他组件的引用",
                        "details": f"引用检查: classifier={references_classifier}, allocator={references_allocator}"
                    })
            except Exception as e:
                logger.warning(f"自动交易引擎兼容性检查失败: {e}")
                compatibility_result["checks"].append({
                    "components": ["自动交易引擎"],
                    "status": "fail",
                    "message": "兼容性检查失败",
                    "details": str(e)
                })
                compatibility_result["status"] = "warning"
        
        self.results["compatibility"] = compatibility_result
    
    def _generate_final_report(self):
        """生成最终报告和状态"""
        # 评估总体状态
        critical_issues = 0
        error_issues = 0
        warning_issues = 0
        
        for issue in self.results["issues"]:
            severity = issue["severity"]
            if severity == "critical":
                critical_issues += 1
            elif severity == "error":
                error_issues += 1
            elif severity == "warning":
                warning_issues += 1
        
        # 确定整体状态
        if critical_issues > 0:
            self.results["overall_status"] = "critical"
        elif error_issues > 0:
            self.results["overall_status"] = "error"
        elif warning_issues > 0:
            self.results["overall_status"] = "warning"
        else:
            self.results["overall_status"] = "pass"
        
        # 汇总结果
        self.results["summary"] = {
            "critical_issues": critical_issues,
            "error_issues": error_issues,
            "warning_issues": warning_issues,
            "total_issues": critical_issues + error_issues + warning_issues,
            "duration": (datetime.now() - self.start_time).total_seconds()
        }
        
        # 添加一般性建议
        if len(self.results["recommendations"]) == 0:
            if critical_issues > 0:
                self.results["recommendations"].append({
                    "type": "general",
                    "message": "关键问题需要先解决，否则系统将无法正常运行"
                })
            elif error_issues > 0:
                self.results["recommendations"].append({
                    "type": "general",
                    "message": "存在错误问题，建议在运行系统前解决"
                })
            elif warning_issues > 0:
                self.results["recommendations"].append({
                    "type": "general",
                    "message": "存在警告问题，可以尝试运行系统，但某些功能可能受限"
                })
        
        logger.info(f"验证完成，总体状态: {self.results['overall_status']}")
        logger.info(f"发现 {critical_issues} 个关键问题, {error_issues} 个错误, {warning_issues} 个警告")
    
    def save_results(self):
        """保存验证结果到文件"""
        try:
            # 创建文件名，包含时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"verification_report_{timestamp}.json"
            
            # 确保data目录存在
            os.makedirs("data", exist_ok=True)
            
            # 保存到文件
            with open(f"data/{filename}", 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            
            logger.info(f"验证结果已保存到 data/{filename}")
            
            # 创建一个符号链接到最新的报告
            latest_link = "data/latest_verification_report.json"
            if os.path.exists(latest_link):
                os.remove(latest_link)
                
            os.symlink(f"{filename}", latest_link)
            
        except Exception as e:
            logger.error(f"保存验证结果失败: {e}")
    
    def print_summary(self):
        """打印验证摘要"""
        summary = self.results["summary"]
        status = self.results["overall_status"]
        
        status_emoji = "✅" if status == "pass" else "⚠️" if status == "warning" else "❌"
        
        print("\n" + "="*60)
        print(f"{status_emoji} 系统验证摘要")
        print("="*60)
        print(f"总体状态: {status.upper()}")
        print(f"验证时间: {self.start_time}")
        print(f"用时: {summary['duration']:.2f} 秒")
        print(f"总问题数: {summary['total_issues']}")
        print(f"  - 关键问题: {summary['critical_issues']}")
        print(f"  - 错误: {summary['error_issues']}")
        print(f"  - 警告: {summary['warning_issues']}")
        print("-"*60)
        
        # 打印主要组件状态
        print("主要组件状态:")
        for component_name, result in self.results["components"].items():
            status_str = "✅ OK" if result["status"] == "pass" else "❌ 失败" if result["status"] == "fail" else "⚠️ 警告"
            print(f"  - {component_name}: {status_str}")
        
        # 如果有问题，打印前几个问题
        if self.results["issues"]:
            print("\n重要问题:")
            for i, issue in enumerate(sorted(self.results["issues"], 
                                          key=lambda x: {"critical": 0, "error": 1, "warning": 2}.get(x["severity"], 3)), 1):
                if i > 5:
                    print(f"  ... 还有 {len(self.results['issues']) - 5} 个问题")
                    break
                severity = issue["severity"]
                severity_emoji = "❌" if severity == "critical" else "⚠️" if severity == "error" else "ℹ️"
                print(f"  {i}. {severity_emoji} [{severity.upper()}] {issue['message']}")
        
        # 打印建议
        if self.results["recommendations"]:
            print("\n建议:")
            for i, rec in enumerate(self.results["recommendations"], 1):
                print(f"  {i}. {rec['message']}")
        
        print("\n完整报告已保存到 data/latest_verification_report.json")
        print("="*60)


def main():
    """主函数"""
    print("🔍 开始量化交易系统全面验证...")
    
    # 设置工作目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    try:
        # 创建验证实例
        verifier = SystemVerification()
        
        # 执行验证
        verifier.run_verification()
        
        # 打印摘要
        verifier.print_summary()
        
        # 返回状态码
        if verifier.results["overall_status"] == "critical":
            return 2
        elif verifier.results["overall_status"] in ["error", "warning"]:
            return 1
        else:
            return 0
            
    except Exception as e:
        print(f"验证过程失败: {e}")
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main()) 