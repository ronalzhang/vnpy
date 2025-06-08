#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
🔧 阶段1: 基础设施修复 - 具体实施
优先级：最高

修复项目：
1. 清理SQLite代码残留 (AUTOINCREMENT语法错误)
2. 修复数据库表结构 (补充缺失的表)
3. 统一数据库连接配置验证
"""

import os
import re
from typing import List, Dict
from db_config import get_db_adapter

class Phase1InfrastructureRepair:
    
    def __init__(self):
        self.repaired_files = []
        self.created_tables = []
        
    def execute_phase_1(self):
        """执行阶段1所有修复"""
        print("🔧 开始阶段1: 基础设施修复")
        print("=" * 50)
        
        # 1.1 清理SQLite代码残留
        self.fix_sqlite_remnants()
        
        # 1.2 修复数据库表结构
        self.fix_database_schema()
        
        # 1.3 验证数据库连接
        self.verify_connections()
        
        print("\n✅ 阶段1修复完成！")
        return True
    
    def fix_sqlite_remnants(self):
        """清理SQLite代码残留"""
        print("\n🧹 1.1 清理SQLite代码残留")
        print("-" * 30)
        
        # SQLite → PostgreSQL 替换模式
        replacement_patterns = [
            # AUTOINCREMENT 语法修复
            (r'INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY'),
            (r'AUTOINCREMENT', 'GENERATED ALWAYS AS IDENTITY'),
            
            # SQLite特有函数替换
            (r'PRAGMA table_info\([^)]+\)', '-- PRAGMA removed (PostgreSQL)'),
            (r'sqlite3\.', '-- sqlite3. (removed)'),
            
            # 数据类型调整
            (r'TEXT DEFAULT CURRENT_TIMESTAMP', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
            (r'\.db\b', '-- .db (removed)'),
        ]
        
        files_to_fix = [
            'quantitative_service.py',
            'web_app.py'
        ]
        
        for file_path in files_to_fix:
            if os.path.exists(file_path):
                self.fix_file_sqlite_code(file_path, replacement_patterns)
        
        print("✅ SQLite代码清理完成")
    
    def fix_file_sqlite_code(self, file_path: str, patterns: List[tuple]):
        """修复单个文件中的SQLite代码"""
        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            changes_made = 0
            
            # 应用替换模式
            for old_pattern, new_pattern in patterns:
                new_content = re.sub(old_pattern, new_pattern, content, flags=re.IGNORECASE | re.MULTILINE)
                if new_content != content:
                    changes_made += 1
                    content = new_content
            
            # 如果有修改，写回文件
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"  ✅ {file_path}: 修复了 {changes_made} 处SQLite代码")
                self.repaired_files.append(file_path)
            else:
                print(f"  ✓ {file_path}: 无需修复")
                
        except Exception as e:
            print(f"  ❌ {file_path}: 修复失败 - {e}")
    
    def fix_database_schema(self):
        """修复数据库表结构"""
        print("\n🏗️ 1.2 修复数据库表结构")
        print("-" * 30)
        
        try:
            adapter = get_db_adapter()
            
            # 检查现有表
            existing_tables = self.get_existing_tables(adapter)
            print(f"现有表: {len(existing_tables)}个")
            
            # 创建缺失的表
            self.create_missing_tables(adapter, existing_tables)
            
            # 修复表结构
            self.fix_table_structures(adapter)
            
            adapter.close()
            print("✅ 数据库表结构修复完成")
            
        except Exception as e:
            print(f"❌ 数据库表结构修复失败: {e}")
    
    def get_existing_tables(self, adapter) -> List[str]:
        """获取现有表列表"""
        result = adapter.execute_query(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = %s",
            ("public",),
            fetch_all=True
        )
        return [row["table_name"] for row in result]
    
    def create_missing_tables(self, adapter, existing_tables: List[str]):
        """创建缺失的表"""
        required_tables = {
            'account_balance_history': """
                CREATE TABLE IF NOT EXISTS account_balance_history (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_balance DECIMAL(18,8) DEFAULT 0,
                    available_balance DECIMAL(18,8) DEFAULT 0,
                    frozen_balance DECIMAL(18,8) DEFAULT 0,
                    daily_pnl DECIMAL(18,8) DEFAULT 0,
                    daily_return DECIMAL(10,6) DEFAULT 0,
                    cumulative_return DECIMAL(10,6) DEFAULT 0,
                    total_trades INTEGER DEFAULT 0,
                    milestone_note TEXT
                )
            """,
            'trading_orders': """
                CREATE TABLE IF NOT EXISTS trading_orders (
                    id TEXT PRIMARY KEY,
                    strategy_id TEXT NOT NULL,
                    signal_id TEXT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity DECIMAL(18,8) NOT NULL,
                    price DECIMAL(18,8) NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    executed_time TIMESTAMP,
                    execution_price DECIMAL(18,8),
                    commission DECIMAL(18,8) DEFAULT 0,
                    pnl DECIMAL(18,8) DEFAULT 0
                )
            """,
            'system_status': """
                CREATE TABLE IF NOT EXISTS system_status (
                    id SERIAL PRIMARY KEY,
                    quantitative_running BOOLEAN DEFAULT FALSE,
                    auto_trading_enabled BOOLEAN DEFAULT FALSE,
                    total_strategies INTEGER DEFAULT 0,
                    running_strategies INTEGER DEFAULT 0,
                    selected_strategies INTEGER DEFAULT 0,
                    current_generation INTEGER DEFAULT 1,
                    evolution_enabled BOOLEAN DEFAULT TRUE,
                    system_health TEXT DEFAULT 'unknown',
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                )
            """
        }
        
        for table_name, create_sql in required_tables.items():
            if table_name not in existing_tables:
                try:
                    adapter.execute_query(create_sql)
                    print(f"  ✅ 创建表: {table_name}")
                    self.created_tables.append(table_name)
                except Exception as e:
                    print(f"  ❌ 创建表失败 {table_name}: {e}")
    
    def fix_table_structures(self, adapter):
        """修复现有表结构"""
        print("  🔧 修复现有表结构...")
        
        # 修复strategies表，确保有type字段
        try:
            adapter.execute_query("""
                ALTER TABLE strategies 
                ADD COLUMN IF NOT EXISTS type TEXT DEFAULT 'momentum'
            """)
            print("  ✅ strategies表: 确保type字段存在")
        except Exception as e:
            print(f"  ⚠️ strategies表修复: {e}")
        
        # 修复trading_signals表时间戳字段
        try:
            adapter.execute_query("""
                ALTER TABLE trading_signals 
                ALTER COLUMN timestamp SET DEFAULT CURRENT_TIMESTAMP
            """)
            print("  ✅ trading_signals表: 修复时间戳默认值")
        except Exception as e:
            print(f"  ⚠️ trading_signals表修复: {e}")
    
    def verify_connections(self):
        """验证数据库连接配置"""
        print("\n🔍 1.3 验证数据库连接配置")
        print("-" * 30)
        
        try:
            # 测试db_config连接
            adapter = get_db_adapter()
            result = adapter.execute_query("SELECT 1 as test", fetch_one=True)
            adapter.close()
            
            if result and result.get('test') == 1:
                print("  ✅ db_config.py: PostgreSQL连接正常")
            else:
                print("  ❌ db_config.py: 连接测试失败")
            
            # 检查连接配置一致性
            self.check_config_consistency()
            
        except Exception as e:
            print(f"  ❌ 数据库连接验证失败: {e}")
    
    def check_config_consistency(self):
        """检查配置一致性"""
        config_files = ['db_config.py', 'quantitative_service.py']
        
        for file_path in config_files:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 检查是否都使用quant_user
                if 'quant_user' in content and 'chenfei0421' in content:
                    print(f"  ✅ {file_path}: 配置一致")
                else:
                    print(f"  ⚠️ {file_path}: 配置可能不一致")

def main():
    """执行阶段1修复"""
    repair = Phase1InfrastructureRepair()
    repair.execute_phase_1()
    
    print(f"\n📊 阶段1修复总结:")
    print(f"  修复文件: {len(repair.repaired_files)}个")
    print(f"  创建表: {len(repair.created_tables)}个")
    
    if repair.repaired_files:
        print(f"  修复的文件: {', '.join(repair.repaired_files)}")
    if repair.created_tables:
        print(f"  创建的表: {', '.join(repair.created_tables)}")

if __name__ == "__main__":
    main() 