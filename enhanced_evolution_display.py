#!/usr/bin/env python3
"""
增强的进化显示系统
支持新旧参数对比、成功率影响分析、分页显示等完整功能
"""

import psycopg2
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from decimal import Decimal

class EnhancedEvolutionDisplay:
    def __init__(self, db_config=None):
        """初始化进化显示系统"""
        self.db_config = db_config or {
            'host': 'localhost',
            'database': 'quantitative',
            'user': 'quant_user',
            'password': '123abc74531'
        }
        
    def get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(**self.db_config)
    
    def get_strategy_evolution_logs_paginated(self, strategy_id: str, page: int = 1, page_size: int = 30) -> Dict[str, Any]:
        """
        获取策略的分页进化日志，包含完整的参数对比分析
        
        Args:
            strategy_id: 策略ID
            page: 页码（从1开始）
            page_size: 每页记录数
            
        Returns:
            包含进化日志、分页信息、参数对比的完整数据
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 计算偏移量
            offset = (page - 1) * page_size
            
            # 获取总记录数
            cursor.execute("""
                SELECT COUNT(*) FROM unified_strategy_logs 
                WHERE strategy_id = %s AND log_type = 'evolution'
            """, (strategy_id,))
            total_count = cursor.fetchone()[0]
            total_pages = (total_count + page_size - 1) // page_size
            
            # 获取分页的进化日志
            cursor.execute("""
                SELECT 
                    strategy_id, timestamp, cycle_id, evolution_type,
                    old_parameters, new_parameters, trigger_reason,
                    strategy_score, target_success_rate, improvement,
                    success, notes, metadata
                FROM unified_strategy_logs 
                WHERE strategy_id = %s AND log_type = 'evolution'
                ORDER BY timestamp DESC 
                LIMIT %s OFFSET %s
            """, (strategy_id, page_size, offset))
            
            rows = cursor.fetchall()
            evolution_logs = []
            
            for row in rows:
                log_entry = {
                    'strategy_id': row[0],
                    'timestamp': row[1].strftime('%Y-%m-%d %H:%M:%S') if row[1] else None,
                    'cycle_id': row[2],
                    'evolution_type': row[3],
                    'old_parameters': row[4] if row[4] else {},
                    'new_parameters': row[5] if row[5] else {},
                    'trigger_reason': row[6],
                    'strategy_score': float(row[7]) if row[7] else 0,
                    'target_success_rate': float(row[8]) if row[8] else 0,
                    'improvement': float(row[9]) if row[9] else 0,
                    'success': bool(row[10]) if row[10] is not None else False,
                    'notes': row[11],
                    'metadata': row[12] if row[12] else {}
                }
                
                # 添加详细的参数对比分析
                if log_entry['old_parameters'] and log_entry['new_parameters']:
                    log_entry['parameter_analysis'] = self._analyze_parameter_changes(
                        log_entry['old_parameters'], 
                        log_entry['new_parameters'],
                        log_entry['improvement']
                    )
                
                # 添加成功率影响分析
                log_entry['impact_analysis'] = self._analyze_evolution_impact(
                    log_entry['strategy_score'],
                    log_entry['target_success_rate'],
                    log_entry['improvement'],
                    log_entry['success']
                )
                
                evolution_logs.append(log_entry)
            
            # 获取策略的整体进化趋势
            trend_analysis = self._get_evolution_trend(cursor, strategy_id)
            
            conn.close()
            
            return {
                'success': True,
                'strategy_id': strategy_id,
                'evolution_logs': evolution_logs,
                'pagination': {
                    'current_page': page,
                    'total_pages': total_pages,
                    'total_count': total_count,
                    'page_size': page_size,
                    'has_next': page < total_pages,
                    'has_prev': page > 1,
                    'next_page': page + 1 if page < total_pages else None,
                    'prev_page': page - 1 if page > 1 else None
                },
                'trend_analysis': trend_analysis,
                'message': f"✅ 获取到 {len(evolution_logs)} 条进化日志 (第{page}页，共{total_pages}页)"
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取进化日志失败: {str(e)}',
                'evolution_logs': [],
                'pagination': {'current_page': 1, 'total_pages': 0, 'total_count': 0, 'page_size': page_size}
            }
    
    def _analyze_parameter_changes(self, old_params: Dict, new_params: Dict, improvement: float) -> Dict[str, Any]:
        """
        深度分析参数变化及其影响
        
        Args:
            old_params: 旧参数
            new_params: 新参数
            improvement: 改进幅度
            
        Returns:
            参数变化分析结果
        """
        changes = []
        
        # 所有参数键的合集
        all_keys = set(list(old_params.keys()) + list(new_params.keys()))
        
        for key in all_keys:
            old_val = old_params.get(key)
            new_val = new_params.get(key)
            
            if old_val != new_val:
                change_info = {
                    'parameter': key,
                    'old_value': old_val,
                    'new_value': new_val,
                    'change_type': self._get_change_type(old_val, new_val),
                    'impact_level': 'unknown'
                }
                
                # 计算数值变化百分比
                if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)) and old_val != 0:
                    change_percent = ((new_val - old_val) / old_val) * 100
                    change_info['change_percent'] = round(change_percent, 2)
                    change_info['impact_level'] = self._assess_impact_level(abs(change_percent))
                
                # 根据参数名称判断影响类型
                change_info['parameter_category'] = self._categorize_parameter(key)
                
                changes.append(change_info)
        
        return {
            'total_changes': len(changes),
            'parameter_changes': changes,
            'overall_improvement': improvement,
            'change_summary': self._summarize_changes(changes),
            'risk_assessment': self._assess_change_risk(changes, improvement)
        }
    
    def _analyze_evolution_impact(self, strategy_score: float, target_success_rate: float, 
                                improvement: float, success: bool) -> Dict[str, Any]:
        """
        分析进化对策略性能的影响
        
        Args:
            strategy_score: 策略评分
            target_success_rate: 目标成功率
            improvement: 改进幅度
            success: 是否成功
            
        Returns:
            影响分析结果
        """
        return {
            'performance_impact': {
                'score_impact': self._assess_score_impact(strategy_score, improvement),
                'success_rate_impact': self._assess_success_rate_impact(target_success_rate, improvement),
                'overall_success': success
            },
            'improvement_analysis': {
                'improvement_magnitude': abs(improvement),
                'improvement_direction': 'positive' if improvement > 0 else 'negative' if improvement < 0 else 'neutral',
                'improvement_level': self._categorize_improvement(improvement)
            },
            'quality_metrics': {
                'strategy_grade': self._grade_strategy_score(strategy_score),
                'evolution_effectiveness': self._assess_evolution_effectiveness(improvement, success),
                'recommended_action': self._recommend_action(strategy_score, improvement, success)
            }
        }
    
    def _get_evolution_trend(self, cursor, strategy_id: str) -> Dict[str, Any]:
        """
        获取策略的整体进化趋势
        
        Args:
            cursor: 数据库游标
            strategy_id: 策略ID
            
        Returns:
            进化趋势分析
        """
        try:
            # 获取最近20次进化的趋势
            cursor.execute("""
                SELECT 
                    timestamp, strategy_score, improvement, success,
                    target_success_rate
                FROM unified_strategy_logs 
                WHERE strategy_id = %s AND log_type = 'evolution'
                ORDER BY timestamp DESC 
                LIMIT 20
            """, (strategy_id,))
            
            trend_data = cursor.fetchall()
            
            if not trend_data:
                return {'has_data': False, 'message': '暂无进化数据'}
            
            scores = [float(row[1]) if row[1] else 0 for row in trend_data]
            improvements = [float(row[2]) if row[2] else 0 for row in trend_data]
            success_rates = [float(row[4]) if row[4] else 0 for row in trend_data]
            
            return {
                'has_data': True,
                'trend_direction': self._calculate_trend_direction(scores),
                'average_improvement': sum(improvements) / len(improvements) if improvements else 0,
                'success_ratio': sum(1 for row in trend_data if row[3]) / len(trend_data),
                'score_trend': {
                    'current': scores[0] if scores else 0,
                    'highest': max(scores) if scores else 0,
                    'lowest': min(scores) if scores else 0,
                    'average': sum(scores) / len(scores) if scores else 0
                },
                'evolution_frequency': len(trend_data),
                'recommendation': self._generate_evolution_recommendation(scores, improvements, success_rates)
            }
            
        except Exception as e:
            return {'has_data': False, 'error': str(e)}
    
    def _get_change_type(self, old_val, new_val) -> str:
        """判断变化类型"""
        if old_val is None and new_val is not None:
            return 'added'
        elif old_val is not None and new_val is None:
            return 'removed'
        else:
            return 'modified'
    
    def _assess_impact_level(self, change_percent: float) -> str:
        """评估影响级别"""
        if change_percent < 5:
            return 'low'
        elif change_percent < 20:
            return 'medium'
        elif change_percent < 50:
            return 'high'
        else:
            return 'extreme'
    
    def _categorize_parameter(self, param_name: str) -> str:
        """参数分类"""
        risk_params = ['stop_loss', 'take_profit', 'max_position']
        signal_params = ['signal_threshold', 'entry_condition', 'exit_condition']
        timing_params = ['time_window', 'frequency', 'interval']
        
        param_lower = param_name.lower()
        
        if any(risk_param in param_lower for risk_param in risk_params):
            return 'risk_management'
        elif any(signal_param in param_lower for signal_param in signal_params):
            return 'signal_generation'
        elif any(timing_param in param_lower for timing_param in timing_params):
            return 'timing_control'
        else:
            return 'general'
    
    def _summarize_changes(self, changes: List[Dict]) -> str:
        """总结参数变化"""
        if not changes:
            return "无参数变化"
        
        categories = {}
        for change in changes:
            category = change['parameter_category']
            categories[category] = categories.get(category, 0) + 1
        
        summary_parts = []
        for category, count in categories.items():
            summary_parts.append(f"{category}: {count}项")
        
        return f"共{len(changes)}项变化 ({', '.join(summary_parts)})"
    
    def _assess_change_risk(self, changes: List[Dict], improvement: float) -> str:
        """评估变化风险"""
        if not changes:
            return 'no_risk'
        
        high_impact_count = sum(1 for change in changes if change.get('impact_level') in ['high', 'extreme'])
        risk_param_count = sum(1 for change in changes if change.get('parameter_category') == 'risk_management')
        
        if high_impact_count > 3 or risk_param_count > 1:
            return 'high_risk'
        elif high_impact_count > 1 or risk_param_count > 0:
            return 'medium_risk'
        else:
            return 'low_risk'
    
    def _assess_score_impact(self, score: float, improvement: float) -> str:
        """评估评分影响"""
        if improvement > 5:
            return 'significant_improvement'
        elif improvement > 0:
            return 'minor_improvement'
        elif improvement < -5:
            return 'significant_decline'
        elif improvement < 0:
            return 'minor_decline'
        else:
            return 'no_change'
    
    def _assess_success_rate_impact(self, success_rate: float, improvement: float) -> str:
        """评估成功率影响"""
        if success_rate > 0.8 and improvement > 0:
            return 'excellent_performance'
        elif success_rate > 0.6 and improvement > 0:
            return 'good_performance'
        elif success_rate > 0.4:
            return 'average_performance'
        else:
            return 'poor_performance'
    
    def _categorize_improvement(self, improvement: float) -> str:
        """改进幅度分类"""
        if improvement > 10:
            return 'major_improvement'
        elif improvement > 3:
            return 'moderate_improvement'
        elif improvement > 0:
            return 'minor_improvement'
        elif improvement > -3:
            return 'minor_decline'
        elif improvement > -10:
            return 'moderate_decline'
        else:
            return 'major_decline'
    
    def _grade_strategy_score(self, score: float) -> str:
        """策略评分等级"""
        if score >= 90:
            return 'A+'
        elif score >= 80:
            return 'A'
        elif score >= 70:
            return 'B'
        elif score >= 60:
            return 'C'
        else:
            return 'D'
    
    def _assess_evolution_effectiveness(self, improvement: float, success: bool) -> str:
        """评估进化有效性"""
        if success and improvement > 5:
            return 'highly_effective'
        elif success and improvement > 0:
            return 'effective'
        elif success:
            return 'moderately_effective'
        else:
            return 'ineffective'
    
    def _recommend_action(self, score: float, improvement: float, success: bool) -> str:
        """推荐操作"""
        if score >= 80 and improvement > 0:
            return 'maintain_current_direction'
        elif score >= 60 and improvement > 0:
            return 'continue_optimization'
        elif score >= 60 and improvement <= 0:
            return 'review_parameters'
        else:
            return 'consider_major_adjustment'
    
    def _calculate_trend_direction(self, scores: List[float]) -> str:
        """计算趋势方向"""
        if len(scores) < 2:
            return 'insufficient_data'
        
        recent_avg = sum(scores[:5]) / min(5, len(scores))
        older_avg = sum(scores[-5:]) / min(5, len(scores))
        
        if recent_avg > older_avg + 2:
            return 'improving'
        elif recent_avg < older_avg - 2:
            return 'declining'
        else:
            return 'stable'
    
    def _generate_evolution_recommendation(self, scores: List[float], improvements: List[float], success_rates: List[float]) -> str:
        """生成进化建议"""
        if not scores:
            return "需要更多数据来分析"
        
        current_score = scores[0]
        avg_improvement = sum(improvements) / len(improvements) if improvements else 0
        
        if current_score >= 80 and avg_improvement > 0:
            return "策略表现优秀，建议保持当前进化方向"
        elif current_score >= 60 and avg_improvement > 0:
            return "策略表现良好，建议继续当前优化策略"
        elif avg_improvement <= 0:
            return "建议调整进化策略，考虑更大幅度的参数变化"
        else:
            return "建议增加进化频率，探索更多参数空间"

# 测试函数
def test_evolution_display():
    """测试进化显示功能"""
    display = EnhancedEvolutionDisplay()
    
    # 测试获取某个策略的进化日志
    result = display.get_strategy_evolution_logs_paginated('STRAT_0035', page=1, page_size=30)
    
    if result['success']:
        print(f"✅ 成功获取进化日志")
        print(f"📊 分页信息: {result['pagination']}")
        print(f"📈 趋势分析: {result['trend_analysis']}")
        
        if result['evolution_logs']:
            first_log = result['evolution_logs'][0]
            print(f"🔍 示例日志:")
            print(f"  时间: {first_log['timestamp']}")
            print(f"  进化类型: {first_log['evolution_type']}")
            if 'parameter_analysis' in first_log:
                print(f"  参数变化: {first_log['parameter_analysis']['change_summary']}")
            if 'impact_analysis' in first_log:
                print(f"  影响评估: {first_log['impact_analysis']['quality_metrics']['recommended_action']}")
    else:
        print(f"❌ 获取失败: {result['message']}")

if __name__ == "__main__":
    test_evolution_display() 