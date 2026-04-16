"""
与前端一致的「无操作会话」滑动窗口：依赖 Redis TTL，每次受保护请求刷新 15 分钟。
Redis 不可用时跳过校验（与现有验证码等降级策略一致），仅依赖 JWT。
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from config import Config

KEY_PREFIX = "session:idle:"


def _key(user_id: str) -> str:
    return f"{KEY_PREFIX}{user_id}"


def _cache(request: Request):
    st = request.app.state
    return getattr(st, "cache", None), bool(getattr(st, "cache_connected", False))


def idle_ttl_seconds() -> int:
    return int(getattr(Config, "SESSION_IDLE_SECONDS", 900))


def register_login_session(request: Request, user_id: str) -> None:
    """登录/注册成功下发 JWT 后调用：开始滑动窗口。"""
    cache, ok = _cache(request)
    if not ok or cache is None or not cache.is_connected():
        return
    cache.set(_key(str(user_id)), "1", expire_seconds=idle_ttl_seconds())


def clear_session_idle(request: Request, user_id: str) -> None:
    """显式登出：删除滑动窗口键，使旧 JWT 在下次受保护请求时 401。"""
    cache, ok = _cache(request)
    if not ok or cache is None or not cache.is_connected():
        return
    cache.delete(_key(str(user_id)))


def ensure_sliding_session_or_401(request: Request, user_id: str) -> None:
    """
    受保护接口：Redis 可用时要求键存在（登录后曾建立），否则 401；
    通过后刷新 TTL。
    """
    cache, connected = _cache(request)
    if not connected or cache is None or not cache.is_connected():
        return
    uid = str(user_id)
    k = _key(uid)
    if not cache.exists(k):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="会话已失效，请重新登录（长时间无操作）",
            headers={"WWW-Authenticate": "Bearer"},
        )
    cache.set(k, "1", expire_seconds=idle_ttl_seconds())


def optional_sliding_session_touch(request: Request, user_id: str) -> bool:
    """
    可选登录：键不存在视为未登录（返回 None）；存在则刷新 TTL。
    Redis 不可用时返回 True（不挡 JWT）。
    """
    cache, connected = _cache(request)
    if not connected or cache is None or not cache.is_connected():
        return True
    uid = str(user_id)
    k = _key(uid)
    if not cache.exists(k):
        return False
    cache.set(k, "1", expire_seconds=idle_ttl_seconds())
    return True
