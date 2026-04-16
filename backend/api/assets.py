"""
资产 / 社区相关的 API 路由
"""

import uuid
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, Request, status, UploadFile, File
from fastapi.responses import JSONResponse

from schemas import Asset, CommentCreate
from api.dependencies import get_current_user, get_current_user_optional
from utils.content_filter import ContentFilter
from storage import get_storage_manager
from logger import logger
from utils.studio_display import prompt_from_studio_history_row

import json


router = APIRouter(prefix="/api/assets", tags=["资产"])

OSS_DOWNLOAD_FALLBACK_URL = "https://example.com/model/demo-elder.stl"


def resolve_asset_model_url(model_url: str) -> str:
    """将模型地址转换为可访问下载链接。"""
    if not model_url:
        return model_url

    if model_url.startswith("models/") or model_url.startswith("oss://"):
        try:
            from utils.oss_util import oss_manager

            oss_key = model_url.replace("oss://", "") if model_url.startswith("oss://") else model_url
            signed_url = oss_manager.generate_presigned_url(oss_key)
            if signed_url:
                return signed_url
        except Exception as e:
            logger.warning(f"生成模型签名链接失败: model_url={model_url}, error={str(e)}")

        # OSS 无法签名时回退到可访问的演示链接，避免前端直接打开 oss:// 失败。
        return OSS_DOWNLOAD_FALLBACK_URL

    return model_url


def _resolve_asset_model_access_url(model_url: str) -> str:
    """把资产模型地址解析为前端可直接访问的下载链接。"""
    if not model_url:
        return model_url

    if model_url.startswith("models/") or model_url.startswith("oss://"):
        try:
            from utils.oss_util import oss_manager
            oss_key = model_url.replace("oss://", "") if model_url.startswith("oss://") else model_url
            signed_url = oss_manager.generate_presigned_url(oss_key)
            if signed_url:
                return signed_url
        except Exception:
            pass

    return model_url


def _normalize_history_params(params: Any) -> Dict[str, Any]:
    """解析 studio_history.params（JSONB / str / dict）。"""
    if params is None:
        return {}
    if isinstance(params, dict):
        return params
    if isinstance(params, str):
        try:
            s = params.strip()
            return json.loads(s) if s else {}
        except Exception:
            return {}
    return {}


def _resolve_image23d_reference_raw(hist: Dict[str, Any]) -> Optional[str]:
    """图生3D 参考图 OSS 原始值：优先 params.reference_image_url，其次历史行 preview_url。"""
    hp = _normalize_history_params(hist.get("params"))
    ref = hp.get("reference_image_url")
    if isinstance(ref, str) and ref.strip():
        return ref.strip()
    pv = hist.get("preview_url")
    if pv and str(pv).strip():
        return str(pv).strip()
    return None


