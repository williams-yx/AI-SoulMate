"""
安全相关核心功能
包含JWT Token生成和验证
"""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from config import Config
from logger import logger


class AuthManager:
    """JWT认证管理器"""
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        创建JWT访问令牌
        
        Args:
            data: 要编码的数据
            expires_delta: 过期时间增量
        
        Returns:
            JWT令牌字符串
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, Config.SECRET_KEY, algorithm=Config.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """
        验证JWT令牌
        
        Args:
            token: JWT令牌字符串
        
        Returns:
            解码后的数据，如果验证失败返回None
        """
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
            return payload
        except jwt.PyJWTError as e:
            logger.debug(f"Token验证失败: {e}")
            return None

    # 一次性 token（OTT）用于登录第二步：验证成功返回用户 JWT，验证失败返回新 OTT
    OTT_TTL_MINUTES = 10
    OTT_TYPE = "one_time"

    @classmethod
    def create_one_time_token(cls, purpose: str, sub: str, **extra) -> str:
        """创建一次性 token，purpose 如 sms_login / email_login / account_login，sub 为 phone/email/username。"""
        to_encode = {
            "type": cls.OTT_TYPE,
            "purpose": purpose,
            "sub": sub,
        }
        to_encode.update(extra)
        return cls.create_access_token(
            data=to_encode,
            expires_delta=timedelta(minutes=cls.OTT_TTL_MINUTES),
        )

    @classmethod
    def verify_one_time_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """验证一次性 token，返回 payload（含 purpose、sub）或 None。"""
        payload = cls.verify_token(token)
        if not payload or payload.get("type") != cls.OTT_TYPE:
            return None
        return payload


# 导出
__all__ = ["AuthManager"]
