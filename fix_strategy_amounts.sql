
-- 连接数据库并修复策略参数
\c quantitative;

-- 修复动量策略参数
UPDATE strategies SET parameters = '{"lookback_period": 20, "threshold": 0.02, "quantity": 1.0, "momentum_threshold": 0.01, "volume_threshold": 2.0}'::jsonb WHERE type = 'momentum';

-- 修复均值回归策略参数  
UPDATE strategies SET parameters = '{"lookback_period": 30, "std_multiplier": 2.0, "quantity": 1.0, "reversion_threshold": 0.02, "min_deviation": 0.01}'::jsonb WHERE type = 'mean_reversion';

-- 修复网格交易策略参数
UPDATE strategies SET parameters = '{"grid_spacing": 0.5, "grid_count": 8, "quantity": 0.5, "lookback_period": 100, "min_profit": 0.3}'::jsonb WHERE type = 'grid_trading';

-- 修复突破策略参数
UPDATE strategies SET parameters = '{"lookback_period": 20, "breakout_threshold": 1.5, "quantity": 1.0, "volume_threshold": 2.0, "confirmation_periods": 3}'::jsonb WHERE type = 'breakout';

-- 修复高频策略参数
UPDATE strategies SET parameters = '{"quantity": 0.8, "min_profit": 0.03, "volatility_threshold": 0.001, "lookback_period": 10, "signal_interval": 30}'::jsonb WHERE type = 'high_frequency';

-- 修复趋势跟踪策略参数
UPDATE strategies SET parameters = '{"lookback_period": 50, "trend_threshold": 1.0, "quantity": 1.2, "trend_strength_min": 0.3}'::jsonb WHERE type = 'trend_following';

-- 查看修复结果
SELECT name, type, parameters->>'quantity' as quantity FROM strategies ORDER BY type;
