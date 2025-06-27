#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能进化系统启动脚本
启动完整的策略自动进化闭环系统
"""

import sys
import time
import requests
import json
from datetime import datetime

def test_api_connection():
    """测试API连接"""
    try:
        response = requests.get('http://localhost:8888/api/strategies', timeout=10)
        if response.status_code == 200:
            print("✅ API服务连接正常")
            return True
        else:
            print(f"❌ API服务响应异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API服务连接失败: {e}")
        return False

def check_intelligent_evolution_status():
    """检查智能进化系统状态"""
    try:
        response = requests.get('http://localhost:8888/api/evolution-status', timeout=10)
        if response.status_code == 200:
            status = response.json()
            print("📊 智能进化系统状态:")
            print(f"   启用状态: {'🟢 已启用' if status.get('enabled') else '🔴 未启用'}")
            
            config = status.get('config', {})
            print(f"   进化间隔: {config.get('evolution_interval', 'N/A')}秒")
            print(f"   冷却期: {config.get('evolution_cooldown_hours', 'N/A')}小时")
            print(f"   最大并发: {config.get('max_concurrent_evolutions', 'N/A')}")
            
            stats = status.get('statistics', {})
            print(f"   进化统计: {stats}")
            return True
        else:
            print(f"❌ 获取进化状态失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 检查进化状态失败: {e}")
        return False

def start_intelligent_evolution():
    """启动智能进化系统"""
    try:
        # 发送启动进化的API请求
        response = requests.post('http://localhost:8888/api/start-intelligent-evolution', 
                               json={'enabled': True}, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print("🚀 智能进化系统启动成功!")
            print(f"   响应: {result.get('message', 'Unknown')}")
            return True
        else:
            print(f"❌ 启动智能进化失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 启动智能进化异常: {e}")
        return False

def monitor_evolution_progress():
    """监控进化进度"""
    print("\n🔄 开始监控智能进化进度...")
    print("按 Ctrl+C 停止监控")
    
    try:
        while True:
            # 获取最新的进化记录
            response = requests.get('http://localhost:8888/api/recent-evolutions?limit=5', timeout=10)
            
            if response.status_code == 200:
                evolutions = response.json()
                
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f"\n[{current_time}] 最新进化活动:")
                
                if evolutions and len(evolutions) > 0:
                    for evo in evolutions[:3]:  # 显示最新3条
                        strategy_id = evo.get('strategy_id', 'Unknown')[-8:]
                        evolution_type = evo.get('evolution_type', 'Unknown')
                        improvement = evo.get('improvement', 0)
                        success = evo.get('success', False)
                        created_time = evo.get('created_time', '')
                        
                        status_icon = "✅" if success else "❌"
                        print(f"   {status_icon} {strategy_id}: {evolution_type}, 改善: {improvement:.1f}分, {created_time}")
                else:
                    print("   📝 暂无最新进化记录")
                
                # 获取系统整体状态
                response_status = requests.get('http://localhost:8888/api/system-status', timeout=5)
                if response_status.status_code == 200:
                    system_status = response_status.json()
                    active_strategies = system_status.get('active_strategies', 0)
                    avg_score = system_status.get('average_score', 0)
                    print(f"   📊 系统状态: {active_strategies}个活跃策略, 平均分数: {avg_score:.1f}")
            
            # 等待30秒后继续监控
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n🛑 用户停止监控")
    except Exception as e:
        print(f"\n❌ 监控异常: {e}")

def main():
    """主函数"""
    print("🧬 智能进化系统控制台")
    print("=" * 50)
    
    # 1. 测试连接
    print("1️⃣ 测试API连接...")
    if not test_api_connection():
        print("❌ 无法连接到量化服务，请确保服务正在运行")
        return
    
    # 2. 检查当前状态
    print("\n2️⃣ 检查智能进化状态...")
    check_intelligent_evolution_status()
    
    # 3. 启动智能进化
    print("\n3️⃣ 启动智能进化系统...")
    if start_intelligent_evolution():
        print("✅ 智能进化系统已成功启动")
        
        # 4. 监控进化过程
        print("\n4️⃣ 开始监控进化过程...")
        monitor_evolution_progress()
    else:
        print("❌ 智能进化系统启动失败")
    
    print("\n🎉 智能进化系统管理完成")
    print("🔗 监控界面: http://47.236.39.134:8888/quantitative.html")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 用户中断程序")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        import traceback
        traceback.print_exc() 