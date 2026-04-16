"""
订单相关的 API 路由
"""

from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Request, status

from schemas import OrderCreate
from api.dependencies import get_current_user
from logger import logger

import json


router = APIRouter(prefix="/api/orders", tags=["订单"])


@router.post("")
async def create_order(
    order_data: OrderCreate,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """创建订单（后端计算金额，写入order_items表）"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    # 验证手机号格式（如果提供了shipping_address）
    if order_data.shipping_address and order_data.shipping_address.get("phone"):
        phone = order_data.shipping_address.get("phone", "").strip()
        import re
        if not re.match(r'^1[3-9]\d{9}$', phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号格式不正确，请输入11位有效手机号"
            )

    # 后端计算总金额（安全校验）
    total = sum(item.get("price", 0) * item.get("quantity", 1) for item in order_data.items)

    # 如果前端传入的金额不一致，使用后端计算的金额
    if abs(total - order_data.total_amount) > 0.01:
        # 以安全为先：强制使用后端计算（前端金额仅作为展示）
        logger.warning("订单金额不一致，已使用后端计算金额")

    # 使用事务确保订单和订单明细的原子性
    async with db.transaction() as conn:
        # 1. 创建订单主记录
        order_row = await conn.fetchrow(
            """
            INSERT INTO orders (user_id, items, total_amount, address_id, payment_method, shipping_address)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            current_user["id"],
            json.dumps(order_data.items),  # 保留原有的items字段（兼容性）
            total,
            order_data.address_id,
            order_data.payment_method,
            json.dumps(order_data.shipping_address) if order_data.shipping_address else None,
        )
        
        order_id = str(order_row["id"])
        
        # 2. 写入订单明细表
        for item in order_data.items:
            product_id = item.get("id")  # 商品ID（可能是UUID或自定义ID）
            product_name = item.get("name", "Unknown Product")
            unit_price = float(item.get("price", 0))
            quantity = int(item.get("quantity", 1))
            total_price = unit_price * quantity
            
            # 构建商品快照
            product_snapshot = {
                "id": product_id,
                "name": product_name,
                "price": unit_price,
            }
            
            # 如果商品ID是UUID格式，尝试从products表获取详细信息
            product_type = "product"
            if product_id and len(str(product_id)) == 36:  # UUID格式
                try:
                    product_detail = await conn.fetchrow(
                        "SELECT name, description, price, price_type, images, specs FROM products WHERE id = $1",
                        product_id
                    )
                    if product_detail:
                        product_snapshot.update({
                            "name": product_detail["name"],
                            "description": product_detail.get("description"),
                            "price": float(product_detail["price"]),
                            "price_type": product_detail.get("price_type"),
                            "images": product_detail.get("images"),
                            "specs": product_detail.get("specs"),
                        })
                except Exception as e:
                    logger.warning(f"Failed to fetch product detail for {product_id}: {e}")
            else:
                # 非UUID格式，可能是自定义商品（如打印服务）
                product_type = "custom"
                product_id = None  # 不关联products表
            
            # 插入订单明细
            await conn.execute(
                """
                INSERT INTO order_items (
                    order_id, product_id, product_type, product_snapshot,
                    quantity, unit_price, total_price, specs
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                order_id,
                product_id,
                product_type,
                json.dumps(product_snapshot),
                quantity,
                unit_price,
                total_price,
                json.dumps(item.get("specs")) if item.get("specs") else None,
            )
        
        logger.info(f"订单创建成功: {order_id}, 用户: {current_user['id']}, 金额: {total}")

    return {"order_id": order_id, "total_amount": total}


@router.get("")
async def get_orders(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取用户订单列表（包含普通订单和充值订单）"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    # 1. 获取普通订单
    orders = await db.fetch(
        """
        SELECT id, items, total_amount, status, created_at, 'order' as order_type
        FROM orders
        WHERE user_id = $1
        ORDER BY created_at DESC
        """,
        current_user["id"],
    )

    # 2. 获取充值订单
    recharge_orders = await db.fetch(
        """
        SELECT 
            id, 
            amount, 
            bonus_amount,
            total_amount as recharge_total_amount,
            amount_yuan as total_amount,
            payment_method,
            status, 
            created_at,
            'recharge' as order_type
        FROM credit_recharges
        WHERE user_id = $1
        ORDER BY created_at DESC
        """,
        current_user["id"],
    )

    # 3. 合并两种订单，转换充值订单格式以匹配前端
    all_orders = []
    
    # 添加普通订单
    for order in orders:
        order_dict = dict(order)
        # 确保created_at是datetime对象，如果是字符串则转换
        if isinstance(order_dict['created_at'], str):
            from datetime import datetime
            order_dict['created_at'] = datetime.fromisoformat(order_dict['created_at'].replace('Z', '+00:00'))
        all_orders.append(order_dict)
    
    # 添加充值订单（转换格式）
    for recharge in recharge_orders:
        recharge_dict = dict(recharge)
        # 构造items字段，让前端能正确显示
        recharge_dict["items"] = json.dumps([{
            "id": "credit_recharge",
            "name": f"积分充值 {recharge_dict['amount']}",
            "price": float(recharge_dict['total_amount']),
            "quantity": 1,
            "bonus": recharge_dict['bonus_amount']
        }])
        # 确保created_at是datetime对象
        if isinstance(recharge_dict['created_at'], str):
            from datetime import datetime
            recharge_dict['created_at'] = datetime.fromisoformat(recharge_dict['created_at'].replace('Z', '+00:00'))
        # 移除时区信息，统一为naive datetime
        if recharge_dict['created_at'].tzinfo is not None:
            recharge_dict['created_at'] = recharge_dict['created_at'].replace(tzinfo=None)
        all_orders.append(recharge_dict)
    
    # 4. 按创建时间降序排序（现在所有时间都是naive datetime）
    all_orders.sort(key=lambda x: x['created_at'], reverse=True)

    return all_orders


@router.get("/{order_id}")
async def get_order_detail(
    order_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取订单详情（包含订单明细）"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    order = await db.fetchrow(
        "SELECT * FROM orders WHERE id = $1 AND user_id = $2",
        order_id,
        current_user["id"],
    )

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # 获取订单明细
    order_items = await db.fetch(
        """
        SELECT 
            id, product_id, product_type, product_snapshot,
            quantity, unit_price, total_price, specs, created_at
        FROM order_items
        WHERE order_id = $1
        ORDER BY created_at ASC
        """,
        order_id,
    )

    order_dict = dict(order)
    order_dict["order_items"] = [dict(item) for item in order_items]

    return order_dict


@router.get("/{order_id}/items")
async def get_order_items(
    order_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取订单明细列表"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    # 验证订单归属
    order = await db.fetchrow(
        "SELECT id FROM orders WHERE id = $1 AND user_id = $2",
        order_id,
        current_user["id"],
    )

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # 获取订单明细
    order_items = await db.fetch(
        """
        SELECT 
            id, product_id, product_type, product_snapshot,
            quantity, unit_price, total_price, specs, created_at
        FROM order_items
        WHERE order_id = $1
        ORDER BY created_at ASC
        """,
        order_id,
    )

    return [dict(item) for item in order_items]


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """取消订单（恢复库存）"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    order = await db.fetchrow(
        "SELECT * FROM orders WHERE id = $1 AND user_id = $2",
        order_id,
        current_user["id"],
    )

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order["status"] not in ["pricing", "pricing_failed", "pending", "paid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Order cannot be cancelled"
        )

    # 使用事务确保订单取消和库存恢复的原子性
    async with db.transaction() as conn:
        # 1. 更新订单状态
        await conn.execute(
            "UPDATE orders SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = $1",
            order_id,
        )
        
        # 2. 恢复库存（仅针对有限库存的商品）
        order_items = await conn.fetch(
            "SELECT product_id, quantity FROM order_items WHERE order_id = $1 AND product_id IS NOT NULL",
            order_id,
        )
        
        for item in order_items:
            product_id = item["product_id"]
            quantity = item["quantity"]
            
            # 检查商品是否存在且为有限库存
            product = await conn.fetchrow(
                "SELECT stock_type FROM products WHERE id = $1",
                product_id,
            )
            
            if product and product["stock_type"] == "limited":
                # 恢复库存
                await conn.execute(
                    "UPDATE products SET stock = stock + $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                    quantity,
                    product_id,
                )
                logger.info(f"恢复商品库存: {product_id}, 数量: {quantity}")
        
        logger.info(f"订单取消成功: {order_id}, 用户: {current_user['id']}")

    return {"message": "Order cancelled successfully"}


@router.post("/{order_id}/confirm-receipt")
async def confirm_receipt(
    order_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """用户确认收货"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    order = await db.fetchrow(
        "SELECT * FROM orders WHERE id = $1 AND user_id = $2",
        order_id,
        current_user["id"],
    )

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order["status"] != "shipped":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Order is not in shipped status"
        )

    # 更新订单状态为 completed
    async with db.transaction() as conn:
        await conn.execute(
            "UPDATE orders SET status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE id = $1",
            order_id,
        )
        await conn.execute(
            """
            UPDATE print_jobs
            SET status = 'received',
                completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id IN (
                SELECT print_job_id
                FROM print_orders
                WHERE order_id = $1
            )
            """,
            order_id,
        )
        await conn.execute(
            """
            UPDATE print_orders
            SET received_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE order_id = $1
            """,
            order_id,
        )
    
    logger.info(f"用户确认收货: {order_id}, 用户: {current_user['id']}")

    return {"message": "Receipt confirmed successfully"}


__all__ = ["router"]
