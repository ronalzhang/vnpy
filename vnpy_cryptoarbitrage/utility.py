#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
工具函数和类
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class LogData:
    """日志数据类"""
    
    def __init__(self, gateway_name: str, msg: str, level: str = "INFO") -> None:
        """构造函数"""
        self.gateway_name = gateway_name
        self.msg = msg
        self.level = level
        self.time = datetime.now()


def load_json(filepath: str) -> dict:
    """
    加载JSON文件
    """
    filepath = Path(filepath)
    
    if filepath.exists():
        with open(filepath, "r", encoding="utf8") as f:
            data = json.load(f)
        return data
    else:
        return {}


def save_json(filepath: str, data: dict) -> None:
    """
    保存JSON文件
    """
    filepath = Path(filepath)
    
    with open(filepath, "w", encoding="utf8") as f:
        json.dump(data, f, indent=4) 