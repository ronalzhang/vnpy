#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
100U → 1万U 投资计划执行器
自动化执行阶段性投资计划，实现快速资金增长
"""

from datetime import datetime, timedelta
from typing import Dict, List
import json
import time
from loguru import logger
from auto_trading_engine import get_trading_engine
from quantitative_service import QuantitativeService

class InvestmentPlan:
    """投资计划执行器"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.trading_engine = get_trading_engine()
        self.quant_service = QuantitativeService()
        
        # 投资计划阶段
        self.phases = [
            {
                'name': '第一阶段',
                'target_amount': 200,      # 目标金额 200U
                'target_days': 7,          # 目标天数 7天
                'daily_target': 0.105,     # 每日目标收益 10.5%
                'max_risk': 0.25,          # 最大单笔风险 25%
                'strategies': ['momentum', 'breakout', 'high_frequency']  # 激进策略组合
            },
            {
                'name': '第二阶段',
                'target_amount': 500,      # 200U → 500U
                'target_days': 10,
                'daily_target': 0.095,     # 9.5%
                'max_risk': 0.20,
                'strategies': ['momentum', 'grid_trading', 'high_frequency']
            },
            {
                'name': '第三阶段', 
                'target_amount': 1000,     # 500U → 1000U
                'target_days': 8,
                'daily_target': 0.085,     # 8.5%
                'max_risk': 0.18,
                'strategies': ['trend_following', 'momentum', 'grid_trading']
            },
            {
                'name': '第四阶段',
                'target_amount': 2500,     # 1000U → 2500U
                'target_days': 12,
                'daily_target': 0.08,      # 8%
                'max_risk': 0.15,
                'strategies': ['momentum', 'mean_reversion', 'trend_following']
            },
            {
                'name': '第五阶段',
                'target_amount': 5000,     # 2500U → 5000U
                'target_days': 10,
                'daily_target': 0.07,      # 7%
                'max_risk': 0.12,
                'strategies': ['grid_trading', 'mean_reversion', 'momentum']
            },
            {
                'name': '最终阶段',
                'target_amount': 10000,    # 5000U → 10000U
                'target_days': 12,
                'daily_target': 0.06,      # 6%
                'max_risk': 0.10,
                'strategies': ['trend_following', 'grid_trading', 'mean_reversion']
            }
        ]
        
        self.current_phase = 0
        self.plan_start_balance = 0
        self.phase_start_balance = 0
        self.phase_start_time = datetime.now()
        
    def start_plan(self):
        """启动投资计划"""
        logger.info("🚀 启动100U→1万U投资计划")
        
        # 获取当前余额
        status = self.trading_engine.get_status()
        self.plan_start_balance = status['balance']
        self.phase_start_balance = self.plan_start_balance
        
        if self.plan_start_balance < 100:
            logger.error(f"余额不足：当前余额 {self.plan_start_balance}U，需要至少100U")
            return False
        
        logger.info(f"计划开始余额: {self.plan_start_balance:.2f} USDT")
        
        # 调整交易引擎参数为激进模式
        self._configure_aggressive_mode()
        
        # 启动当前阶段
        self._start_current_phase()
        
        return True
    
    def _configure_aggressive_mode(self):
        """配置激进交易模式"""
        # 更高的目标收益率
        self.trading_engine.daily_target_return = self.get_current_phase()['daily_target']
        
        # 调整仓位参数 - 更激进
        self.trading_engine.base_position_size = 0.05  # 基础仓位5%
        self.trading_engine.max_position_size = self.get_current_phase()['max_risk']
        
        # 更激进的止盈止损
        self.trading_engine.base_stop_loss = 0.015      # 1.5%止损
        self.trading_engine.base_take_profit = 0.08     # 8%止盈
        
        logger.info("⚡ 已切换至激进交易模式")
    
    def get_current_phase(self) -> Dict:
        """获取当前阶段信息"""
        if self.current_phase < len(self.phases):
            return self.phases[self.current_phase]
        return self.phases[-1]  # 返回最后阶段
    
    def _start_current_phase(self):
        """启动当前阶段"""
        phase = self.get_current_phase()
        self.phase_start_time = datetime.now()
        self.phase_start_balance = self.trading_engine.get_status()['balance']
        
        logger.info(f"🎯 启动{phase['name']}: {self.phase_start_balance:.0f}U → {phase['target_amount']}U")
        logger.info(f"📅 目标天数: {phase['target_days']}天，每日目标: {phase['daily_target']*100:.1f}%")
        
        # 启用对应策略
        self._activate_phase_strategies(phase['strategies'])
        
        # 更新交易参数
        self.trading_engine.daily_target_return = phase['daily_target']
        self.trading_engine.max_position_size = phase['max_risk']
    
    def _activate_phase_strategies(self, strategy_types: List[str]):
        """激活阶段对应的策略"""
        try:
            # 停止所有策略
            strategies = self.quant_service.get_strategies()
            for strategy in strategies:
                if strategy.get('status') == 'running':
                    self.quant_service.stop_strategy(strategy['id'])
            
            # 启动指定策略
            for strategy in strategies:
                if strategy.get('type') in strategy_types:
                    success = self.quant_service.start_strategy(strategy['id'])
                    if success:
                        logger.info(f"✅ 启动策略: {strategy['name']} ({strategy['type']})")
                    else:
                        logger.warning(f"⚠️ 启动策略失败: {strategy['name']}")
                        
        except Exception as e:
            logger.error(f"激活策略失败: {e}")
    
    def check_phase_progress(self) -> Dict:
        """检查阶段进展"""
        phase = self.get_current_phase()
        status = self.trading_engine.get_status()
        current_balance = status['balance']
        
        # 计算进展
        phase_days = (datetime.now() - self.phase_start_time).days
        balance_growth = current_balance - self.phase_start_balance
        growth_ratio = balance_growth / self.phase_start_balance if self.phase_start_balance > 0 else 0
        
        # 目标完成度
        target_growth = phase['target_amount'] - self.phase_start_balance
        completion_ratio = balance_growth / target_growth if target_growth > 0 else 0
        
        progress = {
            'phase_name': phase['name'],
            'current_balance': current_balance,
            'start_balance': self.phase_start_balance,
            'target_balance': phase['target_amount'],
            'balance_growth': balance_growth,
            'growth_ratio': growth_ratio,
            'completion_ratio': min(completion_ratio, 1.0),
            'phase_days': phase_days,
            'target_days': phase['target_days'],
            'daily_target': phase['daily_target'],
            'ahead_of_schedule': completion_ratio > (phase_days / phase['target_days']) if phase_days > 0 else False
        }
        
        return progress
    
    def should_advance_phase(self) -> bool:
        """判断是否应该进入下一阶段"""
        progress = self.check_phase_progress()
        
        # 达到目标金额
        if progress['completion_ratio'] >= 1.0:
            return True
            
        # 提前完成（超过预期进度）
        if progress['ahead_of_schedule'] and progress['completion_ratio'] >= 0.95:
            return True
            
        return False
    
    def advance_to_next_phase(self):
        """进入下一阶段"""
        if self.current_phase < len(self.phases) - 1:
            progress = self.check_phase_progress()
            
            logger.success(f"🎉 {progress['phase_name']}完成！")
            logger.info(f"📈 收益: {progress['balance_growth']:.2f}U ({progress['growth_ratio']*100:.1f}%)")
            logger.info(f"⏰ 用时: {progress['phase_days']}天 (目标{progress['target_days']}天)")
            
            self.current_phase += 1
            self._start_current_phase()
            
            return True
        else:
            logger.success("🏆 投资计划完成！已达到1万U目标！")
            return False
    
    def is_plan_completed(self) -> bool:
        """判断计划是否完成"""
        current_balance = self.trading_engine.get_status()['balance']
        return current_balance >= 10000
    
    def get_overall_progress(self) -> Dict:
        """获取整体进展"""
        status = self.trading_engine.get_status()
        current_balance = status['balance']
        
        total_days = (datetime.now() - self.start_time).days
        total_growth = current_balance - self.plan_start_balance
        total_growth_ratio = total_growth / self.plan_start_balance if self.plan_start_balance > 0 else 0
        
        overall_completion = (current_balance - self.plan_start_balance) / (10000 - self.plan_start_balance) if self.plan_start_balance > 0 else 0
        
        return {
            'start_balance': self.plan_start_balance,
            'current_balance': current_balance,
            'target_balance': 10000,
            'total_growth': total_growth,
            'total_growth_ratio': total_growth_ratio,
            'overall_completion': min(overall_completion, 1.0),
            'total_days': total_days,
            'current_phase': self.current_phase + 1,
            'total_phases': len(self.phases),
            'is_completed': self.is_plan_completed()
        }
    
    def generate_daily_report(self) -> str:
        """生成每日报告"""
        phase_progress = self.check_phase_progress()
        overall_progress = self.get_overall_progress()
        status = self.trading_engine.get_status()
        
        report = f"""
        
📊 === 100U→1万U投资计划日报 ===

💰 资金状况:
   当前余额: {overall_progress['current_balance']:.2f} USDT
   计划起始: {overall_progress['start_balance']:.2f} USDT
   总体增长: {overall_progress['total_growth']:.2f} USDT ({overall_progress['total_growth_ratio']*100:.1f}%)
   完成进度: {overall_progress['overall_completion']*100:.1f}%

🎯 当前阶段: {phase_progress['phase_name']}
   阶段目标: {phase_progress['start_balance']:.0f}U → {phase_progress['target_balance']:.0f}U
   阶段进展: {phase_progress['completion_ratio']*100:.1f}%
   阶段用时: {phase_progress['phase_days']}/{phase_progress['target_days']}天
   {'✅ 超前进度' if phase_progress['ahead_of_schedule'] else '⏳ 按计划进行'}

📈 交易表现:
   今日盈亏: {status.get('daily_pnl', 0):.2f} USDT
   今日收益率: {status.get('daily_return', 0)*100:.2f}%
   今日交易: {status.get('daily_trades', 0)}笔
   今日胜率: {status.get('daily_win_rate', 0)*100:.1f}%
   当前持仓: {status.get('positions_count', 0)}个

⏰ 时间统计:
   计划运行: {overall_progress['total_days']}天
   当前阶段: 第{overall_progress['current_phase']}/{overall_progress['total_phases']}阶段

{"🏆 恭喜！投资计划已完成！" if overall_progress['is_completed'] else ""}
        """
        
        return report.strip()

def main():
    """主函数 - 投资计划执行器"""
    plan = InvestmentPlan()
    
    logger.info("🚀 启动投资计划执行器...")
    
    if not plan.start_plan():
        logger.error("投资计划启动失败")
        return
    
    # 主监控循环
    try:
        while not plan.is_plan_completed():
            # 检查阶段进展
            if plan.should_advance_phase():
                if not plan.advance_to_next_phase():
                    break  # 计划完成
            
            # 生成每日报告
            report = plan.generate_daily_report()
            logger.info(report)
            
            # 等待一天再检查
            time.sleep(24 * 60 * 60)  # 24小时
            
    except KeyboardInterrupt:
        logger.info("手动停止投资计划")
    except Exception as e:
        logger.error(f"投资计划执行错误: {e}")
    
    # 最终报告
    final_report = plan.generate_daily_report()
    logger.info(f"投资计划最终报告:\n{final_report}")

if __name__ == "__main__":
    main() 