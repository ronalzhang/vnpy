
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from quantitative_service import QuantitativeService

def start_real_simulation():
    """启动真实的策略模拟评分"""
    try:
        print("🚀 启动真实策略模拟评分系统...")
        
        # 初始化量化服务
        service = QuantitativeService()
        
        # 确保数据库和策略初始化
        service.init_database()
        service.init_strategies()
        
        # 运行所有策略模拟评分
        print("🔬 开始运行策略模拟...")
        simulation_results = service.run_all_strategy_simulations()
        
        if simulation_results:
            print(f"✅ 模拟评分完成，评估了 {len(simulation_results)} 个策略")
            
            # 显示前10个高分策略
            sorted_results = sorted(simulation_results.items(), 
                                  key=lambda x: x[1].get('final_score', 0), reverse=True)
            
            print("\n🏆 前10个高分策略:")
            for i, (strategy_id, result) in enumerate(sorted_results[:10]):
                score = result.get('final_score', 0)
                win_rate = result.get('win_rate', 0)
                return_rate = result.get('total_return', 0)
                print(f"  {i+1}. 策略 {strategy_id}: {score:.1f}分 (胜率: {win_rate:.1f}%, 收益: {return_rate:.2f}%)")
            
        else:
            print("⚠️ 模拟评分未返回结果")
        
        print("\n🎯 真实评分系统已启动，策略将持续进化优化")
        
    except Exception as e:
        print(f"❌ 启动真实模拟失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    start_real_simulation()
