"""
订单派送策略框架
支持多种派送策略，可根据业务需求灵活切换
"""
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
from logger import logger


class OrderDispatchStrategy(ABC):
    """订单派送策略基类"""
    
    @abstractmethod
    async def select_farm(
        self,
        db: Any,
        order_info: Dict[str, Any],
        available_farms: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        从可用农场中选择一个来处理订单
        
        Args:
            db: 数据库会话
            order_info: 订单信息
            available_farms: 可用农场列表
        
        Returns:
            选中的农场信息，如果没有合适的农场返回None
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """获取策略名称"""
        pass


class NearestLocationStrategy(OrderDispatchStrategy):
    """
    就近派送策略
    优先选择距离用户最近的农场
    """
    
    async def select_farm(
        self,
        db: Any,
        order_info: Dict[str, Any],
        available_farms: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        选择距离用户最近的农场
        
        优先级：
        1. 同城同区
        2. 同城不同区
        3. 同省不同城
        4. 不同省
        """
        if not available_farms:
            return None
        
        user_province = order_info.get('user_province')
        user_city = order_info.get('user_city')
        user_district = order_info.get('user_district')
        
        # TODO: 实现就近匹配算法
        # 当前简单实现：返回第一个同城农场，如果没有则返回第一个
        
        for farm in available_farms:
            if farm.get('city') == user_city and farm.get('province') == user_province:
                logger.info(f"就近策略：选择同城农场 {farm['farm_name']}")
                return farm
        
        # 如果没有同城农场，返回第一个可用农场
        logger.info(f"就近策略：无同城农场，选择 {available_farms[0]['farm_name']}")
        return available_farms[0]
    
    def get_strategy_name(self) -> str:
        return "nearest_location"


class LoadBalanceStrategy(OrderDispatchStrategy):
    """
    负载均衡策略
    根据农场当前负载情况分配订单
    """
    
    async def select_farm(
        self,
        db: Any,
        order_info: Dict[str, Any],
        available_farms: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        选择负载最低的农场
        
        负载计算：
        - 空闲打印机数量
        - 当前订单数量
        - 农场权重
        """
        if not available_farms:
            return None
        
        # TODO: 实现负载均衡算法
        # 当前简单实现：选择空闲打印机最多的农场
        
        best_farm = max(available_farms, key=lambda f: f.get('idle_printers', 0))
        logger.info(f"负载均衡策略：选择农场 {best_farm['farm_name']}（空闲打印机: {best_farm.get('idle_printers', 0)}）")
        return best_farm
    
    def get_strategy_name(self) -> str:
        return "load_balance"


class PriorityStrategy(OrderDispatchStrategy):
    """
    优先级策略
    根据农场优先级分配订单
    """
    
    async def select_farm(
        self,
        db: Any,
        order_info: Dict[str, Any],
        available_farms: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        选择优先级最高的农场
        
        优先级因素：
        - 农场设置的优先级
        - 农场历史完成率
        - 农场评分
        """
        if not available_farms:
            return None
        
        # TODO: 实现优先级算法
        # 当前简单实现：选择priority字段最大的农场
        
        best_farm = max(available_farms, key=lambda f: f.get('priority', 0))
        logger.info(f"优先级策略：选择农场 {best_farm['farm_name']}（优先级: {best_farm.get('priority', 0)}）")
        return best_farm
    
    def get_strategy_name(self) -> str:
        return "priority"


class MaterialMatchStrategy(OrderDispatchStrategy):
    """
    材质匹配策略
    根据订单所需材质选择支持该材质的农场
    """
    
    async def select_farm(
        self,
        db: Any,
        order_info: Dict[str, Any],
        available_farms: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        选择支持所需材质的农场
        
        匹配规则：
        - 必须支持订单所需材质
        - 在支持的农场中选择最优的
        """
        if not available_farms:
            return None
        
        required_material = order_info.get('material', 'PLA')
        
        # TODO: 实现材质匹配算法
        # 当前简单实现：返回第一个农场（假设都支持）
        
        logger.info(f"材质匹配策略：订单需要 {required_material}，选择 {available_farms[0]['farm_name']}")
        return available_farms[0]
    
    def get_strategy_name(self) -> str:
        return "material_match"


class CompositeStrategy(OrderDispatchStrategy):
    """
    组合策略
    综合多个因素进行评分，选择得分最高的农场
    """
    
    def __init__(
        self,
        location_weight: float = 0.4,
        load_weight: float = 0.3,
        priority_weight: float = 0.2,
        quality_weight: float = 0.1
    ):
        """
        初始化组合策略
        
        Args:
            location_weight: 地理位置权重
            load_weight: 负载权重
            priority_weight: 优先级权重
            quality_weight: 质量评分权重
        """
        self.location_weight = location_weight
        self.load_weight = load_weight
        self.priority_weight = priority_weight
        self.quality_weight = quality_weight
    
    async def select_farm(
        self,
        db: Any,
        order_info: Dict[str, Any],
        available_farms: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        综合评分选择农场
        
        评分因素：
        - 地理位置得分（距离越近得分越高）
        - 负载得分（空闲打印机越多得分越高）
        - 优先级得分（优先级越高得分越高）
        - 质量得分（历史完成率、评分等）
        """
        if not available_farms:
            return None
        
        # TODO: 实现综合评分算法
        # 当前简单实现：返回第一个农场
        
        best_farm = available_farms[0]
        best_score = 0.0
        
        for farm in available_farms:
            # 计算各项得分（0-100分）
            location_score = self._calculate_location_score(order_info, farm)
            load_score = self._calculate_load_score(farm)
            priority_score = self._calculate_priority_score(farm)
            quality_score = self._calculate_quality_score(farm)
            
            # 加权总分
            total_score = (
                location_score * self.location_weight +
                load_score * self.load_weight +
                priority_score * self.priority_weight +
                quality_score * self.quality_weight
            )
            
            if total_score > best_score:
                best_score = total_score
                best_farm = farm
        
        logger.info(f"组合策略：选择农场 {best_farm['farm_name']}（综合得分: {best_score:.2f}）")
        return best_farm
    
    def _calculate_location_score(self, order_info: Dict[str, Any], farm: Dict[str, Any]) -> float:
        """计算地理位置得分"""
        # TODO: 实现地理位置评分算法
        user_city = order_info.get('user_city')
        farm_city = farm.get('city')
        
        if user_city == farm_city:
            return 100.0  # 同城满分
        
        user_province = order_info.get('user_province')
        farm_province = farm.get('province')
        
        if user_province == farm_province:
            return 70.0  # 同省70分
        
        return 30.0  # 不同省30分
    
    def _calculate_load_score(self, farm: Dict[str, Any]) -> float:
        """计算负载得分"""
        # TODO: 实现负载评分算法
        idle_printers = farm.get('idle_printers', 0)
        total_printers = farm.get('total_printers', 1)
        
        if total_printers == 0:
            return 0.0
        
        # 空闲率越高得分越高
        idle_rate = idle_printers / total_printers
        return idle_rate * 100.0
    
    def _calculate_priority_score(self, farm: Dict[str, Any]) -> float:
        """计算优先级得分"""
        # TODO: 实现优先级评分算法
        priority = farm.get('priority', 0)
        # 假设优先级范围是0-10，转换为0-100分
        return min(priority * 10, 100.0)
    
    def _calculate_quality_score(self, farm: Dict[str, Any]) -> float:
        """计算质量得分"""
        # TODO: 实现质量评分算法
        # 基于历史完成率、用户评分等
        completed_orders = farm.get('completed_orders', 0)
        total_orders = farm.get('total_orders', 0)
        
        if total_orders == 0:
            return 80.0  # 新农场给80分
        
        completion_rate = completed_orders / total_orders
        return completion_rate * 100.0
    
    def get_strategy_name(self) -> str:
        return "composite"


class RoundRobinStrategy(OrderDispatchStrategy):
    """
    轮询策略
    按顺序轮流分配订单到各个农场
    """
    
    def __init__(self):
        self.last_farm_index = -1
    
    async def select_farm(
        self,
        db: Any,
        order_info: Dict[str, Any],
        available_farms: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        轮询选择农场
        """
        if not available_farms:
            return None
        
        # TODO: 实现轮询算法（需要持久化状态）
        # 当前简单实现：顺序选择
        
        self.last_farm_index = (self.last_farm_index + 1) % len(available_farms)
        selected_farm = available_farms[self.last_farm_index]
        
        logger.info(f"轮询策略：选择农场 {selected_farm['farm_name']}（索引: {self.last_farm_index}）")
        return selected_farm
    
    def get_strategy_name(self) -> str:
        return "round_robin"


class StrategyFactory:
    """策略工厂"""
    
    _strategies = {
        'nearest_location': NearestLocationStrategy,
        'load_balance': LoadBalanceStrategy,
        'priority': PriorityStrategy,
        'material_match': MaterialMatchStrategy,
        'composite': CompositeStrategy,
        'round_robin': RoundRobinStrategy,
    }
    
    @classmethod
    def create_strategy(cls, strategy_name: str, **kwargs) -> OrderDispatchStrategy:
        """
        创建策略实例
        
        Args:
            strategy_name: 策略名称
            **kwargs: 策略参数
        
        Returns:
            策略实例
        """
        strategy_class = cls._strategies.get(strategy_name)
        
        if not strategy_class:
            logger.warning(f"未知策略 {strategy_name}，使用默认组合策略")
            strategy_class = CompositeStrategy
        
        return strategy_class(**kwargs)
    
    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """获取所有可用策略名称"""
        return list(cls._strategies.keys())
    
    @classmethod
    def register_strategy(cls, name: str, strategy_class: type):
        """
        注册自定义策略
        
        Args:
            name: 策略名称
            strategy_class: 策略类
        """
        if not issubclass(strategy_class, OrderDispatchStrategy):
            raise ValueError("策略类必须继承自 OrderDispatchStrategy")
        
        cls._strategies[name] = strategy_class
        logger.info(f"注册自定义策略: {name}")


# 默认策略配置
DEFAULT_STRATEGY = 'composite'
DEFAULT_STRATEGY_CONFIG = {
    'location_weight': 0.4,
    'load_weight': 0.3,
    'priority_weight': 0.2,
    'quality_weight': 0.1
}
