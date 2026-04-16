"""
订单派送管理API
供管理员查看和配置派送策略
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from services.order_dispatch_strategy import StrategyFactory
from dispatch_config import DispatchConfig, apply_preset_config
from logger import logger


router = APIRouter(prefix="/api/admin/dispatch", tags=["订单派送管理"])


class StrategyConfigRequest(BaseModel):
    """策略配置请求"""
    strategy_name: str
    config: Optional[Dict[str, Any]] = None


class PresetConfigRequest(BaseModel):
    """预设配置请求"""
    preset_name: str


# ============ 查询接口 ============

@router.get("/strategies")
async def get_available_strategies():
    """
    获取所有可用的派送策略
    
    Returns:
        策略列表及说明
    """
    strategies = StrategyFactory.get_available_strategies()
    
    strategy_info = {
        'nearest_location': {
            'name': '就近派送策略',
            'description': '优先选择距离用户最近的农场',
            'suitable_for': '物流成本敏感的场景'
        },
        'load_balance': {
            'name': '负载均衡策略',
            'description': '根据农场当前负载情况分配订单',
            'suitable_for': '高峰期或需要均衡负载的场景'
        },
        'priority': {
            'name': '优先级策略',
            'description': '根据农场优先级分配订单',
            'suitable_for': '有明确农场优先级的场景'
        },
        'material_match': {
            'name': '材质匹配策略',
            'description': '根据订单所需材质选择支持该材质的农场',
            'suitable_for': '材质要求严格的场景'
        },
        'composite': {
            'name': '组合策略',
            'description': '综合多个因素进行评分，选择得分最高的农场',
            'suitable_for': '大多数场景（推荐）'
        },
        'round_robin': {
            'name': '轮询策略',
            'description': '按顺序轮流分配订单到各个农场',
            'suitable_for': '需要绝对公平分配的场景'
        }
    }
    
    result = []
    for strategy in strategies:
        info = strategy_info.get(strategy, {
            'name': strategy,
            'description': '自定义策略',
            'suitable_for': '特定场景'
        })
        result.append({
            'strategy_name': strategy,
            **info
        })
    
    return {
        'strategies': result,
        'current_strategy': DispatchConfig.get_strategy_name()
    }


@router.get("/current-config")
async def get_current_config():
    """
    获取当前派送策略配置
    
    Returns:
        当前策略名称和配置
    """
    strategy_name = DispatchConfig.get_strategy_name()
    config = DispatchConfig.get_strategy_config(strategy_name)
    
    return {
        'strategy_name': strategy_name,
        'config': config
    }


@router.get("/presets")
async def get_preset_configs():
    """
    获取预设配置方案
    
    Returns:
        所有预设配置
    """
    presets = [
        {
            'name': 'location_first',
            'display_name': '优先就近派送',
            'description': '适合物流成本敏感的场景',
            'strategy': 'composite',
            'weights': {
                'location': 0.6,
                'load': 0.2,
                'priority': 0.1,
                'quality': 0.1
            }
        },
        {
            'name': 'load_balance_first',
            'display_name': '优先负载均衡',
            'description': '适合高峰期，均衡各农场负载',
            'strategy': 'composite',
            'weights': {
                'location': 0.2,
                'load': 0.5,
                'priority': 0.2,
                'quality': 0.1
            }
        },
        {
            'name': 'quality_first',
            'display_name': '优先质量',
            'description': '适合重要订单，选择质量最好的农场',
            'strategy': 'composite',
            'weights': {
                'location': 0.2,
                'load': 0.2,
                'priority': 0.2,
                'quality': 0.4
            }
        },
        {
            'name': 'nearest_only',
            'display_name': '纯就近派送',
            'description': '只考虑地理位置，不考虑其他因素',
            'strategy': 'nearest_location',
            'weights': None
        },
        {
            'name': 'load_balance_only',
            'display_name': '纯负载均衡',
            'description': '只考虑负载，不考虑其他因素',
            'strategy': 'load_balance',
            'weights': None
        }
    ]
    
    return {
        'presets': presets,
        'current_strategy': DispatchConfig.get_strategy_name()
    }


# ============ 配置接口 ============

@router.post("/set-strategy")
async def set_dispatch_strategy(request: StrategyConfigRequest):
    """
    设置派送策略
    
    Args:
        request: 策略配置请求
    
    Returns:
        设置结果
    """
    try:
        # 验证策略是否存在
        available_strategies = StrategyFactory.get_available_strategies()
        if request.strategy_name not in available_strategies:
            raise HTTPException(
                status_code=400,
                detail=f"未知策略: {request.strategy_name}，可用策略: {', '.join(available_strategies)}"
            )
        
        # 设置策略
        DispatchConfig.set_strategy(request.strategy_name, request.config)
        
        logger.info(f"派送策略已更新: {request.strategy_name}")
        
        return {
            'success': True,
            'message': '策略设置成功',
            'strategy_name': request.strategy_name,
            'config': request.config
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置策略失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply-preset")
async def apply_preset(request: PresetConfigRequest):
    """
    应用预设配置
    
    Args:
        request: 预设配置请求
    
    Returns:
        应用结果
    """
    try:
        success = apply_preset_config(request.preset_name)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"未知预设: {request.preset_name}"
            )
        
        logger.info(f"已应用预设配置: {request.preset_name}")
        
        return {
            'success': True,
            'message': '预设配置应用成功',
            'preset_name': request.preset_name,
            'current_strategy': DispatchConfig.get_strategy_name()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"应用预设配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 测试接口 ============

@router.post("/test-strategy")
async def test_strategy(
    strategy_name: str,
    order_info: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None
):
    """
    测试派送策略
    
    模拟订单派送，查看会选择哪个农场
    
    Args:
        strategy_name: 策略名称
        order_info: 订单信息
        config: 策略配置（可选）
    
    Returns:
        测试结果
    """
    try:
        # TODO: 实现策略测试逻辑
        # 1. 获取可用农场列表
        # 2. 使用指定策略选择农场
        # 3. 返回选择结果和评分详情
        
        return {
            'success': True,
            'message': '策略测试功能待实现',
            'strategy_name': strategy_name,
            'order_info': order_info
        }
    
    except Exception as e:
        logger.error(f"测试策略失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
