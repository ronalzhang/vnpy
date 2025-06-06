#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复真实评分和余额API
1. 移除get_account_info的错误容错，让API失败时显示"-"
2. 启动真实的策略模拟评分系统
3. 恢复真实的余额API调用
"""

import sys
import os

def fix_get_account_info():
    """修复get_account_info，移除错误的容错机制"""
    
    new_method = '''
    def get_account_info(self):
        """获取账户信息 - 真实API调用，失败时返回失败状态"""
        try:
            # 获取当前余额
            current_balance = self._get_current_balance()
            
            # 如果余额获取失败（返回0或None），直接返回失败状态
            if current_balance is None or current_balance <= 0:
                print("❌ 余额获取失败，API未正确连接")
                return {
                    'success': False,
                    'error': 'API连接失败或余额获取异常',
                    'data': None
                }
            
            # 获取持仓信息
            positions_response = self.get_positions()
            positions = positions_response.get('data', []) if positions_response.get('success') else []
            
            # 计算总持仓价值
            total_position_value = sum(
                pos.get('unrealized_pnl', 0) + pos.get('quantity', 0) * pos.get('current_price', 0) 
                for pos in positions
            )
            
            # 获取余额历史（用于计算收益）
            balance_history = self.get_balance_history(days=1)
            today_start_balance = balance_history.get('data', [{}])[-1].get('total_balance', current_balance) if balance_history.get('success') else current_balance
            
            # 计算今日盈亏
            daily_pnl = current_balance - today_start_balance
            daily_return = (daily_pnl / today_start_balance * 100) if today_start_balance > 0 else 0
            
            # 统计交易次数
            try:
                query = "SELECT COUNT(*) as count FROM strategy_trade_logs WHERE executed = 1"
                result = self.db_manager.execute_query(query, fetch_one=True)
                total_trades = result.get('count', 0) if result else 0
            except Exception as e:
                print(f"查询交易次数失败: {e}")
                total_trades = 0
            
            account_info = {
                'total_balance': round(current_balance, 2),
                'available_balance': round(current_balance, 2),  # 简化处理
                'frozen_balance': 0.0,
                'daily_pnl': round(daily_pnl, 2),
                'daily_return': round(daily_return, 2),
                'total_trades': total_trades,
                'positions_count': len(positions),
                'total_position_value': round(total_position_value, 2),
                'last_updated': datetime.now().isoformat()
            }
            
            print(f"💰 账户信息: 总资产 {account_info['total_balance']}U, 今日盈亏 {account_info['daily_pnl']}U ({account_info['daily_return']}%)")
            
            return {
                'success': True,
                'data': account_info
            }
            
        except Exception as e:
            print(f"❌ 获取账户信息失败: {e}")
            import traceback
            traceback.print_exc()
            
            # 不返回默认值，返回失败状态，让前端显示"-"
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    '''
    
    return new_method

def fix_fetch_fresh_balance():
    """修复_fetch_fresh_balance，调用真实的auto_trading_engine"""
    
    new_method = '''
    def _fetch_fresh_balance(self):
        """获取最新余额 - 调用真实的auto_trading_engine API"""
        try:
            # 延迟导入避免启动时加载
            try:
                from auto_trading_engine import get_trading_engine
                trading_engine = get_trading_engine()
                
                if trading_engine and hasattr(trading_engine, 'exchange'):
                    # 调用真实的交易所API
                    balance_data = trading_engine.exchange.fetch_balance()
                    usdt_balance = float(balance_data['USDT']['free'])
                    
                    print(f"💰 获取真实余额: {usdt_balance}U")
                    
                    return {
                        'usdt_balance': usdt_balance,
                        'position_value': 0.0,  # 简化处理
                        'total_value': usdt_balance
                    }
                else:
                    print("❌ 交易引擎未初始化")
                    return None
                    
            except ImportError:
                print("⚠️ auto_trading_engine模块未找到")
                return None
            except Exception as api_error:
                print(f"❌ API调用失败: {api_error}")
                return None
            
        except Exception as e:
            print(f"❌ 获取余额失败: {e}")
            return None
    '''
    
    return new_method

def reset_scores_to_zero():
    """重置所有策略分数为0，准备真实评分"""
    
    reset_script = '''
from db_config import get_db_adapter

def reset_scores_for_real_evaluation():
    """重置策略分数为0，准备启动真实评分系统"""
    try:
        print("🔄 重置策略分数为0，准备真实评分...")
        
        db_adapter = get_db_adapter()
        
        # 重置所有策略分数为0
        update_query = """
        UPDATE strategies 
        SET final_score = 0, 
            simulation_score = 0,
            fitness_score = 0,
            qualified_for_trading = 0,
            updated_at = CURRENT_TIMESTAMP
        """
        
        db_adapter.execute_query(update_query)
        
        print("✅ 策略分数重置完成，等待真实评分系统启动")
        return True
        
    except Exception as e:
        print(f"❌ 重置分数失败: {e}")
        return False

if __name__ == "__main__":
    reset_scores_for_real_evaluation()
'''
    
    return reset_script

def start_real_simulation_script():
    """创建启动真实模拟评分的脚本"""
    
    script = '''
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from quantitative_service import QuantitativeService

def start_real_simulation():
    """启动真实的策略模拟评分"""
    try:
        print("🚀 启动真实策略模拟评分系统...")
        
        # 初始化量化服务
        service = QuantitativeService()
        
        # 确保数据库和策略初始化
        service.init_database()
        service.init_strategies()
        
        # 运行所有策略模拟评分
        print("🔬 开始运行策略模拟...")
        simulation_results = service.run_all_strategy_simulations()
        
        if simulation_results:
            print(f"✅ 模拟评分完成，评估了 {len(simulation_results)} 个策略")
            
            # 显示前10个高分策略
            sorted_results = sorted(simulation_results.items(), 
                                  key=lambda x: x[1].get('final_score', 0), reverse=True)
            
            print("\\n🏆 前10个高分策略:")
            for i, (strategy_id, result) in enumerate(sorted_results[:10]):
                score = result.get('final_score', 0)
                win_rate = result.get('win_rate', 0)
                return_rate = result.get('total_return', 0)
                print(f"  {i+1}. 策略 {strategy_id}: {score:.1f}分 (胜率: {win_rate:.1f}%, 收益: {return_rate:.2f}%)")
            
        else:
            print("⚠️ 模拟评分未返回结果")
        
        print("\\n🎯 真实评分系统已启动，策略将持续进化优化")
        
    except Exception as e:
        print(f"❌ 启动真实模拟失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    start_real_simulation()
'''
    
    return script

def apply_fixes():
    """应用所有修复"""
    
    try:
        # 读取当前文件
        with open('quantitative_service.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("🔧 开始修复真实评分和余额API...")
        
        import re
        
        # 1. 替换get_account_info方法
        new_get_account_info = fix_get_account_info()
        pattern = r'def get_account_info\(self\):.*?return \{[^}]*\}[^}]*\}'
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, new_get_account_info.strip(), content, flags=re.DOTALL)
            print("✅ 已替换get_account_info方法")
        else:
            print("⚠️ 未找到get_account_info方法")
        
        # 2. 替换_fetch_fresh_balance方法
        new_fetch_balance = fix_fetch_fresh_balance()
        pattern = r'def _fetch_fresh_balance\(self\):.*?(?=\n    def |\nclass |\Z)'
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, new_fetch_balance.strip(), content, flags=re.DOTALL)
            print("✅ 已替换_fetch_fresh_balance方法")
        else:
            print("⚠️ 未找到_fetch_fresh_balance方法")
        
        # 保存修改后的文件
        with open('quantitative_service.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 3. 创建重置分数脚本
        reset_script_content = reset_scores_to_zero()
        with open('reset_scores_to_zero.py', 'w', encoding='utf-8') as f:
            f.write(reset_script_content)
        
        # 4. 创建启动真实模拟脚本
        simulation_script_content = start_real_simulation_script()
        with open('start_real_simulation.py', 'w', encoding='utf-8') as f:
            f.write(simulation_script_content)
        
        print("✅ 修复完成！")
        print("\\n📋 修复内容：")
        print("  1. ✅ get_account_info：API失败时返回success=false，让前端显示'-'")
        print("  2. ✅ _fetch_fresh_balance：调用真实的auto_trading_engine API")
        print("  3. ✅ 创建reset_scores_to_zero.py：重置分数为0")
        print("  4. ✅ 创建start_real_simulation.py：启动真实模拟评分")
        
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = apply_fixes()
    if success:
        print("\\n🎉 修复完成！")
        print("💡 接下来的步骤:")
        print("  1. 运行 python3 reset_scores_to_zero.py 重置分数")
        print("  2. 运行 python3 start_real_simulation.py 启动真实评分")
        print("  3. 重启前后端应用")
        print("  4. 现在余额API失败时会显示'-'，评分基于真实模拟交易")
    else:
        print("\\n💥 修复失败，请检查错误信息。") 