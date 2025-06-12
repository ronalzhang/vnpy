-- 修复验证系统数据库结构
-- 1. 给trading_signals表添加trade_type字段
ALTER TABLE trading_signals ADD COLUMN IF NOT EXISTS trade_type VARCHAR(50) DEFAULT 'real_trading';
ALTER TABLE trading_signals ADD COLUMN IF NOT EXISTS validation_id VARCHAR(100);
ALTER TABLE trading_signals ADD COLUMN IF NOT EXISTS validation_round INTEGER DEFAULT 0;
ALTER TABLE trading_signals ADD COLUMN IF NOT EXISTS parameters_used JSONB;

-- 2. 创建高分策略验证表
CREATE TABLE IF NOT EXISTS high_score_validation (
    id SERIAL PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    validation_type VARCHAR(50) NOT NULL, -- 'periodic_check', 'score_verification'
    original_score DECIMAL(10,2),
    validation_trades INTEGER DEFAULT 0,
    validation_success_rate DECIMAL(10,2),
    validation_pnl DECIMAL(10,6),
    validation_result VARCHAR(20), -- 'passed', 'failed', 'pending'
    score_adjustment DECIMAL(10,2) DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validation_details JSONB,
    next_validation TIMESTAMP
);

-- 3. 创建索引优化查询
CREATE INDEX IF NOT EXISTS idx_trading_signals_trade_type ON trading_signals(trade_type);
CREATE INDEX IF NOT EXISTS idx_trading_signals_validation_id ON trading_signals(validation_id);
CREATE INDEX IF NOT EXISTS idx_high_score_validation_strategy ON high_score_validation(strategy_id);
CREATE INDEX IF NOT EXISTS idx_high_score_validation_next ON high_score_validation(next_validation);

-- 4. 更新现有数据的trade_type
UPDATE trading_signals SET trade_type = 'real_trading' WHERE trade_type IS NULL;

-- 5. 添加验证交易分类的约束
ALTER TABLE trading_signals ADD CONSTRAINT check_trade_type 
CHECK (trade_type IN ('real_trading', 'optimization_validation', 'initialization_validation', 'periodic_validation', 'score_verification'));

COMMENT ON TABLE high_score_validation IS '高分策略定期验证记录表';
COMMENT ON COLUMN trading_signals.trade_type IS '交易类型：real_trading(真实), optimization_validation(参数验证), initialization_validation(初始验证), periodic_validation(定期验证), score_verification(分数验证)'; 