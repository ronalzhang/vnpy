#!/usr/bin/env python3
"""
修复交易日志分类错误
将错误标记为real_trading的记录修正为score_verification
"""
import psycopg2
import json
from datetime import datetime

def fix_trading_logs_classification():
    """修复交易日志分类错误"""
    print("🔧 === 开始修复交易日志分类错误 ===")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='quantitative', 
            user='quant_user',
            password='123abc74531'
        )
        cursor = conn.cursor()
        
        # 1. 统计修复前状态
        print("\n📊 修复前状态统计:")
        cursor.execute("""
            SELECT trade_type, is_validation, COUNT(*) as count
            FROM trading_signals 
            GROUP BY trade_type, is_validation
            ORDER BY count DESC
        """)
        before_stats = cursor.fetchall()
        for trade_type, is_validation, count in before_stats:
            validation_str = "验证" if is_validation else "非验证"
            print(f"  {trade_type} ({validation_str}): {count}条")
        
        # 2. 查找所有错误的real_trading记录（应该都是验证交易）
        print("\n🔍 查找错误的real_trading记录...")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM trading_signals 
            WHERE trade_type = 'real_trading' AND is_validation = false
        """)
        error_count = cursor.fetchone()[0]
        print(f"发现 {error_count} 条错误的real_trading记录")
        
        if error_count == 0:
            print("✅ 没有发现错误记录，无需修复")
            return
        
        # 3. 修复这些记录 - 将它们标记为验证交易
        print(f"\n🔧 开始修复 {error_count} 条错误记录...")
        cursor.execute("""
            UPDATE trading_signals 
            SET 
                trade_type = 'score_verification',
                is_validation = true
            WHERE trade_type = 'real_trading' AND is_validation = false
        """)
        
        updated_count = cursor.rowcount
        print(f"✅ 已修复 {updated_count} 条记录")
        
        # 4. 统计修复后状态
        print("\n📊 修复后状态统计:")
        cursor.execute("""
            SELECT trade_type, is_validation, COUNT(*) as count
            FROM trading_signals 
            GROUP BY trade_type, is_validation
            ORDER BY count DESC
        """)
        after_stats = cursor.fetchall()
        for trade_type, is_validation, count in after_stats:
            validation_str = "验证" if is_validation else "非验证"
            print(f"  {trade_type} ({validation_str}): {count}条")
        
        # 5. 验证修复效果
        cursor.execute("""
            SELECT COUNT(*) 
            FROM trading_signals 
            WHERE trade_type = 'real_trading' AND is_validation = false
        """)
        remaining_errors = cursor.fetchone()[0]
        
        if remaining_errors == 0:
            print(f"\n🎉 修复成功！所有错误的real_trading记录已修正")
        else:
            print(f"\n⚠️ 仍有 {remaining_errors} 条错误记录需要手动处理")
        
        # 6. 生成修复报告
        report = {
            "fix_time": datetime.now().isoformat(),
            "before_stats": dict(before_stats),
            "after_stats": dict(after_stats),
            "fixed_count": updated_count,
            "remaining_errors": remaining_errors,
            "success": remaining_errors == 0
        }
        
        with open('trading_logs_fix_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 提交更改
        conn.commit()
        conn.close()
        
        print(f"\n📋 修复报告已保存到: trading_logs_fix_report.json")
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_trading_logs_classification() 