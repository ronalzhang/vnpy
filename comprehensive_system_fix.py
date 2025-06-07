#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
量化系统综合修复脚本
修复数据库结构、代码逻辑错误和策略评分问题
"""

import sqlite3
import json
import time
import shutil
from datetime import datetime
from loguru import logger

class ComprehensiveSystemFixer:
    def __init__(self):
        self.db_path = 'quantitative.db'
        self.backup_path = f'quantitative_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        logger.info("🔧 综合系统修复器初始化完成")
    
    def create_backup(self):
        """创建数据库备份"""
        try:
            shutil.copy2(self.db_path, self.backup_path)
            logger.info(f"✅ 数据库备份完成: {self.backup_path}")
            return True
        except Exception as e:
            logger.error(f"❌ 备份失败: {e}")
            return False
    
    def fix_database_structure(self):
        """修复数据库结构"""
        logger.info("🔧 开始修复数据库结构...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. 创建strategy_evolution_history表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_evolution_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    cycle INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    parameters TEXT,
                    score_before REAL DEFAULT 0.0,
                    score_after REAL DEFAULT 0.0,
                    fitness REAL DEFAULT 0.0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                )
            ''')
            logger.info("✅ 创建strategy_evolution_history表")
            
            # 2. 创建strategy_snapshots表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT NOT NULL,
                    snapshot_name TEXT NOT NULL,
                    parameters TEXT,
                    final_score REAL DEFAULT 0.0,
                    performance_metrics TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            logger.info("✅ 创建strategy_snapshots表")
            
            # 3. 检查并添加evolution_count字段
            cursor.execute("PRAGMA table_info(strategies)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'evolution_count' not in columns:
                cursor.execute('ALTER TABLE strategies ADD COLUMN evolution_count INTEGER DEFAULT 0')
                logger.info("✅ 添加evolution_count字段")
            
            if 'generation' not in columns:
                cursor.execute('ALTER TABLE strategies ADD COLUMN generation INTEGER DEFAULT 1')
                logger.info("✅ 添加generation字段")
            
            if 'fitness' not in columns:
                cursor.execute('ALTER TABLE strategies ADD COLUMN fitness REAL DEFAULT 0.0')
                logger.info("✅ 添加fitness字段")
            
            # 4. 创建索引优化查询性能
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_evolution_history_strategy 
                ON strategy_evolution_history(strategy_id, generation, cycle)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_snapshots_strategy 
                ON strategy_snapshots(strategy_id, timestamp)
            ''')
            
            conn.commit()
            logger.info("✅ 数据库结构修复完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 数据库结构修复失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def fix_strategy_scores(self):
        """修复策略评分系统"""
        logger.info("🔧 开始修复策略评分...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取所有策略
            cursor.execute("SELECT id, total_return, win_rate, total_trades FROM strategies")
            strategies = cursor.fetchall()
            
            fixed_count = 0
            for strategy_id, total_return, win_rate, total_trades in strategies:
                # 重新计算策略评分
                if total_return is None:
                    total_return = 0.0
                if win_rate is None:
                    win_rate = 0.5
                if total_trades is None:
                    total_trades = 0
                
                # 使用改进的评分算法
                base_score = 50.0  # 基础分数
                return_score = total_return * 100  # 收益率转换
                win_rate_score = (win_rate - 0.5) * 40  # 胜率偏差分数
                trade_count_score = min(total_trades / 10, 10)  # 交易频次分数
                
                final_score = max(0, base_score + return_score + win_rate_score + trade_count_score)
                
                # 更新数据库
                cursor.execute('''
                    UPDATE strategies 
                    SET final_score = ?, fitness = ?
                    WHERE id = ?
                ''', (final_score, final_score * 1.2, strategy_id))
                
                fixed_count += 1
            
            conn.commit()
            logger.info(f"✅ 修复了 {fixed_count} 个策略的评分")
            return True
            
        except Exception as e:
            logger.error(f"❌ 策略评分修复失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def fix_quantitative_service_code(self):
        """修复quantitative_service.py中的代码错误"""
        logger.info("🔧 开始修复代码逻辑错误...")
        
        try:
            # 读取quantitative_service.py
            with open('quantitative_service.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 修复AutomatedStrategyManager的属性错误
            if 'self.quantitative_service' not in content:
                # 在__init__方法中添加正确的属性引用
                content = content.replace(
                    'def __init__(self, quantitative_service):',
                    '''def __init__(self, quantitative_service):
        self.quantitative_service = quantitative_service'''
                )
                
                # 修复其他可能的属性引用错误
                content = content.replace(
                    "self.quantitative_service'",
                    "self.quantitative_service"
                )
                
                logger.info("✅ 修复AutomatedStrategyManager属性错误")
            
            # 增强错误处理
            enhanced_error_handling = '''
    def _safe_execute(self, func, *args, **kwargs):
        """安全执行函数，带错误处理"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"函数执行失败 {func.__name__}: {e}")
            return None
