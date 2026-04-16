"""
积分充值相关接口
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime, timezone
import hashlib
import re

from api.dependencies import get_current_user
from config import Config
from logger import logger

router = APIRouter(prefix="/api/credits", tags=["credits"])

_CDK_WHITESPACE_RE = re.compile(r"\s+")
_CDK_INVALID_CHAR_RE = re.compile(r"[^A-Za-z0-9-]")


class RechargeTier(BaseModel):
    id: int
    min_amount: int
    bonus_rate: float
    bonus_fixed: int
    description: str
    sort_order: int
    amount_yuan: float  # 对应的人民币金额


class RechargeRequest(BaseModel):
    amount: int  # 充值积分数量
    payment_method: str  # 支付方式：alipay, stripe
    return_url: Optional[str] = None  # 前端传递的回调URL（可选）


class RechargeResponse(BaseModel):
    recharge_id: str
    amount: int
    bonus_amount: int
    total_amount: int
    payment_method: str
    payment_url: Optional[str] = None
    message: Optional[str] = None


class CdkRedeemRequest(BaseModel):
    code: str


class CdkRedeemResponse(BaseModel):
    points_awarded: int
    points: Optional[int] = None
    free_credits: int
    redeemed_credits: int
    paid_credits: int
    credits: int
    message: str


def _normalize_cdk_code(raw: str) -> str:
    if raw is None:
        return ""
    normalized = _CDK_WHITESPACE_RE.sub("", raw)
    normalized = _CDK_INVALID_CHAR_RE.sub("", normalized).upper().strip("-")
    compact = normalized.replace("-", "")
    if len(compact) < 8 or len(compact) > 64:
        return ""
    return normalized


def _candidate_cdk_codes(raw: str) -> list[str]:
    normalized = _normalize_cdk_code(raw)
    if not normalized:
        return []

    candidates = [normalized]
    compact = normalized.replace("-", "")
    if compact and compact != normalized:
        candidates.append(compact)
    return candidates


def _hash_cdk_code(code: str) -> str:
    payload = f"{Config.CDK_CODE_PEPPER}:{code}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def calculate_bonus(db, amount: int) -> tuple[int, int]:
    """
    计算赠送积分
    返回：(赠送积分, 总积分)
    
    赠送策略：
    - 100以下：不送
    - 100-500：不送
    - 500-1000：5%
    - 1000-5000：10%
    - 5000-10000：15%
    - 10000以上：20%
    """
    bonus_rate = 0
    
    if amount < 100:
        bonus_rate = 0
    elif amount < 500:
        bonus_rate = 0
    elif amount < 1000:
        bonus_rate = 5
    elif amount < 5000:
        bonus_rate = 10
    elif amount < 10000:
        bonus_rate = 15
    else:  # >= 10000
        bonus_rate = 20
    
    bonus_amount = int(amount * bonus_rate / 100)
    total_amount = amount + bonus_amount
    
    logger.info(f"自定义充值计算: 充值{amount}积分, 赠送比例{bonus_rate}%, 赠送{bonus_amount}积分, 总计{total_amount}积分")
    
    return bonus_amount, total_amount


@router.get("/recharge-tiers", response_model=List[RechargeTier])
async def get_recharge_tiers(request: Request):
    """获取充值档位列表"""
    app_state = request.app.state
    db = app_state.db
    
    # 积分转人民币的汇率（1积分 = 0.1元）
    CREDIT_TO_YUAN_RATE = 0.1
    
    tiers = await db.fetch(
        """
        SELECT id, min_amount, bonus_rate, bonus_fixed, description, sort_order
        FROM recharge_tiers
        WHERE is_active = TRUE
        ORDER BY sort_order ASC, min_amount ASC
        """
    )
    
    return [
        {
            "id": t["id"],
            "min_amount": t["min_amount"],
            "bonus_rate": float(t["bonus_rate"]),
            "bonus_fixed": t["bonus_fixed"],
            "description": t["description"],
            "sort_order": t["sort_order"],
            "amount_yuan": t["min_amount"] * CREDIT_TO_YUAN_RATE
        }
        for t in tiers
    ]


@router.post("/recharge", response_model=RechargeResponse)
async def create_recharge(
    request: Request,
    data: RechargeRequest,
    current_user: dict = Depends(get_current_user)
):
    """创建积分充值订单"""
    if data.amount <= 0 or data.amount > 100000:
        raise HTTPException(status_code=400, detail="充值金额必须在 1-100000 之间")
    
    if data.payment_method not in ["alipay", "stripe"]:
        raise HTTPException(status_code=400, detail="不支持的支付方式")
    
    app_state = request.app.state
    db = app_state.db
    
    # 计算赠送积分
    bonus_amount, total_amount = await calculate_bonus(db, data.amount)
    
    # 创建充值记录
    recharge_id = str(uuid.uuid4())
    user_id = str(current_user["id"])
    
    # 计算金额（1积分 = 0.1元）
    amount_yuan = data.amount * 0.1
    
    await db.execute(
        """
        INSERT INTO credit_recharges (id, user_id, amount, bonus_amount, total_amount, amount_yuan, payment_method, status, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
        recharge_id,
        user_id,
        data.amount,
        bonus_amount,
        total_amount,
        amount_yuan,
        data.payment_method,
        "pending",
        datetime.now(timezone.utc)
    )
    
    logger.info(f"用户 {user_id} 创建充值订单: {recharge_id}, 充值: {data.amount} 积分, 赠送: {bonus_amount} 积分, 总计: {total_amount} 积分 (¥{amount_yuan})")
    
    # 创建支付订单
    if data.payment_method == "alipay":
        # 使用全局的 payment_service 实例（已在 payments.py 中初始化）
        from api.payments import payment_service
        import os
        
        # 获取前端地址，优先使用前端传递的 return_url，否则使用环境变量
        if data.return_url:
            base_url = data.return_url.rstrip('/')
            success_url = f"{base_url}/recharge-callback"
        else:
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8080")
            success_url = f"{frontend_url}/recharge-callback"
        
        logger.info(f"充值订单回调地址: {success_url}")
        
        try:
            payment_result = await payment_service.create_payment(
                method="alipay",
                amount=amount_yuan,
                currency="CNY",
                metadata={
                    "order_id": recharge_id,
                    "user_id": user_id,
                    "type": "credit_recharge",
                    "amount": data.amount,
                    "description": f"积分充值 {data.amount} 积分"
                },
                success_url=success_url
            )
            
            return RechargeResponse(
                recharge_id=recharge_id,
                amount=data.amount,
                bonus_amount=bonus_amount,
                total_amount=total_amount,
                payment_method=data.payment_method,
                payment_url=payment_result.get("payment_url"),
                message="请在新页面完成支付"
            )
        except Exception as e:
            logger.error(f"创建支付订单失败: {e}")
            raise HTTPException(status_code=500, detail=f"创建支付订单失败: {str(e)}")
    
    elif data.payment_method == "stripe":
        # TODO: 实现 Stripe 支付
        raise HTTPException(status_code=501, detail="Stripe 支付暂未实现")
    
    return RechargeResponse(
        recharge_id=recharge_id,
        amount=data.amount,
        payment_method=data.payment_method,
        message="充值订单创建成功"
    )


