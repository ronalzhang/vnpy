#!/usr/bin/env python3
"""
增强的策略进化日志显示系统
优化进化日志表格，显示参数变化和效果分析
"""
import psycopg2
import json
from datetime import datetime, timedelta

def enhanced_evolution_display():
    """增强的进化日志显示"""
    print("🧬 === 策略进化日志增强显示系统 ===")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        # 1. 显示最新的进化记录（有参数变化的）
        print("\n🔥 1. 最新进化记录（有参数变化）")
        cursor.execute("""
            SELECT 
                strategy_id, 
                parameters, 
                new_parameters, 
                score_before, 
                score_after, 
                improvement,
                parameter_changes,
                evolution_reason,
                notes,
                created_time
            FROM strategy_evolution_history 
            WHERE parameters IS NOT NULL 
            AND new_parameters IS NOT NULL
            AND parameters != ''
            AND new_parameters != ''
            ORDER BY created_time DESC 
            LIMIT 10
        """)
        
        evolution_records = cursor.fetchall()
        
        if evolution_records:
            print(f"找到 {len(evolution_records)} 条有效进化记录:")
            print("─" * 120)
            print(f"{'序号':<4} {'策略ID':<15} {'评分变化':<12} {'改善':<8} {'参数变化':<40} {'进化原因':<20}")
            print("─" * 120)
            
            for i, record in enumerate(evolution_records, 1):
                strategy_id = record[0][-8:]  # 显示后8位
                score_change = f"{record[3]:.1f}→{record[4]:.1f}"
                improvement = f"+{record[5]:.1f}" if record[5] > 0 else f"{record[5]:.1f}"
                param_changes = record[6][:35] + "..." if record[6] and len(record[6]) > 35 else (record[6] or "N/A")
                reason = record[7][:18] + "..." if record[7] and len(record[7]) > 18 else (record[7] or "N/A")
                
                print(f"{i:<4} {strategy_id:<15} {score_change:<12} {improvement:<8} {param_changes:<40} {reason:<20}")
        else:
            print("⚠️ 没有找到有效的进化记录")
        
        # 2. 分析参数变化效果
        print("\n📊 2. 参数变化效果分析")
        analyze_parameter_effects(cursor)
        
        # 3. 进化成功率统计
        print("\n📈 3. 进化成功率统计")
        analyze_evolution_success_rate(cursor)
        
        # 4. 高效参数变化模式
        print("\n🎯 4. 高效参数变化模式")
        analyze_effective_patterns(cursor)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 增强显示失败: {e}")

