"""
认证相关的API路由
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, Optional
from pydantic import BaseModel
import base64
import io
import random
import re
import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.utils import formataddr
from urllib.parse import urlencode
import smtplib
import asyncio
import json

import aiohttp
import asyncpg

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from schemas import UserCreate, UserLogin, AdminLogin
from auth import hash_password, verify_password
from core.security import AuthManager
from core.points import FREE_POINTS_REFRESH_AMOUNT
from core import session_idle
from config import Config
from logger import logger
from .dependencies import get_current_user
from cache import get_cache_manager

router = APIRouter(prefix="/api/auth", tags=["认证"])

# 验证码存储（临时，生产环境应使用Redis）
verification_codes: Dict[str, Dict[str, Any]] = {}

# 图形验证码存储（Redis 不可用时使用内存）
captcha_store: Dict[str, str] = {}

# 图形验证码连续失败锁定：5 次失败锁 15 分钟
CAPTCHA_MAX_FAIL = 5
CAPTCHA_LOCK_SECONDS = 15 * 60  # 900
# 失败次数/锁定状态存储（Redis 不可用时使用内存，key=ip）
captcha_fail_store: Dict[str, Dict[str, Any]] = {}

# 图形验证码字符集（去除易混淆的 0/O、1/l/I 等）
CAPTCHA_CHARS = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def _count_password_categories(password: str) -> int:
    """统计密码包含的字符类别数：大写/小写/数字/符号。"""
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    return sum([has_upper, has_lower, has_digit, has_symbol])


def _validate_password_security_or_raise(password: str, min_categories: int = 2) -> None:
    """密码安全规则：至少6位，且包含四类中的至少 min_categories 类。"""
    if len(password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码长度至少6位")
    if _count_password_categories(password) < min_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"密码安全等级不足：请至少包含{min_categories}类字符（大写/小写/数字/符号）",
        )


def _client_ip(request: Request) -> str:
    """获取客户端 IP（兼容反向代理 X-Forwarded-For）。"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or "0.0.0.0"
    return "0.0.0.0"


def _get_captcha_fail_state(request: Request) -> tuple[bool, int, int]:
    """返回 (是否已锁定, 当前失败次数, 剩余可试次数)。"""
    app_state = request.app.state
    cache = getattr(app_state, "cache", None)
    cache_connected = getattr(app_state, "cache_connected", False)
    ip = _client_ip(request)
    key = f"captcha_fail:{ip}"
    now = datetime.now(timezone.utc)
    data = None
    if cache_connected and cache:
        raw = cache.get(key)
        if isinstance(raw, str):
            try:
                data = json.loads(raw)
            except Exception:
                data = {}
        elif isinstance(raw, dict):
            data = raw
    else:
        data = captcha_fail_store.get(ip, {})
    if not data or not isinstance(data, dict):
        return False, 0, CAPTCHA_MAX_FAIL
    try:
        count = int(data.get("count") or 0)
    except (TypeError, ValueError):
        count = 0
    locked_until = data.get("locked_until")
    if locked_until:
        try:
            if isinstance(locked_until, str):
                s = locked_until.replace("Z", "+00:00")
                until = datetime.fromisoformat(s)
            else:
                until = locked_until
            if until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)
            if now < until:
                return True, count, 0
        except Exception:
            pass
    remaining = max(0, CAPTCHA_MAX_FAIL - count)
    return False, count, remaining


def _get_captcha_lock_until(request: Request) -> Optional[datetime]:
    """若当前 IP 处于图形验证码锁定期，返回锁定截止时间 (UTC)；否则返回 None。"""
    app_state = request.app.state
    cache = getattr(app_state, "cache", None)
    cache_connected = getattr(app_state, "cache_connected", False)
    ip = _client_ip(request)
    key = f"captcha_fail:{ip}"
    now = datetime.now(timezone.utc)
    data = None
    if cache_connected and cache:
        raw = cache.get(key)
        if isinstance(raw, str):
            try:
                data = json.loads(raw)
            except Exception:
                data = {}
        elif isinstance(raw, dict):
            data = raw
    else:
        data = captcha_fail_store.get(ip, {})
    if not data or not isinstance(data, dict):
        return None
    locked_until = data.get("locked_until")
    if not locked_until:
        return None
    try:
        if isinstance(locked_until, str):
            s = locked_until.replace("Z", "+00:00")
            until = datetime.fromisoformat(s)
        else:
            until = locked_until
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        if now < until:
            return until
    except Exception:
        pass
    return None


def _record_captcha_fail(request: Request) -> tuple[bool, str]:
    """记录一次图形验证码失败，返回 (是否已锁定, 提示文案)。"""
    app_state = request.app.state
    cache = getattr(app_state, "cache", None)
    cache_connected = getattr(app_state, "cache_connected", False)
    ip = _client_ip(request)
    key = f"captcha_fail:{ip}"
    locked, count, _ = _get_captcha_fail_state(request)
    if locked:
        return True, "请15分钟后再试"
    count += 1
    now = datetime.now(timezone.utc)
    if count >= CAPTCHA_MAX_FAIL:
        locked_until = now + timedelta(seconds=CAPTCHA_LOCK_SECONDS)
        data = {"count": count, "locked_until": locked_until.isoformat()}
        if cache_connected and cache:
            cache.set(key, json.dumps(data), expire_seconds=CAPTCHA_LOCK_SECONDS)
        else:
            captcha_fail_store[ip] = data
        return True, "请15分钟后再试"
    data = {"count": count, "locked_until": None}
    if cache_connected and cache:
        cache.set(key, json.dumps(data), expire_seconds=CAPTCHA_LOCK_SECONDS)
    else:
        captcha_fail_store[ip] = data
    remaining = max(0, CAPTCHA_MAX_FAIL - count)
    return False, f"图形验证码错误，还有{remaining}次机会"


def _clear_captcha_fail(request: Request) -> None:
    """验证码校验成功后清除该 IP 的失败计数与锁定。"""
    app_state = request.app.state
    cache = getattr(app_state, "cache", None)
    cache_connected = getattr(app_state, "cache_connected", False)
    ip = _client_ip(request)
    key = f"captcha_fail:{ip}"
    if cache_connected and cache:
        cache.delete(key)
    else:
        captcha_fail_store.pop(ip, None)


def _get_code_from_stored(stored: Any) -> str | None:
    """从缓存返回的验证码结构中取出 code 字符串（兼容 dict 与 str）。"""
    if stored is None:
        return None
    if isinstance(stored, dict):
        return stored.get("code")
    return str(stored) if stored else None


def _user_response(user_row: Any) -> Dict[str, Any]:
    """从 users 表一行转为 API 返回的 user 对象；含免费/兑换/赠送/付费积分。"""
    if not user_row:
        return {}
    u = dict(user_row)
    free = int(u.get("free_points") if u.get("free_points") is not None else u.get("points") or 0)
    redeemed = int(u.get("redeemed_points") or 0)
    paid = int(u.get("paid_points") or 0)
    gift = int(u.get("gift_points") or 0)
    if (
        u.get("free_points") is not None
        or u.get("redeemed_points") is not None
        or u.get("paid_points") is not None
        or u.get("gift_points") is not None
    ):
        total = free + redeemed + gift + paid
    else:
        total = int(
            u.get("points") if u.get("points") is not None else u.get("credits", FREE_POINTS_REFRESH_AMOUNT)
        )
    ref_at = u.get("free_points_refreshed_at")
    return {
        "id": str(u["id"]),
        "username": u.get("nickname") or u.get("username") or "",
        "email": u.get("primary_email") if u.get("primary_email") is not None else u.get("email"),
        "phone": u.get("primary_phone") if u.get("primary_phone") is not None else u.get("phone"),
        "credits": int(total),
        "free_credits": free,
        "redeemed_credits": redeemed,
        "paid_credits": paid,
        "gift_credits": gift,
        "free_points_refreshed_at": ref_at.isoformat() if ref_at and getattr(ref_at, "isoformat", None) else (str(ref_at) if ref_at else None),
        "avatar": u.get("avatar"),
        "role": u.get("role", "student"),
    }


def _normalize_profile_nickname(raw: Optional[str]) -> Optional[str]:
    """个人中心显示名称：去首尾空格，最长 100。"""
    if raw is None:
        return None
    s = (raw or "").strip()[:100]
    return s or None


async def _profile_display_name_taken_by_other(
    db: Any, nickname: str, exclude_user_id: str
) -> bool:
    """是否已有其他用户使用相同显示名（不区分大小写，比较前 trim）。"""
    n = _normalize_profile_nickname(nickname)
    if not n:
        return False
    row = await db.fetchrow(
        """
        SELECT id FROM users
        WHERE id <> $1::uuid
          AND lower(trim(nickname)) = lower($2::text)
        LIMIT 1
        """,
        exclude_user_id,
        n,
    )
    return row is not None


async def _allocate_unique_display_nickname_for_new_user(db: Any, base: str) -> str:
    """为新用户分配不与现有显示名冲突的 nickname（不区分大小写）；冲突时自动加随机后缀。"""
    base = _normalize_profile_nickname(base) or "用户"
    candidate = base
    for _ in range(64):
        row = await db.fetchrow(
            "SELECT 1 FROM users WHERE lower(trim(nickname)) = lower($1::text) LIMIT 1",
            candidate,
        )
        if not row:
            return candidate
        suf = "_" + secrets.token_hex(3)
        candidate = (base[: max(1, 100 - len(suf))] + suf)[:100]
    return (base[:60] + "_" + secrets.token_hex(8))[:100]


PROVIDER_LABELS = {"account": "账号", "email": "邮箱", "phone": "手机", "wechat": "微信", "github": "GitHub"}


def _github_oauth_identifier_from_api(user_dict: Any) -> Optional[str]:
    """GitHub /user JSON 的 id 统一为十进制字符串，避免 bind / login / register 路径 identifier 不一致导致查不到已绑定身份。"""
    if not isinstance(user_dict, dict):
        return None
    raw = user_dict.get("id")
    if raw is None:
        return None
    try:
        return str(int(raw))
    except (TypeError, ValueError):
        s = str(raw).strip()
        return s or None


def _dev_github_identifier_from_code(code: str) -> str:
    """
    OAuth 无法得到真实 GitHub 数字 id 时的占位 identifier（github-login / bind-github / 注册等共用）。
    不得使用本次 authorization code 切片：code 每次授权都不同，会导致「账号登录绑定 GitHub」与「GitHub 登录」
    写入不同 identifier，JWT 落到不同用户，个人中心看不到原绑定。
    """
    return (getattr(Config, "DEV_GITHUB_OAUTH_IDENTITY", None) or "dev_github_local_oauth_user").strip()


def _github_oauth_secrets_configured() -> bool:
    """已配置 client_id + secret 时，绑定/注册不得以占位 GitHub id 冒充成功，否则与真实 GitHub 登录 id 不一致。"""
    return bool((Config.GITHUB_CLIENT_ID or "").strip() and (Config.GITHUB_CLIENT_SECRET or "").strip())


def _github_oauth_token_request_body(code: str, redirect_uri: Optional[str]) -> Dict[str, str]:
    """
    换取 GitHub access_token 的表单字段。
    授权请求里若带了 redirect_uri，此处必须传**完全相同**的字符串，否则在多回调 URL 场景下可能换票失败或行为异常。
    """
    body: Dict[str, str] = {
        "client_id": (Config.GITHUB_CLIENT_ID or "").strip(),
        "client_secret": (Config.GITHUB_CLIENT_SECRET or "").strip(),
        "code": code,
    }
    r = (redirect_uri or "").strip()
    if r:
        body["redirect_uri"] = r
    return body


