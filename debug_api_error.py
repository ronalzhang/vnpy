#!/usr/bin/env python3
import traceback
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_strategies_api():
    try:
        print("🔍 开始逐步调试策略API...")
        
        # 直接导入并测试quantitative_strategies函数
        from web_app import quantitative_strategies
        
        print("✅ 成功导入quantitative_strategies函数")
        
        # 创建模拟请求对象
        class MockRequest:
            def __init__(self):
                self.method = 'GET'
            
            def get_json(self):
                return {}
        
        # 临时替换Flask的request对象
        import web_app
        original_request = getattr(web_app, 'request', None)
        web_app.request = MockRequest()
        
        print("🔧 开始调用quantitative_strategies()...")
        
        # 调用函数
        result = quantitative_strategies()
        
        print(f"✅ 函数调用成功，返回类型: {type(result)}")
        print(f"返回结果: {str(result)[:200]}...")
        
        # 恢复原始request
        if original_request:
            web_app.request = original_request
        
        return True
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        print("\n🔍 详细错误追踪:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_strategies_api()
    if success:
        print("\n🎉 策略API调试成功！")
    else:
        print("\n💥 策略API调试失败！") 