@router.get("")
async def get_assets(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    sort: str = "hot",  # hot/new/popular
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    """获取社区资产列表（分页、排序）"""
    try:
        app_state = request.app.state
        if not hasattr(app_state, "db_connected") or not app_state.db_connected:
            # 开发模式：无数据库时返回模拟社区列表，保证前端可用
            demo_items = [
                {
                    "id": "demo-catgirl",
                    "image_url": "https://images.unsplash.com/photo-1633356122544-f134324a6cee?w=800&h=600&fit=crop&q=80",
                    "prompt": "赛博猫娘，发光护目镜，赛博朋克风格，Q版",
                    "base_model": "clay",
                    "tags": ["CYBER", "Q-Version"],
                    "stats": {"likes": 450, "downloads": 1204},
                    "created_at": None,
                    "author_id": None,
                    "author_name": "demo_user",
                },
                {
                    "id": "demo-elder",
                    "image_url": "https://api.dicebear.com/7.x/bottts/svg?seed=Robot",
                    "prompt": "智慧长老，硬表面建模，细节丰富",
                    "base_model": "mecha",
                    "tags": ["HARD-SURFACE"],
                    "stats": {"likes": 233, "downloads": 802},
                    "created_at": None,
                    "author_id": None,
                    "author_name": "demo_user",
                },
            ]
            return {"items": demo_items[:page_size], "total": len(demo_items), "page": page, "page_size": page_size, "_dev_mode": True}

        db = app_state.db

        offset = (page - 1) * page_size
        current_user_id = str(current_user["id"]) if current_user and current_user.get("id") else None

        # 排序字段使用点赞数量（asset_likes 统计）和下载量
        order_by = {
            "hot": "likes_count DESC, downloads_count DESC, created_at DESC",
            "new": "created_at DESC",
            "popular": "downloads_count DESC, created_at DESC",
        }.get(sort, "created_at DESC")

        assets = await db.fetch(
            f"""
            SELECT
                a.id,
                a.image_url,
                a.prompt,
                a.base_model,
                a.tags,
                a.stats,
                a.created_at,
                a.author_id,
                u.username AS author_name,
                COALESCE(lc.likes, 0) AS likes_count,
                COALESCE(
                    CASE
                        WHEN $3::uuid IS NOT NULL AND EXISTS (
                            SELECT 1 FROM asset_likes al
                            WHERE al.asset_id = a.id AND al.user_id = $3::uuid
                        )
                        THEN TRUE
                        ELSE FALSE
                    END,
                    FALSE
                ) AS liked_by_me,
                COALESCE((a.stats->>'downloads')::int, 0) AS downloads_count
            FROM assets a
            JOIN users u ON a.author_id = u.id
            LEFT JOIN (
                SELECT asset_id, COUNT(*) AS likes
                FROM asset_likes
                GROUP BY asset_id
            ) lc ON lc.asset_id = a.id
            WHERE a.is_published = TRUE
            ORDER BY {order_by}
            LIMIT $1 OFFSET $2
            """,
            page_size,
            offset,
            current_user_id,
        )

        image23d_prompt_by_asset: Dict[str, str] = {}
        if assets:
            try:
                id_strings = [str(r["id"]) for r in assets]
                uuid_list = [uuid.UUID(x) for x in id_strings]
                hist_rows = await db.fetch(
                    """
                    SELECT DISTINCT ON (h.asset_id) h.asset_id::text AS aid, h.mode, h.params
                    FROM studio_history h
                    WHERE h.asset_id = ANY($1::uuid[])
                    ORDER BY h.asset_id, h.created_at DESC
                    """,
                    uuid_list,
                )
                for hr in hist_rows:
                    line = prompt_from_studio_history_row(hr.get("mode"), hr.get("params"))
                    if line:
                        image23d_prompt_by_asset[hr["aid"]] = line
            except Exception as ex:
                logger.warning("社区列表：从 studio_history 补全图生3D 摘要失败: %s", ex)

        total = await db.fetchrow(
            "SELECT COUNT(*) as count FROM assets WHERE is_published = TRUE",
        )

        items = []
        for asset in assets:
            try:
                data = dict(asset)
                aid = str(data.get("id", ""))
                if aid and aid in image23d_prompt_by_asset:
                    data["prompt"] = image23d_prompt_by_asset[aid]
                # 确保 tags / stats 是 JSON 对象，而不是字符串
                try:
                    if isinstance(data.get("tags"), str):
                        data["tags"] = json.loads(data["tags"])
                    elif data.get("tags") is None:
                        data["tags"] = []
                    elif not isinstance(data.get("tags"), list):
                        data["tags"] = []
                except Exception:
                    data["tags"] = []
                
                try:
                    raw_stats = data.get("stats")
                    if isinstance(raw_stats, str):
                        data["stats"] = json.loads(raw_stats)
                    elif raw_stats is None:
                        data["stats"] = {"likes": 0, "downloads": 0}
                    elif not isinstance(raw_stats, dict):
                        data["stats"] = {"likes": 0, "downloads": 0}
                except Exception:
                    data["stats"] = {"likes": 0, "downloads": 0}

                # 用 asset_likes 统计结果覆盖 likes，保持下载量从原 stats 中读取
                likes_count = data.get("likes_count", 0) or 0
                stats_obj = data.get("stats") or {}
                if not isinstance(stats_obj, dict):
                    stats_obj = {"likes": 0, "downloads": 0}
                stats_obj["likes"] = int(likes_count)
                if "downloads" not in stats_obj:
                    stats_obj["downloads"] = 0
                data["stats"] = stats_obj
                data["liked_by_me"] = bool(data.get("liked_by_me"))

                # 删除中间字段
                data.pop("likes_count", None)
                data.pop("downloads_count", None)

                items.append(data)
            except Exception as e:
                logger.error(f"处理资产数据失败: {str(e)}", exc_info=True)
                continue

        return {
            "items": items,
            "total": total["count"] if total else 0,
            "page": page,
            "page_size": page_size,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取资产列表失败: page={page}, sort={sort}, error={str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取资产列表失败: {str(e)}"
        )


@router.get("/{asset_id}")
async def get_asset_detail(
    asset_id: str,
    request: Request,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    """获取作品详情"""
    app_state = request.app.state
    demo_asset_ids = {"demo-catgirl", "demo-elder"}

    if asset_id not in demo_asset_ids:
        try:
            uuid.UUID(asset_id)
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="asset_id 参数格式错误，必须是合法 UUID",
            )

    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        # 开发模式：返回模拟详情
        if asset_id == "demo-catgirl":
            return {
                "id": "demo-catgirl",
                "image_url": "https://images.unsplash.com/photo-1633356122544-f134324a6cee?w=800&h=600&fit=crop&q=80",
                "model_url": None,
                "prompt": "赛博猫娘，发光护目镜，赛博朋克风格，Q版",
                "base_model": "clay",
                "tags": ["CYBER", "Q-Version"],
                "stats": {"likes": 450, "downloads": 1204},
                "author_id": None,
                "author_name": "demo_user",
                "author_avatar": None,
                "_dev_mode": True,
            }
        if asset_id == "demo-elder":
            return {
                "id": "demo-elder",
                "image_url": "https://api.dicebear.com/7.x/bottts/svg?seed=Robot",
                "model_url": None,
                "prompt": "智慧长老，硬表面建模，细节丰富",
                "base_model": "mecha",
                "tags": ["HARD-SURFACE"],
                "stats": {"likes": 233, "downloads": 802},
                "author_id": None,
                "author_name": "demo_user",
                "author_avatar": None,
                "_dev_mode": True,
            }
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    db = app_state.db
    current_user_id = str(current_user["id"]) if current_user else None

    asset = await db.fetchrow(
        """
        SELECT
            a.*,
            a.author_id,
            u.username AS author_name,
            u.avatar AS author_avatar,
            COALESCE(lc.likes, 0) AS likes_count,
            COALESCE(
                CASE
                    WHEN $2::uuid IS NOT NULL AND EXISTS (
                        SELECT 1 FROM asset_likes al
                        WHERE al.asset_id = a.id AND al.user_id = $2::uuid
                    )
                    THEN TRUE
                    ELSE FALSE
                END,
                FALSE
            ) AS liked_by_me
        FROM assets a
        JOIN users u ON a.author_id = u.id
        LEFT JOIN (
            SELECT asset_id, COUNT(*) AS likes
            FROM asset_likes
            GROUP BY asset_id
        ) lc ON lc.asset_id = a.id
        WHERE a.id = $1 AND a.is_published = TRUE
        """,
        asset_id,
        current_user_id,
    )

    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    data = dict(asset)
    try:
        if isinstance(data.get("tags"), str):
            data["tags"] = json.loads(data["tags"])
    except Exception:
        data["tags"] = []
    try:
        if isinstance(data.get("stats"), str):
            data["stats"] = json.loads(data["stats"])
    except Exception:
        data["stats"] = {"likes": 0, "downloads": 0}

    likes_count = data.get("likes_count", 0) or 0
    stats_obj = data.get("stats") or {}
    stats_obj["likes"] = int(likes_count)
    data["stats"] = stats_obj
    data["liked_by_me"] = bool(data.get("liked_by_me"))
    if data.get("image_url"):
        data["image_url"] = _resolve_asset_model_access_url(data["image_url"])
    if data.get("model_url"):
        data["model_url"] = _resolve_asset_model_access_url(data["model_url"])
    data.pop("likes_count", None)

    try:
        from utils.oss_util import oss_manager

        hist = await db.fetchrow(
            """
            SELECT mode, params, preview_url FROM studio_history
            WHERE asset_id = $1::uuid
            ORDER BY created_at DESC
            LIMIT 1
            """,
            asset_id,
        )
        if hist:
            enriched = prompt_from_studio_history_row(hist.get("mode"), hist.get("params"))
            if enriched:
                data["prompt"] = enriched

        # 图生3D：参考图须与作品封面 image_url 解耦（封面可能是 3D 渲染图，勿用 image_url 冒充参考图）
        if hist and str(hist.get("mode") or "") == "image23d":
            data["studio_mode"] = "image23d"
            ref_raw = _resolve_image23d_reference_raw(dict(hist))
            ref_url = None
            if ref_raw:
                if ref_raw.startswith("oss://"):
                    ref_url = oss_manager.generate_presigned_url(ref_raw[len("oss://") :], expires=3600) or ref_raw
                else:
                    ref_url = _resolve_asset_model_access_url(ref_raw)
            if ref_url:
                data["reference_image_url"] = ref_url
    except Exception as ex:
        logger.warning("作品详情：从 studio_history 补全图生3D 摘要/参考图失败: %s", ex)

    return data


@router.get("/{asset_id}/preview-url")
async def get_asset_preview_url(
    asset_id: str,
    request: Request,
):
    """
    按资产 ID 返回当前保存的预览图 URL。
    主要用于前端统一通过后端获取资源，方便后续在服务端实现 COS 实时签名或代理。
    """
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="数据库未连接",
        )

    db = app_state.db
    row = await db.fetchrow(
        "SELECT image_url FROM assets WHERE id = $1 AND is_published = TRUE",
        asset_id,
    )
    if not row or not row.get("image_url"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset preview not found",
        )
    return {"asset_id": asset_id, "url": _resolve_asset_model_access_url(row["image_url"])}


@router.get("/{asset_id}/reference-image-url")
async def get_asset_reference_image_url(
    asset_id: str,
    request: Request,
):
    """
    图生3D 专用：返回用户上传参考图的签名 URL（与 /preview-url 的 assets.image_url 无关）。
    """
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="数据库未连接",
        )

    db = app_state.db
    pub = await db.fetchrow(
        "SELECT id FROM assets WHERE id = $1 AND is_published = TRUE",
        asset_id,
    )
    if not pub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    hist = await db.fetchrow(
        """
        SELECT mode, params, preview_url FROM studio_history
        WHERE asset_id = $1::uuid AND mode = 'image23d'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        asset_id,
    )
    if not hist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference image not found",
        )

    ref_raw = _resolve_image23d_reference_raw(dict(hist))
    if not ref_raw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference image not found",
        )

    from utils.oss_util import oss_manager

    if ref_raw.startswith("oss://"):
        url = oss_manager.generate_presigned_url(ref_raw[len("oss://") :], expires=3600) or ref_raw
    else:
        url = _resolve_asset_model_access_url(ref_raw)
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference image not found",
        )
    return {"asset_id": asset_id, "url": url}


@router.get("/{asset_id}/model-url")
async def get_asset_model_url(
    asset_id: str,
    request: Request,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    """
    鉴权访问并返回带签名的 OSS 预设 URL。
    """
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="数据库未连接",
        )

    db = app_state.db
    current_user_id = str(current_user["id"]) if current_user else None
    
    row = await db.fetchrow(
        "SELECT model_url, author_id, is_published FROM assets WHERE id = $1",
        asset_id,
    )
    if not row or not row.get("model_url"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset model not found",
        )
        
    # 鉴权：只有公开发布的，或是作者本人才可以访问
    if not row.get("is_published"):
        if not current_user_id or str(row.get("author_id")) != current_user_id:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="这是私有模型，无权访问",
            )
            
    return {"asset_id": asset_id, "url": _resolve_asset_model_access_url(row["model_url"])}

@router.post("")
async def create_asset(
    asset_data: Asset,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """发布作品到社区"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    row = await db.fetchrow(
        """
        INSERT INTO assets (
            author_id,
            image_url,
            model_url,
            prompt,
            base_model,
            seed,
            steps,
            sampler,
            tags,
            stats,
            is_published
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, TRUE)
        RETURNING id
        """,
        current_user["id"],
        asset_data.image_url,
        asset_data.model_url,
        asset_data.prompt,
        asset_data.base_model,
        asset_data.seed,
        asset_data.steps,
        asset_data.sampler,
        json.dumps(asset_data.tags or []),
        json.dumps(asset_data.stats or {"likes": 0, "downloads": 0}),
    )

    return {"asset_id": str(row["id"])}


