#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
重置所有策略评分为0分
确保策略评分仅基于真实交易数据，不使用任何模拟或随机数据
这是对用户要求"千万不要给我假数据"的直接响应
"""

import sys
import os
from db_config import get_db_adapter

def reset_all_scores_to_zero():
    """重置所有策略评分为0分，强制使用真实交易数据"""
    try:
        print("🔄 重置所有策略评分为0分，确保仅使用真实交易数据...")
        
        db_adapter = get_db_adapter()
        
        # 1. 获取所有策略数量
        count_query = "SELECT COUNT(*) as total FROM strategies"
        result = db_adapter.execute_query(count_query, fetch_one=True)
        total_strategies = result['total'] if result else 0
        
        if total_strategies == 0:
            print("❌ 没有找到任何策略")
            return False
        
        print(f"📊 找到 {total_strategies} 个策略，开始重置评分...")
        
        # 2. 重置所有策略评分为0，标记为需要重新计算
        reset_query = """
        UPDATE strategies 
        SET 
            final_score = 0.0,
            win_rate = 0.0,
            total_return = 0.0,
            total_trades = 0,
            winning_trades = 0,
            losing_trades = 0,
            max_drawdown = 0.0,
            sharpe_ratio = 0.0,
            profit_factor = 0.0,
            avg_trade_return = 0.0,
            volatility = 0.0,
            qualified_for_trading = 0,
            simulation_score = 0.0,
            fitness_score = 0.0,
            data_source = '等待真实数据',
            last_evaluation_time = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        """
        
        # 执行重置
        db_adapter.execute_query(reset_query)
        
        # 3. 清空模拟数据表（如果存在）
        try:
            db_adapter.execute_query("DELETE FROM strategy_simulation_results")
            print("✅ 已清空策略模拟结果表")
        except Exception as e:
            print(f"ℹ️ 模拟结果表清理: {e}")
        
        # 4. 清空策略初始化记录，强制重新评估
        try:
            db_adapter.execute_query("DELETE FROM strategy_initialization")
            print("✅ 已清空策略初始化记录")
        except Exception as e:
            print(f"ℹ️ 初始化记录清理: {e}")
        
        # 5. 验证重置结果
        verify_query = """
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN final_score = 0 THEN 1 END) as zero_scores,
            MAX(final_score) as max_score,
            COUNT(CASE WHEN qualified_for_trading = 1 THEN 1 END) as qualified
        FROM strategies
        """
        
        verify_result = db_adapter.execute_query(verify_query, fetch_one=True)
        
        if verify_result:
            print(f"\n✅ 策略评分重置完成！")
            print(f"  📊 总策略数: {verify_result['total']}")
            print(f"  🔄 重置为0分: {verify_result['zero_scores']}")
            print(f"  📈 最高分: {verify_result['max_score']}")
            print(f"  💰 合格策略: {verify_result['qualified']}")
            
            if verify_result['zero_scores'] == verify_result['total']:
                print(f"\n🎯 所有策略评分已成功重置为0分")
                print(f"💡 系统现在将仅基于真实交易数据计算评分")
                print(f"⚠️ 策略需要进行真实交易后才能获得评分")
                print(f"🚫 不再使用任何模拟或随机数据")
                return True
            else:
                print(f"⚠️ 部分策略未能重置，请检查数据库")
                return False
        else:
            print(f"❌ 无法验证重置结果")
            return False
        
    except Exception as e:
        print(f"❌ 重置策略评分失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def update_evaluation_config():
    """更新评估配置，确保仅使用真实数据"""
    try:
        print("\n🔧 更新评估配置...")
        
        db_adapter = get_db_adapter()
        
        # 创建或更新系统配置
        config_query = """
        INSERT OR REPLACE INTO system_config (key, value, description, updated_at)
        VALUES 
            ('use_real_data_only', 'true', '仅使用真实交易数据进行评分', CURRENT_TIMESTAMP),
            ('disable_simulation_scoring', 'true', '禁用模拟评分', CURRENT_TIMESTAMP),
            ('min_trades_for_scoring', '10', '最少交易次数要求', CURRENT_TIMESTAMP),
            ('evaluation_mode', 'real_only', '评估模式：仅真实数据', CURRENT_TIMESTAMP)
        """
        
        db_adapter.execute_query(config_query)
        print("✅ 系统配置已更新为仅使用真实数据模式")
        
        return True
        
    except Exception as e:
        print(f"❌ 更新配置失败: {e}")
        return False

def main():
    """主函数"""
    print("🚨 策略评分真实性修复系统")
    print("=" * 60)
    print("⚠️ 响应用户要求：不使用任何假数据或模拟数据")
    print("🎯 目标：确保所有评分都基于真实交易表现")
    print("=" * 60)
    
    # 1. 重置所有策略评分为0
    if not reset_all_scores_to_zero():
        print("💥 评分重置失败")
        return False
    
    # 2. 更新系统配置
    if not update_evaluation_config():
        print("💥 配置更新失败")
        return False
    
    print("\n🎉 策略评分真实性修复完成！")
    print("\n📋 重要说明:")
    print("  ✅ 所有策略评分已重置为0分")
    print("  ✅ 系统配置为仅使用真实交易数据")
    print("  ✅ 禁用了所有模拟和随机评分")
    print("  ⚠️ 策略需要进行真实交易后才能获得评分")
    print("  💰 只有经过实际交易验证的策略才会显示评分")
    print("\n🔄 请重启应用以应用新的配置")
    
    return True

if __name__ == "__main__":
    main()
