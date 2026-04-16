"""
加密工具模块
包含API Key加密功能
"""

import hashlib
import base64
from cryptography.fernet import Fernet
from typing import Optional
from config import Config
from logger import logger


class EncryptionManager:
    """加密管理器"""
    
    @staticmethod
    def _get_key() -> bytes:
        """
        生成或获取加密密钥
        
        Returns:
            加密密钥（bytes）
        """
        key = Config.ENCRYPTION_KEY.encode()
        # 使用 SHA256 生成 32 字节密钥，然后 base64 编码
        key_hash = hashlib.sha256(key).digest()
        return base64.urlsafe_b64encode(key_hash)
    
    @staticmethod
    def encrypt(plaintext: str) -> str:
        """
        加密 API Key
        
        Args:
            plaintext: 明文
        
        Returns:
            加密后的字符串
        """
        if not plaintext:
            return ""
        try:
            f = Fernet(EncryptionManager._get_key())
            return f.encrypt(plaintext.encode()).decode()
        except Exception as e:
            logger.error(f"加密失败: {e}")
            return plaintext  # 失败时返回原文（仅用于开发环境）
    
    @staticmethod
    def decrypt(ciphertext: str) -> str:
        """
        解密 API Key
        
        Args:
            ciphertext: 密文
        
        Returns:
            解密后的字符串
        """
        if not ciphertext:
            return ""
        try:
            f = Fernet(EncryptionManager._get_key())
            return f.decrypt(ciphertext.encode()).decode()
        except Exception as e:
            logger.error(f"解密失败: {e}")
            return ciphertext  # 失败时返回原文（仅用于开发环境）


# 导出
__all__ = ["EncryptionManager"]
