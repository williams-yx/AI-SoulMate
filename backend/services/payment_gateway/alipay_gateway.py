"""
支付宝支付网关实现
使用 python-alipay-sdk
"""
from typing import Dict, Any, Optional
from alipay import AliPay
from .base_gateway import BasePaymentGateway
from logger import logger


class AlipayPaymentGateway(BasePaymentGateway):
    """支付宝支付网关"""
    
    def __init__(
        self,
        app_id: str,
        app_private_key: str,
        alipay_public_key: str,
        is_sandbox: bool = True,
        return_url: str = None,
        notify_url: str = None
    ):
        """
        初始化支付宝网关
        
        Args:
            app_id: 支付宝应用ID
            app_private_key: 应用私钥（用于签名）
            alipay_public_key: 支付宝公钥（用于验签）
            is_sandbox: 是否为沙箱环境
            return_url: 同步回调地址（支付完成后跳转）
            notify_url: 异步回调地址（支付宝服务器通知）
        """
        super().__init__(
            app_id=app_id,
            app_private_key=app_private_key,
            alipay_public_key=alipay_public_key,
            is_sandbox=is_sandbox,
            return_url=return_url,
            notify_url=notify_url
        )
        
        # 创建支付宝客户端
        # 处理密钥格式 - python-alipay-sdk需要完整的PEM格式
        if not app_private_key.startswith("-----BEGIN"):
            app_private_key = f"-----BEGIN RSA PRIVATE KEY-----\n{app_private_key}\n-----END RSA PRIVATE KEY-----"
        
        if not alipay_public_key.startswith("-----BEGIN"):
            alipay_public_key = f"-----BEGIN PUBLIC KEY-----\n{alipay_public_key}\n-----END PUBLIC KEY-----"
        
        self.alipay = AliPay(
            appid=app_id,
            app_notify_url=notify_url,
            app_private_key_string=app_private_key,
            alipay_public_key_string=alipay_public_key,
            sign_type="RSA2",
            debug=is_sandbox  # True表示沙箱环境
        )
        
        self.is_sandbox = is_sandbox
        self.return_url = return_url
        self.notify_url = notify_url
        
        logger.info(f"支付宝网关初始化完成 (沙箱模式: {is_sandbox})")
    
    def is_test_mode(self) -> bool:
        """检查是否为测试模式"""
        return self.is_sandbox
    
    async def create_payment(
        self,
        amount: float,
        currency: str = "CNY",
        metadata: Optional[Dict[str, Any]] = None,
        success_url: str = None,
        cancel_url: str = None
    ) -> Dict[str, Any]:
        """
        创建支付宝支付
        
        Args:
            amount: 金额
            currency: 货币（支付宝只支持CNY）
            metadata: 元数据（包含订单信息）
            success_url: 成功回调URL
            cancel_url: 取消回调URL
        
        Returns:
            包含支付URL的字典
        """
        try:
            order_id = metadata.get("order_id", "") if metadata else ""
            
            # 使用传入的success_url，如果没有则使用初始化时的return_url
            # 确保return_url存在，否则支付宝会报错
            return_url = success_url or self.return_url
            if not return_url:
                raise Exception("支付宝return_url未配置")
            
            logger.info(f"支付宝支付创建: 订单={order_id}, 回调地址={return_url}")
            
            # 创建电脑网站支付
            order_string = self.alipay.api_alipay_trade_page_pay(
                out_trade_no=order_id,
                total_amount=str(amount),
                subject=f"订单支付 - {order_id}",
                return_url=return_url,
                notify_url=self.notify_url
            )
            
            # 构建支付URL
            if self.is_sandbox:
                payment_url = f"https://openapi-sandbox.dl.alipaydev.com/gateway.do?{order_string}"
            else:
                payment_url = f"https://openapi.alipay.com/gateway.do?{order_string}"
            
            logger.info(f"支付宝支付创建成功: 订单={order_id}, 金额={amount}, URL={payment_url[:100]}...")
            
            return {
                "payment_url": payment_url,
                "order_id": order_id
            }
        
        except Exception as e:
            logger.error(f"支付宝支付创建失败: {str(e)}")
            raise Exception(f"Alipay error: {str(e)}")
    
    async def confirm_payment(self, payment_id: str) -> bool:
        """
        确认支付状态
        
        Args:
            payment_id: 订单号
        
        Returns:
            是否支付成功
        """
        try:
            # 查询订单状态
            result = self.alipay.api_alipay_trade_query(
                out_trade_no=payment_id
            )
            
            if result.get("code") == "10000":
                trade_status = result.get("trade_status")
                # TRADE_SUCCESS 或 TRADE_FINISHED 表示支付成功
                return trade_status in ["TRADE_SUCCESS", "TRADE_FINISHED"]
            
            return False
        
        except Exception as e:
            logger.error(f"支付宝支付查询失败: {str(e)}")
            return False
    
    async def refund_payment(
        self,
        payment_id: str,
        amount: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        退款
        
        Args:
            payment_id: 订单号（商户订单号）
            amount: 退款金额（必填）
        
        Returns:
            退款结果
        """
        try:
            if not amount or amount <= 0:
                raise Exception("退款金额必须大于0")
            
            params = {
                "out_trade_no": payment_id,
                "refund_amount": str(amount)
            }
            
            logger.info(f"支付宝退款请求: 订单={payment_id}, 金额={amount}, 参数={params}")
            
            result = self.alipay.api_alipay_trade_refund(**params)
            
            logger.info(f"支付宝退款响应: {result}")
            
            if result.get("code") == "10000":
                logger.info(f"支付宝退款成功: 订单={payment_id}, 金额={amount}")
                return {
                    "success": True,
                    "refund_id": result.get("trade_no")
                }
            else:
                error_code = result.get("code")
                error_msg = result.get("sub_msg") or result.get("msg") or "退款失败"
                sub_code = result.get("sub_code")
                logger.error(
                    f"支付宝退款失败: 订单={payment_id}, "
                    f"code={error_code}, sub_code={sub_code}, msg={error_msg}, "
                    f"完整响应={result}"
                )
                
                # 根据错误码提供更友好的提示
                if sub_code == "ACQ.SYSTEM_ERROR":
                    raise Exception(f"支付宝系统异常，请稍后重试。原因: {error_msg}")
                elif sub_code == "ACQ.TRADE_NOT_EXIST":
                    raise Exception(f"交易不存在或已关闭。原因: {error_msg}")
                elif sub_code == "ACQ.REFUND_AMT_NOT_EQUAL_TOTAL":
                    raise Exception(f"退款金额超出订单金额。原因: {error_msg}")
                else:
                    raise Exception(f"{error_msg} (错误码: {sub_code or error_code})")
        
        except Exception as e:
            logger.error(f"支付宝退款异常: {str(e)}")
            raise Exception(f"Alipay refund error: {str(e)}")
    
    def verify_notify(self, params: Dict[str, str]) -> bool:
        """
        验证支付宝异步通知签名
        
        Args:
            params: 通知参数
        
        Returns:
            签名是否有效
        """
        try:
            # 提取签名
            sign = params.pop("sign", None)
            sign_type = params.pop("sign_type", None)
            
            if not sign:
                return False
            
            # 验证签名
            return self.alipay.verify(params, sign)
        
        except Exception as e:
            logger.error(f"支付宝签名验证失败: {str(e)}")
            return False
