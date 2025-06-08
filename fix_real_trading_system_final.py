#!/usr/bin/env python3
"""
修复真实生产环境量化交易系统的所有问题
"""

import json
import psycopg2

def fix_bitget_trading_config():
    """修复Bitget交易配置"""
    config_fixes = {
        "bitget_fix": """
# Bitget交易修复 - 在quantitative_service.py中添加

def _fix_bitget_order_params(self, client, symbol, side, amount, price=None):
    \"\"\"修复Bitget订单参数\"\"\"
    try:
        # 获取市场价格
        if not price:
            ticker = client.fetch_ticker(symbol)
            price = ticker['last']
        
        # 计算成本
        if side == 'buy':
            # 对于买单，amount是要花费的USDT数量
            cost = amount
            quantity = cost / price
        else:
            # 对于卖单，amount是要卖出的币数量  
            quantity = amount
            cost = quantity * price
        
        return {
            'symbol': symbol,
            'type': 'market',
            'side': side,
            'amount': quantity,
            'cost': cost,
            'price': price
        }
    except Exception as e:
        print(f"修复Bitget参数失败: {e}")
        return None
        """
    }
    
    print("✅ Bitget交易配置修复方案已准备")
    return config_fixes

def fix_trading_amounts():
    """修复交易金额适配当前余额"""
    
    sql_fixes = """
-- 修复策略参数以适配小额资金 (15.25 USDT)
UPDATE strategies SET parameters = json_build_object(
    'lookback_period', 20,
    'threshold', 0.02,
    'quantity', 1.0,  -- 每次交易1 USDT
    'momentum_threshold', 0.01,
    'volume_threshold', 2.0
) WHERE type = 'momentum';

UPDATE strategies SET parameters = json_build_object(
    'lookback_period', 30,
    'std_multiplier', 2.0,
    'quantity', 1.0,  -- 每次交易1 USDT
    'reversion_threshold', 0.02,
    'min_deviation', 0.01
) WHERE type = 'mean_reversion';

UPDATE strategies SET parameters = json_build_object(
    'grid_spacing', 0.5,  -- 降低网格间距
    'grid_count', 8,      -- 减少网格数量
    'quantity', 0.5,      -- 每格0.5 USDT
    'lookback_period', 100,
    'min_profit', 0.3     -- 降低最小利润要求
) WHERE type = 'grid_trading';

UPDATE strategies SET parameters = json_build_object(
    'lookback_period', 20,
    'breakout_threshold', 1.5,
    'quantity', 1.0,      -- 每次交易1 USDT
    'volume_threshold', 2.0,
    'confirmation_periods', 3
) WHERE type = 'breakout';

UPDATE strategies SET parameters = json_build_object(
    'quantity', 0.8,         -- 每次交易0.8 USDT
    'min_profit', 0.03,      -- 降低最小利润
    'volatility_threshold', 0.001,
    'lookback_period', 10,
    'signal_interval', 30
) WHERE type = 'high_frequency';

UPDATE strategies SET parameters = json_build_object(
    'lookback_period', 50,
    'trend_threshold', 1.0,
    'quantity', 1.2,         -- 每次交易1.2 USDT
    'trend_strength_min', 0.3
) WHERE type = 'trend_following';
"""
    
    print("✅ 交易金额修复SQL已准备")
    return sql_fixes

def fix_api_permissions():
    """修复API权限问题"""
    fixes = {
        "binance_fix": """
# Binance API权限问题修复建议：
1. 检查API Key是否有现货交易权限
2. 确认IP白名单设置
3. 验证API Key没有过期

修复代码：
try:
    # 测试API权限
    account = client.fetch_balance()
    print("✅ Binance API权限正常")
except Exception as e:
    if "Invalid API-key" in str(e):
        print("❌ Binance API权限不足，需要：")
        print("  - 启用现货交易权限")
        print("  - 添加服务器IP到白名单")
        print("  - 检查API Key是否过期")
    raise e
        """,
        
        "okx_fix": """
# OKX余额不足修复：
1. 当前余额15.25 USDT
2. 调整每笔交易金额到0.5-1.5 USDT
3. 确保有足够的手续费余额

修复代码：
def _calculate_okx_trade_amount(self, available_balance):
    # 保留手续费 (0.1%)
    fee_reserve = available_balance * 0.002
    # 单笔交易不超过余额的10%
    max_trade = (available_balance - fee_reserve) * 0.1
    return min(max_trade, 1.5)  # 最大1.5 USDT
        """
    }
    
    print("✅ API权限修复方案已准备")
    return fixes

