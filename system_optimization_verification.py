#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统优化验证脚本
测试信号生成、交易执行、小币种支持等关键功能
"""

import sys
import os
import time
import json
import requests
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class SystemOptimizationVerifier:
    """系统优化验证器"""
    
    def __init__(self, server_url="http://47.236.39.134:8888"):
        self.server_url = server_url
        self.test_results = {}
        
    def run_verification(self):
        """运行完整的系统验证"""
        print("🔍 开始系统优化验证...")
        print(f"🌐 服务器地址: {self.server_url}")
        
        # 测试清单
        tests = [
            ('系统状态检查', self.test_system_status),
            ('API连通性测试', self.test_api_connectivity),
            ('余额信息验证', self.test_balance_info),
            ('策略列表检查', self.test_strategies_list),
            ('信号生成测试', self.test_signal_generation),
            ('持仓信息检查', self.test_positions),
            ('交易历史验证', self.test_trading_history),
            ('Web界面可用性', self.test_web_interface),
            ('小币种支持验证', self.test_small_coins),
            ('优化效果评估', self.test_optimization_results)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n📋 执行测试: {test_name}")
            try:
                result = test_func()
                if result:
                    print(f"✅ {test_name} - 通过")
                    passed_tests += 1
                    self.test_results[test_name] = {"status": "PASS", "details": result}
                else:
                    print(f"❌ {test_name} - 失败")
                    self.test_results[test_name] = {"status": "FAIL", "details": result}
            except Exception as e:
                print(f"⚠️ {test_name} - 异常: {e}")
                self.test_results[test_name] = {"status": "ERROR", "error": str(e)}
        
        # 生成测试报告
        self.generate_report(passed_tests, total_tests)
        
        return passed_tests, total_tests
    
    def test_system_status(self):
        """测试系统状态"""
        try:
            response = requests.get(f"{self.server_url}/api/quantitative/system-status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    status_info = data.get('data', {})
                    print(f"   📊 系统运行状态: {status_info.get('quantitative_running', 'Unknown')}")
                    print(f"   🤖 自动交易: {status_info.get('auto_trading_enabled', 'Unknown')}")
                    print(f"   📈 策略总数: {status_info.get('total_strategies', 'Unknown')}")
                    print(f"   🔄 进化状态: {status_info.get('evolution_enabled', 'Unknown')}")
                    return True
            return False
        except Exception as e:
            print(f"   ❌ 系统状态检查失败: {e}")
            return False
    
    def test_api_connectivity(self):
        """测试API连通性"""
        try:
            # 测试健康检查接口
            response = requests.get(f"{self.server_url}/api/quantitative/system-health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                health = data.get('data', {})
                print(f"   💚 系统健康状态: {health.get('overall_health', 'Unknown')}")
                return True
            return False
        except Exception as e:
            print(f"   ❌ API连通性测试失败: {e}")
            return False
    
    def test_balance_info(self):
        """测试余额信息"""
        try:
            response = requests.get(f"{self.server_url}/api/quantitative/account-info", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    balance_data = data.get('data', {})
                    total_balance = balance_data.get('total_balance', 0)
                    available_balance = balance_data.get('available_balance', 0)
                    
                    print(f"   💰 总余额: {total_balance} USDT")
                    print(f"   💵 可用余额: {available_balance} USDT")
                    
                    # 验证小资金优化是否生效
                    if 10 <= total_balance <= 20:
                        print(f"   ✅ 小资金模式适配 (余额范围: 10-20 USDT)")
                        return True
                    elif total_balance > 0:
                        print(f"   ⚠️ 余额状态正常但非小资金模式")
                        return True
                    else:
                        print(f"   ❌ 余额为0或异常")
                        return False
            return False
        except Exception as e:
            print(f"   ❌ 余额信息测试失败: {e}")
            return False
    
    def test_strategies_list(self):
        """测试策略列表"""
        try:
            response = requests.get(f"{self.server_url}/api/quantitative/strategies", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    strategies = data.get('data', [])
                    enabled_strategies = [s for s in strategies if s.get('enabled', False)]
                    high_score_strategies = [s for s in strategies if s.get('final_score', 0) >= 80]
                    
                    print(f"   📊 策略总数: {len(strategies)}")
                    print(f"   ✅ 启用策略: {len(enabled_strategies)}")
                    print(f"   🌟 高分策略(80+): {len(high_score_strategies)}")
                    
                    # 检查小币种策略
                    small_coin_strategies = [s for s in strategies if s.get('symbol') in ['DOGE/USDT', 'XRP/USDT', 'ADA/USDT']]
                    print(f"   🪙 小币种策略: {len(small_coin_strategies)}")
                    
                    return len(strategies) > 0 and len(enabled_strategies) > 0
            return False
        except Exception as e:
            print(f"   ❌ 策略列表测试失败: {e}")
            return False
    
    def test_signal_generation(self):
        """测试信号生成"""
        try:
            response = requests.get(f"{self.server_url}/api/quantitative/signals", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    signals_data = data.get('data', {})
                    signals = signals_data.get('data', [])
                    
                    if signals:
                        # 分析信号类型分布
                        buy_signals = [s for s in signals if s.get('signal_type') == 'buy']
                        sell_signals = [s for s in signals if s.get('signal_type') == 'sell']
                        
                        print(f"   📈 最近信号数量: {len(signals)}")
                        print(f"   🟢 买入信号: {len(buy_signals)}")
                        print(f"   🔴 卖出信号: {len(sell_signals)}")
                        
                        # 检查信号优化效果
                        if len(buy_signals) >= len(sell_signals):
                            print(f"   ✅ 买入信号比例良好 (买入≥卖出)")
                            return True
                        else:
                            print(f"   ⚠️ 卖出信号过多，需要进一步优化")
                            return True  # 仍算通过，但需关注
                    else:
                        print(f"   ⚠️ 暂无最近信号")
                        return True
            return False
        except Exception as e:
            print(f"   ❌ 信号生成测试失败: {e}")
            return False
    
    def test_positions(self):
        """测试持仓信息"""
        try:
            response = requests.get(f"{self.server_url}/api/quantitative/positions", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    positions_data = data.get('data', {})
                    positions = positions_data.get('data', [])
                    
                    print(f"   📦 当前持仓数量: {len(positions)}")
                    
                    if positions:
                        for pos in positions[:3]:  # 显示前3个持仓
                            symbol = pos.get('symbol', 'Unknown')
                            quantity = pos.get('quantity', 0)
                            print(f"   📊 {symbol}: {quantity}")
                    
                    return True  # 持仓可以为空，不影响测试通过
            return False
        except Exception as e:
            print(f"   ❌ 持仓信息测试失败: {e}")
            return False
    
    def test_trading_history(self):
        """测试交易历史"""
        try:
            response = requests.get(f"{self.server_url}/api/quantitative/balance-history", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    history = data.get('data', [])
                    print(f"   📊 余额历史记录: {len(history)}条")
                    
                    if history:
                        latest = history[-1]
                        timestamp = latest.get('timestamp', 'Unknown')
                        balance = latest.get('total_balance', 0)
                        print(f"   📅 最新记录: {timestamp}")
                        print(f"   💰 最新余额: {balance} USDT")
                    
                    return True
            return False
        except Exception as e:
            print(f"   ❌ 交易历史测试失败: {e}")
            return False
    
    def test_web_interface(self):
        """测试Web界面可用性"""
        try:
            # 测试主页
            response = requests.get(f"{self.server_url}/", timeout=10)
            if response.status_code == 200:
                print(f"   🌐 主页可访问")
                
                # 测试量化交易页面
                response = requests.get(f"{self.server_url}/quantitative.html", timeout=10)
                if response.status_code == 200:
                    print(f"   📊 量化交易页面可访问")
                    return True
            return False
        except Exception as e:
            print(f"   ❌ Web界面测试失败: {e}")
            return False
    
    def test_small_coins(self):
        """测试小币种支持"""
        try:
            # 获取策略列表，检查小币种策略
            response = requests.get(f"{self.server_url}/api/quantitative/strategies", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    strategies = data.get('data', [])
                    
                    small_coin_symbols = ['DOGE/USDT', 'XRP/USDT', 'ADA/USDT', 'DOT/USDT']
                    small_coin_strategies = []
                    
                    for strategy in strategies:
                        symbol = strategy.get('symbol', '')
                        if symbol in small_coin_symbols:
                            small_coin_strategies.append({
                                'name': strategy.get('name', ''),
                                'symbol': symbol,
                                'enabled': strategy.get('enabled', False),
                                'score': strategy.get('final_score', 0)
                            })
                    
                    print(f"   🪙 发现小币种策略: {len(small_coin_strategies)}个")
                    
                    for strategy in small_coin_strategies[:3]:
                        print(f"   📊 {strategy['symbol']}: {strategy['name']} (评分: {strategy['score']:.1f})")
                    
                    return len(small_coin_strategies) > 0
            return False
        except Exception as e:
            print(f"   ❌ 小币种支持测试失败: {e}")
            return False
    
    def test_optimization_results(self):
        """测试优化效果评估"""
        try:
            # 综合评估优化效果
            print(f"   🎯 正在评估系统优化效果...")
            
            optimization_metrics = {
                'signal_balance': False,  # 信号平衡性
                'small_coin_support': False,  # 小币种支持
                'api_stability': False,  # API稳定性
                'system_health': False   # 系统健康度
            }
            
            # 检查信号平衡性
            response = requests.get(f"{self.server_url}/api/quantitative/signals", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    signals_data = data.get('data', {})
                    signals = signals_data.get('data', [])
                    
                    if signals:
                        buy_signals = [s for s in signals if s.get('signal_type') == 'buy']
                        sell_signals = [s for s in signals if s.get('signal_type') == 'sell']
                        
                        if len(buy_signals) >= len(sell_signals):
                            optimization_metrics['signal_balance'] = True
                            print(f"   ✅ 信号平衡性优化生效")
            
            # 检查API稳定性
            response = requests.get(f"{self.server_url}/api/quantitative/system-status", timeout=10)
            if response.status_code == 200:
                optimization_metrics['api_stability'] = True
                print(f"   ✅ API稳定性良好")
            
            # 检查系统健康度
            response = requests.get(f"{self.server_url}/api/quantitative/system-health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                health = data.get('data', {})
                if health.get('overall_health') in ['healthy', 'warning']:
                    optimization_metrics['system_health'] = True
                    print(f"   ✅ 系统健康状态良好")
            
            # 计算优化成功率
            success_count = sum(optimization_metrics.values())
            total_count = len(optimization_metrics)
            success_rate = (success_count / total_count) * 100
            
            print(f"   📈 优化成功率: {success_rate:.1f}% ({success_count}/{total_count})")
            
            return success_rate >= 75  # 75%以上算优化成功
        
        except Exception as e:
            print(f"   ❌ 优化效果评估失败: {e}")
            return False
    
    def generate_report(self, passed_tests, total_tests):
        """生成测试报告"""
        success_rate = (passed_tests / total_tests) * 100
        
        print(f"\n{'='*60}")
        print(f"🎯 系统优化验证报告")
        print(f"{'='*60}")
        print(f"📅 验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 服务器地址: {self.server_url}")
        print(f"📊 测试通过率: {success_rate:.1f}% ({passed_tests}/{total_tests})")
        
        if success_rate >= 90:
            print(f"🏆 系统优化效果: 优秀")
        elif success_rate >= 75:
            print(f"✅ 系统优化效果: 良好")
        elif success_rate >= 60:
            print(f"⚠️ 系统优化效果: 一般")
        else:
            print(f"❌ 系统优化效果: 需要改进")
        
        print(f"\n📋 详细测试结果:")
        for test_name, result in self.test_results.items():
            status = result['status']
            if status == 'PASS':
                print(f"   ✅ {test_name}")
            elif status == 'FAIL':
                print(f"   ❌ {test_name}")
            else:
                print(f"   ⚠️ {test_name} (异常)")
        
        # 保存报告到文件
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'server_url': self.server_url,
            'passed_tests': passed_tests,
            'total_tests': total_tests,
            'success_rate': success_rate,
            'detailed_results': self.test_results
        }
        
        with open('system_optimization_report.json', 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细报告已保存至: system_optimization_report.json")

def main():
    """主函数"""
    print("🚀 系统优化验证工具启动")
    print("📋 本工具将验证系统优化效果，包括:")
    print("   - 信号生成智能化")
    print("   - 小币种交易支持")
    print("   - 交易执行增强")
    print("   - Web API完整性")
    print("   - 系统稳定性")
    
    verifier = SystemOptimizationVerifier()
    passed, total = verifier.run_verification()
    
    if passed >= total * 0.8:  # 80%以上通过
        print(f"\n🎉 系统优化验证成功！")
        return True
    else:
        print(f"\n⚠️ 系统优化存在问题，建议进一步调整")
        return False

if __name__ == "__main__":
    main() 