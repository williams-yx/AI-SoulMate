"""
API 路由模块
包含所有 API 路由
"""

# 延迟导入以避免循环依赖


def get_auth_router():
    from .auth import router as auth_router

    return auth_router


def get_projects_router():
    from .projects import router as projects_router

    return projects_router


def get_assets_router():
    from .assets import router as assets_router

    return assets_router


def get_community_router():
    from .community import router as community_router

    return community_router


def get_orders_router():
    from .orders import router as orders_router

    return orders_router


def get_address_router():
    from .address import router as address_router

    return address_router


def get_workflow_router():
    from .workflow import router as workflow_router

    return workflow_router


def get_admin_router():
    from .admin import router as admin_router

    return admin_router


def get_admin_html_router():
    from .admin import admin_html_router

    return admin_html_router


# 导出依赖
from .dependencies import get_current_user, get_admin_user, security

# 导出所有路由及依赖
__all__ = [
    "get_auth_router",
    "get_projects_router",
    "get_assets_router",
    "get_community_router",
    "get_orders_router",
    "get_address_router",
    "get_workflow_router",
    "get_admin_router",
    "get_admin_html_router",
    "get_current_user",
    "get_admin_user",
    "security",
]

