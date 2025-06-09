#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
策略参数统一配置模块
提供所有策略类型的完整参数配置，确保前后端、数据库、进化系统完全同步
"""

# 🎯 统一的策略参数配置 - 所有模块共用
STRATEGY_PARAMETERS_CONFIG = {
    'momentum': {
        # 基础参数
        'lookback_period': {'default': 20, 'range': (10, 50), 'type': 'int', 'description': '回望周期'},
        'threshold': {'default': 0.02, 'range': (0.01, 0.05), 'type': 'float', 'description': '动量阈值'},
        'quantity': {'default': 100, 'range': (50, 200), 'type': 'float', 'description': '交易数量'},
        'momentum_threshold': {'default': 0.01, 'range': (0.005, 0.03), 'type': 'float', 'description': '动量检测阈值'},
        'volume_threshold': {'default': 2.0, 'range': (1.0, 5.0), 'type': 'float', 'description': '成交量阈值'},
        
        # 技术指标参数 - RSI
        'rsi_period': {'default': 14, 'range': (10, 30), 'type': 'int', 'description': 'RSI周期'},
        'rsi_oversold': {'default': 30, 'range': (20, 40), 'type': 'int', 'description': 'RSI超卖线'},
        'rsi_overbought': {'default': 70, 'range': (60, 80), 'type': 'int', 'description': 'RSI超买线'},
        
        # MACD指标参数
        'macd_fast_period': {'default': 12, 'range': (8, 18), 'type': 'int', 'description': 'MACD快线周期'},
        'macd_slow_period': {'default': 26, 'range': (20, 35), 'type': 'int', 'description': 'MACD慢线周期'},
        'macd_signal_period': {'default': 9, 'range': (7, 15), 'type': 'int', 'description': 'MACD信号线周期'},
        
        # 价格动量参数
        'price_momentum_period': {'default': 10, 'range': (5, 20), 'type': 'int', 'description': '价格动量周期'},
        'volume_momentum_period': {'default': 20, 'range': (10, 30), 'type': 'int', 'description': '成交量动量周期'},
        'price_change_filter': {'default': 0.005, 'range': (0.001, 0.02), 'type': 'float', 'description': '价格变化过滤器'},
        
        # 风险控制参数
        'stop_loss_pct': {'default': 2.0, 'range': (1.0, 5.0), 'type': 'float', 'description': '止损百分比'},
        'take_profit_pct': {'default': 4.0, 'range': (2.0, 8.0), 'type': 'float', 'description': '止盈百分比'},
        'max_drawdown_pct': {'default': 5.0, 'range': (2.0, 10.0), 'type': 'float', 'description': '最大回撤百分比'},
        'position_sizing': {'default': 0.1, 'range': (0.05, 0.25), 'type': 'float', 'description': '仓位大小比例'},
        'min_hold_time': {'default': 300, 'range': (60, 1800), 'type': 'int', 'description': '最小持有时间(秒)'},
        'max_hold_time': {'default': 3600, 'range': (1800, 7200), 'type': 'int', 'description': '最大持有时间(秒)'}
    },
    
    'mean_reversion': {
        # 基础参数
        'lookback_period': {'default': 30, 'range': (15, 60), 'type': 'int', 'description': '回望周期'},
        'std_multiplier': {'default': 2.0, 'range': (1.5, 3.0), 'type': 'float', 'description': '标准差倍数'},
        'quantity': {'default': 100, 'range': (50, 200), 'type': 'float', 'description': '交易数量'},
        'reversion_threshold': {'default': 0.02, 'range': (0.01, 0.05), 'type': 'float', 'description': '回归阈值'},
        'min_deviation': {'default': 0.01, 'range': (0.005, 0.03), 'type': 'float', 'description': '最小偏差'},
        
        # 布林带参数
        'bb_period': {'default': 20, 'range': (10, 40), 'type': 'int', 'description': '布林带周期'},
        'bb_std_dev': {'default': 2.0, 'range': (1.5, 3.0), 'type': 'float', 'description': '布林带标准差'},
        'bb_squeeze_threshold': {'default': 0.1, 'range': (0.05, 0.2), 'type': 'float', 'description': '布林带收敛阈值'},
        
        # 均值回归指标
        'z_score_threshold': {'default': 2.0, 'range': (1.5, 3.0), 'type': 'float', 'description': 'Z-score阈值'},
        'correlation_threshold': {'default': 0.7, 'range': (0.5, 0.9), 'type': 'float', 'description': '相关性阈值'},
        'mean_reversion_strength': {'default': 0.3, 'range': (0.1, 0.6), 'type': 'float', 'description': '回归强度'},
        'volatility_adjustment': {'default': 1.0, 'range': (0.5, 2.0), 'type': 'float', 'description': '波动率调整系数'},
        
        # 风险管理参数
        'stop_loss_pct': {'default': 1.5, 'range': (0.8, 3.0), 'type': 'float', 'description': '止损百分比'},
        'take_profit_pct': {'default': 3.0, 'range': (1.5, 5.0), 'type': 'float', 'description': '止盈百分比'},
        'max_positions': {'default': 3, 'range': (1, 5), 'type': 'int', 'description': '最大持仓数'},
        'max_hold_period': {'default': 24, 'range': (6, 72), 'type': 'int', 'description': '最大持有时间(小时)'},
        'risk_per_trade': {'default': 0.02, 'range': (0.01, 0.05), 'type': 'float', 'description': '单笔交易风险'}
    },
    
    'grid_trading': {
        # 网格基础参数
        'grid_spacing': {'default': 1.0, 'range': (0.5, 3.0), 'type': 'float', 'description': '网格间距百分比'},
        'grid_count': {'default': 10, 'range': (5, 20), 'type': 'int', 'description': '网格数量'},
        'quantity': {'default': 1000, 'range': (500, 2000), 'type': 'float', 'description': '交易数量'},
        'lookback_period': {'default': 100, 'range': (50, 200), 'type': 'int', 'description': '回望周期'},
        'min_profit': {'default': 0.5, 'range': (0.2, 1.0), 'type': 'float', 'description': '最小利润百分比'},
        
        # 网格高级参数
        'upper_price_limit': {'default': 110000, 'range': (90000, 150000), 'type': 'float', 'description': '上限价格'},
        'lower_price_limit': {'default': 90000, 'range': (50000, 110000), 'type': 'float', 'description': '下限价格'},
        'grid_density': {'default': 0.5, 'range': (0.2, 1.0), 'type': 'float', 'description': '网格密度'},
        'rebalance_threshold': {'default': 5.0, 'range': (2.0, 10.0), 'type': 'float', 'description': '再平衡阈值'},
        'profit_taking_ratio': {'default': 0.8, 'range': (0.5, 1.0), 'type': 'float', 'description': '获利回吐比例'},
        'grid_spacing_type': {'default': 'arithmetic', 'range': ['arithmetic', 'geometric'], 'type': 'str', 'description': '网格间距类型'},
        
        # 动态调整参数
        'volatility_adjustment': {'default': True, 'range': [True, False], 'type': 'bool', 'description': '波动率调整'},
        'trend_following_factor': {'default': 0.3, 'range': (0.1, 0.6), 'type': 'float', 'description': '趋势跟随因子'},
        'grid_stop_loss': {'default': 8.0, 'range': (5.0, 15.0), 'type': 'float', 'description': '网格止损百分比'},
        'max_grid_exposure': {'default': 10000, 'range': (5000, 20000), 'type': 'float', 'description': '最大网格敞口'},
        'emergency_stop_loss': {'default': 10.0, 'range': (5.0, 20.0), 'type': 'float', 'description': '紧急止损百分比'},
        'dynamic_adjustment': {'default': True, 'range': [True, False], 'type': 'bool', 'description': '动态调整'}
    },
    
    'breakout': {
        # 突破基础参数
        'lookback_period': {'default': 20, 'range': (10, 40), 'type': 'int', 'description': '回望周期'},
        'breakout_threshold': {'default': 1.5, 'range': (0.8, 3.0), 'type': 'float', 'description': '突破阈值'},
        'quantity': {'default': 50, 'range': (25, 100), 'type': 'float', 'description': '交易数量'},
        'volume_threshold': {'default': 2.0, 'range': (1.2, 4.0), 'type': 'float', 'description': '成交量确认倍数'},
        'confirmation_periods': {'default': 3, 'range': (1, 6), 'type': 'int', 'description': '确认周期数'},
        
        # 技术指标确认
        'atr_period': {'default': 14, 'range': (10, 25), 'type': 'int', 'description': 'ATR周期'},
        'atr_multiplier': {'default': 2.0, 'range': (1.5, 3.0), 'type': 'float', 'description': 'ATR倍数'},
        'volume_ma_period': {'default': 20, 'range': (10, 30), 'type': 'int', 'description': '成交量移动平均周期'},
        'price_ma_period': {'default': 50, 'range': (20, 100), 'type': 'int', 'description': '价格移动平均周期'},
        'momentum_confirmation': {'default': True, 'range': [True, False], 'type': 'bool', 'description': '动量确认'},
        'volume_confirmation': {'default': True, 'range': [True, False], 'type': 'bool', 'description': '成交量确认'},
        
        # 假突破过滤
        'false_breakout_filter': {'default': 0.5, 'range': (0.2, 0.8), 'type': 'float', 'description': '假突破过滤强度'},
        'consolidation_detection': {'default': True, 'range': [True, False], 'type': 'bool', 'description': '整理期检测'},
        'trend_strength_filter': {'default': 0.6, 'range': (0.3, 0.9), 'type': 'float', 'description': '趋势强度过滤'},
        
        # 风险控制
        'stop_loss_atr_multiple': {'default': 2.0, 'range': (1.5, 3.0), 'type': 'float', 'description': '止损ATR倍数'},
        'take_profit_atr_multiple': {'default': 4.0, 'range': (2.0, 6.0), 'type': 'float', 'description': '止盈ATR倍数'},
        'max_holding_period': {'default': 48, 'range': (12, 96), 'type': 'int', 'description': '最大持有时间(小时)'}
    },
    
    'high_frequency': {
        # 高频基础参数
        'quantity': {'default': 100, 'range': (50, 200), 'type': 'float', 'description': '交易数量'},
        'min_profit': {'default': 0.05, 'range': (0.01, 0.1), 'type': 'float', 'description': '最小利润百分比'},
        'volatility_threshold': {'default': 0.001, 'range': (0.0005, 0.005), 'type': 'float', 'description': '波动率阈值'},
        'lookback_period': {'default': 10, 'range': (5, 20), 'type': 'int', 'description': '回望周期'},
        'signal_interval': {'default': 30, 'range': (10, 60), 'type': 'int', 'description': '信号间隔(秒)'},
        
        # 微观结构参数
        'bid_ask_spread_threshold': {'default': 0.01, 'range': (0.005, 0.02), 'type': 'float', 'description': '买卖价差阈值'},
        'order_book_depth_min': {'default': 1000, 'range': (500, 2000), 'type': 'float', 'description': '最小订单簿深度'},
        'tick_size_multiple': {'default': 1.0, 'range': (0.5, 3.0), 'type': 'float', 'description': '最小变动单位倍数'},
        'latency_threshold': {'default': 100, 'range': (50, 200), 'type': 'int', 'description': '延迟阈值(毫秒)'},
        'market_impact_limit': {'default': 0.001, 'range': (0.0005, 0.005), 'type': 'float', 'description': '市场影响限制'},
        'slippage_tolerance': {'default': 0.002, 'range': (0.001, 0.005), 'type': 'float', 'description': '滑点容忍度'},
        
        # 高频交易优化
        'inventory_turnover_target': {'default': 10.0, 'range': (5.0, 20.0), 'type': 'float', 'description': '库存周转目标'},
        'risk_limit_per_trade': {'default': 0.01, 'range': (0.005, 0.02), 'type': 'float', 'description': '单笔风险限制'},
        'max_position_duration': {'default': 300, 'range': (60, 600), 'type': 'int', 'description': '最大持仓时间(秒)'},
        'profit_target_multiplier': {'default': 1.5, 'range': (1.2, 2.0), 'type': 'float', 'description': '利润目标倍数'},
        
        # 算法交易参数
        'execution_algorithm': {'default': 'twap', 'range': ['twap', 'vwap', 'pov'], 'type': 'str', 'description': '执行算法'},
        'order_split_size': {'default': 100, 'range': (50, 200), 'type': 'float', 'description': '订单拆分大小'},
        'adaptive_sizing': {'default': True, 'range': [True, False], 'type': 'bool', 'description': '自适应仓位大小'},
        'momentum_detection': {'default': True, 'range': [True, False], 'type': 'bool', 'description': '动量检测'},
        'mean_reversion_mode': {'default': False, 'range': [True, False], 'type': 'bool', 'description': '均值回归模式'},
        'max_inventory_limit': {'default': 5000, 'range': (2000, 10000), 'type': 'float', 'description': '最大库存限制'}
    },
    
    'trend_following': {
        # 趋势基础参数
        'lookback_period': {'default': 50, 'range': (20, 100), 'type': 'int', 'description': '回望周期'},
        'trend_threshold': {'default': 1.0, 'range': (0.5, 2.0), 'type': 'float', 'description': '趋势阈值'},
        'quantity': {'default': 100, 'range': (50, 200), 'type': 'float', 'description': '交易数量'},
        'trend_strength_min': {'default': 0.3, 'range': (0.2, 0.6), 'type': 'float', 'description': '最小趋势强度'},
        'trend_duration_min': {'default': 30, 'range': (15, 60), 'type': 'int', 'description': '最小趋势持续时间(分钟)'},
        
        # 趋势识别参数
        'ema_fast_period': {'default': 12, 'range': (8, 20), 'type': 'int', 'description': '快速EMA周期'},
        'ema_slow_period': {'default': 26, 'range': (20, 50), 'type': 'int', 'description': '慢速EMA周期'},
        'adx_period': {'default': 14, 'range': (10, 25), 'type': 'int', 'description': 'ADX周期'},
        'adx_threshold': {'default': 25, 'range': (20, 35), 'type': 'int', 'description': 'ADX阈值'},
        'slope_threshold': {'default': 0.001, 'range': (0.0005, 0.003), 'type': 'float', 'description': '斜率阈值'},
        'trend_angle_min': {'default': 15, 'range': (10, 30), 'type': 'int', 'description': '最小趋势角度'},
        
        # 趋势确认指标
        'macd_confirmation': {'default': True, 'range': [True, False], 'type': 'bool', 'description': 'MACD确认'},
        'volume_confirmation': {'default': True, 'range': [True, False], 'type': 'bool', 'description': '成交量确认'},
        'rsi_filter': {'default': True, 'range': [True, False], 'type': 'bool', 'description': 'RSI过滤'},
        'multi_timeframe': {'default': True, 'range': [True, False], 'type': 'bool', 'description': '多时间框架确认'},
        
        # 进出场管理
        'trailing_stop_pct': {'default': 3.0, 'range': (2.0, 5.0), 'type': 'float', 'description': '移动止损百分比'},
        'profit_lock_pct': {'default': 2.0, 'range': (1.0, 4.0), 'type': 'float', 'description': '利润锁定百分比'},
        'trend_reversal_detection': {'default': True, 'range': [True, False], 'type': 'bool', 'description': '趋势反转检测'},
        'position_scaling': {'default': True, 'range': [True, False], 'type': 'bool', 'description': '仓位缩放'},
        'max_drawdown_exit': {'default': 5.0, 'range': (3.0, 8.0), 'type': 'float', 'description': '最大回撤退出百分比'},
        'trend_strength_exit': {'default': 0.2, 'range': (0.1, 0.4), 'type': 'float', 'description': '趋势强度退出阈值'}
    }
}

def get_strategy_default_parameters(strategy_type: str) -> dict:
    """获取策略的默认参数"""
    if strategy_type not in STRATEGY_PARAMETERS_CONFIG:
        return {}
    
    defaults = {}
    for param, config in STRATEGY_PARAMETERS_CONFIG[strategy_type].items():
        defaults[param] = config['default']
    return defaults

def get_strategy_parameter_ranges(strategy_type: str) -> dict:
    """获取策略参数的有效范围"""
    if strategy_type not in STRATEGY_PARAMETERS_CONFIG:
        return {}
    
    ranges = {}
    for param, config in STRATEGY_PARAMETERS_CONFIG[strategy_type].items():
        ranges[param] = config['range']
    return ranges

def validate_strategy_parameters(strategy_type: str, parameters: dict) -> tuple:
    """验证策略参数是否在有效范围内"""
    if strategy_type not in STRATEGY_PARAMETERS_CONFIG:
        return False, f"未知策略类型: {strategy_type}"
    
    config = STRATEGY_PARAMETERS_CONFIG[strategy_type]
    errors = []
    
    for param, value in parameters.items():
        if param in config:
            param_config = config[param]
            param_range = param_config['range']
            param_type = param_config['type']
            
            # 类型检查
            if param_type == 'int' and not isinstance(value, int):
                errors.append(f"{param}: 期望整数类型，得到 {type(value)}")
                continue
            elif param_type == 'float' and not isinstance(value, (int, float)):
                errors.append(f"{param}: 期望数值类型，得到 {type(value)}")
                continue
            elif param_type == 'bool' and not isinstance(value, bool):
                errors.append(f"{param}: 期望布尔类型，得到 {type(value)}")
                continue
            elif param_type == 'str' and not isinstance(value, str):
                errors.append(f"{param}: 期望字符串类型，得到 {type(value)}")
                continue
            
            # 范围检查
            if param_type in ['int', 'float'] and isinstance(param_range, tuple):
                min_val, max_val = param_range
                if value < min_val or value > max_val:
                    errors.append(f"{param}: 值 {value} 超出范围 [{min_val}, {max_val}]")
            elif param_type in ['str', 'bool'] and isinstance(param_range, list):
                if value not in param_range:
                    errors.append(f"{param}: 值 {value} 不在允许列表 {param_range} 中")
    
    if errors:
        return False, "; ".join(errors)
    return True, "参数验证通过"

def get_all_strategy_types() -> list:
    """获取所有支持的策略类型"""
    return list(STRATEGY_PARAMETERS_CONFIG.keys())

def get_strategy_parameter_description(strategy_type: str, parameter: str) -> str:
    """获取参数描述"""
    if (strategy_type in STRATEGY_PARAMETERS_CONFIG and 
        parameter in STRATEGY_PARAMETERS_CONFIG[strategy_type]):
        return STRATEGY_PARAMETERS_CONFIG[strategy_type][parameter]['description']
    return "无描述"

# 🔧 为兼容现有代码提供的辅助函数
def get_legacy_template_parameters(strategy_type: str) -> dict:
    """为与现有quantitative_service.py模板兼容而提供的参数范围"""
    if strategy_type not in STRATEGY_PARAMETERS_CONFIG:
        return {}
    
    template = {'param_ranges': {}}
    for param, config in STRATEGY_PARAMETERS_CONFIG[strategy_type].items():
        template['param_ranges'][param] = config['range']
    return template 