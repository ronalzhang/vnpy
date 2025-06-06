#!/usr/bin/env python3
"""服务器数据库修复脚本"""
import sqlite3

print('🔧 在服务器上创建缺失的数据库表...')
conn = sqlite3.connect('quantitative.db')
cursor = conn.cursor()

# 创建 strategy_evolution_history 表
cursor.execute('''
    CREATE TABLE IF NOT EXISTS strategy_evolution_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_id TEXT NOT NULL,
        generation INTEGER DEFAULT 1,
        cycle INTEGER DEFAULT 1,
        evolution_type TEXT,
        old_score REAL DEFAULT 0.0,
        new_score REAL DEFAULT 0.0,
        old_parameters TEXT,
        new_parameters TEXT,
        fitness_improvement REAL DEFAULT 0.0,
        created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (strategy_id) REFERENCES strategies(id)
    )
''')

# 创建 strategy_snapshots 表
cursor.execute('''
    CREATE TABLE IF NOT EXISTS strategy_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_id TEXT,
        snapshot_name TEXT UNIQUE NOT NULL,
        snapshot_type TEXT DEFAULT 'evolution',
        generation INTEGER DEFAULT 1,
        parameters TEXT,
        final_score REAL DEFAULT 0.0,
        performance_metrics TEXT,
        snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# 添加缺失的列
try:
    cursor.execute('ALTER TABLE strategies ADD COLUMN evolution_count INTEGER DEFAULT 0')
    print('✅ 添加 evolution_count 列')
except Exception as e:
    print(f'evolution_count 列已存在: {e}')

try:
    cursor.execute('ALTER TABLE strategies ADD COLUMN protected_status INTEGER DEFAULT 0')
    print('✅ 添加 protected_status 列')
except Exception as e:
    print(f'protected_status 列已存在: {e}')

conn.commit()
conn.close()
print('✅ 数据库表创建完成！演化引擎现在可以完美运行了！') 