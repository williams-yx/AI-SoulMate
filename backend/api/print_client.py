"""
本地打印执行端与云端的最小通信协议。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import Config
from logger import logger
from utils.oss_util import oss_manager


router = APIRouter(prefix="/api/print-client", tags=["打印执行端"])


def _allowed_client_id() -> str:
    return (Config.PRINT_ALLOWED_CLIENT_ID or "mlkj-mac-u1").strip() or "mlkj-mac-u1"


def _assert_allowed_client_id(client_id: str) -> None:
    expected = _allowed_client_id()
    current = (client_id or "").strip()
    if current != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"client_id not allowed, expected={expected}",
        )


class ClientHeartbeatPayload(BaseModel):
    client_id: str
    printer_count: int = 0
    printer_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ClientClaimPayload(BaseModel):
    client_id: str


class ClientTaskStatusPayload(BaseModel):
    client_id: str
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    printer_id: Optional[str] = None
    printer_name: Optional[str] = None
    printer_model: Optional[str] = None
    shipping_company: Optional[str] = None
    tracking_number: Optional[str] = None


def _check_client_token(token: Optional[str]) -> None:
    expected = Config.PRINT_CLIENT_SHARED_TOKEN.strip()
    if expected and token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="print client token invalid",
        )


def _absolute_download_url(request: Request, task_id: str, client_id: str) -> str:
    base_url = str(request.base_url).rstrip("/")
    return f"{base_url}/api/print-client/tasks/{task_id}/download?client_id={client_id}"


def _normalize_print_specs(raw_value: Any) -> Dict[str, Any]:
    if isinstance(raw_value, dict):
        return raw_value
    if isinstance(raw_value, str):
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            logger.warning("print_specs 不是合法 JSON，已回退为空对象")
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


async def _resolve_print_job_id(db, task_id_or_order_id: str) -> Optional[str]:
    row = await db.fetchrow(
        """
        SELECT id
        FROM print_jobs
        WHERE id::text = $1
        UNION
        SELECT po.print_job_id AS id
        FROM print_orders po
        WHERE po.order_id::text = $1
        LIMIT 1
        """,
        task_id_or_order_id,
    )
    return str(row["id"]) if row else None


@router.post("/heartbeat")
async def client_heartbeat(
    payload: ClientHeartbeatPayload,
    request: Request,
    x_print_client_token: Optional[str] = Header(default=None, alias="X-Print-Client-Token"),
):
    _check_client_token(x_print_client_token)
    app_state = request.app.state
    if not getattr(app_state, "db_connected", False):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接")

    _assert_allowed_client_id(payload.client_id)

    await app_state.db.execute(
        """
        INSERT INTO print_clients (client_id, printer_count, status, last_seen_at, metadata, updated_at)
        VALUES ($1, $2, 'online', CURRENT_TIMESTAMP, $3::jsonb, CURRENT_TIMESTAMP)
        ON CONFLICT (client_id)
        DO UPDATE SET
            printer_count = EXCLUDED.printer_count,
            status = 'online',
            last_seen_at = CURRENT_TIMESTAMP,
            metadata = EXCLUDED.metadata,
            updated_at = CURRENT_TIMESTAMP
        """,
        payload.client_id,
        payload.printer_count,
        json.dumps(
            {
                **payload.metadata,
                "printer_ids": payload.printer_ids,
            }
        ),
    )
    return {"ok": True, "client_id": payload.client_id}


@router.get("/tasks")
async def list_print_tasks(
    request: Request,
    client_id: str = Query(...),
    limit: int = Query(default=5, ge=1, le=50),
    x_print_client_token: Optional[str] = Header(default=None, alias="X-Print-Client-Token"),
):
    _check_client_token(x_print_client_token)
    app_state = request.app.state
    if not getattr(app_state, "db_connected", False):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接")

    _assert_allowed_client_id(client_id)

    rows = await app_state.db.fetch(
        """
        SELECT
            pj.id,
            pj.user_id,
            pj.asset_id,
            pj.status,
            pj.slice_status,
            pj.slice_file_key,
            pj.slice_file_name,
            pj.target_client_id,
            pj.claimed_by_client_id,
            pj.last_error,
            po.order_id,
            po.print_specs,
            po.estimated_weight,
            o.status AS order_status
        FROM print_jobs pj
        LEFT JOIN print_orders po ON po.print_job_id = pj.id
        LEFT JOIN orders o ON o.id = po.order_id
        WHERE
            COALESCE(o.status, '') IN ('paid', 'processing', 'shipped', 'completed')
            AND
            (pj.target_client_id = $1 OR pj.target_client_id IS NULL OR pj.target_client_id = '')
            AND (
                (pj.status = 'pending' AND pj.slice_status = 'ready' AND (pj.claimed_by_client_id IS NULL OR pj.claimed_by_client_id = '' OR pj.claimed_by_client_id = $1))
                OR (pj.claimed_by_client_id = $1 AND pj.status IN ('claimed', 'downloading', 'printing'))
            )
        ORDER BY 
            CASE WHEN pj.status = 'pending' THEN 0 ELSE 1 END ASC,
            pj.created_at ASC
        LIMIT $2
        """,
        client_id,
        limit,
    )

    tasks = []
    for row in rows:
        print_specs = _normalize_print_specs(row["print_specs"])
        public_download_url = None
        if row["slice_file_key"]:
            public_download_url = oss_manager.generate_presigned_url(row["slice_file_key"], expires=600)

        tasks.append(
            {
                "task_id": str(row["id"]),
                "order_id": str(row["order_id"]) if row["order_id"] else None,
                "asset_id": str(row["asset_id"]) if row["asset_id"] else None,
                "status": row["status"],
                "slice_status": row["slice_status"],
                "material": print_specs.get("material"),
                "height": print_specs.get("height"),
                "model_url": print_specs.get("model_url"),
                "estimated_weight": float(row["estimated_weight"]) if row["estimated_weight"] is not None else None,
                "file_name": row["slice_file_name"],
                "slice_file_key": row["slice_file_key"],
                "proxy_download_url": _absolute_download_url(request, str(row["id"]), client_id),
                "public_download_url": public_download_url,
                "claimed_by_client_id": row["claimed_by_client_id"],
                "target_client_id": row["target_client_id"],
                "last_error": row["last_error"],
            }
        )

    return {"list": tasks, "total": len(tasks)}


@router.get("/tasks/history")
async def list_print_job_history(
    request: Request,
    client_id: str = Query(...),
    limit: int = Query(default=50, ge=1, le=500),
    x_print_client_token: Optional[str] = Header(default=None, alias="X-Print-Client-Token"),
):
    """
    获取分配或由该打单机处理过的所有任务历史。
    用于打单机网页端的“订单列表”展示。
    """
    _check_client_token(x_print_client_token)
    app_state = request.app.state
    if not getattr(app_state, "db_connected", False):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接")

    _assert_allowed_client_id(client_id)

    rows = await app_state.db.fetch(
        """
        SELECT
            pj.id, pj.user_id, pj.asset_id, pj.status, pj.slice_status,
            pj.slice_file_key, pj.slice_file_name, pj.target_client_id, pj.claimed_by_client_id,
            pj.last_error, pj.created_at, pj.updated_at,
            po.order_id, po.print_specs, po.estimated_weight,
            o.total_amount
        FROM print_jobs pj
        LEFT JOIN print_orders po ON po.print_job_id = pj.id
        LEFT JOIN orders o ON o.id = po.order_id
        WHERE
            pj.status NOT IN ('queued', 'slicing', 'awaiting_payment')
            AND COALESCE(o.status, '') NOT IN ('pricing', 'pricing_failed', 'pending')
            AND (
                pj.target_client_id = $1
                OR pj.claimed_by_client_id = $1
                OR pj.target_client_id IS NULL
                OR pj.target_client_id = ''
            )
        ORDER BY pj.created_at DESC
        LIMIT $2
        """,
        client_id,
        limit,
    )

    tasks = []
    for row in rows:
        print_specs = _normalize_print_specs(row["print_specs"])
        tasks.append(
            {
                "id": str(row["id"]),  # 兼容前端 ID 字段
                "task_id": str(row["id"]),
                "order_id": str(row["order_id"]) if row["order_id"] else None,
                "order_no": str(row["order_id"]) if row["order_id"] else None,  # 兼容前端订单号展示
                "asset_id": str(row["asset_id"]) if row["asset_id"] else None,
                "status": row["status"],
                "slice_status": row["slice_status"],
                "material": print_specs.get("material"),
                "height": print_specs.get("height"),
                "model_url": print_specs.get("model_url"),
                "estimated_weight": float(row["estimated_weight"]) if row["estimated_weight"] is not None else 0,
                "total_amount": float(row["total_amount"]) if row["total_amount"] is not None else 0,
                "file_name": row["slice_file_name"],
                "slice_file_key": row["slice_file_key"],
                "claimed_by_client_id": row["claimed_by_client_id"],
                "target_client_id": row["target_client_id"],
                "last_error": row["last_error"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            }
        )

    return {"list": tasks, "total": len(tasks)}


@router.post("/tasks/{task_id}/claim")
async def claim_print_task(
    task_id: str,
    payload: ClientClaimPayload,
    request: Request,
    x_print_client_token: Optional[str] = Header(default=None, alias="X-Print-Client-Token"),
):
    _check_client_token(x_print_client_token)
    app_state = request.app.state
    if not getattr(app_state, "db_connected", False):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接")

    real_task_id = await _resolve_print_job_id(app_state.db, task_id)
    if not real_task_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    _assert_allowed_client_id(payload.client_id)

    row = await app_state.db.fetchrow(
        """
        UPDATE print_jobs
        SET claimed_by_client_id = $2,
            claimed_at = CURRENT_TIMESTAMP,
            status = 'claimed',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $1
          AND EXISTS (
              SELECT 1
              FROM print_orders po
              JOIN orders o ON o.id = po.order_id
              WHERE po.print_job_id = print_jobs.id
                AND o.status IN ('paid', 'processing', 'shipped', 'completed')
          )
          AND slice_status = 'ready'
          AND (target_client_id = $2 OR target_client_id IS NULL OR target_client_id = '')
          AND (claimed_by_client_id IS NULL OR claimed_by_client_id = '' OR claimed_by_client_id = $2)
          AND status = 'pending'
        RETURNING id, status, claimed_by_client_id
        """,
        real_task_id,
        payload.client_id,
    )

    if not row:
        current = await app_state.db.fetchrow(
            "SELECT status, claimed_by_client_id FROM print_jobs WHERE id = $1",
            real_task_id,
        )
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
        if current["claimed_by_client_id"] == payload.client_id:
            return {"ok": True, "task_id": real_task_id, "status": current["status"]}
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="任务已被其他 client 领取")

    return {"ok": True, "task_id": str(row["id"]), "status": row["status"]}


@router.post("/tasks/{task_id}/status")
async def update_print_task_status(
    task_id: str,
    payload: ClientTaskStatusPayload,
    request: Request,
    x_print_client_token: Optional[str] = Header(default=None, alias="X-Print-Client-Token"),
):
    _check_client_token(x_print_client_token)
    app_state = request.app.state
    if not getattr(app_state, "db_connected", False):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接")

    real_task_id = await _resolve_print_job_id(app_state.db, task_id)
    if not real_task_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在或未被当前 client 持有")

    status_sql = """
        UPDATE print_jobs
        SET status = $2::varchar,
            last_error = $3::text,
            started_at = CASE WHEN $2::varchar = 'printing' AND started_at IS NULL THEN CURRENT_TIMESTAMP ELSE started_at END,
            completed_at = CASE WHEN $2::varchar IN ('completed', 'complete', 'cooling', 'finished', 'failed', 'cancelled', 'canceled') THEN CURRENT_TIMESTAMP ELSE completed_at END,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $1
          AND (claimed_by_client_id = $4::varchar OR claimed_by_client_id IS NULL)
        RETURNING id
    """
    _assert_allowed_client_id(payload.client_id)

    row = await app_state.db.fetchrow(
        status_sql,
        real_task_id,
        payload.status,
        payload.error or payload.message,
        payload.client_id,
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在或未被当前 client 持有")

    relation = await app_state.db.fetchrow(
        """
        SELECT po.order_id
        FROM print_orders po
        WHERE po.print_job_id = $1
        LIMIT 1
        """,
        real_task_id,
    )

    order_id = relation["order_id"] if relation else None

    status_lower = (payload.status or "").strip().lower()
    next_order_status: Optional[str] = None
    if status_lower in {"claimed", "downloading", "printing", "cooling", "completed", "complete", "finished"}:
        next_order_status = "processing"
    elif status_lower == "shipped":
        next_order_status = "shipped"
    elif status_lower in {"received"}:
        next_order_status = "completed"
    elif status_lower in {"cancelled", "canceled"}:
        next_order_status = "cancelled"

    if order_id and next_order_status:
        await app_state.db.execute(
            """
            UPDATE orders
            SET status = $2,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            """,
            order_id,
            next_order_status,
        )

    if order_id and (payload.shipping_company or payload.tracking_number or status_lower in {"shipped", "received"}):
        await app_state.db.execute(
            """
            UPDATE print_orders
            SET shipping_company = COALESCE($2, shipping_company),
                tracking_number = COALESCE($3, tracking_number),
                shipped_at = CASE
                    WHEN $4::varchar = 'shipped' AND shipped_at IS NULL THEN CURRENT_TIMESTAMP
                    ELSE shipped_at
                END,
                received_at = CASE
                    WHEN $4::varchar = 'received' AND received_at IS NULL THEN CURRENT_TIMESTAMP
                    ELSE received_at
                END,
                updated_at = CURRENT_TIMESTAMP
            WHERE order_id = $1
            """,
            order_id,
            payload.shipping_company,
            payload.tracking_number,
            status_lower,
        )

    logger.info(
        "print task status updated task_id=%s client_id=%s status=%s printer=%s tracking=%s",
        real_task_id,
        payload.client_id,
        payload.status,
        payload.printer_name or payload.printer_id,
        payload.tracking_number,
    )
    return {"ok": True, "task_id": real_task_id, "status": payload.status}


@router.get("/tasks/{task_id}/download")
async def download_print_task_file(
    task_id: str,
    request: Request,
    client_id: str = Query(...),
    x_print_client_token: Optional[str] = Header(default=None, alias="X-Print-Client-Token"),
):
    _check_client_token(x_print_client_token)
    _assert_allowed_client_id(client_id)
    app_state = request.app.state
    if not getattr(app_state, "db_connected", False):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接")

    real_task_id = await _resolve_print_job_id(app_state.db, task_id)
    if not real_task_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="切片文件不存在")

    row = await app_state.db.fetchrow(
        """
        SELECT slice_file_key, slice_file_name
        FROM print_jobs
        WHERE id = $1
          AND (target_client_id = $2 OR target_client_id IS NULL OR target_client_id = '')
          AND (claimed_by_client_id = $2 OR claimed_by_client_id IS NULL OR claimed_by_client_id = '')
        """,
        real_task_id,
        client_id,
    )
    if not row or not row["slice_file_key"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="切片文件不存在")

    file_bytes = oss_manager.download_file_bytes(row["slice_file_key"])
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="代理下载 OSS 失败")

    headers = {
        "Content-Disposition": f'attachment; filename="{row["slice_file_name"] or f"{real_task_id}.gcode"}"'
    }
    return StreamingResponse(iter([file_bytes]), media_type="application/octet-stream", headers=headers)
