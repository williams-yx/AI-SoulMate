"""
用户认证工具模块
提供密码加密、验证等功能
"""

from passlib.context import CryptContext
from logger import logger

# 创建密码上下文（使用bcrypt算法）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    使用bcrypt加密密码
    
    Args:
        password: 明文密码
    
    Returns:
        加密后的密码哈希
    """
    try:
        hashed = pwd_context.hash(password)
        logger.debug("密码加密成功")
        return hashed
    except Exception as e:
        logger.error(f"密码加密失败: {e}")
        raise


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        plain_password: 明文密码
        hashed_password: 加密后的密码哈希
    
    Returns:
        密码是否正确
    """
    try:
        is_valid = pwd_context.verify(plain_password, hashed_password)
        if not is_valid:
            logger.debug("密码验证失败")
        return is_valid
    except Exception as e:
        logger.error(f"密码验证失败: {e}")
        return False


# 导出
__all__ = ["hash_password", "verify_password", "pwd_context"]
