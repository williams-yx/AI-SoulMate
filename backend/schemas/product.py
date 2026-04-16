"""
商品相关的数据模型
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class Category(BaseModel):
    """商品分类模型"""
    id: Optional[str] = None
    name: str
    parent_id: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None


class Product(BaseModel):
    """商品模型"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    category_id: Optional[str] = None
    price: float
    price_type: str = 'fixed'  # fixed/weight/custom
    price_unit: Optional[str] = None  # 元/件, 元/g
    stock: int = 0
    stock_type: str = 'limited'  # limited/unlimited/virtual
    images: List[str] = []
    specs: Dict[str, Any] = {}
    status: str = 'active'  # active/inactive/deleted
    sort_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # 关联数据（查询时可选返回）
    category_name: Optional[str] = None


class ProductCreate(BaseModel):
    """创建商品请求模型"""
    name: str
    description: Optional[str] = None
    category_id: Optional[str] = None
    price: float
    price_type: str = 'fixed'
    price_unit: Optional[str] = None
    stock: int = 0
    stock_type: str = 'limited'
    images: List[str] = []
    specs: Dict[str, Any] = {}
    status: str = 'active'
    sort_order: int = 0


class ProductUpdate(BaseModel):
    """更新商品请求模型"""
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    price: Optional[float] = None
    price_type: Optional[str] = None
    price_unit: Optional[str] = None
    stock: Optional[int] = None
    stock_type: Optional[str] = None
    images: Optional[List[str]] = None
    specs: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    sort_order: Optional[int] = None


class OrderItem(BaseModel):
    """订单明细模型"""
    id: Optional[str] = None
    order_id: str
    product_id: Optional[str] = None
    product_type: str = 'product'  # product/course/print/custom
    product_snapshot: Dict[str, Any]  # 商品快照
    quantity: int = 1
    unit_price: float
    total_price: float
    specs: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class PrintOrder(BaseModel):
    """打印订单模型"""
    id: Optional[str] = None
    order_id: str
    print_job_id: str
    asset_id: str
    print_specs: Optional[Dict[str, Any]] = None
    estimated_weight: Optional[float] = None
    actual_weight: Optional[float] = None
    price_per_gram: float = 2.00
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PrintOrderCreate(BaseModel):
    """创建打印订单请求模型"""
    asset_id: str
    height: str  # 5cm/10cm
    material: str = 'PLA_WHITE'
    estimated_weight: Optional[float] = None


class CartItem(BaseModel):
    """购物车项模型"""
    id: Optional[str] = None
    user_id: str
    product_id: str
    quantity: int = 1
    specs: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # 关联数据（查询时返回）
    product: Optional[Product] = None


class CartItemAdd(BaseModel):
    """添加购物车请求模型"""
    product_id: str
    quantity: int = 1
    specs: Optional[Dict[str, Any]] = None


class CartItemUpdate(BaseModel):
    """更新购物车请求模型"""
    quantity: int


# 导出
__all__ = [
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