@router.post("/redeem-cdk", response_model=CdkRedeemResponse)
async def redeem_cdk(
    request: Request,
    data: CdkRedeemRequest,
    current_user: dict = Depends(get_current_user)
):
    """兑换 CDK，发放兑换积分（与免费/付费积分分离）。"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(status_code=503, detail="数据库未连接")
    db = app_state.db
    user_id = str(current_user["id"])

    code_candidates = _candidate_cdk_codes(data.code)
    if not code_candidates:
        logger.warning("CDK redeem rejected: invalid code format, user_id=%s", user_id)
        raise HTTPException(status_code=400, detail="兑换码格式无效")
    if not Config.CDK_CODE_PEPPER:
        logger.error("CDK_CODE_PEPPER is not configured on server")
        raise HTTPException(status_code=503, detail="CDK 服务未配置，请联系管理员")
    code_hashes = [_hash_cdk_code(code) for code in code_candidates]
    display_code = code_candidates[0]
    code_prefix = display_code[:8]

    invalid_or_expired_msg = "兑换码无效或已失效"

    async with db.pool.acquire() as conn:
        async with conn.transaction():
            code_row = await conn.fetchrow(
                """
                SELECT id, points, status, max_redeem_count, redeemed_count, redeemed_by_user_id, expires_at
                FROM cdk_redemption_codes
                WHERE code_hash = ANY($1::text[])
                FOR UPDATE
                """,
                code_hashes,
            )

            if not code_row:
                logger.warning("CDK redeem miss: user_id=%s, code_prefix=%s", user_id, code_prefix)
                raise HTTPException(status_code=400, detail=invalid_or_expired_msg)

            code_row = dict(code_row)

            status = str(code_row.get("status") or "").lower()
            expires_at = code_row.get("expires_at")
            if status != "active":
                logger.warning("CDK redeem rejected: inactive status=%s, user_id=%s, code_prefix=%s", status, user_id, code_prefix)
                raise HTTPException(status_code=400, detail=invalid_or_expired_msg)
            if expires_at and expires_at <= datetime.now(timezone.utc):
                await conn.execute(
                    "UPDATE cdk_redemption_codes SET status = 'expired', updated_at = now() WHERE id = $1",
                    code_row["id"],
                )
                logger.warning("CDK redeem rejected: expired, user_id=%s, code_prefix=%s", user_id, code_prefix)
                raise HTTPException(status_code=400, detail=invalid_or_expired_msg)

            max_redeem_count = int(code_row.get("max_redeem_count") or 1)
            redeemed_count = int(code_row.get("redeemed_count") or 0)
            if redeemed_count >= max_redeem_count:
                await conn.execute(
                    "UPDATE cdk_redemption_codes SET status = 'used', updated_at = now() WHERE id = $1",
                    code_row["id"],
                )
                logger.warning("CDK redeem rejected: used up, user_id=%s, code_prefix=%s, redeemed_count=%s, max=%s", user_id, code_prefix, redeemed_count, max_redeem_count)
                raise HTTPException(status_code=400, detail=invalid_or_expired_msg)

            redeemed_by = code_row.get("redeemed_by_user_id")
            if redeemed_by and str(redeemed_by) == user_id:
                logger.warning("CDK redeem rejected: already used by same user_id=%s, code_prefix=%s", user_id, code_prefix)
                raise HTTPException(status_code=400, detail="该兑换码已被你使用")

            points_awarded = int(code_row.get("points") or 0)
            if points_awarded <= 0:
                logger.warning("CDK redeem rejected: non-positive points=%s, user_id=%s, code_prefix=%s", points_awarded, user_id, code_prefix)
                raise HTTPException(status_code=400, detail=invalid_or_expired_msg)

            user_credits_row = await conn.fetchrow(
                """
                UPDATE users
                SET redeemed_points = COALESCE(redeemed_points, 0) + $1
                WHERE id = $2
                RETURNING COALESCE(free_points, 0) AS free_points,
                          COALESCE(redeemed_points, 0) AS redeemed_points,
                          COALESCE(gift_points, 0) AS gift_points,
                          COALESCE(paid_points, 0) AS paid_points
                """,
                points_awarded,
                user_id,
            )

            if not user_credits_row:
                raise HTTPException(status_code=404, detail="User not found")

            user_credits = dict(user_credits_row)

            next_redeemed_count = redeemed_count + 1
            next_status = "used" if next_redeemed_count >= max_redeem_count else "active"
            await conn.execute(
                """
                UPDATE cdk_redemption_codes
                SET redeemed_count = $1,
                    redeemed_by_user_id = CASE WHEN max_redeem_count = 1 THEN $2::uuid ELSE redeemed_by_user_id END,
                    redeemed_at = CASE WHEN max_redeem_count = 1 THEN now() ELSE redeemed_at END,
                    status = $3,
                    updated_at = now()
                WHERE id = $4
                """,
                next_redeemed_count,
                user_id,
                next_status,
                code_row["id"],
            )

            client_ip = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            await conn.execute(
                """
                INSERT INTO cdk_redemption_records (code_id, user_id, points, code_prefix, client_ip, user_agent, redeemed_at)
                VALUES ($1, $2, $3, $4, $5, $6, now())
                """,
                code_row["id"],
                user_id,
                points_awarded,
                code_prefix,
                client_ip,
                user_agent,
            )
    logger.info("用户 %s 兑换 CDK 成功，获得 %s 积分", user_id, points_awarded)
    return CdkRedeemResponse(
        points_awarded=points_awarded,
        points=points_awarded,
        free_credits=int(user_credits.get("free_points") or 0),
        redeemed_credits=int(user_credits.get("redeemed_points") or 0),
        paid_credits=int(user_credits.get("paid_points") or 0),
        credits=int(user_credits.get("free_points") or 0)
        + int(user_credits.get("redeemed_points") or 0)
        + int(user_credits.get("gift_points") or 0)
        + int(user_credits.get("paid_points") or 0),
        message=f"兑换成功，已到账 {points_awarded} 积分",
    )


@router.get("/recharge-history")
async def get_recharge_history(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """获取充值记录（已废弃，请使用 /recharge-orders）"""
    app_state = request.app.state
    db = app_state.db
    user_id = str(current_user["id"])
    
    records = await db.fetch(
        """
        SELECT id, amount, bonus_amount, total_amount, amount_yuan, payment_method, status, created_at, paid_at
        FROM credit_recharges
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT 50
        """,
        user_id
    )
    
    return {
        "records": [
            {
                "id": str(r["id"]),
                "amount": r["amount"],
                "bonus_amount": r.get("bonus_amount", 0),
                "total_amount": r.get("total_amount", r["amount"]),
                "amount_yuan": float(r["amount_yuan"]),
                "payment_method": r["payment_method"],
                "status": r["status"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "paid_at": r["paid_at"].isoformat() if r["paid_at"] else None
            }
            for r in records
        ]
    }


@router.get("/recharge-orders")
async def get_recharge_orders(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    current_user: dict = Depends(get_current_user)
):
    """获取充值订单列表"""
    from services.credit_service import CreditService
    
    app_state = request.app.state
    db = app_state.db
    user_id = str(current_user["id"])
    
    credit_service = CreditService(db)
    result = await credit_service.get_recharge_orders(
        user_id=user_id,
        page=page,
        page_size=page_size,
        status=status
    )
    
    # 格式化返回数据
    orders = []
    for order in result["orders"]:
        orders.append({
            "id": str(order["id"]),
            "amount": order["amount"],
            "bonus_amount": order["bonus_amount"],
            "total_amount": order["total_amount"],
            "amount_yuan": float(order["amount_yuan"]),
            "remaining_credits": order["remaining_credits"],
            "credit_price": order["credit_price"],
            "payment_method": order["payment_method"],
            "status": order["status"],
            "can_refund": order["can_refund"],
            "refund_deadline": order["refund_deadline"],
            "created_at": order["created_at"].isoformat() if order["created_at"] else None,
            "paid_at": order["paid_at"].isoformat() if order["paid_at"] else None,
            "refunded_at": order["refunded_at"].isoformat() if order["refunded_at"] else None,
            "refund_amount": float(order["refund_amount"]) if order["refund_amount"] else None
        })
    
    return {
        "orders": orders,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "total_pages": result["total_pages"]
    }


@router.get("/recharge-orders/{recharge_id}")
async def get_recharge_order_detail(
    request: Request,
    recharge_id: str,
    current_user: dict = Depends(get_current_user)
):
    """获取充值订单详情"""
    from services.credit_service import CreditService
    
    app_state = request.app.state
    db = app_state.db
    user_id = str(current_user["id"])
    
    # 查询充值订单
    order = await db.fetchrow(
        """
        SELECT id, user_id, amount, bonus_amount, total_amount, 
               amount_yuan, remaining_credits, payment_method, status,
               created_at, paid_at, refunded_at, refund_amount, refund_reason,
               payment_id
        FROM credit_recharges
        WHERE id = $1
        """,
        recharge_id
    )
    
    if not order:
        raise HTTPException(status_code=404, detail="充值订单不存在")
    
    if str(order["user_id"]) != user_id:
        raise HTTPException(status_code=403, detail="无权访问此订单")
    
    # 计算是否可以退款和退款截止时间
    can_refund = False
    refund_deadline = None
    credit_price = None
    
    if order["status"] == "paid" and not order["refunded_at"]:
        paid_at = order["paid_at"]
        if paid_at:
            from datetime import datetime, timezone, timedelta
            now = datetime.now(timezone.utc)
            days_passed = (now - paid_at).total_seconds() / 86400
            can_refund = days_passed <= 7
            refund_deadline = (paid_at + timedelta(days=7)).isoformat()
            
            # 计算积分单价
            if order["total_amount"] and order["total_amount"] > 0:
                credit_price = float(order["amount_yuan"]) / order["total_amount"]
    
    return {
        "id": str(order["id"]),
        "amount": order["amount"],
        "bonus_amount": order["bonus_amount"],
        "total_amount": order["total_amount"],
        "amount_yuan": float(order["amount_yuan"]),
        "remaining_credits": order["remaining_credits"],
        "credit_price": credit_price,
        "payment_method": order["payment_method"],
        "payment_id": order["payment_id"],
        "status": order["status"],
        "can_refund": can_refund,
        "refund_deadline": refund_deadline,
        "created_at": order["created_at"].isoformat() if order["created_at"] else None,
        "paid_at": order["paid_at"].isoformat() if order["paid_at"] else None,
        "refunded_at": order["refunded_at"].isoformat() if order["refunded_at"] else None,
        "refund_amount": float(order["refund_amount"]) if order["refund_amount"] else None,
        "refund_reason": order["refund_reason"]
    }


@router.post("/recharge-orders/{recharge_id}/pay")
async def pay_recharge_order(
    request: Request,
    recharge_id: str,
    current_user: dict = Depends(get_current_user)
):
    """重新支付充值订单"""
    app_state = request.app.state
    db = app_state.db
    user_id = str(current_user["id"])
    
    # 查询订单
    recharge = await db.fetchrow(
        "SELECT * FROM credit_recharges WHERE id = $1",
        recharge_id
    )
    
    if not recharge:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    if str(recharge["user_id"]) != user_id:
        raise HTTPException(status_code=403, detail="无权操作此订单")
    
    if recharge["status"] != "pending":
        raise HTTPException(status_code=400, detail="只能支付待支付的订单")
    
    # 重新创建支付
    payment_method = recharge["payment_method"]
    amount_yuan = float(recharge["amount_yuan"])
    
    if payment_method == "alipay":
        from api.payments import payment_service
        import os
        
        # 获取回调地址
        return_url_param = request.query_params.get("return_url")
        if return_url_param:
            success_url = f"{return_url_param}/recharge-callback"
        else:
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8080")
            success_url = f"{frontend_url}/recharge-callback"
        
        logger.info(f"重新支付充值订单: {recharge_id}, 回调地址: {success_url}")
        
        try:
            payment_result = await payment_service.create_payment(
                method="alipay",
                amount=amount_yuan,
                currency="CNY",
                metadata={
                    "order_id": recharge_id,
                    "user_id": user_id,
                    "type": "credit_recharge",
                    "amount": recharge["amount"],
                    "description": f"积分充值 {recharge['amount']} 积分"
                },
                success_url=success_url
            )
            
            return {
                "success": True,
                "payment_url": payment_result.get("payment_url"),
                "message": "请在新页面完成支付"
            }
        except Exception as e:
            logger.error(f"创建支付订单失败: {e}")
            raise HTTPException(status_code=500, detail=f"创建支付订单失败: {str(e)}")
    
    else:
        raise HTTPException(status_code=501, detail="不支持的支付方式")


@router.post("/recharge-orders/{recharge_id}/cancel")
async def cancel_recharge_order(
    request: Request,
    recharge_id: str,
    current_user: dict = Depends(get_current_user)
):
    """取消未支付的充值订单"""
    app_state = request.app.state
    db = app_state.db
    user_id = str(current_user["id"])
    
    # 查询订单
    recharge = await db.fetchrow(
        "SELECT id, user_id, status FROM credit_recharges WHERE id = $1",
        recharge_id
    )
    
    if not recharge:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    if str(recharge["user_id"]) != user_id:
        raise HTTPException(status_code=403, detail="无权操作此订单")
    
    if recharge["status"] != "pending":
        raise HTTPException(status_code=400, detail="只能取消待支付的订单")
    
    # 更新订单状态
    await db.execute(
        "UPDATE credit_recharges SET status = 'cancelled' WHERE id = $1",
        recharge_id
    )
    
    logger.info(f"用户 {user_id} 取消充值订单: {recharge_id}")
    
    return {
        "success": True,
        "message": "订单已取消"
    }


@router.post("/recharge-orders/{recharge_id}/refund")
async def refund_recharge_order(
    request: Request,
    recharge_id: str,
    current_user: dict = Depends(get_current_user)
):
    """申请退款"""
    from services.credit_service import CreditService
    
    app_state = request.app.state
    db = app_state.db
    user_id = str(current_user["id"])
    
    credit_service = CreditService(db)
    success, message, refund_amount = await credit_service.refund_recharge(
        recharge_id=recharge_id,
        user_id=user_id,
        reason="用户申请7天无理由退款"
    )
    
    if success:
        return {
            "success": True,
            "message": message,
            "refund_amount": refund_amount
        }
    else:
        raise HTTPException(status_code=400, detail=message)


@router.post("/recharge-callback")
async def recharge_callback(
    request: Request,
    recharge_id: str,
    payment_id: str
):
    """充值支付回调（内部接口，由支付回调触发）"""
    app_state = request.app.state
    db = app_state.db
    
    # 查询充值记录
    recharge = await db.fetchrow(
        "SELECT * FROM credit_recharges WHERE id = $1",
        recharge_id
    )
    
    if not recharge:
        logger.error(f"充值记录不存在: {recharge_id}")
        return {"success": False, "message": "充值记录不存在"}
    
    if recharge["status"] == "paid":
        logger.info(f"充值订单已处理: {recharge_id}")
        return {"success": True, "message": "充值订单已处理"}
    
    # 更新充值记录状态，初始化 remaining_credits
    total_amount = int(recharge["total_amount"])
    await db.execute(
        """
        UPDATE credit_recharges
        SET status = $1, paid_at = $2, payment_id = $3, remaining_credits = $4
        WHERE id = $5
        """,
        "paid",
        datetime.now(timezone.utc),
        payment_id,
        total_amount,
        recharge_id
    )
    
    user_id = str(recharge["user_id"])
    amount = int(recharge["amount"])
    bonus = int(recharge.get("bonus_amount") or 0)

    # 将付费积分和赠送积分都加到 paid_points（合并赠送积分）
    await db.execute(
        """
        UPDATE users
        SET paid_points = COALESCE(paid_points, 0) + $1
        WHERE id = $2
        """,
        amount + bonus,
        user_id,
    )

    logger.info(
        f"充值成功: 用户 {user_id} 实付积分 {amount}, 赠送 {bonus}, 合计到账 {amount + bonus}"
    )
    
    return {"success": True, "message": "充值成功"}


@router.post("/admin/fix-remaining-credits")
async def fix_remaining_credits(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """修复所有充值订单的 remaining_credits 字段（管理员接口）"""
    app_state = request.app.state
    db = app_state.db
    
    # 查询所有已支付但 remaining_credits 异常的充值订单
    orders = await db.fetch(
        """
        SELECT id, user_id, total_amount, remaining_credits
        FROM credit_recharges
        WHERE status = 'paid' 
          AND refunded_at IS NULL
          AND (remaining_credits IS NULL OR remaining_credits > total_amount)
        """
    )
    
    fixed_count = 0
    
    for order in orders:
        order_id = str(order["id"])
        user_id = str(order["user_id"])
        total_amount = order["total_amount"]
        
        # 计算该订单的实际消耗（从 credit_consumption_records 表）
        consumed = await db.fetchval(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM credit_consumption_records
            WHERE recharge_id = $1
            """,
            order_id
        )
        
        remaining = max(0, total_amount - consumed)
        
        # 更新 remaining_credits
        await db.execute(
            "UPDATE credit_recharges SET remaining_credits = $1 WHERE id = $2",
            remaining,
            order_id
        )
        
        fixed_count += 1
        logger.info(
            f"修复充值订单 {order_id}: 总积分={total_amount}, "
            f"已消耗={consumed}, 剩余={remaining}"
        )
    
    return {
        "success": True,
        "message": f"已修复 {fixed_count} 个充值订单的 remaining_credits 字段",
        "fixed_count": fixed_count
    }
