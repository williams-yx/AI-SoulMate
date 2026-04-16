"""
管理员相关的 API 路由
"""

from typing import Dict, Any, Optional
import os
import csv
import io

from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.responses import HTMLResponse, Response
from datetime import datetime, timezone

from schemas import AdminLogin
from auth import verify_password
from core.security import AuthManager
from core import session_idle
from api.dependencies import get_admin_user
from logger import logger

router = APIRouter(prefix="/api/admin", tags=["管理员"])


# 操作日志记录
async def log_operation(request: Request, admin_id: str, action: str, resource_type: str, resource_id: str = None, details: Dict[str, Any] = None):
    """记录管理员操作日志"""
    try:
        app_state = request.app.state
        if hasattr(app_state, 'db_connected') and app_state.db_connected:
            import json
            db = app_state.db
            await db.execute("""
                INSERT INTO operation_logs (admin_id, action, resource_type, resource_id, details, created_at)
                VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
            """, admin_id, action, resource_type, resource_id, json.dumps(details) if details else None)
    except Exception as e:
        logger.error(f"记录操作日志失败: {e}")  # 日志记录失败不应影响主流程


@router.post("/login")
async def admin_login(login_data: AdminLogin, request: Request):
    """管理员登录"""
    app_state = request.app.state
    if not hasattr(app_state, 'db_connected') or not app_state.db_connected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接")
    
    db = app_state.db
    
    # 新结构：通过 user_identities(provider='account') 查管理员并校验密码
    ident = await db.fetchrow(
        "SELECT user_id, credential FROM user_identities WHERE provider = 'account' AND identifier = $1",
        login_data.username,
    )
    if not ident:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误，或非管理员账户")
    import json
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误，或非管理员账户")
    user = await db.fetchrow(
        "SELECT id, nickname, primary_email, primary_phone, role, is_active FROM users WHERE id = $1 AND role = 'admin'",
        ident["user_id"],
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误，或非管理员账户")
    if not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已被禁用")
    from datetime import timedelta
    access_token = AuthManager.create_access_token(
        data={"sub": str(user["id"]), "role": "admin"},
        expires_delta=timedelta(hours=24),
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


@router.get("/stats")
async def get_admin_stats(
    request: Request,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
):
    """获取系统统计数据（管理员）。必须登录且具备 admin 角色。"""
    app_state = request.app.state
    if not hasattr(app_state, 'db_connected') or not app_state.db_connected:
        return {
            "users": {"total": 0, "active": 0},
            "assets": {"total": 0, "published": 0},
            "orders": {"total": 0, "pending": 0},
            "revenue": {"total": 0.0, "today": 0.0},
            "workflows": 0,
            "devices": 0,
            "print_jobs": 0,
            "note": "数据库未连接，返回空数据"
        }
    
    try:
        db = app_state.db
        
        # 用户统计
        users_count = await db.fetchrow("SELECT COUNT(*) as count FROM users")
        active_users = await db.fetchrow("SELECT COUNT(*) as count FROM users WHERE is_active = TRUE")
        
        # 作品统计
        assets_count = await db.fetchrow("SELECT COUNT(*) as count FROM assets")
        published_assets = await db.fetchrow("SELECT COUNT(*) as count FROM assets WHERE is_published = TRUE")
        
        # 订单统计
        orders_count = await db.fetchrow("SELECT COUNT(*) as count FROM orders")
        pending_orders = await db.fetchrow("SELECT COUNT(*) as count FROM orders WHERE status = 'pending'")
        
        # 交易额统计
        total_revenue = await db.fetchrow(
            "SELECT COALESCE(SUM(total_amount), 0) as total FROM orders WHERE status IN ('paid', 'shipped', 'completed')"
        )
        today_revenue = await db.fetchrow(
            "SELECT COALESCE(SUM(total_amount), 0) as total FROM orders WHERE status IN ('paid', 'shipped', 'completed') AND DATE(created_at) = CURRENT_DATE"
        )
        
        # 工作流统计
        workflows_count = await db.fetchrow("SELECT COUNT(*) as count FROM workflows")
        
        # 设备统计
        devices_count = await db.fetchrow("SELECT COUNT(*) as count FROM devices")
        
        # 打印任务统计
        print_jobs_count = await db.fetchrow("SELECT COUNT(*) as count FROM print_jobs")
        
        return {
            "users": {
                "total": users_count['count'] if users_count else 0,
                "active": active_users['count'] if active_users else 0
            },
            "assets": {
                "total": assets_count['count'] if assets_count else 0,
                "published": published_assets['count'] if published_assets else 0
            },
            "orders": {
                "total": orders_count['count'] if orders_count else 0,
                "pending": pending_orders['count'] if pending_orders else 0
            },
            "revenue": {
                "total": float(total_revenue['total']) if total_revenue else 0.0,
                "today": float(today_revenue['total']) if today_revenue else 0.0
            },
            "workflows": workflows_count['count'] if workflows_count else 0,
            "devices": devices_count['count'] if devices_count else 0,
            "print_jobs": print_jobs_count['count'] if print_jobs_count else 0
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取统计数据失败: {str(e)}")


@router.get("/users")
async def get_all_users(
    request: Request,
    page: int = 1,
    page_size: int = 50,
    role: Optional[str] = None,
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """获取所有用户列表（管理员）"""
    app_state = request.app.state
    if not hasattr(app_state, 'db_connected') or not app_state.db_connected:
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "note": "数据库未连接"
        }
    
    db = app_state.db
    offset = (page - 1) * page_size
    
    query = "SELECT id, nickname, primary_email, primary_phone, points, role, is_active, created_at FROM users WHERE 1=1"
    params = []
    
    if role:
        query += " AND role = $" + str(len(params) + 1)
        params.append(role)
    
    query += " ORDER BY created_at DESC LIMIT $" + str(len(params) + 1) + " OFFSET $" + str(len(params) + 2)
    params.extend([page_size, offset])
    
    users = await db.fetch(query, *params)
    total = await db.fetchrow("SELECT COUNT(*) as count FROM users")
    
    return {
        "items": [dict(user) for user in users],
        "total": total['count'] if total else 0,
        "page": page,
        "page_size": page_size
    }


@router.put("/users/{user_id}/status")
async def toggle_user_status(
    user_id: str,
    status_param: bool,
    request: Request,
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """切换用户状态（启用/禁用）"""
    app_state = request.app.state
    if not hasattr(app_state, 'db_connected') or not app_state.db_connected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接")
    
    db = app_state.db
    
    user = await db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    
    await db.execute(
        "UPDATE users SET is_active = $1 WHERE id = $2",
        status_param, user_id
    )
    
    # 记录操作日志
    await log_operation(
        request,
        admin_user['id'],
        "toggle_user_status",
        "user",
        user_id,
        {"old_status": user.get('is_active'), "new_status": status_param}
    )
    
    return {"message": f"用户已{'启用' if status_param else '禁用'}", "user_id": user_id, "is_active": status_param}


@router.put("/assets/{asset_id}/publish")
async def toggle_asset_publish(
    asset_id: str,
    publish: bool,
    request: Request,
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """切换作品发布状态"""
    app_state = request.app.state
    if not hasattr(app_state, 'db_connected') or not app_state.db_connected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接")
    
    db = app_state.db
    
    asset = await db.fetchrow("SELECT * FROM assets WHERE id = $1", asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="作品不存在")
    
    await db.execute(
        "UPDATE assets SET is_published = $1 WHERE id = $2",
        publish, asset_id
    )
    
    # 记录操作日志
    await log_operation(
        request,
        admin_user['id'],
        "toggle_asset_publish",
        "asset",
        asset_id,
        {"old_status": asset.get('is_published'), "new_status": publish}
    )
    
    return {"message": f"作品已{'发布' if publish else '下架'}", "asset_id": asset_id, "is_published": publish}


@router.get("/export/{resource_type}")
async def export_data(
    resource_type: str,
    request: Request,
    format: str = "csv",
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """导出数据（CSV格式）"""
    app_state = request.app.state
    if not hasattr(app_state, 'db_connected') or not app_state.db_connected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接")
    
    db = app_state.db
    
    if resource_type == "users":
        rows = await db.fetch("SELECT id, nickname, primary_email, primary_phone, points, role, is_active, created_at FROM users ORDER BY created_at DESC")
        headers = ["ID", "用户名", "邮箱", "手机", "积分", "角色", "状态", "创建时间"]
        data = [[str(r['id']), r.get('nickname', ''), r.get('primary_email', ''), r.get('primary_phone', ''),
                 r.get('points', 0), r.get('role', ''), '活跃' if r.get('is_active') else '禁用',
                 r.get('created_at', '').isoformat() if r.get('created_at') else ''] for r in rows]
    elif resource_type == "assets":
        rows = await db.fetch("SELECT id, author_id, prompt, base_model, is_published, created_at FROM assets ORDER BY created_at DESC")
        headers = ["ID", "作者ID", "Prompt", "模型", "发布状态", "创建时间"]
        data = [[str(r['id']), str(r.get('author_id', '')), r.get('prompt', '')[:100], 
                 r.get('base_model', ''), '已发布' if r.get('is_published') else '未发布',
                 r.get('created_at', '').isoformat() if r.get('created_at') else ''] for r in rows]
    elif resource_type == "orders":
        rows = await db.fetch("SELECT id, user_id, total_amount, status, payment_method, created_at FROM orders ORDER BY created_at DESC")
        headers = ["ID", "用户ID", "金额", "状态", "支付方式", "创建时间"]
        data = [[str(r['id']), str(r.get('user_id', '')), float(r.get('total_amount', 0)), 
                 r.get('status', ''), r.get('payment_method', ''),
                 r.get('created_at', '').isoformat() if r.get('created_at') else ''] for r in rows]
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的数据类型")
    
    # 生成CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(data)
    
    # 记录操作日志
    await log_operation(
        request,
        admin_user['id'],
        "export_data",
        resource_type,
        None,
        {"format": format, "rows_count": len(data)}
    )
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={resource_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"}
    )


@router.get("/logs")
async def get_operation_logs(
    request: Request,
    page: int = 1,
    page_size: int = 50,
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """获取操作日志"""
    app_state = request.app.state
    if not hasattr(app_state, 'db_connected') or not app_state.db_connected:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}
    
    db = app_state.db
    offset = (page - 1) * page_size
    logs = await db.fetch("""
        SELECT ol.*, u.nickname as admin_name
        FROM operation_logs ol
        LEFT JOIN users u ON ol.admin_id = u.id
        ORDER BY ol.created_at DESC
        LIMIT $1 OFFSET $2
    """, page_size, offset)
    
    total = await db.fetchrow("SELECT COUNT(*) as count FROM operation_logs")
    
    return {
        "items": [dict(log) for log in logs],
        "total": total['count'] if total else 0,
        "page": page,
        "page_size": page_size
    }


@router.get("/charts/data")
async def get_chart_data(
    request: Request,
    chart_type: str,
    days: int = 7,
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """获取图表数据"""
    app_state = request.app.state
    if not hasattr(app_state, 'db_connected') or not app_state.db_connected:
        return {"labels": [], "data": []}
    
    db = app_state.db
    
    if chart_type == "user_growth":
        # 用户增长趋势
        rows = await db.fetch(f"""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM users
            WHERE created_at >= CURRENT_DATE - INTERVAL '{days} days'
            GROUP BY DATE(created_at)
            ORDER BY date
        """)
        return {
            "labels": [r['date'].strftime('%Y-%m-%d') for r in rows],
            "data": [r['count'] for r in rows]
        }
    elif chart_type == "revenue_trend":
        # 收入趋势
        rows = await db.fetch(f"""
            SELECT DATE(created_at) as date, COALESCE(SUM(total_amount), 0) as total
            FROM orders
            WHERE created_at >= CURRENT_DATE - INTERVAL '{days} days'
            AND status IN ('paid', 'shipped', 'completed')
            GROUP BY DATE(created_at)
            ORDER BY date
        """)
        return {
            "labels": [r['date'].strftime('%Y-%m-%d') for r in rows],
            "data": [float(r['total']) for r in rows]
        }
    elif chart_type == "asset_publish":
        # 作品发布统计
        rows = await db.fetch("""
            SELECT 
                COUNT(*) FILTER (WHERE is_published = TRUE) as published,
                COUNT(*) FILTER (WHERE is_published = FALSE) as unpublished
            FROM assets
        """)
        if rows:
            r = rows[0]
            return {
                "labels": ["已发布", "未发布"],
                "data": [r['published'], r['unpublished']]
            }
    elif chart_type == "order_status":
        # 订单状态分布
        rows = await db.fetch("""
            SELECT status, COUNT(*) as count
            FROM orders
            GROUP BY status
        """)
        return {
            "labels": [r['status'] for r in rows],
            "data": [r['count'] for r in rows]
        }
    
    return {"labels": [], "data": []}


# HTML 页面路由（需要单独注册，不使用 prefix）
admin_html_router = APIRouter(tags=["管理员页面"])


@admin_html_router.get("/admin", response_class=HTMLResponse)
async def admin_page():
    """管理后台页面"""
    admin_paths = [
        "admin.html",
        "../frontend/admin.html",
        "frontend/admin.html"
    ]
    for path in admin_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
    raise HTTPException(status_code=404, detail="Admin page not found")


@admin_html_router.get("/frontend/admin.html", response_class=HTMLResponse)
async def admin_page_frontend():
    """管理后台页面（前端路径）"""
    admin_paths = [
        "../frontend/admin.html",
        "frontend/admin.html",
        "admin.html"
    ]
    for path in admin_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
    raise HTTPException(status_code=404, detail="Admin page not found")


__all__ = ["router", "admin_html_router"]
