#!/usr/bin/env python3
import traceback

def test_calculation_functions():
    try:
        from web_app import calculate_strategy_sharpe_ratio, calculate_strategy_max_drawdown, calculate_strategy_profit_factor, calculate_strategy_volatility
        print("✅ 导入成功")
        
        # 测试夏普比率
        try:
            result = calculate_strategy_sharpe_ratio("STRAT_0088", 4)
            print(f"✅ 夏普比率: {result}")
        except Exception as e:
            print(f"❌ 夏普比率计算失败: {e}")
            traceback.print_exc()
        
        # 测试最大回撤
        try:
            result = calculate_strategy_max_drawdown("STRAT_0088")
            print(f"✅ 最大回撤: {result}")
        except Exception as e:
            print(f"❌ 最大回撤计算失败: {e}")
            traceback.print_exc()
        
        # 测试盈亏比
        try:
            result = calculate_strategy_profit_factor("STRAT_0088", 2, 2)
            print(f"✅ 盈亏比: {result}")
        except Exception as e:
            print(f"❌ 盈亏比计算失败: {e}")
            traceback.print_exc()
        
        # 测试波动率
        try:
            result = calculate_strategy_volatility("STRAT_0088")
            print(f"✅ 波动率: {result}")
        except Exception as e:
            print(f"❌ 波动率计算失败: {e}")
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_calculation_functions() 