#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from vnpy.trader.app import BaseApp
from vnpy.trader.engine import MainEngine
from vnpy.event import EventEngine

from .engine import CryptoArbitrageEngine
from .ui import CryptoArbitrageWidget


class CryptoArbitrageApp(BaseApp):
    """加密货币套利应用"""
    
    app_name = "CryptoArbitrage"   # 应用名称
    app_module = __module__        # 模块名称
    app_path = Path(__file__).parent  # 模块路径
    display_name = "加密货币套利"  # 显示名称
    engine_class = CryptoArbitrageEngine  # 引擎类
    widget_class = CryptoArbitrageWidget  # 控件类
    widget_name = "CryptoArbitrageWidget"  # 控件类名称
    default_setting = {"交易所API配置": "crypto_config.json"}  # 默认配置
    
    def __init__(self, main_engine, event_engine):
        """构造函数"""
        # 不调用BaseApp的__init__，因为它是抽象类
        self.main_engine = main_engine
        self.event_engine = event_engine
        self.engine = None
        self.widget = None
        
        # 创建引擎
        self.engine = self.engine_class(main_engine, event_engine)
    
    def start(self, enable_trading=False):
        """启动套利系统"""
        print("""
========================================================
       加密货币跨交易所套利系统 - 启动中...
========================================================
        """)
        
        # 启动套利引擎
        self.engine.start(enable_trading=enable_trading)
        
        print("""
========================================================
       加密货币跨交易所套利系统 使用指南
========================================================
1. 点击"启动监控"按钮开始监控价格差异
2. 价格差异表格将显示不同交易所间的价格差异
3. 当发现套利机会时（价差≥0.5%），会在日志中提示
4. 如需启动自动交易，点击"启动自动交易"按钮
5. 交易记录表格将显示已执行的套利交易
6. 账户余额表格将显示各交易所的资金情况
7. 点击"停止"按钮可停止监控和交易

命令行选项:
- 使用 --real 参数可强制使用真实API（禁用模拟模式）
- 使用 --trade 参数可启用自动交易功能

注意: 
- 系统价格更新频率为5秒一次，避免过于频繁刷新
- 请在crypto_config.json中正确配置API密钥
- 使用实盘交易前，请确保了解相关风险
========================================================
        """)
    
    def show(self):
        """显示UI界面"""
        # 创建套利界面
        if not self.widget:
            self.widget = self.widget_class(self.main_engine, self.event_engine)
            
        # 设置窗口标题和图标
        self.widget.setWindowTitle("加密货币跨交易所套利系统")
        
        # 显示窗口
        self.widget.showMaximized() 