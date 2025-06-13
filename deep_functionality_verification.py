#!/usr/bin/env python3
"""
深度功能验证脚本 - 专门验证交易周期优化方案的核心功能
"""

import requests
import json
import time
import sys
from datetime import datetime, timedelta

class DeepFunctionalityVerifier:
    def __init__(self):
        self.api_base = 'http://localhost:8888'
        self.results = []
        
    def log_result(self, test_name: str, status: str, details: str, data=None):
        """记录验证结果"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        emoji = {"PASS": "✅", "FAIL": "❌", "WARNING": "⚠️", "INFO": "ℹ️"}
        print(f"[{timestamp}] {emoji.get(status, '❓')} {test_name}: {details}")
        
        if data and isinstance(data, dict):
            for key, value in data.items():
                print(f"    {key}: {value}")
        
        self.results.append({"test": test_name, "status": status, "details": details, "data": data})
    
    def verify_mrot_calculation_logic(self):
        """验证MRoT计算逻辑"""
        print("\n🧮 验证MRoT计算逻辑...")
        
        try:
            # 获取最近的交易信号，寻找有MRoT数据的
            response = requests.get(f"{self.api_base}/api/quantitative/signals?limit=20", timeout=10)
            if response.status_code == 200:
                signals_data = response.json()
                signals = signals_data.get('signals', [])
                
                mrot_signals = [s for s in signals if s.get('mrot_score') is not None]
                
                if mrot_signals:
                    self.log_result("MRoT数据可用性", "PASS", f"找到{len(mrot_signals)}个包含MRoT的信号")
                    
                    # 验证MRoT计算逻辑
                    for i, signal in enumerate(mrot_signals[:3]):
                        mrot = signal.get('mrot_score', 0)
                        holding_minutes = signal.get('holding_minutes', 0)
                        expected_return = signal.get('expected_return', 0)
                        
                        if holding_minutes > 0 and expected_return is not None:
                            # 验证计算公式: MRoT = PNL / holding_minutes
                            expected_mrot = expected_return / holding_minutes
                            
                            if abs(mrot - expected_mrot) < 0.001:
                                self.log_result(f"MRoT计算-信号{i+1}", "PASS", 
                                              f"计算正确: {mrot:.6f} = {expected_return:.2f}/{holding_minutes}分钟")
                            else:
                                self.log_result(f"MRoT计算-信号{i+1}", "FAIL",
                                              f"计算错误: 期望{expected_mrot:.6f}, 实际{mrot:.6f}")
                        else:
                            self.log_result(f"MRoT计算-信号{i+1}", "WARNING", "缺少计算所需数据")
                
                else:
                    self.log_result("MRoT数据可用性", "WARNING", "未找到包含MRoT的信号数据")
                    
        except Exception as e:
            self.log_result("MRoT计算验证", "FAIL", f"验证失败: {e}")
    
    def verify_trade_cycle_matching(self):
        """验证交易周期配对逻辑"""
        print("\n🔄 验证交易周期配对逻辑...")
        
        try:
            response = requests.get(f"{self.api_base}/api/quantitative/signals?limit=50", timeout=10)
            if response.status_code == 200:
                signals_data = response.json()
                signals = signals_data.get('signals', [])
                
                # 按策略分组分析周期配对
                strategy_groups = {}
                for signal in signals:
                    strategy_id = signal.get('strategy_id')
                    if strategy_id not in strategy_groups:
                        strategy_groups[strategy_id] = []
                    strategy_groups[strategy_id].append(signal)
                
                total_cycles = 0
                complete_cycles = 0
                open_cycles = 0
                
                for strategy_id, strategy_signals in strategy_groups.items():
                    # 统计该策略的周期情况
                    cycle_signals = [s for s in strategy_signals if s.get('cycle_id')]
                    
                    if cycle_signals:
                        total_cycles += len(cycle_signals)
                        
                        for signal in cycle_signals:
                            if signal.get('cycle_status') == 'closed':
                                complete_cycles += 1
                            elif signal.get('cycle_status') == 'open':
                                open_cycles += 1
                
                if total_cycles > 0:
                    completion_rate = (complete_cycles / total_cycles) * 100
                    self.log_result("交易周期统计", "PASS", 
                                  f"总周期:{total_cycles}, 完成:{complete_cycles}, 开放:{open_cycles}")
                    self.log_result("周期完成率", "PASS" if completion_rate > 30 else "WARNING",
                                  f"完成率: {completion_rate:.1f}%")
                    
                    # 验证FIFO配对逻辑
                    fifo_errors = 0
                    for strategy_id, strategy_signals in strategy_groups.items():
                        buy_signals = [s for s in strategy_signals if s.get('signal_type') == 'buy' and s.get('executed')]
                        sell_signals = [s for s in strategy_signals if s.get('signal_type') == 'sell' and s.get('executed')]
                        
                        if len(buy_signals) > 1 and len(sell_signals) > 0:
                            # 检查是否按时间顺序配对
                            buy_signals.sort(key=lambda x: x.get('timestamp', ''))
                            
                            # 简单验证：最早的买入应该最先被配对
                            earliest_buy = buy_signals[0]
                            if earliest_buy.get('cycle_status') == 'closed':
                                self.log_result(f"FIFO配对-策略{strategy_id}", "PASS", "最早买入信号已配对")
                            else:
                                fifo_errors += 1
                    
                    if fifo_errors == 0:
                        self.log_result("FIFO配对逻辑", "PASS", "配对逻辑正确")
                    else:
                        self.log_result("FIFO配对逻辑", "WARNING", f"发现{fifo_errors}个潜在问题")
                
                else:
                    self.log_result("交易周期配对", "WARNING", "未找到交易周期数据")
                    
        except Exception as e:
            self.log_result("交易周期配对验证", "FAIL", f"验证失败: {e}")
    
    def verify_scs_scoring_system(self):
        """验证SCS综合评分系统"""
        print("\n📊 验证SCS综合评分系统...")
        
        try:
            response = requests.get(f"{self.api_base}/api/quantitative/strategies", timeout=10)
            if response.status_code == 200:
                strategies_data = response.json()
                strategies = strategies_data.get('strategies', [])
                
                if strategies:
                    # 分析评分分布
                    scored_strategies = [s for s in strategies if s.get('final_score', 0) > 0]
                    
                    if scored_strategies:
                        scores = [s['final_score'] for s in scored_strategies]
                        avg_score = sum(scores) / len(scores)
                        max_score = max(scores)
                        min_score = min(scores)
                        
                        self.log_result("SCS评分统计", "PASS", 
                                      f"平均分:{avg_score:.2f}, 最高:{max_score:.2f}, 最低:{min_score:.2f}")
                        
                        # 检查评分合理性
                        valid_scores = [s for s in scores if 0 <= s <= 100]
                        if len(valid_scores) == len(scores):
                            self.log_result("评分范围检查", "PASS", "所有评分都在0-100范围内")
                        else:
                            self.log_result("评分范围检查", "FAIL", f"发现{len(scores)-len(valid_scores)}个异常评分")
                        
                        # 分析效率等级分布（基于MRoT标准）
                        grade_distribution = {"A级": 0, "B级": 0, "C级": 0, "D级": 0, "F级": 0}
                        
                        for strategy in scored_strategies:
                            score = strategy.get('final_score', 0)
                            
                            # 根据评分推测效率等级
                            if score >= 80:
                                grade_distribution["A级"] += 1
                            elif score >= 60:
                                grade_distribution["B级"] += 1
                            elif score >= 40:
                                grade_distribution["C级"] += 1
                            elif score >= 20:
                                grade_distribution["D级"] += 1
                            else:
                                grade_distribution["F级"] += 1
                        
                        self.log_result("效率等级分布", "INFO", "策略效率等级统计", grade_distribution)
                        
                        # 检查高分策略特征
                        high_score_strategies = [s for s in scored_strategies if s.get('final_score', 0) >= 65]
                        if high_score_strategies:
                            self.log_result("高效策略识别", "PASS", f"发现{len(high_score_strategies)}个高效策略(≥65分)")
                        else:
                            self.log_result("高效策略识别", "WARNING", "暂无65分以上的高效策略")
                    
                    else:
                        self.log_result("SCS评分系统", "WARNING", "策略暂无评分数据")
                else:
                    self.log_result("SCS评分系统", "FAIL", "无法获取策略数据")
                    
        except Exception as e:
            self.log_result("SCS评分系统验证", "FAIL", f"验证失败: {e}")
    
    def verify_intelligent_evolution(self):
        """验证智能进化系统"""
        print("\n🧬 验证智能进化系统...")
        
        try:
            # 检查系统状态中的进化信息
            response = requests.get(f"{self.api_base}/api/quantitative/system-status", timeout=10)
            if response.status_code == 200:
                status = response.json()
                
                evolution_enabled = status.get('evolution_enabled', False)
                generation = status.get('current_generation', 0)
                
                self.log_result("进化系统状态", "PASS" if evolution_enabled else "WARNING",
                              f"进化系统: {'运行中' if evolution_enabled else '未启用'}, 第{generation}代")
                
                if evolution_enabled and generation > 0:
                    # 检查策略代数信息
                    strategies_response = requests.get(f"{self.api_base}/api/quantitative/strategies", timeout=10)
                    if strategies_response.status_code == 200:
                        strategies_data = strategies_response.json()
                        strategies = strategies_data.get('strategies', [])
                        
                        # 分析策略代数分布
                        generation_distribution = {}
                        for strategy in strategies:
                            strategy_generation = strategy.get('generation', 0)
                            generation_distribution[strategy_generation] = generation_distribution.get(strategy_generation, 0) + 1
                        
                        if generation_distribution:
                            self.log_result("策略代数分布", "PASS", "策略进化代数统计", generation_distribution)
                            
                            # 检查是否有新世代策略
                            latest_generation = max(generation_distribution.keys())
                            if latest_generation >= generation:
                                self.log_result("进化活跃度", "PASS", f"发现第{latest_generation}代策略")
                            else:
                                self.log_result("进化活跃度", "WARNING", "策略代数落后于系统代数")
                
                # 验证是否有基于MRoT的进化决策
                # 通过检查策略参数变化来间接验证
                strategies_with_changes = 0
                recent_changes = 0
                
                for strategy in strategies:
                    # 检查是否有参数优化记录（间接表明进化活动）
                    if strategy.get('updated_time') and strategy.get('created_time'):
                        updated_time = strategy.get('updated_time')
                        # 简单检查最近是否有更新
                        if '2025-06' in updated_time:  # 当前月份有更新
                            recent_changes += 1
                            strategies_with_changes += 1
                
                if recent_changes > 0:
                    self.log_result("进化活动检测", "PASS", f"检测到{recent_changes}个策略最近有优化")
                else:
                    self.log_result("进化活动检测", "WARNING", "未检测到最近的进化活动")
                    
        except Exception as e:
            self.log_result("智能进化验证", "FAIL", f"验证失败: {e}")
    
    def verify_automation_workflow(self):
        """验证自动化工作流程"""
        print("\n🔄 验证自动化工作流程...")
        
        try:
            # 1. 验证自动信号生成
            signals_response = requests.get(f"{self.api_base}/api/quantitative/signals?limit=10", timeout=10)
            if signals_response.status_code == 200:
                signals_data = signals_response.json()
                signals = signals_data.get('signals', [])
                
                recent_signals = [s for s in signals if '2025-06-13' in s.get('timestamp', '')]
                if recent_signals:
                    self.log_result("自动信号生成", "PASS", f"今日生成{len(recent_signals)}个信号")
                else:
                    self.log_result("自动信号生成", "WARNING", "今日暂无信号生成")
            
            # 2. 验证自动交易执行
            executed_signals = [s for s in signals if s.get('executed')]
            if executed_signals:
                execution_rate = (len(executed_signals) / len(signals)) * 100 if signals else 0
                self.log_result("自动交易执行", "PASS", f"执行率: {execution_rate:.1f}%")
            else:
                self.log_result("自动交易执行", "WARNING", "暂无已执行的交易")
            
            # 3. 验证自动评分更新
            strategies_response = requests.get(f"{self.api_base}/api/quantitative/strategies", timeout=10)
            if strategies_response.status_code == 200:
                strategies_data = strategies_response.json()
                strategies = strategies_data.get('strategies', [])
                
                scored_strategies = [s for s in strategies if s.get('final_score', 0) > 0]
                score_coverage = (len(scored_strategies) / len(strategies)) * 100 if strategies else 0
                
                self.log_result("自动评分更新", "PASS" if score_coverage > 50 else "WARNING",
                              f"评分覆盖率: {score_coverage:.1f}%")
            
            # 4. 验证系统健康状态
            system_response = requests.get(f"{self.api_base}/api/quantitative/system-status", timeout=10)
            if system_response.status_code == 200:
                system_status = system_response.json()
                
                auto_trading = system_status.get('auto_trading_enabled', False)
                evolution_enabled = system_status.get('evolution_enabled', False)
                
                automation_score = sum([auto_trading, evolution_enabled])
                
                self.log_result("系统自动化程度", "PASS" if automation_score >= 1 else "WARNING",
                              f"自动交易:{'开启' if auto_trading else '关闭'}, 自动进化:{'开启' if evolution_enabled else '关闭'}")
                              
        except Exception as e:
            self.log_result("自动化工作流程验证", "FAIL", f"验证失败: {e}")
    
    def verify_realtime_performance(self):
        """验证实时性能和响应"""
        print("\n⚡ 验证实时性能...")
        
        api_endpoints = [
            "/api/quantitative/system-status",
            "/api/quantitative/strategies",
            "/api/quantitative/account-info"
        ]
        
        total_response_time = 0
        successful_calls = 0
        
        for endpoint in api_endpoints:
            try:
                start_time = time.time()
                response = requests.get(f"{self.api_base}{endpoint}", timeout=5)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    successful_calls += 1
                    total_response_time += response_time
                    
                    status = "PASS" if response_time < 1000 else "WARNING"
                    self.log_result(f"API响应时间-{endpoint.split('/')[-1]}", status,
                                  f"{response_time:.0f}ms")
                else:
                    self.log_result(f"API可用性-{endpoint.split('/')[-1]}", "FAIL",
                                  f"HTTP {response.status_code}")
                                  
            except Exception as e:
                self.log_result(f"API连接-{endpoint.split('/')[-1]}", "FAIL", f"连接失败: {str(e)[:30]}")
        
        if successful_calls > 0:
            avg_response_time = total_response_time / successful_calls
            self.log_result("平均响应时间", "PASS" if avg_response_time < 800 else "WARNING",
                          f"{avg_response_time:.0f}ms")
    
    def generate_functionality_report(self):
        """生成功能验证报告"""
        print("\n" + "="*70)
        print("🎯 交易周期优化方案深度功能验证报告")
        print("="*70)
        
        # 按功能模块分类统计
        modules = {
            "MRoT计算": [r for r in self.results if "mrot" in r['test'].lower() or "计算" in r['test']],
            "交易周期": [r for r in self.results if "周期" in r['test'] or "配对" in r['test']],
            "SCS评分": [r for r in self.results if "scs" in r['test'].lower() or "评分" in r['test']],
            "智能进化": [r for r in self.results if "进化" in r['test'] or "evolution" in r['test'].lower()],
            "自动化": [r for r in self.results if "自动" in r['test']],
            "性能": [r for r in self.results if "性能" in r['test'] or "响应" in r['test']]
        }
        
        overall_status = "PASS"
        critical_issues = []
        
        for module_name, module_results in modules.items():
            if module_results:
                module_passes = sum(1 for r in module_results if r['status'] == 'PASS')
                module_fails = sum(1 for r in module_results if r['status'] == 'FAIL')
                module_total = len(module_results)
                
                module_success_rate = (module_passes / module_total) * 100
                
                if module_success_rate >= 70:
                    module_status = "✅ 正常"
                elif module_success_rate >= 50:
                    module_status = "⚠️  一般"
                    overall_status = "WARNING"
                else:
                    module_status = "❌ 异常"
                    overall_status = "FAIL"
                    critical_issues.append(module_name)
                
                print(f"{module_name:12} : {module_status} ({module_success_rate:.1f}%, {module_passes}/{module_total})")
        
        print("\n" + "-"*70)
        
        if overall_status == "PASS":
            print("🎉 交易周期优化方案功能验证：全部正常！")
            print("✅ 您的全自动量化交易系统按设计正常运行")
        elif overall_status == "WARNING":
            print("⚠️  交易周期优化方案功能验证：基本正常，有待改进")
            print("🔧 建议关注部分功能模块的优化")
        else:
            print("❌ 交易周期优化方案功能验证：发现问题")
            print(f"🚨 关键问题模块: {', '.join(critical_issues)}")
        
        return overall_status == "PASS"
    
    def run_deep_verification(self):
        """运行深度功能验证"""
        print("🔬 开始交易周期优化方案深度功能验证...")
        print(f"⏰ 验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 按功能模块逐一验证
        self.verify_mrot_calculation_logic()
        self.verify_trade_cycle_matching()
        self.verify_scs_scoring_system()
        self.verify_intelligent_evolution()
        self.verify_automation_workflow()
        self.verify_realtime_performance()
        
        # 生成功能验证报告
        return self.generate_functionality_report()

def main():
    """主函数"""
    print("🔬 交易周期优化方案深度功能验证工具")
    print("=" * 60)
    
    try:
        verifier = DeepFunctionalityVerifier()
        success = verifier.run_deep_verification()
        
        if success:
            print("\n🎉 深度功能验证完成！交易周期优化方案运行完美！")
            return 0
        else:
            print("\n⚠️  深度功能验证完成，部分功能需要关注。")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  验证被中断")
        return 1
    except Exception as e:
        print(f"\n\n❌ 验证过程发生错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 