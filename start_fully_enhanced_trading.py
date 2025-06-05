#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 完整增强版量化交易系统启动器
功能：原版所有功能 + 持续优化增强
用途：完全替代原版后端 start_quantitative_service.py
"""

import sys
import logging
from pathlib import Path

# 添加当前路径
sys.path.append(str(Path(__file__).parent))

from integrate_continuous_optimization import main

if __name__ == "__main__":
    # 直接启动完整增强版服务
    main() 