@router.post("/{asset_id}/like")
async def like_asset(
    asset_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """点赞作品（+1）"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    # 确保作品存在
    asset = await db.fetchrow(
        "SELECT id, stats FROM assets WHERE id = $1",
        asset_id,
    )
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    # 插入用户点赞记录（若已存在则忽略）
    await db.execute(
        """
        INSERT INTO asset_likes (asset_id, user_id)
        VALUES ($1, $2)
        ON CONFLICT (asset_id, user_id) DO NOTHING
        """,
        asset_id,
        current_user["id"],
    )

    # 重新统计点赞数量
    row = await db.fetchrow(
        "SELECT COUNT(*) AS likes FROM asset_likes WHERE asset_id = $1",
        asset_id,
    )
    likes = int(row["likes"] if row else 0)

    # 同步到 assets.stats.likes，保持兼容
    raw_stats = asset["stats"]
    if not raw_stats:
        stats: Dict[str, Any] = {"likes": likes, "downloads": 0}
    else:
        if isinstance(raw_stats, str):
            try:
                stats = json.loads(raw_stats)
            except Exception:
                stats = {"likes": likes, "downloads": 0}
        else:
            stats = dict(raw_stats)
        stats["likes"] = likes

    await db.execute(
        "UPDATE assets SET stats = $1 WHERE id = $2",
        json.dumps(stats),
        asset_id,
    )

    return {"message": "Liked successfully", "likes": likes}


@router.post("/{asset_id}/unlike")
async def unlike_asset(
    asset_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """取消点赞作品（-1，最少减到 0）"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    asset = await db.fetchrow(
        "SELECT id, stats FROM assets WHERE id = $1",
        asset_id,
    )
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    # 删除用户点赞记录（若不存在则忽略）
    await db.execute(
        "DELETE FROM asset_likes WHERE asset_id = $1 AND user_id = $2",
        asset_id,
        current_user["id"],
    )

    # 重新统计点赞数量
    row = await db.fetchrow(
        "SELECT COUNT(*) AS likes FROM asset_likes WHERE asset_id = $1",
        asset_id,
    )
    likes = int(row["likes"] if row else 0)

    raw_stats = asset["stats"]
    if not raw_stats:
        stats: Dict[str, Any] = {"likes": likes, "downloads": 0}
    else:
        if isinstance(raw_stats, str):
            try:
                stats = json.loads(raw_stats)
            except Exception:
                stats = {"likes": likes, "downloads": 0}
        else:
            stats = dict(raw_stats)
        stats["likes"] = likes

    await db.execute(
        "UPDATE assets SET stats = $1 WHERE id = $2",
        json.dumps(stats),
        asset_id,
    )

    return {"message": "Unliked successfully", "likes": likes}


