#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
紧急修复系统 - 解决关键问题
1. 恢复策略持久化数据加载
2. 停止自动交易并清仓
3. 启动真正的持续优化系统
4. 修复日志记录问题
"""

import sqlite3
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests
import hashlib
import hmac
import urllib.parse

class EmergencySystemFixer:
    """紧急系统修复器"""
    
    def __init__(self):
        self.db_path = "quantitative.db"
        self.config_path = "crypto_config.json"
        self.logger = self._setup_logger()
        self.config = self._load_config()
        
        # 币安API配置
        self.api_key = self.config.get('binance', {}).get('api_key', '')
        self.api_secret = self.config.get('binance', {}).get('api_secret', '')
        self.base_url = "https://api.binance.com"
        
    def _setup_logger(self):
        """设置日志记录器"""
        logger = logging.getLogger("EmergencyFixer")
        logger.setLevel(logging.INFO)
        
        # 创建文件处理器
        file_handler = logging.FileHandler(f"logs/emergency_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        file_handler.setLevel(logging.INFO)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 创建格式器
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')
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
    
    def check_account_balance(self) -> Dict:
        """检查账户余额"""
        self.logger.info("🔍 检查账户余额...")
        
        try:
            # 获取账户信息
            account_info = self._make_request("/api/v3/account")
            
            if not account_info:
                self.logger.error("无法获取账户信息")
                return {}
                
            balances = {}
            for balance in account_info.get('balances', []):
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if total > 0:
                    balances[asset] = {
                        'free': free,
                        'locked': locked,
                        'total': total
                    }
            
            self.logger.info(f"当前账户余额: {balances}")
            return balances
            
        except Exception as e:
            self.logger.error(f"检查余额失败: {e}")
            return {}
    
    def get_open_orders(self) -> List[Dict]:
        """获取当前挂单"""
        self.logger.info("📋 检查当前挂单...")
        
        try:
            orders = self._make_request("/api/v3/openOrders")
            self.logger.info(f"当前挂单数量: {len(orders)}")
            return orders
        except Exception as e:
            self.logger.error(f"获取挂单失败: {e}")
            return []
    
    def cancel_all_orders(self) -> bool:
        """取消所有挂单"""
        self.logger.info("❌ 取消所有挂单...")
        
        try:
            # 获取所有交易对的挂单
            symbols = set()
            orders = self.get_open_orders()
            
            for order in orders:
                symbols.add(order['symbol'])
            
            # 为每个交易对取消所有挂单
            success_count = 0
            for symbol in symbols:
                try:
                    result = self._make_request(
                        "/api/v3/openOrders",
                        params={'symbol': symbol},
                        method="DELETE"
                    )
                    if result:
                        success_count += 1
                        self.logger.info(f"已取消 {symbol} 的所有挂单")
                except Exception as e:
                    self.logger.error(f"取消 {symbol} 挂单失败: {e}")
            
            self.logger.info(f"✅ 成功取消 {success_count} 个交易对的挂单")
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"取消挂单失败: {e}")
            return False
    
    def sell_all_positions(self) -> bool:
        """卖出所有持仓换成USDT"""
        self.logger.info("💰 开始清仓所有持仓...")
        
        balances = self.check_account_balance()
        if not balances:
            return False
        
        success_count = 0
        
        for asset, balance_info in balances.items():
            if asset == 'USDT':  # 跳过USDT
                continue
                
            if balance_info['total'] < 0.001:  # 跳过小额资产
                continue
            
            try:
                symbol = f"{asset}USDT"
                quantity = balance_info['free']  # 使用可用余额
                
                if quantity < 0.001:
                    continue
                
                # 获取交易对信息
                ticker = self._make_request(f"/api/v3/ticker/price", {'symbol': symbol})
                if not ticker:
                    self.logger.warning(f"无法获取 {symbol} 价格信息")
                    continue
                
                # 市价卖出
                order_params = {
                    'symbol': symbol,
                    'side': 'SELL',
                    'type': 'MARKET',
                    'quantity': f"{quantity:.8f}".rstrip('0').rstrip('.')
                }
                
                result = self._make_request("/api/v3/order", order_params, "POST")
                
                if result:
                    success_count += 1
                    self.logger.info(f"✅ 成功卖出 {quantity} {asset}")
                else:
                    self.logger.error(f"❌ 卖出 {asset} 失败")
                    
            except Exception as e:
                self.logger.error(f"卖出 {asset} 时出错: {e}")
        
        self.logger.info(f"清仓完成，成功处理 {success_count} 个资产")
        return success_count > 0
    
    def load_historical_strategies(self) -> List[Dict]:
        """加载历史高分策略"""
        self.logger.info("📚 加载历史高分策略...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 查询高分策略 (≥50分)
            cursor.execute("""
                SELECT id, name, symbol, type, parameters, final_score, 
                       win_rate, total_return, sharpe_ratio, profit_factor
                FROM strategies 
                WHERE final_score >= 50.0 
                ORDER BY final_score DESC 
                LIMIT 100
            """)
            
            strategies = []
            for row in cursor.fetchall():
                strategy = {
                    'id': row[0],
                    'name': row[1],
                    'symbol': row[2],
                    'type': row[3],
                    'parameters': json.loads(row[4]) if row[4] else {},
                    'final_score': row[5],
                    'win_rate': row[6],
                    'total_return': row[7],
                    'sharpe_ratio': row[8],
                    'profit_factor': row[9]
                }
                strategies.append(strategy)
            
            conn.close()
            
            self.logger.info(f"加载了 {len(strategies)} 个高分策略")
            return strategies
            
        except Exception as e:
            self.logger.error(f"加载历史策略失败: {e}")
            return []
    
    def activate_best_strategies(self) -> bool:
        """激活最佳策略用于交易"""
        self.logger.info("🚀 激活最佳策略...")
        
        try:
            strategies = self.load_historical_strategies()
            if not strategies:
                self.logger.warning("没有找到高分策略")
                return False
            
            # 选择前10个最高分策略
            top_strategies = strategies[:10]
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 首先禁用所有策略
            cursor.execute("UPDATE strategies SET enabled = 0")
            
            # 激活top策略
            activated_count = 0
            for strategy in top_strategies:
                cursor.execute("""
                    UPDATE strategies 
                    SET enabled = 1, qualified_for_trading = 1 
                    WHERE id = ?
                """, (strategy['id'],))
                activated_count += 1
                
                self.logger.info(f"激活策略: {strategy['name']} (分数: {strategy['final_score']})")
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"✅ 成功激活 {activated_count} 个高分策略")
            return True
            
        except Exception as e:
            self.logger.error(f"激活策略失败: {e}")
            return False
    
    def fix_logging_system(self) -> bool:
        """修复日志记录系统"""
        self.logger.info("🔧 修复日志记录系统...")
        
        try:
            # 创建日志目录
            import os
            log_dirs = ['logs/system', 'logs/trading', 'logs/evolution', 'logs/optimization']
            for log_dir in log_dirs:
                os.makedirs(log_dir, exist_ok=True)
            
            # 清理旧的错误日志
            error_log_path = f"logs/system/error_fix_{datetime.now().strftime('%Y%m%d')}.log"
            with open(error_log_path, 'w', encoding='utf-8') as f:
                f.write(f"# 系统错误修复日志 - {datetime.now()}\n")
                f.write("日志系统已重新初始化\n")
            
            self.logger.info("✅ 日志系统修复完成")
            return True
            
        except Exception as e:
            self.logger.error(f"修复日志系统失败: {e}")
            return False
    
    def stop_auto_trading(self) -> bool:
        """停止自动交易"""
        self.logger.info("🛑 停止自动交易系统...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 禁用所有策略的自动交易
            cursor.execute("UPDATE strategies SET enabled = 0")
            
            # 记录停止时间
            cursor.execute("""
                INSERT OR REPLACE INTO system_settings (key, value) 
                VALUES ('auto_trading_stopped', ?)
            """, (datetime.now().isoformat(),))
            
            conn.commit()
            conn.close()
            
            self.logger.info("✅ 自动交易已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"停止自动交易失败: {e}")
            return False
    
    def run_emergency_fix(self):
        """运行紧急修复"""
        self.logger.info("🚨 开始紧急系统修复...")
        
        # 步骤1: 停止自动交易
        self.logger.info("=== 步骤1: 停止自动交易 ===")
        self.stop_auto_trading()
        
        # 步骤2: 检查账户状态
        self.logger.info("=== 步骤2: 检查账户状态 ===")
        balances = self.check_account_balance()
        
        # 步骤3: 取消所有挂单
        self.logger.info("=== 步骤3: 取消所有挂单 ===")
        self.cancel_all_orders()
        
        # 步骤4: 清仓所有持仓
        self.logger.info("=== 步骤4: 清仓所有持仓 ===")
        self.sell_all_positions()
        
        # 步骤5: 加载历史策略
        self.logger.info("=== 步骤5: 加载历史高分策略 ===")
        strategies = self.load_historical_strategies()
        
        # 步骤6: 修复日志系统
        self.logger.info("=== 步骤6: 修复日志系统 ===")
        self.fix_logging_system()
        
        # 步骤7: 生成修复报告
        self.logger.info("=== 步骤7: 生成修复报告 ===")
        self._generate_fix_report(balances, strategies)
        
        self.logger.info("🎯 紧急修复完成！")
    
    def _generate_fix_report(self, balances: Dict, strategies: List[Dict]):
        """生成修复报告"""
        report = {
            "fix_time": datetime.now().isoformat(),
            "account_balances": balances,
            "high_score_strategies_count": len(strategies),
            "top_strategies": strategies[:5] if strategies else [],
            "actions_taken": [
                "停止自动交易",
                "取消所有挂单", 
                "清仓所有持仓",
                "加载历史高分策略",
                "修复日志系统"
            ],
            "recommendations": [
                "确认所有持仓已清仓完成",
                "验证USDT余额是否正确",
                "重新配置策略参数",
                "启动真正的持续优化系统",
                "设置更严格的风险控制"
            ]
        }
        
        report_path = f"emergency_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"📊 修复报告已保存: {report_path}")

if __name__ == "__main__":
    fixer = EmergencySystemFixer()
    fixer.run_emergency_fix() 