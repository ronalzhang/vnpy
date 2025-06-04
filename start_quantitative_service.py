#!/usr/bin/env python3
"""
🚀 无GUI量化交易系统后台服务启动器
专门用于服务器部署的量化系统启动脚本
"""

import sys
import time
import threading
import logging
from quantitative_service import QuantitativeService, AutomatedStrategyManager, EvolutionaryStrategyEngine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('quantitative_service.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class QuantitativeBackgroundService:
    """量化交易后台服务"""
    
    def __init__(self):
        self.quantitative_service = None
        self.manager = None
        self.engine = None
        self.running = False
        
    def initialize(self):
        """初始化量化服务组件"""
        try:
            logger.info("🚀 初始化量化交易系统...")
            
            # 先创建QuantitativeService实例
            self.quantitative_service = QuantitativeService()
            
            # 使用QuantitativeService实例初始化管理器
            self.manager = AutomatedStrategyManager(self.quantitative_service)
            self.engine = EvolutionaryStrategyEngine()
            
            logger.info("✅ 量化服务组件初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 初始化失败: {e}")
            return False
    
    def run_quantitative_cycle(self):
        """运行一次量化系统循环"""
        try:
            # 策略评估和选择
            self.manager.evaluate_and_select_strategies()
            logger.info("✅ 策略评估完成")
            
            # 策略进化
            self.engine.evolve()
            logger.info("✅ 策略进化完成")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 量化系统运行错误: {e}")
            return False
    
    def start_background_service(self):
        """启动后台服务循环"""
        self.running = True
        logger.info("🎯 量化系统后台服务已启动")
        
        while self.running:
            try:
                success = self.run_quantitative_cycle()
                
                if success:
                    logger.info("💚 系统状态：在线 - 量化系统正常运行")
                else:
                    logger.warning("⚠️  系统状态：异常 - 正在重试")
                
                # 每60秒运行一次
                time.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("🛑 收到停止信号，正在关闭服务...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"❌ 未预期错误: {e}")
                time.sleep(30)  # 出错时等待30秒后重试
    
    def stop(self):
        """停止服务"""
        self.running = False
        logger.info("🛑 量化系统后台服务已停止")

def main():
    """主函数"""
    logger.info("="*60)
    logger.info("🌟 校长的渐进式智能进化量化交易系统")
    logger.info("📈 后台服务启动器 v2.0")
    logger.info("="*60)
    
    service = QuantitativeBackgroundService()
    
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