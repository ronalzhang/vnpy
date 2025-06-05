#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清仓脚本 - 将所有非USDT资产换成USDT
用于为量化交易准备初始资金
"""

import json
import time
import requests
import hashlib
import hmac
import urllib.parse
from datetime import datetime
from typing import Dict, List

class PositionCleaner:
    """资产清仓器"""
    
    def __init__(self):
        self.config = self._load_config()
        self.api_key = self.config.get('binance', {}).get('api_key', '')
        self.api_secret = self.config.get('binance', {}).get('api_secret', '')
        self.base_url = "https://api.binance.com"
        
        # 最小清仓价值（美元）
        self.min_clear_value = 1.0
        
        # 不清仓的稳定币列表
        self.stable_coins = ['USDT', 'USDC', 'BUSD', 'DAI', 'TUSD']
        
    def _load_config(self):
        """加载配置"""
        try:
            with open('crypto_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置失败: {e}")
            return {}
    
    def _create_signature(self, query_string: str) -> str:
        """创建API签名"""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _make_request(self, endpoint: str, params: Dict = None, method: str = "GET") -> Dict:
        """发送API请求"""
        if not self.api_key or not self.api_secret:
            print("❌ API密钥未配置！")
            return {}
            
        if not params:
            params = {}
            
        params['timestamp'] = int(time.time() * 1000)
        params['recvWindow'] = 10000
        
        query_string = urllib.parse.urlencode(params)
        signature = self._create_signature(query_string)
        query_string += f"&signature={signature}"
        
        url = f"{self.base_url}{endpoint}?{query_string}"
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
                raise ValueError(f"不支持的方法: {method}")
                
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"API请求失败: {e}")
            return {}
    
    def get_account_balances(self) -> List[Dict]:
        """获取账户余额"""
        print("🔍 获取账户余额...")
        
        account_info = self._make_request("/api/v3/account")
        if not account_info:
            return []
        
        balances = []
        for balance in account_info.get('balances', []):
            free = float(balance['free'])
            locked = float(balance['locked'])
            total = free + locked
            
            if total > 0:
                balances.append({
                    'asset': balance['asset'],
                    'free': free,
                    'locked': locked,
                    'total': total
                })
        
        return balances
    
    def get_asset_price(self, symbol: str) -> float:
        """获取资产价格"""
        try:
            if symbol == 'USDT':
                return 1.0
                
            # 尝试不同的交易对
            for quote in ['USDT', 'BUSD', 'USDC']:
                pair = f"{symbol}{quote}"
                price_info = self._make_request("/api/v3/ticker/price", {'symbol': pair})
                
                if price_info and 'price' in price_info:
                    price = float(price_info['price'])
                    
                    # 如果不是USDT对，需要转换
                    if quote != 'USDT':
                        quote_price = self.get_asset_price(quote)
                        price = price * quote_price
                    
                    return price
            
            print(f"⚠️ 无法获取 {symbol} 的价格")
            return 0.0
            
        except Exception as e:
            print(f"获取价格失败 {symbol}: {e}")
            return 0.0
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """获取交易对信息"""
        try:
            exchange_info = self._make_request("/api/v3/exchangeInfo")
            
            for symbol_info in exchange_info.get('symbols', []):
                if symbol_info['symbol'] == symbol:
                    return symbol_info
            
            return {}
            
        except Exception as e:
            print(f"获取交易对信息失败: {e}")
            return {}
    
    def format_quantity(self, symbol: str, quantity: float) -> str:
        """格式化数量"""
        try:
            symbol_info = self.get_symbol_info(symbol)
            
            for filter_info in symbol_info.get('filters', []):
                if filter_info['filterType'] == 'LOT_SIZE':
                    step_size = float(filter_info['stepSize'])
                    
                    # 计算精度
                    precision = 0
                    if step_size < 1:
                        precision = len(str(step_size).split('.')[1].rstrip('0'))
                    
                    # 格式化数量
                    formatted = f"{quantity:.{precision}f}".rstrip('0').rstrip('.')
                    return formatted
            
            # 默认精度
            return f"{quantity:.8f}".rstrip('0').rstrip('.')
            
        except Exception as e:
            print(f"格式化数量失败: {e}")
            return f"{quantity:.8f}".rstrip('0').rstrip('.')
    
    def sell_asset(self, asset: str, quantity: float) -> bool:
        """卖出资产换USDT"""
        try:
            if asset in self.stable_coins:
                print(f"⏭️ 跳过稳定币: {asset}")
                return True
            
            # 寻找最佳交易对
            best_pair = None
            for quote in ['USDT', 'BUSD', 'USDC']:
                pair = f"{asset}{quote}"
                symbol_info = self.get_symbol_info(pair)
                
                if symbol_info and symbol_info.get('status') == 'TRADING':
                    best_pair = pair
                    break
            
            if not best_pair:
                print(f"❌ 找不到 {asset} 的可用交易对")
                return False
            
            # 格式化数量
            formatted_quantity = self.format_quantity(best_pair, quantity)
            
            print(f"💰 卖出 {formatted_quantity} {asset} (交易对: {best_pair})")
            
            # 执行市价卖单
            order_params = {
                'symbol': best_pair,
                'side': 'SELL',
                'type': 'MARKET',
                'quantity': formatted_quantity
            }
            
            result = self._make_request("/api/v3/order", order_params, "POST")
            
            if result and 'orderId' in result:
                print(f"✅ 卖单成功: {result['orderId']}")
                
                # 等待订单执行
                time.sleep(1)
                
                # 检查订单状态
                order_status = self._make_request("/api/v3/order", {
                    'symbol': best_pair,
                    'orderId': result['orderId']
                })
                
                if order_status.get('status') in ['FILLED', 'PARTIALLY_FILLED']:
                    filled_qty = float(order_status.get('executedQty', 0))
                    print(f"✅ 订单执行: {filled_qty} {asset}")
                    return True
                else:
                    print(f"⚠️ 订单状态: {order_status.get('status')}")
                    return False
            else:
                print(f"❌ 卖单失败: {asset}")
                return False
                
        except Exception as e:
            print(f"卖出资产失败 {asset}: {e}")
            return False
    
    def clear_all_positions(self) -> Dict:
        """清仓所有持仓"""
        print("🚀 开始清仓所有非USDT资产...")
        print("=" * 50)
        
        # 获取余额
        balances = self.get_account_balances()
        
        if not balances:
            print("❌ 无法获取余额信息")
            return {'success': False, 'error': '无法获取余额'}
        
        print(f"📊 发现 {len(balances)} 种资产:")
        
        total_value_before = 0.0
        cleared_assets = []
        failed_assets = []
        
        for balance in balances:
            asset = balance['asset']
            total_qty = balance['total']
            
            # 获取价格计算价值
            price = self.get_asset_price(asset)
            value = total_qty * price
            total_value_before += value
            
            print(f"  {asset}: {total_qty:.8f} (约 ${value:.2f})")
            
            # 判断是否需要清仓
            if asset in self.stable_coins:
                print(f"    ⏭️ 稳定币，保留")
                continue
            
            if value < self.min_clear_value:
                print(f"    ⏭️ 价值过低，跳过 (${value:.2f} < ${self.min_clear_value})")
                continue
            
            if balance['free'] <= 0:
                print(f"    ⏭️ 无可用余额，跳过")
                continue
            
            # 执行清仓
            print(f"    🔄 清仓中...")
            success = self.sell_asset(asset, balance['free'])
            
            if success:
                cleared_assets.append({
                    'asset': asset,
                    'quantity': balance['free'],
                    'value': value
                })
                print(f"    ✅ 清仓成功")
            else:
                failed_assets.append({
                    'asset': asset,
                    'quantity': balance['free'],
                    'value': value
                })
                print(f"    ❌ 清仓失败")
            
            print()
            time.sleep(2)  # 避免API限制
        
        print("=" * 50)
        print("📊 清仓总结:")
        print(f"✅ 成功清仓: {len(cleared_assets)} 种资产")
        print(f"❌ 清仓失败: {len(failed_assets)} 种资产")
        
        cleared_value = sum(item['value'] for item in cleared_assets)
        print(f"💰 清仓价值: ${cleared_value:.2f}")
        
        # 获取最终USDT余额
        time.sleep(3)
        final_balances = self.get_account_balances()
        usdt_balance = 0.0
        
        for balance in final_balances:
            if balance['asset'] == 'USDT':
                usdt_balance = balance['total']
                break
        
        print(f"💵 最终USDT余额: {usdt_balance:.2f}U")
        print("🎯 量化交易资金准备完毕！")
        
        return {
            'success': True,
            'cleared_assets': cleared_assets,
            'failed_assets': failed_assets,
            'total_value_before': total_value_before,
            'cleared_value': cleared_value,
            'final_usdt_balance': usdt_balance
        }
    
    def check_current_positions(self) -> Dict:
        """检查当前持仓（不执行清仓）"""
        print("🔍 检查当前持仓...")
        
        balances = self.get_account_balances()
        
        if not balances:
            return {'error': '无法获取余额'}
        
        total_value = 0.0
        positions = []
        
        for balance in balances:
            asset = balance['asset']
            total_qty = balance['total']
            
            if total_qty > 0:
                price = self.get_asset_price(asset)
                value = total_qty * price
                total_value += value
                
                positions.append({
                    'asset': asset,
                    'quantity': total_qty,
                    'free': balance['free'],
                    'locked': balance['locked'],
                    'price': price,
                    'value': value,
                    'is_stable': asset in self.stable_coins
                })
        
        # 按价值排序
        positions.sort(key=lambda x: x['value'], reverse=True)
        
        print(f"\n📊 持仓概况 (总价值: ${total_value:.2f}):")
        print("-" * 80)
        print(f"{'资产':<8} {'数量':<15} {'可用':<15} {'价格':<10} {'价值':<10} {'类型'}")
        print("-" * 80)
        
        for pos in positions:
            asset_type = "稳定币" if pos['is_stable'] else "加密货币"
            print(f"{pos['asset']:<8} {pos['quantity']:<15.8f} {pos['free']:<15.8f} "
                  f"${pos['price']:<9.4f} ${pos['value']:<9.2f} {asset_type}")
        
        return {
            'positions': positions,
            'total_value': total_value,
            'count': len(positions)
        }

def main():
    """主函数"""
    cleaner = PositionCleaner()
    
    print("🎯 资产清仓工具")
    print("=" * 50)
    
    while True:
        print("\n请选择操作:")
        print("1. 检查当前持仓")
        print("2. 清仓所有非USDT资产")
        print("3. 退出")
        
        choice = input("\n请输入选择 (1-3): ").strip()
        
        if choice == '1':
            result = cleaner.check_current_positions()
            
        elif choice == '2':
            confirm = input("\n⚠️  确认要清仓所有非USDT资产吗？ (yes/no): ").strip().lower()
            
            if confirm == 'yes':
                result = cleaner.clear_all_positions()
                
                if result.get('success'):
                    print(f"\n🎉 清仓完成！最终USDT余额: {result['final_usdt_balance']:.2f}U")
                    print("💡 现在可以启动安全自动交易引擎了！")
                else:
                    print(f"\n❌ 清仓失败: {result.get('error')}")
            else:
                print("取消清仓操作")
                
        elif choice == '3':
            print("退出程序")
            break
            
        else:
            print("无效选择，请重试")

if __name__ == "__main__":
    main() 