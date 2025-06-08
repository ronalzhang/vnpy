#!/usr/bin/env python3
"""
快速系统状态检查
"""
import requests
import json

def check_system():
    server_url = "http://47.236.39.134:8888"
    
    print("🔍 快速系统状态检查")
    print("=" * 50)
    
    try:
        # 1. 检查系统状态
        print("1. 系统状态...")
        response = requests.get(f"{server_url}/api/quantitative/system-status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                status = data.get('data', {})
                print(f"   ✅ 系统运行: {status.get('quantitative_running', False)}")
                print(f"   ✅ 自动交易: {status.get('auto_trading_enabled', False)}")
                print(f"   ✅ 策略总数: {status.get('total_strategies', 0)}")
                print(f"   ✅ 运行策略: {status.get('running_strategies', 0)}")
            else:
                print("   ❌ 系统状态API返回失败")
        else:
            print(f"   ❌ 系统状态API返回错误: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 系统状态检查失败: {e}")
    
    try:
        # 2. 检查策略数据
        print("\n2. 策略数据...")
        response = requests.get(f"{server_url}/api/quantitative/strategies", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                strategies = data.get('data', [])
                enabled_count = len([s for s in strategies if s.get('enabled', False)])
                qualified_count = len([s for s in strategies if s.get('qualified_for_trading', False)])
                print(f"   ✅ 策略总数: {len(strategies)}")
                print(f"   ✅ 启用策略: {enabled_count}")
                print(f"   ✅ 符合交易条件: {qualified_count}")
                
                if strategies:
                    print("\n   📋 策略列表(前5个):")
                    for i, strategy in enumerate(strategies[:5]):
                        status_icon = "🟢" if strategy.get('enabled') else "🔴"
                        print(f"      {status_icon} {strategy.get('name', 'N/A')} - {strategy.get('final_score', 0):.1f}分")
            else:
                print("   ❌ 策略数据API返回失败")
        else:
            print(f"   ❌ 策略数据API返回错误: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 策略数据检查失败: {e}")
    
    try:
        # 3. 检查前端页面
        print("\n3. 前端页面...")
        response = requests.get(f"{server_url}/quantitative.html", timeout=10)
        if response.status_code == 200:
            print("   ✅ 前端页面正常加载")
        else:
            print(f"   ❌ 前端页面加载错误: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 前端页面检查失败: {e}")
    
    print("\n=" * 50)
    print("🎯 检查完成！")

if __name__ == "__main__":
    check_system() 