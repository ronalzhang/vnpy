#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统重启问题修复脚本
彻底解决应用不停重启的问题
"""

import os
import sys
import json
import sqlite3
import logging
import traceback
from datetime import datetime, timedelta
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/system_restart_fix.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SystemRestartFixer:
    """系统重启问题修复器"""
    
    def __init__(self):
        self.db_path = "quantitative.db"
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        logger.info("🔧 系统重启问题修复器初始化完成")
    
    def diagnose_issues(self):
        """诊断系统问题"""
        logger.info("🔍 开始诊断系统问题...")
        
        issues = []
        
        # 1. 检查数据库完整性
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查strategies表
            cursor.execute("SELECT COUNT(*) FROM strategies")
            strategy_count = cursor.fetchone()[0]
            logger.info(f"📊 发现 {strategy_count} 个策略")
            
            # 检查是否有type字段
            cursor.execute("PRAGMA table_info(strategies)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'type' not in columns:
                issues.append("数据库缺少type字段")
                logger.warning("⚠️ strategies表缺少type字段")
            
            if 'strategy_type' not in columns:
                issues.append("数据库缺少strategy_type字段")
                logger.warning("⚠️ strategies表缺少strategy_type字段")
            
            conn.close()
            
        except Exception as e:
            issues.append(f"数据库连接失败: {e}")
            logger.error(f"❌ 数据库诊断失败: {e}")
        
        # 2. 检查关键文件
        critical_files = [
            "enhanced_strategy_evolution.py",
            "quantitative_service.py",
            "auto_trading_engine.py"
        ]
        
        for file_path in critical_files:
            if not os.path.exists(file_path):
                issues.append(f"关键文件缺失: {file_path}")
                logger.warning(f"⚠️ 关键文件缺失: {file_path}")
        
        # 3. 检查配置文件
        config_files = ["crypto_config.json", "api_keys.json"]
        for config_file in config_files:
            if not os.path.exists(config_file):
                logger.warning(f"⚠️ 配置文件缺失: {config_file}")
        
        return issues
    
    def create_backup(self):
        """创建系统备份"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"system_backup_{timestamp}.db"
            
            # 备份数据库
            if os.path.exists(self.db_path):
                os.system(f"cp {self.db_path} {backup_path}")
                logger.info(f"✅ 数据库备份完成: {backup_path}")
            
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"❌ 备份失败: {e}")
            return None
    
    def fix_database_schema(self):
        """修复数据库结构"""
        logger.info("🔧 开始修复数据库结构...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查并添加缺失字段
            cursor.execute("PRAGMA table_info(strategies)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # 添加type字段
            if 'type' not in columns:
                cursor.execute("ALTER TABLE strategies ADD COLUMN type TEXT DEFAULT 'momentum'")
                logger.info("✅ 添加type字段")
            
            # 添加strategy_type字段
            if 'strategy_type' not in columns:
                cursor.execute("ALTER TABLE strategies ADD COLUMN strategy_type TEXT DEFAULT 'momentum'")
                logger.info("✅ 添加strategy_type字段")
            
            # 更新现有记录
            cursor.execute("""
                UPDATE strategies 
                SET type = COALESCE(type, 'momentum'),
                    strategy_type = COALESCE(strategy_type, 'momentum')
                WHERE type IS NULL OR strategy_type IS NULL
            """)
            
            # 确保所有策略都有有效的类型
            cursor.execute("""
                UPDATE strategies 
                SET type = CASE 
                    WHEN name LIKE '%动量%' OR name LIKE '%momentum%' THEN 'momentum'
                    WHEN name LIKE '%均值%' OR name LIKE '%mean%' THEN 'mean_reversion'
                    WHEN name LIKE '%突破%' OR name LIKE '%breakout%' THEN 'breakout'
                    WHEN name LIKE '%网格%' OR name LIKE '%grid%' THEN 'grid_trading'
                    WHEN name LIKE '%高频%' OR name LIKE '%hf%' THEN 'high_frequency'
                    ELSE 'momentum'
                END,
                strategy_type = CASE 
                    WHEN name LIKE '%动量%' OR name LIKE '%momentum%' THEN 'momentum'
                    WHEN name LIKE '%均值%' OR name LIKE '%mean%' THEN 'mean_reversion'
                    WHEN name LIKE '%突破%' OR name LIKE '%breakout%' THEN 'breakout'
                    WHEN name LIKE '%网格%' OR name LIKE '%grid%' THEN 'grid_trading'
                    WHEN name LIKE '%高频%' OR name LIKE '%hf%' THEN 'high_frequency'
                    ELSE 'momentum'
                END
            """)
            
            conn.commit()
            conn.close()
            
            logger.info("✅ 数据库结构修复完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 数据库结构修复失败: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def fix_evolution_system(self):
        """修复进化系统"""
        logger.info("🔧 开始修复进化系统...")
        
        try:
            # 修复enhanced_strategy_evolution.py中的多样性指数计算
            with open("enhanced_strategy_evolution.py", "r", encoding="utf-8") as f:
                content = f.read()
            
            # 查找并修复_calculate_diversity_index方法
            old_code = '''    def _calculate_diversity_index(self, population_fitness: Dict) -> float:
        """计算种群多样性指数"""
        try:
            if len(population_fitness) < 2:
                return 0.0
            
            # 基于策略类型的多样性
            strategy_types = {}
            for p in population_fitness.values():
                strategy_type = p['strategy']['type']
                strategy_types[strategy_type] = strategy_types.get(strategy_type, 0) + 1'''
            
            new_code = '''    def _calculate_diversity_index(self, population_fitness: Dict) -> float:
        """计算种群多样性指数"""
        try:
            if len(population_fitness) < 2:
                return 0.0
            
            # 基于策略类型的多样性
            strategy_types = {}
            for p in population_fitness.values():
                # 安全获取策略类型
                strategy = p.get('strategy', {})
                strategy_type = strategy.get('type') or strategy.get('strategy_type', 'momentum')
                strategy_types[strategy_type] = strategy_types.get(strategy_type, 0) + 1'''
            
            if old_code in content:
                content = content.replace(old_code, new_code)
                
                with open("enhanced_strategy_evolution.py", "w", encoding="utf-8") as f:
                    f.write(content)
                
                logger.info("✅ 修复进化系统多样性指数计算")
            else:
                logger.warning("⚠️ 未找到需要修复的多样性指数代码")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 进化系统修复失败: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def fix_error_handling(self):
        """修复错误处理"""
        logger.info("🔧 开始修复错误处理...")
        
        try:
            # 检查并修复quantitative_service.py中的错误处理
            files_to_fix = [
                "quantitative_service.py",
                "auto_trading_engine.py",
                "enhanced_strategy_evolution.py"
            ]
            
            for file_path in files_to_fix:
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # 添加更好的异常处理
                    modifications = [
                        # 替换bare except语句
                        ("except:", "except Exception as e:"),
                        # 添加异常日志
                        ("pass  # 忽略错误", "logger.error(f'操作失败: {e}')"),
                    ]
                    
                    for old, new in modifications:
                        if old in content:
                            content = content.replace(old, new)
                    
                    # 写回文件
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    logger.info(f"✅ 修复错误处理: {file_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 错误处理修复失败: {e}")
            return False
    
    def create_stability_monitor(self):
        """创建稳定性监控脚本"""
        logger.info("🔧 创建稳定性监控脚本...")
        
        monitor_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统稳定性监控脚本
"""

import psutil
import time
import logging
import subprocess
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/stability_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class StabilityMonitor:
    def __init__(self):
        self.process_names = ['python', 'quantitative']
        self.restart_count = 0
        self.max_restarts = 5
        
    def check_processes(self):
        """检查关键进程"""
        running_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if any(name in ' '.join(proc.info['cmdline'] or []) for name in self.process_names):
                    running_processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return running_processes
    
    def monitor_system(self):
        """监控系统状态"""
        logger.info("🔍 开始系统稳定性监控...")
        
        while True:
            try:
                # 检查内存使用
                memory = psutil.virtual_memory()
                if memory.percent > 90:
                    logger.warning(f"⚠️ 内存使用率过高: {memory.percent}%")
                
                # 检查CPU使用
                cpu_percent = psutil.cpu_percent(interval=1)
                if cpu_percent > 90:
                    logger.warning(f"⚠️ CPU使用率过高: {cpu_percent}%")
                
                # 检查磁盘空间
                disk = psutil.disk_usage('/')
                if disk.percent > 90:
                    logger.warning(f"⚠️ 磁盘使用率过高: {disk.percent}%")
                
                # 检查关键进程
                processes = self.check_processes()
                if not processes:
                    logger.warning("⚠️ 未检测到关键进程运行")
                
                time.sleep(30)  # 每30秒检查一次
                
            except KeyboardInterrupt:
                logger.info("👋 监控停止")
                break
            except Exception as e:
                logger.error(f"❌ 监控出错: {e}")
                time.sleep(10)

if __name__ == "__main__":
    monitor = StabilityMonitor()
    monitor.monitor_system()
'''
        
        try:
            with open("stability_monitor.py", "w", encoding="utf-8") as f:
                f.write(monitor_script)
            
            os.chmod("stability_monitor.py", 0o755)
            logger.info("✅ 稳定性监控脚本创建完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 稳定性监控脚本创建失败: {e}")
            return False
    
    def create_safe_startup_script(self):
        """创建安全启动脚本"""
        logger.info("🔧 创建安全启动脚本...")
        
        startup_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全启动脚本
确保系统稳定启动
"""

import os
import sys
import time
import logging
import subprocess
import signal
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/safe_startup.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SafeStartup:
    def __init__(self):
        self.processes = []
        self.running = True
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}，开始优雅关闭...")
        self.running = False
        self.cleanup()
    
    def pre_startup_check(self):
        """启动前检查"""
        logger.info("🔍 进行启动前检查...")
        
        # 检查数据库
        if not os.path.exists("quantitative.db"):
            logger.error("❌ 数据库文件不存在")
            return False
        
        # 检查日志目录
        Path("logs").mkdir(exist_ok=True)
        
        # 检查关键文件
        critical_files = [
            "quantitative_service.py",
            "enhanced_strategy_evolution.py"
        ]
        
        for file_path in critical_files:
            if not os.path.exists(file_path):
                logger.error(f"❌ 关键文件缺失: {file_path}")
                return False
        
        logger.info("✅ 启动前检查通过")
        return True
    
    def start_services(self):
        """启动服务"""
        if not self.pre_startup_check():
            logger.error("❌ 启动前检查失败，终止启动")
            return False
        
        logger.info("🚀 开始启动服务...")
        
        try:
            # 启动量化服务
            proc = subprocess.Popen([
                sys.executable, "quantitative_service.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.processes.append(proc)
            logger.info("✅ 量化服务启动成功")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 服务启动失败: {e}")
            return False
    
    def monitor_services(self):
        """监控服务状态"""
        logger.info("🔍 开始监控服务状态...")
        
        restart_count = 0
        max_restarts = 3
        
        while self.running:
            try:
                # 检查进程状态
                active_processes = []
                for proc in self.processes:
                    if proc.poll() is None:  # 进程仍在运行
                        active_processes.append(proc)
                    else:
                        logger.warning(f"⚠️ 进程已退出: PID {proc.pid}")
                        
                        # 重启服务
                        if restart_count < max_restarts:
                            logger.info("🔄 尝试重启服务...")
                            if self.start_services():
                                restart_count += 1
                                logger.info(f"✅ 服务重启成功 ({restart_count}/{max_restarts})")
                            else:
                                logger.error("❌ 服务重启失败")
                        else:
                            logger.error("❌ 达到最大重启次数，停止监控")
                            self.running = False
                
                self.processes = active_processes
                time.sleep(10)  # 每10秒检查一次
                
            except KeyboardInterrupt:
                logger.info("👋 监控停止")
                self.running = False
            except Exception as e:
                logger.error(f"❌ 监控出错: {e}")
                time.sleep(5)
    
    def cleanup(self):
        """清理资源"""
        logger.info("🧹 开始清理资源...")
        
        for proc in self.processes:
            try:
                proc.terminate()
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
            except Exception as e:
                logger.error(f"清理进程失败: {e}")
        
        logger.info("✅ 资源清理完成")
    
    def run(self):
        """运行安全启动器"""
        try:
            if self.start_services():
                self.monitor_services()
            else:
                logger.error("❌ 初始启动失败")
        finally:
            self.cleanup()

if __name__ == "__main__":
    startup = SafeStartup()
    startup.run()
'''
        
        try:
            with open("safe_startup.py", "w", encoding="utf-8") as f:
                f.write(startup_script)
            
            os.chmod("safe_startup.py", 0o755)
            logger.info("✅ 安全启动脚本创建完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 安全启动脚本创建失败: {e}")
            return False
    
    def run_comprehensive_fix(self):
        """运行全面修复"""
        logger.info("🔧 开始全面修复系统重启问题...")
        
        # 1. 诊断问题
        issues = self.diagnose_issues()
        if issues:
            logger.warning(f"⚠️ 发现 {len(issues)} 个问题:")
            for issue in issues:
                logger.warning(f"  - {issue}")
        
        # 2. 创建备份
        backup_path = self.create_backup()
        if backup_path:
            logger.info(f"✅ 备份创建完成: {backup_path}")
        
        # 3. 修复数据库结构
        if self.fix_database_schema():
            logger.info("✅ 数据库结构修复完成")
        
        # 4. 修复进化系统
        if self.fix_evolution_system():
            logger.info("✅ 进化系统修复完成")
        
        # 5. 修复错误处理
        if self.fix_error_handling():
            logger.info("✅ 错误处理修复完成")
        
        # 6. 创建监控脚本
        if self.create_stability_monitor():
            logger.info("✅ 稳定性监控脚本创建完成")
        
        # 7. 创建安全启动脚本
        if self.create_safe_startup_script():
            logger.info("✅ 安全启动脚本创建完成")
        
        logger.info("🎉 全面修复完成！")
        
        # 生成修复报告
        self.generate_fix_report(issues)
    
    def generate_fix_report(self, original_issues):
        """生成修复报告"""
        report = {
            "修复时间": datetime.now().isoformat(),
            "原始问题": original_issues,
            "修复操作": [
                "修复数据库结构，添加缺失字段",
                "修复进化系统多样性指数计算错误",
                "改进错误处理机制",
                "创建系统稳定性监控",
                "创建安全启动脚本"
            ],
            "新增文件": [
                "stability_monitor.py - 系统稳定性监控",
                "safe_startup.py - 安全启动脚本",
                "fix_restart_issues.py - 修复脚本"
            ],
            "建议": [
                "使用 python safe_startup.py 启动系统",
                "定期运行 python stability_monitor.py 监控系统",
                "保持数据库定期备份",
                "监控系统日志文件"
            ]
        }
        
        with open("restart_fix_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info("📋 修复报告已生成: restart_fix_report.json")

def main():
    """主函数"""
    fixer = SystemRestartFixer()
    fixer.run_comprehensive_fix()

if __name__ == "__main__":
    main() 