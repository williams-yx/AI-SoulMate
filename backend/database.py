"""
数据库连接管理模块
"""

import asyncpg
from typing import Optional
from logger import logger
from config import Config


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def init(self):
        """
        初始化数据库连接池
        """
        try:
            self.pool = await asyncpg.create_pool(
                Config.DATABASE_URL,
                min_size=5,
                max_size=20
            )
            logger.info("数据库连接池创建成功")
        except Exception as e:
            logger.error(f"数据库连接池创建失败: {e}")
            raise
    
    async def execute(self, query: str, *args):
        """
        执行SQL语句（INSERT/UPDATE/DELETE）
        
        Args:
            query: SQL查询语句
            *args: 查询参数
        
        Returns:
            执行结果
        """
        if not self.pool:
            raise RuntimeError("数据库连接池未初始化")
        
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args):
        """
        获取多行数据
        
        Args:
            query: SQL查询语句
            *args: 查询参数
        
        Returns:
            查询结果列表
        """
        if not self.pool:
            raise RuntimeError("数据库连接池未初始化")
        
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args):
        """
        获取单行数据
        
        Args:
            query: SQL查询语句
            *args: 查询参数
        
        Returns:
            查询结果（单行）或None
        """
        if not self.pool:
            raise RuntimeError("数据库连接池未初始化")
        
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args):
        """
        获取单行单列的值（如 COUNT(*) 或某字段）
        
        Args:
            query: SQL查询语句
            *args: 查询参数
        
        Returns:
            第一行第一列的值，无结果时返回 None
        """
        if not self.pool:
            raise RuntimeError("数据库连接池未初始化")
        
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)
    
    def transaction(self):
        """
        获取数据库事务上下文管理器
        
        Returns:
            事务上下文管理器
        """
        if not self.pool:
            raise RuntimeError("数据库连接池未初始化")
        
        return self.pool.acquire()
    
    async def close(self):
        """
        关闭数据库连接池
        """
        if self.pool:
            await self.pool.close()
            logger.info("数据库连接池已关闭")


# 导出
__all__ = ["DatabaseManager"]
