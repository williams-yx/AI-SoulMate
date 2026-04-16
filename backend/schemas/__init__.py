"""
API请求/响应模型模块
包含所有API的请求和响应模型
"""

from .user import User, UserCreate, UserLogin, AdminLogin
from .project import Project
from .asset import Asset, StudioGenerate, StudioImageTo3D
from .workflow import Workflow
from .post import CommentCreate, CommunityPostCreate
from .common import (
    Course, Order, OrderCreate, Address, Device, PrintJob,
    ModelConfig, ModelConfigCreate, ModelConfigUpdate
)
from .product import (
    Category, Product, ProductCreate, ProductUpdate,
    OrderItem, PrintOrder, PrintOrderCreate,
    CartItem, CartItemAdd, CartItemUpdate
)

# 导出所有模型
__all__ = [
    "User",
    "UserCreate",
    "UserLogin",
    "AdminLogin",
    "Project",
    "Asset",
    "StudioGenerate",
    "StudioImageTo3D",
    "Workflow",
    "CommentCreate",
    "CommunityPostCreate",
    "Course",
    "Order",
    "OrderCreate",
    "Address",
    "Device",
    "PrintJob",
    "ModelConfig",
    "ModelConfigCreate",
    "ModelConfigUpdate",
    # 商品相关
    "Category",
    "Product",
    "ProductCreate",
    "ProductUpdate",
    "OrderItem",
    "PrintOrder",
    "PrintOrderCreate",
    "CartItem",
    "CartItemAdd",
    "CartItemUpdate",
]