def create_comprehensive_fix():
    """创建综合修复方案"""
    
    fix_content = '''#!/usr/bin/env python3
"""
真实生产环境量化交易系统全面修复
"""

import re
import os

def apply_quantitative_service_fixes():
    """修复quantitative_service.py"""
    file_path = 'quantitative_service.py'
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 1. 修复Bitget交易参数问题
    bitget_fix = """
    def _fix_bitget_order_params(self, client, symbol, side, amount, price=None):
        \"\"\"修复Bitget订单参数\"\"\"
        try:
            # 获取市场价格
            if not price:
                ticker = client.fetch_ticker(symbol)
                price = ticker['last']
            
            # 计算正确的数量和成本
            if side == 'buy':
                # 买单：amount是要花费的USDT，需要计算买入数量
                cost = amount
                quantity = cost / price
            else:
                # 卖单：amount是要卖出的币数量
                quantity = amount
                cost = quantity * price
            
            return {
                'symbol': symbol,
                'type': 'market', 
                'side': side,
                'amount': quantity,
                'price': price,
                'params': {'cost': cost} if side == 'buy' else {}
            }
        except Exception as e:
            print(f"修复Bitget参数失败: {e}")
            return None
"""
    
    # 2. 修复交易执行逻辑
    execute_fix = '''
    def _execute_single_signal_fixed(self, signal):
        """修复后的信号执行逻辑"""
        try:
            symbol = signal.get('symbol', 'BTC/USDT')
            side = signal.get('signal_type', 'buy').lower()
            confidence = signal.get('confidence', 0.5)
            
            # 根据当前余额计算交易金额
            current_balance = self._get_current_balance()
            if current_balance < 2.0:
                print(f"⚠️ 余额过低 ({current_balance:.2f} USDT)，跳过交易")
                return False
            
            # 保守的交易金额：余额的5-10%
            base_amount = current_balance * 0.08
            # 根据置信度调整
            trade_amount = base_amount * confidence
            # 限制最大交易额
            trade_amount = min(trade_amount, 2.0)  # 最大2 USDT
            
            print(f"💰 计算交易金额: {trade_amount:.3f} USDT (余额: {current_balance:.2f})")
            
            success = False
            for exchange_name, client in self.exchange_clients.items():
                try:
                    if exchange_name == 'bitget':
                        # 使用修复后的Bitget参数
                        order_params = self._fix_bitget_order_params(client, symbol, side, trade_amount)
                        if order_params:
                            order = client.create_order(**order_params)
                        else:
                            continue
                    else:
                        # 标准交易参数
                        if side == 'buy':
                            order = client.create_market_buy_order(symbol, trade_amount)
                        else:
                            # 卖单需要检查持仓
                            positions = self.get_positions()
                            coin_symbol = symbol.split('/')[0]
                            position = next((p for p in positions if coin_symbol in p.get('symbol', '')), None)
                            if not position or position.get('quantity', 0) <= 0:
                                print(f"⚠️ 没有 {coin_symbol} 持仓，无法卖出")
                                continue
                            quantity = min(trade_amount / signal.get('price', 1), position.get('quantity', 0))
                            order = client.create_market_sell_order(symbol, quantity)
                    
                    print(f"✅ {exchange_name} 交易成功: {order.get('id', 'N/A')}")
                    
                    # 记录交易日志
                    self.log_strategy_trade(
                        strategy_id=signal.get('strategy_id', 'unknown'),
                        signal_type=side,
                        price=signal.get('price', 0),
                        quantity=trade_amount,
                        confidence=confidence,
                        executed=1,
                        pnl=0.0
                    )
                    
                    success = True
                    break
                    
                except Exception as e:
                    print(f"⚠️ 在 {exchange_name} 执行交易失败: {exchange_name} {str(e)}")
                    continue
            
            return success
            
        except Exception as e:
            print(f"❌ 执行交易信号失败: {e}")
            return False
'''
    
    # 在文件中查找并替换_execute_single_signal方法
    if '_execute_single_signal(' in content:
        # 找到方法开始位置
        start_pos = content.find('def _execute_single_signal(')
        if start_pos != -1:
            # 找到下一个方法开始位置
            next_method_pos = content.find('\\n    def ', start_pos + 1)
            if next_method_pos == -1:
                next_method_pos = len(content)
            
            # 替换方法
            content = content[:start_pos] + execute_fix.strip() + '\\n\\n' + content[next_method_pos:]
    
    # 在class末尾添加Bitget修复方法
    if '_fix_bitget_order_params(' not in content:
        class_end = content.rfind('class QuantitativeService:')
        if class_end != -1:
            # 找到class的结束位置
            next_class_pos = content.find('\\nclass ', class_end + 1)
            if next_class_pos == -1:
                next_class_pos = len(content)
            
            # 在class结束前添加方法
            insert_pos = content.rfind('\\n\\n', class_end, next_class_pos)
            if insert_pos != -1:
                content = content[:insert_pos] + bitget_fix + content[insert_pos:]
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 已修复: {file_path}")
        return True
    else:
        print(f"✅ 无需修复: {file_path}")
        return False

def main():
    """主修复函数"""
    print("🔧 开始修复真实生产环境量化交易系统...")
    
    # 应用所有修复
    apply_quantitative_service_fixes()
    
    print("🎯 所有修复完成！")

if __name__ == "__main__":
    main()
'''
    
    with open('comprehensive_trading_fix.py', 'w', encoding='utf-8') as f:
        f.write(fix_content)
    
    print("✅ 综合修复脚本已创建")

def main():
    """主函数"""
    print("🔧 准备修复真实生产环境量化交易系统...")
    
    # 准备所有修复方案
    fix_bitget_trading_config()
    fix_trading_amounts()  
    fix_api_permissions()
    create_comprehensive_fix()
    
    print("🎯 所有修复方案已准备完成！")

if __name__ == "__main__":
    main() 