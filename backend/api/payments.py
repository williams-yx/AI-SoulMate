"""
支付相关的 API 路由
"""
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request, status
from pydantic import BaseModel

from api.dependencies import get_current_user
from services.payment_gateway import PaymentService
from logger import logger
import os


router = APIRouter(prefix="/api/payments", tags=["支付"])


async def get_farm_payment_config(db, order_id: str) -> Dict[str, Any]:
    """
    获取订单对应农场的支付配置
    
    Args:
        db: 数据库连接
        order_id: 订单ID
    
    Returns:
        支付配置字典，如果不是打印订单或农场没有配置则返回None
    """
    # 1. 检查是否是打印订单
    print_order = await db.fetchrow(
        "SELECT id FROM print_orders WHERE order_id = $1",
        order_id
    )
    
    if not print_order:
        return None
    
    # 2. 查找订单分配的农场
    assignment = await db.fetchrow(
        """
        SELECT oa.farm_id, fs.api_endpoint
        FROM order_assignments oa
        JOIN farm_status fs ON oa.farm_id = fs.farm_id
        WHERE oa.order_id = $1
        """,
        order_id
    )
    
    if not assignment or not assignment["api_endpoint"]:
        return None
    
    # 3. 调用农场API获取支付配置
    try:
        import httpx
        farm_api_url = assignment["api_endpoint"].rstrip("/") + "/api/payment/config"
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(farm_api_url)
            
            if response.status_code == 200:
                payment_config = response.json()
                logger.info(f"从农场获取支付配置成功: farm_id={assignment['farm_id']}")
                return payment_config
            else:
                logger.warning(f"从农场获取支付配置失败: HTTP {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"调用农场API获取支付配置失败: {str(e)}")
        return None


async def auto_dispatch_print_order(db, order_id: str):
    """
    自动调度打印订单到农场
    
    当前策略：分配给第一个在线的农场（单农场模式）
    未来扩展：可以替换为智能调度算法
    """
    # 1. 检查是否是打印订单
    print_order = await db.fetchrow(
        "SELECT id, print_job_id FROM print_orders WHERE order_id = $1",
        order_id
    )
    
    if not print_order:
        logger.info(f"订单 {order_id} 不是打印订单，跳过调度")
        return
    
    # 2. 查找第一个在线的农场
    farm = await db.fetchrow(
        """
        SELECT farm_id, farm_name, api_endpoint
        FROM farm_status
        WHERE status = 'online' AND enabled = true
        ORDER BY last_heartbeat DESC
        LIMIT 1
        """
    )
    
    if not farm:
        logger.warning(f"没有在线农场，订单 {order_id} 等待调度")
        return
    
    # 3. 创建订单分配记录
    await db.execute(
        """
        INSERT INTO order_assignments (order_id, farm_id, status, assigned_at)
        VALUES ($1, $2, 'assigned', CURRENT_TIMESTAMP)
        ON CONFLICT (order_id) DO NOTHING
        """,
        order_id,
        farm["farm_id"]
    )
    
    await db.execute(
        """
        UPDATE print_jobs
        SET status = 'pending',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $1
        """,
        str(print_order["print_job_id"]),
    )

    logger.info(f"订单 {order_id} 已自动分配给农场 {farm['farm_name']}，状态更新为待打印")


# 初始化支付服务
payment_service = PaymentService(
    stripe_api_key=os.getenv("STRIPE_SECRET_KEY"),
    paypal_client_id=os.getenv("PAYPAL_CLIENT_ID"),
    paypal_client_secret=os.getenv("PAYPAL_CLIENT_SECRET"),
    paypal_mode=os.getenv("PAYPAL_MODE", "sandbox"),
    alipay_app_id=os.getenv("ALIPAY_APP_ID"),
    alipay_app_private_key=os.getenv("ALIPAY_PRIVATE_KEY"),
    alipay_public_key=os.getenv("ALIPAY_PUBLIC_KEY"),
    alipay_is_sandbox=os.getenv("ALIPAY_SANDBOX", "true").lower() == "true",
    alipay_return_url=os.getenv("ALIPAY_RETURN_URL"),
    alipay_notify_url=os.getenv("ALIPAY_NOTIFY_URL")
)


class CreatePaymentRequest(BaseModel):
    """创建支付请求"""
    order_id: str
    payment_method: str  # stripe 或 paypal
    amount: float
    currency: str = "usd"
    return_url: str = None  # 前端传递的回调URL（可选）


class ConfirmPaymentRequest(BaseModel):
    """确认支付请求"""
    order_id: str
    payment_method: str
    payment_id: str  # Stripe的payment_intent_id 或 PayPal的order_id


@router.post("/create")
async def create_payment(
    req: CreatePaymentRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    创建支付
    
    - Stripe: 返回 client_secret 用于前端确认支付
    - PayPal: 返回 approval_url 用于跳转到PayPal
    """
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="数据库未连接"
        )
    
    db = app_state.db
    
    try:
        # 验证订单归属
        order = await db.fetchrow(
            "SELECT id, total_amount, status FROM orders WHERE id = $1 AND user_id = $2",
            req.order_id,
            current_user["id"]
        )
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="订单不存在"
            )
        
        if order["status"] != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"订单状态不允许支付: {order['status']}"
            )
        
        # 验证金额
        # 如果使用USD，需要考虑汇率转换（1 CNY ≈ 0.14 USD）
        order_amount = float(order["total_amount"])
        payment_amount = req.amount
        
        if req.currency.upper() == "USD":
            # USD支付：将订单金额（CNY）转换为USD进行比较
            expected_usd = order_amount * 0.14
            # 允许最低金额调整（Stripe最低$0.50）
            expected_usd = max(expected_usd, 0.50)
            # 允许5%的误差
            if abs(expected_usd - payment_amount) > expected_usd * 0.05:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"支付金额与订单金额不符: 订单¥{order_amount}, 预期${expected_usd:.2f}, 实际${payment_amount}"
                )
        elif req.currency.upper() == "CNY":
            # CNY支付：直接比较
            if abs(order_amount - payment_amount) > 0.01:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"支付金额与订单金额不符: 订单¥{order_amount}, 支付¥{payment_amount}"
                )
        else:
            # 其他货币：直接比较
            if abs(order_amount - payment_amount) > 0.01:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"支付金额与订单金额不符: 订单{order_amount}, 支付{payment_amount}"
                )
        
        # 创建支付
        # 构建回调URL - 优先使用前端传递的URL，否则从请求头获取
        if req.return_url:
            # 前端传递了完整的回调URL
            base_url = req.return_url.rstrip('/')
            success_url = f"{base_url}/orders/{req.order_id}?payment=success"
            cancel_url = f"{base_url}/orders/{req.order_id}?payment=cancel"
        else:
            # 从请求头获取前端地址
            origin = request.headers.get("origin") or request.headers.get("referer", "http://localhost:8080")
            if origin.endswith('/'):
                origin = origin.rstrip('/')
            success_url = f"{origin}/orders/{req.order_id}?payment=success"
            cancel_url = f"{origin}/orders/{req.order_id}?payment=cancel"
        
        logger.info(f"支付回调URL: success={success_url}, cancel={cancel_url}")
        
        # 检查是否是打印订单，如果是则使用农场的支付配置
        farm_payment_config = await get_farm_payment_config(db, req.order_id)
        
        # 如果有农场支付配置且使用支付宝，使用农场的配置创建支付
        if farm_payment_config and req.payment_method == "alipay":
            alipay_config = farm_payment_config.get("alipay", {})
            if alipay_config.get("app_id"):
                logger.info(f"使用农场支付配置创建支付: 订单={req.order_id}, app_id={alipay_config.get('app_id')}")
                
                # 使用农场的支付宝配置创建临时支付服务
                from services.payment_gateway import PaymentService
                farm_payment_service = PaymentService(
                    alipay_app_id=alipay_config.get("app_id"),
                    alipay_app_private_key=alipay_config.get("app_private_key"),
                    alipay_public_key=alipay_config.get("gateway_public_key"),
                    alipay_is_sandbox=alipay_config.get("is_sandbox", True),
                    alipay_return_url=alipay_config.get("return_url"),
                    alipay_notify_url=alipay_config.get("notify_url")
                )
                
                # 使用农场的支付服务创建支付
                payment_data = await farm_payment_service.create_payment(
                    method=req.payment_method,
                    amount=req.amount,
                    currency=req.currency,
                    metadata={
                        "order_id": req.order_id,
                        "user_id": current_user["id"]
                    },
                    success_url=success_url,
                    cancel_url=cancel_url
                )
                
                # 记录支付信息到订单
                payment_id = payment_data.get('session_id') or payment_data.get('payment_intent_id') or payment_data.get('order_id')
                await db.execute(
                    """
                    UPDATE orders 
                    SET payment_method = $1, 
                        payment_id = $2,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = $3
                    """,
                    req.payment_method,
                    payment_id,
                    req.order_id
                )
                
                logger.info(
                    f"用户 {current_user['id']} 使用农场支付配置创建支付: "
                    f"订单={req.order_id}, 方式={req.payment_method}, 金额={req.amount}"
                )
                
                return {
                    "message": "支付创建成功",
                    "payment_method": req.payment_method,
                    **payment_data
                }
        
        # 使用默认支付配置创建支付
        payment_data = await payment_service.create_payment(
            method=req.payment_method,
            amount=req.amount,
            currency=req.currency,
            metadata={
                "order_id": req.order_id,
                "user_id": current_user["id"]
            },
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        # 记录支付信息到订单
        payment_id = payment_data.get('session_id') or payment_data.get('payment_intent_id') or payment_data.get('order_id')
        await db.execute(
            """
            UPDATE orders 
            SET payment_method = $1, 
                payment_id = $2,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $3
            """,
            req.payment_method,
            payment_id,
            req.order_id
        )
        
        logger.info(
            f"用户 {current_user['id']} 创建支付: "
            f"订单={req.order_id}, 方式={req.payment_method}, 金额={req.amount}"
        )
        
        return {
            "message": "支付创建成功",
            "payment_method": req.payment_method,
            **payment_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建支付失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建支付失败: {str(e)}"
        )


@router.post("/confirm")
async def confirm_payment(
    req: ConfirmPaymentRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    确认支付完成
    
    前端在用户完成支付后调用此接口
    """
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="数据库未连接"
        )
    
    db = app_state.db
    
    try:
        # 验证订单归属
        order = await db.fetchrow(
            "SELECT id, status FROM orders WHERE id = $1 AND user_id = $2",
            req.order_id,
            current_user["id"]
        )
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="订单不存在"
            )
        
        # 确认支付状态
        is_paid = await payment_service.confirm_payment(
            method=req.payment_method,
            payment_id=req.payment_id
        )
        
        if not is_paid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="支付未完成"
            )
        
        # 更新订单状态
        await db.execute(
            """
            UPDATE orders 
            SET status = 'paid', updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            """,
            req.order_id
        )
        await db.execute(
            """
            UPDATE print_jobs
            SET status = 'pending',
                updated_at = CURRENT_TIMESTAMP
            WHERE id IN (
                SELECT print_job_id
                FROM print_orders
                WHERE order_id = $1
            )
              AND slice_status = 'ready'
            """,
            req.order_id,
        )
        
        logger.info(
            f"用户 {current_user['id']} 支付成功: "
            f"订单={req.order_id}, 方式={req.payment_method}"
        )
        
        # 自动调度打印订单到农场
        try:
            await auto_dispatch_print_order(db, req.order_id)
        except Exception as e:
            logger.error(f"订单自动调度失败: {str(e)}")
            # 调度失败不影响支付成功，订单会进入待调度队列
        
        return {
            "message": "支付成功",
            "order_id": req.order_id,
            "status": "paid"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"确认支付失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"确认支付失败: {str(e)}"
        )


