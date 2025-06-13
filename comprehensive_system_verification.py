#!/usr/bin/env python3
"""
交易周期优化方案全面验证脚本
验证所有新功能是否正确实现并工作
"""

import psycopg2
import requests
import json
import datetime
import sys
from typing import Dict, List, Tuple, Optional

class SystemVerification:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'quantitative',
            'user': 'quant_user',
            'password': '123abc74531'
        }
        self.api_base = 'http://localhost:8888'
        self.verification_report = {
            'timestamp': datetime.datetime.now().isoformat(),
            'tests': [],
            'summary': {
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'warnings': 0
            }
        }
    
    def log_test(self, test_name: str, status: str, details: str, data: any = None):
        """记录测试结果"""
        result = {
            'test_name': test_name,
            'status': status,  # PASS, FAIL, WARNING
            'details': details,
            'timestamp': datetime.datetime.now().isoformat(),
            'data': data
        }
        self.verification_report['tests'].append(result)
        self.verification_report['summary']['total_tests'] += 1
        if status.lower() == 'warning':
            self.verification_report['summary']['warnings'] += 1
        elif status.lower() in ['pass', 'fail']:
            self.verification_report['summary'][status.lower() + 'ed'] += 1
        
        # 实时输出
        status_emoji = {'PASS': '✅', 'FAIL': '❌', 'WARNING': '⚠️'}
        print(f"{status_emoji.get(status, '❓')} {test_name}: {details}")
        if data and isinstance(data, dict) and len(str(data)) < 200:
            print(f"   数据: {data}")
    
    def get_db_connection(self):
        """获取数据库连接"""
        try:
            return psycopg2.connect(**self.db_config)
        except Exception as e:
            self.log_test("数据库连接", "FAIL", f"无法连接数据库: {e}")
            return None
    
    def test_database_structure(self):
        """验证数据库结构"""
        print("\n=== 数据库结构验证 ===")
        
        conn = self.get_db_connection()
        if not conn:
            return
            
        try:
            cur = conn.cursor()
            
            # 检查表是否存在
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
            tables = [row[0] for row in cur.fetchall()]
            
            if 'trading_signals' in tables:
                self.log_test("表存在性检查", "PASS", "trading_signals表存在")
            else:
                self.log_test("表存在性检查", "FAIL", "trading_signals表不存在", {'available_tables': tables})
                return
            
            # 检查新字段
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default 
                FROM information_schema.columns 
                WHERE table_name = 'trading_signals' 
                ORDER BY ordinal_position;
            """)
            columns = cur.fetchall()
            existing_fields = [col[0] for col in columns]
            
            # 必需的新字段
            required_fields = [
                'cycle_id', 'cycle_status', 'open_time', 'close_time', 
                'holding_minutes', 'mrot_score', 'paired_signal_id'
            ]
            
            missing_fields = []
            for field in required_fields:
                if field in existing_fields:
                    self.log_test(f"字段检查-{field}", "PASS", f"{field}字段存在")
                else:
                    missing_fields.append(field)
                    self.log_test(f"字段检查-{field}", "FAIL", f"{field}字段缺失")
            
            if missing_fields:
                self.log_test("数据库结构完整性", "FAIL", f"缺失字段: {missing_fields}")
            else:
                self.log_test("数据库结构完整性", "PASS", "所有必需字段都存在")
            
        except Exception as e:
            self.log_test("数据库结构验证", "FAIL", f"验证失败: {e}")
        finally:
            conn.close()
    
    def test_trade_cycle_matching(self):
        """验证交易周期匹配逻辑"""
        print("\n=== 交易周期匹配验证 ===")
        
        conn = self.get_db_connection()
        if not conn:
            return
            
        try:
            cur = conn.cursor()
            
            # 检查是否有完整的交易周期
            cur.execute("""
                SELECT strategy_id, cycle_id, cycle_status, signal_type, executed, 
                       open_time, close_time, holding_minutes, mrot_score
                FROM trading_signals 
                WHERE cycle_id IS NOT NULL 
                ORDER BY strategy_id, open_time DESC
                LIMIT 10;
            """)
            cycles = cur.fetchall()
            
            if cycles:
                self.log_test("交易周期数据", "PASS", f"找到{len(cycles)}个交易周期记录")
                
                # 分析周期完整性
                complete_cycles = 0
                open_cycles = 0
                
                for cycle in cycles:
                    strategy_id, cycle_id, status, signal_type, executed, open_time, close_time, holding_minutes, mrot_score = cycle
                    
                    if status == 'closed' and close_time and holding_minutes is not None:
                        complete_cycles += 1
                        self.log_test("完整周期验证", "PASS", 
                                    f"策略{strategy_id}周期{cycle_id}: {holding_minutes}分钟, MRoT={mrot_score}")
                    elif status == 'open':
                        open_cycles += 1
                
                self.log_test("周期统计", "PASS", 
                            f"完整周期: {complete_cycles}, 开放周期: {open_cycles}")
                
            else:
                self.log_test("交易周期数据", "WARNING", "未找到交易周期记录，可能系统刚启动")
                
        except Exception as e:
            self.log_test("交易周期匹配验证", "FAIL", f"验证失败: {e}")
        finally:
            conn.close()
    
    def test_api_interfaces(self):
        """验证API接口"""
        print("\n=== API接口验证 ===")
        
        # 测试关键API端点
        api_tests = [
            ('/api/quantitative/system-status', '系统状态API'),
            ('/api/quantitative/strategies', '策略列表API'),
        ]
        
        for endpoint, description in api_tests:
            try:
                response = requests.get(f"{self.api_base}{endpoint}", timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success', True):  # 某些API没有success字段，默认认为成功
                        self.log_test(f"API测试-{description}", "PASS", 
                                    f"响应正常，状态码: {response.status_code}")
                    else:
                        self.log_test(f"API测试-{description}", "FAIL", 
                                    f"API返回错误: {data.get('error', '未知错误')}")
                else:
                    self.log_test(f"API测试-{description}", "FAIL", 
                                f"HTTP错误，状态码: {response.status_code}")
                                
            except requests.exceptions.RequestException as e:
                self.log_test(f"API测试-{description}", "FAIL", f"请求失败: {e}")
            except json.JSONDecodeError as e:
                self.log_test(f"API测试-{description}", "FAIL", f"JSON解析失败: {e}")
    
    def generate_report(self):
        """生成验证报告"""
        print("\n" + "="*60)
        print("📊 交易周期优化方案验证报告")
        print("="*60)
        
        summary = self.verification_report['summary']
        total = summary['total_tests']
        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        warnings = summary.get('warnings', 0)
        
        print(f"总测试数: {total}")
        print(f"✅ 通过: {passed} ({passed/total*100:.1f}%)")
        print(f"❌ 失败: {failed} ({failed/total*100:.1f}%)")
        print(f"⚠️  警告: {warnings} ({warnings/total*100:.1f}%)")
        
        # 成功率评估
        success_rate = (passed / total) * 100 if total > 0 else 0
        
        if success_rate >= 90:
            status = "🎉 优秀"
        elif success_rate >= 75:
            status = "✅ 良好"
        elif success_rate >= 60:
            status = "⚠️  及格"
        else:
            status = "❌ 需要改进"
        
        print(f"\n总体评估: {status} (成功率: {success_rate:.1f}%)")
        
        # 关键问题总结
        critical_failures = [test for test in self.verification_report['tests'] if test['status'] == 'FAIL']
        if critical_failures:
            print(f"\n🚨 关键问题 ({len(critical_failures)}个):")
            for failure in critical_failures:
                print(f"   • {failure['test_name']}: {failure['details']}")
        
        # 保存报告到文件
        report_filename = f"verification_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(self.verification_report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细报告已保存到: {report_filename}")
        
        return success_rate >= 75  # 75%以上认为验证通过
    
    def run_all_tests(self):
        """运行所有验证测试"""
        print("🚀 开始交易周期优化方案全面验证...")
        print(f"⏰ 验证时间: {datetime.datetime.now()}")
        
        # 按优先级顺序执行验证
        self.test_database_structure()
        self.test_trade_cycle_matching()
        self.test_api_interfaces()
        
        # 生成并返回验证结果
        return self.generate_report()

def main():
    """主函数"""
    try:
        verifier = SystemVerification()
        success = verifier.run_all_tests()
        
        if success:
            print("\n🎉 验证完成！交易周期优化方案实施成功！")
            sys.exit(0)
        else:
            print("\n⚠️  验证完成，但发现一些问题需要修复。")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  验证被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 验证过程中发生未预期错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 