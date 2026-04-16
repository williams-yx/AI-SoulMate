"""
将旧版 users 表迁移到新结构：users + user_identities

旧表字段：id, username, email, password_hash, phone, credits, avatar, role, created_at, is_active, openid, github_id
新表 users：id, nickname, avatar, primary_email, primary_phone, points, role, is_active, created_at
新表 user_identities：id, user_id, provider, identifier, credential, linked_at

运行方式（在 backend 目录下）：
  python scripts/migrate_users_to_identities.py

或项目根目录：
  python -m backend.scripts.migrate_users_to_identities

需设置环境变量 DATABASE_URL，或使用默认 postgresql://postgres:password@localhost:5432/ai_soulmate
"""

import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg
from config import Config


async def run_migration():
    database_url = os.getenv("DATABASE_URL", Config.DATABASE_URL)
    conn = await asyncpg.connect(database_url)

    try:
        # 1. 检查是否为旧版 users（是否有 username 列）
        row = await conn.fetchrow("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'username'
        """)
        if not row:
            print("users 表已是新结构或不存在，无需迁移。")
            return

        print("检测到旧版 users 表，开始迁移...")

        async with conn.transaction():
            # 2. 创建 user_identities 表（若不存在）
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_identities (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    provider VARCHAR(50) NOT NULL,
                    identifier VARCHAR(255) NOT NULL,
                    credential JSONB DEFAULT '{}',
                    linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(provider, identifier),
                    UNIQUE(user_id, provider)
                )
            """)
            print("  - user_identities 表已就绪")

            # 3. 添加新列到 users（若不存在）
            for col, typ in [
                ("nickname", "VARCHAR(100)"),
                ("primary_email", "VARCHAR(255)"),
                ("primary_phone", "VARCHAR(50)"),
                ("points", "INTEGER DEFAULT 1000"),
            ]:
                exists = await conn.fetchval("""
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = $1
                """, col)
                if not exists:
                    await conn.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")
                    print(f"  - 已添加列 users.{col}")

            # 4. 复制数据到新列
            await conn.execute("""
                UPDATE users SET
                    nickname = username,
                    primary_email = email,
                    primary_phone = phone,
                    points = COALESCE(credits, 1000)
                WHERE username IS NOT NULL
            """)
            print("  - 已复制 nickname/primary_email/primary_phone/points")

            # 5. 为每个用户写入 user_identities
            users = await conn.fetch("""
                SELECT id, username, email, password_hash, phone, openid, github_id FROM users
            """)
            for u in users:
                uid, username, email, password_hash, phone, openid, github_id = (
                    u["id"], u["username"], u["email"], u["password_hash"],
                    u["phone"], u["openid"], u["github_id"]
                )
                identities = []
                if username:
                    identities.append((
                        uid, "account", username,
                        json.dumps({"password_hash": password_hash} if password_hash else {})
                    ))
                if email:
                    identities.append((uid, "email", email, "{}"))
                if phone:
                    identities.append((uid, "phone", str(phone).strip(), "{}"))
                if openid:
                    identities.append((uid, "wechat", openid, "{}"))
                if github_id:
                    identities.append((uid, "github", str(github_id), "{}"))

                for user_id, provider, identifier, credential in identities:
                    await conn.execute("""
                        INSERT INTO user_identities (user_id, provider, identifier, credential)
                        VALUES ($1, $2, $3, $4::jsonb)
                        ON CONFLICT (user_id, provider) DO UPDATE SET
                            identifier = EXCLUDED.identifier,
                            credential = EXCLUDED.credential
                    """, user_id, provider, identifier, credential)

            print(f"  - 已为 {len(users)} 个用户写入 user_identities")

            # 6. 删除旧列（会连带删除其上的 UNIQUE 约束）
            cols_to_drop = ["username", "email", "password_hash", "phone", "credits", "openid", "github_id"]
            for col in cols_to_drop:
                exists = await conn.fetchval("""
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = $1
                """, col)
                if exists:
                    await conn.execute(f"ALTER TABLE users DROP COLUMN IF EXISTS {col}")
                    print(f"  - 已删除列 users.{col}")

            # 7. 为新列添加 UNIQUE（若尚未存在）
            for col in ["primary_email", "primary_phone"]:
                idx = f"users_{col}_key"
                has = await conn.fetchval("""
                    SELECT 1 FROM pg_constraint WHERE conname = $1 AND conrelid = 'public.users'::regclass
                """, idx)
                if not has:
                    await conn.execute(f"ALTER TABLE users ADD CONSTRAINT {idx} UNIQUE ({col})")
                    print(f"  - 已添加 UNIQUE users.{col}")

            # 8. 索引
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_identities_user_id ON user_identities(user_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_identities_provider_identifier ON user_identities(provider, identifier)")
            print("  - 索引已就绪")

        print("迁移完成。")
    except Exception as e:
        print(f"迁移失败: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run_migration())
