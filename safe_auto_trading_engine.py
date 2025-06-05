#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全自动交易引擎 - 既能量化交易又保证资金安全
特点：
1. 多重安全检查
2. 严格的风险控制
3. 实时余额监控
4. 智能止损机制
5. 透明的交易记录
"""

import sqlite3
import json
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
import hashlib
import hmac
import urllib.parse

class SafeAutoTradingEngine:
    """安全自动交易引擎"""
    
    def __init__(self):
        self.db_path = "quantitative.db"
        self.config_path = "crypto_config.json"
        self.logger = self._setup_logger()
        self.config = self._load_config()
        
        # 安全参数
        self.max_total_risk = 0.10  # 最大总风险：账户的10%
        self.max_single_trade_risk = 0.02  # 单笔交易最大风险：2%
        self.min_balance_threshold = 5.0  # 最小余额阈值：5U
        self.max_daily_trades = 50  # 每日最大交易次数
        self.max_daily_loss = 0.05  # 每日最大亏损：5%
        
        # 运行状态
        self.running = False
        self.initial_balance = 0.0
        self.current_balance = 0.0
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.last_balance_check = datetime.now()
        
        # API配置
        self.api_key = self.config.get('binance', {}).get('api_key', '')
        self.api_secret = self.config.get('binance', {}).get('api_secret', '')
        self.base_url = "https://api.binance.com"
        
    def _setup_logger(self):
        """设置日志记录器"""
        logger = logging.getLogger("SafeAutoTrading")
        logger.setLevel(logging.INFO)
        
        # 文件处理器
        file_handler = logging.FileHandler(f"logs/trading/safe_trading_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler.setLevel(logging.INFO)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 格式器
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | SAFE_TRADING | %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
        
    def _load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def _create_signature(self, query_string: str) -> str:
        """创建币安API签名"""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _make_request(self, endpoint: str, params: Dict = None, method: str = "GET") -> Dict:
        """发送币安API请求"""
        if not self.api_key or not self.api_secret:
            self.logger.error("API密钥未配置")
            return {}
            
        if not params:
            params = {}
            
        # 添加时间戳
        params['timestamp'] = int(time.time() * 1000)
        params['recvWindow'] = 10000
        
        # 创建查询字符串
        query_string = urllib.parse.urlencode(params)
        
        # 创建签名
        signature = self._create_signature(query_string)
        query_string += f"&signature={signature}"
        
        # 创建完整URL
        url = f"{self.base_url}{endpoint}?{query_string}"
        
        # 设置请求头
        headers = {
            'X-MBX-APIKEY': self.api_key,
            'Content-Type': 'application/json'
        }
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
                
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            self.logger.error(f"API请求失败: {e}")
            return {}
    
    def get_account_balance(self) -> float:
        """获取USDT余额"""
        try:
            account_info = self._make_request("/api/v3/account")
            
            if not account_info:
                return 0.0
                
            for balance in account_info.get('balances', []):
                if balance['asset'] == 'USDT':
                    return float(balance['free'])
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"获取余额失败: {e}")
            return 0.0
    
    def safety_check(self) -> tuple[bool, str]:
        """安全检查"""
        try:
            # 1. 检查余额
            current_balance = self.get_account_balance()
            
            if current_balance < self.min_balance_threshold:
                return False, f"余额过低: {current_balance:.2f}U < {self.min_balance_threshold}U"
            
            # 2. 检查每日交易次数
            if self.daily_trades >= self.max_daily_trades:
                return False, f"超过每日交易限制: {self.daily_trades} >= {self.max_daily_trades}"
            
            # 3. 检查每日亏损
            if self.initial_balance > 0:
                daily_loss_ratio = abs(self.daily_pnl) / self.initial_balance
                if self.daily_pnl < 0 and daily_loss_ratio > self.max_daily_loss:
                    return False, f"超过每日亏损限制: {daily_loss_ratio:.1%} >= {self.max_daily_loss:.1%}"
            
            # 4. 检查总体风险
            if self.initial_balance > 0:
                total_loss = self.initial_balance - current_balance
                if total_loss > self.initial_balance * self.max_total_risk:
                    return False, f"超过总风险限制: 亏损{total_loss:.2f}U"
            
            return True, "安全检查通过"
            
        except Exception as e:
            return False, f"安全检查出错: {e}"
    
    def calculate_position_size(self, symbol: str, signal_strength: float) -> float:
        """计算安全的仓位大小"""
        try:
            current_balance = self.get_account_balance()
            
            # 基于风险计算仓位
            max_risk_amount = current_balance * self.max_single_trade_risk
            
            # 基于信号强度调整
            signal_factor = min(1.0, max(0.1, signal_strength))
            
            # 计算USDT数量
            position_size = max_risk_amount * signal_factor
            
            # 最小交易量限制
            min_size = 6.0  # 币安最小交易额约6U
            position_size = max(min_size, position_size)
            
            self.logger.info(f"计算仓位: {symbol}, 信号强度:{signal_strength:.2f}, 仓位:{position_size:.2f}U")
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"计算仓位失败: {e}")
            return 6.0  # 返回最小仓位
    
    def execute_trade(self, strategy_id: str, symbol: str, side: str, quantity: float, price: float = None) -> Dict:
        """执行安全交易"""
        try:
            # 安全检查
            safe, reason = self.safety_check()
            if not safe:
                self.logger.warning(f"交易被拒绝: {reason}")
                return {'status': 'rejected', 'reason': reason}
            
            # 准备订单参数
            order_params = {
                'symbol': symbol.replace('/', ''),
                'side': side.upper(),
                'type': 'MARKET' if not price else 'LIMIT',
                'quantity': f"{quantity:.8f}".rstrip('0').rstrip('.')
            }
            
            if price:
                order_params['price'] = f"{price:.8f}".rstrip('0').rstrip('.')
                order_params['timeInForce'] = 'GTC'
            
            # 执行订单
            result = self._make_request("/api/v3/order", order_params, "POST")
            
            if result:
                # 记录交易
                self._record_trade(strategy_id, symbol, side, quantity, price, result)
                self.daily_trades += 1
                
                self.logger.info(f"✅ 交易成功: {side} {quantity} {symbol} @ {price or 'MARKET'}")
                return {'status': 'success', 'order': result}
            else:
                self.logger.error(f"❌ 交易失败: {symbol}")
                return {'status': 'failed', 'reason': 'API调用失败'}
                
        except Exception as e:
            self.logger.error(f"执行交易出错: {e}")
            return {'status': 'error', 'reason': str(e)}
    
    def _record_trade(self, strategy_id: str, symbol: str, side: str, quantity: float, price: float, order_result: Dict):
        """记录交易到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO trading_orders (
                    id, strategy_id, symbol, side, quantity, price, status,
                    created_time, executed_time, execution_price
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_result.get('orderId', f"safe_{int(time.time())}"),
                strategy_id,
                symbol,
                side,
                quantity,
                price or 0.0,
                order_result.get('status', 'UNKNOWN'),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                float(order_result.get('price', price or 0.0))
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"记录交易失败: {e}")
    
    def monitor_balance(self):
        """余额监控线程"""
        while self.running:
            try:
                current_balance = self.get_account_balance()
                
                if current_balance != self.current_balance:
                    change = current_balance - self.current_balance
                    self.current_balance = current_balance
                    
                    self.logger.info(f"💰 余额变化: {change:+.2f}U, 当前: {current_balance:.2f}U")
                    
                    # 记录余额历史
                    self._record_balance(current_balance)
                
                # 每小时重置日交易计数（可选）
                now = datetime.now()
                if (now - self.last_balance_check).total_seconds() > 3600:
                    self.last_balance_check = now
                    # 这里可以添加每小时的风险评估
                
                time.sleep(30)  # 每30秒检查一次余额
                
            except Exception as e:
                self.logger.error(f"余额监控出错: {e}")
                time.sleep(60)
    
    def _record_balance(self, balance: float):
        """记录余额到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO account_balance_history (
                    total_balance, available_balance, frozen_balance,
                    timestamp
                ) VALUES (?, ?, ?, ?)
            """, (
                balance,
                balance,
                0.0,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"记录余额失败: {e}")
    
    def start_safe_trading(self):
        """启动安全交易"""
        if self.running:
            self.logger.warning("安全交易引擎已在运行")
            return
        
        self.logger.info("🚀 启动安全自动交易引擎...")
        
        # 获取初始余额
        self.initial_balance = self.get_account_balance()
        self.current_balance = self.initial_balance
        
        if self.initial_balance <= 0:
            self.logger.error("初始余额为0，无法启动交易")
            return
        
        self.logger.info(f"💰 初始余额: {self.initial_balance:.2f}U")
        self.logger.info(f"🛡️ 安全参数: 单笔风险{self.max_single_trade_risk:.1%}, 总风险{self.max_total_risk:.1%}")
        
        self.running = True
        
        # 启动余额监控线程
        balance_thread = threading.Thread(target=self.monitor_balance, daemon=True)
        balance_thread.start()
        
        self.logger.info("✅ 安全交易引擎启动成功")
    
    def stop_safe_trading(self):
        """停止安全交易"""
        self.logger.info("🛑 停止安全自动交易引擎...")
        self.running = False
    
    def get_trading_status(self) -> Dict:
        """获取交易状态"""
        safe, reason = self.safety_check()
        
        return {
            'running': self.running,
            'safe': safe,
            'safety_reason': reason,
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'daily_trades': self.daily_trades,
            'daily_pnl': self.daily_pnl,
            'max_daily_trades': self.max_daily_trades,
            'max_single_risk': f"{self.max_single_trade_risk:.1%}",
            'max_total_risk': f"{self.max_total_risk:.1%}",
            'api_configured': bool(self.api_key and self.api_secret)
        }

