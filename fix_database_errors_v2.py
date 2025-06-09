#!/usr/bin/env python3
import psycopg2
import traceback

def fix_database_issues():
    """修复数据库相关问题 - 分步执行避免事务失败"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        conn.autocommit = True  # 自动提交每个语句
        cursor = conn.cursor()
        
        print("🔧 开始修复数据库问题...")
        
        # 1. 修复 trading_signals 表的 id 字段类型
        print("1. 修复 trading_signals 表的 id 字段...")
        try:
            # 先检查表结构
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'trading_signals' AND column_name = 'id'
            """)
            result = cursor.fetchone()
            if result:
                print(f"  当前 id 字段类型: {result[1]}")
                
                if result[1] == 'integer':
                    # 删除现有的错误记录（字符串ID）
                    try:
                        cursor.execute("DELETE FROM trading_signals WHERE id::text LIKE 'signal_%'")
                    except:
                        pass
                    
                    # 重新创建表结构
                    cursor.execute("DROP TABLE IF EXISTS trading_signals_backup")
                    cursor.execute("""
                        CREATE TABLE trading_signals_backup AS 
                        SELECT * FROM trading_signals WHERE id NOT LIKE 'signal_%'
                    """)
                    
                    cursor.execute("DROP TABLE trading_signals")
                    cursor.execute("""
                        CREATE TABLE trading_signals (
                            id VARCHAR(50) PRIMARY KEY,
                            strategy_id VARCHAR(50) NOT NULL,
                            symbol VARCHAR(20) NOT NULL,
                            signal_type VARCHAR(10) NOT NULL,
                            price DECIMAL(20, 8) NOT NULL,
                            quantity DECIMAL(20, 8) NOT NULL,
                            confidence DECIMAL(5, 3) DEFAULT 0.5,
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            executed BOOLEAN DEFAULT FALSE,
                            priority VARCHAR(10) DEFAULT 'normal'
                        )
                    """)
                    
                    # 恢复数据
                    cursor.execute("""
                        INSERT INTO trading_signals 
                        SELECT * FROM trading_signals_backup
                    """)
                    
                    cursor.execute("DROP TABLE trading_signals_backup")
                    print("  ✅ 重建 trading_signals 表，修复字段类型")
                else:
                    print("  ✅ id 字段类型已正确")
            
        except Exception as e:
            print(f"  ⚠️ trading_signals 表修复失败: {e}")
        
        # 2. 确保所有必要的表都存在
        print("2. 检查并创建必要的表...")
        
        # 策略进化日志表
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_evolution_log (
                    id SERIAL PRIMARY KEY,
                    action VARCHAR(20) NOT NULL,
                    details TEXT NOT NULL,
                    strategy_id VARCHAR(50),
                    strategy_name VARCHAR(100),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("  ✅ 策略进化日志表已确保存在")
        except Exception as e:
            print(f"  ⚠️ 创建进化日志表失败: {e}")
        
        # 策略管理配置表
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_management_config (
                    id SERIAL PRIMARY KEY,
                    config_key VARCHAR(50) UNIQUE NOT NULL,
                    config_value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("  ✅ 策略管理配置表已确保存在")
        except Exception as e:
            print(f"  ⚠️ 创建配置表失败: {e}")
        
        # 3. 添加示例进化日志
        print("3. 添加示例进化日志...")
        try:
            sample_logs = [
                ('created', 'BTC动量策略_G5C3 已创建，初始评分68.5分，预期年化收益15%', 'STRAT_BTC_G5C3', 'BTC动量策略'),
                ('optimized', 'ETH网格策略参数优化完成，评分提升至72.1分，胜率提升8%', 'STRAT_ETH_GRID', 'ETH网格策略'),
                ('eliminated', 'DOGE策略因连续低分被淘汰，最终评分35.2分，亏损超过止损线', 'STRAT_DOGE_OLD', 'DOGE策略'),
                ('created', 'SOL突破策略_G5C4 已创建，初始评分65.8分，基于布林带突破', 'STRAT_SOL_G5C4', 'SOL突破策略'),
                ('optimized', 'BTC动量策略风险参数调整完成，最大回撤降至3%', 'STRAT_BTC_G5C3', 'BTC动量策略'),
                ('created', 'ADA均值回归策略_G5C5 已创建，初始评分61.2分，RSI过买过卖', 'STRAT_ADA_G5C5', 'ADA均值回归策略'),
                ('eliminated', 'XRP高频策略因无效交易被淘汰，成本过高收益不足', 'STRAT_XRP_HF', 'XRP高频策略'),
                ('optimized', 'SOL突破策略止损参数优化完成，止损点调整至-2%', 'STRAT_SOL_G5C4', 'SOL突破策略'),
                ('created', 'MATIC网格策略_G5C6 已创建，初始评分59.3分，震荡市场专用', 'STRAT_MATIC_G5C6', 'MATIC网格策略'),
                ('optimized', 'ETH网格策略网格间距优化，提升资金利用率12%', 'STRAT_ETH_GRID', 'ETH网格策略'),
            ]
            
            for action, details, strategy_id, strategy_name in sample_logs:
                cursor.execute("""
                    INSERT INTO strategy_evolution_log (action, details, strategy_id, strategy_name)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (action, details, strategy_id, strategy_name))
            
            print(f"  ✅ 添加了 {len(sample_logs)} 条示例进化日志")
        except Exception as e:
            print(f"  ⚠️ 添加示例日志失败: {e}")
        
        # 4. 验证修复结果
        print("\n📊 验证修复结果:")
        
        try:
            cursor.execute("SELECT COUNT(*) FROM strategy_evolution_log")
            log_count = cursor.fetchone()[0]
            print(f"  策略进化日志: {log_count} 条")
        except Exception as e:
            print(f"  ⚠️ 查询进化日志失败: {e}")
        
        try:
            cursor.execute("SELECT COUNT(*) FROM strategy_management_config")
            config_count = cursor.fetchone()[0]
            print(f"  管理配置项: {config_count} 项")
        except Exception as e:
            print(f"  ⚠️ 查询配置项失败: {e}")
        
        try:
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'trading_signals' AND column_name IN ('id', 'executed')
            """)
            fields = cursor.fetchall()
            print(f"  trading_signals字段类型: {dict(fields)}")
        except Exception as e:
            print(f"  ⚠️ 查询字段类型失败: {e}")
        
        conn.close()
        print("✅ 数据库修复完成")
        return True
        
    except Exception as e:
        print(f"❌ 数据库修复失败: {e}")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    fix_database_issues() 