"""
评论相关的数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional


class CommentCreate(BaseModel):
    """发表评论请求"""
    content: Optional[str] = None
    parent_id: Optional[str] = None  # 楼中楼回复
    images: list[str] = Field(default_factory=list)  # 图片 URL 列表
    videos: list[str] = Field(default_factory=list)  # 视频 URL 列表


class CommunityPostCreate(BaseModel):
    """发布社区帖子请求"""
    content: Optional[str] = None
    images: list[str] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)
    videos: list[str] = Field(default_factory=list)
