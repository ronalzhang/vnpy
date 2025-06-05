#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库升级脚本
修复生产环境数据库表结构问题
"""

import sqlite3
import os
from datetime import datetime

def upgrade_database():
    """升级数据库表结构"""
    db_path = "quantitative.db"
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    print(f"🔧 开始升级数据库: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查并添加缺失的列
        upgrades = [
            {
                'table': 'strategies',
                'column': 'realized_pnl',
                'definition': 'REAL DEFAULT 0.0',
                'description': '已实现盈亏'
            },
            {
                'table': 'strategies', 
                'column': 'unrealized_pnl',
                'definition': 'REAL DEFAULT 0.0',
                'description': '未实现盈亏'
            },
            {
                'table': 'strategies',
                'column': 'generation',
                'definition': 'INTEGER DEFAULT 0',
                'description': '进化世代'
            },
            {
                'table': 'strategies',
                'column': 'evolution_cycle',
                'definition': 'INTEGER DEFAULT 0', 
                'description': '进化轮次'
            },
            {
                'table': 'strategies',
                'column': 'creation_method',
                'definition': 'TEXT DEFAULT "original"',
                'description': '创建方法'
            },
            {
                'table': 'strategies',
                'column': 'parent_ids',
                'definition': 'TEXT DEFAULT ""',
                'description': '父代ID'
            }
        ]
        
        for upgrade in upgrades:
            try:
                # 检查列是否存在
                cursor.execute(f"PRAGMA table_info({upgrade['table']})")
                columns = [column[1] for column in cursor.fetchall()]
                
                if upgrade['column'] not in columns:
                    # 添加缺失的列
                    sql = f"ALTER TABLE {upgrade['table']} ADD COLUMN {upgrade['column']} {upgrade['definition']}"
                    cursor.execute(sql)
                    print(f"  ✅ 添加列: {upgrade['table']}.{upgrade['column']} - {upgrade['description']}")
                else:
                    print(f"  ✓ 列已存在: {upgrade['table']}.{upgrade['column']}")
                    
            except Exception as e:
                print(f"  ❌ 升级列失败: {upgrade['table']}.{upgrade['column']} - {e}")
        
        # 创建增强日志表（如果不存在）
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS enhanced_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    module TEXT NOT NULL,
                    category TEXT NOT NULL,
                    message TEXT NOT NULL,
                    data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("  ✅ 创建/检查 enhanced_logs 表")
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_evolution_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT NOT NULL,
                    generation INTEGER DEFAULT 0,
                    action_type TEXT NOT NULL,
                    old_parameters TEXT,
                    new_parameters TEXT,
                    score_before REAL DEFAULT 0,
                    score_after REAL DEFAULT 0,
                    reason TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("  ✅ 创建/检查 strategy_evolution_logs 表")
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auto_trading_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT NOT NULL,
                    strategy_id TEXT,
                    symbol TEXT,
                    signal_type TEXT,
                    price REAL,
                    quantity REAL,
                    confidence REAL,
                    result TEXT,
                    error_message TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("  ✅ 创建/检查 auto_trading_logs 表")
            
        except Exception as e:
            print(f"  ❌ 创建日志表失败: {e}")
        
        # 创建系统状态表
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    quantitative_running BOOLEAN DEFAULT 0,
                    auto_trading_enabled BOOLEAN DEFAULT 0,
                    evolution_enabled BOOLEAN DEFAULT 0,
                    total_strategies INTEGER DEFAULT 0,
                    current_generation INTEGER DEFAULT 0,
                    system_health TEXT DEFAULT 'unknown',
                    last_update TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("  ✅ 创建/检查 system_status 表")
            
            # 插入初始状态（如果表为空）
            cursor.execute("SELECT COUNT(*) FROM system_status")
            if cursor.fetchone()[0] == 0:
                cursor.execute('''
                    INSERT INTO system_status 
                    (quantitative_running, auto_trading_enabled, evolution_enabled, system_health)
                    VALUES (1, 0, 1, 'good')
                ''')
                print("  ✅ 插入初始系统状态")
                
        except Exception as e:
            print(f"  ❌ 创建系统状态表失败: {e}")
        
        # 提交所有更改
        conn.commit()
        conn.close()
        
        print(f"✅ 数据库升级完成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True
        
    except Exception as e:
        print(f"❌ 数据库升级失败: {e}")
        return False

if __name__ == "__main__":
    success = upgrade_database()
    exit(0 if success else 1) 