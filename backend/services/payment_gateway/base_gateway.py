"""
支付网关抽象基类
定义所有支付网关必须实现的接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BasePaymentGateway(ABC):
    """支付网关抽象基类"""
    
    def __init__(self, **config):
        """
        初始化支付网关
        
        Args:
            **config: 支付网关配置参数
        """
        self.config = config
    
    @abstractmethod
    def is_test_mode(self) -> bool:
        """
        检查是否为测试模式
        
        Returns:
            bool: True表示测试模式，False表示生产模式
        """
        pass
    
    @abstractmethod
    async def create_payment(
        self,
        amount: float,
        currency: str,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        创建支付
        
        Args:
            amount: 支付金额
            currency: 货币类型
            metadata: 元数据（如订单ID等）
            **kwargs: 其他参数（如回调URL等）
        
        Returns:
            Dict: 包含支付信息的字典
        """
        pass
    
    @abstractmethod
    async def confirm_payment(self, payment_id: str) -> bool:
        """
        确认支付是否成功
        
        Args:
            payment_id: 支付ID
        
        Returns:
            bool: 支付是否成功
        """
        pass
    
    @abstractmethod
    async def refund_payment(
        self,
        payment_id: str,
        amount: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        退款
        
        Args:
            payment_id: 支付ID
            amount: 退款金额（可选，不填则全额退款）
        
        Returns:
            Dict: 退款信息
        """
        pass
