"""
通用数据模型
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime


class Course(BaseModel):
    """课程模型"""
    id: Optional[str] = None
    title: str
    description: str
    level: str  # L1, L2, L3
    price: float
    duration_hours: int
    content: Dict[str, Any]
    is_active: bool = True


class Order(BaseModel):
    """订单模型"""
    id: Optional[str] = None
    user_id: Optional[str] = None
    items: List[Dict[str, Any]]
    total_amount: float
    status: str = "pending"  # pending, paid, shipped, completed
    created_at: Optional[datetime] = None
    address_id: Optional[str] = None
    payment_method: Optional[str] = None
    shipping_address: Optional[Dict[str, Any]] = None


class OrderCreate(BaseModel):
    """创建订单请求模型（前端不允许传 user_id）"""
    items: List[Dict[str, Any]]
    total_amount: float
    address_id: Optional[str] = None
    payment_method: Optional[str] = None
    shipping_address: Optional[Dict[str, Any]] = None


class Address(BaseModel):
    """地址模型"""
    id: Optional[str] = None
    user_id: str
    name: str
    phone: str
    province: str
    city: str
    district: str
    address: str
    is_default: bool = False


class Device(BaseModel):
    """设备模型"""
    id: Optional[str] = None
    user_id: str
    device_id: str
    char_prompt: Optional[str] = None
    last_sync_at: Optional[datetime] = None


class PrintJob(BaseModel):
    """打印任务模型"""
    id: Optional[str] = None
    user_id: str
    asset_id: str
    status: str = "pending"  # pending/printing/completed/failed
    credits_used: int = 0
    created_at: Optional[datetime] = None


class ModelConfig(BaseModel):
    """模型配置模型"""
    model_config = ConfigDict(protected_namespaces=())
    id: Optional[str] = None
    user_id: Optional[str] = None
    name: str
    api_endpoint: str
    api_key: Optional[str] = None
    auth_type: str = "api_key"
    model_name: Optional[str] = None
    provider: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = {}
    is_active: bool = True
    is_default: bool = False


class ModelConfigCreate(BaseModel):
    """模型配置创建模型"""
    model_config = ConfigDict(protected_namespaces=())
    name: str
    api_endpoint: str
    api_key: Optional[str] = None
    auth_type: str = "api_key"
    model_name: Optional[str] = None
    provider: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = {}


class ModelConfigUpdate(BaseModel):
    """模型配置更新模型"""
    model_config = ConfigDict(protected_namespaces=())
    name: Optional[str] = None
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    auth_type: Optional[str] = None
    model_name: Optional[str] = None
    provider: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


# 导出
__all__ = [
    "Course",
    "Order",
    "OrderCreate",
    "Address",
    "Device",
    "PrintJob",
    "ModelConfig",
    "ModelConfigCreate",
    "ModelConfigUpdate",
]