async def _lookup_user_id_by_github_identifier(db: Any, github_id: str) -> Optional[str]:
    """按 GitHub 数字 id 查找已绑定的 user_id；兼容历史库中纯数字 identifier 的多种字符串形式。"""
    gid = (github_id or "").strip()
    if not gid:
        return None
    variants: list[str] = [gid]
    if gid.isdigit():
        n = str(int(gid))
        if n not in variants:
            variants.append(n)
    seen: set[str] = set()
    for v in variants:
        if not v or v in seen:
            continue
        seen.add(v)
        row = await db.fetchrow(
            "SELECT user_id FROM user_identities WHERE provider = 'github' AND identifier = $1",
            v,
        )
        if row:
            return str(row["user_id"])
    return None


def _mask_identifier(provider: str, identifier: str) -> str:
    """脱敏显示：邮箱保留前后、手机中间*、账号/微信/GitHub 仅显示已绑定。"""
    if not identifier:
        return "已绑定"
    if provider == "email":
        if "@" in identifier:
            a, b = identifier.split("@", 1)
            return f"{a[:1]}***@{b}" if len(a) > 1 else f"***@{b}"
        return "***"
    if provider == "phone":
        if len(identifier) >= 11:
            return f"{identifier[:3]}****{identifier[-4:]}"
        return "****"
    if provider in ("account", "wechat", "github"):
        return identifier[:4] + "***" if len(identifier) > 4 else "已绑定"
    return "已绑定"


async def _merge_other_user_into_current(
    db: Any, current_user_id: str, other_user_id: str, use_other_nickname: bool
) -> None:
    """将 other_user 的所有身份并入 current_user，积分相加，并记录分摊来源用于解绑。"""
    if current_user_id == other_user_id:
        return
    other = await db.fetchrow(
        "SELECT nickname, primary_email, primary_phone, COALESCE(points, 0) AS points, COALESCE(free_points, 0) AS free_points, COALESCE(redeemed_points, 0) AS redeemed_points, COALESCE(paid_points, 0) AS paid_points, COALESCE(gift_points, 0) AS gift_points FROM users WHERE id = $1",
        other_user_id,
    )
    if not other:
        return
    other_points = int(other.get("points") or 0)
    other_free = int(other.get("free_points") or other_points or 0)
    other_redeemed = int(other.get("redeemed_points") or 0)
    other_paid = int(other.get("paid_points") or 0)
    other_gift = int(other.get("gift_points") or 0)
    if other_free + other_redeemed + other_paid + other_gift > 0:
        other_points = other_free + other_redeemed + other_paid + other_gift

    # GitHub：若双方各有一条且 identifier 不同（常见为当前用户为占位 dev_*、对方为真实数字 id），
    # 必须先 UPDATE 当前用户的 github.identifier，再删对方的 github。若先按 provider 批量删对方，
    # 会把真实 GitHub 行删掉且 UNIQUE(user_id,provider) 下无法把真实 id 迁回当前用户，导致永远两个账号。
    cur_gh = await db.fetchrow(
        "SELECT identifier FROM user_identities WHERE user_id = $1 AND provider = 'github' LIMIT 1",
        current_user_id,
    )
    oth_gh = await db.fetchrow(
        "SELECT identifier FROM user_identities WHERE user_id = $1 AND provider = 'github' LIMIT 1",
        other_user_id,
    )
    if cur_gh and oth_gh and (cur_gh["identifier"] or "") != (oth_gh["identifier"] or ""):
        c_id = (cur_gh["identifier"] or "").strip()
        o_id = (oth_gh["identifier"] or "").strip()

        def _github_numeric_user_id(s: str) -> bool:
            if not s:
                return False
            try:
                int(s)
                return True
            except ValueError:
                return False

        # 占位 dev_* 与真实数字 id 并存时，必须保留数字 id，不能反过来写成占位。
        if _github_numeric_user_id(o_id) and not _github_numeric_user_id(c_id):
            winner = o_id
        elif _github_numeric_user_id(c_id) and not _github_numeric_user_id(o_id):
            winner = c_id
        else:
            winner = o_id

        await db.execute(
            "UPDATE user_identities SET identifier = $1 WHERE user_id = $2 AND provider = 'github'",
            winner,
            current_user_id,
        )
        await db.execute(
            "DELETE FROM user_identities WHERE user_id = $1 AND provider = 'github'",
            other_user_id,
        )

    # 先删除「被合并方」中与当前用户已存在 provider 冲突的身份，避免 UNIQUE(user_id, provider) 违反
    await db.execute(
        """DELETE FROM user_identities WHERE user_id = $1 AND provider IN (
            SELECT provider FROM user_identities WHERE user_id = $2
        )""",
        other_user_id,
        current_user_id,
    )
    moved = await db.fetch(
        "SELECT provider, identifier FROM user_identities WHERE user_id = $1",
        other_user_id,
    )
    if moved:
        await db.execute(
            "UPDATE user_identities SET user_id = $1 WHERE user_id = $2",
            current_user_id,
            other_user_id,
        )

    # 积分合并：无论是否还有身份迁入都要合（例如对方仅 GitHub 且已在上面并入当前 github 行）
    if other_points > 0:
        await db.execute(
            """
            UPDATE users SET
                points = COALESCE(points, 0) + $1,
                free_points = COALESCE(free_points, points, 0) + $2,
                redeemed_points = COALESCE(redeemed_points, 0) + $3,
                paid_points = COALESCE(paid_points, points, 0) + $4,
                gift_points = COALESCE(gift_points, 0) + $5
            WHERE id = $6
            """,
            other_points,
            other_free,
            other_redeemed,
            other_paid,
            other_gift,
            current_user_id,
        )

    if moved:
        n = len(moved)
        base_f = other_free // n
        rem_f = other_free % n
        base_r = other_redeemed // n
        rem_r = other_redeemed % n
        base_p = other_paid // n
        rem_p = other_paid % n
        for idx, row in enumerate(moved):
            free_share = base_f + (rem_f if idx == 0 else 0)
            redeemed_share = base_r + (rem_r if idx == 0 else 0)
            paid_share = base_p + (rem_p if idx == 0 else 0)
            total_share = free_share + redeemed_share + paid_share
            await db.execute(
                """UPDATE user_identities SET credits_contributed = $1, free_contributed = $2, redeemed_contributed = $3, paid_contributed = $4
                   WHERE user_id = $5 AND provider = $6 AND identifier = $7""",
                total_share,
                free_share,
                redeemed_share,
                paid_share,
                current_user_id,
                row["provider"],
                row["identifier"],
            )
    if use_other_nickname and other.get("nickname"):
        await db.execute("UPDATE users SET nickname = $1 WHERE id = $2", other["nickname"], current_user_id)
    cur = await db.fetchrow(
        "SELECT primary_email, primary_phone FROM users WHERE id = $1",
        current_user_id,
    )
    if cur:
        if not cur.get("primary_email") and other.get("primary_email"):
            try:
                await db.execute("UPDATE users SET primary_email = $1 WHERE id = $2", other["primary_email"], current_user_id)
            except asyncpg.UniqueViolationError:
                raise HTTPException(
                    status_code=400,
                    detail="该邮箱已被其他账号使用，无法自动合并，请先解绑或更换账号后重试",
                )
        if not cur.get("primary_phone") and other.get("primary_phone"):
            try:
                await db.execute("UPDATE users SET primary_phone = $1 WHERE id = $2", other["primary_phone"], current_user_id)
            except asyncpg.UniqueViolationError:
                raise HTTPException(
                    status_code=400,
                    detail="该手机号已被其他账号使用，无法自动合并，请先解绑或更换账号后重试",
                )
    await db.execute("DELETE FROM users WHERE id = $1", other_user_id)


def _send_sms_sync(phone: str, code: str) -> bool:
    """同步发送短信验证码。未配置或未安装 SDK 时不发送，返回 False；发送成功返回 True。"""
    if not (
        Config.ALIYUN_ACCESS_KEY_ID
        and Config.ALIYUN_ACCESS_KEY_SECRET
        and Config.SMS_SIGN_NAME
        and Config.SMS_TEMPLATE_CODE
    ):
        logger.info(f"[短信未配置] 验证码将仅存于服务端: {phone} -> {code}")
        return False
    try:
        from alibabacloud_dysmsapi20170525.client import Client as DysmsClient
        from alibabacloud_tea_openapi import models as open_api_models
        from alibabacloud_dysmsapi20170525 import models as dysms_models
    except ImportError:
        logger.warning("未安装阿里云短信 SDK（alibabacloud_dysmsapi20170525），验证码未发送")
        return False
    config = open_api_models.Config(
        access_key_id=Config.ALIYUN_ACCESS_KEY_ID,
        access_key_secret=Config.ALIYUN_ACCESS_KEY_SECRET,
        endpoint="dysmsapi.aliyuncs.com",
        region_id="cn-hangzhou",
    )
    client = DysmsClient(config)
    req = dysms_models.SendSmsRequest(
        phone_numbers=phone,
        sign_name=Config.SMS_SIGN_NAME,
        template_code=Config.SMS_TEMPLATE_CODE,
        template_param=json.dumps({"code": code}),
    )
    logger.info(
        f"[短信] 正在调用阿里云 API: endpoint=dysmsapi.aliyuncs.com, sign_name={Config.SMS_SIGN_NAME!r}, "
        f"template_code={Config.SMS_TEMPLATE_CODE}, phone={phone[:3]}****{phone[-4:] if len(phone) >= 7 else '****'}"
    )
    try:
        resp = client.send_sms(req)
        body = getattr(resp, "body", None)
        code_val = getattr(body, "code", None) if body else getattr(resp, "code", None)
        msg_val = getattr(body, "message", None) if body else getattr(resp, "message", None)
        if code_val != "OK":
            logger.warning(
                f"[短信] 阿里云返回失败: code={code_val!r}, message={msg_val!r}. "
                f"完整 body={body!r}"
            )
            return False
        logger.info(f"[短信] 已提交发送: phone={phone[:3]}****{phone[-4:] if len(phone) >= 7 else '****'}")
        return True
    except Exception as e:
        logger.exception(f"[短信] 调用阿里云异常（可能未连上）: {e!r}")
        return False


def _send_email_sync(to_email: str, code: str, subject: str = "您的登录验证码") -> None:
    """同步发送邮件（在未配置 SMTP 时不发送，仅记录日志）。"""
    if not Config.SMTP_HOST or not Config.SMTP_USER or not Config.SMTP_PASSWORD:
        logger.info(f"[邮件未配置] 验证码将仅存于服务端: {to_email} -> {code}")
        return
    from_addr = Config.SMTP_FROM or Config.SMTP_USER
    msg = MIMEText(f"您的验证码是：{code}\n\n有效期 15 分钟，请勿泄露。", "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr(("验证码", from_addr))
    msg["To"] = to_email
    try:
        if Config.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT, timeout=15) as server:
                server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
                server.sendmail(from_addr, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=15) as server:
                if Config.SMTP_USE_TLS:
                    server.starttls()
                server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
                server.sendmail(from_addr, [to_email], msg.as_string())
        logger.info(f"邮件已发送: {to_email}")
    except Exception as e:
        logger.error(f"发送邮件失败: {e}")
        raise


def _generate_captcha_text(length: int = 6) -> str:
    return "".join(random.choices(CAPTCHA_CHARS, k=length))


