#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复版集成量化交易系统
整合增强日志、修复自动交易、透明策略进化
"""

import os
import sys
import time
import json
import threading
import signal
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enhanced_logging_system import get_enhanced_logger, log_system, log_trading, log_evolution
from fixed_auto_trading_engine import get_fixed_trading_engine
from enhanced_strategy_evolution import get_enhanced_evolution_engine
import traceback

class FixedIntegratedSystem:
    """修复版集成系统"""
    
    def __init__(self):
        self.logger = get_enhanced_logger()
        self.running = False
        self.auto_trading_enabled = False
        self.evolution_enabled = False
        
        # 核心组件
        self.quantitative_service = None
        self.trading_engine = None
        self.evolution_engine = None
        self.web_app = None
        
        # 管理线程
        self.management_thread = None
        self.evolution_thread = None
        self.monitoring_thread = None
        
        # 系统状态
        self.start_time = None
        self.last_evolution_time = None
        self.system_stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'total_evolution_cycles': 0,
            'active_strategies': 0,
            'system_uptime': 0
        }
        
        log_system("INFO", "修复版集成系统初始化开始")
    
    def initialize(self) -> bool:
        """初始化系统"""
        try:
            log_system("INFO", "🚀 启动修复版量化交易系统...")
            
            # 1. 初始化量化服务
            if not self._init_quantitative_service():
                return False
            
            # 2. 初始化自动交易引擎
            if not self._init_trading_engine():
                return False
            
            # 3. 初始化策略进化引擎
            if not self._init_evolution_engine():
                return False
            
            # 4. 初始化Web服务
            if not self._init_web_service():
                log_system("WARNING", "Web服务初始化失败，但系统可以继续运行")
            
            # 5. 设置信号处理
            self._setup_signal_handlers()
            
            log_system("INFO", "✅ 系统初始化完成")
            return True
            
        except Exception as e:
            log_system("ERROR", f"系统初始化失败: {e}")
            log_system("ERROR", traceback.format_exc())
            return False
    
    def _init_quantitative_service(self) -> bool:
        """初始化量化服务"""
        try:
            log_system("INFO", "初始化量化交易服务...")
            
            # 导入量化服务
            from quantitative_service import QuantitativeService
            
            self.quantitative_service = QuantitativeService()
            
            # 初始化数据库和策略
            self.quantitative_service.init_database()
            self.quantitative_service.init_strategies()
            
            log_system("INFO", "✅ 量化交易服务初始化成功")
            return True
            
        except Exception as e:
            log_system("ERROR", f"量化服务初始化失败: {e}")
            return False
    
    def _init_trading_engine(self) -> bool:
        """初始化自动交易引擎"""
        try:
            log_system("INFO", "初始化修复版自动交易引擎...")
            
            self.trading_engine = get_fixed_trading_engine()
            
            # 测试引擎状态
            status = self.trading_engine.get_status()
            if status.get('error'):
                log_system("WARNING", f"交易引擎状态异常: {status['error']}")
                log_system("INFO", "启用模拟模式继续运行")
            
            log_system("INFO", "✅ 自动交易引擎初始化成功")
            return True
            
        except Exception as e:
            log_system("ERROR", f"自动交易引擎初始化失败: {e}")
            return False
    
    def _init_evolution_engine(self) -> bool:
        """初始化策略进化引擎"""
        try:
            log_system("INFO", "初始化增强策略进化引擎...")
            
            self.evolution_engine = get_enhanced_evolution_engine(self.quantitative_service)
            
            log_system("INFO", "✅ 策略进化引擎初始化成功")
            return True
            
        except Exception as e:
            log_system("ERROR", f"策略进化引擎初始化失败: {e}")
            return False
    
    def _init_web_service(self) -> bool:
        """初始化Web服务"""
        try:
            log_system("INFO", "初始化Web服务...")
            
            from web_app import app
            
            # 在后台线程启动Flask应用
            def run_flask():
                try:
                    app.run(host='0.0.0.0', port=8888, debug=False, use_reloader=False)
                except Exception as e:
                    log_system("ERROR", f"Web服务运行错误: {e}")
            
            flask_thread = threading.Thread(target=run_flask, daemon=True)
            flask_thread.start()
            
            self.web_app = app
            
            # 等待服务启动
            time.sleep(2)
            
            log_system("INFO", "✅ Web服务已启动 (端口:8888)")
            return True
            
        except Exception as e:
            log_system("ERROR", f"Web服务初始化失败: {e}")
            return False
    
    def _setup_signal_handlers(self):
        """设置信号处理"""
        def signal_handler(signum, frame):
            log_system("INFO", f"收到信号 {signum}，开始优雅关闭...")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # 终止信号
    
    def start(self) -> bool:
        """启动系统"""
        try:
            if self.running:
                log_system("WARNING", "系统已经在运行")
                return True
            
            self.running = True
            self.start_time = datetime.now()
            
            log_system("INFO", "🚀 启动修复版集成系统...")
            
            # 启动核心服务
            self._start_quantitative_service()
            
            # 启动管理线程
            self._start_management_threads()
            
            # 更新系统状态
            self._update_system_status()
            
            log_system("INFO", "✅ 系统启动成功")
            log_system("INFO", f"🌐 Web界面访问地址: http://localhost:8888/quantitative.html")
            
            return True
            
        except Exception as e:
            log_system("ERROR", f"系统启动失败: {e}")
            self.running = False
            return False
    
    def _start_quantitative_service(self):
        """启动量化服务"""
        try:
            if self.quantitative_service:
                self.quantitative_service.start()
                log_system("INFO", "量化服务已启动")
        except Exception as e:
            log_system("ERROR", f"启动量化服务失败: {e}")
    
    def _start_management_threads(self):
        """启动管理线程"""
        try:
            # 系统监控线程
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            # 管理决策线程
            self.management_thread = threading.Thread(target=self._management_loop, daemon=True)
            self.management_thread.start()
            
            # 策略进化线程
            self.evolution_thread = threading.Thread(target=self._evolution_loop, daemon=True)
            self.evolution_thread.start()
            
            log_system("INFO", "管理线程已启动")
            
        except Exception as e:
            log_system("ERROR", f"启动管理线程失败: {e}")
    
    def _monitoring_loop(self):
        """系统监控循环"""
        log_system("INFO", "系统监控循环启动")
        
        while self.running:
            try:
                # 更新系统统计
                self._update_system_stats()
                
                # 健康检查
                self._system_health_check()
                
                # 记录系统状态
                self._log_system_status()
                
                time.sleep(30)  # 每30秒监控一次
                
            except Exception as e:
                log_system("ERROR", f"系统监控错误: {e}")
                time.sleep(60)
        
        log_system("INFO", "系统监控循环结束")
    
    def _management_loop(self):
        """管理决策循环"""
        log_system("INFO", "管理决策循环启动")
        
        while self.running:
            try:
                # 检查自动交易状态
                self._check_auto_trading_status()
                
                # 检查策略状态
                self._check_strategy_status()
                
                # 执行智能决策
                self._make_intelligent_decisions()
                
                time.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                log_system("ERROR", f"管理决策错误: {e}")
                time.sleep(120)
        
        log_system("INFO", "管理决策循环结束")
    
    def _evolution_loop(self):
        """策略进化循环"""
        log_system("INFO", "策略进化循环启动")
        
        while self.running:
            try:
                if self.evolution_enabled:
                    # 检查是否需要进化
                    if self._should_run_evolution():
                        log_system("INFO", "开始策略进化周期...")
                        
                        # 执行进化
                        evolution_result = self.evolution_engine.start_evolution_cycle()
                        
                        if evolution_result.get('success', False):
                            self.system_stats['total_evolution_cycles'] += 1
                            self.last_evolution_time = datetime.now()
                            
                            log_system("INFO", f"✅ 策略进化完成 - 第 {evolution_result['generation']} 代")
                            log_system("INFO", f"📊 平均适应性: {evolution_result['avg_fitness']:.1f}")
                            log_system("INFO", f"🎯 最佳适应性: {evolution_result['max_fitness']:.1f}")
                        else:
                            log_system("ERROR", f"策略进化失败: {evolution_result.get('error', '未知错误')}")
                    
                # 每2小时检查一次进化条件
                time.sleep(7200)
                
            except Exception as e:
                log_system("ERROR", f"策略进化错误: {e}")
                log_system("ERROR", traceback.format_exc())
                time.sleep(3600)  # 出错后等待1小时
        
        log_system("INFO", "策略进化循环结束")
    
    def _should_run_evolution(self) -> bool:
        """检查是否应该运行进化"""
        try:
            # 检查时间间隔
            if self.last_evolution_time:
                time_since_last = datetime.now() - self.last_evolution_time
                if time_since_last < timedelta(hours=6):  # 至少6小时间隔
                    return False
            
            # 检查策略表现
            strategies_response = self.quantitative_service.get_strategies()
            if not strategies_response.get('success', False):
                return False
            
            strategies = strategies_response['data']
            if len(strategies) < 3:  # 至少有3个策略才进化
                return True  # 策略太少，需要进化生成更多
            
            # 检查平均表现
            avg_score = sum(s.get('final_score', 0) for s in strategies) / len(strategies)
            if avg_score < 60:  # 平均分低于60时进化
                return True
            
            # 检查是否有新策略需要评估
            new_strategies = [s for s in strategies if s.get('total_trades', 0) < 5]
            if len(new_strategies) > len(strategies) * 0.3:  # 新策略超过30%
                return True
            
            return False
            
        except Exception as e:
            log_system("ERROR", f"检查进化条件失败: {e}")
            return False
    
    def _update_system_stats(self):
        """更新系统统计"""
        try:
            if self.start_time:
                self.system_stats['system_uptime'] = int((datetime.now() - self.start_time).total_seconds())
            
            # 更新策略数量
            strategies_response = self.quantitative_service.get_strategies()
            if strategies_response.get('success', False):
                self.system_stats['active_strategies'] = len(strategies_response['data'])
            
            # 更新交易统计
            if self.trading_engine:
                trading_status = self.trading_engine.get_status()
                if not trading_status.get('error'):
                    self.system_stats['total_trades'] = trading_status.get('daily_trades', 0)
                    self.system_stats['successful_trades'] = trading_status.get('daily_wins', 0)
            
        except Exception as e:
            log_system("ERROR", f"更新系统统计失败: {e}")
    
    def _system_health_check(self):
        """系统健康检查"""
        try:
            health_issues = []
            
            # 检查量化服务
            if not self.quantitative_service:
                health_issues.append("量化服务未运行")
            
            # 检查交易引擎
            if self.trading_engine:
                trading_status = self.trading_engine.get_status()
                if trading_status.get('error'):
                    health_issues.append(f"交易引擎异常: {trading_status['error']}")
                elif not trading_status.get('running', False) and self.auto_trading_enabled:
                    health_issues.append("自动交易已启用但引擎未运行")
            
            # 检查策略状态
            strategies_response = self.quantitative_service.get_strategies()
            if strategies_response.get('success', False):
                strategies = strategies_response['data']
                if len(strategies) == 0:
                    health_issues.append("没有活跃策略")
                else:
                    low_performance_strategies = [s for s in strategies if s.get('final_score', 0) < 30]
                    if len(low_performance_strategies) > len(strategies) * 0.5:
                        health_issues.append("超过50%的策略表现不佳")
            
            # 记录健康状况
            if health_issues:
                log_system("WARNING", f"系统健康检查发现问题: {'; '.join(health_issues)}")
            else:
                log_system("DEBUG", "系统健康检查正常")
            
        except Exception as e:
            log_system("ERROR", f"系统健康检查失败: {e}")
    
    def _log_system_status(self):
        """记录系统状态"""
        try:
            status = {
                'running': self.running,
                'auto_trading_enabled': self.auto_trading_enabled,
                'evolution_enabled': self.evolution_enabled,
                'uptime_minutes': self.system_stats['system_uptime'] // 60,
                'active_strategies': self.system_stats['active_strategies'],
                'daily_trades': self.system_stats['total_trades'],
                'evolution_cycles': self.system_stats['total_evolution_cycles']
            }
            
            log_system("DEBUG", f"系统状态: {status}")
            
        except Exception as e:
            log_system("ERROR", f"记录系统状态失败: {e}")
    
    def _check_auto_trading_status(self):
        """检查自动交易状态"""
        try:
            if not self.auto_trading_enabled:
                return
            
            if not self.trading_engine:
                log_system("WARNING", "自动交易已启用但引擎未初始化")
                return
            
            trading_status = self.trading_engine.get_status()
            
            if not trading_status.get('running', False):
                log_system("WARNING", "自动交易引擎未运行，尝试重启...")
                
                # 尝试重启交易引擎
                if self.trading_engine.start():
                    log_trading("ENGINE_RESTART", result="自动重启成功")
                    log_system("INFO", "✅ 自动交易引擎重启成功")
                else:
                    log_trading("ENGINE_RESTART", error_message="自动重启失败")
                    log_system("ERROR", "❌ 自动交易引擎重启失败")
            
        except Exception as e:
            log_system("ERROR", f"检查自动交易状态失败: {e}")
    
    def _check_strategy_status(self):
        """检查策略状态"""
        try:
            strategies_response = self.quantitative_service.get_strategies()
            if not strategies_response.get('success', False):
                return
            
            strategies = strategies_response['data']
            
            # 检查策略数量
            if len(strategies) < 5:
                log_system("WARNING", f"活跃策略数量过少: {len(strategies)}")
                # 可以触发策略生成
            
            # 检查策略表现
            poor_strategies = [s for s in strategies if s.get('final_score', 0) < 20]
            if poor_strategies:
                log_system("WARNING", f"发现 {len(poor_strategies)} 个表现极差的策略")
                
                # 停用表现极差的策略
                for strategy in poor_strategies:
                    if strategy.get('total_trades', 0) > 10:  # 至少有10次交易记录
                        try:
                            self.quantitative_service.stop_strategy(strategy['id'])
                            log_evolution(
                                strategy_id=strategy['id'],
                                action_type="AUTO_DISABLE",
                                reason=f"表现极差自动停用 (评分: {strategy.get('final_score', 0):.1f})"
                            )
                        except Exception as e:
                            log_system("ERROR", f"停用策略失败: {e}")
            
        except Exception as e:
            log_system("ERROR", f"检查策略状态失败: {e}")
    
    def _make_intelligent_decisions(self):
        """执行智能决策"""
        try:
            # 获取系统状态
            strategies_response = self.quantitative_service.get_strategies()
            if not strategies_response.get('success', False):
                return
            
            strategies = strategies_response['data']
            
            # 决策1: 动态调整进化频率
            avg_performance = sum(s.get('final_score', 0) for s in strategies) / max(len(strategies), 1)
            
            if avg_performance < 40:
                # 表现很差，加快进化
                if not self.evolution_enabled:
                    self.enable_evolution()
                    log_system("INFO", "🧬 系统表现较差，自动启用策略进化")
            elif avg_performance > 80:
                # 表现很好，可以放缓进化
                log_system("INFO", "📈 系统表现良好，保持当前配置")
            
            # 决策2: 动态调整自动交易
            if len(strategies) > 0:
                good_strategies = [s for s in strategies if s.get('final_score', 0) > 70]
                if len(good_strategies) >= 3 and not self.auto_trading_enabled:
                    self.enable_auto_trading()
                    log_system("INFO", "💰 发现足够的优质策略，自动启用自动交易")
                elif len(good_strategies) < 2 and self.auto_trading_enabled:
                    self.disable_auto_trading()
                    log_system("INFO", "⚠️ 优质策略不足，自动停用自动交易")
            
        except Exception as e:
            log_system("ERROR", f"智能决策失败: {e}")
    
    def _update_system_status(self):
        """更新系统状态到数据库"""
        try:
            if self.quantitative_service:
                self.quantitative_service.update_system_status(
                    quantitative_running=True,
                    auto_trading_enabled=self.auto_trading_enabled,
                    evolution_enabled=self.evolution_enabled,
                    total_strategies=self.system_stats['active_strategies'],
                    current_generation=self.evolution_engine.current_generation if self.evolution_engine else 0,
                    system_health="良好" if self.running else "异常"
                )
        except Exception as e:
            log_system("ERROR", f"更新系统状态失败: {e}")
    
    def enable_auto_trading(self) -> bool:
        """启用自动交易"""
        try:
            if self.auto_trading_enabled:
                log_system("INFO", "自动交易已经启用")
                return True
            
            if not self.trading_engine:
                log_system("ERROR", "交易引擎未初始化")
                return False
            
            if self.trading_engine.start():
                self.auto_trading_enabled = True
                log_trading("AUTO_TRADING_ENABLE", result="自动交易启用成功")
                log_system("INFO", "✅ 自动交易已启用")
                
                # 更新系统状态
                self._update_system_status()
                return True
            else:
                log_trading("AUTO_TRADING_ENABLE", error_message="启用失败")
                log_system("ERROR", "❌ 自动交易启用失败")
                return False
                
        except Exception as e:
            log_system("ERROR", f"启用自动交易失败: {e}")
            return False
    
    def disable_auto_trading(self) -> bool:
        """停用自动交易"""
        try:
            if not self.auto_trading_enabled:
                log_system("INFO", "自动交易已经停用")
                return True
            
            if self.trading_engine:
                self.trading_engine.stop()
            
            self.auto_trading_enabled = False
            log_trading("AUTO_TRADING_DISABLE", result="自动交易停用成功")
            log_system("INFO", "⏸️ 自动交易已停用")
            
            # 更新系统状态
            self._update_system_status()
            return True
            
        except Exception as e:
            log_system("ERROR", f"停用自动交易失败: {e}")
            return False
    
    def enable_evolution(self) -> bool:
        """启用策略进化"""
        try:
            self.evolution_enabled = True
            log_evolution(
                strategy_id="EVOLUTION_SYSTEM",
                action_type="EVOLUTION_ENABLE",
                reason="策略进化系统启用"
            )
            log_system("INFO", "🧬 策略进化已启用")
            
            # 更新系统状态
            self._update_system_status()
            return True
            
        except Exception as e:
            log_system("ERROR", f"启用策略进化失败: {e}")
            return False
    
    def disable_evolution(self) -> bool:
        """停用策略进化"""
        try:
            self.evolution_enabled = False
            log_evolution(
                strategy_id="EVOLUTION_SYSTEM",
                action_type="EVOLUTION_DISABLE",
                reason="策略进化系统停用"
            )
            log_system("INFO", "⏸️ 策略进化已停用")
            
            # 更新系统状态
            self._update_system_status()
            return True
            
        except Exception as e:
            log_system("ERROR", f"停用策略进化失败: {e}")
            return False
    
    def get_system_status(self) -> Dict:
        """获取系统状态"""
        try:
            trading_status = {}
            if self.trading_engine:
                trading_status = self.trading_engine.get_status()
            
            evolution_status = {}
            if self.evolution_engine:
                evolution_status = self.evolution_engine.get_evolution_status()
            
            return {
                'system': {
                    'running': self.running,
                    'auto_trading_enabled': self.auto_trading_enabled,
                    'evolution_enabled': self.evolution_enabled,
                    'start_time': self.start_time.isoformat() if self.start_time else None,
                    'uptime_seconds': self.system_stats['system_uptime'],
                    'stats': self.system_stats
                },
                'trading': trading_status,
                'evolution': evolution_status,
                'health': self.logger.get_system_health_summary()
            }
            
        except Exception as e:
            log_system("ERROR", f"获取系统状态失败: {e}")
            return {'error': str(e)}
    
    def stop(self):
        """停止系统"""
        try:
            log_system("INFO", "🛑 开始停止系统...")
            
            self.running = False
            
            # 停用自动交易
            if self.auto_trading_enabled:
                self.disable_auto_trading()
            
            # 停用策略进化
            if self.evolution_enabled:
                self.disable_evolution()
            
            # 停止量化服务
            if self.quantitative_service:
                self.quantitative_service.stop()
            
            # 等待线程结束
            if self.management_thread and self.management_thread.is_alive():
                self.management_thread.join(timeout=5)
            
            if self.evolution_thread and self.evolution_thread.is_alive():
                self.evolution_thread.join(timeout=5)
            
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5)
            
            log_system("INFO", "✅ 系统已安全停止")
            
        except Exception as e:
            log_system("ERROR", f"停止系统失败: {e}")
    
    def run_interactive(self):
        """运行交互式界面"""
        try:
            print("\n" + "="*60)
            print("🚀 修复版量化交易系统 - 交互式控制台")
            print("="*60)
            
            while self.running:
                print("\n📊 系统状态:")
                print(f"   运行时间: {self.system_stats['system_uptime']//3600}小时{(self.system_stats['system_uptime']%3600)//60}分钟")
                print(f"   自动交易: {'✅ 启用' if self.auto_trading_enabled else '❌ 停用'}")
                print(f"   策略进化: {'✅ 启用' if self.evolution_enabled else '❌ 停用'}")
                print(f"   活跃策略: {self.system_stats['active_strategies']} 个")
                print(f"   今日交易: {self.system_stats['total_trades']} 次")
                print(f"   进化周期: {self.system_stats['total_evolution_cycles']} 次")
                
                print("\n🎯 可用命令:")
                print("   1 - 启用/停用自动交易")
                print("   2 - 启用/停用策略进化")
                print("   3 - 手动执行策略进化")
                print("   4 - 查看详细状态")
                print("   5 - 查看进化日志")
                print("   6 - 查看交易日志")
                print("   q - 退出系统")
                
                print(f"\n🌐 Web界面: http://localhost:8888/quantitative.html")
                
                choice = input("\n请选择操作 (1-6/q): ").strip().lower()
                
                if choice == '1':
                    if self.auto_trading_enabled:
                        self.disable_auto_trading()
                    else:
                        self.enable_auto_trading()
                        
                elif choice == '2':
                    if self.evolution_enabled:
                        self.disable_evolution()
                    else:
                        self.enable_evolution()
                        
                elif choice == '3':
                    if self.evolution_engine:
                        print("\n🧬 执行手动进化...")
                        result = self.evolution_engine.start_evolution_cycle()
                        if result.get('success'):
                            print(f"✅ 进化完成 - 第 {result['generation']} 代")
                            print(f"📊 平均适应性: {result['avg_fitness']:.1f}")
                        else:
                            print(f"❌ 进化失败: {result.get('error', '未知错误')}")
                    else:
                        print("❌ 进化引擎未初始化")
                        
                elif choice == '4':
                    status = self.get_system_status()
                    print(f"\n📋 详细状态:")
                    print(json.dumps(status, indent=2, ensure_ascii=False))
                    
                elif choice == '5':
                    if self.evolution_engine:
                        logs = self.evolution_engine.get_evolution_logs(20)
                        print(f"\n🧬 最近20条进化日志:")
                        for log in logs[-10:]:
                            print(f"   {log['timestamp'][:19]} | {log['action']} | {log['strategy_id'][:8]}")
                    else:
                        print("❌ 进化引擎未初始化")
                        
                elif choice == '6':
                    trading_logs = self.logger.get_trading_logs(days=1)
                    print(f"\n💰 今日交易日志 (最近10条):")
                    for log in trading_logs[-10:]:
                        print(f"   {log['timestamp'][:19]} | {log['action_type']} | {log.get('symbol', 'N/A')} | {log.get('result', log.get('error_message', 'N/A'))}")
                        
                elif choice == 'q':
                    print("\n🛑 正在安全关闭系统...")
                    break
                    
                else:
                    print("❌ 无效选择，请重试")
                
                time.sleep(1)
            
        except KeyboardInterrupt:
            print("\n🛑 收到中断信号")
        except Exception as e:
            log_system("ERROR", f"交互式界面错误: {e}")
        finally:
            self.stop()

# 全局系统实例
_integrated_system = None

def get_fixed_integrated_system():
    """获取修复版集成系统实例"""
    global _integrated_system
    if _integrated_system is None:
        _integrated_system = FixedIntegratedSystem()
    return _integrated_system

def main():
    """主函数"""
    try:
        # 创建系统实例
        system = get_fixed_integrated_system()
        
        # 初始化系统
        if not system.initialize():
            print("❌ 系统初始化失败")
            return
        
        # 启动系统
        if not system.start():
            print("❌ 系统启动失败")
            return
        
        # 默认启用进化
        system.enable_evolution()
        
        # 运行交互式界面
        system.run_interactive()
        
    except Exception as e:
        print(f"❌ 系统运行失败: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 