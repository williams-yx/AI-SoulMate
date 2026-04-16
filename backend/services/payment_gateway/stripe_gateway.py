"""
Stripe 支付网关实现
"""
import stripe
from typing import Dict, Any, Optional
from .base_gateway import BasePaymentGateway
from logger import logger


class StripePaymentGateway(BasePaymentGateway):
    """Stripe 支付网关"""
    
    def __init__(self, api_key: str):
        """
        初始化 Stripe 网关
        
        Args:
            api_key: Stripe API密钥
        """
        super().__init__(api_key=api_key)
        stripe.api_key = api_key
        self.api_key = api_key
    
    def is_test_mode(self) -> bool:
        """检查是否为测试模式"""
        return self.api_key.startswith("sk_test_")
    
    async def create_payment(
        self,
        amount: float,
        currency: str = "usd",
        metadata: Optional[Dict[str, Any]] = None,
        success_url: str = None,
        cancel_url: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        创建Stripe Checkout Session（用于跳转支付）
        
        Args:
            amount: 金额（单位：元）
            currency: 货币类型（支持 usd, cny 等）
            metadata: 元数据（如订单ID等）
            success_url: 支付成功后的跳转URL
            cancel_url: 取消支付后的跳转URL
        
        Returns:
            包含 checkout_url 的字典
        """
        try:
            # 转换为分（Stripe使用最小货币单位）
            # 对于人民币，最小单位也是分
            amount_cents = int(amount * 100)
            
            # 确保货币代码小写
            currency = currency.lower()
            
            # 创建 Checkout Session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': currency,
                        'unit_amount': amount_cents,
                        'product_data': {
                            'name': f"订单支付 - {metadata.get('order_id', 'N/A') if metadata else 'N/A'}",
                            'description': '商品订单支付',
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url or 'http://localhost:8080/orders?payment=success',
                cancel_url=cancel_url or 'http://localhost:8080/orders?payment=cancel',
                metadata=metadata or {},
            )
            
            logger.info(f"Stripe Checkout Session创建成功: {checkout_session.id}, 货币: {currency}, 金额: {amount}")
            
            return {
                "session_id": checkout_session.id,
                "checkout_url": checkout_session.url,
                "amount": amount,
                "currency": currency,
                "status": checkout_session.status
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Checkout Session创建失败: {str(e)}")
            raise Exception(f"Stripe error: {str(e)}")
    
    async def confirm_payment(self, payment_id: str) -> bool:
        """
        确认支付是否成功
        
        Args:
            payment_id: 支付意图ID 或 Checkout Session ID
        
        Returns:
            支付是否成功
        """
        try:
            # 尝试作为Checkout Session ID处理
            if payment_id.startswith('cs_'):
                session = stripe.checkout.Session.retrieve(payment_id)
                is_succeeded = session.payment_status == "paid"
                logger.info(f"Stripe Checkout Session状态: {session.payment_status}, ID: {payment_id}")
                return is_succeeded
            else:
                # 作为Payment Intent ID处理
                payment_intent = stripe.PaymentIntent.retrieve(payment_id)
                is_succeeded = payment_intent.status == "succeeded"
                logger.info(f"Stripe支付状态: {payment_intent.status}, ID: {payment_id}")
                return is_succeeded
        except stripe.error.StripeError as e:
            logger.error(f"Stripe支付确认失败: {str(e)}")
            return False
    
    async def refund_payment(
        self,
        payment_id: str,
        amount: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        退款
        
        Args:
            payment_id: 支付意图ID
            amount: 退款金额（可选，不填则全额退款）
        
        Returns:
            退款信息
        """
        try:
            refund_params = {"payment_intent": payment_id}
            
            if amount is not None:
                refund_params["amount"] = int(amount * 100)
            
            refund = stripe.Refund.create(**refund_params)
            
            logger.info(f"Stripe退款成功: {refund.id}")
            
            return {
                "refund_id": refund.id,
                "status": refund.status,
                "amount": refund.amount / 100 if refund.amount else None
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe退款失败: {str(e)}")
            raise Exception(f"Stripe refund error: {str(e)}")
