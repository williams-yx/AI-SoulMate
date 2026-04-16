"""
一次性数据修复：清空 users 与 user_identities，得到纯净的账号表。

会先解除所有引用 users 的外键（将 user_id / author_id / admin_id / creator_id 置为 NULL），
再删除 user_identities 与 users 的全部数据。其他业务数据（课程、作品、订单等）保留，
但作者/用户关联会被清空。

运行前请务必备份数据库。

运行方式（在 backend 目录下）：
  python scripts/clear_users_and_identities.py

或项目根目录：
  python -m backend.scripts.clear_users_and_identities

环境变量 DATABASE_URL 可选，默认使用 config 中的连接串。
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg
from config import Config


async def run_clear():
    database_url = os.getenv("DATABASE_URL", Config.DATABASE_URL)
    conn = await asyncpg.connect(database_url)

    try:
        async with conn.transaction():
            # 1. 解除所有引用 users 的外键（置 NULL），避免删除 users 时违反约束
            updates = [
                ("projects", "user_id"),
                ("orders", "user_id"),
                ("assets", "author_id"),
                ("workflows", "creator_id"),
                ("devices", "user_id"),
                ("print_jobs", "user_id"),
                ("addresses", "user_id"),
                ("operation_logs", "admin_id"),
                ("user_courses", "user_id"),
                ("workflow_executions", "user_id"),
            ]
            for table, col in updates:
                try:
                    r = await conn.execute(
                        f'UPDATE {table} SET {col} = NULL WHERE {col} IS NOT NULL'
                    )
                    print(f"  - {table}.{col}: {r}")
                except Exception as e:
                    # 表或列不存在时跳过
                    print(f"  - {table}.{col}: 跳过 ({e})")

            # 2. 删除所有身份与用户（user_model_configs 有 ON DELETE CASCADE，会随 users 删除）
            deleted_id = await conn.fetchval("SELECT COUNT(*) FROM user_identities")
            await conn.execute("DELETE FROM user_identities")
            print(f"  - user_identities: 已删除 {deleted_id} 条")

            deleted_u = await conn.fetchval("SELECT COUNT(*) FROM users")
            await conn.execute("DELETE FROM users")
            print(f"  - users: 已删除 {deleted_u} 条")

        print("")
        print("[OK] 清理完成：users 与 user_identities 已为空，其他表中外键已置 NULL。")
        print("     重启应用后 init_database 会重新创建预设账号（admin、admin02、dev、user01～user20）。")
    finally:
        await conn.close()


def main():
    print("清除所有用户与身份数据（解除外键后清空 users / user_identities）...")
    asyncio.run(run_clear())


if __name__ == "__main__":
    main()
