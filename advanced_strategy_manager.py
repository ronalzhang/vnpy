#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
高级策略管理器 - 分层验证体系
实现全自动自我迭代升级的量化交易系统
"""

import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class StrategyStatus(Enum):
    """策略状态枚举"""
    SIMULATION_INIT = "simulation_init"          # 模拟初始化
    REAL_ENV_SIMULATION = "real_env_simulation"  # 真实环境模拟
    SMALL_REAL_TRADING = "small_real_trading"    # 小额真实交易
    FULL_REAL_TRADING = "full_real_trading"      # 正式真实交易
    ELITE_OPTIMIZATION = "elite_optimization"    # 精英优化
    RETIRED = "retired"                          # 退役

@dataclass
class StrategyValidation:
    """策略验证记录"""
    strategy_id: str
    status: StrategyStatus
    score: float
    win_rate: float
    total_return: float
    total_trades: int
    validation_start: datetime
    validation_end: Optional[datetime] = None
    real_trading_pnl: float = 0.0
    promotion_history: List[str] = None

class AdvancedStrategyManager:
    """高级策略管理器"""
    
    def __init__(self, quantitative_service):
        self.service = quantitative_service
        self.validation_records: Dict[str, StrategyValidation] = {}
        
        # 分层阈值配置
        self.thresholds = {
            'simulation_to_real_env': 50.0,     # 模拟 → 真实环境模拟
            'real_env_to_small_real': 65.0,     # 真实环境模拟 → 小额真实交易
            'small_real_to_full_real': 70.0,    # 小额真实 → 正式真实交易
            'full_real_to_elite': 80.0,         # 正式交易 → 精英优化
            'retirement_threshold': 35.0         # 退役阈值
        }
        
        # 资金分配配置
        self.fund_allocation = {
            'simulation_init': 0.0,              # 纯模拟，无资金
            'real_env_simulation': 0.0,          # 真实环境模拟，无资金
            'small_real_trading': 0.05,          # 5%资金用于小额验证
            'full_real_trading': 0.20,           # 20%资金用于正式交易
            'elite_optimization': 0.30           # 30%资金用于精英策略
        }
        
        # 验证周期配置 (小时)
        self.validation_periods = {
            'simulation_init': 24,               # 1天模拟初始化
            'real_env_simulation': 72,           # 3天真实环境验证
            'small_real_trading': 168,           # 7天小额真实交易验证
            'full_real_trading': 720,            # 30天正式交易验证
            'elite_optimization': float('inf')   # 持续优化
        }
        
        print("🚀 高级策略管理器初始化完成")
        print(f"📊 分层验证体系已建立")
        
    def run_advanced_management_cycle(self):
        """运行高级管理周期"""
        try:
            print("\n🔄 开始高级策略管理周期...")
            
            # 1. 评估所有策略当前状态
            self._evaluate_all_strategies()
            
            # 2. 检查晋升条件
            self._check_promotion_conditions()
            
            # 3. 检查退役条件
            self._check_retirement_conditions()
            
            # 4. 动态资金分配
            self._dynamic_fund_allocation()
            
            # 5. 自动交易状态管理
            auto_trading_should_enable = self._should_enable_auto_trading()
            if auto_trading_should_enable != self.service.auto_trading_enabled:
                self._toggle_auto_trading(auto_trading_should_enable)
            
            # 6. 生成管理报告
            self._generate_management_report()
            
            print("✅ 高级策略管理周期完成")
            
        except Exception as e:
            print(f"❌ 高级管理周期出错: {e}")
    
    def _evaluate_all_strategies(self):
        """评估所有策略"""
        strategies = self.service.get_strategies()
        if not strategies.get('success', False):
            return
            
        for strategy in strategies['data']:
            strategy_id = strategy['id']
            score = strategy.get('final_score', 0)
            win_rate = strategy.get('win_rate', 0)
            total_return = strategy.get('total_return', 0)
            total_trades = strategy.get('total_trades', 0)
            
            # 更新或创建验证记录
            if strategy_id not in self.validation_records:
                self.validation_records[strategy_id] = StrategyValidation(
                    strategy_id=strategy_id,
                    status=StrategyStatus.SIMULATION_INIT,
                    score=score,
                    win_rate=win_rate,
                    total_return=total_return,
                    total_trades=total_trades,
                    validation_start=datetime.now(),
                    promotion_history=[]
                )
            else:
                # 更新验证记录
                record = self.validation_records[strategy_id]
                record.score = score
                record.win_rate = win_rate
                record.total_return = total_return
                record.total_trades = total_trades
    
    def _check_promotion_conditions(self):
        """检查晋升条件"""
        for strategy_id, record in self.validation_records.items():
            current_status = record.status
            score = record.score
            
            # 检查验证时间是否足够
            validation_duration = (datetime.now() - record.validation_start).total_seconds() / 3600
            required_duration = self.validation_periods[current_status.value]
            
            if validation_duration < required_duration:
                continue  # 验证时间不够
            
            # 检查晋升条件
            promoted = False
            new_status = current_status
            
            if current_status == StrategyStatus.SIMULATION_INIT and score >= self.thresholds['simulation_to_real_env']:
                new_status = StrategyStatus.REAL_ENV_SIMULATION
                promoted = True
                
            elif current_status == StrategyStatus.REAL_ENV_SIMULATION and score >= self.thresholds['real_env_to_small_real']:
                new_status = StrategyStatus.SMALL_REAL_TRADING
                promoted = True
                
            elif current_status == StrategyStatus.SMALL_REAL_TRADING and score >= self.thresholds['small_real_to_full_real']:
                # 额外检查：小额交易必须盈利
                if record.real_trading_pnl > 0:
                    new_status = StrategyStatus.FULL_REAL_TRADING
                    promoted = True
                    
            elif current_status == StrategyStatus.FULL_REAL_TRADING and score >= self.thresholds['full_real_to_elite']:
                new_status = StrategyStatus.ELITE_OPTIMIZATION
                promoted = True
            
            if promoted:
                self._promote_strategy(strategy_id, new_status)
    
    def _promote_strategy(self, strategy_id: str, new_status: StrategyStatus):
        """晋升策略"""
        record = self.validation_records[strategy_id]
        old_status = record.status.value
        
        record.status = new_status
        record.validation_start = datetime.now()
        record.validation_end = datetime.now()
        record.promotion_history.append(f"{datetime.now().isoformat()}: {old_status} → {new_status.value}")
        
        print(f"🎉 策略晋升: {strategy_id}")
        print(f"   {old_status} → {new_status.value}")
        print(f"   当前评分: {record.score:.1f}")
        print(f"   成功率: {record.win_rate:.1%}")
        
        # 更新策略配置
        self._update_strategy_configuration(strategy_id, new_status)
    
    def _check_retirement_conditions(self):
        """检查退役条件"""
        for strategy_id, record in self.validation_records.items():
            if record.score < self.thresholds['retirement_threshold']:
                validation_duration = (datetime.now() - record.validation_start).total_seconds() / 3600
                
                # 给策略足够的验证时间
                min_validation_time = self.validation_periods[record.status.value] * 0.5
                
                if validation_duration >= min_validation_time:
                    self._retire_strategy(strategy_id)
    
    def _retire_strategy(self, strategy_id: str):
        """退役策略"""
        record = self.validation_records[strategy_id]
        record.status = StrategyStatus.RETIRED
        
        print(f"📤 策略退役: {strategy_id}")
        print(f"   评分过低: {record.score:.1f} < {self.thresholds['retirement_threshold']}")
        
        # 停用策略
        self.service.stop_strategy(strategy_id)
    
    def _should_enable_auto_trading(self) -> bool:
        """判断是否应该启用自动交易"""
        # 检查是否有符合真实交易条件的策略
        real_trading_strategies = 0
        total_real_allocation = 0.0
        
        for record in self.validation_records.values():
            if record.status in [StrategyStatus.SMALL_REAL_TRADING, 
                               StrategyStatus.FULL_REAL_TRADING, 
                               StrategyStatus.ELITE_OPTIMIZATION]:
                real_trading_strategies += 1
                total_real_allocation += self.fund_allocation[record.status.value]
        
        # 条件1: 至少有一个策略达到真实交易阶段
        # 条件2: 总资金分配合理
        # 条件3: 系统健康状态良好
        return (real_trading_strategies > 0 and 
                total_real_allocation > 0 and 
                self._check_system_health())
    
    def _check_system_health(self) -> bool:
        """检查系统健康状态"""
        try:
            # 检查数据库连接
            if not hasattr(self.service, 'db_manager') or self.service.db_manager is None:
                print("⚠️ 数据库连接异常，暂停自动交易")
                return False
            
            # 检查余额获取
            try:
                balance = self.service._get_current_balance()
                if balance <= 0:
                    print("⚠️ 余额获取异常，暂停自动交易")
                    return False
            except:
                print("⚠️ 余额API异常，暂停自动交易")
                return False
            
            # 检查策略数量
            strategies = self.service.get_strategies()
            if not strategies.get('success', False) or len(strategies.get('data', [])) == 0:
                print("⚠️ 策略获取异常，暂停自动交易")
                return False
            
            return True
            
        except Exception as e:
            print(f"⚠️ 系统健康检查失败: {e}")
            return False
    
    def _toggle_auto_trading(self, enable: bool):
        """切换自动交易状态"""
        try:
            reason = "系统智能判断" if enable else "系统保护机制"
            print(f"🔄 自动{'启用' if enable else '禁用'}交易 - {reason}")
            
            self.service.set_auto_trading(enable)
            
            # 记录操作日志
            self.service._log_operation(
                "自动交易切换",
                f"{'启用' if enable else '禁用'}自动交易 - {reason}",
                "success"
            )
            
        except Exception as e:
            print(f"❌ 切换自动交易失败: {e}")
    
    def _dynamic_fund_allocation(self):
        """动态资金分配"""
        total_balance = self.service._get_current_balance()
        
        for strategy_id, record in self.validation_records.items():
            if record.status == StrategyStatus.RETIRED:
                continue
                
            # 计算该策略应分配的资金
            allocation_ratio = self.fund_allocation[record.status.value]
            allocated_amount = total_balance * allocation_ratio
            
            # 更新策略资金配置
            if allocated_amount > 0:
                self._update_strategy_fund_allocation(strategy_id, allocated_amount)
    
    def _update_strategy_fund_allocation(self, strategy_id: str, allocated_amount: float):
        """更新策略资金分配"""
        try:
            strategy = self.service.get_strategy(strategy_id)
            if strategy:
                # 更新策略的交易量参数
                parameters = strategy.get('parameters', {})
                
                # 根据分配资金调整交易量
                base_trade_amount = allocated_amount * 0.1  # 每次交易使用10%的分配资金
                parameters['trade_amount'] = base_trade_amount
                parameters['allocated_fund'] = allocated_amount
                
                self.service.update_strategy_config(strategy_id, {
                    'parameters': parameters,
                    'allocation_ratio': allocated_amount / self.service._get_current_balance()
                })
                
        except Exception as e:
            print(f"❌ 更新策略资金分配失败 {strategy_id}: {e}")
    
    def _update_strategy_configuration(self, strategy_id: str, status: StrategyStatus):
        """更新策略配置"""
        try:
            strategy = self.service.get_strategy(strategy_id)
            if strategy:
                parameters = strategy.get('parameters', {})
                
                # 根据状态调整策略参数
                if status == StrategyStatus.REAL_ENV_SIMULATION:
                    parameters['simulation_mode'] = True
                    parameters['use_real_data'] = True
                    parameters['risk_level'] = 'conservative'
                    
                elif status == StrategyStatus.SMALL_REAL_TRADING:
                    parameters['simulation_mode'] = False
                    parameters['use_real_data'] = True
                    parameters['risk_level'] = 'conservative'
                    parameters['max_position_size'] = 0.05  # 限制仓位大小
                    
                elif status == StrategyStatus.FULL_REAL_TRADING:
                    parameters['simulation_mode'] = False
                    parameters['use_real_data'] = True
                    parameters['risk_level'] = 'moderate'
                    parameters['max_position_size'] = 0.15
                    
                elif status == StrategyStatus.ELITE_OPTIMIZATION:
                    parameters['simulation_mode'] = False
                    parameters['use_real_data'] = True
                    parameters['risk_level'] = 'aggressive'
                    parameters['max_position_size'] = 0.25
                    parameters['enable_compound_trading'] = True
                
                self.service.update_strategy_config(strategy_id, {
                    'parameters': parameters,
                    'validation_status': status.value
                })
                
        except Exception as e:
            print(f"❌ 更新策略配置失败 {strategy_id}: {e}")
    
    def _generate_management_report(self):
        """生成管理报告"""
        print("\n📊 === 策略管理报告 ===")
        
        status_counts = {}
        for record in self.validation_records.values():
            status = record.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in status_counts.items():
            print(f"  {status}: {count}个策略")
        
        # 显示top策略
        top_strategies = sorted(
            self.validation_records.values(),
            key=lambda x: x.score,
            reverse=True
        )[:5]
        
        print("\n🏆 Top 5 策略:")
        for i, record in enumerate(top_strategies, 1):
            print(f"  {i}. {record.strategy_id}: {record.score:.1f}分 [{record.status.value}]")
        
        print(f"\n💰 当前余额: {self.service._get_current_balance():.2f} USDT")
        print(f"🤖 自动交易状态: {'启用' if self.service.auto_trading_enabled else '禁用'}")
        print("=" * 50)

# 全局实例
advanced_manager = None

def get_advanced_manager(quantitative_service):
    """获取高级管理器实例"""
    global advanced_manager
    if advanced_manager is None:
        advanced_manager = AdvancedStrategyManager(quantitative_service)
    return advanced_manager 