@router.get("/methods")
async def get_payment_methods(
    request: Request,
    order_id: str = None
):
    """
    获取可用的支付方式
    
    如果提供了 order_id 且是打印订单，则返回农场配置的支付方式
    否则返回主系统默认支付方式
    """
    app_state = request.app.state
    
    # 如果提供了订单ID，检查是否是打印订单并获取农场支付配置
    if order_id and hasattr(app_state, "db_connected") and app_state.db_connected:
        db = app_state.db
        try:
            farm_payment_config = await get_farm_payment_config(db, order_id)
            
            if farm_payment_config:
                # 返回农场配置的支付方式
                methods = []
                
                # 检查农场是否配置了支付宝
                if "alipay" in farm_payment_config:
                    alipay_config = farm_payment_config["alipay"]
                    if alipay_config.get("app_id"):
                        methods.append({
                            "id": "alipay",
                            "name": "支付宝",
                            "description": "使用支付宝扫码支付（农场收款）",
                            "icon": "smartphone",
                            "test_mode": alipay_config.get("is_sandbox", True),
                            "source": "farm"
                        })
                
                # 检查农场是否配置了微信支付
                if "wechat" in farm_payment_config:
                    wechat_config = farm_payment_config["wechat"]
                    if wechat_config.get("app_id"):
                        methods.append({
                            "id": "wechat",
                            "name": "微信支付",
                            "description": "使用微信扫码支付（农场收款）",
                            "icon": "smartphone",
                            "test_mode": False,
                            "source": "farm"
                        })
                
                if methods:
                    logger.info(f"订单 {order_id} 使用农场支付配置，支持 {len(methods)} 种支付方式")
                    return {
                        "methods": methods,
                        "default_currency": "cny",
                        "source": "farm"
                    }
        except Exception as e:
            logger.error(f"获取农场支付配置失败: {str(e)}")
    
    # 返回主系统默认支付方式
    methods = []
    
    # 暂时注释掉 Stripe 和 PayPal，只保留支付宝
    # if payment_service.stripe:
    #     methods.append({
    #         "id": "stripe",
    #         "name": "信用卡/借记卡",
    #         "description": "支持 Visa、Mastercard、American Express 等",
    #         "icon": "credit-card",
    #         "test_mode": payment_service.stripe.is_test_mode(),
    #         "source": "platform"
    #     })
    
    # if payment_service.paypal:
    #     methods.append({
    #         "id": "paypal",
    #         "name": "PayPal",
    #         "description": "使用 PayPal 账户支付",
    #         "icon": "wallet",
    #         "test_mode": payment_service.paypal.is_test_mode(),
    #         "source": "platform"
    #     })
    
    if payment_service.alipay:
        methods.append({
            "id": "alipay",
            "name": "支付宝",
            "description": "使用支付宝扫码支付",
            "icon": "smartphone",
            "test_mode": payment_service.alipay.is_test_mode(),
            "source": "platform"
        })
    
    return {
        "methods": methods,
        "default_currency": "usd",
        "source": "platform"
    }


