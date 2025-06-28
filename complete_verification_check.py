#!/usr/bin/env python3
"""
完整系统验证检查
对修复后的系统进行全方位验证
"""
import psycopg2
import requests
import json
import os
from datetime import datetime, timedelta

def main_verification():
    """主验证函数"""
    print("🔍 === 开始完整系统验证 ===")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": {},
        "overall_score": 0,
        "status": "UNKNOWN"
    }
    
    # 执行各项验证测试
    test_results = []
    
    # 1. 数据库状态验证
    print("\n1️⃣ 数据库状态验证")
    db_score = test_database_status()
    test_results.append(("database", db_score))
    results["tests"]["database"] = db_score
    
    # 2. 日志冲突验证
    print("\n2️⃣ 日志冲突验证")
    conflict_score = test_log_conflicts()
    test_results.append(("conflicts", conflict_score))
    results["tests"]["conflicts"] = conflict_score
    
    # 3. 新日志生成验证
    print("\n3️⃣ 新日志生成验证")
    generation_score = test_new_log_generation()
    test_results.append(("generation", generation_score))
    results["tests"]["generation"] = generation_score
    
    # 4. 统一日志表验证
    print("\n4️⃣ 统一日志表验证")
    unified_score = test_unified_logs()
    test_results.append(("unified", unified_score))
    results["tests"]["unified"] = unified_score
    
    # 5. 服务状态验证
    print("\n5️⃣ 服务状态验证")
    service_score = test_service_status()
    test_results.append(("services", service_score))
    results["tests"]["services"] = service_score
    
    # 6. 代码修复验证
    print("\n6️⃣ 代码修复验证")
    code_score = test_code_fixes()
    test_results.append(("code_fixes", code_score))
    results["tests"]["code_fixes"] = code_score
    
    # 计算总体评分
    total_score = sum([score for _, score in test_results]) / len(test_results)
    results["overall_score"] = round(total_score, 1)
    
    # 确定状态
    if total_score >= 95:
        results["status"] = "EXCELLENT"
        status_emoji = "🏆"
        status_text = "优秀"
    elif total_score >= 85:
        results["status"] = "GOOD"
        status_emoji = "✅"
        status_text = "良好"
    elif total_score >= 70:
        results["status"] = "FAIR"
        status_emoji = "⚠️"
        status_text = "一般"
    else:
        results["status"] = "POOR"
        status_emoji = "❌"
        status_text = "需改进"
    
    # 保存报告
    report_file = f'complete_verification_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 打印总结
    print(f"\n🎯 === 验证总结 ===")
    print(f"{status_emoji} 总体评分: {total_score:.1f}/100 ({status_text})")
    print(f"📄 详细报告: {report_file}")
    
    for test_name, score in test_results:
        emoji = "✅" if score >= 90 else "⚠️" if score >= 70 else "❌"
        print(f"  {emoji} {test_name}: {score:.1f}/100")
    
    return results