def _generate_captcha_image(text: str) -> bytes:
    """生成 6 位验证码图片，返回 PNG 字节（大号字体便于辨认）."""
    def _blank_png() -> bytes:
        buf = io.BytesIO()
        Image.new("RGB", (200, 64), color=(30, 41, 59)).save(buf, format="PNG")
        return buf.getvalue()

    try:
        out_width, out_height = 200, 64
        font_size = 40
        font = None
        for path in (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "arial.ttf",
        ):
            try:
                font = ImageFont.truetype(path, font_size)
                break
            except Exception:
                continue
        use_scale = font is None
        if font is None:
            font = ImageFont.load_default()
            # 默认字体极小：先在小画布上画，再放大 3 倍，字符才会大
            scale = 3
            width, height = out_width // scale, out_height // scale
        else:
            scale = 1
            width, height = out_width, out_height
        img = Image.new("RGB", (width, height), color=(30, 41, 59))
        draw = ImageDraw.Draw(img)
        if use_scale:
            x, char_step = 2, 8
        else:
            x, char_step = 12, 30
        for ch in text:
            y = random.randint(1, 4) if use_scale else random.randint(6, 14)
            draw.text((x, y), ch, fill=(148, 163, 184), font=font)
            x += char_step
        for _ in range(3):
            x1, y1 = random.randint(0, max(0, width - 1)), random.randint(0, max(0, height - 1))
            x2, y2 = random.randint(0, max(0, width - 1)), random.randint(0, max(0, height - 1))
            draw.line([(x1, y1), (x2, y2)], fill=(71, 85, 105), width=1)
        if use_scale and scale > 1:
            try:
                resample = Image.Resampling.LANCZOS  # type: ignore[attr-defined]
            except AttributeError:
                resample = getattr(Image, "LANCZOS", 1)
            img = img.resize((out_width, out_height), resample)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        logger.error("图形验证码绘制失败，使用占位图: %s", e)
        return _blank_png()


def _verify_captcha_or_raise(request: Request, captcha_id: str, user_input: str) -> None:
    """校验图形验证码，失败时根据失败次数抛出带提示的 HTTPException；成功则清除该 IP 的失败计数。"""
    locked, _, remaining = _get_captcha_fail_state(request)
    if locked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="请15分钟后再试")
    if not _verify_captcha(request, captcha_id, user_input):
        is_now_locked, detail = _record_captcha_fail(request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )
    _clear_captcha_fail(request)