@router.get("/config")
async def get_payment_config():
    """
    获取支付配置（前端需要的公钥等）
    """
    config = {}
    
    # Stripe 公钥
    stripe_publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY")
    if stripe_publishable_key:
        config["stripe_publishable_key"] = stripe_publishable_key
    
    # PayPal Client ID
    paypal_client_id = os.getenv("PAYPAL_CLIENT_ID")
    if paypal_client_id:
        config["paypal_client_id"] = paypal_client_id
    
    return config


@router.post("/alipay/notify")
async def alipay_notify(request: Request):
    """
    支付宝异步通知回调
    
    支付宝会在支付完成后调用此接口通知支付结果
    """
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        return {"code": "fail", "msg": "数据库未连接"}
    
    db = app_state.db
    
    try:
        # 获取POST参数
        form_data = await request.form()
        params = dict(form_data)
        
        logger.info(f"收到支付宝异步通知: {params}")
        
        # 验证签名
        if not payment_service.alipay:
            logger.error("支付宝网关未初始化")
            return {"code": "fail", "msg": "支付宝网关未初始化"}
        
        is_valid = payment_service.alipay.verify_notify(params)
        if not is_valid:
            logger.error("支付宝通知签名验证失败")
            return {"code": "fail", "msg": "签名验证失败"}
        
        # 获取订单信息
        out_trade_no = params.get("out_trade_no")  # 商户订单号
        trade_status = params.get("trade_status")  # 交易状态
        trade_no = params.get("trade_no")  # 支付宝交易号
        
        if not out_trade_no:
            logger.error("支付宝通知缺少订单号")
            return {"code": "fail", "msg": "缺少订单号"}
        
        # 只处理支付成功的通知
        if trade_status in ["TRADE_SUCCESS", "TRADE_FINISHED"]:
            # 检查是否是充值订单（通过查询 credit_recharges 表）
            recharge = await db.fetchrow(
                "SELECT * FROM credit_recharges WHERE id = $1",
                out_trade_no
            )
            
            if recharge:
                # 处理充值订单
                if recharge["status"] != "paid":
                    # 初始化 remaining_credits
                    total_amount = int(recharge["total_amount"])
                    
                    await db.execute(
                        """
                        UPDATE credit_recharges
                        SET status = 'paid', paid_at = CURRENT_TIMESTAMP, payment_id = $1, remaining_credits = $2
                        WHERE id = $3
                        """,
                        trade_no,
                        total_amount,
                        out_trade_no
                    )
                    
                    amt = int(recharge["amount"])
                    bonus = int(recharge.get("bonus_amount") or 0)
                    
                    # 将付费积分和赠送积分都加到 paid_points（合并赠送积分）
                    await db.execute(
                        """
                        UPDATE users
                        SET paid_points = COALESCE(paid_points, 0) + $1
                        WHERE id = $2
                        """,
                        amt + bonus,
                        str(recharge["user_id"]),
                    )

                    logger.info(
                        f"充值成功: 用户 {recharge['user_id']} 实付积分 {amt}, 赠送 {bonus}, 合计到账 {amt + bonus}"
                    )
                else:
                    logger.info(f"充值订单 {out_trade_no} 已处理")
            else:
                # 处理商城订单
                result = await db.execute(
                    """
                    UPDATE orders 
                    SET status = 'paid', updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1 AND status = 'pending'
                    """,
                    out_trade_no
                )
                
                if result == "UPDATE 1":
                    await db.execute(
                        """
                        UPDATE print_jobs
                        SET status = 'pending',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id IN (
                            SELECT print_job_id
                            FROM print_orders
                            WHERE order_id = $1
                        )
                          AND slice_status = 'ready'
                        """,
                        out_trade_no,
                    )
                    logger.info(f"支付宝支付成功，订单 {out_trade_no} 已更新为已支付")
                    
                    # 自动分配打印订单到农场
                    await auto_dispatch_print_order(db, out_trade_no)
                else:
                    logger.warning(f"订单 {out_trade_no} 状态未更新（可能已经是已支付状态）")
        
        # 返回success给支付宝，表示已处理
        return "success"
    
    except Exception as e:
        logger.error(f"处理支付宝通知失败: {str(e)}")
        return {"code": "fail", "msg": str(e)}


@router.get("/alipay/return")
async def alipay_return(request: Request):
    """
    支付宝同步返回页面
    
    用户支付完成后会跳转到此页面
    """
    try:
        # 获取GET参数
        params = dict(request.query_params)
        
        logger.info(f"收到支付宝同步返回: {params}")
        
        # 验证签名
        if payment_service.alipay:
            is_valid = payment_service.alipay.verify_notify(params)
            if not is_valid:
                logger.error("支付宝返回签名验证失败")
                return {"message": "签名验证失败"}
        
        # 获取订单号
        out_trade_no = params.get("out_trade_no")
        
        # 重定向到前端订单详情页
        if out_trade_no:
            return {
                "message": "支付成功",
                "order_id": out_trade_no,
                "redirect_url": f"/orders/{out_trade_no}"
            }
        else:
            return {"message": "缺少订单号"}
    
    except Exception as e:
        logger.error(f"处理支付宝返回失败: {str(e)}")
        return {"message": f"处理失败: {str(e)}"}


__all__ = ["router"]
