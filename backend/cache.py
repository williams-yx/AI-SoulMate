"""
Redis缓存模块
提供统一的缓存功能，包括验证码存储、Session存储、数据缓存等
"""

import redis
import json
import os
from typing import Optional, Any, Dict
from datetime import timedelta
from logger import logger


class CacheManager:
    """Redis缓存管理器"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._connected = False
    
    def connect(self, redis_url: Optional[str] = None) -> bool:
        """
        连接Redis服务器
        
        Args:
            redis_url: Redis连接URL，如果为None则从环境变量读取
        
        Returns:
            连接是否成功
        """
        try:
            if redis_url is None:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            
            # 解析Redis URL
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,  # 自动解码为字符串
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # 测试连接
            self.redis_client.ping()
            self._connected = True
            logger.info("✅ Redis缓存连接成功")
            return True
            
        except Exception as e:
            logger.error(f"⚠️  Redis缓存连接失败: {e}")
            self._connected = False
            self.redis_client = None
            return False
    
    def is_connected(self) -> bool:
        """检查Redis是否已连接"""
        if not self._connected or self.redis_client is None:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            self._connected = False
            return False
    
    def disconnect(self):
        """断开Redis连接"""
        if self.redis_client:
            try:
                self.redis_client.close()
                logger.info("Redis连接已关闭")
            except Exception as e:
                logger.error(f"关闭Redis连接失败: {e}")
            finally:
                self.redis_client = None
                self._connected = False
    
    # ========== 基础缓存操作 ==========
    
    def get(self, key: str) -> Optional[str]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
        
        Returns:
            缓存值，如果不存在返回None
        """
        if not self.is_connected():
            return None
        try:
            return self.redis_client.get(key)
        except Exception as e:
            logger.error(f"获取缓存失败 {key}: {e}")
            return None
    
    def set(self, key: str, value: str, expire_seconds: Optional[int] = None) -> bool:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            expire_seconds: 过期时间（秒），None表示永不过期
        
        Returns:
            是否设置成功
        """
        if not self.is_connected():
            return False
        try:
            if expire_seconds:
                self.redis_client.setex(key, expire_seconds, value)
            else:
                self.redis_client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"设置缓存失败 {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
        
        Returns:
            是否删除成功
        """
        if not self.is_connected():
            return False
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"删除缓存失败 {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        检查缓存是否存在
        
        Args:
            key: 缓存键
        
        Returns:
            是否存在
        """
        if not self.is_connected():
            return False
        try:
            return self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"检查缓存失败 {key}: {e}")
            return False
    
    def expire(self, key: str, seconds: int) -> bool:
        """
        设置缓存过期时间
        
        Args:
            key: 缓存键
            seconds: 过期时间（秒）
        
        Returns:
            是否设置成功
        """
        if not self.is_connected():
            return False
        try:
            return self.redis_client.expire(key, seconds)
        except Exception as e:
            logger.error(f"设置过期时间失败 {key}: {e}")
            return False
    
    # ========== JSON数据缓存 ==========
    
    def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        获取JSON格式的缓存数据
        
        Args:
            key: 缓存键
        
        Returns:
            JSON数据，如果不存在返回None
        """
        value = self.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败 {key}: {e}")
            return None
    
    def set_json(self, key: str, value: Dict[str, Any], expire_seconds: Optional[int] = None) -> bool:
        """
        设置JSON格式的缓存数据
        
        Args:
            key: 缓存键
            value: JSON数据
            expire_seconds: 过期时间（秒）
        
        Returns:
            是否设置成功
        """
        try:
            json_str = json.dumps(value, ensure_ascii=False)
            return self.set(key, json_str, expire_seconds)
        except Exception as e:
            logger.error(f"JSON序列化失败 {key}: {e}")
            return False
    
    # ========== 验证码存储 ==========
    
    def set_verification_code(self, phone: str, code: str, expire_seconds: int = 300) -> bool:
        """
        存储验证码
        
        Args:
            phone: 手机号
            code: 验证码
            expire_seconds: 过期时间（秒），默认5分钟
        
        Returns:
            是否存储成功
        """
        key = f"verification_code:{phone}"
        data = {
            "code": code,
            "created_at": str(os.times()[4])  # 使用进程时间作为时间戳
        }
        return self.set_json(key, data, expire_seconds)
    
    def get_verification_code(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        获取验证码
        
        Args:
            phone: 手机号
        
        Returns:
            验证码信息，如果不存在返回None
        """
        key = f"verification_code:{phone}"
        return self.get_json(key)
    
    def delete_verification_code(self, phone: str) -> bool:
        """
        删除验证码
        
        Args:
            phone: 手机号
        
        Returns:
            是否删除成功
        """
        key = f"verification_code:{phone}"
        return self.delete(key)
    
    # ========== Session存储 ==========
    
    def set_session(self, session_id: str, user_data: Dict[str, Any], expire_seconds: int = 3600) -> bool:
        """
        存储Session数据
        
        Args:
            session_id: Session ID
            user_data: 用户数据
            expire_seconds: 过期时间（秒），默认1小时
        
        Returns:
            是否存储成功
        """
        key = f"session:{session_id}"
        return self.set_json(key, user_data, expire_seconds)
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取Session数据
        
        Args:
            session_id: Session ID
        
        Returns:
            Session数据，如果不存在返回None
        """
        key = f"session:{session_id}"
        return self.get_json(key)
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除Session数据
        
        Args:
            session_id: Session ID
        
        Returns:
            是否删除成功
        """
        key = f"session:{session_id}"
        return self.delete(key)
    
    # ========== 数据缓存 ==========
    
    def cache_user_data(self, user_id: str, user_data: Dict[str, Any], expire_seconds: int = 3600) -> bool:
        """
        缓存用户数据
        
        Args:
            user_id: 用户ID
            user_data: 用户数据
            expire_seconds: 过期时间（秒），默认1小时
        
        Returns:
            是否缓存成功
        """
        key = f"user:{user_id}"
        return self.set_json(key, user_data, expire_seconds)
    
    def get_cached_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存的用户数据
        
        Args:
            user_id: 用户ID
        
        Returns:
            用户数据，如果不存在返回None
        """
        key = f"user:{user_id}"
        return self.get_json(key)
    
    def delete_cached_user_data(self, user_id: str) -> bool:
        """
        删除缓存的用户数据
        
        Args:
            user_id: 用户ID
        
        Returns:
            是否删除成功
        """
        key = f"user:{user_id}"
        return self.delete(key)


# 全局缓存管理器实例
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """
    获取缓存管理器实例（单例模式）
    
    Returns:
        缓存管理器实例
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


# 导出
__all__ = ["CacheManager", "get_cache_manager"]
