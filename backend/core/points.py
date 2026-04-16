"""
积分逻辑：免费积分（可刷新）+ 兑换积分（CDK）+ 赠送积分（充值活动）+ 付费积分。
- 免费积分：首次使用后开始 24 小时计时，到期刷新为 100
- 兑换积分：CDK 兑换获得，不刷新
- 赠送积分：充值活动赠送，不刷新
- 付费积分：充值获得，不刷新
- 扣费顺序：免费 -> 兑换 -> 赠送 -> 付费
"""
from typing import Any, Dict

FREE_POINTS_REFRESH_AMOUNT = 100  # 每日刷新量
FREE_POINTS_REFRESH_INTERVAL_SECONDS = 24 * 3600  # 24 小时


async def maybe_refresh_free_points(db: Any, user_id: str) -> None:
    """
    若用户免费积分未满且距“本轮首次使用免费积分”的时间已满 24 小时，则刷新为
    FREE_POINTS_REFRESH_AMOUNT（默认 100）。
    需在查询用户后、返回前调用（会执行 UPDATE 并影响后续读取）。
    """
    # 兜底清理历史脏数据：若免费积分已满额，说明当前不在计时轮次，清空计时点。
    await db.execute(
        """
        UPDATE users SET free_points_refreshed_at = NULL
        WHERE id = $1
          AND COALESCE(free_points, 0) >= $2
          AND free_points_refreshed_at IS NOT NULL
        """,
        user_id,
        FREE_POINTS_REFRESH_AMOUNT,
    )

    await db.execute(
        """
        UPDATE users SET
            free_points = $1,
            free_points_refreshed_at = NULL
        WHERE id = $2
          AND COALESCE(free_points, 0) < $1
          AND (
            (free_points_refreshed_at IS NOT NULL AND (now() - free_points_refreshed_at) >= interval '24 hours')
            OR
            (free_points_refreshed_at IS NULL AND COALESCE(free_points, 0) = 0)
          )
        """,
        FREE_POINTS_REFRESH_AMOUNT,
        user_id,
    )

    # 数据修复：免费积分已低于满额（说明曾消耗过免费积分）但 free_points_refreshed_at 仍为 NULL 时，
    # 个人中心无法展示 24h 倒计时。常见于历史迁移、旧扣费路径未写入锚点等；补写 now() 作为本轮计时起点
    # （无法还原真实首扣时刻）。满额清锚点、0 分走上方自动刷新逻辑，均不会进入本分支。
    await db.execute(
        """
        UPDATE users SET free_points_refreshed_at = now()
        WHERE id = $1
          AND COALESCE(free_points, 0) > 0
          AND COALESCE(free_points, 0) < $2
          AND free_points_refreshed_at IS NULL
        """,
        user_id,
        FREE_POINTS_REFRESH_AMOUNT,
    )


def total_points(row: Dict[str, Any]) -> int:
    """从 users 行或 current_user 字典得到总积分（免费 + 兑换 + 赠送 + 付费）。"""
    free = row.get("free_points")
    redeemed = row.get("redeemed_points")
    paid = row.get("paid_points")
    gift = row.get("gift_points")
    # 兼容旧数据：若没有双轨列则用 points
    if free is None and redeemed is None and paid is None and gift is None:
        return int(row.get("points") or row.get("credits") or 0)
    return int(free or 0) + int(redeemed or 0) + int(gift or 0) + int(paid or 0)


async def deduct_points(db: Any, user_id: str, amount: int, reason: str = "unknown", related_id: str = None) -> bool:
    """
    扣减积分：使用新的 CreditService 进行 FIFO 消耗。
    消耗顺序：免费 → 兑换 → 付费（按充值时间FIFO）
    
    Args:
        db: 数据库连接
        user_id: 用户ID
        amount: 扣除积分数量
        reason: 消耗原因（如 "generate_3d", "purchase_product"）
        related_id: 关联业务ID
        
    Returns:
        bool: 成功返回 True，积分不足返回 False
    """
    if amount <= 0:
        return True
    
    try:
        from services.credit_service import CreditService
        credit_service = CreditService(db)
        success = await credit_service.consume_credits(
            user_id=user_id,
            amount=amount,
            reason=reason,
            related_id=related_id
        )
        return success
    except Exception as e:
        from logger import logger
        logger.error(f"扣除积分失败: {e}")
        return False
