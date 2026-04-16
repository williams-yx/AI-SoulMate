"""
工作流相关的数据模型
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class Workflow(BaseModel):
    """工作流模型"""
    id: Optional[str] = None
    creator_id: str
    graph_data: Dict[str, Any]  # {nodes: [], edges: []}
    is_published: bool = False
    created_at: Optional[datetime] = None


# 导出
__all__ = ["Workflow"]
