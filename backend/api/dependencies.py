"""
API依赖注入
包含认证、权限验证等依赖
"""

from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, Optional
from core.security import AuthManager
from core.points import maybe_refresh_free_points, total_points
from core import session_idle


security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    获取当前登录用户
    
    Args:
        credentials: HTTP Bearer token凭证
        request: FastAPI请求对象
    
    Returns:
        用户信息字典
    """
    token = credentials.credentials
    payload = AuthManager.verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session_idle.ensure_sliding_session_or_401(request, str(payload.get("sub")))

    app_state = request.app.state
    if not hasattr(app_state, 'db_connected') or not app_state.db_connected:
        raise HTTPException(status_code=503, detail="数据库未连接")
    
    # 从数据库获取用户信息（含 free/redeemed/gift/paid；列可能尚未迁移则用 points）
    try:
        user_data = await app_state.db.fetchrow(
            "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, redeemed_points, paid_points, gift_points, free_points_refreshed_at, role, is_active, created_at FROM users WHERE id = $1",
            payload.get("sub"),
        )
    except Exception:
        user_data = await app_state.db.fetchrow(
            "SELECT id, nickname, avatar, primary_email, primary_phone, points, role, is_active, created_at FROM users WHERE id = $1",
            payload.get("sub"),
        )
    if user_data is None:
        raise HTTPException(status_code=404, detail="User not found")

    u = dict(user_data)
    # 若已迁移双轨积分：免费积分用尽且满 24 小时则刷新为 1000
    if "free_points_refreshed_at" in u or "free_points" in u:
        await maybe_refresh_free_points(app_state.db, str(payload.get("sub")))
        user_data = await app_state.db.fetchrow(
            "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, redeemed_points, paid_points, gift_points, free_points_refreshed_at, role, is_active, created_at FROM users WHERE id = $1",
            payload.get("sub"),
        )
        u = dict(user_data) if user_data else u
    # 兼容前端字段名
    u["username"] = u.get("nickname") or ""
    u["email"] = u.get("primary_email")
    u["phone"] = u.get("primary_phone")
    u["credits"] = total_points(u)
    # 区分 0 与 None：free_points=0 时不应回退到 points，否则重置账号会误把付费当免费显示
    u["free_credits"] = int(u.get("free_points") if u.get("free_points") is not None else (u.get("points") or 0))
    u["redeemed_credits"] = int(u.get("redeemed_points") or 0)
    u["paid_credits"] = int(u.get("paid_points") if u.get("paid_points") is not None else (u.get("points") or 0))
    u["gift_credits"] = int(u.get("gift_points") or 0)
    # 供前端显示免费积分刷新倒计时（ISO 字符串）
    ref_at = u.get("free_points_refreshed_at")
    u["free_points_refreshed_at"] = ref_at.isoformat() if ref_at and getattr(ref_at, "isoformat", None) else (str(ref_at) if ref_at else None)
    return u


async def get_current_user_optional(
    request: Request,
) -> Optional[Dict[str, Any]]:
    """
    尝试获取当前登录用户，未登录时返回 None（不会抛出 401）
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return None

    token = auth_header.split(" ", 1)[1].strip()
    payload = AuthManager.verify_token(token)
    if payload is None:
        return None

    if not session_idle.optional_sliding_session_touch(request, str(payload.get("sub"))):
        return None

    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        return None

    user_data = await app_state.db.fetchrow(
        "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, redeemed_points, paid_points, gift_points, role, is_active, created_at FROM users WHERE id = $1",
        payload.get("sub"),
    )
    if user_data is None:
        return None
    u = dict(user_data)
    u["username"] = u.get("nickname") or ""
    u["email"] = u.get("primary_email")
    u["phone"] = u.get("primary_phone")
    u["credits"] = total_points(u)
    u["free_credits"] = int(u.get("free_points") if u.get("free_points") is not None else (u.get("points") or 0))
    u["redeemed_credits"] = int(u.get("redeemed_points") or 0)
    u["paid_credits"] = int(u.get("paid_points") if u.get("paid_points") is not None else (u.get("points") or 0))
    u["gift_credits"] = int(u.get("gift_points") or 0)
    return u


async def get_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    验证当前用户是否为管理员
    
    Args:
        current_user: 当前用户信息
    
    Returns:
        管理员用户信息
    """
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# 导出
__all__ = ["security", "get_current_user", "get_current_user_optional", "get_admin_user"]
