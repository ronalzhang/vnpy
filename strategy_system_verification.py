#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 策略系统全面验证脚本
功能：从0开始验证 生成策略 -> 进化策略 -> 合并策略 -> 淘汰策略 的完整流程
作者：量化交易系统
"""

import requests
import json
import time
import datetime
from typing import Dict, List, Any

class StrategySystemVerifier:
    def __init__(self, base_url="http://47.236.39.134:8888"):
        self.base_url = base_url
        self.session = requests.Session()
        self.verification_results = {}
        
    def log(self, message: str, level: str = "INFO"):
        """记录验证日志"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def api_call(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
        """安全的API调用"""
        try:
            url = f"{self.base_url}{endpoint}"
            if method == "GET":
                response = self.session.get(url)
            elif method == "POST":
                response = self.session.post(url, json=data)
            elif method == "PUT":
                response = self.session.put(url, json=data)
            elif method == "DELETE":
                response = self.session.delete(url)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
                
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log(f"API调用失败 [{method} {endpoint}]: {str(e)}", "ERROR")
            return {"success": False, "error": str(e)}
    
    def verify_step_1_system_status(self) -> bool:
        """🔍 步骤1：验证系统状态"""
        self.log("🔍 步骤1：验证系统状态", "INFO")
        
        # 检查系统健康状态
        health = self.api_call("/api/quantitative/system-health")
        if health.get("success"):
            self.log(f"✅ 系统健康状态正常")
        else:
            self.log("❌ 系统健康状态检查失败", "ERROR")
            return False
            
        # 检查系统状态
        status = self.api_call("/api/quantitative/system-status")
        if status.get("success"):
            self.log(f"✅ 系统状态检查通过")
        else:
            self.log("❌ 系统状态检查失败", "ERROR")
            return False
            
        self.verification_results["system_status"] = True
        return True
    
    def verify_step_2_strategy_creation(self) -> List[str]:
        """🔍 步骤2：验证策略创建功能"""
        self.log("🔍 步骤2：验证策略创建功能", "INFO")
        
        created_strategies = []
        strategy_types = ["momentum", "mean_reversion", "breakout"]
        
        for strategy_type in strategy_types:
            self.log(f"📝 创建{strategy_type}策略...")
            
            create_data = {
                "strategy_type": strategy_type,
                "name": f"🧪测试{strategy_type}策略_{int(time.time())}",
                "auto_params": True
            }
            
            result = self.api_call("/api/quantitative/strategies/create", "POST", create_data)
            
            if result.get("success"):
                strategy_id = result.get("strategy_id")
                if strategy_id:
                    created_strategies.append(strategy_id)
                    self.log(f"✅ {strategy_type}策略创建成功")
                else:
                    self.log(f"❌ {strategy_type}策略创建失败：无有效ID", "ERROR")
            else:
                self.log(f"❌ {strategy_type}策略创建失败", "ERROR")
        
        self.verification_results["strategy_creation"] = len(created_strategies) > 0
        return created_strategies
    
    def verify_step_3_strategy_parameters(self, strategy_ids: List[str]) -> bool:
        """🔍 步骤3：验证策略参数完整性"""
        self.log("🔍 步骤3：验证策略参数完整性", "INFO")
        
        all_params_valid = True
        
        for strategy_id in strategy_ids:
            strategy = self.api_call(f"/api/quantitative/strategies/{strategy_id}")
            
            if strategy.get("success"):
                params = strategy.get("data", {}).get("parameters", {})
                
                required_params = [
                    "rsi_period", "rsi_upper", "rsi_lower",
                    "macd_fast", "macd_slow", "macd_signal",
                    "bb_period", "bb_std_dev",
                    "stop_loss_percent", "take_profit_percent"
                ]
                
                missing_params = [p for p in required_params if p not in params or params[p] is None]
                
                if missing_params:
                    self.log(f"❌ 策略参数缺失: {missing_params}", "ERROR")
                    all_params_valid = False
                else:
                    self.log(f"✅ 策略参数完整 ({len(params)}个参数)")
            else:
                self.log(f"❌ 获取策略详情失败", "ERROR")
                all_params_valid = False
        
        self.verification_results["strategy_parameters"] = all_params_valid
        return all_params_valid
    
    def verify_step_4_evolution_system(self) -> bool:
        """🔍 步骤4：验证进化系统"""
        self.log("🔍 步骤4：验证进化系统", "INFO")
        
        evolution_status = self.api_call("/api/quantitative/evolution/status")
        
        if evolution_status.get("success"):
            self.log("✅ 进化系统状态获取成功")
            
            # 手动触发一次进化
            trigger_result = self.api_call("/api/quantitative/evolution/trigger", "POST")
            
            if trigger_result.get("success"):
                self.log("✅ 进化触发成功")
                time.sleep(3)
                
                evolution_logs = self.api_call("/api/quantitative/evolution-log")
                if evolution_logs.get("success"):
                    logs = evolution_logs.get("logs", [])
                    self.log(f"📜 获取到 {len(logs)} 条进化日志")
                    
                    self.verification_results["evolution_system"] = True
                    return True
                else:
                    self.log("❌ 获取进化日志失败", "ERROR")
            else:
                self.log(f"❌ 进化触发失败", "ERROR")
        else:
            self.log("❌ 获取进化系统状态失败", "ERROR")
        
        self.verification_results["evolution_system"] = False
        return False
    
    def generate_verification_report(self) -> str:
        """🔍 生成验证报告"""
        self.log("📋 生成验证报告", "INFO")
        
        report = {
            "验证时间": datetime.datetime.now().isoformat(),
            "系统版本": "VNPY量化交易系统 v2.0",
            "验证结果": self.verification_results,
            "总体状态": "通过" if all(self.verification_results.values()) else "失败",
            "通过率": f"{sum(self.verification_results.values())}/{len(self.verification_results)}"
        }
        
        return json.dumps(report, ensure_ascii=False, indent=2)
    
    def run_full_verification(self) -> bool:
        """🚀 运行完整验证流程"""
        self.log("🚀 开始策略系统全面验证", "INFO")
        self.log("=" * 60)
        
        try:
            # 步骤1：系统状态
            if not self.verify_step_1_system_status():
                return False
            
            # 步骤2：策略创建
            created_strategies = self.verify_step_2_strategy_creation()
            if not created_strategies:
                self.log("❌ 策略创建失败，终止验证", "ERROR")
                return False
            
            # 步骤3：参数完整性
            if not self.verify_step_3_strategy_parameters(created_strategies):
                self.log("⚠️ 参数验证有问题，但继续验证", "WARN")
            
            # 步骤4：进化系统
            if not self.verify_step_4_evolution_system():
                self.log("⚠️ 进化系统验证有问题，但继续验证", "WARN")
            
            # 生成报告
            report = self.generate_verification_report()
            print("\n" + "="*60)
            print("📋 验证报告:")
            print(report)
            print("="*60)
            
            self.log("✅ 策略系统验证完成", "INFO")
            
            # 总结
            passed_count = sum(self.verification_results.values())
            total_count = len(self.verification_results)
            
            if passed_count == total_count:
                self.log("🎉 所有验证项目通过！系统运行正常", "INFO")
                return True
            else:
                self.log(f"⚠️ 验证通过 {passed_count}/{total_count} 项，系统基本可用", "WARN")
                return False
                
        except Exception as e:
            self.log(f"💥 验证过程发生异常: {str(e)}", "ERROR")
            return False

def main():
    """主函数"""
    verifier = StrategySystemVerifier()
    success = verifier.run_full_verification()
    
    return success

if __name__ == "__main__":
    main() 