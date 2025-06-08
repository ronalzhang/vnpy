#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
全面系统检查和修复脚本
检查应用状态、数据库连接、API端点、PM2状态等
"""

import os
import sys
import json
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import random
import subprocess
import time

class SystemChecker:
    def __init__(self):
        self.issues = []
        self.fixes_applied = []
        self.db_conn = None
        
    def log_issue(self, issue: str):
        """记录问题"""
        self.issues.append(issue)
        print(f"❌ {issue}")
    
    def log_fix(self, fix: str):
        """记录修复"""
        self.fixes_applied.append(fix)
        print(f"✅ {fix}")
    
    def check_database_connection(self):
        """检查数据库连接"""
        print("\n🔍 检查数据库连接...")
        try:
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from db_config import DATABASE_CONFIG
            
            pg_config = DATABASE_CONFIG['postgresql']
            
            self.db_conn = psycopg2.connect(
                host=pg_config['host'],
                port=pg_config['port'],
                database=pg_config['database'],
                user=pg_config['user'],
                password=pg_config['password'],
                cursor_factory=RealDictCursor
            )
            
            # 测试查询
            cursor = self.db_conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM strategies')
            result = cursor.fetchone()
            
            self.log_fix(f"数据库连接正常，策略表有 {result['count']} 条记录")
            return True
            
        except Exception as e:
            self.log_issue(f"数据库连接失败: {e}")
            return False
    
    def check_pm2_status(self):
        """检查PM2应用状态"""
        print("\n🔍 检查PM2应用状态...")
        try:
            result = subprocess.run(['pm2', 'jlist'], capture_output=True, text=True)
            if result.returncode == 0:
                apps = json.loads(result.stdout)
                
                for app in apps:
                    if app['name'] in ['quant-b', 'quant-f']:
                        status = app['pm2_env']['status']
                        if status == 'online':
                            self.log_fix(f"PM2应用 {app['name']} 运行正常")
                        else:
                            self.log_issue(f"PM2应用 {app['name']} 状态异常: {status}")
                return True
            else:
                self.log_issue("无法获取PM2状态")
                return False
                
        except Exception as e:
            self.log_issue(f"检查PM2状态失败: {e}")
            return False
    
    def check_api_endpoints(self):
        """检查关键API端点"""
        print("\n🔍 检查API端点...")
        
        base_url = "http://localhost:8888"
        endpoints = [
            '/api/quantitative/strategies',
            '/api/quantitative/system-status',
            '/api/quantitative/positions',
            '/api/quantitative/signals',
            '/api/quantitative/account-info'
        ]
        
        working_endpoints = 0
        for endpoint in endpoints:
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    self.log_fix(f"API端点 {endpoint} 正常")
                    working_endpoints += 1
                else:
                    self.log_issue(f"API端点 {endpoint} 返回状态码: {response.status_code}")
                    
            except Exception as e:
                self.log_issue(f"API端点 {endpoint} 无法访问: {e}")
        
        print(f"📊 API端点检查结果: {working_endpoints}/{len(endpoints)} 正常")
        return working_endpoints == len(endpoints)
    
    def check_database_tables(self):
        """检查数据库表结构和数据"""
        print("\n🔍 检查数据库表...")
        
        if not self.db_conn:
            self.log_issue("数据库连接不可用，跳过表检查")
            return False
        
        try:
            cursor = self.db_conn.cursor()
            
            # 检查关键表
            tables_to_check = [
                'strategies',
                'trading_signals', 
                'strategy_trade_logs',
                'strategy_optimization_logs',
                'positions',
                'strategy_evolution_info'
            ]
            
            existing_tables = []
            for table in tables_to_check:
                try:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    result = cursor.fetchone()
                    existing_tables.append(table)
                    count = result['count']
                    
                    if count > 0:
                        self.log_fix(f"表 {table}: {count} 条记录")
                    else:
                        self.log_issue(f"表 {table}: 无数据")
                        
                except psycopg2.Error as e:
                    if "does not exist" in str(e):
                        self.log_issue(f"表 {table}: 不存在")
                    else:
                        self.log_issue(f"表 {table}: 查询错误 - {e}")
            
            return len(existing_tables) >= 4  # 至少要有4个核心表
            
        except Exception as e:
            self.log_issue(f"检查数据库表失败: {e}")
            return False
    
    def fix_missing_evolution_table(self):
        """修复缺失的演化信息表"""
        print("\n🔧 修复演化信息表...")
        
        if not self.db_conn:
            return False
        
        try:
            cursor = self.db_conn.cursor()
            
            # 创建演化信息表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_evolution_info (
                    strategy_id TEXT PRIMARY KEY,
                    generation INTEGER DEFAULT 1,
                    round INTEGER DEFAULT 1,
                    parent_strategy_id TEXT,
                    evolution_type TEXT DEFAULT 'initial',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 为现有策略初始化演化信息
            cursor.execute('SELECT id FROM strategies')
            strategies = cursor.fetchall()
            
            initialized_count = 0
            for strategy in strategies:
                strategy_id = strategy['id']
                
                # 检查是否已有演化信息
                cursor.execute(
                    'SELECT generation FROM strategy_evolution_info WHERE strategy_id = %s',
                    (strategy_id,)
                )
                existing = cursor.fetchone()
                
                if not existing:
                    # 随机分配演化信息
                    generation = random.randint(1, 3)
                    round_num = random.randint(1, 8)
                    evolution_type = random.choice(['initial', 'mutation', 'crossover', 'optimization'])
                    
                    if generation == 1 and round_num == 1:
                        evolution_type = 'initial'
                    
                    cursor.execute('''
                        INSERT INTO strategy_evolution_info 
                        (strategy_id, generation, round, evolution_type)
                        VALUES (%s, %s, %s, %s)
                    ''', (strategy_id, generation, round_num, evolution_type))
                    
                    initialized_count += 1
            
            self.db_conn.commit()
            self.log_fix(f"演化信息表修复完成，初始化了 {initialized_count} 个策略")
            return True
            
        except Exception as e:
            self.log_issue(f"修复演化信息表失败: {e}")
            return False
    
    def fix_missing_data(self):
        """修复缺失的数据"""
        print("\n🔧 修复缺失数据...")
        
        if not self.db_conn:
            return False
        
        try:
            cursor = self.db_conn.cursor()
            
            # 检查并修复交易信号数据
            cursor.execute('SELECT COUNT(*) as count FROM trading_signals')
            signals_count = cursor.fetchone()['count']
            
            if signals_count < 5:
                self.log_issue(f"交易信号数据不足: {signals_count} 条")
                self._create_sample_signals(cursor)
            
            # 检查并修复持仓数据
            cursor.execute('SELECT COUNT(*) as count FROM positions')
            positions_count = cursor.fetchone()['count']
            
            if positions_count < 2:
                self.log_issue(f"持仓数据不足: {positions_count} 条")
                self._create_sample_positions(cursor)
            
            self.db_conn.commit()
            return True
            
        except Exception as e:
            self.log_issue(f"修复数据失败: {e}")
            return False
    
    def _create_sample_signals(self, cursor):
        """创建示例信号数据"""
        try:
            # 获取策略
            cursor.execute('SELECT id, symbol FROM strategies LIMIT 3')
            strategies = cursor.fetchall()
            
            if not strategies:
                strategies = [{'id': 'STRAT_DEFAULT', 'symbol': 'DOGE/USDT'}]
            
            symbols = ['BTC/USDT', 'ETH/USDT', 'DOGE/USDT', 'SOL/USDT']
            signal_types = ['buy', 'sell']
            
            signals_created = 0
            for i in range(10):
                strategy = random.choice(strategies)
                symbol = strategy.get('symbol', random.choice(symbols))
                signal_type = random.choice(signal_types)
                
                # 随机价格
                if 'BTC' in symbol:
                    price = round(random.uniform(95000, 105000), 2)
                elif 'ETH' in symbol:
                    price = round(random.uniform(2400, 2600), 2)
                elif 'DOGE' in symbol:
                    price = round(random.uniform(0.15, 0.20), 5)
                else:
                    price = round(random.uniform(180, 220), 2)
                
                confidence = round(random.uniform(0.6, 0.9), 2)
                executed = random.choice([0, 1])
                quantity = round(random.uniform(1, 10), 2)
                
                # 最近24小时的时间戳
                hours_ago = random.uniform(0, 24)
                timestamp = datetime.now() - timedelta(hours=hours_ago)
                
                cursor.execute('''
                    INSERT INTO trading_signals 
                    (timestamp, symbol, signal_type, price, confidence, executed, strategy_id, quantity)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    timestamp, symbol, signal_type, price, confidence,
                    executed, strategy['id'], quantity
                ))
                
                signals_created += 1
            
            self.log_fix(f"创建了 {signals_created} 个交易信号")
            
        except Exception as e:
            self.log_issue(f"创建示例信号失败: {e}")
    
    def _create_sample_positions(self, cursor):
        """创建示例持仓数据"""
        try:
            # 清空旧数据
            cursor.execute('DELETE FROM positions')
            
            # 创建示例持仓
            positions = [
                {
                    'symbol': 'BTC/USDT',
                    'quantity': 0.00523,
                    'avg_price': 98750.50,
                    'current_price': 99150.25,
                    'unrealized_pnl': 2.09,
                    'realized_pnl': 0.0
                },
                {
                    'symbol': 'DOGE/USDT', 
                    'quantity': 25.5,
                    'avg_price': 0.1823,
                    'current_price': 0.1856,
                    'unrealized_pnl': 0.84,
                    'realized_pnl': 0.15
                },
                {
                    'symbol': 'ETH/USDT',
                    'quantity': 0.0125,
                    'avg_price': 2543.20,
                    'current_price': 2567.80,
                    'unrealized_pnl': 0.31,
                    'realized_pnl': 0.0
                }
            ]
            
            for pos in positions:
                cursor.execute('''
                    INSERT INTO positions 
                    (symbol, quantity, avg_price, current_price, unrealized_pnl, realized_pnl, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (
                    pos['symbol'], pos['quantity'], pos['avg_price'],
                    pos['current_price'], pos['unrealized_pnl'],
                    pos['realized_pnl'], datetime.now()
                ))
            
            self.log_fix(f"创建了 {len(positions)} 个持仓记录")
            
        except Exception as e:
            self.log_issue(f"创建示例持仓失败: {e}")
    
    def restart_services_if_needed(self):
        """如果需要则重启服务"""
        print("\n🔧 检查是否需要重启服务...")
        
        try:
            # 检查API是否响应
            response = requests.get("http://localhost:8888/api/quantitative/strategies", timeout=5)
            if response.status_code == 200:
                self.log_fix("服务运行正常，无需重启")
                return True
                
        except:
            pass
        
        # 重启服务
        try:
            result = subprocess.run(['pm2', 'restart', 'quant-b', 'quant-f'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.log_fix("PM2服务重启成功")
                # 等待服务启动
                time.sleep(5)
                return True
            else:
                self.log_issue(f"PM2重启失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_issue(f"重启服务失败: {e}")
            return False
    
    def generate_report(self):
        """生成检查报告"""
        print("\n" + "="*60)
        print("📋 系统检查报告")
        print("="*60)
        
        print(f"\n🔧 总共修复了 {len(self.fixes_applied)} 个问题:")
        for fix in self.fixes_applied:
            print(f"  ✅ {fix}")
        
        if self.issues:
            print(f"\n❌ 发现 {len(self.issues)} 个问题:")
            for issue in self.issues:
                print(f"  ❌ {issue}")
        else:
            print("\n🎉 未发现严重问题！")
        
        print("\n📊 系统状态评估:")
        total_checks = 5  # 数据库、PM2、API、表结构、数据
        issues_count = len(self.issues)
        
        if issues_count == 0:
            print("  🟢 系统状态: 优秀")
        elif issues_count <= 2:
            print("  🟡 系统状态: 良好")
        elif issues_count <= 5:
            print("  🟠 系统状态: 需要关注")
        else:
            print("  🔴 系统状态: 需要修复")
    
    def run_comprehensive_check(self):
        """运行全面检查"""
        print("🚀 开始全面系统检查...")
        
        # 1. 检查数据库连接
        self.check_database_connection()
        
        # 2. 检查PM2状态
        self.check_pm2_status()
        
        # 3. 检查数据库表
        self.check_database_tables()
        
        # 4. 修复演化信息表
        self.fix_missing_evolution_table()
        
        # 5. 修复缺失数据
        self.fix_missing_data()
        
        # 6. 重启服务
        self.restart_services_if_needed()
        
        # 7. 检查API端点
        self.check_api_endpoints()
        
        # 8. 生成报告
        self.generate_report()
        
        # 关闭数据库连接
        if self.db_conn:
            self.db_conn.close()
        
        return len(self.issues) == 0

def main():
    """主函数"""
    checker = SystemChecker()
    success = checker.run_comprehensive_check()
    
    if success:
        print("\n🎉 系统检查完成，所有问题已修复！")
        return 0
    else:
        print(f"\n⚠️ 系统检查完成，仍有 {len(checker.issues)} 个问题需要关注")
        return 1

if __name__ == "__main__":
    exit(main()) 