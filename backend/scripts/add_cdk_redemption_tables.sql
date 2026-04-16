-- CDK 兑换功能数据库迁移

ALTER TABLE public.users ADD COLUMN IF NOT EXISTS redeemed_points integer DEFAULT 0;
ALTER TABLE public.user_identities ADD COLUMN IF NOT EXISTS redeemed_contributed integer DEFAULT 0 NOT NULL;

CREATE TABLE IF NOT EXISTS public.cdk_redemption_codes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code_hash char(64) NOT NULL UNIQUE,
    code_prefix varchar(12),
    points integer NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'active',
    max_redeem_count integer NOT NULL DEFAULT 1,
    redeemed_count integer NOT NULL DEFAULT 0,
    redeemed_by_user_id uuid REFERENCES public.users(id) ON DELETE SET NULL,
    redeemed_at timestamp with time zone,
    expires_at timestamp with time zone,
    note text,
    created_by uuid REFERENCES public.users(id) ON DELETE SET NULL,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT cdk_redemption_codes_points_check CHECK (points > 0),
    CONSTRAINT cdk_redemption_codes_status_check CHECK (status IN ('active', 'used', 'disabled', 'expired')),
    CONSTRAINT cdk_redemption_codes_max_redeem_count_check CHECK (max_redeem_count > 0),
    CONSTRAINT cdk_redemption_codes_redeemed_count_check CHECK (redeemed_count >= 0)
);

CREATE INDEX IF NOT EXISTS idx_cdk_redemption_codes_status
    ON public.cdk_redemption_codes(status, expires_at, redeemed_count);

CREATE TABLE IF NOT EXISTS public.cdk_redemption_records (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code_id uuid NOT NULL REFERENCES public.cdk_redemption_codes(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    points integer NOT NULL,
    code_prefix varchar(12),
    client_ip varchar(64),
    user_agent text,
    redeemed_at timestamp with time zone DEFAULT now(),
    CONSTRAINT cdk_redemption_records_points_check CHECK (points > 0)
);

CREATE INDEX IF NOT EXISTS idx_cdk_redemption_records_user_id
    ON public.cdk_redemption_records(user_id, redeemed_at DESC);

CREATE INDEX IF NOT EXISTS idx_cdk_redemption_records_code_id
    ON public.cdk_redemption_records(code_id);
