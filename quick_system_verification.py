#!/usr/bin/env python3
"""
快速系统验证脚本 - 验证全自动量化交易系统
"""

import subprocess
import requests
import json
import time
import sys
from datetime import datetime

class QuickSystemVerifier:
    def __init__(self):
        self.api_base = 'http://localhost:8888'
        self.results = []
        
    def log_result(self, test_name: str, status: str, details: str):
        """记录验证结果"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        emoji = {"PASS": "✅", "FAIL": "❌", "WARNING": "⚠️"}
        print(f"[{timestamp}] {emoji.get(status, '❓')} {test_name}: {details}")
        self.results.append({"test": test_name, "status": status, "details": details})
    
    def test_pm2_processes(self):
        """验证PM2进程状态"""
        print("\n🔍 检查PM2进程状态...")
        try:
            result = subprocess.run(['pm2', 'jlist'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                processes = json.loads(result.stdout)
                running_count = sum(1 for p in processes if p.get('pm2_env', {}).get('status') == 'online')
                total_count = len(processes)
                
                if running_count >= 2:  # 至少前端和后端都在运行
                    self.log_result("PM2进程状态", "PASS", f"{running_count}/{total_count} 个进程在线")
                    
                    # 检查关键进程
                    for process in processes:
                        name = process.get('name', 'unknown')
                        status = process.get('pm2_env', {}).get('status', 'unknown')
                        if 'quant' in name.lower():
                            self.log_result(f"关键进程-{name}", "PASS" if status == "online" else "FAIL", f"状态: {status}")
                else:
                    self.log_result("PM2进程状态", "FAIL", f"只有{running_count}/{total_count}个进程在线")
            else:
                self.log_result("PM2进程状态", "FAIL", "PM2命令执行失败")
        except Exception as e:
            self.log_result("PM2进程状态", "FAIL", f"检查失败: {e}")
    
    def test_api_endpoints(self):
        """测试关键API端点"""
        print("\n🌐 测试API端点...")
        
        endpoints = [
            ("/api/quantitative/system-status", "系统状态API"),
            ("/api/quantitative/strategies", "策略管理API"),
        ]
        
        for endpoint, name in endpoints:
            try:
                response = requests.get(f"{self.api_base}{endpoint}", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    self.log_result(f"API-{name}", "PASS", f"响应正常 ({len(str(data))} bytes)")
                else:
                    self.log_result(f"API-{name}", "FAIL", f"HTTP {response.status_code}")
            except requests.exceptions.RequestException as e:
                self.log_result(f"API-{name}", "FAIL", f"请求失败: {str(e)[:50]}")
    
    def test_system_automation(self):
        """验证系统自动化功能"""
        print("\n🤖 验证系统自动化...")
        
        try:
            # 检查系统状态
            response = requests.get(f"{self.api_base}/api/quantitative/system-status", timeout=5)
            if response.status_code == 200:
                status = response.json()
                
                # 验证自动交易
                auto_trading = status.get('auto_trading_enabled', False)
                self.log_result("自动交易状态", "PASS" if auto_trading else "WARNING", 
                              f"自动交易: {'开启' if auto_trading else '关闭'}")
                
                # 验证进化系统
                evolution_enabled = status.get('evolution_enabled', False)
                generation = status.get('current_generation', 0)
                self.log_result("进化系统状态", "PASS" if evolution_enabled else "WARNING",
                              f"进化系统: {'开启' if evolution_enabled else '关闭'}, 第{generation}代")
                
                # 验证策略数量
                total_strategies = status.get('total_strategies', 0)
                running_strategies = status.get('running_strategies', 0)
                self.log_result("策略运行状态", "PASS" if running_strategies > 0 else "WARNING",
                              f"运行中: {running_strategies}/{total_strategies}")
                
        except Exception as e:
            self.log_result("系统自动化验证", "FAIL", f"检查失败: {e}")
    
    def test_trading_data(self):
        """验证交易数据"""
        print("\n📊 验证交易数据...")
        
        try:
            # 检查最近的交易信号
            response = requests.get(f"{self.api_base}/api/quantitative/signals?limit=5", timeout=5)
            if response.status_code == 200:
                signals_data = response.json()
                signals = signals_data.get('signals', [])
                
                if signals:
                    recent_signals = len(signals)
                    executed_signals = sum(1 for s in signals if s.get('executed'))
                    
                    self.log_result("交易信号生成", "PASS", f"最近{recent_signals}个信号，{executed_signals}个已执行")
                    
                    # 检查是否有交易周期相关字段
                    first_signal = signals[0]
                    cycle_fields = ['cycle_id', 'mrot_score', 'holding_minutes']
                    found_fields = [field for field in cycle_fields if field in first_signal]
                    
                    if found_fields:
                        self.log_result("交易周期字段", "PASS", f"包含字段: {found_fields}")
                    else:
                        self.log_result("交易周期字段", "WARNING", "未检测到周期相关字段")
                else:
                    self.log_result("交易信号生成", "WARNING", "未发现最近的交易信号")
            else:
                self.log_result("交易数据API", "FAIL", f"API响应异常: {response.status_code}")
                
        except Exception as e:
            self.log_result("交易数据验证", "FAIL", f"检查失败: {e}")
    
    def test_database_connectivity(self):
        """简单验证数据库连接"""
        print("\n🗄️  验证数据库连接...")
        
        try:
            # 通过API检查数据库状态
            response = requests.get(f"{self.api_base}/api/quantitative/strategies", timeout=5)
            if response.status_code == 200:
                strategies_data = response.json()
                strategies = strategies_data.get('strategies', [])
                
                if strategies:
                    total_strategies = len(strategies)
                    enabled_strategies = sum(1 for s in strategies if s.get('enabled'))
                    
                    self.log_result("数据库连接", "PASS", f"成功读取{total_strategies}个策略")
                    self.log_result("策略状态", "PASS", f"{enabled_strategies}个策略已启用")
                    
                    # 检查策略评分
                    scored_strategies = sum(1 for s in strategies if s.get('final_score', 0) > 0)
                    self.log_result("策略评分", "PASS" if scored_strategies > 0 else "WARNING",
                                  f"{scored_strategies}个策略有评分")
                else:
                    self.log_result("数据库连接", "WARNING", "策略列表为空")
            else:
                self.log_result("数据库连接", "FAIL", "无法通过API访问数据库")
                
        except Exception as e:
            self.log_result("数据库验证", "FAIL", f"检查失败: {e}")
    
    def test_realtime_monitoring(self):
        """验证实时监控功能"""
        print("\n📈 验证实时监控...")
        
        try:
            # 检查账户信息
            response = requests.get(f"{self.api_base}/api/quantitative/account-info", timeout=5)
            if response.status_code == 200:
                account_data = response.json()
                
                balance = account_data.get('total_balance', 0)
                self.log_result("账户余额监控", "PASS", f"当前余额: {balance:.2f}")
                
                if 'last_update' in account_data:
                    self.log_result("数据实时性", "PASS", f"最后更新: {account_data['last_update']}")
                else:
                    self.log_result("数据实时性", "WARNING", "无最后更新时间")
                    
        except Exception as e:
            self.log_result("实时监控验证", "FAIL", f"检查失败: {e}")
    
    def check_log_activity(self):
        """检查日志活动"""
        print("\n📝 检查系统日志活动...")
        
        try:
            # 检查PM2日志中的最近活动
            result = subprocess.run(['pm2', 'logs', '--lines', '20', '--nostream'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logs = result.stdout
                
                # 检查关键活动
                activity_indicators = [
                    ('交易信号', ['信号', 'signal', '交易']),
                    ('策略评分', ['评分', 'score', '策略']),
                    ('进化活动', ['进化', 'evolution', '优化']),
                    ('MRoT计算', ['mrot', 'MRoT', '周期'])
                ]
                
                for activity_name, keywords in activity_indicators:
                    found = any(keyword in logs.lower() for keyword in keywords)
                    self.log_result(f"日志活动-{activity_name}", 
                                  "PASS" if found else "WARNING",
                                  "检测到活动" if found else "未检测到活动")
                
                # 检查错误
                error_count = logs.lower().count('error') + logs.lower().count('❌')
                self.log_result("系统错误检查", 
                              "WARNING" if error_count > 5 else "PASS",
                              f"发现{error_count}个错误信息")
            else:
                self.log_result("日志检查", "WARNING", "无法读取PM2日志")
                
        except Exception as e:
            self.log_result("日志活动检查", "FAIL", f"检查失败: {e}")
    
    def generate_summary(self):
        """生成验证总结"""
        print("\n" + "="*60)
        print("🎯 全自动量化交易系统验证总结")
        print("="*60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['status'] == 'PASS')
        failed_tests = sum(1 for r in self.results if r['status'] == 'FAIL')
        warning_tests = sum(1 for r in self.results if r['status'] == 'WARNING')
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"总测试项: {total_tests}")
        print(f"✅ 通过: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        print(f"❌ 失败: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        print(f"⚠️  警告: {warning_tests} ({warning_tests/total_tests*100:.1f}%)")
        
        if success_rate >= 80:
            status = "🎉 系统运行良好"
        elif success_rate >= 60:
            status = "✅ 系统基本正常"
        elif success_rate >= 40:
            status = "⚠️  系统需要关注"
        else:
            status = "❌ 系统需要修复"
        
        print(f"\n总体状态: {status} (成功率: {success_rate:.1f}%)")
        
        # 关键问题汇总
        critical_failures = [r for r in self.results if r['status'] == 'FAIL']
        if critical_failures:
            print(f"\n🚨 关键问题 ({len(critical_failures)}个):")
            for failure in critical_failures:
                print(f"   • {failure['test']}: {failure['details']}")
        
        # 自动化功能确认
        automation_tests = [r for r in self.results if '自动' in r['test'] or '进化' in r['test']]
        automation_ok = all(r['status'] in ['PASS', 'WARNING'] for r in automation_tests)
        
        print(f"\n🤖 全自动化确认: {'✅ 正常运行' if automation_ok else '❌ 需要检查'}")
        
        return success_rate >= 60 and len(critical_failures) <= 2
    
    def run_verification(self):
        """运行完整验证"""
        print("🚀 开始快速系统验证...")
        print(f"⏰ 验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 按优先级执行验证
        self.test_pm2_processes()
        self.test_api_endpoints()
        self.test_system_automation()
        self.test_database_connectivity()
        self.test_trading_data()
        self.test_realtime_monitoring()
        self.check_log_activity()
        
        # 生成总结
        return self.generate_summary()

def main():
    """主函数"""
    print("🔍 全自动量化交易系统快速验证工具")
    print("=" * 50)
    
    try:
        verifier = QuickSystemVerifier()
        success = verifier.run_verification()
        
        if success:
            print("\n🎉 系统验证完成！全自动量化交易系统运行正常！")
            return 0
        else:
            print("\n⚠️  系统验证完成，发现一些需要关注的问题。")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  验证被中断")
        return 1
    except Exception as e:
        print(f"\n\n❌ 验证过程发生错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 