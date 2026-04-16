"""
对象存储模块
提供文件上传、存储、访问URL生成等功能
支持本地文件系统和对象存储（OSS/S3，可选）
"""

import os
import aiofiles
from pathlib import Path
from typing import Optional, BinaryIO
from datetime import datetime
import uuid
from logger import logger


class StorageManager:
    """存储管理器"""
    
    def __init__(self, base_dir: str = "./uploads"):
        """
        初始化存储管理器
        
        Args:
            base_dir: 基础存储目录
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"存储管理器初始化: {self.base_dir.absolute()}")
    
    def get_upload_dir(self) -> Path:
        """
        获取上传目录路径
        
        Returns:
            上传目录Path对象
        """
        return self.base_dir
    
    def create_subdir(self, subdir: str) -> Path:
        """
        创建子目录
        
        Args:
            subdir: 子目录名称（如: images, models, avatars等）
        
        Returns:
            子目录Path对象
        """
        subdir_path = self.base_dir / subdir
        subdir_path.mkdir(parents=True, exist_ok=True)
        return subdir_path
    
    def generate_filename(self, original_filename: str, prefix: Optional[str] = None) -> str:
        """
        生成唯一文件名
        
        Args:
            original_filename: 原始文件名
            prefix: 文件名前缀（可选）
        
        Returns:
            唯一文件名
        """
        # 获取文件扩展名
        ext = Path(original_filename).suffix
        
        # 生成唯一文件名
        unique_id = str(uuid.uuid4())
        if prefix:
            filename = f"{prefix}_{unique_id}{ext}"
        else:
            # 使用日期作为前缀
            date_prefix = datetime.now().strftime("%Y%m%d")
            filename = f"{date_prefix}_{unique_id}{ext}"
        
        return filename
    
    def get_file_path(self, filename: str, subdir: Optional[str] = None) -> Path:
        """
        获取文件完整路径
        
        Args:
            filename: 文件名
            subdir: 子目录（可选）
        
        Returns:
            文件完整路径
        """
        if subdir:
            return self.base_dir / subdir / filename
        return self.base_dir / filename
    
    def get_file_url(self, filename: str, subdir: Optional[str] = None) -> str:
        """
        生成文件访问URL
        
        Args:
            filename: 文件名
            subdir: 子目录（可选）
        
        Returns:
            文件访问URL
        """
        if subdir:
            return f"/uploads/{subdir}/{filename}"
        return f"/uploads/{filename}"
    
    async def save_file(
        self,
        file_data: bytes,
        filename: str,
        subdir: Optional[str] = None
    ) -> tuple[Path, str]:
        """
        保存文件
        
        Args:
            file_data: 文件数据（字节）
            filename: 文件名
            subdir: 子目录（可选）
        
        Returns:
            (文件路径, 访问URL) 元组
        """
        try:
            # 创建子目录（如果需要）
            if subdir:
                file_dir = self.create_subdir(subdir)
            else:
                file_dir = self.base_dir
            
            # 构建文件路径
            file_path = file_dir / filename
            
            # 保存文件
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_data)
            
            # 生成访问URL
            file_url = self.get_file_url(filename, subdir)
            
            logger.info(f"文件保存成功: {file_path.relative_to(self.base_dir)}")
            return file_path, file_url
            
        except Exception as e:
            logger.error(f"文件保存失败 {filename}: {e}")
            raise
    
    async def read_file(self, filename: str, subdir: Optional[str] = None) -> bytes:
        """
        读取文件
        
        Args:
            filename: 文件名
            subdir: 子目录（可选）
        
        Returns:
            文件数据（字节）
        """
        try:
            file_path = self.get_file_path(filename, subdir)
            
            if not file_path.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            async with aiofiles.open(file_path, 'rb') as f:
                data = await f.read()
            
            return data
            
        except Exception as e:
            logger.error(f"文件读取失败 {filename}: {e}")
            raise
    
    async def delete_file(self, filename: str, subdir: Optional[str] = None) -> bool:
        """
        删除文件
        
        Args:
            filename: 文件名
            subdir: 子目录（可选）
        
        Returns:
            是否删除成功
        """
        try:
            file_path = self.get_file_path(filename, subdir)
            
            if not file_path.exists():
                logger.warning(f"文件不存在，无需删除: {file_path}")
                return False
            
            file_path.unlink()
            logger.info(f"文件删除成功: {file_path.relative_to(self.base_dir)}")
            return True
            
        except Exception as e:
            logger.error(f"文件删除失败 {filename}: {e}")
            return False
    
    def file_exists(self, filename: str, subdir: Optional[str] = None) -> bool:
        """
        检查文件是否存在
        
        Args:
            filename: 文件名
            subdir: 子目录（可选）
        
        Returns:
            文件是否存在
        """
        file_path = self.get_file_path(filename, subdir)
        return file_path.exists()
    
    def get_file_size(self, filename: str, subdir: Optional[str] = None) -> Optional[int]:
        """
        获取文件大小
        
        Args:
            filename: 文件名
            subdir: 子目录（可选）
        
        Returns:
            文件大小（字节），如果文件不存在返回None
        """
        file_path = self.get_file_path(filename, subdir)
        if file_path.exists():
            return file_path.stat().st_size
        return None
    
    async def save_upload_file(
        self,
        file_content: bytes,
        original_filename: str,
        subdir: Optional[str] = None,
        prefix: Optional[str] = None
    ) -> tuple[str, str]:
        """
        保存上传的文件（自动生成唯一文件名）
        
        Args:
            file_content: 文件内容（字节）
            original_filename: 原始文件名
            subdir: 子目录（可选）
            prefix: 文件名前缀（可选）
        
        Returns:
            (文件名, 访问URL) 元组
        """
        # 生成唯一文件名
        filename = self.generate_filename(original_filename, prefix)
        
        # 保存文件
        file_path, file_url = await self.save_file(file_content, filename, subdir)
        
        return filename, file_url


# 全局存储管理器实例
_storage_manager: Optional[StorageManager] = None


def get_storage_manager(base_dir: Optional[str] = None) -> StorageManager:
    """
    获取存储管理器实例（单例模式）
    
    Args:
        base_dir: 基础存储目录，如果为None则使用默认值或环境变量
    
    Returns:
        存储管理器实例
    """
    global _storage_manager
    if _storage_manager is None:
        if base_dir is None:
            base_dir = os.getenv("UPLOAD_DIR", "./uploads")
        _storage_manager = StorageManager(base_dir)
    return _storage_manager


# 导出
__all__ = ["StorageManager", "get_storage_manager"]
