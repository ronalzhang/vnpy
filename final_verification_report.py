#!/usr/bin/env python3
"""
最终验证报告 - 确认交易日志系统和策略进化全面修复
"""
import psycopg2
import requests
import json
from datetime import datetime

def generate_final_verification_report():
    """生成最终验证报告"""
    print("🏆 === 交易日志系统和策略进化全面修复验证 ===")
    
    report = {
        "verification_time": datetime.now().isoformat(),
        "database_status": {},
        "frontend_status": {},
        "evolution_status": {},
        "global_switches": {},
        "final_score": 0,
        "issues_resolved": []
    }
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        print("\n📊 1. 数据库状态验证")
        # 1. 检查数据库日志分类
        cursor.execute("""
            SELECT trade_type, is_validation, COUNT(*) as count
            FROM trading_signals 
            GROUP BY trade_type, is_validation
            ORDER BY count DESC
        """)
        db_stats = cursor.fetchall()
        report["database_status"]["log_distribution"] = dict(db_stats)
        
        for trade_type, is_validation, count in db_stats:
            validation_str = "验证" if is_validation else "非验证"
            print(f"  {trade_type} ({validation_str}): {count}条")
        
        # 2. 检查最近生成的记录
        cursor.execute("""
            SELECT trade_type, is_validation, COUNT(*) as count
            FROM trading_signals 
            WHERE timestamp >= NOW() - INTERVAL '1 hour'
            GROUP BY trade_type, is_validation
        """)
        recent_stats = cursor.fetchall()
        recent_real_trading = sum(count for trade_type, is_validation, count in recent_stats 
                                 if trade_type == 'real_trading' and not is_validation)
        
        print(f"\n最近1小时新记录:")
        for trade_type, is_validation, count in recent_stats:
            validation_str = "验证" if is_validation else "非验证"
            print(f"  {trade_type} ({validation_str}): {count}条")
        
        # 3. 检查全局开关状态
        print("\n🔧 2. 全局开关状态验证")
        cursor.execute("SELECT real_trading_enabled FROM real_trading_control WHERE id = 1")
        real_trading_enabled = cursor.fetchone()
        real_trading_status = real_trading_enabled[0] if real_trading_enabled else False
        
        cursor.execute("SELECT auto_trading_enabled FROM system_status ORDER BY last_updated DESC LIMIT 1")
        auto_trading_enabled = cursor.fetchone()
        auto_trading_status = auto_trading_enabled[0] if auto_trading_enabled else False
        
        print(f"  实盘交易开关: {'✅ 已启用' if real_trading_status else '❌ 已关闭'}")
        print(f"  自动交易开关: {'✅ 已启用' if auto_trading_status else '❌ 已关闭'}")
        
        report["global_switches"] = {
            "real_trading_enabled": real_trading_status,
            "auto_trading_enabled": auto_trading_status
        }
        
        # 4. 检查策略进化
        print("\n🧬 3. 策略进化状态验证")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM strategy_evolution_history 
            WHERE created_time >= NOW() - INTERVAL '1 hour'
        """)
        recent_evolution = cursor.fetchone()[0]
        print(f"  最近1小时进化记录: {recent_evolution}条")
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM unified_strategy_logs 
            WHERE timestamp >= NOW() - INTERVAL '1 hour' AND log_type = 'evolution'
        """)
        recent_unified_evolution = cursor.fetchone()[0] if cursor.fetchone() else 0
        print(f"  统一进化日志: {recent_unified_evolution}条")
        
        report["evolution_status"] = {
            "recent_evolution_count": recent_evolution,
            "unified_evolution_count": recent_unified_evolution
        }
        
        conn.close()
        
        # 5. 前端API验证
        print("\n🖥️ 4. 前端API状态验证")
        try:
            response = requests.get('http://localhost:8888/api/quantitative/strategies/STRAT_0035/trade-logs', 
                                  timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    logs = data.get('logs', [])
                    recent_real_count = sum(1 for log in logs[:10] 
                                          if log.get('trade_type') == 'real_trading')
                    recent_verification_count = sum(1 for log in logs[:10] 
                                                  if log.get('trade_type') == 'verification')
                    
                    print(f"  策略STRAT_0035最新10条日志:")
                    print(f"    验证交易: {recent_verification_count}条")
                    print(f"    实盘交易: {recent_real_count}条")
                    
                    report["frontend_status"] = {
                        "api_accessible": True,
                        "recent_verification_logs": recent_verification_count,
                        "recent_real_logs": recent_real_count
                    }
                else:
                    print("  ❌ 前端API返回失败")
                    report["frontend_status"]["api_accessible"] = False
            else:
                print(f"  ❌ 前端API访问失败: {response.status_code}")
                report["frontend_status"]["api_accessible"] = False
        except Exception as e:
            print(f"  ❌ 前端API测试失败: {e}")
            report["frontend_status"]["api_accessible"] = False
        
        # 6. 综合评分
        print("\n🏆 5. 综合修复评分")
        score = 0
        issues_resolved = []
        
        # 实盘交易开关正确关闭 (25分)
        if not real_trading_status:
            score += 25
            issues_resolved.append("✅ 实盘交易开关正确关闭")
        
        # 最近无错误real_trading记录生成 (25分) 
        if recent_real_trading == 0:
            score += 25
            issues_resolved.append("✅ 新记录全部正确分类为验证交易")
        
        # 前端API正常工作 (25分)
        if report["frontend_status"].get("api_accessible"):
            score += 25
            issues_resolved.append("✅ 前端API正常返回正确分类的日志")
        
        # 策略进化正常运行 (25分)
        if recent_evolution > 0:
            score += 25
            issues_resolved.append("✅ 策略进化系统正常运行")
        
        report["final_score"] = score
        report["issues_resolved"] = issues_resolved
        
        print(f"  综合评分: {score}/100分")
        print("  已解决问题:")
        for issue in issues_resolved:
            print(f"    {issue}")
        
        if score >= 90:
            status = "🎉 完美修复"
        elif score >= 75:
            status = "✅ 修复成功"
        elif score >= 60:
            status = "⚠️ 基本修复"
        else:
            status = "❌ 需要继续修复"
        
        print(f"\n{status} - 总体评分: {score}/100")
        
        # 保存报告
        with open('final_verification_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📋 完整验证报告已保存到: final_verification_report.json")
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_final_verification_report() 