@router.get("/captcha")
async def get_captcha(request: Request):
    """获取账号登录用图形验证码：返回 base64 图片与 captcha_id，登录时需带上 captcha_id 与用户输入的验证码."""
    if not HAS_PIL:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="验证码服务不可用")
    try:
        locked, _, _ = _get_captcha_fail_state(request)
        if locked:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="请15分钟后再试")
        text = _generate_captcha_text(6)
        captcha_id = str(uuid.uuid4())
        app_state = request.app.state
        cache = getattr(app_state, "cache", None)
        cache_connected = getattr(app_state, "cache_connected", False)
        if cache_connected and cache:
            cache.set(f"captcha:{captcha_id}", text, expire_seconds=300)
        else:
            captcha_store[captcha_id] = text
        img_b64 = base64.b64encode(_generate_captcha_image(text)).decode("ascii")
        return {"image": f"data:image/png;base64,{img_b64}", "captcha_id": captcha_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("生成图形验证码失败: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="验证码生成失败，请稍后重试或联系管理员",
        )


@router.get("/captcha-lock-state")
async def get_captcha_lock_state(request: Request):
    """获取当前 IP 的图形验证码锁定状态，用于前端显示倒计时。连续错 5 次锁定 15 分钟。"""
    try:
        until = _get_captcha_lock_until(request)
        if until is None:
            return {"locked": False}
        return {"locked": True, "locked_until_utc": until.isoformat()}
    except Exception as e:
        logger.exception("读取 captcha-lock-state 失败: %s", e)
        return {"locked": False}


def _verify_captcha(request: Request, captcha_id: str, user_input: str) -> bool:
    """校验图形验证码，校验后删除（一次性）。"""
    if not captcha_id or not user_input:
        return False
    app_state = request.app.state
    cache = getattr(app_state, "cache", None)
    cache_connected = getattr(app_state, "cache_connected", False)
    stored = None
    if cache_connected and cache:
        stored = cache.get(f"captcha:{captcha_id}")
        if stored is not None:
            cache.delete(f"captcha:{captcha_id}")
    else:
        stored = captcha_store.pop(captcha_id, None)
    if stored is None:
        return False
    return stored.upper() == user_input.strip().upper()


@router.post("/logout")
async def auth_logout(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
):
    """显式登出：删除 Redis 滑动会话键（若已连接）；JWT 在受保护请求上随即失效。"""
    if credentials and credentials.scheme.lower() == "bearer" and credentials.credentials:
        payload = AuthManager.verify_token(credentials.credentials)
        uid = (payload or {}).get("sub")
        if uid:
            session_idle.clear_session_idle(request, str(uid))
    return {"ok": True}


@router.get("/session/touch")
async def session_touch(_request: Request, _user: Dict[str, Any] = Depends(get_current_user)):
    """
    刷新 Redis 滑动会话 TTL（与 core.session_idle、Config.SESSION_IDLE_SECONDS 一致）。
    供前端在用户操作/切页时节流调用，使「无操作窗口」与前端 IDLE 计时对齐。
    """
    return {"ok": True}


@router.post("/register")
async def register(user_data: UserCreate, request: Request):
    """用户注册：填写账号密码即可注册，可选绑定手机/邮箱（需验证码）"""
    app_state = request.app.state
    register_via = (getattr(user_data, "register_via", None) or "account").strip().lower()
    if register_via not in {"account", "phone", "email"}:
        register_via = "account"
    create_account_identity = register_via == "account"

    # 1. 用户名规范：去除首尾空格，与登录查询一致
    username = (user_data.username or "").strip()
    if not username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名不能为空")

    # 2. 验证密码一致性
    if user_data.password != user_data.password_confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="两次输入的密码不一致")

    # 3. 验证密码安全规则
    _validate_password_security_or_raise(user_data.password, min_categories=3)

    # 开发模式：如果数据库未连接，返回模拟注册成功
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        logger.warning("数据库未连接，使用开发模式注册")
        access_token = AuthManager.create_access_token(
            data={"sub": "dev-user-id"},
            expires_delta=timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        session_idle.register_login_session(request, "dev-user-id")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": "dev-user-id",
                "username": user_data.username,
                "email": user_data.email,
                "phone": user_data.phone,
                "credits": FREE_POINTS_REFRESH_AMOUNT,
                "role": "student"
            },
            "_dev_mode": True,
            "message": "开发模式：数据库未连接，返回模拟注册成功"
        }

    db = app_state.db
    cache = app_state.cache if hasattr(app_state, "cache") else None
    cache_connected = app_state.cache_connected if hasattr(app_state, "cache_connected") else False

    # 3. 验证手机号（如果提供）
    phone = None
    if user_data.phone:
        if not re.match(r"^1[3-9]\d{9}$", user_data.phone):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="手机号格式不正确")
        if not user_data.phone_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="填写手机号后需要输入手机验证码")
        stored_code = None
        if cache_connected and cache:
            stored = cache.get_verification_code(user_data.phone)
            stored_code = _get_code_from_stored(stored)
        else:
            info = verification_codes.get(user_data.phone)
            if info and isinstance(info, dict):
                stored_code = info.get("code")
        if not stored_code or stored_code != user_data.phone_code:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="手机验证码错误或已过期")
        if cache_connected and cache:
            cache.delete_verification_code(user_data.phone)
        else:
            verification_codes.pop(user_data.phone, None)
        phone = user_data.phone

    # 4. 验证邮箱（如果提供）
    email = None
    if user_data.email:
        if user_data.email_code:
            stored_code = None
            key = f"email_{user_data.email}"
            if cache_connected and cache:
                stored = cache.get_verification_code(key)
                stored_code = _get_code_from_stored(stored)
            else:
                info = verification_codes.get(key)
                if info and isinstance(info, dict):
                    stored_code = info.get("code")
            if not stored_code or stored_code != user_data.email_code:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱验证码错误或已过期")
            if cache_connected and cache:
                cache.delete_verification_code(key)
            else:
                verification_codes.pop(key, None)
        email = user_data.email

    # 5. 处理微信绑定（如果提供）
    openid = None
    if user_data.wechat_code:
        # TODO: 调用微信API获取openid
        # 开发模式：使用code生成模拟openid
        openid = f"wechat_{user_data.wechat_code[:10]}"

    # 6. 处理GitHub绑定（如果提供）
    github_id = None
    if user_data.github_code:
        if Config.GITHUB_CLIENT_ID and Config.GITHUB_CLIENT_SECRET:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://github.com/login/oauth/access_token",
                        data={
                            "client_id": Config.GITHUB_CLIENT_ID,
                            "client_secret": Config.GITHUB_CLIENT_SECRET,
                            "code": user_data.github_code,
                        },
                        headers={"Accept": "application/json"},
                        timeout=10,
                    ) as resp:
                        token_data = await resp.json()
                    access_token = token_data.get("access_token")
                    if access_token:
                        async with session.get(
                            "https://api.github.com/user",
                            headers={"Authorization": f"token {access_token}"},
                            timeout=10,
                        ) as resp:
                            user_data_github = await resp.json()
                        github_id = _github_oauth_identifier_from_api(user_data_github)
            except Exception as e:
                logger.error(f"GitHub绑定失败: {e}")
        if not github_id:
            if _github_oauth_secrets_configured():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="注册时 GitHub 绑定失败：未能完成 OAuth（换票或拉取用户信息失败），请检查网络与 GitHub 应用配置",
                )
            github_id = _dev_github_identifier_from_code(user_data.github_code)

    # 7. 检查是否已被注册（新结构：查 user_identities，使用规范后的 username）
    account_identifier = username if create_account_identity else None
    existing = await db.fetchrow(
        """
        SELECT user_id FROM user_identities
        WHERE (provider = 'account' AND identifier = $1 AND $1 IS NOT NULL)
           OR (provider = 'email' AND identifier = $2 AND $2 IS NOT NULL)
           OR (provider = 'phone' AND identifier = $3 AND $3 IS NOT NULL)
        LIMIT 1
        """,
        account_identifier,
        email,
        str(phone).strip() if phone else None,
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名、邮箱或手机号已被注册")

    # 8. 密码加密（仅 account 注册需要写入账号凭证）
    password_hash = hash_password(user_data.password) if create_account_identity else None

    # 9. 创建用户（新结构：users + user_identities，identifier 必须与登录时查询一致）
    # 显示名与全站唯一（不区分大小写）；若与已有昵称冲突则自动加后缀
    if register_via == "phone" and phone:
        nick_base = "手机" + (phone[-4:] if len(phone) >= 4 else phone)
    elif register_via == "email" and email:
        nick_base = (email.split("@")[0] if "@" in email else email) or "用户"
    else:
        nick_base = username
    initial_nickname = await _allocate_unique_display_nickname_for_new_user(db, nick_base)
    created = await db.fetchrow(
        """
        INSERT INTO users (nickname, primary_email, primary_phone, points, free_points, paid_points, role, is_active)
        VALUES ($1, $2, $3, $4, $4, 0, 'student', TRUE)
        RETURNING id, nickname, avatar, primary_email, primary_phone, points, free_points, paid_points, role
        """,
        initial_nickname,
        email,
        phone,
        FREE_POINTS_REFRESH_AMOUNT,
    )
    user_id = created["id"]

    # 10. 写入登录身份（account 的 identifier 用规范后的 username，登录时同样 strip 后查询）
    if create_account_identity:
        await db.execute(
            """INSERT INTO user_identities (user_id, provider, identifier, credential)
               VALUES ($1, 'account', $2, $3::jsonb)""",
            user_id, username, json.dumps({"password_hash": password_hash}),
        )
    if email:
        await db.execute(
            """INSERT INTO user_identities (user_id, provider, identifier) VALUES ($1, 'email', $2)""",
            user_id, email,
        )
    if phone:
        await db.execute(
            """INSERT INTO user_identities (user_id, provider, identifier) VALUES ($1, 'phone', $2)""",
            user_id, str(phone).strip(),
        )
    if openid:
        await db.execute(
            """INSERT INTO user_identities (user_id, provider, identifier) VALUES ($1, 'wechat', $2)""",
            user_id, openid,
        )
    if github_id:
        await db.execute(
            """INSERT INTO user_identities (user_id, provider, identifier) VALUES ($1, 'github', $2)""",
            user_id, github_id,
        )

    access_token = AuthManager.create_access_token(
        data={"sub": str(user_id)},
        expires_delta=timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    session_idle.register_login_session(request, str(user_id))
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": _user_response(created),
    }


class LoginAccountRequestBody(BaseModel):
    username: Optional[str] = ""
    captcha_id: Optional[str] = ""
    captcha_code: Optional[str] = ""


@router.post("/login/account-request")
async def login_account_request(request: Request, body: LoginAccountRequestBody):
    """账号登录第一步：校验图形验证码后返回 one_time_token，用于第二步提交用户名+密码。"""
    captcha_id = (body.captcha_id or "").strip()
    captcha_code = (body.captcha_code or "").strip()
    username = (body.username or "").strip()
    if not captcha_id or not captcha_code:
        raise HTTPException(status_code=400, detail="请先获取并输入图形验证码")
    if not username:
        raise HTTPException(status_code=400, detail="请输入用户名")
    _verify_captcha_or_raise(request, captcha_id, captcha_code)
    one_time_token = AuthManager.create_one_time_token("account_login", username)
    return {"one_time_token": one_time_token}


@router.post("/login")
async def login(login_data: UserLogin, request: Request):
    """用户登录：支持多种登录方式。手机/邮箱/账号登录需先获取 one_time_token，验证成功返回用户 JWT，验证失败返回新 one_time_token。"""
    logger.info("🚀 登录请求到达: /api/auth/login")
    app_state = request.app.state

    # 开发模式：如果数据库未连接，返回模拟登录
    if not hasattr(app_state, 'db_connected') or not app_state.db_connected:
        logger.warning("数据库未连接，使用开发模式登录")
        access_token = AuthManager.create_access_token(
            data={"sub": "dev-user-id"},
            expires_delta=timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        session_idle.register_login_session(request, "dev-user-id")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": "dev-user-id",
                "username": "dev_user",
                "email": "dev@example.com",
                "credits": FREE_POINTS_REFRESH_AMOUNT,
                "role": "student"
            },
            "_dev_mode": True,
            "message": "开发模式：数据库未连接，返回模拟登录成功"
        }

    db = app_state.db
    cache = app_state.cache if hasattr(app_state, 'cache') else None
    cache_connected = app_state.cache_connected if hasattr(app_state, 'cache_connected') else False
    user = None

    # 方式1: 用户名+密码，需 one_time_token（由 login/account-request 或图形验证码通过后获得）
    if login_data.username and login_data.password is not None:
        username = (login_data.username or "").strip()
        if not username:
            raise HTTPException(status_code=400, detail="请输入用户名")
        _validate_password_security_or_raise(login_data.password)
        ott = AuthManager.verify_one_time_token(login_data.one_time_token or "")
        if not ott or ott.get("purpose") != "account_login" or (ott.get("sub") or "").strip() != username:
            raise HTTPException(status_code=400, detail="请先完成图形验证并获取登录凭证，或凭证已过期")
        try:
            ident = await db.fetchrow(
                "SELECT user_id, credential FROM user_identities WHERE provider = 'account' AND identifier = $1",
                username,
            )
            if not ident:
                new_ott = AuthManager.create_one_time_token("account_login", username)
                return JSONResponse(status_code=401, content={"detail": "该账号尚未完成注册", "one_time_token": new_ott})
            cred = ident.get("credential")
            if isinstance(cred, str):
                try:
                    cred = json.loads(cred) if cred else {}
                except Exception:
                    cred = {}
            elif cred is None:
                cred = {}
            if not isinstance(cred, dict):
                cred = {}
            password_hash = cred.get("password_hash")
            if not password_hash:
                new_ott = AuthManager.create_one_time_token("account_login", username)
                return JSONResponse(status_code=401, content={"detail": "该账号尚未完成注册", "one_time_token": new_ott})
            is_valid = verify_password(login_data.password, password_hash)
            if not is_valid:
                new_ott = AuthManager.create_one_time_token("account_login", username)
                return JSONResponse(status_code=401, content={"detail": "用户名或密码错误", "one_time_token": new_ott})
            user = await db.fetchrow(
                "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, redeemed_points, paid_points, gift_points, free_points_refreshed_at, is_active, role FROM users WHERE id = $1",
                ident["user_id"],
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ 数据库/密码验证失败: {e}")
            raise HTTPException(status_code=500, detail="登录失败")

    # 方式2: 手机号+验证码，需 one_time_token（由 send-code 返回）
    elif login_data.phone and login_data.phone_code is not None:
        phone = (login_data.phone or "").strip()
        ott = AuthManager.verify_one_time_token(login_data.one_time_token or "")
        if not ott or ott.get("purpose") != "sms_login" or (ott.get("sub") or "").strip() != phone:
            raise HTTPException(status_code=400, detail="请先获取手机验证码，或登录凭证已过期")
        stored_code = None
        if cache_connected and cache:
            stored = cache.get_verification_code(phone)
            stored_code = _get_code_from_stored(stored)
            if stored_code:
                cache.delete_verification_code(phone)
        else:
            info = verification_codes.get(phone)
            if info and isinstance(info, dict):
                created_at = info.get("created_at")
                expire_seconds = getattr(Config, "SMS_PHONE_CODE_EXPIRE_SECONDS", 300)
                if created_at and (datetime.now(timezone.utc) - created_at).total_seconds() < expire_seconds:
                    stored_code = info.get("code")
                verification_codes.pop(phone, None)
        if not stored_code or stored_code != login_data.phone_code:
            new_ott = AuthManager.create_one_time_token("sms_login", phone)
            return JSONResponse(status_code=401, content={"detail": "手机验证码错误或已过期", "one_time_token": new_ott})
        ident = await db.fetchrow(
            "SELECT user_id FROM user_identities WHERE provider = 'phone' AND identifier = $1",
            phone,
        )
        if ident:
            user = await db.fetchrow(
                "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, redeemed_points, paid_points, gift_points, free_points_refreshed_at, is_active, role FROM users WHERE id = $1",
                ident["user_id"],
            )
        else:
            new_ott = AuthManager.create_one_time_token("sms_login", phone)
            return JSONResponse(status_code=401, content={"detail": "该账号尚未完成注册", "one_time_token": new_ott})

    # 方式3: 邮箱+验证码，需 one_time_token（由 send-email-code 返回）
    elif login_data.email and login_data.email_code is not None:
        email = (login_data.email or "").strip()
        ott = AuthManager.verify_one_time_token(login_data.one_time_token or "")
        if not ott or ott.get("purpose") != "email_login" or (ott.get("sub") or "").strip() != email:
            raise HTTPException(status_code=400, detail="请先获取邮箱验证码，或登录凭证已过期")
        key = f"email_{email}"
        stored_code = None
        if cache_connected and cache:
            stored = cache.get_verification_code(key)
            stored_code = _get_code_from_stored(stored)
            if stored_code:
                cache.delete_verification_code(key)
        else:
            info = verification_codes.get(key)
            if info and isinstance(info, dict):
                exp = info.get("expires_at")
                if exp and datetime.now(timezone.utc) < exp:
                    stored_code = info.get("code")
                verification_codes.pop(key, None)
        if not stored_code or stored_code != login_data.email_code:
            new_ott = AuthManager.create_one_time_token("email_login", email)
            return JSONResponse(status_code=401, content={"detail": "邮箱验证码错误或已过期", "one_time_token": new_ott})

        ident = await db.fetchrow(
            "SELECT user_id FROM user_identities WHERE provider = 'email' AND identifier = $1",
            email,
        )
        if ident:
            user = await db.fetchrow(
                "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, redeemed_points, paid_points, gift_points, free_points_refreshed_at, is_active, role FROM users WHERE id = $1",
                ident["user_id"],
            )
        else:
            new_ott = AuthManager.create_one_time_token("email_login", email)
            return JSONResponse(status_code=401, content={"detail": "该账号尚未完成注册", "one_time_token": new_ott})

    # 方式4: 微信授权（新结构：user_identities provider=wechat）
    elif login_data.wechat_code:
        openid = f"wechat_{login_data.wechat_code[:10]}"
        ident = await db.fetchrow(
            "SELECT user_id FROM user_identities WHERE provider = 'wechat' AND identifier = $1",
            openid,
        )
        if not ident:
            raise HTTPException(status_code=404, detail="该微信账号未绑定")
        user = await db.fetchrow(
            "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, redeemed_points, paid_points, gift_points, free_points_refreshed_at, is_active, role FROM users WHERE id = $1",
            ident["user_id"],
        )
    
    # 方式5: GitHub授权
    elif login_data.github_code:
        github_id = None
        if Config.GITHUB_CLIENT_ID and Config.GITHUB_CLIENT_SECRET:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://github.com/login/oauth/access_token",
                        data={
                            "client_id": Config.GITHUB_CLIENT_ID,
                            "client_secret": Config.GITHUB_CLIENT_SECRET,
                            "code": login_data.github_code,
                        },
                        headers={"Accept": "application/json"},
                        timeout=10,
                    ) as resp:
                        token_data = await resp.json()
                    access_token_gh = token_data.get("access_token")
                    if access_token_gh:
                        async with session.get(
                            "https://api.github.com/user",
                            headers={"Authorization": f"token {access_token_gh}"},
                            timeout=10,
                        ) as resp:
                            user_data_github = await resp.json()
                        github_id = _github_oauth_identifier_from_api(user_data_github)
            except Exception as e:
                logger.error(f"GitHub登录失败: {e}")
                raise HTTPException(status_code=500, detail="GitHub授权失败")
        else:
            github_id = _dev_github_identifier_from_code(login_data.github_code)
        
        if not github_id:
            raise HTTPException(status_code=500, detail="GitHub授权失败")
        ident = await db.fetchrow(
            "SELECT user_id FROM user_identities WHERE provider = 'github' AND identifier = $1",
            github_id,
        )
        if not ident:
            raise HTTPException(status_code=404, detail="该GitHub账号未绑定")
        user = await db.fetchrow(
            "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, redeemed_points, paid_points, gift_points, free_points_refreshed_at, is_active, role FROM users WHERE id = $1",
            ident["user_id"],
        )

    else:
        raise HTTPException(status_code=400, detail="请提供有效的登录信息")
    
    if not user or not user.get('is_active', True):
        raise HTTPException(status_code=403, detail="账户已被禁用")
    
    access_token = AuthManager.create_access_token(
        data={"sub": str(user['id'])},
        expires_delta=timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    session_idle.register_login_session(request, str(user["id"]))

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": _user_response(user),
    }


@router.get("/github-auth-url")
async def github_auth_url(redirect_uri: str):
    """返回 GitHub OAuth 授权页 URL，前端跳转用。登录与绑定均加 prompt=select_account，强制显示账号选择页，避免直接用浏览器已登录账号而不做选择。"""
    if not Config.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub 登录未配置（缺少 GITHUB_CLIENT_ID）",
        )
    state = secrets.token_urlsafe(16)
    params = {
        "client_id": Config.GITHUB_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": "user:email",
        "state": state,
        "prompt": "select_account",  # 登录与绑定都要求选账号，不直接用浏览器已登录身份
    }
    url = "https://github.com/login/oauth/authorize?" + urlencode(params)
    return {"url": url, "state": state}


