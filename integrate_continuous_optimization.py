#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成持续优化系统到现有量化服务
解决策略只初始化模拟的问题，实现真正的持续优化
"""
import sys
import logging
import time
from pathlib import Path

# 添加当前路径
sys.path.append(str(Path(__file__).parent))

from quantitative_service import QuantitativeService
from continuous_strategy_optimization import ContinuousOptimizationManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/integration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnhancedQuantitativeService(QuantitativeService):
    """增强版量化服务 - 集成持续优化功能"""
    
    def __init__(self, config_file='crypto_config.json'):
        super().__init__(config_file)
        
        # 初始化持续优化管理器
        self.continuous_optimizer = None
        self._init_continuous_optimization()
    
    def _init_continuous_optimization(self):
        """初始化持续优化系统"""
        try:
            logger.info("🔄 初始化持续优化系统...")
            self.continuous_optimizer = ContinuousOptimizationManager(self)
            logger.info("✅ 持续优化系统初始化完成")
        except Exception as e:
            logger.error(f"初始化持续优化系统失败: {e}")
    
    def start(self):
        """启动增强版量化服务"""
        try:
            # 启动基础服务
            super().start()
            
            # 启动持续优化系统
            if self.continuous_optimizer:
                self.continuous_optimizer.start_continuous_optimization()
                logger.info("🚀 持续优化系统已启动")
            else:
                logger.warning("⚠️ 持续优化系统未初始化")
                
        except Exception as e:
            logger.error(f"启动增强服务失败: {e}")
            raise
    
    def stop(self):
        """停止增强版量化服务"""
        try:
            # 停止持续优化系统
            if self.continuous_optimizer:
                self.continuous_optimizer.stop_continuous_optimization()
                logger.info("🛑 持续优化系统已停止")
            
            # 停止基础服务
            super().stop()
            
        except Exception as e:
            logger.error(f"停止增强服务失败: {e}")
    
    def get_enhanced_status(self):
        """获取增强功能状态"""
        try:
            base_status = self.get_system_status_from_db()
            
            if self.continuous_optimizer:
                optimization_status = self.continuous_optimizer.get_optimization_status()
                
                enhanced_status = {
                    **base_status,
                    'continuous_optimization': optimization_status,
                    'features': {
                        'continuous_simulation': optimization_status.get('system_running', False),
                        'intelligent_optimization': True,
                        'strict_trading_gates': True,
                        'real_time_scoring': True
                    }
                }
            else:
                enhanced_status = {
                    **base_status,
                    'continuous_optimization': {'system_running': False, 'error': 'Not initialized'},
                    'features': {
                        'continuous_simulation': False,
                        'intelligent_optimization': False,
                        'strict_trading_gates': False,
                        'real_time_scoring': False
                    }
                }
            
            return enhanced_status
            
        except Exception as e:
            logger.error(f"获取增强状态失败: {e}")
            return {'error': str(e)}
    
    def force_optimization_cycle(self):
        """强制执行一轮优化"""
        if self.continuous_optimizer:
            logger.info("🔧 强制执行优化周期...")
            try:
                # 手动触发优化
                underperforming = self.continuous_optimizer._identify_underperforming_strategies()
                if underperforming:
                    self.continuous_optimizer._optimize_strategies(underperforming)
                
                # 更新交易权限
                self.continuous_optimizer.trading_gatekeeper.update_trading_permissions()
                
                logger.info("✅ 强制优化周期完成")
                return True
            except Exception as e:
                logger.error(f"强制优化失败: {e}")
                return False
        else:
            logger.warning("持续优化系统未初始化")
            return False
    
    def get_strategy_optimization_history(self, strategy_id: str = None, limit: int = 20):
        """获取策略优化历史"""
        try:
            if strategy_id:
                query = """
                    SELECT strategy_id, optimization_date, old_parameters, new_parameters, optimization_reason
                    FROM strategy_optimization_log 
                    WHERE strategy_id = ?
                    ORDER BY optimization_date DESC LIMIT ?
                """
                params = (strategy_id, limit)
            else:
                query = """
                    SELECT strategy_id, optimization_date, old_parameters, new_parameters, optimization_reason
                    FROM strategy_optimization_log 
                    ORDER BY optimization_date DESC LIMIT ?
                """
                params = (limit,)
            
            results = self.db_manager.execute_query(query, params, fetch_all=True)
            
            history = []
            for row in results:
                history.append({
                    'strategy_id': row[0],
                    'optimization_date': row[1],
                    'old_parameters': row[2],
                    'new_parameters': row[3],
                    'optimization_reason': row[4]
                })
            
            return {'success': True, 'data': history}
            
        except Exception as e:
            logger.error(f"获取优化历史失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_strategy_simulation_history(self, strategy_id: str, limit: int = 30):
        """获取策略模拟历史"""
        try:
            results = self.db_manager.execute_query("""
                SELECT simulation_date, score, win_rate, total_return, total_trades, success
                FROM strategy_simulation_history 
                WHERE strategy_id = ?
                ORDER BY simulation_date DESC LIMIT ?
            """, (strategy_id, limit), fetch_all=True)
            
            history = []
            for row in results:
                history.append({
                    'simulation_date': row[0],
                    'score': row[1],
                    'win_rate': row[2],
                    'total_return': row[3],
                    'total_trades': row[4],
                    'success': bool(row[5])
                })
            
            return {'success': True, 'data': history}
            
        except Exception as e:
            logger.error(f"获取模拟历史失败: {e}")
            return {'success': False, 'error': str(e)}


def main():
    """主函数 - 启动增强版量化服务"""
    logger.info("🚀 启动增强版量化交易系统...")
    
    try:
        # 创建增强服务实例
        service = EnhancedQuantitativeService()
        
        logger.info("📋 系统功能列表:")
        logger.info("  ✅ 持续模拟交易循环 (5分钟间隔)")
        logger.info("  ✅ 智能参数优化")
        logger.info("  ✅ 严格65分交易门槛")
        logger.info("  ✅ 实时评分更新")
        logger.info("  ✅ 自动策略淘汰")
        logger.info("  ✅ 完整优化历史追踪")
        
        # 启动服务
        service.start()
        
        logger.info("🎯 增强版量化系统启动成功！")
        logger.info("📊 系统将持续优化策略直到达到65分交易门槛")
        
        # 保持运行
        try:
            while True:
                # 每小时输出一次状态
                time.sleep(3600)
                
                status = service.get_enhanced_status()
                opt_status = status.get('continuous_optimization', {})
                
                if opt_status.get('system_running', False):
                    qualified = opt_status.get('qualified_strategies', 0)
                    total = opt_status.get('total_strategies', 0)
                    rate = opt_status.get('qualification_rate', 0)
                    
                    logger.info(f"📈 系统运行正常: {qualified}/{total} 策略合格 ({rate:.1f}%)")
                else:
                    logger.warning("⚠️ 持续优化系统未运行")
                
        except KeyboardInterrupt:
            logger.info("📴 接收到停止信号...")
            service.stop()
            logger.info("✅ 系统已安全停止")
            
    except Exception as e:
        logger.error(f"启动系统失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 