"""
创建预设用户账号脚本
包含22个账号：1个admin、1个开发测试、20个用户测试账号
"""

import asyncio
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import hash_password
from database import DatabaseManager
from config import Config

# 预设账号列表
PRESET_USERS = [
    # Admin账号
    {
        "username": "admin",
        "password": "admin123",
        "email": "admin@aisoulmate.com",
        "role": "admin",
        "credits": 10000
    },
    # 开发测试账号
    {
        "username": "dev",
        "password": "dev123",
        "email": "dev@aisoulmate.com",
        "role": "student",
        "credits": 5000
    },
    # 20个用户测试账号
    {
        "username": "user01",
        "password": "user123",
        "email": "user01@aisoulmate.com",
        "role": "student",
        "credits": 1000
    },
    {
        "username": "user02",
        "password": "user123",
        "email": "user02@aisoulmate.com",
        "role": "student",
        "credits": 1000
    },
    {
        "username": "user03",
        "password": "user123",
        "email": "user03@aisoulmate.com",
        "role": "student",
        "credits": 1000
    },
    {
        "username": "user04",
        "password": "user123",
        "email": "user04@aisoulmate.com",
        "role": "student",
        "credits": 1000
    },
    {
        "username": "user05",
        "password": "user123",
        "email": "user05@aisoulmate.com",
        "role": "student",
        "credits": 1000
    },
    {
        "username": "user06",
        "password": "user123",
        "email": "user06@aisoulmate.com",
        "role": "student",
        "credits": 1000
    },
    {
        "username": "user07",
        "password": "user123",
        "email": "user07@aisoulmate.com",
        "role": "student",
        "credits": 1000
    },
    {
        "username": "user08",
        "password": "user123",
        "email": "user08@aisoulmate.com",
        "role": "student",
        "credits": 1000
    },
    {
        "username": "user09",
        "password": "user123",
        "email": "user09@aisoulmate.com",
        "role": "student",
        "credits": 1000
    },
    {
        "username": "user10",
        "password": "user123",
        "email": "user10@aisoulmate.com",
        "role": "student",
        "credits": 1000
    },
    {
        "username": "user11",
        "password": "user123",
        "email": "user11@aisoulmate.com",
        "role": "student",
        "credits": 1000
    },
    {
        "username": "user12",
        "password": "user123",
        "email": "user12@aisoulmate.com",
        "role": "student",
        "credits": 1000
    },
    {
        "username": "user13",
        "password": "user123",
        "email": "user13@aisoulmate.com",
        "role": "student",
        "credits": 1000
    },
    {
        "username": "user14",
        "password": "user123",
        "email": "user14@aisoulmate.com",
        "role": "student",
        "credits": 1000
    },
    {
        "username": "user15",
        "password": "user123",
        "email": "user15@aisoulmate.com",
        "role": "student",
        "credits": 1000
    },
    {
        "username": "user16",
        "password": "user123",
        "email": "user16@aisoulmate.com",
        "role": "student",
        "credits": 1000
    },
    {
        "username": "user17",
        "password": "user123",
        "email": "user17@aisoulmate.com",
        "role": "student",
        "credits": 1000
    },
    {
        "username": "user18",
        "password": "user123",
        "email": "user18@aisoulmate.com",
        "role": "student",
        "credits": 1000
    },
    {
        "username": "user19",
        "password": "user123",
        "email": "user19@aisoulmate.com",
        "role": "student",
        "credits": 1000
    },
    {
        "username": "user20",
        "password": "user123",
        "email": "user20@aisoulmate.com",
        "role": "student",
        "credits": 1000
    },
]


async def create_preset_users():
    """创建预设用户账号"""
    db = DatabaseManager()
    
    try:
        await db.connect()
        print("✅ 数据库连接成功")
        
        created_count = 0
        skipped_count = 0
        
        for user_data in PRESET_USERS:
            # 检查用户是否已存在
            existing = await db.fetchrow(
                "SELECT id FROM users WHERE username = $1",
                user_data["username"]
            )
            
            if existing:
                print(f"⏭️  用户 {user_data['username']} 已存在，跳过")
                skipped_count += 1
                continue
            
            # 加密密码
            password_hash = hash_password(user_data["password"])
            
            # 插入用户
            await db.execute(
                """
                INSERT INTO users (username, email, password_hash, role, credits)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_data["username"],
                user_data["email"],
                password_hash,
                user_data["role"],
                user_data["credits"]
            )
            
            print(f"✅ 创建用户: {user_data['username']} ({user_data['role']})")
            created_count += 1
        
        print(f"\n📊 统计:")
        print(f"   创建: {created_count} 个账号")
        print(f"   跳过: {skipped_count} 个账号")
        print(f"   总计: {len(PRESET_USERS)} 个账号")
        
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        raise
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(create_preset_users())