@router.post("/github-login")
async def github_login(payload: Dict[str, Any], request: Request):
    """GitHub 登录：仅在使用完整 OAuth 配置时进行真实认证，否则明确报错（不做假登录）"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接")

    db = app_state.db
    code = payload.get("code")
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少登录凭证 code")
    ru_raw = payload.get("redirect_uri")
    redirect_uri_oauth = (ru_raw.strip() if isinstance(ru_raw, str) and ru_raw.strip() else None)

    # 未配置完整 GitHub OAuth 时直接报错，不做“开发模式”假登录
    if not Config.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub 登录未配置（缺少 GITHUB_CLIENT_ID）",
        )
    if not Config.GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub 登录未配置完整，请在服务端设置 GITHUB_CLIENT_SECRET（.env 或环境变量）",
        )

    github_id: str | None = None
    email: str | None = None
    username: str | None = None

    token_url = "https://github.com/login/oauth/access_token"
    user_url = "https://api.github.com/user"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                token_url,
                data=_github_oauth_token_request_body(str(code), redirect_uri_oauth),
                headers={"Accept": "application/json"},
                timeout=10,
            ) as resp:
                token_data = await resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                err_msg = token_data.get("error_description") or token_data.get("error") or "无法获取访问令牌"
                logger.warning(f"GitHub OAuth 获取 token 失败: {token_data}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"GitHub 登录失败：{err_msg}")

            async with session.get(
                user_url,
                headers={
                    "Authorization": f"token {access_token}",
                    "Accept": "application/json",
                },
                timeout=10,
            ) as resp:
                user_data = await resp.json()

            github_id = _github_oauth_identifier_from_api(user_data)
            if not github_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="GitHub 登录失败：无法解析用户标识",
                )
            username = user_data.get("login") or f"github_user_{github_id[-6:]}"
            email = user_data.get("email") or f"{username}@github.com"
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"GitHub 登录请求异常: {e}")
        if _github_oauth_secrets_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GitHub 登录暂时失败，请稍后重试",
            ) from e
        logger.warning("GitHub OAuth 未配置完整，使用开发占位登录。")
        github_id = _dev_github_identifier_from_code(code)
        username = f"github_user_{github_id[-6:]}"
        email = f"{username}@github.com"

    if not github_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub 登录失败：无法获取用户标识",
        )

    # 查找或创建用户（新结构：user_identities provider=github）
    existing_uid = await _lookup_user_id_by_github_identifier(db, github_id)
    if existing_uid:
        user = await db.fetchrow(
            "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, redeemed_points, paid_points, gift_points, free_points_refreshed_at, is_active, role FROM users WHERE id = $1",
            existing_uid,
        )
    else:
        # 仅创建 GitHub 身份，不写入 primary_email / 不创建 email 身份，邮箱显示「未绑定」供用户后续绑定
        gh_nick = await _allocate_unique_display_nickname_for_new_user(db, username)
        created = await db.fetchrow(
            """
            INSERT INTO users (nickname, points, free_points, paid_points, role)
            VALUES ($1, $2, $2, 0, 'student')
            RETURNING id, nickname, avatar, primary_email, primary_phone, points, free_points, redeemed_points, paid_points, role
            """,
            gh_nick,
            FREE_POINTS_REFRESH_AMOUNT,
        )
        await db.execute(
            "INSERT INTO user_identities (user_id, provider, identifier) VALUES ($1, 'github', $2)",
            created["id"],
            github_id,
        )
        user = created

    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已被禁用")

    access_token = AuthManager.create_access_token(
        data={"sub": str(user["id"])},
        expires_delta=timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    session_idle.register_login_session(request, str(user["id"]))
    resp_user = _user_response(user)
    resp_user["github_id"] = github_id
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": resp_user,
    }


@router.post("/send-email-code")
async def send_email_code(
    request: Request,
    email: str = None,
    captcha_id: str = None,
    captcha_code: str = None,
    scene: str = "login",
):
    """发送邮箱验证码：需先通过图形验证码校验，有效期 15 分钟。"""
    if not captcha_id or not captcha_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先获取并输入图形验证码")
    _verify_captcha_or_raise(request, captcha_id, captcha_code)
    if not email or not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱格式不正确")
    app_state = request.app.state
    cache = app_state.cache if hasattr(app_state, "cache") else None
    cache_connected = app_state.cache_connected if hasattr(app_state, "cache_connected") else False
    db = app_state.db if hasattr(app_state, "db") else None

    # 登录场景：未注册邮箱不发送验证码，避免“先发码后报未注册”的体验不一致。
    if scene == "login" and db is not None:
        ident = await db.fetchrow(
            "SELECT 1 FROM user_identities WHERE provider = 'email' AND identifier = $1 LIMIT 1",
            email,
        )
        if not ident:
            raise HTTPException(status_code=404, detail="该账号尚未完成注册")

    code = str(random.randint(100000, 999999))
    expire_seconds = getattr(Config, "EMAIL_CODE_EXPIRE_SECONDS", 900)

    key = f"email_{email}"
    if cache_connected and cache:
        cache.set_verification_code(key, code, expire_seconds=expire_seconds)
    else:
        verification_codes[key] = {
            "code": code,
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=expire_seconds),
        }

    smtp_configured = bool(Config.SMTP_HOST and Config.SMTP_USER and Config.SMTP_PASSWORD)
    if smtp_configured:
        try:
            await asyncio.to_thread(_send_email_sync, email, code, "您的登录验证码")
        except Exception as e:
            logger.error(f"发送邮件失败: {e}")
            raise HTTPException(status_code=500, detail="验证码发送失败，请稍后重试")

    one_time_token = AuthManager.create_one_time_token("email_login", email)
    if smtp_configured:
        return {"message": "验证码已发送到您的邮箱，请查收（15分钟内有效）", "one_time_token": one_time_token}
    return {
        "message": "当前未配置邮件服务，验证码未发送到邮箱。请在服务端配置 SMTP（.env 或环境变量），详见项目 .env.example。",
        "code": code,
        "one_time_token": one_time_token,
    }


def _sms_configured() -> bool:
    return bool(
        Config.ALIYUN_ACCESS_KEY_ID
        and Config.ALIYUN_ACCESS_KEY_SECRET
        and Config.SMS_SIGN_NAME
        and Config.SMS_TEMPLATE_CODE
    )


@router.post("/send-code")
async def send_code(
    request: Request,
    phone: str = None,
    captcha_id: str = None,
    captcha_code: str = None,
    scene: str = "login",
):
    """发送手机验证码：需先通过图形验证码校验，再校验 11 位大陆手机号并发送。"""
    if not captcha_id or not captcha_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先获取并输入图形验证码")
    _verify_captcha_or_raise(request, captcha_id, captcha_code)
    phone = (phone or "").strip()
    if not re.match(r"^1[3-9]\d{9}$", phone):
        raise HTTPException(status_code=400, detail="手机号格式不正确（需为 11 位、1 开头、第二位 3–9）")
    code = str(random.randint(100000, 999999))
    expire_seconds = getattr(Config, "SMS_PHONE_CODE_EXPIRE_SECONDS", 300)

    app_state = request.app.state
    cache = getattr(app_state, "cache", None)
    cache_connected = getattr(app_state, "cache_connected", False)
    db = app_state.db if hasattr(app_state, "db") else None

    # 登录场景：未注册手机号不发送验证码，避免“先发码后报未注册”的体验不一致。
    if scene == "login" and db is not None:
        ident = await db.fetchrow(
            "SELECT 1 FROM user_identities WHERE provider = 'phone' AND identifier = $1 LIMIT 1",
            phone,
        )
        if not ident:
            raise HTTPException(status_code=404, detail="该账号尚未完成注册")

    if cache_connected and cache:
        cache.set_verification_code(phone, code, expire_seconds=expire_seconds)
        logger.debug(f"手机号 {phone} 的验证码已存入缓存")
    else:
        verification_codes[phone] = {"code": code, "created_at": datetime.now(timezone.utc)}
        logger.warning("Redis 未连接，验证码存储在内存中")

    sms_configured = _sms_configured()
    actually_sent = False
    if sms_configured:
        try:
            actually_sent = await asyncio.to_thread(_send_sms_sync, phone, code)
        except Exception as e:
            logger.error(f"发送短信失败: {e}")
            raise HTTPException(status_code=500, detail="验证码发送失败，请稍后重试")

    one_time_token = AuthManager.create_one_time_token("sms_login", phone)
    if actually_sent:
        return {"message": "验证码已发送到您的手机，请查收（5 分钟内有效）", "one_time_token": one_time_token}
    if sms_configured:
        msg = "验证码发送失败，请稍后重试。可查看服务端日志或阿里云控制台发送记录。"
    else:
        msg = "当前未配置短信服务，验证码未发送到手机。请在服务端配置阿里云短信（.env），详见 .env.example 与过程文档。"
    return {"message": msg, "code": code, "one_time_token": one_time_token}


@router.get("/wechat-auth-url")
async def wechat_auth_url(redirect_uri: str):
    """返回微信开放平台网站应用扫码登录页 URL，用于 iframe 展示二维码。需在微信开放平台创建网站应用并配置授权回调域。"""
    if not Config.WECHAT_APPID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="微信登录未配置（缺少 WECHAT_APPID）",
        )
    state = secrets.token_urlsafe(16)
    params = {
        "appid": Config.WECHAT_APPID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "snsapi_login",
        "state": state,
    }
    url = "https://open.weixin.qq.com/connect/qrconnect?" + urlencode(params) + "#wechat_redirect"
    return {"url": url, "state": state}


@router.post("/wechat-login")
async def wechat_login(code_data: dict, request: Request):
    """微信扫码登录：用微信回调的 code 换 openid，查找或创建用户并返回 JWT。"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(status_code=503, detail="数据库未连接")

    db = app_state.db
    code = code_data.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="缺少登录凭证")

    openid: str | None = None
    nickname: str | None = None

    if Config.WECHAT_APPID and Config.WECHAT_SECRET:
        token_url = "https://api.weixin.qq.com/sns/oauth2/access_token"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    token_url,
                    params={
                        "appid": Config.WECHAT_APPID,
                        "secret": Config.WECHAT_SECRET,
                        "code": code,
                        "grant_type": "authorization_code",
                    },
                    timeout=10,
                ) as resp:
                    data = await resp.json()
                if "openid" not in data:
                    err = data.get("errmsg", "未知错误")
                    logger.warning(f"微信 oauth2 失败: {data}")
                    raise HTTPException(status_code=400, detail=f"微信授权失败：{err}")
                openid = data["openid"]
                # 可选：拉取用户信息
                userinfo_url = "https://api.weixin.qq.com/sns/userinfo"
                async with session.get(
                    userinfo_url,
                    params={"access_token": data["access_token"], "openid": data["openid"]},
                    timeout=10,
                ) as u_resp:
                    u_data = await u_resp.json()
                if "nickname" in u_data:
                    nickname = u_data.get("nickname") or f"微信用户_{openid[-6:]}"
                else:
                    nickname = f"微信用户_{openid[-6:]}"
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"微信登录请求异常: {e}")
            raise HTTPException(status_code=502, detail="微信授权服务暂时不可用") from e

    if not openid:
        openid = f"dev_wechat_{code[:12]}"
        nickname = f"微信用户_{openid[-6:]}"

    ident = await db.fetchrow(
        "SELECT user_id FROM user_identities WHERE provider = 'wechat' AND identifier = $1",
        openid,
    )
    if ident:
        user = await db.fetchrow(
            "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, redeemed_points, paid_points, gift_points, free_points_refreshed_at, is_active, role FROM users WHERE id = $1",
            ident["user_id"],
        )
    else:
        wx_nick = await _allocate_unique_display_nickname_for_new_user(db, nickname)
        created = await db.fetchrow(
            """
            INSERT INTO users (nickname, points, free_points, paid_points, role)
            VALUES ($1, $2, $2, 0, 'student')
            RETURNING id, nickname, avatar, primary_email, primary_phone, points, free_points, redeemed_points, paid_points, role
            """,
            wx_nick,
            FREE_POINTS_REFRESH_AMOUNT,
        )
        await db.execute(
            "INSERT INTO user_identities (user_id, provider, identifier) VALUES ($1, 'wechat', $2)",
            created["id"],
            openid,
        )
        user = created

    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="账户已被禁用")

    access_token = AuthManager.create_access_token(
        data={"sub": str(user["id"])},
        expires_delta=timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    session_idle.register_login_session(request, str(user["id"]))
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": _user_response(user),
    }


