"""
项目相关的数据模型
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class Project(BaseModel):
    """项目模型"""
    model_config = ConfigDict(protected_namespaces=())
    id: Optional[str] = None
    user_id: str
    title: str
    description: str
    prompt: str
    style_model: str
    status: str = "draft"  # draft, generating, completed, failed
    model_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# 导出
__all__ = ["Project"]