@router.post("/{asset_id}/download")
async def download_asset(
    asset_id: str,
    request: Request,
    # 要求有效登录态：未登录或 Token 过期直接返回 401，由前端全局 401 逻辑跳转到登录页
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """下载作品（需登录；成功时增加下载计数）"""
    try:
        app_state = request.app.state
        if not hasattr(app_state, "db_connected") or not app_state.db_connected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
            )

        db = app_state.db

        asset = await db.fetchrow(
            "SELECT stats, model_url FROM assets WHERE id = $1",
            asset_id,
        )

        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

        # 安全地解析 stats 字段（可能是字符串或字典）
        raw_stats = asset["stats"]
        if not raw_stats:
            stats: Dict[str, Any] = {"likes": 0, "downloads": 0}
        elif isinstance(raw_stats, str):
            try:
                stats = json.loads(raw_stats)
            except Exception:
                stats = {"likes": 0, "downloads": 0}
        else:
            # 如果是字典，创建一个可修改的副本
            stats = dict(raw_stats) if isinstance(raw_stats, dict) else {"likes": 0, "downloads": 0}

        # 确保 stats 有必要的字段
        if "likes" not in stats:
            stats["likes"] = 0
        if "downloads" not in stats:
            stats["downloads"] = 0

        # 每次下载点击都增加下载计数。
        stats["downloads"] = stats.get("downloads", 0) + 1
        await db.execute(
            "UPDATE assets SET stats = $1 WHERE id = $2",
            json.dumps(stats),
            asset_id,
        )

        downloads_count = stats.get("downloads", 0)
        model_url = resolve_asset_model_url(asset["model_url"])

        return {"model_url": model_url, "downloads": downloads_count}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载作品失败: asset_id={asset_id}, error={str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下载失败: {str(e)}"
        )


