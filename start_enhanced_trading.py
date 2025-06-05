#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动增强版量化交易系统
解决策略只模拟一次的问题，实现真正的持续优化直到65分门槛
"""
import os
import sys
import logging
from pathlib import Path

# 确保logs目录存在
os.makedirs('logs', exist_ok=True)

# 添加当前路径
sys.path.append(str(Path(__file__).parent))

def main():
    """主函数"""
    print("🚀 启动增强版量化交易系统...")
    print("📋 新系统特性:")
    print("  ✅ 每5分钟持续模拟交易")
    print("  ✅ 实时优化策略参数")
    print("  ✅ 严格65分交易门槛")
    print("  ✅ 智能策略淘汰机制")
    print("  ✅ 完整性能追踪")
    print()
    
    try:
        from integrate_continuous_optimization import main as run_enhanced_system
        run_enhanced_system()
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("请确保所有依赖文件都在当前目录中")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 