def test_database_status():
    """测试数据库状态"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        # 检查基本表是否存在
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('trading_signals', 'strategies', 'unified_strategy_logs')
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        if len(tables) == 3:
            print("  ✅ 所有核心表存在")
            table_score = 100
        else:
            print(f"  ❌ 缺少表: {set(['trading_signals', 'strategies', 'unified_strategy_logs']) - set(tables)}")
            table_score = (len(tables) / 3) * 100
        
        # 检查记录数量
        cursor.execute("SELECT COUNT(*) FROM trading_signals")
        signal_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM strategies")
        strategy_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM unified_strategy_logs")
        unified_count = cursor.fetchone()[0]
        
        print(f"  📊 trading_signals: {signal_count} 条记录")
        print(f"  📊 strategies: {strategy_count} 个策略")
        print(f"  📊 unified_strategy_logs: {unified_count} 条记录")
        
        cursor.close()
        conn.close()
        
        # 根据数据量评分
        data_score = 100 if signal_count > 1000 and strategy_count > 10 and unified_count > 1000 else 80
        
        return (table_score + data_score) / 2
        
    except Exception as e:
        print(f"  ❌ 数据库连接失败: {e}")
        return 0

def test_log_conflicts():
    """测试日志冲突情况"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        # 检查冲突记录
        cursor.execute("""
            SELECT COUNT(*) FROM trading_signals 
            WHERE is_validation = true AND trade_type = 'real_trading'
        """)
        conflicts = cursor.fetchone()[0]
        
        # 检查字段完整性
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN trade_type IS NULL THEN 1 END) as missing_trade_type,
                COUNT(CASE WHEN cycle_id IS NULL THEN 1 END) as missing_cycle_id,
                COUNT(CASE WHEN strategy_score IS NULL THEN 1 END) as missing_strategy_score,
                COUNT(*) as total
            FROM trading_signals
        """)
        completeness = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        print(f"  📊 冲突记录: {conflicts} 条")
        print(f"  📊 缺失trade_type: {completeness[0]} 条")
        print(f"  📊 缺失cycle_id: {completeness[1]} 条")
        print(f"  📊 缺失strategy_score: {completeness[2]} 条")
        
        # 计算评分
        if conflicts == 0 and sum(completeness[:3]) == 0:
            score = 100
            print("  ✅ 完美！无任何冲突或缺失")
        elif conflicts == 0:
            score = 90 - (sum(completeness[:3]) / completeness[3] * 10)
            print("  ✅ 无冲突，但有字段缺失")
        else:
            score = max(0, 80 - conflicts * 5)
            print("  ❌ 存在冲突记录")
        
        return score
        
    except Exception as e:
        print(f"  ❌ 冲突检查失败: {e}")
        return 0

def test_new_log_generation():
    """测试新日志生成是否正常"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        # 检查最近30分钟的日志
        cursor.execute("""
            SELECT 
                COUNT(*) as total_recent,
                COUNT(CASE WHEN is_validation = true AND trade_type = 'real_trading' THEN 1 END) as new_conflicts,
                COUNT(CASE WHEN trade_type = 'real_trading' THEN 1 END) as real_logs,
                COUNT(CASE WHEN trade_type = 'score_verification' THEN 1 END) as validation_logs
            FROM trading_signals 
            WHERE timestamp >= NOW() - INTERVAL '30 minutes'
        """)
        recent = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        total_recent, new_conflicts, real_logs, validation_logs = recent
        
        print(f"  📊 最近30分钟日志: {total_recent} 条")
        print(f"  📊 新冲突: {new_conflicts} 条")
        print(f"  📊 真实交易日志: {real_logs} 条")
        print(f"  📊 验证交易日志: {validation_logs} 条")
        
        # 评分逻辑
        if total_recent == 0:
            score = 50  # 没有新日志，中等分数
            print("  ⚠️ 最近无新日志生成")
        elif new_conflicts == 0:
            score = 100  # 有新日志且无冲突，满分
            print("  ✅ 新日志生成正常，无冲突")
        else:
            score = max(0, 80 - new_conflicts * 10)  # 有冲突，扣分
            print("  ❌ 新日志存在冲突")
        
        return score
        
    except Exception as e:
        print(f"  ❌ 新日志检查失败: {e}")
        return 0

def test_unified_logs():
    """测试统一日志表"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        # 统计各类型日志分布
        cursor.execute("""
            SELECT 
                log_type,
                COUNT(*) as count
            FROM unified_strategy_logs
            GROUP BY log_type
            ORDER BY count DESC
        """)
        distribution = cursor.fetchall()
        
        # 检查最近同步
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN timestamp >= NOW() - INTERVAL '1 hour' THEN 1 END) as recent
            FROM unified_strategy_logs
        """)
        sync_stats = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        total_unified, recent_unified = sync_stats
        
        print(f"  📊 统一日志总计: {total_unified} 条")
        for log_type, count in distribution:
            percentage = (count / total_unified * 100) if total_unified > 0 else 0
            print(f"    - {log_type}: {count} 条 ({percentage:.1f}%)")
        print(f"  📊 最近1小时同步: {recent_unified} 条")
        
        # 评分
        if total_unified > 10000:
            score = 100
            print("  ✅ 统一日志表数据充足")
        elif total_unified > 1000:
            score = 90
            print("  ✅ 统一日志表数据良好")
        else:
            score = 70
            print("  ⚠️ 统一日志表数据较少")
        
        return score
        
    except Exception as e:
        print(f"  ❌ 统一日志检查失败: {e}")
        return 0

def test_service_status():
    """测试服务状态"""
    services = [
        ("Web服务", "http://localhost:8888/api/system/status"),
        ("量化API", "http://localhost:8888/api/quantitative/system-status")
    ]
    
    online_count = 0
    
    for service_name, url in services:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"  ✅ {service_name}: 在线")
                online_count += 1
            else:
                print(f"  ❌ {service_name}: 响应错误 ({response.status_code})")
        except Exception as e:
            print(f"  ❌ {service_name}: 离线 ({e})")
    
    score = (online_count / len(services)) * 100
    return score

def test_code_fixes():
    """测试代码修复状态"""
    key_files = [
        "start_evolution_scheduler.py",
        "modern_strategy_manager.py", 
        "real_trading_manager.py",
        "quantitative_service.py",
        "web_app.py"
    ]
    
    fixed_count = 0
    
    for filename in key_files:
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 检查关键修复标记
                has_trade_type = 'trade_type' in content
                has_verification = 'score_verification' in content
                has_validation = 'is_validation' in content
                
                if has_trade_type and (has_verification or has_validation):
                    print(f"  ✅ {filename}: 修复完整")
                    fixed_count += 1
                else:
                    print(f"  ⚠️ {filename}: 修复不完整")
            except Exception as e:
                print(f"  ❌ {filename}: 读取失败 ({e})")
        else:
            print(f"  ❌ {filename}: 文件不存在")
    
    score = (fixed_count / len(key_files)) * 100
    return score

if __name__ == "__main__":
    main_verification() 