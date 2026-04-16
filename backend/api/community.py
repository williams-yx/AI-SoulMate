"""
社区帖子与混排流 API
"""

from typing import Any, Dict, List, Optional
import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from api.dependencies import get_current_user, get_current_user_optional
from logger import logger
from schemas import CommentCreate, CommunityPostCreate
from storage import get_storage_manager
from utils.content_filter import ContentFilter


router = APIRouter(prefix="/api/community", tags=["社区"])


_ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/bmp",
}
_ALLOWED_VIDEO_TYPES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
}
_ALLOWED_MODEL_EXTS = {".glb", ".gltf", ".obj", ".stl", ".fbx"}


def _ensure_db(request: Request):
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="数据库未连接",
        )
    return app_state.db


def _filter_model_urls(urls: Optional[List[str]]) -> List[str]:
    if not urls:
        return []
    safe: List[str] = []
    for raw in urls:
        if not raw or not isinstance(raw, str):
            continue
        value = raw.strip()
        lower = value.lower()
        if lower.startswith("javascript:") or lower.startswith("data:"):
            continue
        if not value.startswith("/uploads/"):
            continue
        ext = Path(value).suffix.lower()
        if ext in _ALLOWED_MODEL_EXTS:
            safe.append(value)
    return safe


def _normalize_json_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if isinstance(v, str) and v.strip()]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(v) for v in parsed if isinstance(v, str) and v.strip()]
        except Exception:
            return []
    return []


