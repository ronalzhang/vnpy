#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
加密货币套利应用的图形界面
"""

import csv
import json
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional
import os
import webbrowser

import numpy as np
import pyqtgraph as pg

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtWidgets, QtCore, QtGui
from vnpy.trader.ui.widget import (
    BaseMonitor, BaseCell, DirectionCell, EnumCell,
    TimeCell, PnlCell, BidCell, AskCell,
    MsgCell, DateCell
)
from vnpy.trader.constant import Direction, Offset

from ..engine import (
    APP_NAME,
    EVENT_CRYPTO_LOG,
    EVENT_CRYPTO_DIFF,
    EVENT_CRYPTO_TRADE,
    EVENT_CRYPTO_BALANCE
)

# 单元格颜色
COLOR_LONG = QtGui.QColor("red")
COLOR_SHORT = QtGui.QColor("green")
COLOR_BLACK = QtGui.QColor("black")
COLOR_BLUE = QtGui.QColor("darkblue")
COLOR_GREEN = QtGui.QColor("darkgreen")

class TimeStringCell(BaseCell):
    """处理字符串格式的时间单元格"""
    
    def __init__(self, text: str, data: Any) -> None:
        """构造函数"""
        super().__init__(text, data)
        
        # 设置单元格样式
        self.setForeground(QtGui.QColor("darkblue"))
        font = self.font()
        font.setBold(True)
        self.setFont(font)
        self.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)


class PriceDiffCell(BaseCell):
    """价差百分比单元格"""
    
    def __init__(self, text: str, data: Any) -> None:
        """构造函数"""
        # 转换为百分比格式
        if isinstance(data, float):
            text = f"{data * 100:.2f}%"
            
            # 根据阈值设置颜色
            if data >= 0.005:  # 0.5%
                self.color = QtGui.QColor("red")
                self.font = QtGui.QFont("Arial", 10, QtGui.QFont.Bold)
            elif data >= 0.003:  # 0.3%
                self.color = QtGui.QColor("orange")
                self.font = QtGui.QFont("Arial", 9, QtGui.QFont.Bold)
            elif data >= 0.001:  # 0.1%
                self.color = QtGui.QColor("green")
            else:
                self.color = QtGui.QColor("black")
        
        super().__init__(text, data)
        

class BalanceCell(BaseCell):
    """余额信息单元格"""
    
    def __init__(self, text: str, data: Any) -> None:
        """构造函数"""
        if isinstance(data, dict):
            # 格式化余额信息
            balance_text = ", ".join([f"{k}: {v}" for k, v in data.items() if k != 'info'])
            text = balance_text
        
        super().__init__(text, data)


class PriceCell(BaseCell):
    """价格单元格，格式化为2位小数"""
    
    def __init__(self, text: str, data: Any) -> None:
        """构造函数"""
        if isinstance(data, (float, int)):
            # 格式化为2位小数
            text = f"{data:.2f}"
        
        super().__init__(text, data)


class CryptoArbitrageWidget(QtWidgets.QWidget):
    """加密货币套利应用"""

    signal = QtCore.pyqtSignal(Event)
    
    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        """构造函数"""
        super().__init__()

        self.main_engine = main_engine
        self.event_engine = event_engine
        self.crypto_engine = None
        
        # 添加运行模式状态记录
        self.last_mode = "real"  # 默认为实盘模式
        
        # 初始化界面
        self.init_ui()
        
        # 注册事件处理函数
        self.register_event()
        
        # 初始化引擎
        self.init_engine()

    def init_ui(self) -> None:
        """初始化界面"""
        self.setWindowTitle("加密货币套利")
        
        # 创建控制区域
        control_group = QtWidgets.QGroupBox("控制")
        control_layout = QtWidgets.QHBoxLayout()
        control_group.setLayout(control_layout)
        
        self.monitor_button = QtWidgets.QPushButton("启动监控")
        self.monitor_button.clicked.connect(self.start_monitor)
        self.monitor_button.setFixedHeight(40)
        control_layout.addWidget(self.monitor_button)
        
        self.trade_button = QtWidgets.QPushButton("启动自动交易")
        self.trade_button.clicked.connect(self.start_trading)
        self.trade_button.setFixedHeight(40)
        self.trade_button.setEnabled(False)  # 默认禁用交易按钮
        control_layout.addWidget(self.trade_button)
        
        self.stop_button = QtWidgets.QPushButton("停止")
        self.stop_button.clicked.connect(self.stop)
        self.stop_button.setFixedHeight(40)
        self.stop_button.setEnabled(False)  # 默认禁用停止按钮
        control_layout.addWidget(self.stop_button)
        
        # 添加日志控制选项
        self.verbose_checkbox = QtWidgets.QCheckBox("详细日志")
        self.verbose_checkbox.setChecked(False)
        self.verbose_checkbox.stateChanged.connect(self.toggle_verbose_logging)
        control_layout.addWidget(self.verbose_checkbox)
        
        # 添加模拟模式指示器
        self.simulation_label = QtWidgets.QLabel("🔄 未启动")
        self.simulation_label.setStyleSheet("color: gray; font-weight: bold;")
        control_layout.addWidget(self.simulation_label)
        
        # 创建价格差异表格
        diff_group = QtWidgets.QGroupBox("价格差异")
        diff_layout = QtWidgets.QVBoxLayout()
        diff_group.setLayout(diff_layout)
        
        self.diff_monitor = PriceDiffMonitor(self.main_engine, self.event_engine)
        diff_layout.addWidget(self.diff_monitor)
        
        # 创建交易记录表格
        trade_group = QtWidgets.QGroupBox("交易记录")
        trade_layout = QtWidgets.QVBoxLayout()
        trade_group.setLayout(trade_layout)
        
        self.trade_monitor = TradeMonitor(self.main_engine, self.event_engine)
        trade_layout.addWidget(self.trade_monitor)
        
        # 创建余额表格
        balance_group = QtWidgets.QGroupBox("账户余额")
        balance_layout = QtWidgets.QVBoxLayout()
        balance_group.setLayout(balance_layout)
        
        self.balance_monitor = BalanceMonitor(self.main_engine, self.event_engine)
        balance_layout.addWidget(self.balance_monitor)
        
        # 创建日志区域
        log_group = QtWidgets.QGroupBox("日志")
        log_layout = QtWidgets.QVBoxLayout()
        log_group.setLayout(log_layout)
        
        self.log_monitor = LogMonitor(self.main_engine, self.event_engine)
        log_layout.addWidget(self.log_monitor)
        
        # 设置整体布局
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(control_group)
        
        # 上半部分：价格差异和余额
        top_hbox = QtWidgets.QHBoxLayout()
        top_hbox.addWidget(diff_group, 7)
        top_hbox.addWidget(balance_group, 3)
        vbox.addLayout(top_hbox, 4)
        
        # 下半部分：交易记录和日志
        bottom_hbox = QtWidgets.QHBoxLayout()
        bottom_hbox.addWidget(trade_group, 6)
        bottom_hbox.addWidget(log_group, 4)
        vbox.addLayout(bottom_hbox, 6)
        
        self.setLayout(vbox)
        
    def register_event(self) -> None:
        """注册事件监听"""
        pass
        
    def start_monitor(self) -> None:
        """启动监控"""
        try:
            # 使用上次的运行模式
            if not self.crypto_engine:
                # 初始化引擎
                event_engine = EventEngine()
                self.crypto_engine = CryptoArbitrageEngine(event_engine)
                init_result = self.crypto_engine.init_engine(
                    settings=prepare_config(api_keys_required=True),
                    verbose=True,
                    enable_trading=True,
                    simulate=False if self.last_mode == "real" else True  # 使用记录的模式
                )
                
                # 如果初始化失败(比如API密钥无效),则提示错误
                if not init_result:
                    QtWidgets.QMessageBox.warning(
                        self,
                        "启动失败",
                        "实盘模式初始化失败，请检查API配置"
                    )
                    return
            
            self.crypto_engine.start(enable_trading=False)
            self.monitor_button.setEnabled(False)
            self.trade_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            
            # 检查是否处于模拟模式
            if not self.crypto_engine.exchanges:
                # 没有连接到交易所，可能是模拟模式
                self.simulation_label.setText("⚠️ 模拟模式")
                self.simulation_label.setStyleSheet("color: orange; font-weight: bold;")
                self.last_mode = "simulate"
            else:
                # 检查连接的交易所类型
                has_real_exchange = False
                for name, exchange in self.crypto_engine.exchanges.items():
                    if hasattr(exchange, "base_prices"):
                        # 这是我们定义的模拟交易所类
                        continue
                    else:
                        # 这是真实的交易所连接
                        has_real_exchange = True
                        break
                
                if has_real_exchange:
                    self.simulation_label.setText("✅ 实盘模式")
                    self.simulation_label.setStyleSheet("color: green; font-weight: bold;")
                    self.last_mode = "real"
                else:
                    self.simulation_label.setText("⚠️ 模拟模式")
                    self.simulation_label.setStyleSheet("color: orange; font-weight: bold;")
                    self.last_mode = "simulate"
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "启动失败",
                f"启动监控失败，错误信息：\n{str(e)}\n\n{traceback.format_exc()}"
            )
            
    def start_trading(self) -> None:
        """启动自动交易"""
        reply = QtWidgets.QMessageBox.question(
            self,
            "确认启动交易",
            "您确定要启动自动交易功能吗？这将根据设定的阈值自动执行套利交易。",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            try:
                self.crypto_engine.enable_trading = True
                self.trade_button.setEnabled(False)
                self.crypto_engine.write_log("自动交易已启动")
            except Exception as e:
                QtWidgets.QMessageBox.warning(
                    self,
                    "启动失败",
                    f"启动自动交易失败，错误信息：\n{str(e)}\n\n{traceback.format_exc()}"
                )
            
    def stop(self) -> None:
        """停止运行"""
        try:
            self.crypto_engine.stop()
            self.monitor_button.setEnabled(True)
            self.trade_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            
            # 保持模式标签显示，但添加停止状态指示
            current_text = self.simulation_label.text()
            if "已停止" not in current_text:
                self.simulation_label.setText(f"{current_text} (已停止)")
                self.simulation_label.setStyleSheet(self.simulation_label.styleSheet() + "; opacity: 0.7;")
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "停止失败",
                f"停止失败，错误信息：\n{str(e)}\n\n{traceback.format_exc()}"
            )
    
    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """关闭窗口事件"""
        reply = QtWidgets.QMessageBox.question(
            self,
            "退出",
            "确认退出？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            if self.crypto_engine:
                try:
                    self.crypto_engine.stop()
                except Exception as e:
                    print(f"关闭引擎时出错: {e}")
            event.accept()
        else:
            event.ignore()

    def toggle_verbose_logging(self, state):
        """切换详细日志模式"""
        verbose = bool(state)
        if hasattr(self.crypto_engine, "verbose_logging"):
            self.crypto_engine.verbose_logging = verbose
            self.crypto_engine.write_log(
                f"详细日志模式: {'开启' if verbose else '关闭'}", 
                force=True
            )


class PriceDiffMonitor(BaseMonitor):
    """价格差异监控组件"""
    
    event_type = EVENT_CRYPTO_DIFF
    data_key = ""
    sorting = True
    headers = {
        "symbol": {"display": "交易对", "cell": BaseCell},
        "min_exchange": {"display": "低价交易所", "cell": BaseCell},
        "max_exchange": {"display": "高价交易所", "cell": BaseCell},
        "min_price": {"display": "最低价", "cell": PriceCell},
        "max_price": {"display": "最高价", "cell": PriceCell},
        "price_diff": {"display": "价差", "cell": PriceCell},
        "price_diff_pct": {"display": "价差率", "cell": PriceDiffCell},
        "min_depth": {"display": "低价深度", "cell": PriceCell},
        "max_depth": {"display": "高价深度", "cell": PriceCell},
        "min_volume": {"display": "低价成交量", "cell": PriceCell},
        "max_volume": {"display": "高价成交量", "cell": PriceCell},
        "executable": {"display": "可执行", "cell": BaseCell},
    }
    
    def __init__(
        self,
        main_engine: MainEngine,
        event_engine: EventEngine,
    ) -> None:
        """构造函数"""
        super().__init__(main_engine, event_engine)
        self.cell_data = {}
    
    def process_event(self, event: Event) -> None:
        """处理事件"""
        diff_list = event.data
        
        # 清空原有数据
        self.cells.clear()
        self.cell_data.clear()
        
        # 添加新数据
        for diff_item in diff_list:
            symbol = diff_item["symbol"]
            
            # 准备表格显示数据
            data = diff_item.copy()
            
            # 处理深度信息
            if "depth_info" in diff_item and diff_item["depth_info"]:
                min_depth_info = diff_item["depth_info"].get("min_exchange_depth", {})
                max_depth_info = diff_item["depth_info"].get("max_exchange_depth", {})
                
                data["min_depth"] = min_depth_info.get("ask_depth", 0)
                data["max_depth"] = max_depth_info.get("bid_depth", 0)
            else:
                data["min_depth"] = 0
                data["max_depth"] = 0
            
            # 处理成交量信息
            if "volumes" in diff_item and diff_item["volumes"]:
                data["min_volume"] = diff_item["volumes"].get(diff_item["min_exchange"], 0)
                data["max_volume"] = diff_item["volumes"].get(diff_item["max_exchange"], 0)
            else:
                data["min_volume"] = 0
                data["max_volume"] = 0
            
            # 可执行状态
            data["executable"] = "✅" if diff_item.get("can_execute", True) else "❌"
            
            self.cell_data[symbol] = data
        
        # 刷新表格
        self.update_table()
        
    def update_table(self) -> None:
        """更新表格"""
        self.clearContents()
        self.setRowCount(0)
        
        try:
            for row_idx, data in enumerate(self.cell_data.values()):
                self.insertRow(row_idx)
                
                for col_idx, (header, header_dict) in enumerate(self.headers.items()):
                    cell_type = header_dict["cell"]
                    
                    if header in data:
                        cell_data = data[header]
                        
                        # 特殊处理时间类型
                        if cell_type == TimeCell and isinstance(cell_data, str):
                            # 如果是字符串格式的时间，使用TimeStringCell代替TimeCell
                            cell = TimeStringCell(str(cell_data), cell_data)
                        elif header == "type" and "mapping" in header_dict:
                            display_value = header_dict["mapping"].get(str(cell_data), str(cell_data))
                            cell = EnumCell(display_value, cell_data)
                        else:
                            cell = cell_type(str(cell_data), cell_data)
                            
                        self.setItem(row_idx, col_idx, cell)
        except Exception as e:
            print(f"更新表格时出错: {e}")
            import traceback
            traceback.print_exc()


class TradeMonitor(BaseMonitor):
    """交易记录监控组件"""
    
    event_type = EVENT_CRYPTO_TRADE
    data_key = ""
    sorting = True
    headers = {
        "timestamp": {"display": "时间", "cell": TimeStringCell},
        "symbol": {"display": "交易对", "cell": BaseCell},
        "type": {"display": "类型", "cell": EnumCell, "mapping": {"open": "开仓", "close": "平仓"}},
        "buy_exchange": {"display": "买入交易所", "cell": BaseCell},
        "sell_exchange": {"display": "卖出交易所", "cell": BaseCell},
        "amount": {"display": "数量", "cell": BaseCell},
        "price_diff": {"display": "价差", "cell": PriceCell},
        "profit": {"display": "预计利润", "cell": PriceCell},
    }
    
    def __init__(
        self,
        main_engine: MainEngine,
        event_engine: EventEngine,
    ) -> None:
        """构造函数"""
        super().__init__(main_engine, event_engine)
        self.cell_data = {}
        
        # 添加右键菜单
        self.menu = QtWidgets.QMenu(self)
        
        export_action = QtWidgets.QAction("导出CSV", self)
        export_action.triggered.connect(self.export_csv)
        self.menu.addAction(export_action)
    
    def process_event(self, event: Event) -> None:
        """处理事件"""
        trade_data = event.data
        
        # 生成唯一标识符
        timestamp = trade_data["timestamp"]
        symbol = trade_data["symbol"]
        key = f"{timestamp}_{symbol}_{trade_data['type']}"
        
        # 设置表格所需字段
        data = {
            "timestamp": timestamp,
            "symbol": symbol,
            "type": trade_data["type"],
            "buy_exchange": trade_data["arb_info"]["buy_exchange"],
            "sell_exchange": trade_data["arb_info"]["sell_exchange"],
            "amount": trade_data["arb_info"]["amount"],
            "price_diff": trade_data["arb_info"]["price_diff"],
            "profit": trade_data["arb_info"]["price_diff"] * trade_data["arb_info"]["amount"],
        }
        
        # 添加数据并刷新表格
        self.cell_data[key] = data
        self.update_table()
        
    def update_table(self) -> None:
        """更新表格"""
        self.clearContents()
        self.setRowCount(0)
        
        for row_idx, data in enumerate(self.cell_data.values()):
            self.insertRow(row_idx)
            
            for col_idx, (header, header_dict) in enumerate(self.headers.items()):
                cell_type = header_dict["cell"]
                
                if header in data:
                    cell_data = data[header]
                    
                    # 特殊处理时间类型
                    if cell_type == TimeCell and isinstance(cell_data, str):
                        # 如果是字符串格式的时间，使用TimeStringCell代替TimeCell
                        cell = TimeStringCell(str(cell_data), cell_data)
                    elif header == "type" and "mapping" in header_dict:
                        display_value = header_dict["mapping"].get(str(cell_data), str(cell_data))
                        cell = EnumCell(display_value, cell_data)
                    else:
                        cell = cell_type(str(cell_data), cell_data)
                        
                    self.setItem(row_idx, col_idx, cell)
    
    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        """右键菜单事件"""
        self.menu.popup(QtGui.QCursor.pos())
    
    def export_csv(self) -> None:
        """导出CSV文件"""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出交易记录", "", "CSV(*.csv)")
        
        if not path:
            return
            
        try:
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                
                # 写入表头
                headers = [d["display"] for d in self.headers.values()]
                writer.writerow(headers)
                
                # 写入数据
                for item in self.cell_data.values():
                    row_data = []
                    for column in self.headers.keys():
                        row_data.append(str(item[column]))
                    writer.writerow(row_data)
                
            QtWidgets.QMessageBox.information(
                self, 
                "导出成功", 
                f"交易记录已成功导出至：\n{path}"
            )
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "导出失败",
                f"导出失败，错误信息：\n{str(e)}\n\n{traceback.format_exc()}"
            )
            

class BalanceMonitor(BaseMonitor):
    """账户余额监控组件"""
    
    event_type = EVENT_CRYPTO_BALANCE
    data_key = "exchange"
    sorting = False
    headers = {
        "exchange": {"display": "交易所", "cell": BaseCell},
        "balance_info": {"display": "余额", "cell": BalanceCell},
        "timestamp": {"display": "更新时间", "cell": TimeStringCell},
    }
    
    def __init__(
        self,
        main_engine: MainEngine,
        event_engine: EventEngine,
    ) -> None:
        """构造函数"""
        super().__init__(main_engine, event_engine)
        self.cell_data = {}
    
    def process_event(self, event: Event) -> None:
        """处理事件"""
        data = event.data
        exchange_name = data["exchange"].upper()
        
        # 格式化余额信息
        data["balance_info"] = data["balance"]
        
        # 更新数据
        self.cell_data[exchange_name] = data
        self.update_table()
        
    def update_table(self) -> None:
        """更新表格"""
        self.clearContents()
        self.setRowCount(0)
        
        try:
            for row_idx, data in enumerate(self.cell_data.values()):
                self.insertRow(row_idx)
                
                for col_idx, (header, header_dict) in enumerate(self.headers.items()):
                    cell_type = header_dict["cell"]
                    
                    if header in data:
                        cell_data = data[header]
                        cell = cell_type(str(cell_data), cell_data)
                        self.setItem(row_idx, col_idx, cell)
        except Exception as e:
            print(f"更新余额表格时出错: {e}")
            import traceback
            traceback.print_exc()


class LogMonitor(QtWidgets.QTextEdit):
    """日志监控组件"""
    
    signal = QtCore.pyqtSignal(Event)
    
    def __init__(
        self,
        main_engine: MainEngine,
        event_engine: EventEngine,
    ) -> None:
        """构造函数"""
        super().__init__()
        
        self.main_engine = main_engine
        self.event_engine = event_engine
        
        self.init_ui()
        self.register_event()
        
    def init_ui(self) -> None:
        """初始化界面"""
        self.setReadOnly(True)
        self.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.NoWrap)
        self.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, Monospace;
                font-size: 12px;
                background-color: #F0F0F0;
            }
        """)
        
    def register_event(self) -> None:
        """注册事件监听"""
        self.signal.connect(self.process_log_event)
        self.event_engine.register(EVENT_CRYPTO_LOG, self.signal.emit)
        
    def process_log_event(self, event: Event) -> None:
        """处理日志事件"""
        log = event.data
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        msg = f"[{timestamp}] {log.msg}"
        self.append(msg)
        
        # 滚动到底部
        self.moveCursor(QtGui.QTextCursor.End) 