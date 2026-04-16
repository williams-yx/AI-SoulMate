-- 积分系统重构迁移脚本
-- 执行此脚本前请备份数据库

-- 1. 创建 credit_recharges 表（如果不存在）
CREATE TABLE IF NOT EXISTS credit_recharges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,
    bonus_amount INTEGER DEFAULT 0,
    total_amount INTEGER NOT NULL,
    amount_yuan DECIMAL(10, 2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    payment_id VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    paid_at TIMESTAMP WITH TIME ZONE,
    remaining_credits INTEGER DEFAULT 0,
    refunded_at TIMESTAMP WITH TIME ZONE,
    refund_amount DECIMAL(10, 2),
    refund_reason TEXT,
    CONSTRAINT credit_recharges_amount_check CHECK (amount > 0 AND amount <= 100000),
    CONSTRAINT credit_recharges_amount_yuan_check CHECK (amount_yuan > 0),
    CONSTRAINT credit_recharges_bonus_amount_check CHECK (bonus_amount >= 0),
    CONSTRAINT credit_recharges_total_amount_check CHECK (total_amount = amount + bonus_amount)
);

-- 2. 创建索引
CREATE INDEX IF NOT EXISTS idx_credit_recharges_user_id ON credit_recharges(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_recharges_status ON credit_recharges(status);
CREATE INDEX IF NOT EXISTS idx_credit_recharges_created_at ON credit_recharges(created_at DESC);

-- 3. 创建积分消耗记录表
CREATE TABLE IF NOT EXISTS credit_consumption_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recharge_id UUID REFERENCES credit_recharges(id) ON DELETE SET NULL,
    amount INTEGER NOT NULL,
    credit_type VARCHAR(20) NOT NULL,
    reason VARCHAR(100),
    related_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT credit_consumption_amount_check CHECK (amount > 0)
);

-- 4. 创建索引
CREATE INDEX IF NOT EXISTS idx_credit_consumption_user_id ON credit_consumption_records(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_consumption_recharge_id ON credit_consumption_records(recharge_id);

-- 5. 合并 gift_points 到 paid_points
UPDATE users 
SET paid_points = COALESCE(paid_points, 0) + COALESCE(gift_points, 0)
WHERE gift_points > 0 OR gift_points IS NOT NULL;

-- 6. 初始化已支付订单的 remaining_credits
UPDATE credit_recharges 
SET remaining_credits = total_amount 
WHERE status = 'paid' AND (remaining_credits IS NULL OR remaining_credits = 0);

-- 迁移完成
SELECT 'Migration completed successfully!' AS status;
