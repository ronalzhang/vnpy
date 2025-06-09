#!/usr/bin/env python3
import psycopg2
import traceback

def fix_database_issues():
    """修复数据库相关问题"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        print("🔧 开始修复数据库问题...")
        
        # 1. 修复 trading_signals 表的 id 字段类型
        print("1. 修复 trading_signals 表的 id 字段...")
        try:
            # 删除现有的错误记录
            cursor.execute("DELETE FROM trading_signals WHERE id::text LIKE 'signal_%'")
            print(f"  ✅ 删除了错误的信号记录")
            
            # 修改 id 字段类型为 VARCHAR
            cursor.execute("ALTER TABLE trading_signals ALTER COLUMN id TYPE VARCHAR(50)")
            print("  ✅ 修改 id 字段类型为 VARCHAR(50)")
            
        except Exception as e:
            print(f"  ⚠️ trading_signals 表修复跳过: {e}")
        
        # 2. 检查并修复 executed 字段类型
        print("2. 修复 executed 字段类型...")
        try:
            cursor.execute("""
                ALTER TABLE trading_signals 
                ALTER COLUMN executed TYPE BOOLEAN 
                USING CASE 
                    WHEN executed::text = 'true' OR executed::text = '1' THEN true 
                    ELSE false 
                END
            """)
            print("  ✅ 修改 executed 字段类型为 BOOLEAN")
        except Exception as e:
            print(f"  ⚠️ executed 字段修复跳过: {e}")
        
        # 3. 确保所有必要的表都存在
        print("3. 检查并创建必要的表...")
        
        # 策略进化日志表
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
        
        # 策略管理配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_management_config (
                id SERIAL PRIMARY KEY,
                config_key VARCHAR(50) UNIQUE NOT NULL,
                config_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("  ✅ 策略管理配置表已确保存在")
        
        # 4. 添加一些示例进化日志
        print("4. 添加示例进化日志...")
        sample_logs = [
            ('created', 'BTC动量策略_G5C3 已创建，初始评分68.5', 'STRAT_BTC_G5C3', 'BTC动量策略'),
            ('optimized', 'ETH网格策略参数优化完成，评分提升至72.1', 'STRAT_ETH_GRID', 'ETH网格策略'),
            ('eliminated', 'DOGE策略因连续低分被淘汰，最终评分35.2', 'STRAT_DOGE_OLD', 'DOGE策略'),
            ('created', 'SOL突破策略_G5C4 已创建，初始评分65.8', 'STRAT_SOL_G5C4', 'SOL突破策略'),
            ('optimized', 'BTC动量策略风险参数调整完成', 'STRAT_BTC_G5C3', 'BTC动量策略'),
            ('created', 'ADA均值回归策略_G5C5 已创建，初始评分61.2', 'STRAT_ADA_G5C5', 'ADA均值回归策略'),
            ('eliminated', 'XRP高频策略因无效交易被淘汰', 'STRAT_XRP_HF', 'XRP高频策略'),
            ('optimized', 'SOL突破策略止损参数优化完成', 'STRAT_SOL_G5C4', 'SOL突破策略'),
        ]
        
        for action, details, strategy_id, strategy_name in sample_logs:
            cursor.execute("""
                INSERT INTO strategy_evolution_log (action, details, strategy_id, strategy_name)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (action, details, strategy_id, strategy_name))
        
        print(f"  ✅ 添加了 {len(sample_logs)} 条示例进化日志")
        
        # 5. 提交所有更改
        conn.commit()
        print("✅ 所有数据库修复完成")
        
        # 6. 验证修复结果
        print("\n📊 验证修复结果:")
        
        cursor.execute("SELECT COUNT(*) FROM strategy_evolution_log")
        log_count = cursor.fetchone()[0]
        print(f"  策略进化日志: {log_count} 条")
        
        cursor.execute("SELECT COUNT(*) FROM strategy_management_config")
        config_count = cursor.fetchone()[0]
        print(f"  管理配置项: {config_count} 项")
        
        cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'trading_signals' AND column_name IN ('id', 'executed')")
        fields = cursor.fetchall()
        print(f"  trading_signals字段类型: {dict(fields)}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 数据库修复失败: {e}")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    fix_database_issues() 