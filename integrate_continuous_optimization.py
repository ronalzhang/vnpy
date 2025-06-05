#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版量化服务 - 完整替代原版后端
包含原版所有功能 + 持续优化系统
"""
import sys
import logging
import time
import threading
from pathlib import Path
from datetime import datetime

# 添加当前路径
sys.path.append(str(Path(__file__).parent))

from quantitative_service import QuantitativeService, AutomatedStrategyManager, EvolutionaryStrategyEngine
from continuous_strategy_optimization import ContinuousOptimizationManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/enhanced_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FullyEnhancedQuantitativeService(QuantitativeService):
    """完全增强版量化服务 - 原版功能 + 持续优化"""
    
    def __init__(self, config_file='crypto_config.json'):
        # 初始化基础量化服务
        super().__init__(config_file)
        
        # 初始化原版核心组件
        self.strategy_manager = None
        self.evolution_engine = None
        
        # 初始化增强功能
        self.continuous_optimizer = None
        
        # 服务状态
        self.running = False
        self.service_thread = None
        
        self._init_all_components()
    
    def _init_all_components(self):
        """初始化所有组件"""
        try:
            logger.info("🔄 初始化完整增强版量化服务...")
            
            # 1. 初始化原版核心组件
            logger.info("📋 初始化原版核心组件...")
            self.strategy_manager = AutomatedStrategyManager(self)
            self.evolution_engine = EvolutionaryStrategyEngine(self)
            logger.info("✅ 原版组件初始化完成")
            
            # 2. 初始化增强功能
            logger.info("🚀 初始化增强优化系统...")
            self.continuous_optimizer = ContinuousOptimizationManager(self)
            logger.info("✅ 增强功能初始化完成")
            
        except Exception as e:
            logger.error(f"组件初始化失败: {e}")
            raise
    
    def start_enhanced_service(self):
        """启动完整增强版服务"""
        try:
            logger.info("🚀 启动完整增强版量化服务...")
            
            # 启动基础服务
            logger.info("📡 启动基础量化服务...")
            # super().start()  # 不调用父类start，因为我们要自定义循环
            
            # 启动增强优化系统
            if self.continuous_optimizer:
                logger.info("🔄 启动持续优化系统...")
                self.continuous_optimizer.start_continuous_optimization()
                logger.info("✅ 持续优化系统已启动")
            
            # 启动主服务循环
            self.running = True
            self.service_thread = threading.Thread(target=self._main_service_loop, daemon=True)
            self.service_thread.start()
            
            logger.info("🎯 完整增强版量化服务启动成功！")
            
        except Exception as e:
            logger.error(f"启动增强服务失败: {e}")
            raise
    
    def stop_enhanced_service(self):
        """停止完整增强版服务"""
        try:
            logger.info("🛑 停止完整增强版服务...")
            
            # 停止主循环
            self.running = False
            
            # 停止持续优化系统
            if self.continuous_optimizer:
                self.continuous_optimizer.stop_continuous_optimization()
                logger.info("✅ 持续优化系统已停止")
            
            # 停止基础服务
            # super().stop()
            
            logger.info("✅ 完整增强版服务已安全停止")
            
        except Exception as e:
            logger.error(f"停止增强服务失败: {e}")
    
    def _main_service_loop(self):
        """主服务循环 - 整合原版功能"""
        logger.info("🔄 启动主服务循环...")
        
        while self.running:
            try:
                # 执行原版核心功能循环
                success = self._run_quantitative_cycle()
                
                if success:
                    logger.debug("💚 系统状态：在线 - 量化系统正常运行")
                else:
                    logger.warning("⚠️ 系统状态：异常 - 正在重试")
                
                # 每60秒运行一次 (与原版保持一致)
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"主服务循环出错: {e}")
                time.sleep(30)  # 出错时等待30秒后重试
    
    def _run_quantitative_cycle(self):
        """运行量化系统循环 - 原版逻辑"""
        try:
            # 计算当前策略统计
            total_strategies = len(self.strategies)
            running_strategies = sum(1 for s in self.strategies.values() if s.get('enabled', False))
            selected_strategies = sum(1 for s in self.strategies.values() if s.get('qualified_for_trading', False))
            
            # 更新系统状态到数据库
            self.update_system_status(
                quantitative_running=True,
                auto_trading_enabled=self.auto_trading_enabled,
                total_strategies=total_strategies,
                running_strategies=running_strategies,
                selected_strategies=selected_strategies,
                system_health='healthy',
                notes='增强版量化服务正常运行'
            )
            
            # 原版核心功能：自动策略管理
            if self.strategy_manager:
                self.strategy_manager.auto_manage_strategies()
                logger.debug("✅ 自动策略管理完成")
            
            # 原版核心功能：策略进化
            if self.evolution_engine:
                evolution_result = self.evolution_engine.run_evolution_cycle()
                if evolution_result:
                    # 更新进化代数
                    current_generation = getattr(self.evolution_engine, 'current_generation', 0)
                    self.update_system_status(current_generation=current_generation)
                logger.debug("✅ 策略进化完成")
            
            return True
            
        except Exception as e:
            logger.error(f"量化系统运行错误: {e}")
            
            # 更新错误状态到数据库
            self.update_system_status(
                system_health='error',
                notes=f'运行错误: {str(e)}'
            )
            
            return False
    
    def get_full_enhanced_status(self):
        """获取完整增强功能状态"""
        try:
            # 基础状态
            base_status = self.get_system_status_from_db()
            
            # 增强优化状态
            optimization_status = {}
            if self.continuous_optimizer:
                optimization_status = self.continuous_optimizer.get_optimization_status()
            
            # 原版组件状态
            strategy_manager_status = {
                'active': bool(self.strategy_manager),
                'last_run': 'running' if self.running else 'stopped'
            }
            
            evolution_engine_status = {
                'active': bool(self.evolution_engine),
                'generation': getattr(self.evolution_engine, 'current_generation', 0) if self.evolution_engine else 0
            }
            
            # 完整状态组合
            full_status = {
                **base_status,
                'service_type': 'fully_enhanced',
                'original_features': {
                    'strategy_manager': strategy_manager_status,
                    'evolution_engine': evolution_engine_status,
                    'auto_trading': self.auto_trading_enabled,
                    'main_loop_running': self.running
                },
                'enhanced_features': {
                    'continuous_optimization': optimization_status,
                    'continuous_simulation': optimization_status.get('system_running', False),
                    'intelligent_optimization': True,
                    'strict_trading_gates': True,
                    'real_time_scoring': True
                },
                'integration_status': {
                    'all_components_active': all([
                        self.strategy_manager,
                        self.evolution_engine, 
                        self.continuous_optimizer,
                        self.running
                    ]),
                    'service_mode': 'full_replacement'
                }
            }
            
            return full_status
            
        except Exception as e:
            logger.error(f"获取完整状态失败: {e}")
            return {'error': str(e)}


class EnhancedBackgroundService:
    """增强版后台服务 - 完整替代原版"""
    
    def __init__(self):
        self.enhanced_service = None
        self.running = False
        
    def initialize(self):
        """初始化增强服务组件"""
        try:
            logger.info("🚀 初始化完整增强版量化交易系统...")
            
            # 创建完整增强版服务实例
            self.enhanced_service = FullyEnhancedQuantitativeService()
            
            logger.info("✅ 完整增强版服务组件初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 初始化失败: {e}")
            return False
    
    def start_background_service(self):
        """启动后台服务"""
        try:
            # 启动增强服务
            self.enhanced_service.start_enhanced_service()
            
            self.running = True
            logger.info("🎯 完整增强版后台服务已启动")
            
            # 保持运行
            while self.running:
                try:
                    # 每小时输出一次综合状态
                    time.sleep(3600)
                    
                    status = self.enhanced_service.get_full_enhanced_status()
                    
                    # 原版功能状态
                    original_ok = status.get('original_features', {}).get('main_loop_running', False)
                    
                    # 增强功能状态  
                    enhanced_ok = status.get('enhanced_features', {}).get('continuous_optimization', {}).get('system_running', False)
                    
                    if original_ok and enhanced_ok:
                        qualified = status.get('enhanced_features', {}).get('continuous_optimization', {}).get('qualified_strategies', 0)
                        total = status.get('enhanced_features', {}).get('continuous_optimization', {}).get('total_strategies', 0)
                        rate = status.get('enhanced_features', {}).get('continuous_optimization', {}).get('qualification_rate', 0)
                        generation = status.get('original_features', {}).get('evolution_engine', {}).get('generation', 0)
                        
                        logger.info(f"📈 完整系统运行正常: {qualified}/{total} 策略合格 ({rate:.1f}%), 第{generation}代")
                    else:
                        logger.warning(f"⚠️ 系统部分异常 - 原版功能: {original_ok}, 增强功能: {enhanced_ok}")
                        
                except KeyboardInterrupt:
                    logger.info("📴 接收到停止信号...")
                    break
                except Exception as e:
                    logger.error(f"状态检查失败: {e}")
                    time.sleep(300)  # 出错后5分钟重试
            
        except Exception as e:
            logger.error(f"启动后台服务失败: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """停止服务"""
        try:
            self.running = False
            
            if self.enhanced_service:
                self.enhanced_service.stop_enhanced_service()
            
            logger.info("🛑 完整增强版后台服务已停止")
            
        except Exception as e:
            logger.error(f"停止服务失败: {e}")


def main():
    """主函数 - 启动完整增强版量化服务"""
    logger.info("="*60)
    logger.info("🌟 校长的完整增强版量化交易系统")
    logger.info("📈 原版功能 + 持续优化 v3.0")
    logger.info("📋 功能特性:")
    logger.info("  ✅ 原版自动策略管理 (AutomatedStrategyManager)")
    logger.info("  ✅ 原版策略进化引擎 (EvolutionaryStrategyEngine)")  
    logger.info("  ✅ 增强持续模拟交易 (每5分钟)")
    logger.info("  ✅ 增强智能参数优化 (每30分钟)")
    logger.info("  ✅ 增强65分严格门槛控制")
    logger.info("  ✅ 增强实时评分更新系统")
    logger.info("="*60)
    
    service = EnhancedBackgroundService()
    
    # 初始化服务
    if not service.initialize():
        logger.error("❌ 服务初始化失败，退出")
        sys.exit(1)
    
    try:
        # 启动后台服务
        service.start_background_service()
    except Exception as e:
        logger.error(f"❌ 服务运行失败: {e}")
        sys.exit(1)
    finally:
        service.stop()


if __name__ == "__main__":
    main() 