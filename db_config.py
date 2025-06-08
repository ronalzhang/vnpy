#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库配置和适配器
仅支持PostgreSQL
"""

import os
import psycopg2
import psycopg2.extras
from typing import Union, Dict, Any, List, Tuple

# 数据库配置
DATABASE_CONFIG = {
    'type': 'postgresql',  # 仅支持PostgreSQL
    'postgresql': {
        'host': 'localhost',
        'port': 5432,
        'database': 'quantitative',
        'user': 'quant_user',
        'password': 'chenfei0421'
    },

}

class DatabaseAdapter:
    """数据库适配器，专门用于PostgreSQL"""
    
    def __init__(self, config: Dict = None):
        self.config = config or DATABASE_CONFIG
        self.db_type = 'postgresql'  # 仅支持PostgreSQL
        self.connection = None
        self.connect()
    
    def connect(self):
        """建立PostgreSQL数据库连接"""
        try:
            pg_config = self.config['postgresql']
            self.connection = psycopg2.connect(
                host=pg_config['host'],
                port=pg_config['port'],
                database=pg_config['database'],
                user=pg_config['user'],
                password=pg_config['password'],
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            self.connection.autocommit = True
            print(f"✅ 已连接到PostgreSQL数据库: {pg_config['database']}")
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            raise
    
    def execute_query(self, query: str, params: tuple = (), fetch_one: bool = False, 
                     fetch_all: bool = False) -> Union[Dict, List[Dict], None]:
        """执行PostgreSQL查询"""
        try:
            cursor = self.connection.cursor()
            
            # PostgreSQL使用%s占位符
            query = query.replace('?', '%s')
            
            cursor.execute(query, params)
            
            if fetch_one:
                result = cursor.fetchone()
                return dict(result) if result else None
            elif fetch_all:
                results = cursor.fetchall()
                return [dict(row) for row in results] if results else []
            else:
                self.connection.commit()
                return None
        except Exception as e:
            print(f"❌ 查询执行失败: {e}")
            print(f"Query: {query}")
            print(f"Params: {params}")
            self.connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
    
    def get_schema_sql(self, table_name: str) -> str:
        """获取PostgreSQL建表SQL"""
        schemas = {
            'strategies': """
                CREATE TABLE IF NOT EXISTS strategies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    type TEXT NOT NULL,
                    enabled INTEGER DEFAULT 0,
                    parameters TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    generation INTEGER DEFAULT 1,
                    cycle INTEGER DEFAULT 1,
                    parent_id TEXT,
                    parent1_id TEXT,
                    parent2_id TEXT,
                    creation_method TEXT DEFAULT 'manual',
                    protected_status INTEGER DEFAULT 0,
                    is_persistent INTEGER DEFAULT 1,
                    final_score REAL DEFAULT 50.0,
                    win_rate REAL DEFAULT 0,
                    total_return REAL DEFAULT 0,
                    total_trades INTEGER DEFAULT 0,
                    simulation_score REAL DEFAULT 0,
                    qualified_for_trading INTEGER DEFAULT 0,
                    simulation_date TEXT,
                    allocation_ratio REAL DEFAULT 0,
                    last_evolution_time TEXT,
                    age_days INTEGER DEFAULT 0,
                    fitness_score REAL DEFAULT 50.0,
                    parent_strategy_id TEXT,
                    mutation_count INTEGER DEFAULT 0,
                    is_protected INTEGER DEFAULT 0,
                    fitness REAL DEFAULT 0.0
                )
            """
        }
        
        return schemas.get(table_name, '')
    
    def init_tables(self):
        """初始化所有表"""
        tables = ['strategies']  # 可以扩展更多表
        
        for table in tables:
            schema_sql = self.get_schema_sql(table)
            if schema_sql:
                self.execute_query(schema_sql)
                print(f"✅ 表 {table} 初始化完成")
    

    

    
    def close(self):
        """关闭连接"""
        if self.connection:
            self.connection.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

# 全局数据库实例
db_adapter = None

def get_db_adapter() -> DatabaseAdapter:
    """获取数据库适配器实例"""
    global db_adapter
    if db_adapter is None:
        db_adapter = DatabaseAdapter()
    return db_adapter

def switch_database(db_type: str):
    """切换数据库类型"""
    global db_adapter
    if db_adapter:
        db_adapter.close()
    
    config = DATABASE_CONFIG.copy()
    config['type'] = db_type
    db_adapter = DatabaseAdapter(config)
    return db_adapter 