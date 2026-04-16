"""
统一支付服务
管理多个支付网关，提供统一的支付接口
"""
from typing import Dict, Any, Optional
from .stripe_gateway import StripePaymentGateway
from .paypal_gateway import PayPalPaymentGateway
from .alipay_gateway import AlipayPaymentGateway
from logger import logger


class PaymentService:
    """统一支付服务"""
    
    def __init__(
        self,
        stripe_api_key: Optional[str] = None,
        paypal_client_id: Optional[str] = None,
        paypal_client_secret: Optional[str] = None,
        paypal_mode: str = "sandbox",
        alipay_app_id: Optional[str] = None,
        alipay_app_private_key: Optional[str] = None,
        alipay_public_key: Optional[str] = None,
        alipay_is_sandbox: bool = True,
        alipay_return_url: Optional[str] = None,
        alipay_notify_url: Optional[str] = None
    ):
        """
        初始化支付服务
        
        Args:
            stripe_api_key: Stripe API密钥
            paypal_client_id: PayPal Client ID
            paypal_client_secret: PayPal Client Secret
            paypal_mode: PayPal模式 (sandbox 或 live)
            alipay_app_id: 支付宝应用ID
            alipay_app_private_key: 支付宝应用私钥
            alipay_public_key: 支付宝公钥
            alipay_is_sandbox: 支付宝是否为沙箱环境
            alipay_return_url: 支付宝同步回调地址
            alipay_notify_url: 支付宝异步回调地址
        """
        self.stripe = None
        self.paypal = None
        self.alipay = None
        
        if stripe_api_key:
            self.stripe = StripePaymentGateway(stripe_api_key)
        
        if paypal_client_id and paypal_client_secret:
            self.paypal = PayPalPaymentGateway(
                paypal_client_id,
                paypal_client_secret,
                paypal_mode
            )
        
        if alipay_app_id and alipay_app_private_key and alipay_public_key:
            try:
                self.alipay = AlipayPaymentGateway(
                    alipay_app_id,
                    alipay_app_private_key,
                    alipay_public_key,
                    alipay_is_sandbox,
                    alipay_return_url,
                    alipay_notify_url
                )
                logger.info("✅ 支付宝支付网关初始化成功")
            except Exception as e:
                logger.error(f"❌ 支付宝支付网关初始化失败: {str(e)}")
                self.alipay = None
    
    async def create_payment(
        self,
        method: str,
        amount: float,
        currency: str = "usd",
        metadata: Optional[Dict[str, Any]] = None,
        success_url: str = None,
        cancel_url: str = None
    ) -> Dict[str, Any]:
        """
        创建支付
        
        Args:
            method: 支付方式 (stripe 或 paypal)
            amount: 金额
            currency: 货币
            metadata: 元数据
            success_url: 支付成功后的跳转URL
            cancel_url: 取消支付后的跳转URL
        
        Returns:
            支付信息
        """
        if method == "stripe":
            if not self.stripe:
                raise Exception("Stripe未配置")
            return await self.stripe.create_payment(
                amount, currency, metadata, success_url, cancel_url
            )
        
        elif method == "paypal":
            if not self.paypal:
                raise Exception("PayPal未配置")
            return await self.paypal.create_payment(amount, currency.upper(), metadata)
        
        elif method == "alipay":
            if not self.alipay:
                raise Exception("支付宝未配置")
            return await self.alipay.create_payment(
                amount, currency.upper(), metadata, success_url, cancel_url
            )
        
        else:
            raise Exception(f"不支持的支付方式: {method}")
    
    async def confirm_payment(self, method: str, payment_id: str) -> bool:
        """
        确认支付
        
        Args:
            method: 支付方式
            payment_id: 支付ID
        
        Returns:
            是否成功
        """
        if method == "stripe":
            if not self.stripe:
                raise Exception("Stripe未配置")
            return await self.stripe.confirm_payment(payment_id)
        
        elif method == "paypal":
            if not self.paypal:
                raise Exception("PayPal未配置")
            return await self.paypal.confirm_payment(payment_id)
        
        elif method == "alipay":
            if not self.alipay:
                raise Exception("支付宝未配置")
            return await self.alipay.confirm_payment(payment_id)
        
        else:
            raise Exception(f"不支持的支付方式: {method}")
    
    async def refund_payment(
        self,
        method: str,
        payment_id: str,
        amount: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        退款
        
        Args:
            method: 支付方式
            payment_id: 支付ID
            amount: 退款金额（可选）
        
        Returns:
            退款信息
        """
        if method == "stripe":
            if not self.stripe:
                raise Exception("Stripe未配置")
            return await self.stripe.refund_payment(payment_id, amount)
        
        elif method == "alipay":
            if not self.alipay:
                raise Exception("支付宝未配置")
            return await self.alipay.refund_payment(payment_id, amount)
        
        else:
            raise Exception(f"不支持的支付方式: {method}")