@router.get("/identities")
async def get_identities(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """获取当前用户已绑定的登录方式列表（用于个人中心展示与合并选择）。"""
    app_state = request.app.state
    if not getattr(app_state, "db_connected", False):
        return {"items": []}
    db = app_state.db
    user_id = current_user.get("id") or current_user.get("sub")
    rows = await db.fetch(
        "SELECT provider, identifier, linked_at FROM user_identities WHERE user_id = $1 ORDER BY linked_at",
        user_id,
    )
    items = [
        {
            "provider": r["provider"],
            "provider_label": PROVIDER_LABELS.get(r["provider"], r["provider"]),
            "identifier_masked": _mask_identifier(r["provider"], r["identifier"] or ""),
            "linked_at": r["linked_at"].isoformat() if getattr(r["linked_at"], "isoformat", None) else str(r["linked_at"]),
        }
        for r in rows
    ]
    return {"items": items}


@router.patch("/profile")
async def update_profile(
    body: dict, request: Request, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """更新个人资料：昵称（个人中心显示名称）或从某绑定账号同步昵称。"""
    app_state = request.app.state
    if not getattr(app_state, "db_connected", False):
        raise HTTPException(status_code=503, detail="数据库未连接")
    db = app_state.db
    user_id = current_user.get("id") or current_user.get("sub")
    nickname = body.get("nickname")
    display_name_from = body.get("display_name_from")  # "email" | "phone" | "wechat" | "github" | "account"

    if display_name_from:
        row = await db.fetchrow(
            "SELECT identifier FROM user_identities WHERE user_id = $1 AND provider = $2",
            user_id,
            display_name_from,
        )
        if row and row.get("identifier"):
            ident = row["identifier"]
            if display_name_from == "email" and "@" in ident:
                nickname = ident.split("@")[0]
            elif display_name_from == "phone":
                nickname = ident[-4:] if len(ident) >= 4 else ident
            else:
                nickname = ident[:20] if ident else nickname
        else:
            nickname = None
    if nickname is not None:
        nickname = _normalize_profile_nickname(nickname)
    if nickname is not None:
        if await _profile_display_name_taken_by_other(db, nickname, str(user_id)):
            raise HTTPException(status_code=400, detail="该显示名称已被其他用户使用，请换一个")
        try:
            await db.execute("UPDATE users SET nickname = $1 WHERE id = $2", nickname, user_id)
        except asyncpg.exceptions.UniqueViolationError:
            raise HTTPException(status_code=400, detail="该显示名称已被使用，请换一个") from None
    user = await db.fetchrow(
        "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, paid_points, gift_points, free_points_refreshed_at, role FROM users WHERE id = $1",
        user_id,
    )
    return {"user": _user_response(user)}


@router.post("/bind-phone")
async def bind_phone(phone_data: dict, request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """绑定手机号（需验证码）。若该手机已绑定其他账号则合并，可选 use_other_nickname 保留对方昵称。"""
    app_state = request.app.state
    if not getattr(app_state, "db_connected", False):
        raise HTTPException(status_code=503, detail="数据库未连接")
    db = app_state.db
    phone = phone_data.get("phone")
    phone_code = phone_data.get("phone_code")
    if not phone or not re.match(r"^1[3-9]\d{9}$", phone):
        raise HTTPException(status_code=400, detail="手机号格式不正确")
    user_id = str(current_user.get("id") or current_user.get("sub"))

    # 验证码校验
    cache = getattr(app_state, "cache", None)
    cache_connected = getattr(app_state, "cache_connected", False)
    key = f"phone_{phone}"
    stored_code = None
    if cache_connected and cache:
        stored = cache.get_verification_code(key)
        stored_code = _get_code_from_stored(stored)
        if stored_code:
            cache.delete_verification_code(key)
    else:
        info = verification_codes.get(key)
        if info and isinstance(info, dict):
            exp = info.get("expires_at")
            if exp and datetime.now(timezone.utc) < exp:
                stored_code = info.get("code")
            verification_codes.pop(key, None)
    if not stored_code or stored_code != phone_code:
        raise HTTPException(status_code=400, detail="手机验证码错误或已过期")

    existing = await db.fetchrow(
        "SELECT user_id FROM user_identities WHERE provider = 'phone' AND identifier = $1",
        phone,
    )
    use_other_nickname = bool(phone_data.get("use_other_nickname"))

    if existing:
        other_id = str(existing["user_id"])
        if other_id == user_id:
            await db.execute("UPDATE users SET primary_phone = $1 WHERE id = $2", phone, user_id)
            await db.execute(
                "INSERT INTO user_identities (user_id, provider, identifier) VALUES ($1, 'phone', $2) ON CONFLICT (user_id, provider) DO UPDATE SET identifier = EXCLUDED.identifier",
                user_id,
                phone,
            )
        else:
            # 该手机号已属于另一用户：将该用户合并到当前用户（与 bind_account / bind_github 一致）
            await _merge_other_user_into_current(db, user_id, other_id, use_other_nickname)
            await db.execute("UPDATE users SET primary_phone = $1 WHERE id = $2", phone, user_id)
            user = await db.fetchrow(
                "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, paid_points, gift_points, free_points_refreshed_at, role FROM users WHERE id = $1",
                user_id,
            )
            return {"phone": phone, "user": _user_response(user), "merged": True}
    else:
        await db.execute("UPDATE users SET primary_phone = $1 WHERE id = $2", phone, user_id)
        await db.execute(
            "INSERT INTO user_identities (user_id, provider, identifier) VALUES ($1, 'phone', $2) ON CONFLICT (user_id, provider) DO UPDATE SET identifier = EXCLUDED.identifier",
            user_id,
            phone,
        )

    user = await db.fetchrow(
        "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, paid_points, gift_points, free_points_refreshed_at, role FROM users WHERE id = $1",
        user_id,
    )
    return {"phone": phone, "user": _user_response(user), "merged": False}


@router.post("/bind-email")
async def bind_email(body: dict, request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """绑定邮箱（需验证码）。若该邮箱已绑定其他账号则合并，可选 use_other_nickname。"""
    app_state = request.app.state
    if not getattr(app_state, "db_connected", False):
        raise HTTPException(status_code=503, detail="数据库未连接")
    db = app_state.db
    email = (body.get("email") or "").strip()
    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    user_id = str(current_user.get("id") or current_user.get("sub"))
    code = (body.get("email_code") or "").strip()
    code = str(code)  # 统一为字符串，避免 JSON 传数字导致比较失败
    key = f"email_{email}"
    cache = getattr(app_state, "cache", None)
    cache_connected = getattr(app_state, "cache_connected", False)
    stored_code = None
    if cache_connected and cache:
        stored = cache.get_verification_code(key)
        stored_code = _get_code_from_stored(stored)
        if stored_code:
            cache.delete_verification_code(key)
    else:
        info = verification_codes.get(key)
        if info and isinstance(info, dict):
            exp = info.get("expires_at")
            if exp and datetime.now(timezone.utc) < exp:
                stored_code = info.get("code")
            verification_codes.pop(key, None)
    stored_code = str(stored_code).strip() if stored_code else None
    if not stored_code or stored_code != code:
        raise HTTPException(status_code=400, detail="邮箱验证码错误或已过期")
    existing = await db.fetchrow(
        "SELECT user_id FROM user_identities WHERE provider = 'email' AND identifier = $1",
        email,
    )
    use_other_nickname = bool(body.get("use_other_nickname"))
    if existing:
        other_id = str(existing["user_id"])
        if other_id == user_id:
            await db.execute("UPDATE users SET primary_email = $1 WHERE id = $2", email, user_id)
            await db.execute(
                "INSERT INTO user_identities (user_id, provider, identifier) VALUES ($1, 'email', $2) ON CONFLICT (user_id, provider) DO UPDATE SET identifier = EXCLUDED.identifier",
                user_id,
                email,
            )
        else:
            # 该邮箱已属于另一用户：将该用户合并到当前用户（与 bind_account / bind_github 一致）
            await _merge_other_user_into_current(db, user_id, other_id, use_other_nickname)
            await db.execute("UPDATE users SET primary_email = $1 WHERE id = $2", email, user_id)
            user = await db.fetchrow(
                "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, paid_points, gift_points, free_points_refreshed_at, role FROM users WHERE id = $1",
                user_id,
            )
            return {"email": email, "user": _user_response(user), "merged": True}
    else:
        await db.execute("UPDATE users SET primary_email = $1 WHERE id = $2", email, user_id)
        await db.execute(
            "INSERT INTO user_identities (user_id, provider, identifier) VALUES ($1, 'email', $2) ON CONFLICT (user_id, provider) DO UPDATE SET identifier = EXCLUDED.identifier",
            user_id,
            email,
        )
    user = await db.fetchrow(
        "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, paid_points, gift_points, free_points_refreshed_at, role FROM users WHERE id = $1",
        user_id,
    )
    return {"email": email, "user": _user_response(user), "merged": False}


@router.post("/bind-wechat")
async def bind_wechat(body: dict, request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """绑定微信（传 code 由服务端换 openid）。若该微信已绑定其他账号则合并，可选 use_other_nickname。"""
    app_state = request.app.state
    if not getattr(app_state, "db_connected", False):
        raise HTTPException(status_code=503, detail="数据库未连接")
    db = app_state.db
    code = body.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="缺少微信授权 code")
    user_id = str(current_user.get("id") or current_user.get("sub"))
    openid = None
    if Config.WECHAT_APPID and Config.WECHAT_SECRET:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.weixin.qq.com/sns/oauth2/access_token",
                    params={
                        "appid": Config.WECHAT_APPID,
                        "secret": Config.WECHAT_SECRET,
                        "code": code,
                        "grant_type": "authorization_code",
                    },
                    timeout=10,
                ) as resp:
                    data = await resp.json()
                openid = data.get("openid") if isinstance(data, dict) else None
        except Exception as e:
            logger.error(f"bind-wechat 换取 openid 失败: {e}")
    if not openid:
        openid = f"dev_wechat_{code[:12]}"
    existing = await db.fetchrow(
        "SELECT user_id FROM user_identities WHERE provider = 'wechat' AND identifier = $1",
        openid,
    )
    if existing:
        other_id = str(existing["user_id"])
        if other_id != user_id:
            use_other_nickname = bool(body.get("use_other_nickname"))
            await _merge_other_user_into_current(db, user_id, other_id, use_other_nickname)
            user = await db.fetchrow(
                "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, paid_points, gift_points, free_points_refreshed_at, role FROM users WHERE id = $1",
                user_id,
            )
            return {"user": _user_response(user), "merged": True}
        user = await db.fetchrow(
            "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, paid_points, gift_points, free_points_refreshed_at, role FROM users WHERE id = $1",
            user_id,
        )
        return {"user": _user_response(user), "merged": False}
    await db.execute(
        "INSERT INTO user_identities (user_id, provider, identifier) VALUES ($1, 'wechat', $2) ON CONFLICT (user_id, provider) DO UPDATE SET identifier = EXCLUDED.identifier",
        user_id,
        openid,
    )
    user = await db.fetchrow(
        "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, paid_points, gift_points, free_points_refreshed_at, role FROM users WHERE id = $1",
        user_id,
    )
    return {"user": _user_response(user), "merged": False}


@router.post("/bind-github")
async def bind_github(body: dict, request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """绑定 GitHub（传 code）。若该 GitHub 已绑定其他账号则合并，可选 use_other_nickname。"""
    app_state = request.app.state
    if not getattr(app_state, "db_connected", False):
        raise HTTPException(status_code=503, detail="数据库未连接")
    db = app_state.db
    code = body.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="缺少 GitHub 授权 code")
    ru_raw = body.get("redirect_uri")
    redirect_uri_oauth = (ru_raw.strip() if isinstance(ru_raw, str) and ru_raw.strip() else None)
    user_id = str(current_user.get("id") or current_user.get("sub"))
    github_id = None
    if Config.GITHUB_CLIENT_ID and Config.GITHUB_CLIENT_SECRET:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://github.com/login/oauth/access_token",
                    data=_github_oauth_token_request_body(str(code), redirect_uri_oauth),
                    headers={"Accept": "application/json"},
                    timeout=10,
                ) as resp:
                    token_data = await resp.json()
                access_token = token_data.get("access_token") if isinstance(token_data, dict) else None
                if not access_token and isinstance(token_data, dict):
                    logger.warning(
                        "bind-github: 换票未返回 access_token: %s",
                        token_data.get("error_description") or token_data.get("error") or token_data,
                    )
                if access_token:
                    async with session.get(
                        "https://api.github.com/user",
                        headers={"Authorization": f"token {access_token}"},
                        timeout=10,
                    ) as resp:
                        ud = await resp.json()
                    github_id = _github_oauth_identifier_from_api(ud)
        except Exception as e:
            logger.error(f"bind-github 失败: {e}")
    if not github_id:
        if _github_oauth_secrets_configured():
            raise HTTPException(
                status_code=400,
                detail=(
                    "GitHub 绑定失败：换票未成功或无法解析用户 id。"
                    "请确认回调 redirect_uri 与发起授权时完全一致（个人中心绑定一般含 bind=github），"
                    "并在 GitHub OAuth 应用的 Authorized callback URLs 中登记该完整地址。"
                ),
            )
        github_id = _dev_github_identifier_from_code(code)
    existing_other_uid = await _lookup_user_id_by_github_identifier(db, github_id)
    if existing_other_uid:
        other_id = str(existing_other_uid)
        if other_id != user_id:
            # 与 bind_account 一致：将该 GitHub 所属用户合并到当前用户，积分相加，只保留一个账号
            use_other_nickname = bool(body.get("use_other_nickname"))
            await _merge_other_user_into_current(db, user_id, other_id, use_other_nickname)
            user = await db.fetchrow(
                "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, paid_points, gift_points, free_points_refreshed_at, role FROM users WHERE id = $1",
                user_id,
            )
            return {"user": _user_response(user), "merged": True}
        user = await db.fetchrow(
            "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, paid_points, gift_points, free_points_refreshed_at, role FROM users WHERE id = $1",
            user_id,
        )
        return {"user": _user_response(user), "merged": False}
    await db.execute(
        "INSERT INTO user_identities (user_id, provider, identifier) VALUES ($1, 'github', $2) ON CONFLICT (user_id, provider) DO UPDATE SET identifier = EXCLUDED.identifier",
        user_id,
        github_id,
    )
    user = await db.fetchrow(
        "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, paid_points, gift_points, free_points_refreshed_at, role FROM users WHERE id = $1",
        user_id,
    )
    return {"user": _user_response(user), "merged": False}


@router.post("/bind-account")
async def bind_account(body: dict, request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """绑定账号（用户名+密码）。若该账号已存在且属于其他用户则合并到当前用户；若已属于当前用户则视为已绑定。"""
    app_state = request.app.state
    if not getattr(app_state, "db_connected", False):
        raise HTTPException(status_code=503, detail="数据库未连接")
    db = app_state.db
    username = (body.get("username") or "").strip()
    password = body.get("password")
    if not username:
        raise HTTPException(status_code=400, detail="请输入账号名")
    if not password:
        raise HTTPException(status_code=400, detail="请输入密码")
    user_id = str(current_user.get("id") or current_user.get("sub"))

    # 当前用户已绑定的账号（每个用户只能有一个 account 身份）
    current_account = await db.fetchrow(
        "SELECT identifier FROM user_identities WHERE user_id = $1 AND provider = 'account'",
        user_id,
    )
    if current_account:
        if current_account["identifier"] == username:
            user = await db.fetchrow(
                "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, paid_points, gift_points, free_points_refreshed_at, role FROM users WHERE id = $1",
                user_id,
            )
            return {"username": username, "user": _user_response(user), "merged": False}
        raise HTTPException(status_code=400, detail="您已绑定过账号，无法再绑定其他账号")

    existing = await db.fetchrow(
        "SELECT user_id, credential FROM user_identities WHERE provider = 'account' AND identifier = $1",
        username,
    )
    if not existing:
        raise HTTPException(status_code=400, detail="该账号不存在，请先注册")
    cred = existing.get("credential")
    if isinstance(cred, str):
        try:
            cred = json.loads(cred) if cred else {}
        except Exception:
            cred = {}
    elif cred is None:
        cred = {}
    if not isinstance(cred, dict):
        cred = {}
    password_hash = cred.get("password_hash") if isinstance(cred, dict) else None
    if not password_hash or not verify_password(password, password_hash):
        raise HTTPException(status_code=401, detail="密码错误")
    other_id = str(existing["user_id"])
    if other_id != user_id:
        use_other_nickname = bool(body.get("use_other_nickname"))
        await _merge_other_user_into_current(db, user_id, other_id, use_other_nickname)
        user = await db.fetchrow(
            "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, paid_points, gift_points, free_points_refreshed_at, role FROM users WHERE id = $1",
            user_id,
        )
        return {"username": username, "user": _user_response(user), "merged": True}
    user = await db.fetchrow(
        "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, paid_points, gift_points, free_points_refreshed_at, role FROM users WHERE id = $1",
        user_id,
    )
    return {"username": username, "user": _user_response(user), "merged": False}


async def _unbind_identity_to_new_user(db: Any, current_user_id: str, provider: str) -> None:
    """解绑时将被解绑的身份「拆出」为独立新用户；该身份带走合并时带入的免费/付费积分（从当前用户按免费扣免费、付费扣付费）。"""
    row = await db.fetchrow(
        """SELECT identifier, credential,
           COALESCE(credits_contributed, 0) AS credits_contributed,
           COALESCE(free_contributed, 0) AS free_contributed,
           COALESCE(redeemed_contributed, 0) AS redeemed_contributed,
           COALESCE(paid_contributed, 0) AS paid_contributed
           FROM user_identities WHERE user_id = $1 AND provider = $2""",
        current_user_id,
        provider,
    )
    if not row:
        raise HTTPException(status_code=400, detail=f"未绑定{PROVIDER_LABELS.get(provider, provider)}")
    count = await db.fetchval("SELECT COUNT(*) FROM user_identities WHERE user_id = $1", current_user_id)
    if count <= 1:
        raise HTTPException(status_code=400, detail="至少保留一种登录方式，无法解绑")
    identifier = str(row["identifier"] or "")
    cred = row.get("credential")
    cred_json = json.dumps(cred) if cred is not None and not isinstance(cred, str) else (cred or "{}")
    free_contributed = int(row.get("free_contributed") or 0)
    redeemed_contributed = int(row.get("redeemed_contributed") or 0)
    paid_contributed = int(row.get("paid_contributed") or 0)
    # 兼容旧数据：仅有 credits_contributed 时，按免费->兑换->付费拆分
    if free_contributed == 0 and redeemed_contributed == 0 and paid_contributed == 0:
        legacy = int(row.get("credits_contributed") or 0)
        if legacy > 0:
            row_points = await db.fetchrow(
                "SELECT COALESCE(free_points, 0) AS free_points, COALESCE(redeemed_points, 0) AS redeemed_points, COALESCE(paid_points, 0) AS paid_points FROM users WHERE id = $1",
                current_user_id,
            )
            cur_f = int((row_points.get("free_points") or 0) if row_points else 0)
            cur_r = int((row_points.get("redeemed_points") or 0) if row_points else 0)
            cur_p = int((row_points.get("paid_points") or 0) if row_points else 0)
            free_contributed = min(legacy, cur_f)
            left = max(0, legacy - free_contributed)
            redeemed_contributed = min(left, cur_r)
            left = max(0, left - redeemed_contributed)
            paid_contributed = min(left, cur_p)
    row_points = await db.fetchrow(
        "SELECT COALESCE(free_points, 0) AS free_points, COALESCE(redeemed_points, 0) AS redeemed_points, COALESCE(paid_points, 0) AS paid_points FROM users WHERE id = $1",
        current_user_id,
    )
    cur_free = int((row_points.get("free_points") or 0) if row_points else 0)
    cur_redeemed = int((row_points.get("redeemed_points") or 0) if row_points else 0)
    cur_paid = int((row_points.get("paid_points") or 0) if row_points else 0)
    deduct_free = min(free_contributed, cur_free)
    deduct_redeemed = min(redeemed_contributed, cur_redeemed)
    deduct_paid = min(paid_contributed, cur_paid)
    total_give = deduct_free + deduct_redeemed + deduct_paid
    if total_give == 0:
        total_give = min(FREE_POINTS_REFRESH_AMOUNT, cur_free)
        deduct_free = total_give
        deduct_redeemed = 0
        deduct_paid = 0

    # 新用户昵称（与全站显示名唯一性一致）
    if provider == "account":
        nick_base = identifier[:50] if identifier else "用户"
    elif provider == "email":
        nick_base = (identifier.split("@")[0][:30] + "（邮箱）") if "@" in identifier else "邮箱用户"
    elif provider == "phone":
        nick_base = "手机" + (identifier[-4:] if len(identifier) >= 4 else identifier)
    else:
        nick_base = identifier[:20] if identifier else "用户"
    nickname = await _allocate_unique_display_nickname_for_new_user(db, nick_base)

    # 创建新用户：免费/兑换/付费与拆出一致
    new_row = await db.fetchrow(
        """
        INSERT INTO users (nickname, points, free_points, redeemed_points, paid_points, role, is_active)
        VALUES ($1, $2, $3, $4, $5, 'student', TRUE)
        RETURNING id
        """,
        nickname,
        total_give,
        deduct_free,
        deduct_redeemed,
        deduct_paid,
    )
    new_user_id = str(new_row["id"])

    await db.execute("DELETE FROM user_identities WHERE user_id = $1 AND provider = $2", current_user_id, provider)
    if provider == "email":
        await db.execute("UPDATE users SET primary_email = NULL WHERE id = $1", current_user_id)
    elif provider == "phone":
        await db.execute("UPDATE users SET primary_phone = NULL WHERE id = $1 AND primary_phone = $2", current_user_id, identifier)

    if provider == "account":
        await db.execute(
            """INSERT INTO user_identities (user_id, provider, identifier, credential, credits_contributed, free_contributed, redeemed_contributed, paid_contributed)
               VALUES ($1, $2, $3, $4::jsonb, 0, 0, 0, 0)""",
            new_user_id,
            provider,
            identifier,
            cred_json,
        )
    else:
        await db.execute(
            """INSERT INTO user_identities (user_id, provider, identifier, credits_contributed, free_contributed, redeemed_contributed, paid_contributed)
               VALUES ($1, $2, $3, 0, 0, 0, 0)""",
            new_user_id,
            provider,
            identifier,
        )
    if provider == "email":
        await db.execute("UPDATE users SET primary_email = $1 WHERE id = $2", identifier, new_user_id)
    elif provider == "phone":
        await db.execute("UPDATE users SET primary_phone = $1 WHERE id = $2", identifier, new_user_id)

    # 从当前用户扣减：免费扣免费、付费扣付费（该身份带走自己合并时带入的部分）
    if deduct_free > 0 or deduct_redeemed > 0 or deduct_paid > 0:
        await db.execute(
            """
            UPDATE users SET
                free_points = free_points - $1,
                redeemed_points = redeemed_points - $2,
                paid_points = paid_points - $3,
                points = COALESCE(points, 0) - $4
            WHERE id = $5
            """,
            deduct_free,
            deduct_redeemed,
            deduct_paid,
            total_give,
            current_user_id,
        )


@router.post("/unbind-account")
async def unbind_account(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """解绑账号（用户名+密码）登录方式；该账号将变为独立新用户，用其登录后不再看到当前账号的绑定。至少保留一种登录方式。"""
    app_state = request.app.state
    if not getattr(app_state, "db_connected", False):
        raise HTTPException(status_code=503, detail="数据库未连接")
    db = app_state.db
    user_id = str(current_user.get("id") or current_user.get("sub"))
    await _unbind_identity_to_new_user(db, user_id, "account")
    user = await db.fetchrow(
        "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, paid_points, gift_points, free_points_refreshed_at, role FROM users WHERE id = $1",
        user_id,
    )
    return {"user": _user_response(user)}


@router.post("/send-unbind-phone-code")
async def send_unbind_phone_code(body: dict, request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """解绑手机前：校验图形验证码后向已绑定手机号发送短信验证码。"""
    captcha_id = body.get("captcha_id") or ""
    captcha_code = body.get("captcha_code") or ""
    if not captcha_id or not captcha_code:
        raise HTTPException(status_code=400, detail="请先获取并输入图形验证码")
    app_state = request.app.state
    if not getattr(app_state, "db_connected", False):
        raise HTTPException(status_code=503, detail="数据库未连接")
    _verify_captcha_or_raise(request, captcha_id, captcha_code)
    db = app_state.db
    user_id = str(current_user.get("id") or current_user.get("sub"))
    row = await db.fetchrow(
        "SELECT identifier FROM user_identities WHERE user_id = $1 AND provider = 'phone'",
        user_id,
    )
    if not row:
        raise HTTPException(status_code=400, detail="未绑定手机号")
    phone = str(row["identifier"] or "")
    if not re.match(r"^1[3-9]\d{9}$", phone):
        raise HTTPException(status_code=400, detail="绑定的手机号格式异常")
    code = str(random.randint(100000, 999999))
    expire_seconds = getattr(Config, "SMS_PHONE_CODE_EXPIRE_SECONDS", 300)
    cache = getattr(app_state, "cache", None)
    cache_connected = getattr(app_state, "cache_connected", False)
    if cache_connected and cache:
        cache.set_verification_code(phone, code, expire_seconds=expire_seconds)
    else:
        verification_codes[phone] = {"code": code, "created_at": datetime.now(timezone.utc)}
    if _sms_configured():
        try:
            await asyncio.to_thread(_send_sms_sync, phone, code)
        except Exception as e:
            logger.error(f"解绑验证短信发送失败: {e}")
            raise HTTPException(status_code=500, detail="验证码发送失败，请稍后重试")
    return {"message": "验证码已发送到您的绑定手机，请查收（5分钟内有效）"}


@router.post("/send-unbind-email-code")
async def send_unbind_email_code(body: dict, request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """解绑邮箱前：校验图形验证码后向已绑定邮箱发送验证码。"""
    captcha_id = body.get("captcha_id") or ""
    captcha_code = body.get("captcha_code") or ""
    if not captcha_id or not captcha_code:
        raise HTTPException(status_code=400, detail="请先获取并输入图形验证码")
    app_state = request.app.state
    if not getattr(app_state, "db_connected", False):
        raise HTTPException(status_code=503, detail="数据库未连接")
    _verify_captcha_or_raise(request, captcha_id, captcha_code)
    db = app_state.db
    user_id = str(current_user.get("id") or current_user.get("sub"))
    row = await db.fetchrow(
        "SELECT identifier FROM user_identities WHERE user_id = $1 AND provider = 'email'",
        user_id,
    )
    if not row:
        raise HTTPException(status_code=400, detail="未绑定邮箱")
    email = str(row["identifier"] or "")
    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
        raise HTTPException(status_code=400, detail="绑定的邮箱格式异常")
    code = str(random.randint(100000, 999999))
    expire_seconds = getattr(Config, "EMAIL_CODE_EXPIRE_SECONDS", 900)
    key = f"email_{email}"
    cache = getattr(app_state, "cache", None)
    cache_connected = getattr(app_state, "cache_connected", False)
    if cache_connected and cache:
        cache.set_verification_code(key, code, expire_seconds=expire_seconds)
    else:
        verification_codes[key] = {
            "code": code,
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=expire_seconds),
        }
    smtp_configured = bool(Config.SMTP_HOST and Config.SMTP_USER and Config.SMTP_PASSWORD)
    if smtp_configured:
        try:
            await asyncio.to_thread(_send_email_sync, email, code, "您的解绑验证码")
        except Exception as e:
            logger.error(f"解绑验证邮件发送失败: {e}")
            raise HTTPException(status_code=500, detail="验证码发送失败，请稍后重试")
    return {"message": "验证码已发送到您的绑定邮箱，请查收（15分钟内有效）"}


@router.post("/unbind-phone")
async def unbind_phone(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """解绑手机号。需先调用 send-unbind-phone-code 获取短信验证码，传 phone_code 验证后解绑。至少保留一种登录方式。"""
    try:
        raw = await request.body()
        body = json.loads(raw) if raw else {}
    except Exception:
        body = {}
    app_state = request.app.state
    if not getattr(app_state, "db_connected", False):
        raise HTTPException(status_code=503, detail="数据库未连接")
    db = app_state.db
    user_id = str(current_user.get("id") or current_user.get("sub"))
    row = await db.fetchrow(
        "SELECT identifier FROM user_identities WHERE user_id = $1 AND provider = 'phone'",
        user_id,
    )
    if not row:
        raise HTTPException(status_code=400, detail="未绑定手机号")
    phone = str(row["identifier"] or "")
    phone_code = (body.get("phone_code") or "").strip()
    if not phone_code:
        raise HTTPException(status_code=400, detail="请输入手机验证码")
    cache = getattr(app_state, "cache", None)
    cache_connected = getattr(app_state, "cache_connected", False)
    stored_code = None
    if cache_connected and cache:
        stored = cache.get_verification_code(phone)
        stored_code = _get_code_from_stored(stored)
        if stored_code:
            cache.delete_verification_code(phone)
    else:
        info = verification_codes.get(phone)
        if info and isinstance(info, dict):
            exp = info.get("expires_at")
            if exp and datetime.now(timezone.utc) < exp:
                stored_code = info.get("code")
            verification_codes.pop(phone, None)
    if not stored_code or stored_code != phone_code:
        raise HTTPException(status_code=400, detail="手机验证码错误或已过期")
    await _unbind_identity_to_new_user(db, user_id, "phone")
    user = await db.fetchrow(
        "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, paid_points, gift_points, free_points_refreshed_at, role FROM users WHERE id = $1",
        user_id,
    )
    return {"user": _user_response(user) if user else {}}


@router.post("/unbind-email")
async def unbind_email(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """解绑邮箱。需先调用 send-unbind-email-code 获取邮箱验证码，传 email_code 验证后解绑。至少保留一种登录方式。"""
    try:
        raw = await request.body()
        body = json.loads(raw) if raw else {}
    except Exception:
        body = {}
    app_state = request.app.state
    if not getattr(app_state, "db_connected", False):
        raise HTTPException(status_code=503, detail="数据库未连接")
    db = app_state.db
    user_id = str(current_user.get("id") or current_user.get("sub"))
    row = await db.fetchrow(
        "SELECT identifier FROM user_identities WHERE user_id = $1 AND provider = 'email'",
        user_id,
    )
    if not row:
        raise HTTPException(status_code=400, detail="未绑定邮箱")
    email = str(row["identifier"] or "")
    email_code = (body.get("email_code") or "").strip()
    if not email_code:
        raise HTTPException(status_code=400, detail="请输入邮箱验证码")
    key = f"email_{email}"
    cache = getattr(app_state, "cache", None)
    cache_connected = getattr(app_state, "cache_connected", False)
    stored_code = None
    if cache_connected and cache:
        stored = cache.get_verification_code(key)
        stored_code = _get_code_from_stored(stored)
        if stored_code:
            cache.delete_verification_code(key)
    else:
        info = verification_codes.get(key)
        if info and isinstance(info, dict):
            exp = info.get("expires_at")
            if exp and datetime.now(timezone.utc) < exp:
                stored_code = info.get("code")
            verification_codes.pop(key, None)
    # 统一为字符串再比较（Redis/JSON 可能返回 int）
    stored_code = str(stored_code).strip() if stored_code else None
    if not stored_code or stored_code != email_code:
        raise HTTPException(status_code=400, detail="邮箱验证码错误或已过期")
    try:
        await _unbind_identity_to_new_user(db, user_id, "email")
        user = await db.fetchrow(
            "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, paid_points, gift_points, free_points_refreshed_at, role FROM users WHERE id = $1",
            user_id,
        )
        return {"user": _user_response(user) if user else {}}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("解绑邮箱失败: %s", e)
        raise HTTPException(status_code=500, detail=f"解绑失败：{str(e)}")


@router.post("/unbind-wechat")
async def unbind_wechat(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """解绑微信；该微信将变为独立新用户，用其登录后不再看到当前账号的绑定。至少保留一种登录方式。"""
    app_state = request.app.state
    if not getattr(app_state, "db_connected", False):
        raise HTTPException(status_code=503, detail="数据库未连接")
    db = app_state.db
    user_id = str(current_user.get("id") or current_user.get("sub"))
    await _unbind_identity_to_new_user(db, user_id, "wechat")
    user = await db.fetchrow(
        "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, paid_points, gift_points, free_points_refreshed_at, role FROM users WHERE id = $1",
        user_id,
    )
    return {"user": _user_response(user)}


@router.post("/unbind-github")
async def unbind_github(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """解绑 GitHub；该 GitHub 将变为独立新用户，用其登录后不再看到当前账号的绑定。至少保留一种登录方式。"""
    app_state = request.app.state
    if not getattr(app_state, "db_connected", False):
        raise HTTPException(status_code=503, detail="数据库未连接")
    db = app_state.db
    user_id = str(current_user.get("id") or current_user.get("sub"))
    await _unbind_identity_to_new_user(db, user_id, "github")
    user = await db.fetchrow(
        "SELECT id, nickname, avatar, primary_email, primary_phone, points, free_points, paid_points, gift_points, free_points_refreshed_at, role FROM users WHERE id = $1",
        user_id,
    )
    return {"user": _user_response(user)}


@router.post("/admin/login")
async def admin_login(login_data: AdminLogin, request: Request):
    """管理员登录（与 api/admin 一致：通过 user_identities 校验）"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(status_code=503, detail="数据库未连接")
    db = app_state.db
    ident = await db.fetchrow(
        "SELECT user_id, credential FROM user_identities WHERE provider = 'account' AND identifier = $1",
        login_data.username,
    )
    if not ident:
        raise HTTPException(status_code=401, detail="用户名或密码错误，或非管理员账户")
    cred = ident.get("credential")
    if isinstance(cred, str):
        try:
            cred = json.loads(cred) if cred else {}
        except Exception:
            cred = {}
    elif cred is None:
        cred = {}
    password_hash = cred.get("password_hash") if isinstance(cred, dict) else None
    if not password_hash or not verify_password(login_data.password, password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误，或非管理员账户")
    user = await db.fetchrow(
        "SELECT id, nickname, primary_email, role, is_active FROM users WHERE id = $1 AND role = 'admin'",
        ident["user_id"],
    )
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误，或非管理员账户")
    if not user.get("is_active"):
        raise HTTPException(status_code=403, detail="账户已被禁用")
    access_token = AuthManager.create_access_token(
        data={"sub": str(user["id"]), "role": "admin"},
        expires_delta=timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    session_idle.register_login_session(request, str(user["id"]))
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user["id"]),
            "username": user.get("nickname"),
            "email": user.get("primary_email"),
            "role": user.get("role"),
        },
    }


# 导出
__all__ = ["router"]