@router.get("/feed")
async def get_community_feed(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    sort: str = "hot",  # hot/new/popular
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    """获取社区混排流：作品 + 帖子"""
    db = _ensure_db(request)
    current_user_id = str(current_user["id"]) if current_user and current_user.get("id") else None
    offset = max(0, (page - 1) * page_size)

    if sort == "new":
        order_expr = "created_at DESC"
    elif sort == "popular":
        order_expr = "download_count DESC, like_count DESC, created_at DESC"
    else:
        order_expr = "like_count DESC, download_count DESC, created_at DESC"

    rows = await db.fetch(
        f"""
        SELECT * FROM (
            SELECT
                'asset'::text AS item_type,
                a.id AS id,
                a.created_at AS created_at,
                a.author_id AS author_id,
                COALESCE(u.username, '匿名用户') AS author_name,
                COALESCE((a.stats->>'likes')::int, 0) AS like_count,
                COALESCE((a.stats->>'downloads')::int, 0) AS download_count,
                COALESCE(
                    $3::uuid IS NOT NULL AND EXISTS (
                        SELECT 1 FROM asset_likes al
                        WHERE al.asset_id = a.id AND al.user_id = $3::uuid
                    ),
                    FALSE
                ) AS liked_by_me,
                a.prompt AS prompt,
                a.image_url AS image_url,
                a.base_model AS base_model,
                a.tags AS tags,
                NULL::text AS content,
                '[]'::jsonb AS images,
                '[]'::jsonb AS models,
                '[]'::jsonb AS videos
            FROM assets a
            LEFT JOIN users u ON u.id = a.author_id
            WHERE a.is_published = TRUE

            UNION ALL

            SELECT
                'post'::text AS item_type,
                p.id AS id,
                p.created_at AS created_at,
                p.author_id AS author_id,
                COALESCE(u.username, '匿名用户') AS author_name,
                p.like_count AS like_count,
                0::int AS download_count,
                COALESCE(
                    $3::uuid IS NOT NULL AND EXISTS (
                        SELECT 1 FROM community_post_likes l
                        WHERE l.post_id = p.id AND l.user_id = $3::uuid
                    ),
                    FALSE
                ) AS liked_by_me,
                NULL::text AS prompt,
                NULL::text AS image_url,
                NULL::text AS base_model,
                '[]'::jsonb AS tags,
                p.content AS content,
                p.images AS images,
                p.models AS models,
                p.videos AS videos
            FROM community_posts p
            LEFT JOIN users u ON u.id = p.author_id
            WHERE p.status = 'published'
        ) mixed
        ORDER BY {order_expr}
        LIMIT $1 OFFSET $2
        """,
        page_size,
        offset,
        current_user_id,
    )

    asset_total = await db.fetchval("SELECT COUNT(*) FROM assets WHERE is_published = TRUE")
    post_total = await db.fetchval("SELECT COUNT(*) FROM community_posts WHERE status = 'published'")

    items = []
    for row in rows:
        item_type = row["item_type"]
        base = {
            "item_type": item_type,
            "id": str(row["id"]),
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
            "author_id": str(row["author_id"]) if row.get("author_id") else None,
            "author_name": row.get("author_name") or "匿名用户",
            "liked_by_me": bool(row.get("liked_by_me")),
        }
        if item_type == "asset":
            item = {
                **base,
                "prompt": row.get("prompt") or "",
                "image_url": row.get("image_url") or "",
                "base_model": row.get("base_model") or "",
                "tags": row.get("tags") or [],
                "stats": {
                    "likes": int(row.get("like_count") or 0),
                    "downloads": int(row.get("download_count") or 0),
                },
            }
        else:
            item = {
                **base,
                "content": row.get("content") or "",
                "images": row.get("images") or [],
                "models": row.get("models") or [],
                "videos": row.get("videos") or [],
                "stats": {
                    "likes": int(row.get("like_count") or 0),
                },
            }
        items.append(item)

    return {
        "items": items,
        "total": int(asset_total or 0) + int(post_total or 0),
        "page": page,
        "page_size": page_size,
    }


@router.post("/posts")
async def create_post(
    request: Request,
    body: CommunityPostCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """发布社区帖子（支持文字、图片、3D、视频）"""
    db = _ensure_db(request)

    has_content = bool((body.content or "").strip())
    has_images = bool(body.images)
    has_models = bool(body.models)
    has_videos = bool(body.videos)
    if not has_content and not has_images and not has_models and not has_videos:
        raise HTTPException(status_code=400, detail="请填写内容或上传附件")

    safe_content = ""
    if has_content:
        ok, err = ContentFilter.filter_content(body.content or "")
        if not ok:
            raise HTTPException(status_code=400, detail=err)
        safe_content = ContentFilter.sanitize_for_display(body.content or "")

    safe_images = ContentFilter.filter_image_urls(body.images)
    safe_models = _filter_model_urls(body.models)
    safe_videos = ContentFilter.filter_video_urls(body.videos)

    if len(safe_images) > 9:
        raise HTTPException(status_code=400, detail="图片最多 9 张")
    if len(safe_models) > 6:
        raise HTTPException(status_code=400, detail="3D 文件最多 6 个")
    if len(safe_videos) > 3:
        raise HTTPException(status_code=400, detail="视频最多 3 个")

    row = await db.fetchrow(
        """
        INSERT INTO community_posts (author_id, content, images, models, videos, status)
        VALUES ($1, $2, $3, $4, $5, 'published')
        RETURNING id, created_at
        """,
        current_user["id"],
        safe_content,
        json.dumps(safe_images),
        json.dumps(safe_models),
        json.dumps(safe_videos),
    )

    return {
        "post_id": str(row["id"]),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


@router.get("/posts/{post_id}")
async def get_post_detail(
    post_id: str,
    request: Request,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    """获取帖子详情"""
    db = _ensure_db(request)
    current_user_id = str(current_user["id"]) if current_user and current_user.get("id") else None

    row = await db.fetchrow(
        """
        SELECT
            p.id,
            p.author_id,
            p.content,
            p.images,
            p.models,
            p.videos,
            p.like_count,
            p.created_at,
            p.updated_at,
            COALESCE(u.username, '匿名用户') AS author_name,
            u.avatar AS author_avatar,
            COALESCE(
                $2::uuid IS NOT NULL AND EXISTS (
                    SELECT 1 FROM community_post_likes l
                    WHERE l.post_id = p.id AND l.user_id = $2::uuid
                ),
                FALSE
            ) AS liked_by_me
        FROM community_posts p
        LEFT JOIN users u ON u.id = p.author_id
        WHERE p.id = $1 AND p.status = 'published'
        """,
        post_id,
        current_user_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="帖子不存在")

    return {
        "id": str(row["id"]),
        "author_id": str(row["author_id"]) if row.get("author_id") else None,
        "author_name": row.get("author_name") or "匿名用户",
        "author_avatar": row.get("author_avatar"),
        "content": row.get("content") or "",
        "images": _normalize_json_list(row.get("images")),
        "models": _normalize_json_list(row.get("models")),
        "videos": _normalize_json_list(row.get("videos")),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
        "liked_by_me": bool(row.get("liked_by_me")),
        "stats": {
            "likes": int(row.get("like_count") or 0),
        },
    }


@router.post("/posts/upload-image")
async def upload_post_image(
    request: Request,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """上传帖子图片"""
    _ensure_db(request)

    if not file.content_type or file.content_type.lower() not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="仅支持 JPG/PNG/WEBP/GIF/BMP 图片")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片大小不能超过 10MB")

    storage = get_storage_manager()
    original_name = file.filename or "post-image.jpg"
    filename, url = await storage.save_upload_file(
        content,
        original_filename=original_name,
        subdir="community/posts/images",
        prefix=f"post-{current_user['id']}-img",
    )
    return {"url": url, "filename": filename}


@router.post("/posts/upload-model")
async def upload_post_model(
    request: Request,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """上传帖子 3D 文件"""
    _ensure_db(request)

    original_name = file.filename or "post-model.glb"
    ext = Path(original_name).suffix.lower()
    if ext not in _ALLOWED_MODEL_EXTS:
        raise HTTPException(status_code=400, detail="仅支持 GLB/GLTF/OBJ/STL/FBX")

    content = await file.read()
    if len(content) > 200 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="3D 文件大小不能超过 200MB")

    storage = get_storage_manager()
    filename, url = await storage.save_upload_file(
        content,
        original_filename=original_name,
        subdir="community/posts/models",
        prefix=f"post-{current_user['id']}-model",
    )
    return {"url": url, "filename": filename}


@router.post("/posts/upload-video")
async def upload_post_video(
    request: Request,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """上传帖子视频（可选）"""
    _ensure_db(request)

    if not file.content_type or file.content_type.lower() not in _ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=400, detail="仅支持 MP4/WEBM/MOV 视频")

    content = await file.read()
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="视频大小不能超过 100MB")

    storage = get_storage_manager()
    original_name = file.filename or "post-video.mp4"
    filename, url = await storage.save_upload_file(
        content,
        original_filename=original_name,
        subdir="community/posts/videos",
        prefix=f"post-{current_user['id']}-video",
    )
    return {"url": url, "filename": filename}


@router.post("/posts/comments/upload-image")
async def upload_post_comment_image(
    request: Request,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """上传帖子评论图片"""
    _ensure_db(request)

    if not file.content_type or file.content_type.lower() not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="仅支持 JPG/PNG/WEBP/GIF/BMP 图片")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片大小不能超过 10MB")

    storage = get_storage_manager()
    original_name = file.filename or "comment-image.jpg"
    filename, url = await storage.save_upload_file(
        content,
        original_filename=original_name,
        subdir="community/posts/comments/images",
        prefix=f"post-comment-{current_user['id']}-img",
    )
    return {"url": url, "filename": filename}


@router.post("/posts/comments/upload-video")
async def upload_post_comment_video(
    request: Request,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """上传帖子评论视频"""
    _ensure_db(request)

    if not file.content_type or file.content_type.lower() not in _ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=400, detail="仅支持 MP4/WEBM/MOV 视频")

    content = await file.read()
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="视频大小不能超过 100MB")

    storage = get_storage_manager()
    original_name = file.filename or "comment-video.mp4"
    filename, url = await storage.save_upload_file(
        content,
        original_filename=original_name,
        subdir="community/posts/comments/videos",
        prefix=f"post-comment-{current_user['id']}-video",
    )
    return {"url": url, "filename": filename}


@router.post("/posts/{post_id}/like")
async def like_post(
    post_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """点赞帖子"""
    db = _ensure_db(request)

    exists = await db.fetchrow(
        "SELECT id FROM community_posts WHERE id = $1 AND status = 'published'",
        post_id,
    )
    if not exists:
        raise HTTPException(status_code=404, detail="帖子不存在")

    await db.execute(
        """
        INSERT INTO community_post_likes (post_id, user_id)
        VALUES ($1, $2)
        ON CONFLICT (post_id, user_id) DO NOTHING
        """,
        post_id,
        current_user["id"],
    )

    await db.execute(
        """
        UPDATE community_posts
        SET like_count = (SELECT COUNT(*) FROM community_post_likes WHERE post_id = $1),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $1
        """,
        post_id,
    )

    likes = await db.fetchval("SELECT like_count FROM community_posts WHERE id = $1", post_id)
    return {"liked": True, "likes": int(likes or 0)}


@router.delete("/posts/{post_id}/like")
async def unlike_post(
    post_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """取消点赞帖子"""
    db = _ensure_db(request)

    await db.execute(
        "DELETE FROM community_post_likes WHERE post_id = $1 AND user_id = $2",
        post_id,
        current_user["id"],
    )

    await db.execute(
        """
        UPDATE community_posts
        SET like_count = (SELECT COUNT(*) FROM community_post_likes WHERE post_id = $1),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $1
        """,
        post_id,
    )

    likes = await db.fetchval("SELECT like_count FROM community_posts WHERE id = $1", post_id)
    return {"liked": False, "likes": int(likes or 0)}


@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """删除帖子（作者本人）"""
    db = _ensure_db(request)

    post = await db.fetchrow("SELECT id, author_id FROM community_posts WHERE id = $1", post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    if str(post["author_id"]) != str(current_user["id"]):
        raise HTTPException(status_code=403, detail="无权限删除该帖子")

    await db.execute("DELETE FROM community_posts WHERE id = $1", post_id)
    logger.info(f"用户 {current_user['id']} 删除帖子 {post_id}")

    return {"ok": True, "post_id": post_id}


@router.get("/posts/{post_id}/comments")
async def list_post_comments(
    post_id: str,
    request: Request,
    page: int = 1,
    page_size: int = 50,
    sort: str = "new",  # new/liked/replied
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    """获取帖子评论列表（支持楼中楼）"""
    db = _ensure_db(request)
    current_user_id = str(current_user["id"]) if current_user else None
    offset = max(0, (page - 1) * page_size)

    post = await db.fetchrow(
        "SELECT id FROM community_posts WHERE id = $1 AND status = 'published'",
        post_id,
    )
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    order_by = {
        "new": "c.created_at DESC",
        "liked": "c.like_count DESC, c.created_at DESC",
        "replied": "c.reply_count DESC, c.created_at DESC",
    }.get(sort, "c.created_at DESC")

    rows = await db.fetch(
        f"""
        SELECT
            c.id,
            c.post_id,
            c.author_id,
            c.parent_id,
            c.content,
            c.images,
            c.videos,
            c.like_count,
            c.reply_count,
            c.created_at,
            COALESCE(u.username, '匿名用户') AS author_name,
            u.avatar AS author_avatar,
            COALESCE(
                $4::uuid IS NOT NULL AND EXISTS (
                    SELECT 1 FROM community_post_comment_likes cl
                    WHERE cl.comment_id = c.id AND cl.user_id = $4::uuid
                ),
                FALSE
            ) AS liked_by_me
        FROM community_post_comments c
        LEFT JOIN users u ON c.author_id = u.id
        WHERE c.post_id = $1 AND c.status = 'published' AND c.parent_id IS NULL
        ORDER BY {order_by}
        LIMIT $2 OFFSET $3
        """,
        post_id,
        page_size,
        offset,
        current_user_id,
    )

    all_comment_ids = [str(r["id"]) for r in rows]
    replies_map: Dict[str, List[Dict[str, Any]]] = {}

    while all_comment_ids:
        reply_rows = await db.fetch(
            """
            SELECT
                c.id,
                c.post_id,
                c.author_id,
                c.parent_id,
                c.content,
                c.images,
                c.videos,
                c.like_count,
                c.reply_count,
                c.created_at,
                COALESCE(u.username, '匿名用户') AS author_name,
                u.avatar AS author_avatar,
                COALESCE(
                    $2::uuid IS NOT NULL AND EXISTS (
                        SELECT 1 FROM community_post_comment_likes cl
                        WHERE cl.comment_id = c.id AND cl.user_id = $2::uuid
                    ),
                    FALSE
                ) AS liked_by_me
            FROM community_post_comments c
            LEFT JOIN users u ON u.id = c.author_id
            WHERE c.parent_id = ANY($1::uuid[]) AND c.status = 'published'
            ORDER BY c.created_at ASC
            """,
            all_comment_ids,
            current_user_id,
        )
        if not reply_rows:
            break

        next_level_ids: List[str] = []
        for reply in reply_rows:
            reply_dict = dict(reply)
            parent_key = str(reply_dict["parent_id"])
            if parent_key not in replies_map:
                replies_map[parent_key] = []
            replies_map[parent_key].append(reply_dict)
            next_level_ids.append(str(reply_dict["id"]))
        all_comment_ids = next_level_ids

    total = await db.fetchval(
        "SELECT COUNT(*) FROM community_post_comments WHERE post_id = $1 AND status = 'published'",
        post_id,
    )

    def build_replies(parent_id: str) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for reply in replies_map.get(parent_id, []):
            data = dict(reply)
            data["id"] = str(data["id"])
            data["author_id"] = str(data["author_id"]) if data.get("author_id") else None
            data["parent_id"] = str(data["parent_id"]) if data.get("parent_id") else None
            data["images"] = _normalize_json_list(data.get("images"))
            data["videos"] = _normalize_json_list(data.get("videos"))
            data["liked_by_me"] = bool(data.get("liked_by_me"))
            data["created_at"] = data["created_at"].isoformat() if data.get("created_at") else None
            data["replies"] = build_replies(str(reply["id"]))
            items.append(data)
        return items

    payload_items: List[Dict[str, Any]] = []
    for row in rows:
        data = dict(row)
        data["id"] = str(data["id"])
        data["author_id"] = str(data["author_id"]) if data.get("author_id") else None
        data["parent_id"] = str(data["parent_id"]) if data.get("parent_id") else None
        data["images"] = _normalize_json_list(data.get("images"))
        data["videos"] = _normalize_json_list(data.get("videos"))
        data["liked_by_me"] = bool(data.get("liked_by_me"))
        data["created_at"] = data["created_at"].isoformat() if data.get("created_at") else None
        data["replies"] = build_replies(str(row["id"]))
        payload_items.append(data)

    return {
        "items": payload_items,
        "total": int(total or 0),
        "page": page,
        "page_size": page_size,
    }


@router.post("/posts/{post_id}/comments")
async def create_post_comment(
    post_id: str,
    body: CommentCreate,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """发布帖子评论（支持文字/图片/视频）"""
    db = _ensure_db(request)

    has_content = bool((body.content or "").strip())
    has_images = bool(body.images)
    has_videos = bool(body.videos)
    if not has_content and not has_images and not has_videos:
        raise HTTPException(status_code=400, detail="请填写内容或上传图片/视频")

    if has_content:
        ok, err = ContentFilter.filter_content(body.content or "")
        if not ok:
            raise HTTPException(status_code=400, detail=err)

    post = await db.fetchrow(
        "SELECT id FROM community_posts WHERE id = $1 AND status = 'published'",
        post_id,
    )
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    safe_images = ContentFilter.filter_image_urls(body.images)
    safe_videos = ContentFilter.filter_video_urls(body.videos)
    if len(safe_images) > 10:
        raise HTTPException(status_code=400, detail="图片最多 10 张")
    if len(safe_videos) > 3:
        raise HTTPException(status_code=400, detail="视频最多 3 个")

    row = await db.fetchrow(
        """
        INSERT INTO community_post_comments (post_id, author_id, parent_id, content, images, videos, status)
        VALUES ($1, $2, $3, $4, $5, $6, 'published')
        RETURNING id, created_at
        """,
        post_id,
        current_user["id"],
        body.parent_id if body.parent_id else None,
        ContentFilter.sanitize_for_display(body.content or ""),
        json.dumps(safe_images),
        json.dumps(safe_videos),
    )

    if body.parent_id:
        await db.execute(
            """
            UPDATE community_post_comments
            SET reply_count = reply_count + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            """,
            body.parent_id,
        )

    return {
        "comment_id": str(row["id"]),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


@router.post("/posts/{post_id}/comments/{comment_id}/like")
async def like_post_comment(
    post_id: str,
    comment_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """点赞帖子评论"""
    db = _ensure_db(request)

    comment = await db.fetchrow(
        "SELECT id FROM community_post_comments WHERE id = $1 AND post_id = $2 AND status = 'published'",
        comment_id,
        post_id,
    )
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")

    await db.execute(
        """
        INSERT INTO community_post_comment_likes (comment_id, user_id)
        VALUES ($1, $2)
        ON CONFLICT (comment_id, user_id) DO NOTHING
        """,
        comment_id,
        current_user["id"],
    )

    await db.execute(
        """
        UPDATE community_post_comments
        SET like_count = (SELECT COUNT(*) FROM community_post_comment_likes WHERE comment_id = $1),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $1
        """,
        comment_id,
    )

    return {"liked": True}


@router.delete("/posts/{post_id}/comments/{comment_id}/like")
async def unlike_post_comment(
    post_id: str,
    comment_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """取消点赞帖子评论"""
    db = _ensure_db(request)

    await db.execute(
        "DELETE FROM community_post_comment_likes WHERE comment_id = $1 AND user_id = $2",
        comment_id,
        current_user["id"],
    )

    await db.execute(
        """
        UPDATE community_post_comments
        SET like_count = (SELECT COUNT(*) FROM community_post_comment_likes WHERE comment_id = $1),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $1 AND post_id = $2
        """,
        comment_id,
        post_id,
    )

    return {"liked": False}


@router.delete("/posts/{post_id}/comments/{comment_id}")
async def delete_post_comment(
    post_id: str,
    comment_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """删除帖子评论（仅作者）"""
    db = _ensure_db(request)

    comment = await db.fetchrow(
        "SELECT id, author_id, parent_id FROM community_post_comments WHERE id = $1 AND post_id = $2",
        comment_id,
        post_id,
    )
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")

    if str(comment["author_id"]) != str(current_user["id"]):
        raise HTTPException(status_code=403, detail="无权限删除")

    await db.execute("DELETE FROM community_post_comments WHERE id = $1", comment_id)

    if comment.get("parent_id"):
        await db.execute(
            """
            UPDATE community_post_comments
            SET reply_count = GREATEST(0, reply_count - 1),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            """,
            comment["parent_id"],
        )

    return {"ok": True}
