"""
订单派送配置
可以通过环境变量或配置文件修改派送策略
"""
import os
from typing import Dict, Any


class DispatchConfig:
    """派送配置类"""
    
    # 默认策略
    DEFAULT_STRATEGY = os.getenv('DISPATCH_STRATEGY', 'composite')
    
    # 策略配置
    STRATEGY_CONFIGS = {
        # 组合策略配置
        'composite': {
            'location_weight': float(os.getenv('DISPATCH_LOCATION_WEIGHT', '0.4')),
            'load_weight': float(os.getenv('DISPATCH_LOAD_WEIGHT', '0.3')),
            'priority_weight': float(os.getenv('DISPATCH_PRIORITY_WEIGHT', '0.2')),
            'quality_weight': float(os.getenv('DISPATCH_QUALITY_WEIGHT', '0.1')),
        },
        
        # 其他策略配置（如需要）
        'nearest_location': {},
        'load_balance': {},
        'priority': {},
        'material_match': {},
        'round_robin': {},
    }
    
    @classmethod
    def get_strategy_name(cls) -> str:
        """获取当前使用的策略名称"""
        return cls.DEFAULT_STRATEGY
    
    @classmethod
    def get_strategy_config(cls, strategy_name: str = None) -> Dict[str, Any]:
        """
        获取策略配置
        
        Args:
            strategy_name: 策略名称，如果为None则使用默认策略
        
        Returns:
            策略配置字典
        """
        if strategy_name is None:
            strategy_name = cls.DEFAULT_STRATEGY
        
        return cls.STRATEGY_CONFIGS.get(strategy_name, {})
    
    @classmethod
    def set_strategy(cls, strategy_name: str, config: Dict[str, Any] = None):
        """
        动态设置策略
        
        Args:
            strategy_name: 策略名称
            config: 策略配置
        """
        cls.DEFAULT_STRATEGY = strategy_name
        if config:
            cls.STRATEGY_CONFIGS[strategy_name] = config


# 预设配置方案

# 方案1: 优先就近派送（适合物流成本敏感的场景）
LOCATION_FIRST_CONFIG = {
    'strategy': 'composite',
    'config': {
        'location_weight': 0.6,
        'load_weight': 0.2,
        'priority_weight': 0.1,
        'quality_weight': 0.1,
    }
}

# 方案2: 优先负载均衡（适合高峰期）
LOAD_BALANCE_FIRST_CONFIG = {
    'strategy': 'composite',
    'config': {
        'location_weight': 0.2,
        'load_weight': 0.5,
        'priority_weight': 0.2,
        'quality_weight': 0.1,
    }
}

# 方案3: 优先质量（适合重要订单）
QUALITY_FIRST_CONFIG = {
    'strategy': 'composite',
    'config': {
        'location_weight': 0.2,
        'load_weight': 0.2,
        'priority_weight': 0.2,
        'quality_weight': 0.4,
    }
}

# 方案4: 纯就近派送
NEAREST_ONLY_CONFIG = {
    'strategy': 'nearest_location',
    'config': {}
}

# 方案5: 纯负载均衡
LOAD_BALANCE_ONLY_CONFIG = {
    'strategy': 'load_balance',
    'config': {}
}


def apply_preset_config(preset_name: str):
    """
    应用预设配置
    
    Args:
        preset_name: 预设名称
            - 'location_first': 优先就近
            - 'load_balance_first': 优先负载均衡
            - 'quality_first': 优先质量
            - 'nearest_only': 纯就近
            - 'load_balance_only': 纯负载均衡
    """
    presets = {
        'location_first': LOCATION_FIRST_CONFIG,
        'load_balance_first': LOAD_BALANCE_FIRST_CONFIG,
        'quality_first': QUALITY_FIRST_CONFIG,
        'nearest_only': NEAREST_ONLY_CONFIG,
        'load_balance_only': LOAD_BALANCE_ONLY_CONFIG,
    }
    
    preset = presets.get(preset_name)
    if preset:
        DispatchConfig.set_strategy(preset['strategy'], preset['config'])
        return True
    return False