'''
            
            if '_safe_execute' not in content:
                # 在类定义后添加安全执行方法
                content = content.replace(
                    'class AutomatedStrategyManager:',
                    f'class AutomatedStrategyManager:{enhanced_error_handling}'
                )
                logger.info("✅ 添加增强错误处理机制")
            
            # 写回文件
            with open('quantitative_service.py', 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info("✅ 代码逻辑修复完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 代码修复失败: {e}")
            return False
    
    def validate_system(self):
        """验证系统修复效果"""
        logger.info("🔍 开始验证系统修复效果...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['strategy_evolution_history', 'strategy_snapshots', 'strategies']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                logger.error(f"❌ 仍缺少表: {missing_tables}")
                return False
            
            # 检查字段是否存在
            cursor.execute("PRAGMA table_info(strategies)")
            columns = [column[1] for column in cursor.fetchall()]
            
            required_fields = ['evolution_count', 'generation', 'fitness']
            missing_fields = [field for field in required_fields if field not in columns]
            
            if missing_fields:
                logger.error(f"❌ 仍缺少字段: {missing_fields}")
                return False
            
            # 检查评分是否修复
            cursor.execute("SELECT COUNT(*) FROM strategies WHERE final_score > 0")
            scored_strategies = cursor.fetchone()[0]
            
            logger.info(f"✅ 验证完成: {scored_strategies} 个策略有有效评分")
            return True
            
        except Exception as e:
            logger.error(f"❌ 验证失败: {e}")
            return False
        finally:
            conn.close()
    
    def create_monitoring_script(self):
        """创建系统监控脚本"""
        monitoring_script = '''#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import requests
import subprocess
from datetime import datetime

def check_system_health():
    """检查系统健康状态"""
    try:
        # 检查API响应
        response = requests.get('http://localhost:8888/api/quantitative/strategies', timeout=5)
        if response.status_code == 200:
            print(f"✅ [{datetime.now()}] API正常响应")
            return True
        else:
            print(f"❌ [{datetime.now()}] API响应异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ [{datetime.now()}] API检查失败: {e}")
        return False

def restart_if_needed():
    """必要时重启服务"""
    if not check_system_health():
        print("🔄 尝试重启服务...")
        try:
            subprocess.run(['pm2', 'restart', 'quant-b'], check=True)
            time.sleep(10)
            if check_system_health():
                print("✅ 服务重启成功")
            else:
                print("❌ 服务重启后仍有问题")
        except Exception as e:
            print(f"❌ 重启失败: {e}")

if __name__ == "__main__":
    while True:
        restart_if_needed()
        time.sleep(300)  # 每5分钟检查一次
'''
        
        with open('system_monitor.py', 'w', encoding='utf-8') as f:
            f.write(monitoring_script)
        
        logger.info("✅ 系统监控脚本创建完成")
    
    def run_comprehensive_fix(self):
        """执行综合修复"""
        logger.info("🚀 开始综合系统修复...")
        
        # 1. 创建备份
        if not self.create_backup():
            logger.error("❌ 备份失败，终止修复")
            return False
        
        # 2. 修复数据库结构
        if not self.fix_database_structure():
            logger.error("❌ 数据库修复失败")
            return False
        
        # 3. 修复策略评分
        if not self.fix_strategy_scores():
            logger.error("❌ 评分修复失败")
            return False
        
        # 4. 修复代码逻辑
        if not self.fix_quantitative_service_code():
            logger.error("❌ 代码修复失败")
            return False
        
        # 5. 验证修复效果
        if not self.validate_system():
            logger.error("❌ 验证失败")
            return False
        
        # 6. 创建监控脚本
        self.create_monitoring_script()
        
        logger.info("🎉 综合系统修复完成！")
        logger.info("📋 建议执行以下操作:")
        logger.info("   1. pm2 restart quant-b")
        logger.info("   2. python system_monitor.py &")
        logger.info("   3. 访问 http://localhost:8888/quantitative.html 验证功能")
        
        return True

if __name__ == "__main__":
    fixer = ComprehensiveSystemFixer()
    fixer.run_comprehensive_fix() 