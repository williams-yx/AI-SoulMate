"""
订单派发服务
在订单支付成功后自动分配到可用农场
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from services.farm_manager import farm_manager
from services.order_dispatch_strategy import (
    StrategyFactory,
    DEFAULT_STRATEGY,
    DEFAULT_STRATEGY_CONFIG
)
from logger import logger
import httpx


class OrderDispatcher:
    """订单派发器"""
    
    def __init__(self, strategy_name: str = DEFAULT_STRATEGY, strategy_config: Dict = None):
        """
        初始化订单派发器
        
        Args:
            strategy_name: 派送策略名称
            strategy_config: 策略配置参数
        """
        self.strategy_name = strategy_name
        self.strategy_config = strategy_config or DEFAULT_STRATEGY_CONFIG
        self.strategy = StrategyFactory.create_strategy(strategy_name, **self.strategy_config)
        logger.info(f"订单派发器初始化，使用策略: {self.strategy.get_strategy_name()}")
    
    async def dispatch_order(
        self,
        db: AsyncSession,
        order_id: str
    ) -> Dict[str, Any]:
        """
        派发订单到农场
        
        Args:
            db: 数据库会话
            order_id: 订单ID
        
        Returns:
            派发结果
        """
        try:
            # 1. 获取订单信息
            order_query = """
                SELECT o.id, o.user_id, o.total_amount,
                       po.asset_id, po.print_specs, po.estimated_weight,
                       a.model_url, a.prompt, a.image_url,
                       u.province, u.city
                FROM orders o
                JOIN print_orders po ON o.id = po.order_id
                JOIN assets a ON po.asset_id = a.id
                LEFT JOIN users u ON o.user_id = u.id
                WHERE o.id = :order_id
            """
            result = await db.execute(order_query, {"order_id": order_id})
            order = result.fetchone()
            
            if not order:
                logger.error(f"订单不存在: {order_id}")
                return {"success": False, "error": "订单不存在"}
            
            # 2. 解析打印规格
            import json
            print_specs = json.loads(order[4]) if isinstance(order[4], str) else order[4]
            material = print_specs.get('material', 'PLA')
            
            # 3. 查找所有可用农场
            available_farms = await farm_manager.get_available_farms(
                db=db,
                material=material
            )
            
            if not available_farms:
                logger.warning(f"没有可用农场，订单 {order_id} 等待分配")
                return {
                    "success": False,
                    "error": "暂无可用农场",
                    "status": "waiting"
                }
            
            # 4. 使用策略选择最优农场
            order_info = {
                'order_id': order_id,
                'user_province': order[9],
                'user_city': order[10],
                'material': material,
                'estimated_weight': float(order[5]),
                'total_amount': float(order[2])
            }
            
            farm = await self.strategy.select_farm(
                db=db,
                order_info=order_info,
                available_farms=available_farms
            )
            
            if not farm:
                logger.warning(f"策略未选择到合适农场，订单 {order_id} 等待分配")
                return {
                    "success": False,
                    "error": "未找到合适农场",
                    "status": "waiting"
                }
            
            # 5. 分配订单到农场
            await farm_manager.assign_order_to_farm(
                db=db,
                order_id=order_id,
                farm_id=farm['farm_id']
            )
            
            # 6. 通知农场（调用农场API）
            try:
                await self._notify_farm(
                    farm_api_endpoint=farm['api_endpoint'],
                    order_data={
                        "order_id": order_id,
                        "user_id": str(order[1]),
                        "asset_id": str(order[3]),
                        "model_url": order[6],
                        "prompt": order[7],
                        "image_url": order[8],
                        "print_specs": print_specs,
                        "estimated_weight": float(order[5]),
                        "total_amount": float(order[2])
                    }
                )
            except Exception as e:
                logger.error(f"通知农场失败: {str(e)}")
                # 通知失败不影响分配结果，农场会通过轮询获取订单
            
            logger.info(f"订单 {order_id} 已派发到农场 {farm['farm_name']}")
            
            return {
                "success": True,
                "farm_id": farm['farm_id'],
                "farm_name": farm['farm_name']
            }
        
        except Exception as e:
            logger.error(f"订单派发失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _notify_farm(
        self,
        farm_api_endpoint: str,
        order_data: Dict[str, Any]
    ):
        """
        通知农场有新订单
        
        Args:
            farm_api_endpoint: 农场API地址
            order_data: 订单数据
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{farm_api_endpoint}/api/orders/new",
                json=order_data
            )
            response.raise_for_status()


# 全局实例
order_dispatcher = OrderDispatcher()