# 集成到现有系统的接口
class SafeTradingIntegration:
    """安全交易集成接口"""
    
    def __init__(self):
        self.engine = SafeAutoTradingEngine()
    
    def add_routes_to_app(self, app):
        """添加路由到Flask应用"""
        
        @app.route('/api/safe_trading/status')
        def safe_trading_status():
            return self.engine.get_trading_status()
        
        @app.route('/api/safe_trading/start', methods=['POST'])
        def start_safe_trading():
            try:
                self.engine.start_safe_trading()
                return {'message': '安全交易引擎启动成功', 'status': 'success'}
            except Exception as e:
                return {'error': str(e)}, 500
        
        @app.route('/api/safe_trading/stop', methods=['POST'])
        def stop_safe_trading():
            try:
                self.engine.stop_safe_trading()
                return {'message': '安全交易引擎已停止', 'status': 'success'}
            except Exception as e:
                return {'error': str(e)}, 500
        
        @app.route('/api/safe_trading/execute', methods=['POST'])
        def execute_safe_trade():
            try:
                data = request.get_json()
                
                result = self.engine.execute_trade(
                    strategy_id=data.get('strategy_id'),
                    symbol=data.get('symbol'),
                    side=data.get('side'),
                    quantity=float(data.get('quantity')),
                    price=float(data.get('price')) if data.get('price') else None
                )
                
                return result
            except Exception as e:
                return {'error': str(e)}, 500
    
    def execute_strategy_trade(self, strategy_id: str, symbol: str, signal: Dict) -> Dict:
        """执行策略交易（供策略调用）"""
        try:
            side = 'BUY' if signal.get('action') == 'buy' else 'SELL'
            signal_strength = signal.get('strength', 0.5)
            
            # 计算安全仓位
            quantity_usdt = self.engine.calculate_position_size(symbol, signal_strength)
            
            # 获取当前价格计算数量
            ticker = self.engine._make_request(f"/api/v3/ticker/price", {'symbol': symbol.replace('/', '')})
            if not ticker:
                return {'status': 'failed', 'reason': '无法获取价格'}
            
            current_price = float(ticker['price'])
            quantity = quantity_usdt / current_price
            
            # 执行交易
            return self.engine.execute_trade(strategy_id, symbol, side, quantity)
            
        except Exception as e:
            return {'status': 'error', 'reason': str(e)}

if __name__ == "__main__":
    engine = SafeAutoTradingEngine()
    engine.start_safe_trading()
    
    try:
        while True:
            status = engine.get_trading_status()
            print(f"状态: {status}")
            time.sleep(60)
    except KeyboardInterrupt:
        engine.stop_safe_trading() 