"""
积分服务 - 处理积分消耗、充值、退款等核心逻辑
"""
from typing import Optional, Tuple
from datetime import datetime, timezone, timedelta
from logger import logger


class CreditService:
    """积分服务类"""
    
    def __init__(self, db):
        # 兼容不同类型的 db 对象
        # 如果 db 有 pool 属性，使用 db.pool
        # 否则假设 db 本身就是 pool
        if hasattr(db, 'pool'):
            self.pool = db.pool
        else:
            self.pool = db
    
    async def consume_credits(
        self,
        user_id: str,
        amount: int,
        reason: str = "unknown",
        related_id: Optional[str] = None,
        conn=None  # 新增：可选的已有连接
    ) -> bool:
        """
        消耗积分（FIFO顺序）
        
        消耗顺序:
        1. 免费积分
        2. 兑换积分
        3. 付费积分（按充值时间FIFO）
        
        Args:
            user_id: 用户ID
            amount: 消耗积分数量
            reason: 消耗原因
            related_id: 关联业务ID
            conn: 可选的已有数据库连接（用于在事务中调用）
            
        Returns:
            bool: 是否成功
        """
        if amount <= 0:
            logger.error(f"消耗积分数量必须大于0: {amount}")
            return False
        
        # 如果提供了连接，直接使用（假设已在事务中）
        if conn is not None:
            return await self._consume_credits_impl(conn, user_id, amount, reason, related_id)
        
        # 否则创建新连接和事务
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                return await self._consume_credits_impl(conn, user_id, amount, reason, related_id)
    
    async def _consume_credits_impl(
        self,
        conn,
        user_id: str,
        amount: int,
        reason: str,
        related_id: Optional[str]
    ) -> bool:
        """消耗积分的实际实现"""
        # 锁定用户行，防止并发问题
        user = await conn.fetchrow(
            """
            SELECT id, free_points, redeemed_points, paid_points
            FROM users
            WHERE id = $1
            FOR UPDATE
            """,
            user_id
        )
        
        if not user:
            logger.error(f"用户不存在: {user_id}")
            return False
        
        free_points = user["free_points"] or 0
        redeemed_points = user["redeemed_points"] or 0
        paid_points = user["paid_points"] or 0
        total_points = free_points + redeemed_points + paid_points
        
        if total_points < amount:
            logger.error(
                f"用户 {user_id} 积分不足: 需要 {amount}, "
                f"拥有 {total_points} (免费:{free_points}, 兑换:{redeemed_points}, 付费:{paid_points})"
            )
            return False
        
        remaining = amount
        
        # 1. 先消耗免费积分
        if remaining > 0 and free_points > 0:
            consume_free = min(remaining, free_points)
            await conn.execute(
                "UPDATE users SET free_points = free_points - $1 WHERE id = $2",
                consume_free,
                user_id
            )
            await self._record_consumption(
                conn, user_id, None, consume_free, "free", reason, related_id
            )
            remaining -= consume_free
            logger.info(f"用户 {user_id} 消耗免费积分 {consume_free}, 剩余需消耗 {remaining}")
        
        # 2. 再消耗兑换积分
        if remaining > 0 and redeemed_points > 0:
            consume_redeemed = min(remaining, redeemed_points)
            await conn.execute(
                "UPDATE users SET redeemed_points = redeemed_points - $1 WHERE id = $2",
                consume_redeemed,
                user_id
            )
            await self._record_consumption(
                conn, user_id, None, consume_redeemed, "redeemed", reason, related_id
            )
            remaining -= consume_redeemed
            logger.info(f"用户 {user_id} 消耗兑换积分 {consume_redeemed}, 剩余需消耗 {remaining}")
        
        # 3. 最后消耗付费积分（FIFO）
        if remaining > 0 and paid_points > 0:
            await self._consume_paid_credits_fifo(
                conn, user_id, remaining, reason, related_id
            )
        
        logger.info(
            f"用户 {user_id} 成功消耗积分 {amount}, 原因: {reason}, 关联ID: {related_id}"
        )
        return True
    
    async def _consume_paid_credits_fifo(
        self,
        conn,
        user_id: str,
        amount: int,
        reason: str,
        related_id: Optional[str]
    ):
        """
        按FIFO顺序消耗付费积分
        """
        # 查询所有可用的充值订单（按充值时间排序）
        recharges = await conn.fetch(
            """
            SELECT id, remaining_credits, paid_at
            FROM credit_recharges
            WHERE user_id = $1 
              AND status = 'paid' 
              AND remaining_credits > 0
              AND refunded_at IS NULL
            ORDER BY paid_at ASC
            FOR UPDATE
            """,
            user_id
        )
        
        remaining = amount
        
        for recharge in recharges:
            if remaining <= 0:
                break
            
            recharge_id = str(recharge["id"])
            available = recharge["remaining_credits"]
            consume = min(remaining, available)
            
            # 更新充值订单的剩余积分
            await conn.execute(
                """
                UPDATE credit_recharges 
                SET remaining_credits = remaining_credits - $1
                WHERE id = $2
                """,
                consume,
                recharge_id
            )
            
            # 记录消耗
            await self._record_consumption(
                conn, user_id, recharge_id, consume, "paid", reason, related_id
            )
            
            remaining -= consume
            logger.info(
                f"用户 {user_id} 从充值订单 {recharge_id} 消耗付费积分 {consume}, "
                f"订单剩余 {available - consume}"
            )
        
        # 更新用户的付费积分总数
        await conn.execute(
            "UPDATE users SET paid_points = paid_points - $1 WHERE id = $2",
            amount,
            user_id
        )
    
    async def _record_consumption(
        self,
        conn,
        user_id: str,
        recharge_id: Optional[str],
        amount: int,
        credit_type: str,
        reason: str,
        related_id: Optional[str]
    ):
        """记录积分消耗"""
        await conn.execute(
            """
            INSERT INTO credit_consumption_records 
            (user_id, recharge_id, amount, credit_type, reason, related_id, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            user_id,
            recharge_id,
            amount,
            credit_type,
            reason,
            related_id,
            datetime.now(timezone.utc)
        )
    
    async def refund_recharge(
        self,
        recharge_id: str,
        user_id: str,
        reason: str = "用户申请退款"
    ) -> Tuple[bool, str, Optional[float]]:
        """
        退款充值订单
        
        Returns:
            (成功, 消息, 退款金额)
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # 锁定充值订单
                recharge = await conn.fetchrow(
                    """
                    SELECT id, user_id, amount, bonus_amount, total_amount, 
                           amount_yuan, remaining_credits, status, paid_at, refunded_at,
                           payment_id, payment_method
                    FROM credit_recharges
                    WHERE id = $1
                    FOR UPDATE
                    """,
                    recharge_id
                )
                
                if not recharge:
                    return False, "充值订单不存在", None
                
                if str(recharge["user_id"]) != user_id:
                    return False, "无权操作此订单", None
                
                if recharge["status"] != "paid":
                    return False, "订单未支付，无法退款", None
                
                if recharge["refunded_at"]:
                    return False, "订单已退款", None
                
                # 检查是否在7天内
                paid_at = recharge["paid_at"]
                if not paid_at:
                    return False, "订单支付时间异常", None
                
                now = datetime.now(timezone.utc)
                days_passed = (now - paid_at).total_seconds() / 86400
                
                if days_passed > 7:
                    return False, "已超过7天退款期限，如需退款请联系客服", None
                
                # 计算退款金额
                total_credits = recharge["total_amount"]  # 付费 + 赠送
                remaining_credits = recharge["remaining_credits"]
                paid_yuan = float(recharge["amount_yuan"])
                
                # 如果 remaining_credits 为 None，说明数据异常，需要修复
                if remaining_credits is None:
                    logger.warning(f"充值订单 {recharge_id} 的 remaining_credits 为 None，尝试修复")
                    # 查询用户当前的积分消耗记录，计算剩余积分
                    consumed = await conn.fetchval(
                        """
                        SELECT COALESCE(SUM(amount), 0)
                        FROM credit_transactions
                        WHERE recharge_id = $1 AND amount < 0
                        """,
                        recharge_id
                    )
                    remaining_credits = total_credits + consumed  # consumed 是负数
                    
                    # 更新数据库
                    await conn.execute(
                        """
                        UPDATE credit_recharges
                        SET remaining_credits = $1
                        WHERE id = $2
                        """,
                        remaining_credits,
                        recharge_id
                    )
                    logger.info(f"已修复充值订单 {recharge_id} 的 remaining_credits: {remaining_credits}")
                
                if remaining_credits == total_credits:
                    # 未消耗，全额退款
                    refund_amount = paid_yuan
                elif remaining_credits > 0:
                    # 部分消耗，按比例退款
                    credit_price = paid_yuan / total_credits
                    refund_amount = remaining_credits * credit_price
                else:
                    # 已全部消耗，无法退款
                    return False, "积分已全部使用，无法退款", None
                
                refund_amount = round(refund_amount, 2)
                
                # 调用支付网关退款
                from api.payments import payment_service
                
                payment_id = recharge.get("payment_id")
                payment_method = recharge.get("payment_method")
                
                if not payment_id:
                    logger.error(f"充值订单 {recharge_id} 缺少 payment_id")
                    return False, "支付订单ID不存在，无法退款", None
                
                if not payment_method:
                    logger.error(f"充值订单 {recharge_id} 缺少 payment_method")
                    return False, "支付方式信息缺失，无法退款", None
                
                logger.info(
                    f"准备退款: 订单 {recharge_id}, payment_id: {payment_id}, "
                    f"payment_method: {payment_method}, 退款金额: ¥{refund_amount}, "
                    f"总积分: {total_credits}, 剩余积分: {remaining_credits}, "
                    f"支付金额: ¥{paid_yuan}"
                )
                
                # 支付宝退款使用商户订单号（out_trade_no），应该使用充值订单的ID
                # 因为创建支付时使用的是充值订单ID作为out_trade_no
                refund_order_id = recharge_id  # 使用充值订单ID作为商户订单号
                
                try:
                    refund_result = await payment_service.refund_payment(
                        method=payment_method,
                        payment_id=refund_order_id,  # 使用充值订单ID
                        amount=refund_amount
                    )
                    
                    if not refund_result.get("success"):
                        error_msg = refund_result.get("message", "退款失败")
                        logger.error(f"退款失败: 订单 {recharge_id}, 错误: {error_msg}")
                        
                        # 如果是支付宝交易不存在的错误，给出更友好的提示
                        if "交易不存在" in error_msg or "TRADE_NOT_EXIST" in error_msg:
                            return False, "支付订单不存在或已关闭，请联系客服处理", None
                        
                        return False, f"退款失败: {error_msg}", None
                    
                except Exception as e:
                    logger.error(f"调用支付网关退款失败: 订单 {recharge_id}, 异常: {e}")
                    return False, f"退款失败: {str(e)}", None
                
                # 更新充值订单状态
                await conn.execute(
                    """
                    UPDATE credit_recharges
                    SET refunded_at = $1,
                        refund_amount = $2,
                        refund_reason = $3,
                        status = 'refunded'
                    WHERE id = $4
                    """,
                    now,
                    refund_amount,
                    reason,
                    recharge_id
                )
                
                # 从用户账户扣除剩余积分
                if remaining_credits > 0:
                    await conn.execute(
                        """
                        UPDATE users
                        SET paid_points = GREATEST(0, paid_points - $1)
                        WHERE id = $2
                        """,
                        remaining_credits,
                        user_id
                    )
                
                logger.info(
                    f"用户 {user_id} 退款成功: 订单 {recharge_id}, "
                    f"退款金额 ¥{refund_amount}, 扣除积分 {remaining_credits}"
                )
                
                return True, f"退款成功，¥{refund_amount} 将原路返回", refund_amount
    
    async def get_recharge_orders(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None
    ):
        """
        获取充值订单列表
        """
        offset = (page - 1) * page_size
        
        where_clause = "WHERE user_id = $1"
        params = [user_id]
        
        if status:
            where_clause += " AND status = $2"
            params.append(status)
        
        # 查询总数
        count_query = f"SELECT COUNT(*) FROM credit_recharges {where_clause}"
        total = await self.pool.fetchval(count_query, *params)
        
        # 查询订单列表
        query = f"""
            SELECT id, amount, bonus_amount, total_amount, amount_yuan,
                   remaining_credits, payment_method, status,
                   created_at, paid_at, refunded_at, refund_amount
            FROM credit_recharges
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
        """
        params.extend([page_size, offset])
        
        orders = await self.pool.fetch(query, *params)
        
        # 计算每个订单的积分单价和是否可退款
        result_orders = []
        now = datetime.now(timezone.utc)
        
        for order in orders:
            order_dict = dict(order)
            
            # 兜底修复：如果是已支付订单但 remaining_credits 为 NULL，自动修复
            if order["status"] == "paid" and order["remaining_credits"] is None:
                total_amount = order["total_amount"]
                logger.warning(
                    f"检测到已支付订单 {order['id']} 的 remaining_credits 为 NULL，自动修复为 {total_amount}"
                )
                await self.pool.execute(
                    "UPDATE credit_recharges SET remaining_credits = $1 WHERE id = $2",
                    total_amount,
                    str(order["id"])
                )
                order_dict["remaining_credits"] = total_amount
            
            # 计算积分单价
            total_credits = order_dict["total_amount"]
            paid_yuan = float(order_dict["amount_yuan"])
            credit_price = paid_yuan / total_credits if total_credits > 0 else 0
            order_dict["credit_price"] = round(credit_price, 4)
            
            # 判断是否可退款
            can_refund = False
            refund_deadline = None
            
            if (order["status"] == "paid" and 
                not order["refunded_at"] and 
                order["paid_at"]):
                paid_at = order["paid_at"]
                # 确保 paid_at 是 aware datetime（带时区）
                if paid_at.tzinfo is None:
                    # 如果是 naive datetime，假设是 UTC
                    paid_at = paid_at.replace(tzinfo=timezone.utc)
                
                days_passed = (now - paid_at).total_seconds() / 86400
                can_refund = days_passed <= 7 and order["remaining_credits"] > 0
                refund_deadline = paid_at + timedelta(days=7)
                
                logger.debug(
                    f"订单 {order['id']}: paid_at={paid_at}, now={now}, "
                    f"days_passed={days_passed:.2f}, can_refund={can_refund}"
                )
            
            order_dict["can_refund"] = can_refund
            order_dict["refund_deadline"] = refund_deadline.isoformat() if refund_deadline else None
            
            result_orders.append(order_dict)
        
        return {
            "orders": result_orders,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
