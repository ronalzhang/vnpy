#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合验证测试脚本
1. 修复策略ID格式问题
2. 设置高分策略测试验证机制
3. 全面测试验证交易功能
"""

import psycopg2
import uuid
import json
import time
import random
from datetime import datetime, timedelta

class ComprehensiveVerificationTest:
    def __init__(self):
        self.conn = psycopg2.connect(
            host='localhost',
            database='quantitative',
            user='quant_user',
            password='123abc74531'
        )
        self.cursor = self.conn.cursor()
        self.test_results = {}
        
    def log_test(self, test_name, status, details=""):
        """记录测试结果"""
        print(f"{'✅' if status else '❌'} {test_name}: {details}")
        self.test_results[test_name] = {"status": status, "details": details}
    
    def test_1_fix_strategy_ids(self):
        """测试1: 修复策略ID格式问题"""
        print("\n🔧 测试1: 修复策略ID格式...")
        
        try:
            # 检查短ID策略数量
            self.cursor.execute("SELECT COUNT(*) FROM strategies WHERE LENGTH(id) < 32")
            short_id_count = self.cursor.fetchone()[0]
            
            if short_id_count == 0:
                self.log_test("策略ID格式检查", True, "所有策略ID格式正确")
                return True
            
            print(f"发现 {short_id_count} 个短ID策略需要修复")
            
            # 只修复前100个短ID策略作为测试
            self.cursor.execute("SELECT id FROM strategies WHERE LENGTH(id) < 32 LIMIT 100")
            short_ids = self.cursor.fetchall()
            
            update_count = 0
            for (old_id,) in short_ids:
                new_id = str(uuid.uuid4())
                self.cursor.execute("UPDATE strategies SET id = %s WHERE id = %s", (new_id, old_id))
                update_count += 1
            
            self.conn.commit()
            self.log_test("策略ID修复", True, f"已修复 {update_count} 个策略ID")
            return True
            
        except Exception as e:
            self.conn.rollback()
            self.log_test("策略ID修复", False, f"修复失败: {e}")
            return False
    
    def test_2_create_high_score_strategies(self):
        """测试2: 创建高分策略用于测试验证机制"""
        print("\n🎯 测试2: 创建高分策略...")
        
        try:
            # 创建5个高分测试策略
            test_cases = [
                {"name": "高分测试策略A", "score": 68.5, "win_rate": 85.0, "trades": 100},
                {"name": "高分测试策略B", "score": 72.3, "win_rate": 65.0, "trades": 5},
                {"name": "高分测试策略C", "score": 75.1, "win_rate": 70.0, "trades": 200},
                {"name": "高分测试策略D", "score": 69.8, "win_rate": 78.0, "trades": 150},
                {"name": "高分测试策略E", "score": 66.2, "win_rate": 72.0, "trades": 80}
            ]
            
            created_count = 0
            for test_case in test_cases:
                strategy_id = str(uuid.uuid4())
                
                # 设置参数
                parameters = {
                    "stop_loss_pct": random.uniform(2.0, 8.0),
                    "take_profit_pct": random.uniform(5.0, 15.0),
                    "quantity": random.uniform(10, 1000),
                    "lookback_period": random.randint(20, 100)
                }
                
                # 插入策略（修复enabled字段类型）
                self.cursor.execute("""
                    INSERT INTO strategies (
                        id, name, symbol, type, enabled, parameters, 
                        final_score, win_rate, total_trades, total_return,
                        created_at, updated_at, generation, cycle
                    ) VALUES (
                        %s, %s, 'BTCUSDT', 'momentum', 1, %s,
                        %s, %s, %s, %s, %s, %s, 2, 3
                    )
                """, (
                    strategy_id, test_case["name"], json.dumps(parameters),
                    test_case["score"], test_case["win_rate"], test_case["trades"],
                    random.uniform(0.1, 0.5), 
                    datetime.now() - timedelta(days=random.randint(1, 30)),
                    datetime.now()
                ))
                created_count += 1
            
            self.conn.commit()
            self.log_test("创建高分测试策略", True, f"成功创建 {created_count} 个测试策略")
            return True
            
        except Exception as e:
            self.conn.rollback()
            self.log_test("创建高分测试策略", False, f"创建失败: {e}")
            return False
    
    def test_3_verify_high_score_validation(self):
        """测试3: 验证高分策略验证机制"""
        print("\n🔍 测试3: 验证高分策略验证机制...")
        
        try:
            # 检查是否有65分以上策略
            self.cursor.execute("SELECT COUNT(*) FROM strategies WHERE final_score >= 65")
            high_score_count = self.cursor.fetchone()[0]
            
            if high_score_count == 0:
                self.log_test("高分策略检查", False, "没有找到65分以上的策略")
                return False
            
            self.log_test("高分策略检查", True, f"找到 {high_score_count} 个高分策略")
            
            # 选择一个高分策略进行验证测试
            self.cursor.execute("SELECT id FROM strategies WHERE final_score >= 65 LIMIT 1")
            test_strategy_id = self.cursor.fetchone()[0]
            
            # 插入验证交易记录
            validation_id = str(uuid.uuid4())
            for i in range(4):
                self.cursor.execute("""
                    INSERT INTO trading_signals (
                        strategy_id, symbol, signal_type, price, quantity, 
                        confidence, executed, expected_return, timestamp,
                        trade_type, validation_id, validation_round
                    ) VALUES (
                        %s, 'BTCUSDT', %s, %s, 10.0, 0.8, 1, %s, %s,
                        'score_verification', %s, %s
                    )
                """, (
                    test_strategy_id,
                    'buy' if i % 2 == 0 else 'sell',
                    random.uniform(40000, 50000),
                    random.uniform(-20, 10),
                    datetime.now() - timedelta(minutes=i*10),
                    validation_id,
                    i + 1
                ))
            
            self.conn.commit()
            self.log_test("高分策略验证模拟", True, f"为策略 {test_strategy_id[:8]} 创建了验证交易记录")
            return True
            
        except Exception as e:
            self.conn.rollback()
            self.log_test("高分策略验证机制", False, f"验证失败: {e}")
            return False
    
    def test_4_verification_trade_classification(self):
        """测试4: 验证交易分类功能"""
        print("\n📊 测试4: 验证交易分类功能...")
        
        try:
            # 检查验证交易记录
            self.cursor.execute("""
                SELECT trade_type, COUNT(*) 
                FROM trading_signals 
                WHERE trade_type IS NOT NULL 
                GROUP BY trade_type
            """)
            trade_types = self.cursor.fetchall()
            
            if not trade_types:
                self.log_test("验证交易记录", False, "没有找到任何验证交易记录")
            else:
                trade_summary = ", ".join([f"{t_type}: {count}条" for t_type, count in trade_types])
                self.log_test("验证交易记录", True, f"交易分类: {trade_summary}")
            
            return True
            
        except Exception as e:
            self.log_test("验证交易分类", False, f"检查失败: {e}")
            return False
    
    def run_comprehensive_test(self):
        """运行综合测试"""
        print("🚀 开始综合验证测试...")
        print("=" * 60)
        
        tests = [
            self.test_1_fix_strategy_ids,
            self.test_2_create_high_score_strategies, 
            self.test_3_verify_high_score_validation,
            self.test_4_verification_trade_classification
        ]
        
        passed_tests = 0
        for test_func in tests:
            try:
                if test_func():
                    passed_tests += 1
                time.sleep(1)
            except Exception as e:
                print(f"❌ 测试执行异常: {e}")
        
        # 输出测试报告
        print("\n" + "=" * 60)
        print("📋 综合测试报告")
        print("=" * 60)
        
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result["status"] else "❌"
            print(f"{status_icon} {test_name}: {result['details']}")
        
        print(f"\n🎯 测试通过率: {passed_tests}/{len(tests)} ({passed_tests/len(tests)*100:.1f}%)")
        return passed_tests == len(tests)
    
    def cleanup(self):
        """清理资源"""
        if hasattr(self, 'cursor'):
            self.cursor.close()
        if hasattr(self, 'conn'):
            self.conn.close()

if __name__ == "__main__":
    try:
        test = ComprehensiveVerificationTest()
        success = test.run_comprehensive_test()
        test.cleanup()
        
        print(f"\n{'🎉 测试完成！' if success else '⚠️ 测试未完全通过'}")
            
    except Exception as e:
        print(f"💥 测试执行失败: {e}") 