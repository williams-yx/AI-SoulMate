-- 为 comments 表新增 videos 字段（幂等）
ALTER TABLE comments
ADD COLUMN IF NOT EXISTS videos JSONB DEFAULT '[]'::jsonb;

-- 历史数据兜底：若存在 NULL 值，统一归一化为空数组
UPDATE comments
SET videos = '[]'::jsonb
WHERE videos IS NULL;
