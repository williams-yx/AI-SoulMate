"""
商品相关的 API 路由
"""

from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Request, Query, status

from schemas import Product, ProductCreate, ProductUpdate, Category
from api.dependencies import get_current_user, get_admin_user
from logger import logger

import json


router = APIRouter(prefix="/api/products", tags=["商品"])


@router.get("/categories")
async def get_categories(request: Request):
    """获取商品分类列表"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    categories = await db.fetch(
        """
        SELECT id, name, parent_id, description, icon, sort_order, is_active, created_at
        FROM categories
        WHERE is_active = TRUE
        ORDER BY sort_order ASC, created_at ASC
        """
    )

    return [dict(cat) for cat in categories]


@router.get("")
async def get_products(
    request: Request,
    category_id: Optional[str] = Query(None, description="分类ID筛选"),
    status_filter: Optional[str] = Query('active', description="状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """获取商品列表（支持分页和筛选）"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    # 构建查询条件
    conditions = ["p.status = $1"]
    params = [status_filter]
    param_index = 2

    if category_id:
        conditions.append(f"p.category_id = ${param_index}")
        params.append(category_id)
        param_index += 1

    where_clause = " AND ".join(conditions)
    offset = (page - 1) * page_size

    # 查询商品列表（关联分类名称）
    query = f"""
        SELECT 
            p.id, p.name, p.description, p.category_id, p.price, 
            p.price_type, p.price_unit, p.stock, p.stock_type,
            p.images, p.specs, p.status, p.sort_order,
            p.created_at, p.updated_at,
            c.name as category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE {where_clause}
        ORDER BY p.sort_order ASC, p.created_at DESC
        LIMIT ${param_index} OFFSET ${param_index + 1}
    """
    params.extend([page_size, offset])

    products = await db.fetch(query, *params)

    # 查询总数
    count_query = f"SELECT COUNT(*) as total FROM products p WHERE {where_clause}"
    total_row = await db.fetchrow(count_query, *params[:len(params) - 2])  # 不包括LIMIT和OFFSET参数
    total = total_row['total'] if total_row else 0

    # 处理返回数据
    items = []
    for product in products:
        data = dict(product)
        # 确保 images 和 specs 是 JSON 对象
        try:
            if isinstance(data.get("images"), str):
                data["images"] = json.loads(data["images"])
        except Exception:
            data["images"] = []
        try:
            if isinstance(data.get("specs"), str):
                data["specs"] = json.loads(data["specs"])
        except Exception:
            data["specs"] = {}
        items.append(data)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/{product_id}")
async def get_product_detail(product_id: str, request: Request):
    """获取商品详情"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    product = await db.fetchrow(
        """
        SELECT 
            p.id, p.name, p.description, p.category_id, p.price, 
            p.price_type, p.price_unit, p.stock, p.stock_type,
            p.images, p.specs, p.status, p.sort_order,
            p.created_at, p.updated_at,
            c.name as category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.id = $1
        """,
        product_id,
    )

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")

    data = dict(product)
    # 确保 images 和 specs 是 JSON 对象
    try:
        if isinstance(data.get("images"), str):
            data["images"] = json.loads(data["images"])
    except Exception:
        data["images"] = []
    try:
        if isinstance(data.get("specs"), str):
            data["specs"] = json.loads(data["specs"])
    except Exception:
        data["specs"] = {}

    return data


@router.post("")
async def create_product(
    product_data: ProductCreate,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_admin_user),
):
    """创建商品（管理员）"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    # 验证分类是否存在
    if product_data.category_id:
        category = await db.fetchrow(
            "SELECT id FROM categories WHERE id = $1", product_data.category_id
        )
        if not category:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="分类不存在")

    row = await db.fetchrow(
        """
        INSERT INTO products (
            name, description, category_id, price, price_type, price_unit,
            stock, stock_type, images, specs, status, sort_order
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        RETURNING id
        """,
        product_data.name,
        product_data.description,
        product_data.category_id,
        product_data.price,
        product_data.price_type,
        product_data.price_unit,
        product_data.stock,
        product_data.stock_type,
        json.dumps(product_data.images),
        json.dumps(product_data.specs),
        product_data.status,
        product_data.sort_order,
    )

    logger.info(f"管理员 {current_user['id']} 创建商品: {row['id']}")
    return {"product_id": str(row["id"]), "message": "商品创建成功"}


@router.put("/{product_id}")
async def update_product(
    product_id: str,
    product_data: ProductUpdate,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_admin_user),
):
    """更新商品（管理员）"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    # 检查商品是否存在
    existing = await db.fetchrow("SELECT id FROM products WHERE id = $1", product_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")

    # 构建更新字段
    update_fields = []
    update_values = []
    param_index = 1

    if product_data.name is not None:
        update_fields.append(f"name = ${param_index}")
        update_values.append(product_data.name)
        param_index += 1

    if product_data.description is not None:
        update_fields.append(f"description = ${param_index}")
        update_values.append(product_data.description)
        param_index += 1

    if product_data.category_id is not None:
        update_fields.append(f"category_id = ${param_index}")
        update_values.append(product_data.category_id)
        param_index += 1

    if product_data.price is not None:
        update_fields.append(f"price = ${param_index}")
        update_values.append(product_data.price)
        param_index += 1

    if product_data.price_type is not None:
        update_fields.append(f"price_type = ${param_index}")
        update_values.append(product_data.price_type)
        param_index += 1

    if product_data.price_unit is not None:
        update_fields.append(f"price_unit = ${param_index}")
        update_values.append(product_data.price_unit)
        param_index += 1

    if product_data.stock is not None:
        update_fields.append(f"stock = ${param_index}")
        update_values.append(product_data.stock)
        param_index += 1

    if product_data.stock_type is not None:
        update_fields.append(f"stock_type = ${param_index}")
        update_values.append(product_data.stock_type)
        param_index += 1

    if product_data.images is not None:
        update_fields.append(f"images = ${param_index}")
        update_values.append(json.dumps(product_data.images))
        param_index += 1

    if product_data.specs is not None:
        update_fields.append(f"specs = ${param_index}")
        update_values.append(json.dumps(product_data.specs))
        param_index += 1

    if product_data.status is not None:
        update_fields.append(f"status = ${param_index}")
        update_values.append(product_data.status)
        param_index += 1

    if product_data.sort_order is not None:
        update_fields.append(f"sort_order = ${param_index}")
        update_values.append(product_data.sort_order)
        param_index += 1

    if not update_fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有提供要更新的字段")

    # 添加 updated_at
    update_fields.append(f"updated_at = CURRENT_TIMESTAMP")

    # 添加 WHERE 条件
    update_values.append(product_id)

    query = f"""
        UPDATE products
        SET {', '.join(update_fields)}
        WHERE id = ${param_index}
    """

    await db.execute(query, *update_values)

    logger.info(f"管理员 {current_user['id']} 更新商品: {product_id}")
    return {"message": "商品更新成功"}


@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_admin_user),
):
    """删除商品（管理员）- 软删除"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    # 软删除：更新状态为 deleted
    result = await db.execute(
        "UPDATE products SET status = 'deleted', updated_at = CURRENT_TIMESTAMP WHERE id = $1",
        product_id,
    )

    if "0" in str(result):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")

    logger.info(f"管理员 {current_user['id']} 删除商品: {product_id}")
    return {"message": "商品删除成功"}


__all__ = ["router"]