def analyze_parameter_effects(cursor):
    """分析参数变化效果"""
    try:
        # 分析各类参数变化的平均效果
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN parameter_changes LIKE '%stop_loss%' THEN 'stop_loss'
                    WHEN parameter_changes LIKE '%take_profit%' THEN 'take_profit'
                    WHEN parameter_changes LIKE '%period%' THEN 'period'
                    WHEN parameter_changes LIKE '%threshold%' THEN 'threshold'
                    WHEN parameter_changes LIKE '%quantity%' THEN 'quantity'
                    ELSE 'other'
                END as param_type,
                COUNT(*) as change_count,
                AVG(improvement) as avg_improvement,
                AVG(score_after - score_before) as avg_score_change,
                COUNT(CASE WHEN improvement > 0 THEN 1 END) as positive_changes
            FROM strategy_evolution_history 
            WHERE parameter_changes IS NOT NULL 
            AND improvement IS NOT NULL
            AND created_time >= CURRENT_TIMESTAMP - INTERVAL '7 days'
            GROUP BY param_type
            ORDER BY avg_improvement DESC
        """)
        
        param_effects = cursor.fetchall()
        
        if param_effects:
            print("   参数类型效果分析:")
            print("   ┌─────────────┬─────────┬───────────┬─────────────┬─────────────┐")
            print("   │ 参数类型    │ 变化次数│ 平均改善  │ 平均评分变化│ 成功率      │")
            print("   ├─────────────┼─────────┼───────────┼─────────────┼─────────────┤")
            
            for effect in param_effects:
                param_type = effect[0]
                count = effect[1]
                avg_improvement = effect[2] or 0
                avg_score_change = effect[3] or 0
                positive_count = effect[4]
                success_rate = (positive_count / count * 100) if count > 0 else 0
                
                print(f"   │ {param_type:<11} │ {count:^7} │ {avg_improvement:^9.2f} │ {avg_score_change:^11.2f} │ {success_rate:^9.1f}% │")
            
            print("   └─────────────┴─────────┴───────────┴─────────────┴─────────────┘")
        else:
            print("   ⚠️ 没有参数效果数据")
    
    except Exception as e:
        print(f"   ❌ 参数效果分析失败: {e}")

def analyze_evolution_success_rate(cursor):
    """分析进化成功率"""
    try:
        # 按时间段分析成功率
        cursor.execute("""
            SELECT 
                DATE(created_time) as evolution_date,
                COUNT(*) as total_evolutions,
                COUNT(CASE WHEN improvement > 0 THEN 1 END) as successful_evolutions,
                AVG(improvement) as avg_improvement,
                MAX(improvement) as max_improvement
            FROM strategy_evolution_history 
            WHERE improvement IS NOT NULL
            AND created_time >= CURRENT_TIMESTAMP - INTERVAL '7 days'
            GROUP BY DATE(created_time)
            ORDER BY evolution_date DESC
        """)
        
        daily_stats = cursor.fetchall()
        
        if daily_stats:
            print("   每日进化成功率:")
            print("   ┌─────────────┬─────────┬─────────┬───────────┬─────────────┐")
            print("   │ 日期        │ 总次数  │ 成功次数│ 成功率    │ 平均改善    │")
            print("   ├─────────────┼─────────┼─────────┼───────────┼─────────────┤")
            
            for stat in daily_stats:
                date = stat[0].strftime('%Y-%m-%d') if stat[0] else 'N/A'
                total = stat[1]
                successful = stat[2]
                success_rate = (successful / total * 100) if total > 0 else 0
                avg_improvement = stat[3] or 0
                
                print(f"   │ {date:<11} │ {total:^7} │ {successful:^7} │ {success_rate:^7.1f}% │ {avg_improvement:^9.2f}   │")
            
            print("   └─────────────┴─────────┴─────────┴───────────┴─────────────┘")
        else:
            print("   ⚠️ 没有每日统计数据")
    
    except Exception as e:
        print(f"   ❌ 成功率分析失败: {e}")

def analyze_effective_patterns(cursor):
    """分析高效的参数变化模式"""
    try:
        # 找出最有效的参数变化模式
        cursor.execute("""
            SELECT 
                parameter_changes,
                COUNT(*) as usage_count,
                AVG(improvement) as avg_improvement,
                MAX(improvement) as max_improvement,
                MIN(improvement) as min_improvement
            FROM strategy_evolution_history 
            WHERE parameter_changes IS NOT NULL 
            AND improvement > 1.0  -- 只看改善超过1分的
            AND created_time >= CURRENT_TIMESTAMP - INTERVAL '7 days'
            GROUP BY parameter_changes
            HAVING COUNT(*) >= 2  -- 至少使用过2次
            ORDER BY avg_improvement DESC
            LIMIT 5
        """)
        
        patterns = cursor.fetchall()
        
        if patterns:
            print("   高效参数变化模式 (Top 5):")
            print("   ┌───┬─────────────────────────────────────────┬─────────┬───────────┐")
            print("   │ # │ 参数变化模式                            │ 使用次数│ 平均改善  │")
            print("   ├───┼─────────────────────────────────────────┼─────────┼───────────┤")
            
            for i, pattern in enumerate(patterns, 1):
                changes = pattern[0][:35] + "..." if len(pattern[0]) > 35 else pattern[0]
                count = pattern[1]
                avg_improvement = pattern[2]
                
                print(f"   │ {i} │ {changes:<39} │ {count:^7} │ {avg_improvement:^9.2f} │")
            
            print("   └───┴─────────────────────────────────────────┴─────────┴───────────┘")
        else:
            print("   ⚠️ 没有发现高效的参数变化模式")
    
    except Exception as e:
        print(f"   ❌ 模式分析失败: {e}")

def create_evolution_report():
    """创建进化报告"""
    print("\n📝 === 生成进化分析报告 ===")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        # 综合统计
        cursor.execute("""
            SELECT 
                COUNT(*) as total_evolutions,
                COUNT(CASE WHEN improvement > 0 THEN 1 END) as successful_evolutions,
                COUNT(CASE WHEN parameters IS NOT NULL AND parameters != '' THEN 1 END) as with_old_params,
                COUNT(CASE WHEN new_parameters IS NOT NULL AND new_parameters != '' THEN 1 END) as with_new_params,
                AVG(improvement) as avg_improvement,
                MAX(improvement) as max_improvement,
                MIN(improvement) as min_improvement
            FROM strategy_evolution_history 
            WHERE created_time >= CURRENT_TIMESTAMP - INTERVAL '7 days'
        """)
        
        summary = cursor.fetchone()
        
        if summary:
            print("📊 7天进化系统总结:")
            print(f"   • 总进化次数: {summary[0]}次")
            print(f"   • 成功进化: {summary[1]}次 ({summary[1]/summary[0]*100:.1f}%)" if summary[0] > 0 else "   • 成功进化: 0次")
            print(f"   • 有旧参数记录: {summary[2]}次 ({summary[2]/summary[0]*100:.1f}%)" if summary[0] > 0 else "   • 有旧参数记录: 0次")
            print(f"   • 有新参数记录: {summary[3]}次 ({summary[3]/summary[0]*100:.1f}%)" if summary[0] > 0 else "   • 有新参数记录: 0次")
            print(f"   • 平均改善: {summary[4]:.2f}分" if summary[4] else "   • 平均改善: 0.00分")
            print(f"   • 最大改善: {summary[5]:.2f}分" if summary[5] else "   • 最大改善: 0.00分")
            print(f"   • 最小变化: {summary[6]:.2f}分" if summary[6] else "   • 最小变化: 0.00分")
        
        # 记录修复效果
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "evolution_system_status": "ENHANCED",
            "parameter_recording": "FIXED",
            "display_optimization": "COMPLETED",
            "summary": summary if summary else "NO_DATA"
        }
        
        with open('/tmp/evolution_enhancement_report.json', 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print("\n✅ 进化分析报告已生成: /tmp/evolution_enhancement_report.json")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 生成报告失败: {e}")

if __name__ == "__main__":
    # 显示增强的进化日志
    enhanced_evolution_display()
    
    # 生成分析报告
    create_evolution_report()
    
    print("\n🎉 策略进化系统增强完成！")
    print("\n📋 增强功能:")
    print("   1. ✅ 详细的参数变化显示")
    print("   2. ✅ 参数效果分析")
    print("   3. ✅ 进化成功率统计")
    print("   4. ✅ 高效变化模式识别")
    print("   5. ✅ 综合进化报告") 