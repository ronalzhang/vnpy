#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
量化交易策略参数范围控制脚本
解决quantity等参数进化过程中的异常值问题
"""

import psycopg2
import json
from decimal import Decimal

# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'database': 'quantitative',
    'user': 'quant_user',
    'password': '123abc74531'
}

# 参数范围配置
PARAMETER_RANGES = {
    # 交易数量参数 - 这是数字币的购买数量
    'quantity': {
        'min': 0.00001,    # 最小交易单位，符合大部分交易所规则
        'max': 10.0,       # 最大数量限制，基于合理的资金使用（假设100U余额，BTC 10万U，最多买0.001个）
        'default': 0.001,  # 默认值：约100U的BTC
        'description': '数字币交易数量'
    },
    
    # 价格阈值参数 - 百分比形式
    'threshold': {
        'min': 0.001,     # 0.1%
        'max': 0.05,      # 5%
        'default': 0.01,  # 1%
        'description': '价格变动阈值百分比'
    },
    
    'trend_threshold': {
        'min': 0.005,     # 0.5%
        'max': 0.03,      # 3%
        'default': 0.015, # 1.5%
        'description': '趋势确认阈值百分比'
    },
    
    'breakout_threshold': {
        'min': 0.005,     # 0.5%
        'max': 0.03,      # 3%
        'default': 0.015, # 1.5%
        'description': '突破阈值百分比'
    },
    
    'momentum_threshold': {
        'min': 0.005,     # 0.5%
        'max': 0.025,     # 2.5%
        'default': 0.01,  # 1%
        'description': '动量阈值百分比'
    },
    
    # 止损止盈参数
    'stop_loss_pct': {
        'min': 0.5,       # 0.5%
        'max': 10.0,      # 10%
        'default': 2.0,   # 2%
        'description': '止损百分比'
    },
    
    'take_profit_pct': {
        'min': 0.5,       # 0.5%
        'max': 20.0,      # 20%
        'default': 4.0,   # 4%
        'description': '止盈百分比'
    },
    
    'trailing_stop_pct': {
        'min': 0.5,       # 0.5%
        'max': 10.0,      # 10%
        'default': 3.0,   # 3%
        'description': '跟踪止损百分比'
    },
    
    # 时间周期参数
    'lookback_period': {
        'min': 5,         # 最少5个周期
        'max': 200,       # 最多200个周期
        'default': 20,    # 默认20个周期
        'description': '回望周期数'
    },
    
    'rsi_period': {
        'min': 10,        # RSI最少10周期
        'max': 30,        # RSI最多30周期
        'default': 14,    # 标准RSI周期
        'description': 'RSI计算周期'
    },
    
    'ema_fast_period': {
        'min': 5,         # 快线最少5周期
        'max': 50,        # 快线最多50周期
        'default': 12,    # 默认12周期
        'description': '快速EMA周期'
    },
    
    'ema_slow_period': {
        'min': 20,        # 慢线最少20周期
        'max': 200,       # 慢线最多200周期
        'default': 26,    # 默认26周期
        'description': '慢速EMA周期'
    },
    
    # 网格交易参数
    'grid_spacing': {
        'min': 0.1,       # 0.1%网格间距
        'max': 5.0,       # 5%网格间距
        'default': 1.0,   # 1%网格间距
        'description': '网格间距百分比'
    },
    
    'grid_count': {
        'min': 3,         # 最少3个网格
        'max': 20,        # 最多20个网格
        'default': 10,    # 默认10个网格
        'description': '网格数量'
    },
    
    # 倍数参数
    'volume_threshold': {
        'min': 1.0,       # 最少1倍成交量
        'max': 5.0,       # 最多5倍成交量
        'default': 2.0,   # 默认2倍成交量
        'description': '成交量倍数阈值'
    },
    
    'std_multiplier': {
        'min': 1.0,       # 1倍标准差
        'max': 4.0,       # 4倍标准差
        'default': 2.0,   # 2倍标准差
        'description': '标准差倍数'
    },
    
    'atr_multiplier': {
        'min': 1.0,       # 1倍ATR
        'max': 5.0,       # 5倍ATR
        'default': 2.0,   # 2倍ATR
        'description': 'ATR倍数'
    },
    
    # 仓位风险参数
    'max_position_risk': {
        'min': 0.01,      # 1%仓位风险
        'max': 0.2,       # 20%仓位风险
        'default': 0.05,  # 5%仓位风险
        'description': '最大仓位风险百分比'
    },
    
    'position_sizing': {
        'min': 1,         # 最小仓位数量
        'max': 100,       # 最大仓位数量
        'default': 10,    # 默认仓位数量
        'description': '仓位大小'
    },
    
    # 置信度和分数参数
    'trend_strength_min': {
        'min': 0.1,       # 10%最小趋势强度
        'max': 1.0,       # 100%最大趋势强度
        'default': 0.3,   # 30%默认趋势强度
        'description': '最小趋势强度'
    },
    
    'confidence_threshold': {
        'min': 0.5,       # 50%最小置信度
        'max': 1.0,       # 100%最大置信度
        'default': 0.7,   # 70%默认置信度
        'description': '信号置信度阈值'
    }
}

def validate_and_fix_parameter(param_name, value, ranges):
    """
    验证并修复单个参数值
    """
    if param_name not in ranges:
        return value  # 不在控制范围内的参数保持原值
    
    param_range = ranges[param_name]
    min_val = param_range['min']
    max_val = param_range['max']
    default_val = param_range['default']
    
    try:
        num_value = float(value)
        
        # 检查是否超出范围
        if num_value < min_val or num_value > max_val:
            print(f"  ⚠️  参数 {param_name} 值 {num_value} 超出范围 [{min_val}, {max_val}]，重置为 {default_val}")
            return default_val
        else:
            return num_value
            
    except (ValueError, TypeError):
        print(f"  ⚠️  参数 {param_name} 值 {value} 无效，重置为 {default_val}")
        return default_val

def fix_strategy_parameters():
    """
    修复所有策略的参数范围问题
    """
    try:
        # 连接数据库
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("🔧 开始修复策略参数范围...")
        print(f"📋 支持的参数类型: {len(PARAMETER_RANGES)} 种")
        
        # 查询所有有参数的策略
        cursor.execute("""
            SELECT id, name, parameters 
            FROM strategies 
            WHERE parameters IS NOT NULL AND parameters != 'null'
        """)
        
        strategies = cursor.fetchall()
        print(f"📊 找到 {len(strategies)} 个有参数的策略")
        
        fixed_count = 0
        total_param_fixes = 0
        
        for strategy_id, strategy_name, params_json in strategies:
            try:
                # 解析参数
                params = json.loads(params_json)
                if not isinstance(params, dict):
                    continue
                
                # 检查并修复参数
                original_params = params.copy()
                param_fixed = False
                
                for param_name, param_value in params.items():
                    if param_name in PARAMETER_RANGES:
                        fixed_value = validate_and_fix_parameter(param_name, param_value, PARAMETER_RANGES)
                        if fixed_value != param_value:
                            params[param_name] = fixed_value
                            param_fixed = True
                            total_param_fixes += 1
                
                # 如果有参数被修复，更新数据库
                if param_fixed:
                    cursor.execute("""
                        UPDATE strategies 
                        SET parameters = %s 
                        WHERE id = %s
                    """, (json.dumps(params), strategy_id))
                    
                    fixed_count += 1
                    print(f"✅ 修复策略: {strategy_name} (ID: {strategy_id})")
                    
            except Exception as e:
                print(f"❌ 处理策略 {strategy_name} 失败: {e}")
                continue
        
        # 提交更改
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"\n🎯 修复完成!")
        print(f"📈 修复策略数量: {fixed_count}")
        print(f"🔧 修复参数总数: {total_param_fixes}")
        print("\n✅ 所有参数现在都在合理范围内，模拟交易验证应该能正常运行")
        
        return True
        
    except Exception as e:
        print(f"❌ 修复过程出错: {e}")
        return False

def show_parameter_ranges():
    """
    显示所有参数的合理范围
    """
    print("\n📋 策略参数合理范围配置:")
    print("=" * 80)
    
    categories = {
        '交易数量': ['quantity'],
        '价格阈值': ['threshold', 'trend_threshold', 'breakout_threshold', 'momentum_threshold'],
        '风险控制': ['stop_loss_pct', 'take_profit_pct', 'trailing_stop_pct', 'max_position_risk'],
        '时间周期': ['lookback_period', 'rsi_period', 'ema_fast_period', 'ema_slow_period'],
        '网格交易': ['grid_spacing', 'grid_count'],
        '倍数参数': ['volume_threshold', 'std_multiplier', 'atr_multiplier'],
        '其他参数': ['position_sizing', 'trend_strength_min', 'confidence_threshold']
    }
    
    for category, params in categories.items():
        print(f"\n🔹 {category}:")
        for param in params:
            if param in PARAMETER_RANGES:
                config = PARAMETER_RANGES[param]
                print(f"  {param:20} | 范围: [{config['min']:8}, {config['max']:8}] | 默认: {config['default']:8} | {config['description']}")

if __name__ == "__main__":
    print("🚀 量化交易策略参数范围控制工具")
    print("=" * 50)
    
    # 显示参数范围配置
    show_parameter_ranges()
    
    # 执行修复
    if fix_strategy_parameters():
        print("\n🎉 参数范围修复成功！")
    else:
        print("\n💥 参数范围修复失败！") 