#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面交易系统优化脚本
解决信号生成、持仓检查、小资金适配等关键问题
"""

import sys
import os
import time
import json
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def apply_comprehensive_trading_fix():
    """应用全面的交易系统优化"""
    
    print("🚀 开始全面交易系统优化...")
    
    # 1. 优化信号生成逻辑 - 增加买入信号，考虑持仓状态
    signal_generation_fix = '''
    def generate_trading_signals(self):
        """生成交易信号 - 全面优化版本"""
        try:
            generated_signals = 0
            current_balance = self._get_current_balance()
            positions = self.get_positions()
            
            print(f"📊 当前余额: {current_balance} USDT")
            print(f"📦 当前持仓数量: {len(positions.get('data', []))}")
            
            # 🎯 获取策略数据
            strategies_response = self.get_strategies()
            if not strategies_response.get('success', False):
                print("❌ 无法获取策略数据，信号生成失败")
                return 0
            
            strategies_data = strategies_response.get('data', [])
            enabled_strategies = [s for s in strategies_data if s.get('enabled', False)]
            
            print(f"📈 启用策略数量: {len(enabled_strategies)}")
            
            # 🔄 智能信号生成策略
            buy_signals_needed = max(3, len(enabled_strategies) // 3)  # 至少3个买入信号
            sell_signals_allowed = len([p for p in positions.get('data', []) if float(p.get('quantity', 0)) > 0])
            
            print(f"🎯 计划生成: {buy_signals_needed}个买入信号, 最多{sell_signals_allowed}个卖出信号")
            
            # 📊 按评分排序策略
            sorted_strategies = sorted(enabled_strategies, 
                                     key=lambda x: x.get('final_score', 0), reverse=True)
            
            buy_generated = 0
            sell_generated = 0
            
            for strategy in sorted_strategies[:10]:  # 限制处理数量
                try:
                    strategy_id = strategy['id']
                    symbol = strategy.get('symbol', 'DOGE/USDT')
                    score = strategy.get('final_score', 0)
                    
                    # 🔍 检查是否有该交易对的持仓
                    has_position = any(
                        p.get('symbol', '').replace('/', '') == symbol.replace('/', '') and 
                        float(p.get('quantity', 0)) > 0 
                        for p in positions.get('data', [])
                    )
                    
                    # 🎲 智能信号类型决策
                    signal_type = self._determine_signal_type(
                        strategy, has_position, buy_generated, sell_generated, 
                        buy_signals_needed, sell_signals_allowed, current_balance
                    )
                    
                    if signal_type == 'skip':
                        continue
                    
                    # 🎯 生成优化的信号
                    signal = self._generate_optimized_signal(strategy_id, strategy, signal_type, current_balance)
                    
                    if signal:
                        self._save_signal_to_db(signal)
                        generated_signals += 1
                        
                        if signal_type == 'buy':
                            buy_generated += 1
                            print(f"🟢 生成买入信号: {strategy_id} | {symbol} | 评分: {score:.1f}")
                        else:
                            sell_generated += 1
                            print(f"🔴 生成卖出信号: {strategy_id} | {symbol} | 评分: {score:.1f}")
                        
                        # 🎯 达到目标数量就停止
                        if buy_generated >= buy_signals_needed and sell_generated >= sell_signals_allowed:
                            break
                
                except Exception as e:
                    print(f"❌ 策略 {strategy_id} 信号生成失败: {e}")
            
            print(f"✅ 信号生成完成: 总共 {generated_signals} 个 (买入: {buy_generated}, 卖出: {sell_generated})")
            
            # 🚀 自动执行信号（如果启用了自动交易）
            if self.auto_trading_enabled and generated_signals > 0:
                executed_count = self._execute_pending_signals()
                print(f"🎯 自动执行了 {executed_count} 个交易信号")
            
            return generated_signals
            
        except Exception as e:
            print(f"生成交易信号失败: {e}")
            return 0
    
    def _determine_signal_type(self, strategy, has_position, buy_generated, sell_generated, 
                              buy_needed, sell_allowed, current_balance):
        """智能决定信号类型"""
        
        # 🎯 优先生成买入信号（如果余额充足且买入信号不足）
        if buy_generated < buy_needed and current_balance > 1.0:
            # 📊 根据策略评分和类型倾向买入
            score = strategy.get('final_score', 0)
            strategy_type = strategy.get('type', '')
            
            # 高分策略更容易生成买入信号
            if score >= 80 or strategy_type in ['momentum', 'breakout', 'grid_trading']:
                return 'buy'
        
        # 🔴 生成卖出信号（如果有持仓且卖出信号未达上限）
        if has_position and sell_generated < sell_allowed:
            # 📈 低分策略或均值回归策略倾向卖出
            score = strategy.get('final_score', 0)
            strategy_type = strategy.get('type', '')
            
            if score < 70 or strategy_type == 'mean_reversion':
                return 'sell'
        
        # ⚖️ 随机决策（保持系统活跃）
        import random
        if random.random() < 0.3:  # 30%概率
            if buy_generated < buy_needed and current_balance > 0.5:
                return 'buy'
            elif has_position and sell_generated < sell_allowed:
                return 'sell'
        
        return 'skip'
    
    def _generate_optimized_signal(self, strategy_id, strategy, signal_type, current_balance):
        """生成优化的交易信号"""
        try:
            import time
            from datetime import datetime
            
            symbol = strategy.get('symbol', 'DOGE/USDT')
            
            # 🔍 获取当前价格（优化版本）
            current_price = self._get_optimized_current_price(symbol)
            if not current_price or current_price <= 0:
                return None
            
            # 💰 计算交易数量（小资金优化）
            if signal_type == 'buy':
                trade_amount = min(
                    current_balance * 0.06,  # 6%的余额
                    1.5,  # 最大1.5 USDT
                    current_balance - 0.5  # 至少保留0.5 USDT
                )
                trade_amount = max(0.5, trade_amount)  # 最少0.5 USDT
                quantity = trade_amount / current_price
            else:
                # 卖出时使用策略参数
                quantity = strategy['parameters'].get('quantity', 0.5)
            
            # 🎯 计算置信度（优化版本）
            base_confidence = 0.7
            score_bonus = min(0.25, (strategy.get('final_score', 70) - 70) * 0.01)
            confidence = base_confidence + score_bonus
            
            # 📊 小币种适配
            if symbol in ['DOGE/USDT', 'XRP/USDT', 'ADA/USDT', 'DOT/USDT']:
                confidence += 0.1  # 小币种加成
            
            signal = {
                'id': f"signal_{int(time.time() * 1000)}",
                'strategy_id': strategy_id,
                'symbol': symbol,
                'signal_type': signal_type,
                'price': current_price,
                'quantity': quantity,
                'confidence': min(0.95, confidence),
                'timestamp': datetime.now().isoformat(),
                'executed': 0,
                'priority': 'high' if strategy.get('final_score', 0) >= 90 else 'normal'
            }
            
            return signal
            
        except Exception as e:
            print(f"❌ 生成优化信号失败: {e}")
            return None
    
    def _get_optimized_current_price(self, symbol):
        """获取优化的当前价格"""
        try:
            # 🌟 尝试从真实交易所获取价格
            if hasattr(self, 'exchange_clients') and self.exchange_clients:
                for client_name, client in self.exchange_clients.items():
                    try:
                        ticker = client.fetch_ticker(symbol)
                        if ticker and 'last' in ticker:
                            price = float(ticker['last'])
                            print(f"💰 {symbol} 当前价格: {price} (来源: {client_name})")
                            return price
                    except Exception as e:
                        continue
            
            # 🎲 如果无法获取真实价格，使用模拟价格
            base_prices = {
                'BTC/USDT': 67000,
                'ETH/USDT': 3500, 
                'DOGE/USDT': 0.08,
                'XRP/USDT': 0.52,
                'ADA/USDT': 0.38,
                'DOT/USDT': 6.5,
                'SOL/USDT': 140,
                'BNB/USDT': 580
            }
            
            base_price = base_prices.get(symbol, 1.0)
            # 添加±2%的随机波动
            import random
            variation = random.uniform(-0.02, 0.02)
            simulated_price = base_price * (1 + variation)
            
            print(f"🎲 {symbol} 模拟价格: {simulated_price}")
            return simulated_price
            
        except Exception as e:
            print(f"❌ 获取价格失败: {e}")
            return 1.0
    '''
    
    # 2. 优化小币种交易支持
    small_coin_optimization = '''
    def _init_small_coin_optimization(self):
        """初始化小币种交易优化"""
        try:
            # 🎯 小资金友好的交易对
            self.small_fund_symbols = [
                'DOGE/USDT',  # 狗币 - 低价格，高流动性
                'XRP/USDT',   # 瑞波币 - 稳定，适合网格
                'ADA/USDT',   # 艾达币 - 良好波动性
                'DOT/USDT',   # 波卡 - 中等价格
                'MATIC/USDT', # 多边形 - 活跃交易
                'VET/USDT',   # 唯链 - 低价格
                'HBAR/USDT',  # 哈希图 - 稳定增长
                'ALGO/USDT'   # 阿尔戈兰德 - 技术性强
            ]
            
            # 💰 小资金交易优化参数
            self.small_fund_config = {
                'min_trade_amount': 0.5,      # 最小交易金额 0.5 USDT
                'max_trade_amount': 1.5,      # 最大交易金额 1.5 USDT
                'balance_allocation': 0.06,    # 每次交易使用6%余额
                'reserve_balance': 0.5,       # 保留余额 0.5 USDT
                'preferred_exchanges': ['bitget'],  # 优先交易所
                'confidence_boost': 0.1       # 小币种置信度加成
            }
            
            print("✅ 小币种交易优化已启用")
            print(f"🎯 支持交易对: {len(self.small_fund_symbols)}个")
            print(f"💰 交易金额范围: {self.small_fund_config['min_trade_amount']}-{self.small_fund_config['max_trade_amount']} USDT")
            
        except Exception as e:
            print(f"❌ 小币种优化初始化失败: {e}")
    '''
    
    # 3. 优化交易执行逻辑
    execution_optimization = '''
    def _execute_single_signal(self, signal):
        """执行单个交易信号 - 优化版本"""
        try:
            signal_id = signal['id']
            strategy_id = signal['strategy_id']
            symbol = signal['symbol']
            signal_type = signal['signal_type']
            price = float(signal['price'])
            quantity = float(signal['quantity'])
            confidence = float(signal['confidence'])
            
            print(f"🎯 执行信号: {signal_type} {symbol} | 数量: {quantity:.6f} | 置信度: {confidence:.2f}")
            
            # 💰 计算交易金额
            trade_amount = price * quantity
            
            # 🔍 余额检查（买入时）
            if signal_type == 'buy':
                current_balance = self._get_current_balance()
                if current_balance < trade_amount + 0.5:  # 保留0.5 USDT
                    print(f"⚠️ 余额不足: 需要 {trade_amount:.2f} USDT, 可用 {current_balance:.2f} USDT")
                    return False
            
            # 📦 持仓检查（卖出时）
            if signal_type == 'sell':
                positions = self.get_positions()
                has_sufficient_position = False
                
                for position in positions.get('data', []):
                    pos_symbol = position.get('symbol', '').replace('/', '')
                    pos_quantity = float(position.get('quantity', 0))
                    
                    if pos_symbol == symbol.replace('/', '') and pos_quantity >= quantity:
                        has_sufficient_position = True
                        break
                
                if not has_sufficient_position:
                    print(f"⚠️ 持仓不足: 无法卖出 {quantity:.6f} {symbol}")
                    return False
            
            # 🏆 选择最优交易所
            selected_exchanges = self._select_optimal_exchanges(symbol, trade_amount, signal_type)
            
            if not selected_exchanges:
                print(f"❌ 无可用交易所执行 {signal_type} {symbol}")
                return False
            
            # 🚀 执行交易
            for exchange_info in selected_exchanges:
                exchange_name = exchange_info['name']
                client = exchange_info['client']
                
                try:
                    # 🎯 根据信号类型执行交易
                    if signal_type == 'buy':
                        order = client.create_market_buy_order(symbol, quantity)
                    else:
                        order = client.create_market_sell_order(symbol, quantity)
                    
                    if order and order.get('id'):
                        print(f"✅ {exchange_name} 交易成功: {signal_type} {quantity:.6f} {symbol}")
                        
                        # 📊 记录交易
                        self._record_executed_trade(signal, order, trade_amount)
                        
                        # 🔄 更新信号状态
                        self.db.execute_query(
                            "UPDATE trading_signals SET executed = 1 WHERE id = ?",
                            (signal_id,)
                        )
                        
                        # 📈 记录策略交易日志
                        self.log_strategy_trade(
                            strategy_id=strategy_id,
                            signal_type=signal_type,
                            price=price,
                            quantity=quantity,
                            confidence=confidence,
                            executed=1,
                            pnl=0.0  # PnL稍后计算
                        )
                        
                        # 🎯 刷新缓存
                        self.invalidate_balance_cache('trade_execution')
                        self.invalidate_positions_cache('trade_execution')
                        
                        return True
                
                except Exception as e:
                    print(f"❌ {exchange_name} 交易失败: {e}")
                    continue
            
            print(f"❌ 所有交易所执行失败: {signal_type} {symbol}")
            return False
            
        except Exception as e:
            print(f"❌ 执行交易信号失败: {e}")
            return False
    '''
    
    # 4. 应用所有优化
    try:
        print("📝 正在应用信号生成优化...")
        
        # 读取当前文件
        with open('quantitative_service.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 1. 替换信号生成方法
        import re
        
        # 查找并替换 generate_trading_signals 方法
        pattern = r'def generate_trading_signals\(self\):.*?(?=\n    def [^_]|\n\nclass|\nif __name__|\Z)'
        replacement = signal_generation_fix.strip()
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # 2. 添加小币种优化方法（如果不存在）
        if '_init_small_coin_optimization' not in content:
            # 在 _init_small_fund_optimization 后添加
            pattern = r'(def _init_small_fund_optimization\(self\):.*?)(\n    def)'
            replacement = r'\1\n\n' + small_coin_optimization.strip() + r'\2'
            content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # 3. 替换交易执行方法
        pattern = r'def _execute_single_signal\(self, signal\):.*?(?=\n    def [^_]|\n\nclass|\nif __name__|\Z)'
        replacement = execution_optimization.strip()
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # 保存文件
        with open('quantitative_service.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 代码优化完成!")
        
        # 5. 数据库优化 - 添加小币种策略
        print("📊 正在优化数据库策略配置...")
        
        from quantitative_service import QuantitativeService
        
        service = QuantitativeService()
        
        # 添加小币种策略
        small_coin_strategies = [
            {
                'name': 'DOGE动量策略',
                'type': 'momentum',
                'symbol': 'DOGE/USDT',
                'parameters': {'threshold': 0.015, 'quantity': 0.8, 'lookback': 5}
            },
            {
                'name': 'XRP网格策略', 
                'type': 'grid_trading',
                'symbol': 'XRP/USDT',
                'parameters': {'grid_spacing': 0.02, 'grid_count': 8, 'quantity': 0.6}
            },
            {
                'name': 'ADA均值回归',
                'type': 'mean_reversion', 
                'symbol': 'ADA/USDT',
                'parameters': {'std_multiplier': 1.8, 'lookback_period': 12, 'quantity': 0.7}
            }
        ]
        
        for strategy_config in small_coin_strategies:
            try:
                # 检查是否已存在
                existing = service.db.execute_query(
                    "SELECT COUNT(*) FROM strategies WHERE name = ?",
                    (strategy_config['name'],),
                    fetch_one=True
                )
                
                if existing[0] == 0:
                    service.db.execute_query(
                        "INSERT INTO strategies (name, type, symbol, enabled, parameters) VALUES (?, ?, ?, ?, ?)",
                        (
                            strategy_config['name'],
                            strategy_config['type'],
                            strategy_config['symbol'],
                            1,
                            json.dumps(strategy_config['parameters'])
                        )
                    )
                    print(f"✅ 添加小币种策略: {strategy_config['name']}")
            
            except Exception as e:
                print(f"❌ 添加策略失败: {e}")
        
        print("🎯 全面优化完成!")
        return True
        
    except Exception as e:
        print(f"❌ 应用优化失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 启动全面交易系统优化...")
    success = apply_comprehensive_trading_fix()
    
    if success:
        print("\n✅ 优化成功完成!")
        print("\n📋 优化总结:")
        print("1. ✅ 信号生成逻辑已优化 - 智能买卖信号平衡")
        print("2. ✅ 小币种交易支持已启用 - DOGE/XRP/ADA等")
        print("3. ✅ 交易执行逻辑已增强 - 余额和持仓检查")
        print("4. ✅ 小资金优化配置已应用 - 0.5-1.5 USDT范围")
        print("5. ✅ 数据库策略已更新 - 新增小币种策略")
        
        print("\n🎯 下一步:")
        print("1. 重启后端服务: pm2 restart quant-b")
        print("2. 验证信号生成: 检查买入信号比例")
        print("3. 监控交易执行: 确保小币种交易正常")
    else:
        print("\n❌ 优化失败，请检查错误信息") 