@router.post("/{asset_id}/publish")
async def publish_asset(
    asset_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """发布自己生成的作品到社区（把 is_published 从 FALSE 改为 TRUE）"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    # 必须是作者本人
    asset = await db.fetchrow(
        "SELECT id, author_id, is_published FROM assets WHERE id = $1",
        asset_id,
    )
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    if str(asset["author_id"]) != str(current_user["id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限发布该作品")

    if asset.get("is_published"):
        return {"message": "已发布", "asset_id": asset_id, "is_published": True}

    await db.execute(
        "UPDATE assets SET is_published = TRUE WHERE id = $1",
        asset_id,
    )
    return {"message": "发布成功", "asset_id": asset_id, "is_published": True}


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """删除作品（只有作者本人可以删除）"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    # 检查作品是否存在，并验证是否为作者本人
    asset = await db.fetchrow(
        "SELECT id, author_id FROM assets WHERE id = $1",
        asset_id,
    )
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    
    if str(asset["author_id"]) != str(current_user["id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限删除该作品")

    # 删除作品
    await db.execute(
        "DELETE FROM assets WHERE id = $1",
        asset_id,
    )
    
    logger.info(f"用户 {current_user['id']} 删除了作品 {asset_id}")
    return {"message": "删除成功", "asset_id": asset_id}


# ---------- 评论相关接口 ----------


@router.post("/comments/upload-image")
async def upload_comment_image(
    request: Request,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """上传评论图片"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    # 验证文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只能上传图片文件")

    # 验证文件大小（限制 5MB）
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="图片大小不能超过 5MB")

    try:
        storage = get_storage_manager()
        # 使用本地存储管理器保存文件（自动生成唯一文件名）
        original_name = file.filename or "upload.jpg"
        filename, url = await storage.save_upload_file(
            content,
            original_filename=original_name,
            subdir="comments",
            prefix="comment",
        )

        return {"url": url, "filename": filename}
    except Exception as e:
        logger.error(f"上传评论图片失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="上传失败"
        )


@router.post("/comments/upload-video")
async def upload_comment_video(
    request: Request,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """上传评论视频"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    # 仅允许常见视频类型
    allowed_types = {"video/mp4", "video/webm", "video/quicktime"}
    if not file.content_type or file.content_type.lower() not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 MP4/WEBM/MOV 视频",
        )

    # 验证文件大小（限制 100MB）
    content = await file.read()
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="视频大小不能超过 100MB",
        )

    try:
        storage = get_storage_manager()
        original_name = file.filename or "upload.mp4"
        filename, url = await storage.save_upload_file(
            content,
            original_filename=original_name,
            subdir="comments/videos",
            prefix="comment-video",
        )

        return {"url": url, "filename": filename}
    except Exception as e:
        logger.error(f"上传评论视频失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="上传失败"
        )


@router.get("/{asset_id}/comments")
async def list_comments(
    asset_id: str,
    request: Request,
    page: int = 1,
    page_size: int = 50,
    sort: str = "new",  # new/liked/replied
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    """获取作品下的评论列表（支持楼中楼、排序）"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}

    db = app_state.db
    current_user_id = str(current_user["id"]) if current_user else None
    offset = (page - 1) * page_size

    # 排序：new 最新 / liked 最多点赞 / replied 最多回复
    order_by = {
        "new": "c.created_at DESC",
        "liked": "c.like_count DESC, c.created_at DESC",
        "replied": "c.reply_count DESC, c.created_at DESC",
    }.get(sort, "c.created_at DESC")

    rows = await db.fetch(
        f"""
        SELECT
            c.id,
            c.asset_id,
            c.author_id,
            c.parent_id,
            c.content,
            c.images,
            c.videos,
            c.like_count,
            c.reply_count,
            c.status,
            c.created_at,
            u.username AS author_name,
            u.avatar AS author_avatar,
            COALESCE(
                $4::uuid IS NOT NULL AND EXISTS (
                    SELECT 1 FROM comment_likes cl
                    WHERE cl.comment_id = c.id AND cl.user_id = $4::uuid
                ),
                FALSE
            ) AS liked_by_me
        FROM comments c
        LEFT JOIN users u ON c.author_id = u.id
        WHERE c.asset_id = $1 AND c.status = 'published' AND c.parent_id IS NULL
        ORDER BY {order_by}
        LIMIT $2 OFFSET $3
        """,
        asset_id,
        page_size,
        offset,
        current_user_id,
    )

    # 递归获取所有层级的回复
    all_comment_ids = [str(r["id"]) for r in rows]
    replies_map = {}
    
    # 递归获取所有子评论
    while True:
        if not all_comment_ids:
            break
        
        reply_rows = await db.fetch(
            """
            SELECT
                c.id,
                c.asset_id,
                c.author_id,
                c.parent_id,
                c.content,
                c.images,
                c.videos,
                c.like_count,
                c.reply_count,
                c.status,
                c.created_at,
                u.username AS author_name,
                u.avatar AS author_avatar,
                COALESCE(
                    $2::uuid IS NOT NULL AND EXISTS (
                        SELECT 1 FROM comment_likes cl
                        WHERE cl.comment_id = c.id AND cl.user_id = $2::uuid
                    ),
                    FALSE
                ) AS liked_by_me
            FROM comments c
            LEFT JOIN users u ON c.author_id = u.id
            WHERE c.parent_id = ANY($1::uuid[]) AND c.status = 'published'
            ORDER BY c.created_at ASC
            """,
            all_comment_ids,
            current_user_id,
        )
        
        if not reply_rows:
            break
        
        # 准备下一轮查询的ID列表
        next_level_ids = []
        for reply in reply_rows:
            reply_dict = dict(reply)
            parent_id = str(reply_dict["parent_id"])
            if parent_id not in replies_map:
                replies_map[parent_id] = []
            replies_map[parent_id].append(reply_dict)
            next_level_ids.append(str(reply_dict["id"]))
        
        all_comment_ids = next_level_ids

    # 统计所有评论（包括楼中楼回复）
    total = await db.fetchrow(
        "SELECT COUNT(*) AS count FROM comments WHERE asset_id = $1 AND status = 'published'",
        asset_id,
    )

    # 递归构建嵌套的回复结构
    def build_replies(parent_id: str) -> list:
        """递归构建某个父评论的所有子回复"""
        replies = replies_map.get(parent_id, [])
        result = []
        for reply in replies:
            reply_dict = dict(reply)
            try:
                reply_dict["images"] = json.loads(reply_dict["images"]) if isinstance(reply_dict.get("images"), str) else (reply_dict.get("images") or [])
            except Exception:
                reply_dict["images"] = []
            try:
                reply_dict["videos"] = json.loads(reply_dict["videos"]) if isinstance(reply_dict.get("videos"), str) else (reply_dict.get("videos") or [])
            except Exception:
                reply_dict["videos"] = []
            reply_dict["liked_by_me"] = bool(reply_dict.get("liked_by_me"))
            # 递归获取子回复
            reply_dict["replies"] = build_replies(str(reply_dict["id"]))
            result.append(reply_dict)
        return result
    
    items = []
    for r in rows:
        data = dict(r)
        try:
            data["images"] = json.loads(data["images"]) if isinstance(data.get("images"), str) else (data.get("images") or [])
        except Exception:
            data["images"] = []
        try:
            data["videos"] = json.loads(data["videos"]) if isinstance(data.get("videos"), str) else (data.get("videos") or [])
        except Exception:
            data["videos"] = []
        data["liked_by_me"] = bool(data.get("liked_by_me"))
        # 递归构建回复树
        data["replies"] = build_replies(str(data["id"]))
        items.append(data)

    return {
        "items": items,
        "total": total["count"] if total else 0,
        "page": page,
        "page_size": page_size,
    }


@router.post("/{asset_id}/comments")
async def create_comment(
    asset_id: str,
    body: CommentCreate,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """发表评论（内容过滤 + XSS 清洗）"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    # 允许单独发送图片/视频：无文字时至少有一种媒体
    has_content = bool((body.content or "").strip())
    has_images = bool(body.images and len(body.images) > 0)
    has_videos = bool(body.videos and len(body.videos) > 0)
    if not has_content and not has_images and not has_videos:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请填写内容或上传图片/视频")
    if has_content:
        ok, err = ContentFilter.filter_content(body.content)
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    db = app_state.db
    asset = await db.fetchrow(
        "SELECT id FROM assets WHERE id = $1 AND is_published = TRUE", asset_id
    )
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="作品不存在")

    content = ContentFilter.sanitize_for_display(body.content)
    parent_id = body.parent_id if body.parent_id else None
    # 图片 URL 白名单：仅保留 /uploads/ 路径，拒绝 javascript:、data:、外链
    safe_images = ContentFilter.filter_image_urls(body.images)
    safe_videos = ContentFilter.filter_video_urls(body.videos)
    images_json = json.dumps(safe_images)
    videos_json = json.dumps(safe_videos)

    row = await db.fetchrow(
        """
        INSERT INTO comments (asset_id, author_id, parent_id, content, images, videos, status)
        VALUES ($1, $2, $3, $4, $5, $6, 'published')
        RETURNING id, created_at
        """,
        asset_id,
        current_user["id"],
        parent_id,
        content,
        images_json,
        videos_json,
    )

    # 如果是回复，更新父评论的回复数
    if parent_id:
        await db.execute(
            "UPDATE comments SET reply_count = reply_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = $1",
            parent_id,
        )

    return {
        "comment_id": str(row["id"]),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


@router.post("/{asset_id}/comments/{comment_id}/like")
async def like_comment(
    asset_id: str,
    comment_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """点赞评论"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db
    comment = await db.fetchrow(
        "SELECT id FROM comments WHERE id = $1 AND asset_id = $2", comment_id, asset_id
    )
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在")

    await db.execute(
        """
        INSERT INTO comment_likes (comment_id, user_id)
        VALUES ($1, $2)
        ON CONFLICT (comment_id, user_id) DO NOTHING
        """,
        comment_id,
        current_user["id"],
    )
    await db.execute(
        "UPDATE comments SET like_count = (SELECT COUNT(*) FROM comment_likes WHERE comment_id = $1), updated_at = CURRENT_TIMESTAMP WHERE id = $1",
        comment_id,
    )
    return {"liked": True}


@router.delete("/{asset_id}/comments/{comment_id}/like")
async def unlike_comment(
    asset_id: str,
    comment_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """取消点赞评论"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db
    await db.execute(
        "DELETE FROM comment_likes WHERE comment_id = $1 AND user_id = $2",
        comment_id,
        current_user["id"],
    )
    await db.execute(
        "UPDATE comments SET like_count = (SELECT COUNT(*) FROM comment_likes WHERE comment_id = $1), updated_at = CURRENT_TIMESTAMP WHERE id = $1",
        comment_id,
    )
    return {"liked": False}


@router.delete("/{asset_id}/comments/{comment_id}")
async def delete_comment(
    asset_id: str,
    comment_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """删除评论（仅作者）"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db
    comment = await db.fetchrow(
        "SELECT id, author_id FROM comments WHERE id = $1 AND asset_id = $2",
        comment_id,
        asset_id,
    )
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在")
    if str(comment["author_id"]) != str(current_user["id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权删除")

    await db.execute("DELETE FROM comments WHERE id = $1", comment_id)
    return {"ok": True}


__all__ = ["router"]
