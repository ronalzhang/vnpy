#!/usr/bin/env python3
"""
🔍 全自动量化交易系统综合验证脚本
验证所有功能是否完善并正常工作
"""

import os
import re
import requests
import json
import time
from datetime import datetime
import subprocess

class QuantitativeSystemVerifier:
    def __init__(self):
        self.base_url = "http://47.236.39.134:8888"  # 服务器地址
        self.verification_results = {}
        self.overall_score = 0
        self.total_checks = 0
        
    def run_comprehensive_verification(self):
        """运行全面验证"""
        print("🔍 开始全面验证全自动量化交易系统...")
        print("=" * 60)
        
        # 1. 代码质量验证
        self.verify_code_quality()
        
        # 2. 服务器连接验证  
        self.verify_server_connection()
        
        # 3. 系统状态验证
        self.verify_system_status()
        
        # 4. 策略配置验证
        self.verify_strategy_configuration()
        
        # 5. 自动交易控制验证
        self.verify_auto_trading_control()
        
        # 6. 参数优化机制验证
        self.verify_parameter_optimization()
        
        # 7. 策略进化系统验证
        self.verify_evolution_system()
        
        # 8. 前端功能验证
        self.verify_frontend_functionality()
        
        # 生成验证报告
        self.generate_verification_report()
        
    def verify_code_quality(self):
        """验证代码质量"""
        print("\n🔍 1. 代码质量验证")
        print("-" * 30)
        
        checks = {}
        
        # 1.1 检查旧版本引用是否清理完毕
        print("检查 AutomatedStrategyManager 旧版本引用...")
        with open('quantitative_service.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        old_patterns = [
            'self.quantitative_service.strategies.items()',
            'self.quantitative_service.strategies.get(',
            'self.quantitative_service.strategies.keys()',
            'self.quantitative_service.strategies.values()'
        ]
        
        found_old_refs = []
        for pattern in old_patterns:
            if pattern in content:
                found_old_refs.append(pattern)
        
        if not found_old_refs:
            checks['old_version_cleanup'] = {"status": "✅", "message": "所有旧版本引用已清理"}
        else:
            checks['old_version_cleanup'] = {"status": "❌", "message": f"仍有旧版本引用: {found_old_refs}"}
        
        # 1.2 检查策略参数模板
        print("检查策略参数模板配置...")
        template_count = content.count("'param_ranges': {")
        if template_count >= 6:
            checks['strategy_templates'] = {"status": "✅", "message": f"策略模板配置完善({template_count}种策略)"}
        else:
            checks['strategy_templates'] = {"status": "❌", "message": f"策略模板不足({template_count}种)"}
        
        # 1.3 检查参数优化方法
        print("检查参数优化机制...")
        optimization_methods = [
            '_moderate_parameter_optimization',
            '_fine_tune_high_score_strategy', 
            '_preserve_elite_strategy'
        ]
        
        missing_methods = []
        for method in optimization_methods:
            if method not in content:
                missing_methods.append(method)
        
        if not missing_methods:
            checks['parameter_optimization'] = {"status": "✅", "message": "参数优化机制完善"}
        else:
            checks['parameter_optimization'] = {"status": "❌", "message": f"缺少优化方法: {missing_methods}"}
        
        # 1.4 检查系统状态异常处理
        print("检查系统状态异常处理...")
        if "'system_health': 'offline'" in content and "system_health='error'" not in content:
            checks['exception_handling'] = {"status": "✅", "message": "异常处理已修复"}
        else:
            checks['exception_handling'] = {"status": "❌", "message": "异常处理修复不完整"}
        
        self.verification_results['code_quality'] = checks
        self._update_score(checks)
        
    def verify_server_connection(self):
        """验证服务器连接"""
        print("\n🔍 2. 服务器连接验证")
        print("-" * 30)
        
        checks = {}
        
        try:
            response = requests.get(f"{self.base_url}/quantitative.html", timeout=10)
            if response.status_code == 200:
                checks['server_connection'] = {"status": "✅", "message": "服务器连接正常"}
            else:
                checks['server_connection'] = {"status": "❌", "message": f"服务器返回状态码: {response.status_code}"}
        except Exception as e:
            checks['server_connection'] = {"status": "❌", "message": f"连接失败: {str(e)}"}
        
        self.verification_results['server_connection'] = checks
        self._update_score(checks)
        
    def verify_system_status(self):
        """验证系统状态API"""
        print("\n🔍 3. 系统状态验证")
        print("-" * 30)
        
        checks = {}
        
        try:
            response = requests.get(f"{self.base_url}/api/quantitative/system-status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # 检查返回格式
                required_fields = ['success', 'running', 'auto_trading_enabled', 'system_health']
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    checks['status_api_format'] = {"status": "✅", "message": "系统状态API格式正确"}
                    
                    # 检查系统是否运行
                    if data.get('success') and data.get('running'):
                        checks['system_running'] = {"status": "✅", "message": "量化系统正在运行"}
                    else:
                        checks['system_running'] = {"status": "⚠️", "message": "量化系统未运行"}
                        
                    # 检查自动交易状态
                    if 'auto_trading_enabled' in data:
                        status = "已开启" if data['auto_trading_enabled'] else "已关闭"
                        checks['auto_trading_status'] = {"status": "✅", "message": f"自动交易{status}"}
                    else:
                        checks['auto_trading_status'] = {"status": "❌", "message": "自动交易状态缺失"}
                        
                else:
                    checks['status_api_format'] = {"status": "❌", "message": f"API格式缺少字段: {missing_fields}"}
            else:
                checks['status_api_format'] = {"status": "❌", "message": f"API返回错误: {response.status_code}"}
                
        except Exception as e:
            checks['status_api_format'] = {"status": "❌", "message": f"API请求失败: {str(e)}"}
        
        self.verification_results['system_status'] = checks
        self._update_score(checks)
        
    def verify_strategy_configuration(self):
        """验证策略配置"""
        print("\n🔍 4. 策略配置验证")
        print("-" * 30)
        
        checks = {}
        
        try:
            response = requests.get(f"{self.base_url}/api/quantitative/strategies", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success') and 'data' in data:
                    strategies = data['data']
                    checks['strategies_loading'] = {"status": "✅", "message": f"成功加载{len(strategies)}个策略"}
                    
                    # 检查策略参数丰富度
                    param_counts = []
                    for strategy in strategies:
                        params = strategy.get('parameters', {})
                        param_counts.append(len(params))
                    
                    avg_params = sum(param_counts) / len(param_counts) if param_counts else 0
                    if avg_params >= 8:  # 期望每个策略至少8个参数
                        checks['strategy_parameters'] = {"status": "✅", "message": f"策略参数丰富(平均{avg_params:.1f}个参数)"}
                    else:
                        checks['strategy_parameters'] = {"status": "⚠️", "message": f"策略参数偏少(平均{avg_params:.1f}个参数)"}
                        
                    # 检查策略评分
                    scored_strategies = [s for s in strategies if s.get('final_score', 0) > 0]
                    if scored_strategies:
                        avg_score = sum(s.get('final_score', 0) for s in scored_strategies) / len(scored_strategies)
                        checks['strategy_scoring'] = {"status": "✅", "message": f"{len(scored_strategies)}个策略有评分(平均{avg_score:.1f}分)"}
                    else:
                        checks['strategy_scoring'] = {"status": "⚠️", "message": "暂无策略评分数据"}
                        
                else:
                    checks['strategies_loading'] = {"status": "❌", "message": "策略加载失败"}
            else:
                checks['strategies_loading'] = {"status": "❌", "message": f"策略API错误: {response.status_code}"}
                
        except Exception as e:
            checks['strategies_loading'] = {"status": "❌", "message": f"策略验证失败: {str(e)}"}
        
        self.verification_results['strategy_configuration'] = checks
        self._update_score(checks)
        
    def verify_auto_trading_control(self):
        """验证自动交易控制"""
        print("\n🔍 5. 自动交易控制验证")
        print("-" * 30)
        
        checks = {}
        
        try:
            # 获取当前自动交易状态
            response = requests.get(f"{self.base_url}/api/quantitative/auto-trading", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    current_status = data.get('enabled', False)
                    checks['auto_trading_api'] = {"status": "✅", "message": f"自动交易API正常(当前{'已开启' if current_status else '已关闭'})"}
                    
                    # 测试开启自动交易
                    toggle_response = requests.post(
                        f"{self.base_url}/api/quantitative/auto-trading",
                        json={'enabled': not current_status},
                        timeout=10
                    )
                    
                    if toggle_response.status_code == 200:
                        toggle_data = toggle_response.json()
                        if toggle_data.get('success'):
                            checks['auto_trading_toggle'] = {"status": "✅", "message": "自动交易开关功能正常"}
                            
                            # 恢复原状态
                            requests.post(
                                f"{self.base_url}/api/quantitative/auto-trading",
                                json={'enabled': current_status},
                                timeout=10
                            )
                        else:
                            checks['auto_trading_toggle'] = {"status": "❌", "message": "自动交易开关失败"}
                    else:
                        checks['auto_trading_toggle'] = {"status": "❌", "message": f"开关API错误: {toggle_response.status_code}"}
                        
                else:
                    checks['auto_trading_api'] = {"status": "❌", "message": "自动交易API返回失败"}
            else:
                checks['auto_trading_api'] = {"status": "❌", "message": f"自动交易API错误: {response.status_code}"}
                
        except Exception as e:
            checks['auto_trading_api'] = {"status": "❌", "message": f"自动交易验证失败: {str(e)}"}
        
        self.verification_results['auto_trading_control'] = checks
        self._update_score(checks)
        
    def verify_parameter_optimization(self):
        """验证参数优化机制"""
        print("\n🔍 6. 参数优化机制验证")
        print("-" * 30)
        
        checks = {}
        
        # 检查是否有参数优化日志
        try:
            response = requests.get(f"{self.base_url}/api/quantitative/strategies", timeout=10)
            if response.status_code == 200:
                data = response.json()
                strategies = data.get('data', [])
                
                if strategies:
                    # 检查第一个策略的优化日志
                    strategy_id = strategies[0].get('id')
                    opt_response = requests.get(
                        f"{self.base_url}/api/quantitative/strategies/{strategy_id}/optimization-logs",
                        timeout=10
                    )
                    
                    if opt_response.status_code == 200:
                        opt_data = opt_response.json()
                        if opt_data.get('success'):
                            logs = opt_data.get('data', [])
                            checks['optimization_logs'] = {"status": "✅", "message": f"参数优化日志正常({len(logs)}条记录)"}
                        else:
                            checks['optimization_logs'] = {"status": "⚠️", "message": "参数优化日志为空"}
                    else:
                        checks['optimization_logs'] = {"status": "❌", "message": f"优化日志API错误: {opt_response.status_code}"}
                        
                    # 检查策略参数复杂度
                    complex_strategies = 0
                    for strategy in strategies:
                        params = strategy.get('parameters', {})
                        if len(params) >= 8:  # 复杂策略应该有8+个参数
                            complex_strategies += 1
                    
                    complexity_ratio = complex_strategies / len(strategies) if strategies else 0
                    if complexity_ratio >= 0.8:  # 80%的策略应该是复杂的
                        checks['parameter_complexity'] = {"status": "✅", "message": f"策略参数复杂度良好({complexity_ratio*100:.1f}%)"}
                    else:
                        checks['parameter_complexity'] = {"status": "⚠️", "message": f"策略参数有待优化({complexity_ratio*100:.1f}%)"}
                        
                else:
                    checks['optimization_logs'] = {"status": "❌", "message": "无策略数据"}
                    
        except Exception as e:
            checks['optimization_logs'] = {"status": "❌", "message": f"参数优化验证失败: {str(e)}"}
        
        self.verification_results['parameter_optimization'] = checks
        self._update_score(checks)
        
    def verify_evolution_system(self):
        """验证策略进化系统"""
        print("\n🔍 7. 策略进化系统验证")
        print("-" * 30)
        
        checks = {}
        
        try:
            response = requests.get(f"{self.base_url}/api/quantitative/evolution/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    evolution_data = data.get('data', {})
                    
                    # 检查进化状态
                    if evolution_data.get('evolution_enabled'):
                        checks['evolution_enabled'] = {"status": "✅", "message": "策略进化已启用"}
                    else:
                        checks['evolution_enabled'] = {"status": "⚠️", "message": "策略进化未启用"}
                    
                    # 检查进化历史
                    generation = evolution_data.get('current_generation', 0)
                    if generation > 0:
                        checks['evolution_history'] = {"status": "✅", "message": f"已进化{generation}代"}
                    else:
                        checks['evolution_history'] = {"status": "⚠️", "message": "暂无进化历史"}
                        
                    # 检查下次进化时间
                    next_time = evolution_data.get('next_evolution_time')
                    if next_time:
                        checks['evolution_schedule'] = {"status": "✅", "message": f"下次进化: {next_time}"}
                    else:
                        checks['evolution_schedule'] = {"status": "⚠️", "message": "进化时间未设置"}
                        
                else:
                    checks['evolution_enabled'] = {"status": "❌", "message": "进化状态API返回失败"}
            else:
                checks['evolution_enabled'] = {"status": "❌", "message": f"进化API错误: {response.status_code}"}
                
        except Exception as e:
            checks['evolution_enabled'] = {"status": "❌", "message": f"进化系统验证失败: {str(e)}"}
        
        self.verification_results['evolution_system'] = checks
        self._update_score(checks)
        
    def verify_frontend_functionality(self):
        """验证前端功能"""
        print("\n🔍 8. 前端功能验证")
        print("-" * 30)
        
        checks = {}
        
        try:
            # 检查量化页面加载
            response = requests.get(f"{self.base_url}/quantitative.html", timeout=10)
            if response.status_code == 200:
                content = response.text
                
                # 检查关键元素
                if 'quantitative.js' in content:
                    checks['frontend_loading'] = {"status": "✅", "message": "前端页面加载正常"}
                else:
                    checks['frontend_loading'] = {"status": "❌", "message": "前端资源缺失"}
                
                # 检查是否有错误提示
                if 'error' not in content.lower():
                    checks['frontend_errors'] = {"status": "✅", "message": "前端无明显错误"}
                else:
                    checks['frontend_errors'] = {"status": "⚠️", "message": "前端可能存在错误"}
                    
            else:
                checks['frontend_loading'] = {"status": "❌", "message": f"前端页面错误: {response.status_code}"}
                
        except Exception as e:
            checks['frontend_loading'] = {"status": "❌", "message": f"前端验证失败: {str(e)}"}
        
        self.verification_results['frontend_functionality'] = checks
        self._update_score(checks)
        
    def _update_score(self, checks):
        """更新总分"""
        for check_name, result in checks.items():
            self.total_checks += 1
            if result['status'] == '✅':
                self.overall_score += 1
            elif result['status'] == '⚠️':
                self.overall_score += 0.5
                
    def generate_verification_report(self):
        """生成验证报告"""
        print("\n" + "=" * 60)
        print("📊 全自动量化交易系统验证报告")
        print("=" * 60)
        
        # 计算总体评分
        score_percentage = (self.overall_score / self.total_checks * 100) if self.total_checks > 0 else 0
        
        print(f"\n🎯 总体评分: {self.overall_score:.1f}/{self.total_checks} ({score_percentage:.1f}%)")
        
        if score_percentage >= 90:
            grade = "🏆 优秀"
        elif score_percentage >= 75:
            grade = "⭐ 良好"  
        elif score_percentage >= 60:
            grade = "📈 及格"
        else:
            grade = "❌ 需要改进"
            
        print(f"总体评级: {grade}")
        
        # 详细报告
        print(f"\n📋 详细验证结果:")
        for category, checks in self.verification_results.items():
            print(f"\n{category.replace('_', ' ').title()}:")
            for check_name, result in checks.items():
                print(f"  {result['status']} {check_name}: {result['message']}")
        
        # 保存报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_score': self.overall_score,
            'total_checks': self.total_checks,
            'score_percentage': score_percentage,
            'grade': grade,
            'detailed_results': self.verification_results
        }
        
        with open('verification_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细报告已保存到: verification_report.json")
        
        # 建议
        print(f"\n💡 改进建议:")
        if score_percentage < 100:
            for category, checks in self.verification_results.items():
                failed_checks = [name for name, result in checks.items() if result['status'] in ['❌', '⚠️']]
                if failed_checks:
                    print(f"  • {category}: {', '.join(failed_checks)}")
        else:
            print("  🎉 系统运行完美，无需改进!")
        
        return score_percentage

if __name__ == "__main__":
    verifier = QuantitativeSystemVerifier()
    verifier.run_comprehensive_verification()
    
    # 计算最终评分
    final_score = (verifier.overall_score / verifier.total_checks * 100) if verifier.total_checks > 0 else 0
    
    print(f"\n🎯 最终评分: {final_score:.1f}%")
    if final_score >= 90:
        print("🎉 全自动量化交易系统验证通过！")
    else:
        print("⚠️ 系统需要进一步优化") 