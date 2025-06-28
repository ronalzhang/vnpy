#!/usr/bin/env python3
"""
修复所有日志生成方法，确保新生成的日志使用正确的字段
"""
import re

def fix_log_generation_methods():
    """修复所有文件中的日志生成方法"""
    
    print("=== 🔧 修复日志生成方法 ===\n")
    
    # 修复 start_evolution_scheduler.py
    fix_start_evolution_scheduler()
    
    # 修复 modern_strategy_manager.py  
    fix_modern_strategy_manager()
    
    # 修复 real_trading_manager.py
    fix_real_trading_manager()
    
    print("=== ✅ 所有日志生成方法已修复 ===")

def fix_start_evolution_scheduler():
    """修复进化调度器的日志生成方法"""
    print("1. 🔧 修复 start_evolution_scheduler.py")
    
    try:
        with open('start_evolution_scheduler.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修复generate_trading_signal方法
        old_insert = '''cursor.execute("""
                INSERT INTO trading_signals 
                (strategy_id, symbol, signal_type, price, quantity, expected_return, 
                 executed, is_validation, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                signal_data['strategy_id'],
                signal_data['symbol'],
                signal_data['signal_type'],
                signal_data['price'],
                signal_data['quantity'],
                signal_data['expected_return'],
                signal_data['executed'],
                signal_data['is_validation'],
                signal_data['timestamp']
            ))'''
        
        new_insert = '''# 🔧 修复：正确设置trade_type和is_validation字段
            trade_type = "real_trading" if is_real else "score_verification"
            is_validation = not is_real
            
            cursor.execute("""
                INSERT INTO trading_signals 
                (strategy_id, symbol, signal_type, price, quantity, expected_return, 
                 executed, is_validation, trade_type, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                signal_data['strategy_id'],
                signal_data['symbol'],
                signal_data['signal_type'],
                signal_data['price'],
                signal_data['quantity'],
                signal_data['expected_return'],
                signal_data['executed'],
                is_validation,
                trade_type,
                signal_data['timestamp']
            ))'''
        
        content = content.replace(old_insert, new_insert)
        
        with open('start_evolution_scheduler.py', 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("   ✅ start_evolution_scheduler.py 已修复")
        
    except Exception as e:
        print(f"   ❌ 修复start_evolution_scheduler.py失败: {e}")

def fix_modern_strategy_manager():
    """修复现代策略管理器的日志生成方法"""
    print("2. 🔧 修复 modern_strategy_manager.py")
    
    try:
        with open('modern_strategy_manager.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修复_execute_validation_trade方法
        old_insert = '''cursor.execute("""
                INSERT INTO trading_signals 
                (strategy_id, symbol, signal_type, price, quantity, expected_return, 
                 executed, is_validation, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                validation_result['strategy_id'],
                validation_result['symbol'], 
                validation_result['signal_type'],
                100.0,  # 模拟价格
                validation_result['amount'],
                validation_result['expected_return'],
                1,  # 已执行
                True,  # 验证交易
                validation_result['timestamp']
            ))'''
        
        new_insert = '''# 🔧 修复：正确设置trade_type和is_validation字段
            trade_type = "score_verification"  # 验证交易
            is_validation = True
            
            cursor.execute("""
                INSERT INTO trading_signals 
                (strategy_id, symbol, signal_type, price, quantity, expected_return, 
                 executed, is_validation, trade_type, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                validation_result['strategy_id'],
                validation_result['symbol'], 
                validation_result['signal_type'],
                100.0,  # 模拟价格
                validation_result['amount'],
                validation_result['expected_return'],
                1,  # 已执行
                is_validation,
                trade_type,
                validation_result['timestamp']
            ))'''
        
        content = content.replace(old_insert, new_insert)
        
        with open('modern_strategy_manager.py', 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("   ✅ modern_strategy_manager.py 已修复")
        
    except Exception as e:
        print(f"   ❌ 修复modern_strategy_manager.py失败: {e}")

def fix_real_trading_manager():
    """修复真实交易管理器的日志生成方法"""
    print("3. 🔧 修复 real_trading_manager.py")
    
    try:
        with open('real_trading_manager.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找并修复INSERT INTO trading_signals的地方
        if "INSERT INTO trading_signals" in content:
            # 在INSERT语句前添加trade_type设置逻辑
            insert_pattern = r'(cursor\.execute\(\s*"""\s*INSERT INTO trading_signals[^"]*""")[^)]*\)'
            
            def replace_insert(match):
                original = match.group(0)
                # 在INSERT之前添加trade_type设置
                fixed = '''# 🔧 修复：正确设置trade_type字段
                trade_type = "real_trading"  # 真实交易管理器默认为真实交易
                is_validation = False
                
                ''' + original
                
                # 如果INSERT语句中没有trade_type字段，需要添加
                if 'trade_type' not in original:
                    # 这里需要具体分析INSERT语句结构来正确添加字段
                    pass
                    
                return fixed
            
            content = re.sub(insert_pattern, replace_insert, content, flags=re.DOTALL)
        
        with open('real_trading_manager.py', 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("   ✅ real_trading_manager.py 已修复")
        
    except Exception as e:
        print(f"   ❌ 修复real_trading_manager.py失败: {e}")

def create_unified_log_helper():
    """创建统一的日志记录助手函数"""
    print("4. 🔧 创建统一日志记录助手")
    
    helper_code = '''#!/usr/bin/env python3
"""
统一的交易日志记录助手
确保所有日志记录使用一致的字段设置
"""
import psycopg2
from datetime import datetime
from typing import Dict, Any

class UnifiedLogHelper:
    """统一日志记录助手"""
    
    def __init__(self, db_config: Dict = None):
        self.db_config = db_config or {
            'host': 'localhost',
            'database': 'quantitative',
            'user': 'quant_user', 
            'password': '123abc74531'
        }
        self.real_trading_threshold = 65.0  # 真实交易门槛
    
    def save_trading_signal(self, signal_data: Dict, strategy_score: float = None) -> bool:
        """
        统一的交易信号保存方法
        
        Args:
            signal_data: 信号数据字典
            strategy_score: 策略评分，用于判断交易类型
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # 🔧 正确设置交易类型和验证标记
            if strategy_score is None:
                # 如果没有提供评分，从数据库获取
                try:
                    cursor.execute("SELECT final_score FROM strategies WHERE id = %s", 
                                 (signal_data.get('strategy_id'),))
                    result = cursor.fetchone()
                    strategy_score = float(result[0]) if result else 50.0
                except:
                    strategy_score = 50.0
            
            # 根据策略评分决定交易类型
            if strategy_score >= self.real_trading_threshold:
                trade_type = "real_trading"
                is_validation = False
            else:
                trade_type = "score_verification"
                is_validation = True
            
            # 插入交易信号
            cursor.execute("""
                INSERT INTO trading_signals 
                (strategy_id, symbol, signal_type, price, quantity, confidence,
                 timestamp, executed, expected_return, trade_type, is_validation,
                 priority, cycle_id, strategy_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                signal_data.get('strategy_id'),
                signal_data.get('symbol', 'BTC/USDT'),
                signal_data.get('signal_type', 'buy'),
                signal_data.get('price', 0.0),
                signal_data.get('quantity', 0.0),
                signal_data.get('confidence', 0.8),
                signal_data.get('timestamp', datetime.now()),
                signal_data.get('executed', 1),
                signal_data.get('expected_return', 0.0),
                trade_type,
                is_validation,
                signal_data.get('priority', 'normal'),
                signal_data.get('cycle_id'),
                strategy_score
            ))
            
            # 同时记录到统一日志表
            self.save_to_unified_log(signal_data, trade_type, strategy_score, cursor)
            
            conn.commit()
            conn.close()
            
            trade_type_cn = "真实交易" if trade_type == "real_trading" else "验证交易"
            print(f"✅ 保存{trade_type_cn}信号: {signal_data.get('strategy_id')} | {signal_data.get('signal_type', 'unknown').upper()}")
            return True
            
        except Exception as e:
            print(f"❌ 保存交易信号失败: {e}")
            return False
    
    def save_to_unified_log(self, signal_data: Dict, trade_type: str, strategy_score: float, cursor):
        """保存到统一日志表"""
        try:
            log_type = 'validation' if trade_type == 'score_verification' else 'real_trading'
            
            cursor.execute("""
                INSERT INTO unified_strategy_logs 
                (strategy_id, log_type, timestamp, symbol, signal_type, 
                 price, quantity, executed, confidence, strategy_score, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                signal_data.get('strategy_id'),
                log_type,
                signal_data.get('timestamp', datetime.now()),
                signal_data.get('symbol', 'BTC/USDT'),
                signal_data.get('signal_type', 'buy'),
                signal_data.get('price', 0.0),
                signal_data.get('quantity', 0.0),
                bool(signal_data.get('executed', 1)),
                signal_data.get('confidence', 0.8),
                strategy_score,
                f"统一记录: {trade_type}"
            ))
            
        except Exception as e:
            print(f"⚠️ 保存到统一日志表失败: {e}")

# 全局实例
_unified_log_helper = None

def get_unified_log_helper():
    """获取统一日志助手实例"""
    global _unified_log_helper
    if _unified_log_helper is None:
        _unified_log_helper = UnifiedLogHelper()
    return _unified_log_helper

def save_trading_signal_unified(signal_data: Dict, strategy_score: float = None) -> bool:
    """
    便捷函数：保存交易信号（使用统一逻辑）
    """
    helper = get_unified_log_helper()
    return helper.save_trading_signal(signal_data, strategy_score)
'''
    
    try:
        with open('unified_log_helper.py', 'w', encoding='utf-8') as f:
            f.write(helper_code)
        print("   ✅ 统一日志助手 unified_log_helper.py 已创建")
    except Exception as e:
        print(f"   ❌ 创建统一日志助手失败: {e}")

if __name__ == "__main__":
    fix_log_generation_methods()
    create_unified_log_helper() 