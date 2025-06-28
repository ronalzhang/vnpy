#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
策略池优化器 - 维护最优策略池规模
- 清理低分和无效策略
- 保持10000个策略的最优规模
- 确保策略质量和多样性
"""

import psycopg2
import logging
from datetime import datetime, timedelta
from typing import Dict, List

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StrategyPoolOptimizer:
    """策略池优化器"""
    
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'quantitative',
            'user': 'quant_user',
            'password': '123abc74531'
        }
        self.target_pool_size = 10000  # 目标策略池大小
        self.min_score_threshold = 20.0  # 最低保留分数
        
    def get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(**self.db_config)
    
    def analyze_strategy_pool(self) -> Dict:
        """分析当前策略池状况"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 总策略数
            cursor.execute("SELECT COUNT(*) FROM strategies")
            total_count = cursor.fetchone()[0]
            
            # 分值分布
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN final_score >= 80 THEN 1 END) as excellent,
                    COUNT(CASE WHEN final_score >= 60 AND final_score < 80 THEN 1 END) as good,
                    COUNT(CASE WHEN final_score >= 40 AND final_score < 60 THEN 1 END) as medium,
                    COUNT(CASE WHEN final_score >= 20 AND final_score < 40 THEN 1 END) as poor,
                    COUNT(CASE WHEN final_score < 20 THEN 1 END) as very_poor,
                    AVG(final_score) as avg_score,
                    MIN(final_score) as min_score,
                    MAX(final_score) as max_score
                FROM strategies
            """)
            
            score_stats = cursor.fetchone()
            
            # 交易活动分析
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN total_trades > 100 THEN 1 END) as very_active,
                    COUNT(CASE WHEN total_trades > 30 AND total_trades <= 100 THEN 1 END) as active,
                    COUNT(CASE WHEN total_trades > 10 AND total_trades <= 30 THEN 1 END) as moderate,
                    COUNT(CASE WHEN total_trades > 0 AND total_trades <= 10 THEN 1 END) as minimal,
                    COUNT(CASE WHEN total_trades = 0 THEN 1 END) as inactive
                FROM strategies
            """)
            
            activity_stats = cursor.fetchone()
            
            # 最近更新分析
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN updated_at > NOW() - INTERVAL '7 days' THEN 1 END) as recent_week,
                    COUNT(CASE WHEN updated_at > NOW() - INTERVAL '30 days' THEN 1 END) as recent_month,
                    COUNT(CASE WHEN updated_at <= NOW() - INTERVAL '30 days' THEN 1 END) as old_strategies
                FROM strategies
            """)
            
            update_stats = cursor.fetchone()
            
            conn.close()
            
            analysis = {
                'total_count': total_count,
                'target_size': self.target_pool_size,
                'cleanup_needed': total_count - self.target_pool_size,
                'score_distribution': {
                    'excellent': score_stats[0],  # ≥80分
                    'good': score_stats[1],       # 60-80分
                    'medium': score_stats[2],     # 40-60分
                    'poor': score_stats[3],       # 20-40分
                    'very_poor': score_stats[4],  # <20分
                    'avg_score': float(score_stats[5]),
                    'min_score': float(score_stats[6]),
                    'max_score': float(score_stats[7])
                },
                'activity_distribution': {
                    'very_active': activity_stats[0],    # >100次交易
                    'active': activity_stats[1],         # 30-100次
                    'moderate': activity_stats[2],       # 10-30次
                    'minimal': activity_stats[3],        # 1-10次
                    'inactive': activity_stats[4]        # 0次交易
                },
                'update_distribution': {
                    'recent_week': update_stats[0],      # 最近7天
                    'recent_month': update_stats[1],     # 最近30天
                    'old_strategies': update_stats[2]    # 30天前
                }
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ 策略池分析失败: {e}")
            conn.close()
            return {}
    
    def identify_cleanup_candidates(self) -> List[str]:
        """识别需要清理的策略"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 清理策略的优先级规则
            cleanup_queries = []
            
            # 1. 超低分策略 (评分<20分)
            cleanup_queries.append((
                "very_low_score",
                "SELECT id FROM strategies WHERE final_score < 20 ORDER BY final_score ASC",
                "清理超低分策略"
            ))
            
            # 2. 无交易记录的低分策略 (评分<40分且无交易)
            cleanup_queries.append((
                "inactive_low_score", 
                "SELECT id FROM strategies WHERE final_score < 40 AND total_trades = 0 ORDER BY final_score ASC",
                "清理无交易的低分策略"
            ))
            
            # 3. 长期未更新的中低分策略 (评分<50分且30天未更新)
            cleanup_queries.append((
                "outdated_medium_score",
                "SELECT id FROM strategies WHERE final_score < 50 AND updated_at < NOW() - INTERVAL '30 days' ORDER BY final_score ASC, updated_at ASC",
                "清理过时的中低分策略"
            ))
            
            # 4. 极少交易的低分策略 (评分<45分且交易<5次)
            cleanup_queries.append((
                "minimal_activity_low_score",
                "SELECT id FROM strategies WHERE final_score < 45 AND total_trades < 5 ORDER BY final_score ASC, total_trades ASC",
                "清理低活跃度策略"
            ))
            
            cleanup_candidates = []
            current_count = self.analyze_strategy_pool()['total_count']
            target_cleanup = current_count - self.target_pool_size
            
            logger.info(f"🎯 目标清理策略数: {target_cleanup}")
            
            for category, query, description in cleanup_queries:
                if len(cleanup_candidates) >= target_cleanup:
                    break
                    
                cursor.execute(query)
                category_candidates = [row[0] for row in cursor.fetchall()]
                
                # 限制每个类别的清理数量
                remaining_needed = target_cleanup - len(cleanup_candidates)
                category_candidates = category_candidates[:remaining_needed]
                
                cleanup_candidates.extend(category_candidates)
                logger.info(f"📋 {description}: {len(category_candidates)}个策略")
            
            conn.close()
            logger.info(f"✅ 总计识别清理候选: {len(cleanup_candidates)}个策略")
            return cleanup_candidates[:target_cleanup]
            
        except Exception as e:
            logger.error(f"❌ 识别清理候选失败: {e}")
            conn.close()
            return []
    
    def backup_strategies(self, strategy_ids: List[str]) -> bool:
        """备份将要删除的策略"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 创建备份表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategies_backup (
                    id VARCHAR PRIMARY KEY,
                    backup_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    original_data JSONB,
                    deletion_reason TEXT
                )
            """)
            
            # 备份策略数据
            for strategy_id in strategy_ids:
                cursor.execute("""
                    SELECT row_to_json(s) FROM strategies s WHERE id = %s
                """, (strategy_id,))
                
                strategy_data = cursor.fetchone()
                if strategy_data:
                    cursor.execute("""
                        INSERT INTO strategies_backup (id, original_data, deletion_reason)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            backup_time = CURRENT_TIMESTAMP,
                            original_data = EXCLUDED.original_data,
                            deletion_reason = EXCLUDED.deletion_reason
                    """, (strategy_id, strategy_data[0], "策略池优化清理"))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ 策略备份完成: {len(strategy_ids)}个策略")
            return True
            
        except Exception as e:
            logger.error(f"❌ 策略备份失败: {e}")
            return False
    
    def cleanup_strategies(self, strategy_ids: List[str]) -> bool:
        """清理策略"""
        if not strategy_ids:
            logger.info("📝 无需清理策略")
            return True
            
        try:
            # 先备份
            if not self.backup_strategies(strategy_ids):
                logger.error("❌ 备份失败，取消清理操作")
                return False
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 删除相关的交易信号
            cursor.execute("""
                DELETE FROM trading_signals 
                WHERE strategy_id = ANY(%s)
            """, (strategy_ids,))
            
            deleted_signals = cursor.rowcount
            logger.info(f"🗑️ 清理交易信号: {deleted_signals}条")
            
            # 删除策略优化日志
            cursor.execute("""
                DELETE FROM strategy_optimization_logs 
                WHERE strategy_id = ANY(%s)
            """, (strategy_ids,))
            
            deleted_logs = cursor.rowcount
            logger.info(f"🗑️ 清理优化日志: {deleted_logs}条")
            
            # 删除策略
            cursor.execute("""
                DELETE FROM strategies 
                WHERE id = ANY(%s)
            """, (strategy_ids,))
            
            deleted_strategies = cursor.rowcount
            logger.info(f"🗑️ 清理策略: {deleted_strategies}个")
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ 策略池清理完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 策略清理失败: {e}")
            return False
    
    def optimize_pool(self) -> Dict:
        """执行策略池优化"""
        logger.info("🚀 开始策略池优化")
        
        # 分析当前状况
        analysis = self.analyze_strategy_pool()
        if not analysis:
            return {'success': False, 'message': '策略池分析失败'}
        
        logger.info(f"📊 当前策略池: {analysis['total_count']}个策略")
        logger.info(f"🎯 目标规模: {analysis['target_size']}个策略")
        
        if analysis['cleanup_needed'] <= 0:
            logger.info("✅ 策略池规模已达标，无需清理")
            return {
                'success': True,
                'message': '策略池规模已达标',
                'analysis': analysis,
                'cleaned': 0
            }
        
        # 识别清理候选
        cleanup_candidates = self.identify_cleanup_candidates()
        if not cleanup_candidates:
            logger.warning("⚠️ 未找到合适的清理候选策略")
            return {
                'success': False,
                'message': '未找到合适的清理候选',
                'analysis': analysis
            }
        
        # 执行清理
        success = self.cleanup_strategies(cleanup_candidates)
        
        # 再次分析验证结果
        final_analysis = self.analyze_strategy_pool()
        
        result = {
            'success': success,
            'message': f"策略池优化{'成功' if success else '失败'}",
            'before_analysis': analysis,
            'after_analysis': final_analysis,
            'cleaned': len(cleanup_candidates) if success else 0
        }
        
        if success:
            logger.info(f"🎉 策略池优化成功: {analysis['total_count']} → {final_analysis['total_count']}个策略")
        else:
            logger.error(f"❌ 策略池优化失败")
        
        return result
    
    def generate_report(self, result: Dict) -> str:
        """生成优化报告"""
        if not result.get('success'):
            return f"策略池优化失败: {result.get('message', '未知错误')}"
        
        before = result['before_analysis']
        after = result['after_analysis']
        
        report = f"""
📊 策略池优化报告
================

🎯 优化目标: 维护{self.target_pool_size}个策略的最优规模

📈 优化结果:
• 优化前策略数: {before['total_count']}个
• 优化后策略数: {after['total_count']}个  
• 清理策略数: {result['cleaned']}个
• 规模达标率: {(after['total_count']/self.target_pool_size*100):.1f}%

📊 分值分布变化:
• 优秀策略(≥80分): {before['score_distribution']['excellent']} → {after['score_distribution']['excellent']}
• 良好策略(60-80分): {before['score_distribution']['good']} → {after['score_distribution']['good']}
• 中等策略(40-60分): {before['score_distribution']['medium']} → {after['score_distribution']['medium']}
• 较差策略(20-40分): {before['score_distribution']['poor']} → {after['score_distribution']['poor']}
• 极差策略(<20分): {before['score_distribution']['very_poor']} → {after['score_distribution']['very_poor']}

📈 质量指标:
• 平均分值: {before['score_distribution']['avg_score']:.2f} → {after['score_distribution']['avg_score']:.2f}
• 活跃策略(>30次交易): {before['activity_distribution']['active'] + before['activity_distribution']['very_active']} → {after['activity_distribution']['active'] + after['activity_distribution']['very_active']}

✅ 优化效果: {"策略池规模和质量均得到优化" if after['total_count'] <= self.target_pool_size else "需要进一步优化"}
        """
        
        return report.strip()

def main():
    """主函数"""
    optimizer = StrategyPoolOptimizer()
    
    # 执行优化
    result = optimizer.optimize_pool()
    
    # 生成报告
    report = optimizer.generate_report(result)
    print(report)
    
    # 保存报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"strategy_pool_optimization_report_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📄 报告已保存至: {report_file}")

if __name__ == "__main__":
    main() 