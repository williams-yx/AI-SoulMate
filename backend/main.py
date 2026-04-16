from fastapi import FastAPI, HTTPException, Depends, Request, status, WebSocket, WebSocketDisconnect, Query, UploadFile, File, Form
from pathlib import Path, PurePosixPath
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any, Tuple
import asyncpg
import jwt
import hashlib
import uuid
import json
from datetime import datetime, timedelta, timezone
import aiofiles
import os
import tempfile
import shutil
import subprocess
import tarfile
from contextlib import asynccontextmanager
import random
import re
import asyncio
from cryptography.fernet import Fernet
import base64
import aiohttp
from urllib.parse import urlparse, urljoin, quote
from logger import logger
from cache import get_cache_manager
from storage import get_storage_manager
from auth import hash_password, verify_password
from config import Config
from database import DatabaseManager
from core.security import AuthManager
from core.points import deduct_points, total_points
from utils.encryption import EncryptionManager
from utils.content_filter import ContentFilter
from utils.studio_display import (
    format_hunyuan_image23d_display_prompt as _format_hunyuan_image23d_display_prompt,
    prompt_from_studio_history_row,
)
from services.ai_service import AIService
from services.hunyuan3d import Hunyuan3DService
from schemas import (
    User,
    UserCreate,
    UserLogin,
    Project,
    Asset,
    StudioGenerate,
    StudioImageTo3D,
    Course,
    Order,
    Address,
    Device,
    PrintJob,
    ModelConfig,
    ModelConfigCreate,
    ModelConfigUpdate,
)
from api import (
    get_auth_router,
    get_projects_router,
    get_assets_router,
    get_community_router,
    get_orders_router,
    get_address_router,
    get_workflow_router,
    get_admin_router,
    get_admin_html_router,
)
from api.dependencies import get_current_user, get_admin_user

# 数据模型已迁移到schemas模块
# DatabaseManager已迁移到database.py模块

 # JWT认证
# 验证码存储（生产环境应使用Redis）
verification_codes: Dict[str, Dict[str, Any]] = {}

# Studio 模型代理会话缓存（用于拼接根路径）
studio_proxy_roots: Dict[str, Dict[str, Any]] = {}
STUDIO_PROXY_TTL_SECONDS = 600

def _cleanup_studio_proxy_roots() -> None:
    """清理过期的模型代理会话，避免内存泄露。"""
    if not studio_proxy_roots:
        return
    now_ts = datetime.now(timezone.utc).timestamp()
    expired_keys = [
        key
        for key, data in studio_proxy_roots.items()
        if now_ts - float(data.get("updated_at", 0)) > STUDIO_PROXY_TTL_SECONDS
    ]
    for key in expired_keys:
        studio_proxy_roots.pop(key, None)

def _is_safe_relative_path(path: str) -> bool:
    """简单校验相对路径，避免目录穿越。"""
    if not path:
        return False
    normalized = path.replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized:
        return False
    return True


def _guess_remote_file_extension(
    url: Optional[str],
    *,
    fallback_format: Optional[str] = None,
    default: str = ".bin",
) -> str:
    """从 URL 或指定格式中推断远端文件扩展名。"""
    # 优先信任指定格式（如 STL），避免带签名链接后缀混淆（如 .glb?format=stl）
    normalized_format = str(fallback_format or "").strip().lower().lstrip(".")
    if normalized_format and re.fullmatch(r"[a-z0-9]+", normalized_format):
        return f".{normalized_format}"

    path = urlparse(url or "").path
    if "." in path:
        ext = path.rsplit(".", 1)[-1].strip().lower()
        if ext and re.fullmatch(r"[a-z0-9]+", ext):
            return f".{ext}"

    return default


def _detect_model_extension_by_magic(file_bytes: bytes, fallback_ext: str = ".bin") -> str:
    if not file_bytes:
        return fallback_ext

    head = file_bytes[:16]
    if head.startswith(b"PK\x03\x04"):
        return ".zip"
    if head.startswith(b"glTF"):
        return ".glb"

    text_head = file_bytes[:512].decode("utf-8", errors="ignore").lstrip().lower()
    if text_head.startswith("solid"):
        return ".stl"
    if text_head.startswith("v ") or text_head.startswith("o ") or text_head.startswith("#"):
        return ".obj"

    return fallback_ext


def _get_backend_runtime_dir() -> Path:
    return Path(__file__).resolve().parent


def _get_blender_cache_dir() -> Path:
    raw = (
        os.getenv("STUDIO_BLENDER_CACHE_DIR", "").strip()
        or os.getenv("PRINT_BLENDER_CACHE_DIR", "").strip()
        or ""
    )
    if raw:
        return Path(raw).expanduser()
    return Path(tempfile.gettempdir()) / "ai-soulmate-blender"


def _extract_blender_archive(archive_path: Path) -> Optional[Path]:
    if not archive_path.exists() or not archive_path.is_file():
        return None

    stat = archive_path.stat()
    cache_root = _get_blender_cache_dir()
    extract_root = cache_root / f"{archive_path.stem}-{int(stat.st_mtime)}-{stat.st_size}"
    blender_binary = next(extract_root.rglob("blender"), None) if extract_root.exists() else None
    if blender_binary and blender_binary.is_file():
        return blender_binary

    extract_root.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:*") as archive:
        archive.extractall(extract_root)

    blender_binary = next(extract_root.rglob("blender"), None)
    if blender_binary and blender_binary.is_file():
        blender_binary.chmod(blender_binary.stat().st_mode | 0o111)
        return blender_binary
    return None


def _resolve_blender_binary() -> Optional[Path]:
    explicit_binary = (
        os.getenv("STUDIO_BLENDER_BINARY", "").strip()
        or os.getenv("PRINT_BLENDER_BINARY", "").strip()
        or ""
    )
    if explicit_binary:
        candidate = Path(explicit_binary).expanduser()
        if candidate.exists() and candidate.is_file():
            return candidate

    backend_dir = _get_backend_runtime_dir()
    workspace_dir = backend_dir.parent
    local_candidates = [
        backend_dir / "bin" / "blender",
        backend_dir / "bin" / "blender-5.1.0-linux-x64" / "blender",
        workspace_dir / "external-tools" / "bin" / "blender",
        workspace_dir / "external-tools" / "bin" / "blender-5.1.0-linux-x64" / "blender",
    ]
    for candidate in local_candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    which_blender = shutil.which("blender")
    if which_blender:
        return Path(which_blender)

    explicit_archive = (
        os.getenv("STUDIO_BLENDER_ARCHIVE", "").strip()
        or os.getenv("PRINT_BLENDER_ARCHIVE", "").strip()
        or ""
    )
    archive_candidates = []
    if explicit_archive:
        archive_candidates.append(Path(explicit_archive).expanduser())
    archive_candidates.extend(sorted((backend_dir / "bin").glob("blender-*.tar.xz")))
    archive_candidates.extend(sorted((backend_dir / "bin").glob("blender-*.tar.*")))
    archive_candidates.extend(sorted((workspace_dir / "external-tools" / "bin").glob("blender-*.tar.xz")))
    archive_candidates.extend(sorted((workspace_dir / "external-tools" / "bin").glob("blender-*.tar.*")))

    for archive_path in archive_candidates:
        extracted = _extract_blender_archive(archive_path)
        if extracted:
            return extracted

    return None


def _convert_model_bytes_to_stl_with_blender(data: bytes, source_ext: str) -> Tuple[bytes, str]:
    blender_binary = _resolve_blender_binary()
    if not blender_binary:
        raise RuntimeError("未找到 Blender 可执行文件")

    normalized_ext = str(source_ext or "").strip().lower().lstrip(".")
    if normalized_ext not in {"glb", "gltf", "fbx", "obj"}:
        raise RuntimeError(f"Blender 不支持该输入格式: {normalized_ext}")

    with tempfile.TemporaryDirectory(prefix="ai-soulmate-blender-") as tmpdir:
        tmpdir_path = Path(tmpdir)
        input_path = tmpdir_path / f"input.{normalized_ext}"
        output_path = tmpdir_path / "output.stl"
        script_path = tmpdir_path / "convert.py"
        input_path.write_bytes(data)
        script_path.write_text(
            """
import bpy
import pathlib
import sys

argv = sys.argv
if "--" not in argv:
    raise RuntimeError("missing blender args")
input_path, output_path = argv[argv.index("--") + 1 : argv.index("--") + 3]

bpy.ops.wm.read_factory_settings(use_empty=True)
ext = pathlib.Path(input_path).suffix.lower()
if ext in {".glb", ".gltf"}:
    bpy.ops.import_scene.gltf(filepath=input_path)
elif ext == ".fbx":
    bpy.ops.import_scene.fbx(filepath=input_path)
elif ext == ".obj":
    try:
        bpy.ops.wm.obj_import(filepath=input_path)
    except Exception:
        bpy.ops.import_scene.obj(filepath=input_path)
else:
    raise RuntimeError(f"unsupported extension: {ext}")

mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
if not mesh_objects:
    raise RuntimeError("no mesh objects found after import")

bpy.ops.object.select_all(action="DESELECT")
for obj in mesh_objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = mesh_objects[0]

if len(mesh_objects) > 1:
    bpy.ops.object.join()

active = bpy.context.view_layer.objects.active
if active is None:
    raise RuntimeError("no active mesh object")

bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
try:
    bpy.ops.export_mesh.stl(filepath=output_path, use_selection=True)
except Exception:
    bpy.ops.wm.stl_export(filepath=output_path, export_selected_objects=True)
""".strip(),
            encoding="utf-8",
        )

        completed = subprocess.run(
            [
                str(blender_binary),
                "--background",
                "--factory-startup",
                "--python",
                str(script_path),
                "--",
                str(input_path),
                str(output_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "Blender 转换失败: "
                + (completed.stderr or completed.stdout or f"exit={completed.returncode}")
            )
        converted = output_path.read_bytes()
        if not converted:
            raise RuntimeError("Blender 导出的 STL 为空")
        return converted, "stl"


def _convert_model_bytes_to_requested_stl_bytes(data: bytes, source_ext: str) -> Tuple[bytes, str]:
    normalized_ext = str(source_ext or "").strip().lower().lstrip(".")
    if normalized_ext == "stl":
        return data, "stl"
    if normalized_ext not in {"glb", "gltf"}:
        raise RuntimeError(f"STL 请求仅支持从 GLB/GLTF 转换，当前格式: {normalized_ext}")
    return _convert_model_bytes_to_stl_with_blender(data, normalized_ext)


def _normalize_requested_result_format(value: Optional[str]) -> Optional[str]:
    normalized = str(value or "").strip().lower().lstrip(".")
    if not normalized or normalized == "auto":
        return None
    return normalized


def _should_prepare_printable_source(requested_format: Optional[str]) -> bool:
    return _normalize_requested_result_format(requested_format) == "stl"


def _matches_requested_result_format(
    url: Optional[str],
    requested_format: Optional[str],
    actual_format: Optional[str] = None,
) -> bool:
    normalized = _normalize_requested_result_format(requested_format)
    if not normalized:
        return bool(url)
    normalized_actual = _normalize_requested_result_format(actual_format)
    ext = _guess_remote_file_extension(url, fallback_format=None, default="").lstrip(".").lower()
    if normalized_actual == normalized:
        # 不能只信声明格式；若 URL 明确还是别的 3D/压缩格式，说明这是一条伪装路由。
        if ext and ext != normalized and ext in {"glb", "gltf", "zip", "obj", "stl", "amf", "fbx", "ply", "usdz"}:
            return False
        return True
    return ext == normalized


def _is_history_renderable_model_url(url: Optional[str]) -> bool:
    ext = _guess_remote_file_extension(url, default="").lstrip(".").lower()
    return ext in {"stl", "obj", "glb", "gltf"}


def _is_single_file_studio_3d_mode(mode: Optional[str]) -> bool:
    return str(mode or "").strip().lower() in {"text23d", "image23d"}


def _resolve_studio_model_links(
    *,
    mode: Optional[str],
    render_model_url: Optional[str],
    download_model_url: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    if _is_single_file_studio_3d_mode(mode):
        single_url = download_model_url or render_model_url
        return single_url, single_url

    resolved_render = render_model_url
    if not resolved_render and _is_history_renderable_model_url(download_model_url):
        resolved_render = download_model_url
    return resolved_render, download_model_url


def _guess_3d_media_type(path: Optional[str]) -> str:
    ext = _guess_remote_file_extension(path, default="").lstrip(".").lower()
    if ext == "glb":
        return "model/gltf-binary"
    if ext == "gltf":
        return "model/gltf+json"
    return "application/octet-stream"


def _is_gcode_source_format(ext_or_format: Optional[str]) -> bool:
    normalized = str(ext_or_format or "").strip().lower().lstrip(".")
    return normalized in {"stl", "obj", "amf"}


def _derive_gcode_source_payload():
    pass  # TODO: 实现或补全

def _normalize_gcode_source_request_format(value: Optional[str]) -> Optional[str]:
    pass  # TODO: 实现或补全

def _convert_model_bytes_to_gcode_source_bytes(data: bytes, source_ext: str) -> Tuple[bytes, str]:
    pass  # TODO: 实现或补全

def _get_hunyuan_result_file_type(file_info: Dict[str, Any]) -> str:
    pass  # TODO: 实现或补全

def _extract_status_result_files(status_result: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(status_result, dict):
        return []
    response_data = status_result.get("Response", status_result)
    result_files = response_data.get("ResultFile3Ds", []) or []
    if not isinstance(result_files, list):
        return []
    return [file_info for file_info in result_files if isinstance(file_info, dict) and file_info.get("Url")]


def _status_result_file_format(file_info: Dict[str, Any]) -> str:
    url_ext = _guess_remote_file_extension(file_info.get("Url"), default="").lstrip(".").lower()
    if url_ext:
        return url_ext
    declared = str(file_info.get("Type") or file_info.get("FileType") or "").strip().lower().lstrip(".")
    if declared:
        return declared
    return url_ext


def _extract_model_file_from_status_result(
    status_result: Optional[Dict[str, Any]],
    *preferred_formats: str,
) -> Tuple[Optional[str], Optional[str]]:
    files = _extract_status_result_files(status_result)
    normalized_preferred = [str(fmt or "").strip().lower().lstrip(".") for fmt in preferred_formats if str(fmt or "").strip()]
    for preferred in normalized_preferred:
        hit = next((file_info for file_info in files if _status_result_file_format(file_info) == preferred), None)
        if hit:
            return str(hit.get("Url") or "").strip() or None, preferred
    return None, None


def _extract_gcode_source_from_status_result(status_result: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """从混元状态结果中优先取 STL，其次 OBJ/AMF，供打印链使用（与 fix-print 一致）。"""
    response_data = status_result.get("Response", status_result) if isinstance(status_result, dict) else {}
    result_files = response_data.get("ResultFile3Ds", []) or []
    if not isinstance(result_files, list):
        return None, None

    for preferred in ("stl", "obj", "amf"):
        hit = next(
            (
                file_info
                for file_info in result_files
                if isinstance(file_info, dict)
                and file_info.get("Url")
                and _is_gcode_source_format(
                    file_info.get("Type")
                    or file_info.get("FileType")
                    or _guess_remote_file_extension(file_info.get("Url"), default="")
                )
                and str(
                    file_info.get("Type")
                    or file_info.get("FileType")
                    or _guess_remote_file_extension(file_info.get("Url"), default="")
                )
                .strip()
                .lower()
                .lstrip(".")
                == preferred
            ),
            None,
        )
        if hit:
            return str(hit.get("Url") or "").strip() or None, preferred
    return None, None


def _collect_gcode_source_candidate_urls(
    *,
    status_result: Optional[Dict[str, Any]],
    primary_model_url: Optional[str],
    render_model_url: Optional[str],
) -> List[str]:
    candidates: List[str] = []

    for file_info in _extract_status_result_files(status_result):
        file_url = str(file_info.get("Url") or "").strip()
        file_format = _status_result_file_format(file_info)
        if not file_url:
            continue
        if file_format not in {"stl", "obj", "amf", "glb", "gltf", "fbx"}:
            continue
        if file_url not in candidates:
            candidates.append(file_url)

    for candidate in (primary_model_url, render_model_url):
        normalized = str(candidate or "").strip()
        if normalized and normalized not in candidates:
            candidates.append(normalized)

    return candidates


def _resolve_render_output_payload(
    *,
    status_result: Optional[Dict[str, Any]],
    fallback_model_url: Optional[str],
    fallback_model_format: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    render_model_url, render_model_format = _extract_model_file_from_status_result(status_result, "glb", "gltf")
    if render_model_url and render_model_format:
        return render_model_url, render_model_format
    if fallback_model_url and _is_history_renderable_model_url(fallback_model_url):
        return fallback_model_url, _resolve_model_format(fallback_model_url, fallback_format=fallback_model_format)
    return None, None


def _resolve_selected_output_payload(
    *,
    status_result: Optional[Dict[str, Any]],
    requested_result_format: Optional[str],
    default_model_url: Optional[str],
    default_model_format: Optional[str],
    gcode_source_url: Optional[str],
    gcode_source_format: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    normalized_requested = str(requested_result_format or "").strip().lower().lstrip(".")
    if normalized_requested == "stl" and gcode_source_url and _matches_requested_result_format(
        gcode_source_url,
        normalized_requested,
        gcode_source_format,
    ):
        return gcode_source_url, gcode_source_format or normalized_requested
    if normalized_requested:
        selected_url, selected_format = _extract_model_file_from_status_result(status_result, normalized_requested)
        if selected_url and selected_format:
            return selected_url, selected_format
    if normalized_requested and gcode_source_url and _matches_requested_result_format(
        gcode_source_url,
        normalized_requested,
        gcode_source_format,
    ):
        return gcode_source_url, normalized_requested
    if normalized_requested == "stl" and gcode_source_url and _is_gcode_source_format(gcode_source_format):
        return gcode_source_url, gcode_source_format
    if normalized_requested and default_model_url and _matches_requested_result_format(
        default_model_url,
        normalized_requested,
        default_model_format,
    ):
        return default_model_url, normalized_requested
    if normalized_requested == "stl" and default_model_url and _is_gcode_source_format(default_model_format):
        return default_model_url, default_model_format
    if normalized_requested:
        return None, normalized_requested
    return default_model_url, default_model_format


def _prefer_printable_selected_output(
    *,
    requested_result_format: Optional[str],
    selected_model_url: Optional[str],
    selected_model_format: Optional[str],
    gcode_source_url: Optional[str],
    gcode_source_format: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    normalized_requested = _normalize_requested_result_format(requested_result_format)
    if normalized_requested != "stl" or not gcode_source_url:
        return selected_model_url, selected_model_format

    preferred_format = (
        _normalize_requested_result_format(gcode_source_format)
        or normalized_requested
    )
    if (
        selected_model_url == gcode_source_url
        and _matches_requested_result_format(
            selected_model_url,
            normalized_requested,
            selected_model_format or preferred_format,
        )
    ):
        return selected_model_url, selected_model_format or preferred_format

    logger.info(
        "STL 请求优先返回可打印源文件: selected=%s printable=%s format=%s",
        (selected_model_url or "")[:160],
        (gcode_source_url or "")[:160],
        preferred_format,
    )
    return gcode_source_url, preferred_format


def _derive_gcode_source_payload(
    *,
    model_url: Optional[str],
    fallback_format: Optional[str] = None,
    status_result: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[str], Optional[str]]:
    if status_result:
        source_url, source_format = _extract_gcode_source_from_status_result(status_result)
        if source_url and source_format:
            return source_url, source_format

    ext = _guess_remote_file_extension(model_url, fallback_format=fallback_format, default="").lstrip(".").lower()
    if _is_gcode_source_format(ext):
        return model_url, ext
    return None, None


def _normalize_gcode_source_request_format(value: Optional[str]) -> Optional[str]:
    normalized = str(value or "").strip().lower().lstrip(".")
    return normalized if _is_gcode_source_format(normalized) else None


def _convert_model_bytes_to_gcode_source_bytes(data: bytes, source_ext: str) -> Tuple[bytes, str]:
    import trimesh

    suffix = f".{source_ext or 'bin'}"
    fd, input_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        with open(input_path, "wb") as handle:
            handle.write(data)

        loaded = trimesh.load(input_path, file_type=(source_ext or None), force="scene")
        if isinstance(loaded, trimesh.Scene):
            meshes = [
                geometry
                for geometry in loaded.geometry.values()
                if isinstance(geometry, trimesh.Trimesh)
                and len(geometry.vertices)
                and len(geometry.faces)
            ]
            if not meshes:
                raise ValueError("GLB 场景中未找到可导出的网格")
            mesh = trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0]
        elif isinstance(loaded, trimesh.Trimesh):
            mesh = loaded
        else:
            raise ValueError(f"不支持的模型对象类型: {type(loaded).__name__}")

        exported = mesh.export(file_type="stl")
        if isinstance(exported, str):
            exported = exported.encode("utf-8")
        if not isinstance(exported, (bytes, bytearray)) or not exported:
            raise ValueError("导出 STL 结果为空")
        return bytes(exported), "stl"
    finally:
        try:
            os.unlink(input_path)
        except OSError:
            pass


async def _download_remote_model_bytes(url: str) -> Optional[bytes]:
    if not url:
        return None
    try:
        from utils.oss_util import oss_manager

        if url.startswith("oss://"):
            oss_key = url[len("oss://"):]
            return await asyncio.to_thread(oss_manager.download_file_bytes, oss_key)

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
                logger.warning(f"下载模型文件失败: status={resp.status}, url={url[:120]}")
    except Exception as e:
        logger.warning(f"下载模型文件失败: {e}")
    return None


async def _build_gcode_source_payload_from_model_url(
    *,
    model_url: Optional[str],
    requested_result_format: Optional[str],
    user_id: str,
    job_uuid: str,
) -> Tuple[Optional[str], Optional[str]]:
    if not model_url:
        return None, None

    raw_bytes = await _download_remote_model_bytes(str(model_url))
    if not raw_bytes:
        return None, None

    source_ext = _guess_remote_file_extension(model_url, default="").lstrip(".").lower()
    detected_ext = _detect_model_extension_by_magic(raw_bytes, f".{source_ext or 'bin'}").lstrip(".").lower()
    if detected_ext:
        source_ext = detected_ext
    normalized_requested = _normalize_gcode_source_request_format(requested_result_format)

    from utils.oss_util import oss_manager

    if source_ext not in {"glb", "gltf", "fbx"}:
        return None, None

    try:
        if normalized_requested == "stl":
            converted_bytes, converted_format = await asyncio.to_thread(
                _convert_model_bytes_to_gcode_source_bytes,
                raw_bytes,
                source_ext,
            )
        else:
            converted_bytes, converted_format = await asyncio.to_thread(
                _convert_model_bytes_to_gcode_source_bytes,
                raw_bytes,
                source_ext,
            )

        oss_key = await asyncio.to_thread(
            oss_manager.upload_file_bytes,
            user_id,
            converted_bytes,
            f".{converted_format}",
            job_uuid,
        )
        if oss_key:
            logger.info(
                "已为打印链生成后备 gcode 源文件: src=%s -> format=%s key=%s",
                source_ext,
                converted_format,
                oss_key,
            )
            return f"oss://{oss_key}", converted_format
    except Exception as e:
        logger.warning(f"生成后备 gcode 源文件失败: {e}")

    return None, None


async def _build_gcode_source_payload_from_model_candidates(
    *,
    status_result: Optional[Dict[str, Any]],
    primary_model_url: Optional[str],
    render_model_url: Optional[str],
    requested_result_format: Optional[str],
    user_id: str,
    job_uuid: str,
) -> Tuple[Optional[str], Optional[str]]:
    candidates = _collect_gcode_source_candidate_urls(
        status_result=status_result,
        primary_model_url=primary_model_url,
        render_model_url=render_model_url,
    )
    normalized_requested = _normalize_gcode_source_request_format(requested_result_format)
    if normalized_requested == "stl":
        candidates = [
            candidate
            for candidate in candidates
            if _guess_remote_file_extension(candidate, default="").lstrip(".").lower() in {"glb", "gltf"}
        ]

    for candidate in candidates:
        gcode_source_url, gcode_source_format = await _build_gcode_source_payload_from_model_url(
            model_url=candidate,
            requested_result_format=requested_result_format,
            user_id=user_id,
            job_uuid=job_uuid,
        )
        if gcode_source_url and gcode_source_format:
            return gcode_source_url, gcode_source_format

    return None, None


def _parse_hunyuan_result_with_preferred_format(
    status_result: Dict[str, Any],
    preferred_format: Optional[str] = None,
) -> Dict[str, Any]:
    """统一解析混元结果，并在指定 ResultFormat 时优先返回对应文件。"""
    return Hunyuan3DService.parse_query_result(
        status_result,
        preferred_model_format=preferred_format,
    )


class StudioPromptTranslateRequest(BaseModel):
    text: str
    source_lang: Optional[str] = "auto"  # auto / zh / en
    target_lang: str = "en"  # zh / en


class StudioPromptOptimizeRequest(BaseModel):
    text: str
    mode: str = "text2image"  # text2image / text23d
    source_lang: Optional[str] = "auto"  # auto / zh / en

# API Key 加密工具
# 内容审核服务
# AI服务模拟
# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = DatabaseManager()
    app.state.db_connected = False
    
    # 初始化 Redis 缓存（Docker 下需 REDIS_URL=redis://redis:6379/0，由 compose 注入）
    app.state.cache = get_cache_manager()
    for attempt in range(1, 4):
        if app.state.cache.connect():
            break
        if attempt < 3:
            await asyncio.sleep(2)
    app.state.cache_connected = app.state.cache.is_connected()
    if not app.state.cache_connected:
        logger.warning("Redis 未连接，验证码/会话将使用内存存储")

    # 尝试连接数据库，失败时不影响服务启动
    for attempt in range(1, 4):
        try:
            await app.state.db.init()
            await init_database(app.state.db)
            await _repair_inconsistent_studio_jobs(app.state.db)
            await _repair_image23d_placeholder_prompts(app.state.db)
            app.state.db_connected = True
            logger.info("✅ 数据库连接成功")
            break
        except Exception as e:
            logger.error(f"⚠️  数据库连接失败 (尝试 {attempt}/3): {e}")
            if attempt < 3:
                await asyncio.sleep(2)
            else:
                logger.warning("⚠️  服务将在无数据库模式下运行（仅提供静态页面）")
                app.state.db_connected = False

    if app.state.db_connected:
        app.state._studio_sync_task = asyncio.create_task(_studio_jobs_sync_loop(app))
    
    yield
    
    if getattr(app.state, "_studio_sync_task", None):
        app.state._studio_sync_task.cancel()
        try:
            await app.state._studio_sync_task
        except asyncio.CancelledError:
            pass
    
    # 关闭时清理
    if app.state.db_connected and app.state.db.pool:
        await app.state.db.pool.close()
    
    # 关闭Redis连接
    if app.state.cache_connected:
        app.state.cache.disconnect()

# FastAPI应用
app = FastAPI(
    title="AI SoulMate Backend API",
    description="AI驱动的STEAM教育平台后台系统",
    version="1.0.0",
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务（用于访问上传的图片）
uploads_dir = Path(Config.UPLOAD_DIR)
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# 注册API路由
app.include_router(get_auth_router())
app.include_router(get_projects_router())
app.include_router(get_assets_router())
app.include_router(get_community_router())
app.include_router(get_orders_router())
app.include_router(get_address_router())
app.include_router(get_workflow_router())
app.include_router(get_admin_router())
app.include_router(get_admin_html_router())

# 商品路由
from api.products import router as products_router
app.include_router(products_router)

# 打印订单路由
from api.print_orders import router as print_orders_router
app.include_router(print_orders_router)

# 本地打印执行端路由
from api.print_client import router as print_client_router
app.include_router(print_client_router)

# 农场管理路由
from api.farms import router as farms_router
app.include_router(farms_router)

# 管理员订单管理路由（暂未实现）
# from api.admin_orders import router as admin_orders_router
# app.include_router(admin_orders_router)

# 支付路由
from api.payments import router as payments_router
app.include_router(payments_router)

# 积分充值路由
from api.credits import router as credits_router
app.include_router(credits_router)

# 订单派送管理路由
from api.dispatch_admin import router as dispatch_admin_router
app.include_router(dispatch_admin_router)


# 身份验证统一使用 api.dependencies.get_current_user（Token 校验 + 数据库用户信息）
# 操作日志记录已迁移到 api/admin.py

# 数据库初始化已交由 docker-entrypoint-initdb.d 和 .sql 文件接管
# 积分多轨制：启动时若缺少 free_points/redeemed_points/paid_points 则加列并回填
async def init_database(db: DatabaseManager):
    """
    创建数据库表（已迁移至外部 00_init_schema.sql 等资源）。
    启动时执行积分多轨制迁移：添加 free_points、redeemed_points、gift_points、paid_points、
    free_points_refreshed_at 并回填。
    """
    try:
        await db.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS free_points integer DEFAULT 100"
        )
        await db.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS paid_points integer DEFAULT 0"
        )
        await db.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS redeemed_points integer DEFAULT 0"
        )
        await db.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS gift_points integer DEFAULT 0"
        )
        await db.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS free_points_refreshed_at timestamp with time zone DEFAULT now()"
        )
        await db.execute(
            "ALTER TABLE user_identities ADD COLUMN IF NOT EXISTS redeemed_contributed integer DEFAULT 0 NOT NULL"
        )
        await db.execute(
            "ALTER TABLE comments ADD COLUMN IF NOT EXISTS videos jsonb DEFAULT '[]'::jsonb"
        )
        await db.execute(
            "UPDATE comments SET videos = '[]'::jsonb WHERE videos IS NULL"
        )
        # 仅对“尚未迁移”的行回填：paid_points=0 且 free_points 仍为旧默认 1000 或 NULL（新默认 60 不覆盖）
        await db.execute(
            """
            UPDATE users SET free_points = COALESCE(points, 1000)
            WHERE points IS NOT NULL AND COALESCE(paid_points, 0) = 0
              AND (free_points IS NULL OR free_points = 1000)
            """
        )
        logger.info("积分多轨制迁移已执行（free_points/redeemed_points/gift_points/paid_points）")
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS cdk_redemption_codes (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                code_hash char(64) NOT NULL UNIQUE,
                code_prefix varchar(12),
                points integer NOT NULL,
                status varchar(20) NOT NULL DEFAULT 'active',
                max_redeem_count integer NOT NULL DEFAULT 1,
                redeemed_count integer NOT NULL DEFAULT 0,
                redeemed_by_user_id uuid,
                redeemed_at timestamp with time zone,
                expires_at timestamp with time zone,
                note text,
                created_by uuid,
                metadata jsonb DEFAULT '{}'::jsonb,
                created_at timestamp with time zone DEFAULT now(),
                updated_at timestamp with time zone DEFAULT now(),
                CONSTRAINT cdk_redemption_codes_points_check CHECK (points > 0),
                CONSTRAINT cdk_redemption_codes_status_check CHECK (status IN ('active', 'used', 'disabled', 'expired')),
                CONSTRAINT cdk_redemption_codes_max_redeem_count_check CHECK (max_redeem_count > 0),
                CONSTRAINT cdk_redemption_codes_redeemed_count_check CHECK (redeemed_count >= 0)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS cdk_redemption_records (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                code_id uuid NOT NULL REFERENCES cdk_redemption_codes(id) ON DELETE CASCADE,
                user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                points integer NOT NULL,
                code_prefix varchar(12),
                client_ip varchar(64),
                user_agent text,
                redeemed_at timestamp with time zone DEFAULT now(),
                CONSTRAINT cdk_redemption_records_points_check CHECK (points > 0)
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_cdk_redemption_codes_status ON cdk_redemption_codes(status, expires_at, redeemed_count)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_cdk_redemption_records_user_id ON cdk_redemption_records(user_id, redeemed_at DESC)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_cdk_redemption_records_code_id ON cdk_redemption_records(code_id)"
        )
        
        # 积分系统重构：合并 gift_points 到 paid_points
        logger.info("执行积分系统重构迁移...")
        await db.execute(
            """
            UPDATE users 
            SET paid_points = COALESCE(paid_points, 0) + COALESCE(gift_points, 0)
            WHERE gift_points > 0 OR gift_points IS NOT NULL
            """
        )
        
        # 为 credit_recharges 表添加新字段
        await db.execute(
            "ALTER TABLE credit_recharges ADD COLUMN IF NOT EXISTS remaining_credits INTEGER DEFAULT 0"
        )
        await db.execute(
            "ALTER TABLE credit_recharges ADD COLUMN IF NOT EXISTS refunded_at TIMESTAMP WITH TIME ZONE"
        )
        await db.execute(
            "ALTER TABLE credit_recharges ADD COLUMN IF NOT EXISTS refund_amount DECIMAL(10, 2)"
        )
        await db.execute(
            "ALTER TABLE credit_recharges ADD COLUMN IF NOT EXISTS refund_reason TEXT"
        )
        
        # 初始化已支付订单的 remaining_credits
        await db.execute(
            """
            UPDATE credit_recharges 
            SET remaining_credits = total_amount 
            WHERE status = 'paid' AND (remaining_credits IS NULL OR remaining_credits = 0)
            """
        )
        
        # 创建积分消耗记录表
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS credit_consumption_records (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                recharge_id UUID REFERENCES credit_recharges(id) ON DELETE SET NULL,
                amount INTEGER NOT NULL,
                credit_type VARCHAR(20) NOT NULL,
                reason VARCHAR(100),
                related_id UUID,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                CONSTRAINT credit_consumption_amount_check CHECK (amount > 0)
            )
            """
        )
        
        # 修改 credit_consumption_records.related_id 为 TEXT 类型（支持非 UUID 的 job_id）
        await db.execute(
            "ALTER TABLE credit_consumption_records ALTER COLUMN related_id TYPE TEXT USING related_id::TEXT"
        )
        
        logger.info("积分系统重构迁移完成")
        # 造梦历史表：每用户最多 500 条，用于侧边栏展示与详情弹层
        await db.execute("""
            CREATE TABLE IF NOT EXISTS studio_history (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                mode varchar(20) NOT NULL,
                prompt text,
                params jsonb DEFAULT '{}',
                preview_url text,
                asset_id uuid REFERENCES assets(id) ON DELETE SET NULL,
                created_at timestamp with time zone DEFAULT now()
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_studio_history_user_created ON studio_history (user_id, created_at DESC)"
        )
        logger.info("studio_history 表已就绪")
        # 造梦异步任务表：持久化 job_id 与元数据，便于离开页面后后台补写历史
        await db.execute("""
            CREATE TABLE IF NOT EXISTS studio_jobs (
                job_id text PRIMARY KEY,
                user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                mode varchar(20) NOT NULL,
                status varchar(20) DEFAULT 'SUBMITTED',
                last_message text,
                prompt text,
                preview_url text,
                render_model_url text,
                base_model text,
                with_texture boolean DEFAULT true,
                generation_params jsonb DEFAULT '{}',
                param_notes jsonb,
                credits_used integer DEFAULT 0,
                charged_at timestamp with time zone,
                finished_at timestamp with time zone,
                notified_at timestamp with time zone,
                terminal_candidate_status varchar(20),
                terminal_candidate_count integer DEFAULT 0,
                terminal_candidate_seen_at timestamp with time zone,
                asset_id uuid REFERENCES assets(id) ON DELETE SET NULL,
                created_at timestamp with time zone DEFAULT now()
            )
        """)
        await db.execute(
            "ALTER TABLE studio_jobs ADD COLUMN IF NOT EXISTS status varchar(20) DEFAULT 'SUBMITTED'"
        )
        await db.execute(
            "ALTER TABLE studio_jobs ADD COLUMN IF NOT EXISTS last_message text"
        )
        await db.execute(
            "ALTER TABLE studio_jobs ADD COLUMN IF NOT EXISTS preview_url text"
        )
        await db.execute(
            "ALTER TABLE studio_jobs ADD COLUMN IF NOT EXISTS render_model_url text"
        )
        await db.execute(
            "ALTER TABLE studio_jobs ADD COLUMN IF NOT EXISTS credits_used integer DEFAULT 0"
        )
        await db.execute(
            "ALTER TABLE studio_jobs ADD COLUMN IF NOT EXISTS charged_at timestamp with time zone"
        )
        await db.execute(
            "ALTER TABLE studio_jobs ADD COLUMN IF NOT EXISTS finished_at timestamp with time zone"
        )
        await db.execute(
            "ALTER TABLE studio_jobs ADD COLUMN IF NOT EXISTS notified_at timestamp with time zone"
        )
        await db.execute(
            "ALTER TABLE studio_jobs ADD COLUMN IF NOT EXISTS terminal_candidate_status varchar(20)"
        )
        await db.execute(
            "ALTER TABLE studio_jobs ADD COLUMN IF NOT EXISTS terminal_candidate_count integer DEFAULT 0"
        )
        await db.execute(
            "ALTER TABLE studio_jobs ADD COLUMN IF NOT EXISTS terminal_candidate_seen_at timestamp with time zone"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_studio_jobs_asset_null ON studio_jobs (created_at) WHERE asset_id IS NULL"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_studio_jobs_user_status_created ON studio_jobs (user_id, status, created_at DESC)"
        )
        logger.info("studio_jobs 表已就绪")

        # 社区帖子表：支持文字 + 图片 + 3D + 视频（可选）
        await db.execute("""
            CREATE TABLE IF NOT EXISTS community_posts (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                author_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                content text DEFAULT '',
                images jsonb DEFAULT '[]'::jsonb,
                models jsonb DEFAULT '[]'::jsonb,
                videos jsonb DEFAULT '[]'::jsonb,
                like_count integer DEFAULT 0,
                status varchar(20) DEFAULT 'published',
                created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
                updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_community_posts_author ON community_posts(author_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_community_posts_created ON community_posts(created_at DESC)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_community_posts_status ON community_posts(status)"
        )

        await db.execute("""
            CREATE TABLE IF NOT EXISTS community_post_likes (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                post_id uuid NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
                user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(post_id, user_id)
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_community_post_likes_post ON community_post_likes(post_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_community_post_likes_user ON community_post_likes(user_id)"
        )

        await db.execute("""
            CREATE TABLE IF NOT EXISTS community_post_comments (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                post_id uuid NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
                author_id uuid REFERENCES users(id) ON DELETE SET NULL,
                parent_id uuid REFERENCES community_post_comments(id) ON DELETE CASCADE,
                content text NOT NULL,
                images jsonb DEFAULT '[]'::jsonb,
                videos jsonb DEFAULT '[]'::jsonb,
                like_count integer DEFAULT 0,
                reply_count integer DEFAULT 0,
                status varchar(20) DEFAULT 'published',
                created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
                updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_community_post_comments_post ON community_post_comments(post_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_community_post_comments_parent ON community_post_comments(parent_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_community_post_comments_author ON community_post_comments(author_id)"
        )

        await db.execute("""
            CREATE TABLE IF NOT EXISTS community_post_comment_likes (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                comment_id uuid NOT NULL REFERENCES community_post_comments(id) ON DELETE CASCADE,
                user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(comment_id, user_id)
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_community_post_comment_likes_comment ON community_post_comment_likes(comment_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_community_post_comment_likes_user ON community_post_comment_likes(user_id)"
        )
        logger.info("community_posts/community_post_likes 表已就绪")

        # 积分充值表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS credit_recharges (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                amount INTEGER NOT NULL,
                amount_yuan DECIMAL(10, 2) NOT NULL,
                payment_method VARCHAR(50) NOT NULL,
                payment_id VARCHAR(255),
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                paid_at TIMESTAMP WITH TIME ZONE,
                CONSTRAINT credit_recharges_amount_check CHECK (amount > 0 AND amount <= 100000),
                CONSTRAINT credit_recharges_amount_yuan_check CHECK (amount_yuan > 0)
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_credit_recharges_user_id ON credit_recharges(user_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_credit_recharges_status ON credit_recharges(status)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_credit_recharges_created_at ON credit_recharges(created_at DESC)"
        )
        logger.info("credit_recharges 表已就绪")
        
        # 充值档位表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS recharge_tiers (
                id SERIAL PRIMARY KEY,
                min_amount INTEGER NOT NULL,
                bonus_rate DECIMAL(5, 2) NOT NULL DEFAULT 0,
                bonus_fixed INTEGER DEFAULT 0,
                description VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                CONSTRAINT recharge_tiers_min_amount_check CHECK (min_amount > 0),
                CONSTRAINT recharge_tiers_bonus_rate_check CHECK (bonus_rate >= 0 AND bonus_rate <= 100)
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_recharge_tiers_active ON recharge_tiers(is_active, sort_order)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_recharge_tiers_min_amount ON recharge_tiers(min_amount)"
        )
        
        # 插入默认充值档位（如果表为空）
        count = await db.fetchval("SELECT COUNT(*) FROM recharge_tiers")
        if count == 0:
            await db.execute("""
                INSERT INTO recharge_tiers (min_amount, bonus_rate, bonus_fixed, description, sort_order) VALUES
                (100, 0, 0, '充值100积分', 1),
                (500, 5, 0, '充值500积分，赠送5%', 2),
                (1000, 10, 0, '充值1000积分，赠送10%', 3),
                (5000, 15, 0, '充值5000积分，赠送15%', 4),
                (10000, 20, 0, '充值10000积分，赠送20%', 5)
            """)
        logger.info("recharge_tiers 表已就绪")
        
        # 为 credit_recharges 表添加赠送积分字段
        await db.execute(
            "ALTER TABLE credit_recharges ADD COLUMN IF NOT EXISTS bonus_amount INTEGER DEFAULT 0"
        )
        await db.execute(
            "ALTER TABLE credit_recharges ADD COLUMN IF NOT EXISTS total_amount INTEGER DEFAULT 0"
        )
        logger.info("credit_recharges 表字段已更新")
        
        # 身份表：解绑时按「该身份合并时带入的免费/付费」分别拆出
        await db.execute(
            "ALTER TABLE user_identities ADD COLUMN IF NOT EXISTS free_contributed integer DEFAULT 0 NOT NULL"
        )
        await db.execute(
            "ALTER TABLE user_identities ADD COLUMN IF NOT EXISTS paid_contributed integer DEFAULT 0 NOT NULL"
        )
        
        # 农场状态管理系统表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS farm_status (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                farm_id UUID NOT NULL UNIQUE,
                farm_name VARCHAR(100),
                api_endpoint VARCHAR(255) NOT NULL,
                api_key VARCHAR(255),
                status VARCHAR(20) DEFAULT 'offline',
                total_printers INT DEFAULT 0,
                idle_printers INT DEFAULT 0,
                busy_printers INT DEFAULT 0,
                offline_printers INT DEFAULT 0,
                province VARCHAR(30),
                city VARCHAR(30),
                district VARCHAR(30),
                last_heartbeat TIMESTAMP,
                heartbeat_interval INT DEFAULT 30,
                total_orders INT DEFAULT 0,
                completed_orders INT DEFAULT 0,
                failed_orders INT DEFAULT 0,
                priority INT DEFAULT 0,
                weight INT DEFAULT 100,
                enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_farm_status_status ON farm_status(status)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_farm_status_enabled ON farm_status(enabled)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_farm_last_heartbeat ON farm_status(last_heartbeat)"
        )
        
        # 农场支付配置字段
        await db.execute(
            "ALTER TABLE farm_status ADD COLUMN IF NOT EXISTS payment_config JSONB DEFAULT '{}'"
        )
        logger.info("farm_status 表已就绪")
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS printer_status (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                farm_id UUID NOT NULL REFERENCES farm_status(farm_id) ON DELETE CASCADE,
                printer_id UUID NOT NULL,
                printer_name VARCHAR(100),
                printer_model VARCHAR(100),
                status VARCHAR(20) DEFAULT 'offline',
                current_order_id UUID,
                nozzle_temp INT,
                bed_temp INT,
                print_progress INT DEFAULT 0,
                max_nozzle_temp INT DEFAULT 300,
                max_bed_temp INT DEFAULT 110,
                build_volume VARCHAR(50),
                supported_materials VARCHAR(200),
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(farm_id, printer_id)
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_printer_status_farm ON printer_status(farm_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_printer_status_status ON printer_status(status)"
        )
        logger.info("printer_status 表已就绪")
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS order_assignments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                order_id UUID NOT NULL,
                farm_id UUID NOT NULL REFERENCES farm_status(farm_id),
                printer_id UUID,
                status VARCHAR(20) DEFAULT 'assigned',
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                accepted_at TIMESTAMP,
                completed_at TIMESTAMP,
                failure_reason TEXT,
                retry_count INT DEFAULT 0,
                UNIQUE(order_id)
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_order_assignments_order ON order_assignments(order_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_order_assignments_farm ON order_assignments(farm_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_order_assignments_status ON order_assignments(status)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_order_assignments_printer ON order_assignments(printer_id)"
        )
        logger.info("order_assignments 表已就绪")

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS print_clients (
                client_id varchar(100) PRIMARY KEY,
                printer_count integer DEFAULT 0,
                status varchar(20) DEFAULT 'online',
                last_seen_at timestamp with time zone DEFAULT now(),
                metadata jsonb DEFAULT '{}'::jsonb,
                created_at timestamp with time zone DEFAULT now(),
                updated_at timestamp with time zone DEFAULT now()
            )
            """
        )
        await db.execute(
            "ALTER TABLE print_jobs ADD COLUMN IF NOT EXISTS slice_status varchar(20) DEFAULT 'queued'"
        )
        await db.execute(
            "ALTER TABLE print_jobs ADD COLUMN IF NOT EXISTS slice_file_key text"
        )
        await db.execute(
            "ALTER TABLE print_jobs ADD COLUMN IF NOT EXISTS slice_file_url text"
        )
        await db.execute(
            "ALTER TABLE print_jobs ADD COLUMN IF NOT EXISTS slice_file_name varchar(255)"
        )
        await db.execute(
            "ALTER TABLE print_jobs ADD COLUMN IF NOT EXISTS target_client_id varchar(100)"
        )
        await db.execute(
            "ALTER TABLE print_jobs ADD COLUMN IF NOT EXISTS claimed_by_client_id varchar(100)"
        )
        await db.execute(
            "ALTER TABLE print_jobs ADD COLUMN IF NOT EXISTS claimed_at timestamp without time zone"
        )
        await db.execute(
            "ALTER TABLE print_jobs ADD COLUMN IF NOT EXISTS started_at timestamp without time zone"
        )
        await db.execute(
            "ALTER TABLE print_jobs ADD COLUMN IF NOT EXISTS completed_at timestamp without time zone"
        )
        await db.execute(
            "ALTER TABLE print_jobs ADD COLUMN IF NOT EXISTS last_error text"
        )
        await db.execute(
            """
            UPDATE print_jobs
            SET slice_status = CASE
                WHEN slice_status IS NOT NULL THEN slice_status
                WHEN slice_file_key IS NOT NULL THEN 'ready'
                WHEN status = 'failed' THEN 'failed'
                ELSE 'queued'
            END
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_print_jobs_target_status ON print_jobs(target_client_id, status, created_at DESC)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_print_jobs_claimed_by ON print_jobs(claimed_by_client_id)"
        )
        allowed_client_id = (Config.PRINT_ALLOWED_CLIENT_ID or "").strip()
        if allowed_client_id:
            await db.execute(
                """
                UPDATE print_jobs
                SET target_client_id = $1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE target_client_id IS NOT NULL
                  AND target_client_id <> ''
                  AND target_client_id <> $1
                """,
                allowed_client_id,
            )
        await db.execute(
            "ALTER TABLE print_orders ADD COLUMN IF NOT EXISTS shipping_company varchar(100)"
        )
        await db.execute(
            "ALTER TABLE print_orders ADD COLUMN IF NOT EXISTS tracking_number varchar(100)"
        )
        await db.execute(
            "ALTER TABLE print_orders ADD COLUMN IF NOT EXISTS shipped_at timestamp without time zone"
        )
        await db.execute(
            "ALTER TABLE print_orders ADD COLUMN IF NOT EXISTS received_at timestamp without time zone"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_print_orders_tracking_number ON print_orders(tracking_number)"
        )
    except Exception as e:
        logger.warning("积分双轨制迁移跳过（可能表结构已是最新）: %s", e)

# API路由

# 注册、登录、微信登录、绑定手机等认证路由由 api/auth 提供（app.include_router(get_auth_router())）

@app.post("/api/auth/refresh")
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """刷新Token"""
    access_token = AuthManager.create_access_token(
        data={"sub": str(current_user['id'])},
        expires_delta=timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/user/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """获取用户资料（包含积分和作品数）"""
    # 获取作品数
    assets_count = await app.state.db.fetchrow(
        "SELECT COUNT(*) as count FROM assets WHERE author_id = $1",
        current_user['id']
    )
    
    free_credits_out = current_user.get("free_credits")
    if free_credits_out is None:
        free_credits_out = int(current_user.get("free_points") or 0)
    paid_credits_out = current_user.get("paid_credits")
    if paid_credits_out is None:
        paid_credits_out = int(current_user.get("paid_points") or 0)
    redeemed_credits_out = current_user.get("redeemed_credits")
    if redeemed_credits_out is None:
        redeemed_credits_out = int(current_user.get("redeemed_points") or 0)
    gift_credits_out = current_user.get("gift_credits")
    if gift_credits_out is None:
        gift_credits_out = int(current_user.get("gift_points") or 0)
    return {
        "id": current_user['id'],
        "username": current_user.get('username'),
        "email": current_user.get('email'),
        "phone": current_user.get('phone'),
        "credits": total_points(current_user),
        "free_credits": free_credits_out,
        "redeemed_credits": redeemed_credits_out,
        "paid_credits": paid_credits_out,
        "gift_credits": gift_credits_out,
        "free_points_refreshed_at": current_user.get("free_points_refreshed_at"),
        "avatar": current_user.get('avatar'),
        "role": current_user.get('role', 'student'),
        "assets_count": assets_count['count'] if assets_count else 0
    }

@app.get("/api/courses")
async def get_courses():
    """获取课程列表"""
    # 开发模式：数据库未连接时，返回模拟课程数据，保证前端可用
    if not hasattr(app.state, "db_connected") or not app.state.db_connected:
        return [
            {
                "id": "dev-l1",
                "title": "L1 启蒙：AI造物主",
                "description": "学习基础提示词，生成平面浮雕，体验3D打印乐趣。",
                "level": "L1",
                "price": 499,
                "duration_hours": 6,
            },
            {
                "id": "dev-l2",
                "title": "L2 进阶：赋予手办“灵魂”",
                "description": "AI辅助建模 + 实体化 + 智能底座，项目制学习。",
                "level": "L2",
                "price": 1499,
                "duration_hours": 10,
            },
            {
                "id": "dev-l3",
                "title": "L3 高阶：实训就业",
                "description": "参与真实项目实训，完成作品集，衔接就业路径。",
                "level": "L3",
                "price": 2499,
                "duration_hours": 16,
            },
        ]

    courses = await app.state.db.fetch(
        """
        SELECT id, title, description, level, price, duration_hours
        FROM courses 
        WHERE is_active = TRUE
        ORDER BY level, title
        """
    )
    
    return [dict(course) for course in courses]

@app.get("/api/model/{model_id}")
async def get_private_model_url(
    model_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    鉴权访问并下发带签名的临时通行证（防盗链校验），默认过期时间 60 秒。
    """
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="数据库未连接",
        )

    db = app_state.db
    current_user_id = str(current_user["id"])
    
    # 权属检查：从数据库中查询指定模型的权属者
    row = await db.fetchrow(
        "SELECT model_url, author_id FROM assets WHERE id = $1",
        model_id,
    )
    if not row or not row.get("model_url"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )
        
    # 身份校验逻辑：防止用户 B 访问用户 A 链接
    if str(row["author_id"]) != current_user_id:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="这是私有模型，无权访问",
        )
            
    model_url = row["model_url"]
    
    # 生成通行证并下发临时链接（如果是 OSS 存储）
    if model_url.startswith("models/") or model_url.startswith("oss://"):
        try:
            from utils.oss_util import oss_manager
            # 获取真实的 Object Key
            oss_key = model_url.replace("oss://", "") if model_url.startswith("oss://") else model_url
            # 下发 60 秒后失效的长链接（Presigned URL）
            signed_url = oss_manager.generate_presigned_url(oss_key, expires=60)
            if signed_url:
                model_url = signed_url
        except Exception as e:
            logger.error(f"Gen url fail: {str(e)}")
            
    return {"model_id": model_id, "url": model_url}

# ========== Studio 生成模块 ==========


studio_jobs: Dict[str, Dict[str, Any]] = {}
studio_proxy_roots: Dict[str, Dict[str, Any]] = {}


class StudioDeferredChargeError(Exception):
    """3D任务完成后扣费失败（余额不足）时抛出。"""


STUDIO_UNSUCCESSFUL_RETENTION_HOURS = 3
STUDIO_UNSUCCESSFUL_RETENTION = timedelta(hours=STUDIO_UNSUCCESSFUL_RETENTION_HOURS)
IMAGE23D_PROMPT_PLACEHOLDERS = {"3D模型", "图生3D模型"}
STUDIO_ACTIVE_STATUS_SET = {
    "SUBMITTED",
    "PENDING",
    "QUEUED",
    "WAITING",
    "RUN",
    "RUNNING",
    "PROCESSING",
    "IN_PROGRESS",
}
STUDIO_FAILURE_STATUS_SET = {"FAILED", "FAIL", "ERROR", "CANCELLED"}
STUDIO_SUCCESS_STATUS_SET = {"SUCCEED", "SUCCESS", "DONE", "COMPLETED"}
STUDIO_TERMINAL_CONFIRM_POLLS = 2


def _normalize_studio_status_name(status: Optional[str]) -> str:
    normalized = (status or "UNKNOWN").upper()
    if normalized == "RUN":
        return "RUNNING"
    if normalized in {"FAIL", "ERROR"}:
        return "FAILED"
    if normalized in {"SUCCESS", "SUCCEED", "DONE"}:
        return "COMPLETED"
    return normalized


def _derive_studio_retry_status(current_status: Optional[str]) -> str:
    normalized = _normalize_studio_status_name(current_status)
    if normalized in STUDIO_ACTIVE_STATUS_SET:
        return normalized
    if normalized in {"SUBMITTED", "PENDING", "QUEUED", "WAITING"}:
        return normalized
    return "RUNNING"


def _parse_json_object(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _parse_json_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def _normalize_studio_params_blob(params: Any) -> Dict[str, Any]:
    raw = _parse_json_object(params)
    normalized = dict(raw)
    normalized["generation_params"] = _parse_json_object(raw.get("generation_params"))
    normalized["param_notes"] = _parse_json_list(raw.get("param_notes"))
    credits_used = raw.get("credits_used")
    try:
        normalized["credits_used"] = int(credits_used or 0)
    except Exception:
        normalized["credits_used"] = 0
    return normalized


def _normalize_studio_prompt(mode: Optional[str], prompt: Any) -> str:
    text = str(prompt or "").strip()
    if mode == "image23d" and text in IMAGE23D_PROMPT_PLACEHOLDERS:
        return ""
    return text


def _studio_job_api_display_prompt(
    mode: Any,
    with_texture: Any,
    generation_params: Any,
    raw_prompt: Any,
) -> Optional[str]:
    """轮询/侧栏等接口返回给前端的展示文案：图生3D 为参数摘要，文生3D 为用户提示词。"""
    if str(mode or "") == "image23d":
        wt = bool(True if with_texture is None else with_texture)
        return _format_hunyuan_image23d_display_prompt(wt, generation_params) or None
    text = _normalize_studio_prompt(mode, raw_prompt)
    return text or None


def _build_studio_history_params(
    *,
    base_model: Optional[str],
    with_texture: Optional[bool],
    generation_params: Any,
    param_notes: Any,
    credits_used: Any,
) -> Dict[str, Any]:
    return {
        "base_model": base_model or "hunyuan-3d",
        "with_texture": bool(True if with_texture is None else with_texture),
        "generation_params": _parse_json_object(generation_params),
        "param_notes": _parse_json_list(param_notes),
        "credits_used": int(credits_used or 0),
    }


def _normalize_single_file_studio_history_params(
    mode: Optional[str],
    params: Any,
    model_url: Optional[str],
) -> Dict[str, Any]:
    """文生3D/图生3D：历史 params 中单文件统一 download/render，避免冗余键（fix-print 行为）。"""
    normalized = _normalize_studio_params_blob(params)
    if not _is_single_file_studio_3d_mode(mode):
        return normalized

    has_explicit_model_routes = any(
        normalized.get(key)
        for key in (
            "gcode_source_model_url",
            "selected_model_url",
            "selected_model_format",
            "gcode_source_model_format",
            "render_model_format",
        )
    )
    if has_explicit_model_routes:
        return normalized

    single_url = str(
        model_url or normalized.get("download_model_url") or normalized.get("render_model_url") or ""
    ).strip()
    if single_url:
        normalized["download_model_url"] = single_url
        normalized["render_model_url"] = single_url

    for key in (
        "gcode_source_model_url",
        "gcode_source_model_format",
        "selected_model_url",
        "selected_model_format",
        "download_model_format",
        "render_model_format",
    ):
        normalized.pop(key, None)
    return normalized


def _resolve_model_format(url: Optional[str], fallback_format: Optional[str] = None) -> Optional[str]:
    normalized = _guess_remote_file_extension(url, fallback_format=fallback_format, default="").lstrip(".").lower()
    return normalized or None


def _data_url_extension(data: str, default: str = ".png") -> str:
    if not isinstance(data, str) or not data.startswith("data:image"):
        return default
    header = data.split(",", 1)[0].lower()
    mime = header.split(";")[0]
    mapping = {
        "data:image/jpeg": ".jpg",
        "data:image/jpg": ".jpg",
        "data:image/png": ".png",
        "data:image/webp": ".webp",
        "data:image/bmp": ".bmp",
        "data:image/gif": ".gif",
    }
    return mapping.get(mime, default)


def _parse_datetime_value(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


async def _persist_image_base64_preview(
    image_base64: Optional[str],
    user_id: str,
    job_uuid: Optional[str] = None,
) -> Optional[str]:
    if not image_base64:
        return None
    try:
        encoded = image_base64
        if image_base64.startswith("data:image"):
            _, encoded = image_base64.split(",", 1)
        image_bytes = base64.b64decode(encoded)
        ext = _data_url_extension(image_base64)
        from utils.oss_util import oss_manager

        oss_key = await asyncio.to_thread(
            oss_manager.upload_file_bytes,
            user_id,
            image_bytes,
            ext,
            job_uuid,
        )
        return f"oss://{oss_key}" if oss_key else None
    except Exception as e:
        logger.warning("persist image23d preview failed: %s", e)
        return None


async def _repair_inconsistent_studio_jobs(db: DatabaseManager) -> None:
    if not getattr(db, "pool", None):
        return
    await db.execute(
        """
        UPDATE studio_jobs
        SET status = 'COMPLETED',
            last_message = '生成完成',
            finished_at = COALESCE(finished_at, now()),
            terminal_candidate_status = NULL,
            terminal_candidate_count = 0,
            terminal_candidate_seen_at = NULL,
            notified_at = CASE
                WHEN status IN ('FAILED', 'FAIL', 'ERROR', 'CANCELLED') THEN NULL
                ELSE notified_at
            END
        WHERE asset_id IS NOT NULL
          AND status IS DISTINCT FROM 'COMPLETED'
        """
    )


async def _repair_image23d_placeholder_prompts(db: DatabaseManager) -> None:
    if not getattr(db, "pool", None):
        return
    await db.execute(
        """
        UPDATE studio_history AS h
        SET prompt = ''
        FROM studio_jobs AS j
        WHERE h.asset_id = j.asset_id
          AND h.mode = 'image23d'
          AND j.mode = 'image23d'
          AND COALESCE(j.prompt, '') = ''
          AND COALESCE(h.prompt, '') IN ('3D模型', '图生3D模型')
        """
    )
    await db.execute(
        """
        UPDATE assets AS a
        SET prompt = ''
        FROM studio_jobs AS j
        WHERE a.id = j.asset_id
          AND j.mode = 'image23d'
          AND COALESCE(j.prompt, '') = ''
          AND COALESCE(a.prompt, '') IN ('3D模型', '图生3D模型')
        """
    )


async def _cleanup_expired_unsuccessful_studio_jobs(db: DatabaseManager) -> None:
    if not getattr(db, "pool", None):
        return
    cutoff = datetime.now(timezone.utc) - STUDIO_UNSUCCESSFUL_RETENTION
    await db.execute(
        """
        DELETE FROM studio_jobs
        WHERE asset_id IS NULL
          AND status IN ('FAILED', 'FAIL', 'ERROR', 'CANCELLED')
          AND COALESCE(finished_at, created_at) < $1
        """,
        cutoff,
    )
    expired_ids = [
        job_id
        for job_id, data in list(studio_jobs.items())
        if _normalize_studio_status_name(data.get("status")) in {"FAILED", "CANCELLED"}
        and (_parse_datetime_value(data.get("finished_at") or data.get("created_at")) or cutoff) < cutoff
    ]
    for job_id in expired_ids:
        studio_jobs.pop(job_id, None)


def _register_studio_job(job_id: str, payload: Dict[str, Any]) -> None:
    studio_jobs[job_id] = {
        "job_id": job_id,
        "status": "SUBMITTED",
        "last_message": "任务已提交，等待排队...",
        "asset_id": None,
        "render_model_url": payload.get("render_model_url"),
        "terminal_candidate_status": None,
        "terminal_candidate_count": 0,
        "terminal_candidate_seen_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **payload,
        "generation_params": _parse_json_object(payload.get("generation_params")),
        "param_notes": _parse_json_list(payload.get("param_notes")),
        "prompt": payload.get("prompt") or "",
    }


async def _persist_studio_job_state(
    db: DatabaseManager,
    job_id: str,
    *,
    status: str,
    last_message: Optional[str] = None,
    asset_id: Optional[str] = None,
    render_model_url: Optional[str] = None,
    finished: bool = False,
    clear_notified: bool = False,
    terminal_candidate_status: Optional[str] = None,
    terminal_candidate_count: Optional[int] = None,
    terminal_candidate_seen_at: Optional[datetime] = None,
    clear_terminal_candidate: bool = False,
) -> None:
    normalized_status = _normalize_studio_status_name(status)
    job = studio_jobs.get(job_id)
    if job is not None:
        job["status"] = normalized_status
        if last_message is not None:
            job["last_message"] = last_message
        if asset_id is not None:
            job["asset_id"] = asset_id
        if render_model_url is not None:
            job["render_model_url"] = render_model_url
        if clear_terminal_candidate:
            job["terminal_candidate_status"] = None
            job["terminal_candidate_count"] = 0
            job["terminal_candidate_seen_at"] = None
        else:
            if terminal_candidate_status is not None:
                job["terminal_candidate_status"] = _normalize_studio_status_name(terminal_candidate_status)
            if terminal_candidate_count is not None:
                job["terminal_candidate_count"] = int(terminal_candidate_count or 0)
            if terminal_candidate_seen_at is not None:
                job["terminal_candidate_seen_at"] = terminal_candidate_seen_at.isoformat()
        if finished:
            job["finished_at"] = datetime.now(timezone.utc).isoformat()

    if not getattr(db, "pool", None):
        return

    await db.execute(
        """
        UPDATE studio_jobs
        SET status = $2,
            last_message = COALESCE($3, last_message),
            asset_id = COALESCE($4::uuid, asset_id),
            render_model_url = COALESCE($5, render_model_url),
            finished_at = CASE WHEN $6 THEN COALESCE(finished_at, now()) ELSE finished_at END,
            notified_at = CASE WHEN $7 THEN NULL ELSE notified_at END,
            terminal_candidate_status = CASE
                WHEN $11 THEN NULL
                WHEN $8::text IS NOT NULL THEN $8::text
                ELSE terminal_candidate_status
            END,
            terminal_candidate_count = CASE
                WHEN $11 THEN 0
                WHEN $9::integer IS NOT NULL THEN $9::integer
                ELSE terminal_candidate_count
            END,
            terminal_candidate_seen_at = CASE
                WHEN $11 THEN NULL
                WHEN $10::timestamptz IS NOT NULL THEN $10::timestamptz
                ELSE terminal_candidate_seen_at
            END
        WHERE job_id = $1
        """,
        job_id,
        normalized_status,
        last_message,
        asset_id,
        render_model_url,
        finished,
        clear_notified,
        _normalize_studio_status_name(terminal_candidate_status) if terminal_candidate_status else None,
        int(terminal_candidate_count) if terminal_candidate_count is not None else None,
        terminal_candidate_seen_at,
        clear_terminal_candidate,
    )

def _build_studio_status(status: str) -> Dict[str, Any]:
    """将上游状态映射为前端可直接使用的阶段信息。"""
    normalized = _normalize_studio_status_name(status)
    if normalized in ["SUBMITTED"]:
        return {"status": "SUBMITTED", "progress": 12, "message": "任务已提交，等待排队...", "retryable": False}
    if normalized in ["PENDING", "QUEUED", "WAITING"]:
        return {"status": normalized, "progress": 22, "message": "任务排队中...", "retryable": False}
    if normalized in ["RUNNING", "PROCESSING", "IN_PROGRESS"]:
        return {"status": normalized, "progress": 34, "message": "AI 正在生成3D模型...", "retryable": False}
    if normalized in ["SUCCEED", "COMPLETED", "SUCCESS", "DONE"]:
        return {"status": "COMPLETED", "progress": 100, "message": "生成完成", "retryable": False}
    if normalized in ["CANCELLED"]:
        return {"status": "CANCELLED", "progress": 0, "message": "任务已取消", "retryable": True}
    if normalized in ["FAILED", "FAIL", "ERROR"]:
        return {"status": "FAILED", "progress": 0, "message": "任务失败", "retryable": True}
    return {"status": normalized, "progress": 28, "message": "AI 正在处理中...", "retryable": True}


def _coerce_datetime_value(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _apply_elapsed_progress(
    stage: Dict[str, Any],
    *,
    created_at: Any = None,
    stage_started_at: Any = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """为非终态任务补一层按耗时增长的进度，避免长任务长期停在固定值。"""
    if not isinstance(stage, dict):
        return stage

    status_name = _normalize_studio_status_name(stage.get("status"))
    if status_name in {"COMPLETED", "FAILED", "CANCELLED"}:
        return stage

    start_dt = _coerce_datetime_value(stage_started_at) or _coerce_datetime_value(created_at)
    if not start_dt:
        return stage

    current_dt = now or datetime.now(timezone.utc)
    elapsed_seconds = max(0.0, (current_dt - start_dt).total_seconds())
    base_progress = int(stage.get("progress") or 0)

    if status_name == "SUBMITTED":
        dynamic_progress = min(14, 8 + int(elapsed_seconds * 0.45))
    elif status_name in {"PENDING", "QUEUED", "WAITING"}:
        dynamic_progress = min(30, 16 + int(elapsed_seconds * 0.22))
    elif status_name in {"RUNNING", "PROCESSING", "IN_PROGRESS"}:
        dynamic_progress = min(86, 34 + int(elapsed_seconds * 0.18))
    else:
        dynamic_progress = min(72, 24 + int(elapsed_seconds * 0.16))

    next_stage = dict(stage)
    next_stage["progress"] = max(base_progress, dynamic_progress)
    return next_stage


def _build_studio_finalizing_stage(current_status: Optional[str]) -> Dict[str, Any]:
    """上游已完成，但本地仍在落库/整理结果时的稳定展示阶段。"""
    base_stage = _build_studio_status(_derive_studio_retry_status(current_status))
    return {
        **base_stage,
        "progress": max(int(base_stage.get("progress") or 0), 92),
        "message": "结果整理中...",
        "retryable": False,
    }


def _resolve_studio_polled_stage(
    *,
    current_status: Optional[str],
    remote_status: Optional[str],
    candidate_status: Optional[str],
    candidate_count: Any,
) -> Dict[str, Any]:
    normalized_remote = _normalize_studio_status_name(remote_status)
    normalized_candidate = _normalize_studio_status_name(candidate_status)
    current_candidate_count = int(candidate_count or 0)

    if normalized_remote == "COMPLETED":
        return {
            "stage": _build_studio_status("COMPLETED"),
            "finalized": True,
            "clear_candidate": True,
            "candidate_status": None,
            "candidate_count": 0,
        }

    if normalized_remote not in {"FAILED", "CANCELLED"}:
        return {
            "stage": _build_studio_status(normalized_remote),
            "finalized": False,
            "clear_candidate": True,
            "candidate_status": None,
            "candidate_count": 0,
        }

    next_candidate_count = current_candidate_count + 1 if normalized_candidate == normalized_remote else 1
    if next_candidate_count >= STUDIO_TERMINAL_CONFIRM_POLLS:
        return {
            "stage": _build_studio_status(normalized_remote),
            "finalized": True,
            "clear_candidate": True,
            "candidate_status": None,
            "candidate_count": 0,
        }

    retry_stage = _build_studio_status(_derive_studio_retry_status(current_status))
    retry_stage["message"] = "状态波动，正在再次确认..."
    retry_stage["retryable"] = False
    return {
        "stage": retry_stage,
        "finalized": False,
        "clear_candidate": False,
        "candidate_status": normalized_remote,
        "candidate_count": next_candidate_count,
    }


def _resolve_studio_polled_stage(
    *,
    current_status: Optional[str],
    remote_status: Optional[str],
    candidate_status: Optional[str],
    candidate_count: Any,
) -> Dict[str, Any]:
    normalized_remote = _normalize_studio_status_name(remote_status)
    normalized_candidate = _normalize_studio_status_name(candidate_status)
    current_candidate_count = int(candidate_count or 0)

    if normalized_remote == "COMPLETED":
        return {
            "stage": _build_studio_status("COMPLETED"),
            "finalized": True,
            "clear_candidate": True,
            "candidate_status": None,
            "candidate_count": 0,
        }

    if normalized_remote not in {"FAILED", "CANCELLED"}:
        return {
            "stage": _build_studio_status(normalized_remote),
            "finalized": False,
            "clear_candidate": True,
            "candidate_status": None,
            "candidate_count": 0,
        }

    next_candidate_count = current_candidate_count + 1 if normalized_candidate == normalized_remote else 1
    if next_candidate_count >= STUDIO_TERMINAL_CONFIRM_POLLS:
        return {
            "stage": _build_studio_status(normalized_remote),
            "finalized": True,
            "clear_candidate": True,
            "candidate_status": None,
            "candidate_count": 0,
        }

    retry_stage = _build_studio_status(_derive_studio_retry_status(current_status))
    retry_stage["message"] = "状态波动，正在再次确认..."
    retry_stage["retryable"] = False
    return {
        "stage": retry_stage,
        "finalized": False,
        "clear_candidate": False,
        "candidate_status": normalized_remote,
        "candidate_count": next_candidate_count,
    }


def _cleanup_studio_proxy_roots() -> None:
    """清理过期代理会话，避免内存持续增长。"""
    now_ts = datetime.now(timezone.utc).timestamp()
    expire_seconds = 3600
    expired = [
        token for token, data in studio_proxy_roots.items()
        if now_ts - float(data.get("updated_at", 0)) > expire_seconds
    ]
    for token in expired:
        studio_proxy_roots.pop(token, None)


STUDIO_HISTORY_LIMIT = 500


async def _ensure_studio_history_limit(db: DatabaseManager, user_id: str) -> None:
    """保证该用户 studio_history 条数不超过 STUDIO_HISTORY_LIMIT，多则删最旧的。"""
    uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    n = await db.fetchval("SELECT COUNT(*) FROM studio_history WHERE user_id = $1", uid)
    if (n or 0) < STUDIO_HISTORY_LIMIT:
        return
    row = await db.fetchrow(
        "SELECT created_at FROM studio_history WHERE user_id = $1 ORDER BY created_at DESC OFFSET $2 LIMIT 1",
        uid,
        STUDIO_HISTORY_LIMIT - 1,
    )
    if row:
        await db.execute(
            "DELETE FROM studio_history WHERE user_id = $1 AND created_at <= $2",
            uid,
            row["created_at"],
        )


async def _insert_studio_history(
    db: DatabaseManager,
    user_id: str,
    mode: str,
    prompt: str | None,
    params: dict,
    preview_url: str | None,
    asset_id: str | None,
) -> None:
    """写入一条造梦历史；写入前会执行上限清理（500 条）。"""
    await _ensure_studio_history_limit(db, user_id)
    uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    aid = uuid.UUID(asset_id) if asset_id else None
    await db.execute(
        """
        INSERT INTO studio_history (user_id, mode, prompt, params, preview_url, asset_id)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        uid,
        mode,
        _normalize_studio_prompt(mode, prompt),
        json.dumps(params) if isinstance(params, dict) else "{}",
        preview_url,
        aid,
    )


async def _ensure_studio_history_model_routes(
    db: DatabaseManager,
    *,
    asset_id: str,
    user_id: str,
    selected_model_url: Optional[str],
    selected_model_format: Optional[str],
    render_model_url: Optional[str],
    render_model_format: Optional[str],
    gcode_source_model_url: Optional[str],
    gcode_source_model_format: Optional[str],
) -> None:
    if not asset_id:
        return

    row = await db.fetchrow(
        """
        SELECT id, params
        FROM studio_history
        WHERE asset_id = $1
          AND user_id = $2
        ORDER BY created_at DESC
        LIMIT 1
        """,
        asset_id,
        uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
    )
    if not row:
        return

    params = _normalize_studio_params_blob(row["params"])
    changed = False

    def _put(key: str, value: Optional[str]) -> None:
        nonlocal changed
        if not value:
            return
        if params.get(key) != value:
            params[key] = value
            changed = True

    _put("download_model_url", selected_model_url)
    _put("selected_model_url", selected_model_url)
    _put("download_model_format", selected_model_format)
    _put("selected_model_format", selected_model_format)
    _put("render_model_url", render_model_url)
    _put("render_model_format", render_model_format)
    _put("gcode_source_model_url", gcode_source_model_url)
    _put("gcode_source_model_format", gcode_source_model_format)

    if changed:
        await db.execute(
            "UPDATE studio_history SET params = $2::jsonb WHERE id = $1",
            row["id"],
            json.dumps(params, ensure_ascii=False),
        )

    if selected_model_url:
        await db.execute(
            "UPDATE assets SET model_url = $2 WHERE id = $1 AND model_url IS DISTINCT FROM $2",
            asset_id,
            selected_model_url,
        )


async def _repair_missing_printable_model_routes(
    db: DatabaseManager,
    *,
    asset_id: Optional[str],
    user_id: str,
    job_uuid: str,
    requested_result_format: Optional[str],
    history_params: Optional[Dict[str, Any]],
    asset_model_url: Optional[str],
    render_model_url: Optional[str],
) -> Dict[str, Optional[str]]:
    normalized_requested = _normalize_requested_result_format(requested_result_format)
    params = _normalize_studio_params_blob(history_params or {})

    result = {
        "selected_model_url": None,
        "selected_model_format": None,
        "render_model_url": render_model_url or params.get("render_model_url"),
        "render_model_format": (
            str(params.get("render_model_format") or "").strip().lower()
            or _resolve_model_format(render_model_url or params.get("render_model_url"))
        ),
        "gcode_source_model_url": None,
        "gcode_source_model_format": None,
    }
    if normalized_requested != "stl" or not asset_id:
        return result

    raw_selected_model_url = params.get("selected_model_url") or params.get("download_model_url")
    raw_selected_model_format = (
        params.get("selected_model_format")
        or params.get("download_model_format")
        or _resolve_model_format(raw_selected_model_url, fallback_format=normalized_requested)
    )
    raw_gcode_source_model_url = params.get("gcode_source_model_url")
    raw_gcode_source_model_format = (
        params.get("gcode_source_model_format")
        or _resolve_model_format(raw_gcode_source_model_url, fallback_format=normalized_requested)
    )

    if raw_selected_model_url and _matches_requested_result_format(
        raw_selected_model_url,
        normalized_requested,
        raw_selected_model_format,
    ):
        result["selected_model_url"] = str(raw_selected_model_url).strip()
        result["selected_model_format"] = str(raw_selected_model_format or normalized_requested).strip().lower()
    if raw_gcode_source_model_url and _matches_requested_result_format(
        raw_gcode_source_model_url,
        normalized_requested,
        raw_gcode_source_model_format,
    ):
        result["gcode_source_model_url"] = str(raw_gcode_source_model_url).strip()
        result["gcode_source_model_format"] = str(raw_gcode_source_model_format or normalized_requested).strip().lower()

    if result["selected_model_url"] and result["gcode_source_model_url"]:
        return result

    if result["gcode_source_model_url"] and not result["selected_model_url"]:
        result["selected_model_url"] = result["gcode_source_model_url"]
        result["selected_model_format"] = result["gcode_source_model_format"]
        await _ensure_studio_history_model_routes(
            db,
            asset_id=asset_id,
            user_id=user_id,
            selected_model_url=result["selected_model_url"],
            selected_model_format=result["selected_model_format"],
            render_model_url=result["render_model_url"],
            render_model_format=result["render_model_format"],
            gcode_source_model_url=result["gcode_source_model_url"],
            gcode_source_model_format=result["gcode_source_model_format"],
        )
        return result

    candidate_primary_url = (
        params.get("download_model_url")
        or params.get("selected_model_url")
        or asset_model_url
    )
    repaired_gcode_source_url, repaired_gcode_source_format = await _build_gcode_source_payload_from_model_url(
        model_url=str(candidate_primary_url).strip() if candidate_primary_url else None,
        requested_result_format=normalized_requested,
        user_id=user_id,
        job_uuid=job_uuid or asset_id,
    )
    if not repaired_gcode_source_url or not repaired_gcode_source_format:
        return result

    repaired_gcode_source_format = repaired_gcode_source_format.strip().lower()
    result["selected_model_url"] = repaired_gcode_source_url
    result["selected_model_format"] = repaired_gcode_source_format
    result["gcode_source_model_url"] = repaired_gcode_source_url
    result["gcode_source_model_format"] = repaired_gcode_source_format

    await _ensure_studio_history_model_routes(
        db,
        asset_id=asset_id,
        user_id=user_id,
        selected_model_url=result["selected_model_url"],
        selected_model_format=result["selected_model_format"],
        render_model_url=result["render_model_url"],
        render_model_format=result["render_model_format"],
        gcode_source_model_url=result["gcode_source_model_url"],
        gcode_source_model_format=result["gcode_source_model_format"],
    )
    logger.info(
        "已回补缺失的 STL printable 路由: asset_id=%s job=%s selected=%s",
        asset_id,
        job_uuid,
        repaired_gcode_source_url,
    )
    return result


async def _finalize_sync_generated_model_routes(
    db: DatabaseManager,
    *,
    asset_id: str,
    user_id: str,
    requested_result_format: Optional[str],
    history_params: Optional[Dict[str, Any]],
    asset_model_url: Optional[str],
    selected_model_url: Optional[str],
    selected_model_format: Optional[str],
    render_model_url: Optional[str],
    render_model_format: Optional[str],
    gcode_source_model_url: Optional[str],
    gcode_source_model_format: Optional[str],
    job_uuid: str,
) -> Dict[str, Optional[str]]:
    normalized_requested = _normalize_requested_result_format(requested_result_format)
    final_selected_url = str(selected_model_url or "").strip() or None
    final_selected_format = _normalize_requested_result_format(selected_model_format) or _resolve_model_format(
        final_selected_url,
        fallback_format=selected_model_format,
    )
    final_gcode_source_url = str(gcode_source_model_url or "").strip() or None
    final_gcode_source_format = _normalize_requested_result_format(gcode_source_model_format) or _resolve_model_format(
        final_gcode_source_url,
        fallback_format=gcode_source_model_format,
    )
    final_render_url = str(render_model_url or "").strip() or None
    final_render_format = _resolve_model_format(final_render_url, fallback_format=render_model_format)

    needs_printable_repair = normalized_requested == "stl" and (
        not _matches_requested_result_format(
            final_selected_url,
            normalized_requested,
            final_selected_format,
        )
        or not _matches_requested_result_format(
            final_gcode_source_url,
            normalized_requested,
            final_gcode_source_format,
        )
    )

    if needs_printable_repair:
        repaired = await _repair_missing_printable_model_routes(
            db,
            asset_id=asset_id,
            user_id=user_id,
            job_uuid=job_uuid,
            requested_result_format=normalized_requested,
            history_params=history_params,
            asset_model_url=asset_model_url,
            render_model_url=final_render_url,
        )
        final_selected_url = repaired.get("selected_model_url") or final_selected_url
        final_selected_format = repaired.get("selected_model_format") or final_selected_format
        final_render_url = repaired.get("render_model_url") or final_render_url
        final_render_format = repaired.get("render_model_format") or final_render_format
        final_gcode_source_url = repaired.get("gcode_source_model_url") or final_gcode_source_url
        final_gcode_source_format = repaired.get("gcode_source_model_format") or final_gcode_source_format
    else:
        await _ensure_studio_history_model_routes(
            db,
            asset_id=asset_id,
            user_id=user_id,
            selected_model_url=final_selected_url,
            selected_model_format=final_selected_format,
            render_model_url=final_render_url,
            render_model_format=final_render_format,
            gcode_source_model_url=final_gcode_source_url,
            gcode_source_model_format=final_gcode_source_format,
        )

    return {
        "selected_model_url": final_selected_url,
        "selected_model_format": final_selected_format,
        "render_model_url": final_render_url,
        "render_model_format": final_render_format,
        "gcode_source_model_url": final_gcode_source_url,
        "gcode_source_model_format": final_gcode_source_format,
    }


async def _deduct_points_in_tx(conn: asyncpg.Connection, user_id: uuid.UUID, amount: int, job_id: Optional[str] = None) -> bool:
    """
    事务内扣减积分：使用 CreditService 进行 FIFO 消耗。
    注意：这个函数在事务内调用，传入的 conn 已经在事务中。
    """
    if amount <= 0:
        return True
    
    try:
        # 创建一个临时的 pool 对象，直接使用当前事务的连接
        class TxPool:
            def __init__(self, connection):
                self._conn = connection
            
            async def execute(self, query, *args):
                return await self._conn.execute(query, *args)
            
            async def fetch(self, query, *args):
                return await self._conn.fetch(query, *args)
            
            async def fetchrow(self, query, *args):
                return await self._conn.fetchrow(query, *args)
            
            async def fetchval(self, query, *args):
                return await self._conn.fetchval(query, *args)
        
        from services.credit_service import CreditService
        credit_service = CreditService(TxPool(conn))
        
        # 传入 conn 参数，让 CreditService 在当前事务中执行
        success = await credit_service.consume_credits(
            user_id=str(user_id),
            amount=amount,
            reason="studio_job",
            related_id=job_id,  # 传入 job_id 用于关联
            conn=conn  # 传入当前事务的连接
        )
        return success
    except Exception as e:
        logger.error(f"事务内扣除积分失败: {e}")
        return False


async def _transfer_url_to_oss(
    url: str,
    user_id: str,
    ext: str = ".bin",
    job_uuid: Optional[str] = None,
    infer_model_extension: bool = False,
) -> str:
    """将给定的外链 URL 下载下来并作为私有文件传至 OSS。"""
    try:
        from utils.oss_util import oss_manager
        if not url or url.startswith("oss://") or not oss_manager.bucket:
            return url
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    upload_ext = ext
                    if infer_model_extension:
                        detected_ext = _detect_model_extension_by_magic(data, ext)
                        if detected_ext != ext:
                            logger.warning(
                                "模型扩展名与文件头不一致，自动修正: declared=%s detected=%s url=%s",
                                ext,
                                detected_ext,
                                (url or "")[:160],
                            )
                        upload_ext = detected_ext
                    oss_key = await asyncio.to_thread(oss_manager.upload_file_bytes, user_id, data, upload_ext, job_uuid)
                    if oss_key:
                        return f"oss://{oss_key}"
    except Exception as e:
        logger.error(f"Transfer to OSS failed: {e}")
    return url

async def _complete_studio_job_if_done(
    db: DatabaseManager,
    job_id: str,
    job_meta: Dict[str, Any],
    preview_url: Optional[str],
    model_url: str,
    render_model_url: Optional[str],
    current_user_id: Any,
    status_result: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    在事务中：若该 job 尚未写入 asset，则写入 asset + studio_history 并更新 studio_jobs.asset_id。
    用于轮询完成与后台同步，避免重复写入。返回 asset_id 或 None。
    """
    uid = current_user_id if isinstance(current_user_id, uuid.UUID) else uuid.UUID(str(current_user_id))
    
    # 生成一个统一的文件夹 UUID，让该任务的模型和贴图存在一起
    job_uuid = str(uuid.uuid4())
    
    generation_params = job_meta.get("generation_params") if isinstance(job_meta.get("generation_params"), dict) else {}
    requested_result_format = generation_params.get("ResultFormat") if isinstance(generation_params, dict) else None
    should_prepare_printable_source = _should_prepare_printable_source(requested_result_format)
    render_model_url, render_model_format = _resolve_render_output_payload(
        status_result=status_result,
        fallback_model_url=render_model_url,
        fallback_model_format=_resolve_model_format(render_model_url),
    )
    gcode_source_url, gcode_source_format = (None, None)
    if should_prepare_printable_source:
        gcode_source_url, gcode_source_format = _derive_gcode_source_payload(
            model_url=model_url,
            fallback_format=requested_result_format,
            status_result=status_result,
        )
    selected_source_url, selected_source_format = _resolve_selected_output_payload(
        status_result=status_result,
        requested_result_format=requested_result_format,
        default_model_url=model_url,
        default_model_format=_resolve_model_format(model_url, fallback_format=requested_result_format),
        gcode_source_url=gcode_source_url,
        gcode_source_format=gcode_source_format,
    )
    primary_model_url = selected_source_url or model_url

    # 按真实返回格式保存对象名，避免 STL/OBJ 等被错误伪装成 .glb。
    model_ext = _guess_remote_file_extension(
        primary_model_url,
        fallback_format=selected_source_format or requested_result_format,
        default=".glb",
    )
    preview_ext = _guess_remote_file_extension(preview_url or model_url, default=".png")
    # 将模型/图片外链同步上传到私有 OSS 存储桶
    oss_model_url = await _transfer_url_to_oss(
        primary_model_url,
        str(uid),
        model_ext,
        job_uuid,
        infer_model_extension=True,
    )
    oss_preview_url = await _transfer_url_to_oss(preview_url or model_url, str(uid), preview_ext, job_uuid) if preview_url else oss_model_url
    oss_model_format = _resolve_model_format(oss_model_url)

    # 合并分支逻辑：
    # 1. 先根据 should_prepare_printable_source 判断是否需要生成可打印源
    # 2. 生成 gcode_source_url, gcode_source_format
    # 3. 兼容 download_model_format 变量
    oss_gcode_source_url = None
    if should_prepare_printable_source:
        gcode_source_url, gcode_source_format = _derive_gcode_source_payload(
            model_url=model_url,
            fallback_format=requested_result_format,
            status_result=status_result,
        )
    if gcode_source_url and gcode_source_format:
        if gcode_source_url == primary_model_url:
            if _is_gcode_source_format(oss_model_format):
                oss_gcode_source_url = oss_model_url
                gcode_source_format = oss_model_format
            else:
                logger.warning(
                    "候选 gcode 源文件内容与声明格式不一致，放弃直接复用: declared=%s actual=%s url=%s",
                    gcode_source_format,
                    oss_model_format,
                    (primary_model_url or "")[:160],
                )
        else:
            candidate_gcode_source_url = await _transfer_url_to_oss(
                gcode_source_url,
                str(uid),
                f".{gcode_source_format}",
                job_uuid,
                infer_model_extension=True,
            )
            candidate_gcode_source_format = _resolve_model_format(candidate_gcode_source_url)
            if _is_gcode_source_format(candidate_gcode_source_format):
                oss_gcode_source_url = candidate_gcode_source_url
                gcode_source_format = candidate_gcode_source_format
            else:
                logger.warning(
                    "上传后的 gcode 源文件仍非可打印格式，放弃使用: declared=%s actual=%s url=%s",
                    gcode_source_format,
                    candidate_gcode_source_format,
                    (gcode_source_url or "")[:160],
                )
    # 兼容两种分支的后续处理：若需要可打印源但未生成，则尝试从候选模型推导
    if should_prepare_printable_source and not oss_gcode_source_url:
        oss_gcode_source_url, gcode_source_format = await _build_gcode_source_payload_from_model_candidates(
            status_result=status_result,
            primary_model_url=primary_model_url,
            render_model_url=render_model_url,
            requested_result_format=requested_result_format,
            user_id=str(uid),
            job_uuid=job_uuid,
        )

    # 同步 render 模型到 OSS（若存在）
    oss_render_model_url = None
    if render_model_url and render_model_format:
        if render_model_url == primary_model_url:
            oss_render_model_url = oss_model_url
        elif render_model_url == gcode_source_url and oss_gcode_source_url:
            oss_render_model_url = oss_gcode_source_url
        else:
            oss_render_model_url = await _transfer_url_to_oss(
                render_model_url,
                str(uid),
                _guess_remote_file_extension(render_model_url, fallback_format=render_model_format, default=".glb"),
                job_uuid,
            )

    # 计算最终对外的 download/selected 输出（默认走 OSS）
    selected_model_url, selected_model_format = _resolve_selected_output_payload(
        status_result=None,
        requested_result_format=requested_result_format,
        default_model_url=oss_model_url,
        default_model_format=oss_model_format,
        gcode_source_url=oss_gcode_source_url,
        gcode_source_format=gcode_source_format,
    )
    selected_model_url, selected_model_format = _prefer_printable_selected_output(
        requested_result_format=requested_result_format,
        selected_model_url=selected_model_url,
        selected_model_format=selected_model_format,
        gcode_source_url=oss_gcode_source_url,
        gcode_source_format=gcode_source_format,
    )

    if not db.pool:
        return None
    async with db.pool.acquire() as conn:
        async with conn.transaction():
            job_row = await conn.fetchrow(
                """
                SELECT job_id, credits_used, charged_at, mode, preview_url
                FROM studio_jobs
                WHERE job_id = $1 AND asset_id IS NULL
                FOR UPDATE
                """,
                job_id,
            )
            if not job_row:
                return None
            credits_needed = int(job_row["credits_used"] or job_meta.get("credits_used") or 0)
            if credits_needed < 0:
                credits_needed = 0
            if job_row["charged_at"] is None:
                ok = await _deduct_points_in_tx(conn, uid, credits_needed, job_id)
                if not ok:
                    raise StudioDeferredChargeError(
                        f"任务已完成，但当前积分不足以扣费（需{credits_needed}积分）。请充值后重试领取结果。"
                    )

            base_model = job_meta.get("base_model") or "hunyuan-3d"
            mode = str(job_row.get("mode") or job_meta.get("mode") or "text23d")
            prompt = _normalize_studio_prompt(mode, job_meta.get("prompt"))
            with_texture = job_meta.get("with_texture", True)
            source_ref: Optional[str] = None
            if mode == "image23d":
                history_prompt = _format_hunyuan_image23d_display_prompt(with_texture, job_meta.get("generation_params"))
                asset_prompt = history_prompt
                # 以 DB 提交时写入的参考图为准（避免 UPDATE 后 preview_url 被 3D 预览污染、或内存 job 已错）
                source_ref = job_row.get("preview_url") or job_meta.get("source_image_url") or job_meta.get("preview_url")
                asset_image_url = source_ref or oss_preview_url
                history_preview_url = source_ref or oss_preview_url
            else:
                history_prompt = prompt
                asset_prompt = prompt if prompt else "3D模型"
                asset_image_url = oss_preview_url
                history_preview_url = oss_preview_url
            params = _build_studio_history_params(
                base_model=base_model,
                with_texture=with_texture,
                generation_params=job_meta.get("generation_params"),
                param_notes=job_meta.get("param_notes"),
                credits_used=job_meta.get("credits_used"),
            )
            if mode == "image23d" and source_ref and oss_preview_url:
                params["generated_preview_url"] = oss_preview_url
            if mode == "image23d" and source_ref:
                params["reference_image_url"] = source_ref
            if oss_render_model_url:
                params["render_model_url"] = oss_render_model_url
            if render_model_format:
                params["render_model_format"] = render_model_format
            normalized_requested_result_format = _normalize_requested_result_format(requested_result_format)
            db_model_url = selected_model_url or oss_model_url
            db_model_format = _resolve_model_format(
                db_model_url,
                fallback_format=selected_model_format or normalized_requested_result_format,
            )
            # ResultFormat=STL 时优先落库 STL，避免数据库 model_url 仍指向 GLB。
            if (
                normalized_requested_result_format == "stl"
                and oss_gcode_source_url
                and _is_gcode_source_format(gcode_source_format)
                and db_model_format != "stl"
            ):
                db_model_url = oss_gcode_source_url
                db_model_format = str(gcode_source_format or "stl").strip().lower()
            if db_model_url:
                params["download_model_url"] = db_model_url
                params["selected_model_url"] = db_model_url
            if db_model_format:
                params["download_model_format"] = db_model_format
                params["selected_model_format"] = db_model_format
            if oss_gcode_source_url and gcode_source_format:
                params["gcode_source_model_url"] = oss_gcode_source_url
                params["gcode_source_model_format"] = gcode_source_format
            mode_for_history = "text23d" if mode == "text23d" else "image23d"

            asset_row = await conn.fetchrow(
                """
                INSERT INTO assets (author_id, image_url, model_url, prompt, base_model,
                                  seed, steps, sampler, is_published)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, FALSE)
                RETURNING id
                """,
                uid,
                asset_image_url,
                db_model_url,
                asset_prompt,
                base_model,
                None, None, None,
            )
            aid = str(asset_row["id"])
            # 图生 3D：保留 studio_jobs.preview_url 为参考图，不把 3D 结果预览写回（否则造梦/社区缩略图被顶掉）
            if mode == "image23d":
                await conn.execute(
                    """
                    UPDATE studio_jobs
                    SET asset_id = $1,
                        status = 'COMPLETED',
                        last_message = '生成完成',
                        finished_at = COALESCE(finished_at, now()),
                        notified_at = NULL,
                        preview_url = preview_url,
                        render_model_url = $3
                    WHERE job_id = $2
                    """,
                    aid,
                    job_id,
                    oss_render_model_url,
                )
            else:
                await conn.execute(
                    """
                    UPDATE studio_jobs
                    SET asset_id = $1,
                        status = 'COMPLETED',
                        last_message = '生成完成',
                        finished_at = COALESCE(finished_at, now()),
                        notified_at = NULL,
                        preview_url = $3,
                        render_model_url = $4
                    WHERE job_id = $2
                    """,
                    aid,
                    job_id,
                    oss_preview_url,
                    oss_render_model_url,
                )
    asset_id = aid

    params = _normalize_single_file_studio_history_params(
        mode,
        params,
        str(db_model_url or oss_model_url or ""),
    )

    # 异步任务完成路径此前只写 asset / studio_jobs，未插入 studio_history，导致左侧「历史」在任务结束后消失
    await _insert_studio_history(
        db,
        str(uid),
        mode_for_history,
        history_prompt,
        params,
        history_preview_url,
        asset_id,
    )

    await _ensure_studio_history_model_routes(
        db,
        asset_id=asset_id,
        user_id=str(uid),
        selected_model_url=db_model_url,
        selected_model_format=db_model_format,
        render_model_url=oss_render_model_url,
        render_model_format=render_model_format,
        gcode_source_model_url=oss_gcode_source_url,
        gcode_source_model_format=gcode_source_format,
    )
    return asset_id


async def _studio_jobs_sync_loop(app: FastAPI) -> None:
    """后台周期拉取未完成的 3D 任务，完成则写资产与历史，避免用户离开页面后结果丢失。"""
    while True:
        try:
            await asyncio.sleep(15)
        except asyncio.CancelledError:
            break
        if not getattr(app.state, "db_connected", False) or not getattr(app.state, "db", None):
            continue
        db = app.state.db
        try:
            await _repair_inconsistent_studio_jobs(db)
            await _repair_image23d_placeholder_prompts(db)
            await _cleanup_expired_unsuccessful_studio_jobs(db)
            rows = await db.fetch(
                """
                SELECT job_id, user_id, mode, prompt, preview_url, render_model_url, base_model, with_texture, generation_params, param_notes, credits_used, charged_at, status, terminal_candidate_status, terminal_candidate_count
                FROM studio_jobs
                WHERE asset_id IS NULL
                  AND status NOT IN ('COMPLETED', 'FAILED', 'CANCELLED')
                ORDER BY created_at ASC
                LIMIT 30
                """
            )
        except Exception as e:
            logger.warning("studio_jobs sync fetch: %s", e)
            continue
        for row in rows:
            try:
                status_result = await Hunyuan3DService._query_job_status(row["job_id"])
                generation_params = _parse_json_object(row["generation_params"])
                preferred_format = generation_params.get("ResultFormat") if isinstance(generation_params, dict) else None
                render_parsed = Hunyuan3DService.parse_query_result(status_result)
                parsed = _parse_hunyuan_result_with_preferred_format(
                    status_result,
                    preferred_format=preferred_format,
                )
                normalized_remote_status = _normalize_studio_status_name(parsed.get("status"))
                asset_id = None
                if normalized_remote_status == "COMPLETED" and parsed.get("model_url"):
                    job_meta = {
                        "prompt": row["prompt"],
                        "base_model": row["base_model"] or "hunyuan-3d",
                        "mode": row["mode"],
                        "with_texture": row["with_texture"] if row["with_texture"] is not None else True,
                        "generation_params": generation_params,
                        "param_notes": row["param_notes"],
                        "credits_used": int(row["credits_used"] or 0),
                        "charged_at": row["charged_at"].isoformat() if row["charged_at"] else None,
                    }
                    if str(row.get("mode") or "") == "image23d" and row.get("preview_url"):
                        job_meta["source_image_url"] = row["preview_url"]
                    asset_id = await _complete_studio_job_if_done(
                        db,
                        row["job_id"],
                        job_meta,
                        parsed.get("preview_url"),
                        parsed["model_url"],
                        render_parsed.get("model_url") if _is_history_renderable_model_url(render_parsed.get("model_url")) else None,
                        row["user_id"],
                        status_result,
                    )

                if asset_id:
                    stage_resolution = {
                        "stage": _build_studio_status("COMPLETED"),
                        "finalized": True,
                        "clear_candidate": True,
                        "candidate_status": None,
                        "candidate_count": 0,
                    }
                elif normalized_remote_status == "COMPLETED":
                    stage_resolution = {
                        "stage": _build_studio_finalizing_stage(row["status"]),
                        "finalized": False,
                        "clear_candidate": True,
                        "candidate_status": None,
                        "candidate_count": 0,
                    }
                else:
                    stage_resolution = _resolve_studio_polled_stage(
                        current_status=row["status"],
                        remote_status=parsed.get("status") or "",
                        candidate_status=row["terminal_candidate_status"],
                        candidate_count=row["terminal_candidate_count"],
                    )

                stage = stage_resolution["stage"]
                await _persist_studio_job_state(
                    db,
                    row["job_id"],
                    status=stage["status"],
                    last_message=stage["message"],
                    asset_id=asset_id,
                    render_model_url=render_parsed.get("model_url") if _is_history_renderable_model_url(render_parsed.get("model_url")) else None,
                    finished=bool(asset_id) and stage["status"] == "COMPLETED",
                    terminal_candidate_status=stage_resolution["candidate_status"],
                    terminal_candidate_count=stage_resolution["candidate_count"],
                    terminal_candidate_seen_at=None if stage_resolution["clear_candidate"] else datetime.now(timezone.utc),
                    clear_terminal_candidate=stage_resolution["clear_candidate"],
                )
                if (stage["status"] not in ["COMPLETED"] or not parsed.get("model_url")) and not asset_id:
                    if stage_resolution["finalized"] and stage["status"] in ["FAILED", "CANCELLED"]:
                        await _persist_studio_job_state(
                            db,
                            row["job_id"],
                            status=stage["status"],
                            last_message=stage["message"],
                            finished=True,
                            clear_notified=True,
                            clear_terminal_candidate=True,
                        )
                    continue
                # asset_id 已在上方 COMPLETED 分支里写入，无需再次重复完成逻辑
            except Exception as e:
                if isinstance(e, StudioDeferredChargeError):
                    await _persist_studio_job_state(
                        db,
                        row["job_id"],
                        status="FAILED",
                        last_message=str(e),
                        finished=True,
                        clear_notified=True,
                        clear_terminal_candidate=True,
                    )
                    logger.info("studio_jobs sync job %s deferred charge: %s", row["job_id"], e)
                else:
                    await _persist_studio_job_state(
                        db,
                        row["job_id"],
                        status=_derive_studio_retry_status(row["status"]),
                        last_message="状态同步重试中...",
                        clear_terminal_candidate=True,
                    )
                    logger.warning("studio_jobs sync job %s: %s", row["job_id"], e)


def _is_safe_relative_path(path: str) -> bool:
    p = PurePosixPath(path)
    return (not p.is_absolute()) and (".." not in p.parts)


def _sanitize_local_model_filename(filename: str) -> str:
    """本地3D上传文件名安全化，保留常见字符，防止路径注入。"""
    base = PurePosixPath(filename or "").name.strip()
    if not base:
        base = "model.bin"
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return safe[:128] or "model.bin"


_HY3D_ALLOWED_MODEL = {"3.0", "3.1"}
_HY3D_ALLOWED_GENERATE_TYPE = {
    "normal": "Normal",
    "lowpoly": "LowPoly",
    "geometry": "Geometry",
    "sketch": "Sketch",
}
_HY3D_ALLOWED_POLYGON_TYPE = {"triangle", "quadrilateral"}
_HY3D_ALLOWED_RESULT_FORMAT = {"GLB", "STL"}
_HY3D_BASE_CREDITS_BY_GENERATE_TYPE: Dict[str, int] = {
    "Normal": 40,
    "LowPoly": 50,
    "Geometry": 30,
    "Sketch": 50,
}
_HY3D_EXTRA_CREDITS: Dict[str, int] = {
    "MultiViewImages": 20,
    "EnablePBR": 20,
    "FaceCount": 20,
    "ResultFormat": 10,
}
_T2I_BASE_CREDITS = 20

_T2I_ALLOWED_RATIO = {"1:1", "3:4", "4:3", "16:9", "9:16"}
_T2I_ALLOWED_RESOLUTION_LEVEL = {"720p", "1k", "2k"}
_T2I_SHORT_EDGE_BY_LEVEL: Dict[str, int] = {
    "720p": 720,
    "1k": 1024,
    "2k": 2048,
}
_T2I_ALLOWED_QUALITY = {"standard", "hd"}
_T2I_STYLE_PROMPT_HINT: Dict[str, str] = {
    "auto": "",
    "cinematic": "cinematic composition, dramatic lighting, film still aesthetics, rich atmosphere",
    "photoreal": "photorealistic, ultra detailed textures, realistic light and shadow, natural color grading",
    "anime": "anime style, cel shading, clean line art, vibrant colors, stylized illustration",
    "illustration": "digital illustration, concept art style, painterly details, expressive brushwork",
    "watercolor": "watercolor painting style, soft brush strokes, paper texture, gentle tones",
    "pixel": "pixel art style, retro 8-bit game aesthetics, blocky crisp pixels",
}


def _calculate_hunyuan3d_credits(generation_params: Optional[Dict[str, Any]]) -> Tuple[int, List[str]]:
    """
    根据混元生3D参数计算积分：
    - 任务类型基价：Normal40 / LowPoly50 / Geometry30 / Sketch50
    - 附加参数加价：MultiViewImages +20 / EnablePBR +20 / FaceCount +20 / ResultFormat +10
    """
    params = generation_params or {}
    generate_type = str(params.get("GenerateType") or "Normal")
    base = _HY3D_BASE_CREDITS_BY_GENERATE_TYPE.get(generate_type, 40)
    total = base
    notes = [f"{generate_type} 基础积分 {base}"]

    multi_view_images = params.get("MultiViewImages")
    if isinstance(multi_view_images, list) and len(multi_view_images) > 0:
        extra = _HY3D_EXTRA_CREDITS["MultiViewImages"]
        total += extra
        notes.append(f"MultiViewImages +{extra}")

    if bool(params.get("EnablePBR")):
        extra = _HY3D_EXTRA_CREDITS["EnablePBR"]
        total += extra
        notes.append(f"EnablePBR +{extra}")

    if "FaceCount" in params and params.get("FaceCount") is not None:
        extra = _HY3D_EXTRA_CREDITS["FaceCount"]
        total += extra
        notes.append(f"FaceCount +{extra}")

    if params.get("ResultFormat"):
        extra = _HY3D_EXTRA_CREDITS["ResultFormat"]
        total += extra
        notes.append(f"ResultFormat +{extra}")

    notes.append(f"总积分 {total}")
    return total, notes


def _parse_image_size(size: str) -> Tuple[int, int]:
    m = re.match(r"^\s*(\d{2,5})x(\d{2,5})\s*$", size or "", flags=re.IGNORECASE)
    if not m:
        raise HTTPException(status_code=400, detail="image_size 格式不合法，应为 WxH（例如 1024x1024）")
    w = int(m.group(1))
    h = int(m.group(2))
    if w < 256 or h < 256 or w > 4096 or h > 4096:
        raise HTTPException(status_code=400, detail="image_size 超出范围（256~4096）")
    return w, h


def _ratio_from_size(width: int, height: int) -> str:
    if width == height:
        return "1:1"
    # 仅支持固定比例，按最接近匹配
    target = width / height
    candidates = {
        "1:1": 1.0,
        "3:4": 3 / 4,
        "4:3": 4 / 3,
        "16:9": 16 / 9,
        "9:16": 9 / 16,
    }
    best = min(candidates.items(), key=lambda item: abs(item[1] - target))
    return best[0]


def _calc_size_by_ratio_and_level(ratio: str, level: str) -> str:
    """
    根据“清晰度档位 + 画幅比例”计算输出分辨率。
    规则：短边由档位决定（720/1024/2048），按比例推导长边；若超 2048 自动等比压缩。
    """
    short_edge = _T2I_SHORT_EDGE_BY_LEVEL[level]
    a, b = [int(v) for v in ratio.split(":")]

    if a == b:
        width = short_edge
        height = short_edge
    elif a > b:
        height = short_edge
        width = int(round(height * a / b))
    else:
        width = short_edge
        height = int(round(width * b / a))

    max_edge = max(width, height)
    if max_edge > 2048:
        scale = 2048 / max_edge
        width = int(round(width * scale))
        height = int(round(height * scale))

    # 对齐到偶数，避免部分上游模型因奇数尺寸报错
    width = max(256, (width // 2) * 2)
    height = max(256, (height // 2) * 2)
    return f"{width}x{height}"


def _normalize_text2image_spec(generate_data: StudioGenerate) -> Dict[str, Any]:
    """
    文生图规格归一化与合法性校验。
    输入优先级：
      1) resolution_level + aspect_ratio（新逻辑）
      2) image_size（兼容旧参数）
    返回:
      {
        "aspect_ratio": "1:1",
        "image_size": "1024x1024",
        "resolution_level": "1k",
        "note": "...",  # 可选
      }
    """
    ratio = (generate_data.aspect_ratio or "1:1").strip()
    if ratio not in _T2I_ALLOWED_RATIO:
        allowed = ", ".join(sorted(_T2I_ALLOWED_RATIO))
        raise HTTPException(status_code=400, detail=f"aspect_ratio 不合法，仅支持: {allowed}")

    level = (generate_data.resolution_level or "1k").strip().lower()
    if level not in _T2I_ALLOWED_RESOLUTION_LEVEL:
        allowed = ", ".join(sorted(_T2I_ALLOWED_RESOLUTION_LEVEL))
        raise HTTPException(status_code=400, detail=f"resolution_level 不合法，仅支持: {allowed}")

    # 优先新逻辑：由“清晰度档位 + 画幅比例”计算
    calculated_size = _calc_size_by_ratio_and_level(ratio, level)
    note: Optional[str] = None

    # 兼容：若旧端显式传 image_size，则优先用该尺寸，但回填比例/档位提示
    size = (generate_data.image_size or "").strip().lower()
    if size:
        width, height = _parse_image_size(size)
        inferred_ratio = _ratio_from_size(width, height)
        if inferred_ratio != ratio:
            ratio = inferred_ratio
            calculated_size = _calc_size_by_ratio_and_level(ratio, level)
            note = f"检测到 image_size 与所选比例不一致，已按 image_size 归一为比例 {ratio}"
        else:
            calculated_size = f"{width}x{height}"
            note = "已兼容使用自定义 image_size，建议改用“清晰度档位 + 画幅比例”"

    return {
        "aspect_ratio": ratio,
        "image_size": calculated_size,
        "resolution_level": level,
        "note": note,
    }


def _normalize_text2image_quality(generate_data: StudioGenerate) -> str:
    """文生图清晰度归一化。"""
    # 兼容旧参数 quality。若不传，则按分辨率档位自动推断。
    quality = (generate_data.quality or "").strip().lower()
    if not quality:
        level = (generate_data.resolution_level or "1k").strip().lower()
        quality = "hd" if level == "2k" else "standard"
    if quality not in _T2I_ALLOWED_QUALITY:
        allowed = ", ".join(sorted(_T2I_ALLOWED_QUALITY))
        raise HTTPException(status_code=400, detail=f"quality 不合法，仅支持: {allowed}")
    return quality


def _build_text2image_styled_prompt(prompt: str, style: Optional[str]) -> Tuple[str, str, Optional[str]]:
    """
    文生图风格提示词工程（上游无显式风格参数时，拼接 style guidance）。
    返回: (effective_prompt, style_code, note)
    """
    style_code = (style or "auto").strip().lower()
    if style_code not in _T2I_STYLE_PROMPT_HINT:
        allowed = ", ".join(_T2I_STYLE_PROMPT_HINT.keys())
        raise HTTPException(status_code=400, detail=f"style 不合法，仅支持: {allowed}")

    style_hint = _T2I_STYLE_PROMPT_HINT.get(style_code, "")
    if not style_hint:
        return prompt, "auto", None

    effective_prompt = f"{prompt}\n\nStyle guidance: {style_hint}"
    note = "当前模型未提供独立风格开关，已通过提示词工程注入风格约束"
    return effective_prompt, style_code, note


def _sanitize_hunyuan_3d_params(
    *,
    with_texture: bool,
    model: Optional[str],
    generate_type: Optional[str],
    face_count: Optional[int],
    enable_pbr: Optional[bool],
    polygon_type: Optional[str],
    result_format: Optional[str],
    multi_view_images: Optional[List[str]] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    混元生3D参数白名单校验 + 兜底。
    官方参数：Model / GenerateType / FaceCount / EnablePBR / PolygonType / ResultFormat / MultiViewImages
    """
    params: Dict[str, Any] = {}
    notes: List[str] = []

    # GenerateType：如果前端不传，按白模/彩模默认补齐
    generate_type_raw = (generate_type or "").strip()
    if generate_type_raw:
        normalized_generate_type = _HY3D_ALLOWED_GENERATE_TYPE.get(generate_type_raw.lower())
        if not normalized_generate_type:
            allowed = "Normal, LowPoly, Geometry, Sketch"
            raise HTTPException(status_code=400, detail=f"generate_type 不合法，仅支持: {allowed}")
    else:
        normalized_generate_type = "Normal" if with_texture else "Geometry"
    params["GenerateType"] = normalized_generate_type

    # Model：3.0 / 3.1
    normalized_model = (model or "").strip()
    if normalized_model:
        if normalized_model not in _HY3D_ALLOWED_MODEL:
            raise HTTPException(status_code=400, detail="model 不合法，仅支持: 3.0, 3.1")
        params["Model"] = normalized_model

    # 兜底：3.1 不支持 LowPoly/Sketch（官方限制）
    if params.get("Model") == "3.1" and params["GenerateType"] in {"LowPoly", "Sketch"}:
        params["Model"] = "3.0"
        notes.append("Model=3.1 不支持 LowPoly/Sketch，已自动降级为 3.0")

    # FaceCount：按 GenerateType 限制范围
    if face_count is not None:
        low = 3000 if params["GenerateType"] == "LowPoly" else 10000
        high = 1500000
        clamped = max(low, min(high, int(face_count)))
        if clamped != int(face_count):
            notes.append(f"face_count 超出范围，已自动调整为 {clamped}")
        params["FaceCount"] = clamped

    # EnablePBR
    if enable_pbr is not None:
        normalized_enable_pbr = bool(enable_pbr)
        if params["GenerateType"] == "Geometry" and normalized_enable_pbr:
            normalized_enable_pbr = False
            notes.append("Geometry 模式不建议开启PBR，已自动关闭")
        params["EnablePBR"] = normalized_enable_pbr

    # PolygonType：仅 LowPoly 下生效
    polygon_type_raw = (polygon_type or "").strip().lower()
    if polygon_type_raw:
        if polygon_type_raw not in _HY3D_ALLOWED_POLYGON_TYPE:
            raise HTTPException(status_code=400, detail="polygon_type 不合法，仅支持: triangle, quadrilateral")
        if params["GenerateType"] == "LowPoly":
            params["PolygonType"] = polygon_type_raw
        else:
            notes.append("polygon_type 仅在 LowPoly 模式生效，已忽略")

    # ResultFormat：GLB / STL。为保证历史参数复现稳定，GLB 也显式落库。
    result_format_raw = (result_format or "").strip().upper() or "GLB"
    if result_format_raw:
        if result_format_raw not in _HY3D_ALLOWED_RESULT_FORMAT:
            allowed = ", ".join(sorted(_HY3D_ALLOWED_RESULT_FORMAT))
            raise HTTPException(status_code=400, detail=f"result_format 不合法，仅支持: {allowed}")
        params["ResultFormat"] = result_format_raw

    # MultiViewImages：可选多视图输入（非空字符串列表）
    if multi_view_images is not None:
        cleaned_multi_view_images = [
            str(item).strip()
            for item in multi_view_images
            if isinstance(item, str) and str(item).strip()
        ]
        if not cleaned_multi_view_images:
            notes.append("multi_view_images 为空，已忽略")
        else:
            params["MultiViewImages"] = cleaned_multi_view_images

    return params, notes


def _sanitize_hunyuan_image3d_params(
    generate_data: StudioImageTo3D,
    with_texture: bool
) -> Tuple[Dict[str, Any], List[str]]:
    return _sanitize_hunyuan_3d_params(
        with_texture=with_texture,
        model=generate_data.model,
        generate_type=generate_data.generate_type,
        face_count=generate_data.face_count,
        enable_pbr=generate_data.enable_pbr,
        polygon_type=generate_data.polygon_type,
        result_format=generate_data.result_format,
        multi_view_images=generate_data.multi_view_images,
    )


def _sanitize_hunyuan_text3d_params(
    generate_data: StudioGenerate,
    with_texture: bool
) -> Tuple[Dict[str, Any], List[str]]:
    return _sanitize_hunyuan_3d_params(
        with_texture=with_texture,
        model=generate_data.model,
        generate_type=generate_data.generate_type,
        face_count=generate_data.face_count,
        enable_pbr=generate_data.enable_pbr,
        polygon_type=generate_data.polygon_type,
        result_format=generate_data.result_format,
        multi_view_images=generate_data.multi_view_images,
    )

@app.post("/api/studio/translate-prompt")
async def translate_studio_prompt(
    payload: StudioPromptTranslateRequest,
    current_user: dict = Depends(get_current_user)
):
    """提示词中英翻译（中 -> 英 / 英 -> 中）"""
    _ = current_user  # 显式依赖登录态，防止被匿名滥用
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="翻译内容不能为空")
    if len(text) > 5000:
        raise HTTPException(status_code=400, detail="翻译内容过长，请控制在5000字符以内")

    source_lang = (payload.source_lang or "auto").lower()
    target_lang = (payload.target_lang or "en").lower()
    if source_lang not in {"auto", "zh", "en"}:
        raise HTTPException(status_code=400, detail="source_lang 仅支持 auto/zh/en")
    if target_lang not in {"zh", "en"}:
        raise HTTPException(status_code=400, detail="target_lang 仅支持 zh/en")
    if source_lang in {"zh", "en"} and source_lang == target_lang:
        return {
            "translated_text": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "note": "源语言与目标语言一致，未执行翻译",
        }

    try:
        result = await AIService.translate_text(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        translated_text = (result or {}).get("translated_text", "").strip()
        if not translated_text:
            raise Exception("翻译服务未返回内容")
        return {
            "translated_text": translated_text,
            "source_lang": source_lang,
            "target_lang": target_lang,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"翻译失败: {str(e)}")


@app.post("/api/studio/optimize-prompt")
async def optimize_studio_prompt(
    payload: StudioPromptOptimizeRequest,
    current_user: dict = Depends(get_current_user)
):
    """使用 LLM 优化造梦提示词，保持原语言输出。"""
    _ = current_user
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="提示词不能为空")
    if len(text) > 5000:
        raise HTTPException(status_code=400, detail="提示词过长，请控制在5000字符以内")

    studio_mode = (payload.mode or "text2image").strip().lower()
    if studio_mode not in {"text2image", "text23d"}:
        raise HTTPException(status_code=400, detail="mode 仅支持 text2image/text23d")

    source_lang = (payload.source_lang or "auto").lower()
    if source_lang not in {"auto", "zh", "en"}:
        raise HTTPException(status_code=400, detail="source_lang 仅支持 auto/zh/en")

    try:
        result = await AIService.optimize_prompt(
            text=text,
            mode=studio_mode,
            source_lang=source_lang,
        )
        optimized_text = (result or {}).get("optimized_text", "").strip()
        if not optimized_text:
            raise Exception("提示词优化服务未返回内容")
        return {
            "optimized_text": optimized_text,
            "mode": studio_mode,
            "source_lang": source_lang,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提示词优化失败: {str(e)}")

@app.post("/api/studio/submit-text-3d")
async def submit_text_to_3d(
    generate_data: StudioGenerate,
    current_user: dict = Depends(get_current_user)
):
    """提交文生3D任务（异步，返回 job_id）"""
    if not hasattr(app.state, "db_connected") or not app.state.db_connected:
        raise HTTPException(status_code=503, detail="数据库未连接")

    is_valid, reject_reason = ContentFilter.filter_content(generate_data.prompt)
    if not is_valid:
        raise HTTPException(status_code=400, detail=reject_reason)

    try:
        with_texture = generate_data.with_texture if generate_data.with_texture is not None else True
        generation_params, param_notes = _sanitize_hunyuan_text3d_params(generate_data, with_texture)
        credits_needed, credit_notes = _calculate_hunyuan3d_credits(generation_params)
        if total_points(current_user) < credits_needed:
            raise HTTPException(status_code=400, detail=f"积分不足，需要至少{credits_needed}积分")
        job_id = await Hunyuan3DService.submit_text_to_3d(
            prompt=generate_data.prompt,
            with_texture=with_texture,
            generation_params=generation_params,
        )

        base_model = generate_data.lora or generate_data.model_config_id or "hunyuan-3d"
        _register_studio_job(job_id, {
            "user_id": str(current_user['id']),
            "mode": "text23d",
            "prompt": generate_data.prompt,
            "preview_url": None,
            "base_model": base_model,
            "with_texture": with_texture,
            "generation_params": generation_params,
            "param_notes": param_notes,
            "credits_used": credits_needed,
        })
        await app.state.db.execute(
            """
            INSERT INTO studio_jobs (
                job_id, user_id, mode, status, last_message, prompt, preview_url, base_model,
                with_texture, generation_params, param_notes, credits_used
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ON CONFLICT (job_id) DO NOTHING
            """,
            job_id,
            current_user['id'],
            "text23d",
            "SUBMITTED",
            "任务已提交，等待排队...",
            generate_data.prompt,
            None,
            base_model,
            with_texture,
            json.dumps(_parse_json_object(generation_params)),
            json.dumps(_parse_json_list(param_notes)),
            credits_needed,
        )

        return {
            "job_id": job_id,
            "status": "submitted",
            "mode": "text23d",
            "texture_mode": "color" if with_texture else "white",
            "generation_params": generation_params,
            "param_notes": param_notes,
            "credit_notes": credit_notes,
            "status_endpoint": f"/api/studio/job/{job_id}",
            "credits_used": credits_needed
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交失败: {str(e)}")

@app.post("/api/studio/submit-image-3d")
async def submit_image_to_3d(
    generate_data: StudioImageTo3D,
    current_user: dict = Depends(get_current_user)
):
    """提交图生3D任务（异步，返回 job_id）"""
    if not hasattr(app.state, "db_connected") or not app.state.db_connected:
        raise HTTPException(status_code=503, detail="数据库未连接")

    try:
        with_texture = generate_data.with_texture if generate_data.with_texture is not None else True
        generation_params, param_notes = _sanitize_hunyuan_image3d_params(generate_data, with_texture)
        credits_needed, credit_notes = _calculate_hunyuan3d_credits(generation_params)
        if total_points(current_user) < credits_needed:
            raise HTTPException(status_code=400, detail=f"积分不足，需要至少{credits_needed}积分")
        job_id = await Hunyuan3DService.submit_image_to_3d(
            image_base64=generate_data.image_base64,
            with_texture=with_texture,
            generation_params=generation_params
        )
        input_preview_url = await _persist_image_base64_preview(
            generate_data.image_base64,
            str(current_user["id"]),
            job_id,
        )

        base_model = generate_data.lora or generate_data.model_config_id or "hunyuan-3d"
        _register_studio_job(job_id, {
            "user_id": str(current_user['id']),
            "mode": "image23d",
            "prompt": _normalize_studio_prompt("image23d", generate_data.prompt),
            "preview_url": input_preview_url,
            "base_model": base_model,
            "with_texture": with_texture,
            "generation_params": generation_params,
            "param_notes": param_notes,
            "credits_used": credits_needed,
        })
        await app.state.db.execute(
            """
            INSERT INTO studio_jobs (
                job_id, user_id, mode, status, last_message, prompt, preview_url, base_model,
                with_texture, generation_params, param_notes, credits_used
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ON CONFLICT (job_id) DO NOTHING
            """,
            job_id,
            current_user['id'],
            "image23d",
            "SUBMITTED",
            "任务已提交，等待排队...",
            _normalize_studio_prompt("image23d", generate_data.prompt),
            input_preview_url,
            base_model,
            with_texture,
            json.dumps(_parse_json_object(generation_params)),
            json.dumps(_parse_json_list(param_notes)),
            credits_needed,
        )

        return {
            "job_id": job_id,
            "status": "submitted",
            "mode": "image23d",
            "texture_mode": "color" if with_texture else "white",
            "generation_params": generation_params,
            "param_notes": param_notes,
            "credit_notes": credit_notes,
            "display_prompt": _format_hunyuan_image23d_display_prompt(with_texture, generation_params),
            "status_endpoint": f"/api/studio/job/{job_id}",
            "credits_used": credits_needed
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交失败: {str(e)}")

@app.get("/api/studio/job/{job_id}")
async def query_studio_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """查询 3D 任务状态（用于前端轮询）"""
    if not hasattr(app.state, "db_connected") or not app.state.db_connected:
        raise HTTPException(status_code=503, detail="数据库未连接")
    job = studio_jobs.get(job_id)
    if not job:
        row = await app.state.db.fetchrow(
            "SELECT user_id, mode, status, last_message, prompt, preview_url, render_model_url, base_model, with_texture, generation_params, param_notes, credits_used, charged_at, asset_id, created_at, terminal_candidate_status, terminal_candidate_count, terminal_candidate_seen_at FROM studio_jobs WHERE job_id = $1",
            job_id,
        )
        if not row or str(row["user_id"]) != str(current_user.get("id")):
            raise HTTPException(status_code=404, detail="任务不存在或已过期")
        # 安全处理 generation_params，确保始终是字典类型
        generation_params = row["generation_params"]
        if isinstance(generation_params, str):
            try:
                import json
                generation_params = json.loads(generation_params)
            except (json.JSONDecodeError, TypeError):
                generation_params = {}
        elif not isinstance(generation_params, dict):
            generation_params = {}
            
        job = {
            "user_id": str(row["user_id"]),
            "mode": row["mode"],
            "status": _normalize_studio_status_name(row["status"] or "SUBMITTED"),
            "last_message": row["last_message"],
            "prompt": _normalize_studio_prompt(row["mode"], row["prompt"]),
            "preview_url": row["preview_url"],
            "render_model_url": row["render_model_url"],
            "base_model": row["base_model"] or "hunyuan-3d",
            "with_texture": row["with_texture"] if row["with_texture"] is not None else True,
            "generation_params": _parse_json_object(row["generation_params"]),
            "param_notes": _parse_json_list(row["param_notes"]),
            "credits_used": int(row["credits_used"] or 0),
            "charged_at": row["charged_at"].isoformat() if row["charged_at"] else None,
            "asset_id": str(row["asset_id"]) if row["asset_id"] else None,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "terminal_candidate_status": row["terminal_candidate_status"],
            "terminal_candidate_count": int(row["terminal_candidate_count"] or 0),
            "terminal_candidate_seen_at": row["terminal_candidate_seen_at"].isoformat() if row["terminal_candidate_seen_at"] else None,
        }
        studio_jobs[job_id] = job
    else:
        job["status"] = _normalize_studio_status_name(job.get("status"))
        job["generation_params"] = _parse_json_object(job.get("generation_params"))
        job["param_notes"] = _parse_json_list(job.get("param_notes"))
        job["prompt"] = _normalize_studio_prompt(job.get("mode"), job.get("prompt"))
        row = await app.state.db.fetchrow(
            "SELECT user_id, mode, status, last_message, prompt, preview_url, render_model_url, base_model, with_texture, generation_params, param_notes, credits_used, charged_at, asset_id, created_at, terminal_candidate_status, terminal_candidate_count, terminal_candidate_seen_at FROM studio_jobs WHERE job_id = $1",
            job_id,
        )
        if row:
            job.update({
                "user_id": str(row["user_id"]),
                "mode": row["mode"],
                "status": _normalize_studio_status_name(row["status"] or "SUBMITTED"),
                "last_message": row["last_message"],
                "prompt": _normalize_studio_prompt(row["mode"], row["prompt"]),
                "preview_url": row["preview_url"],
                "render_model_url": row["render_model_url"],
                "base_model": row["base_model"] or "hunyuan-3d",
                "with_texture": row["with_texture"] if row["with_texture"] is not None else True,
                "generation_params": _parse_json_object(row["generation_params"]),
                "param_notes": _parse_json_list(row["param_notes"]),
                "credits_used": int(row["credits_used"] or 0),
                "charged_at": row["charged_at"].isoformat() if row["charged_at"] else None,
                "asset_id": str(row["asset_id"]) if row["asset_id"] else None,
                "created_at": row["created_at"].isoformat() if row["created_at"] else job.get("created_at"),
                "terminal_candidate_status": row["terminal_candidate_status"],
                "terminal_candidate_count": int(row["terminal_candidate_count"] or 0),
                "terminal_candidate_seen_at": row["terminal_candidate_seen_at"].isoformat() if row["terminal_candidate_seen_at"] else None,
            })
            studio_jobs[job_id] = job
    if job.get("user_id") != str(current_user.get("id")):
        raise HTTPException(status_code=403, detail="无权限访问该任务")

    from utils.oss_util import oss_manager

    async def _build_completed_response() -> Dict[str, Any]:
        history_params: Dict[str, Any] = {}
        requested_result_format = (
            _normalize_requested_result_format(
                ((job.get("generation_params") or {}).get("ResultFormat") if isinstance(job.get("generation_params"), dict) else None)
            )
        )
        history_row = await app.state.db.fetchrow(
            "SELECT params FROM studio_history WHERE asset_id = $1 ORDER BY created_at DESC LIMIT 1",
            job["asset_id"],
        )
        if history_row and history_row.get("params") is not None:
            history_params = _normalize_studio_params_blob(history_row["params"])
        asset_row = await app.state.db.fetchrow(
            "SELECT image_url, model_url FROM assets WHERE id = $1",
            job["asset_id"],
        )
        preview_url = asset_row["image_url"] if asset_row and asset_row.get("image_url") else job.get("preview_url")
        asset_model_url = asset_row["model_url"] if asset_row and asset_row.get("model_url") else None
        repaired_routes = await _repair_missing_printable_model_routes(
            app.state.db,
            asset_id=job.get("asset_id"),
            user_id=str(current_user.get("id")),
            job_uuid=job_id,
            requested_result_format=requested_result_format,
            history_params=history_params,
            asset_model_url=asset_model_url,
            render_model_url=history_params.get("render_model_url") or job.get("render_model_url"),
        )
        if repaired_routes.get("render_model_url") and not history_params.get("render_model_url"):
            history_params["render_model_url"] = repaired_routes["render_model_url"]
        if repaired_routes.get("render_model_format") and not history_params.get("render_model_format"):
            history_params["render_model_format"] = repaired_routes["render_model_format"]
        if repaired_routes.get("selected_model_url"):
            history_params["download_model_url"] = repaired_routes["selected_model_url"]
            history_params["selected_model_url"] = repaired_routes["selected_model_url"]
        if repaired_routes.get("selected_model_format"):
            history_params["download_model_format"] = repaired_routes["selected_model_format"]
            history_params["selected_model_format"] = repaired_routes["selected_model_format"]
        if repaired_routes.get("gcode_source_model_url"):
            history_params["gcode_source_model_url"] = repaired_routes["gcode_source_model_url"]
        if repaired_routes.get("gcode_source_model_format"):
            history_params["gcode_source_model_format"] = repaired_routes["gcode_source_model_format"]
        if repaired_routes.get("selected_model_url"):
            asset_model_url = repaired_routes["selected_model_url"]
        selected_model_url = history_params.get("selected_model_url")
        if isinstance(selected_model_url, str):
            selected_model_url = selected_model_url.strip() or None
        else:
            selected_model_url = None
        selected_model_format = (
            str(history_params.get("selected_model_format") or history_params.get("download_model_format") or "").strip().lower()
            or None
        )
        if not selected_model_format and requested_result_format:
            selected_model_format = requested_result_format
        if selected_model_url and not _matches_requested_result_format(
            selected_model_url,
            selected_model_format or requested_result_format,
            selected_model_format,
        ):
            selected_model_url = None
        download_model_url = selected_model_url or (asset_model_url if not selected_model_format else None)
        model_url = history_params.get("render_model_url") or job.get("render_model_url")
        if not model_url and _is_history_renderable_model_url(download_model_url):
            model_url = download_model_url
        download_model_format = (
            str(history_params.get("download_model_format") or history_params.get("selected_model_format") or "").strip().lower()
            or requested_result_format
            or _resolve_model_format(download_model_url, fallback_format=requested_result_format)
        )
        if not selected_model_format:
            selected_model_format = _resolve_model_format(
                download_model_url,
                fallback_format=requested_result_format,
            )
        render_model_format = (
            str(history_params.get("render_model_format") or "").strip().lower()
            or _resolve_model_format(model_url)
        )
        gcode_source_model_url = history_params.get("gcode_source_model_url")
        gcode_source_model_format = (
            str(history_params.get("gcode_source_model_format") or "").strip().lower() or None
        )
        selected_model_url, selected_model_format = _prefer_printable_selected_output(
            requested_result_format=requested_result_format,
            selected_model_url=selected_model_url,
            selected_model_format=selected_model_format,
            gcode_source_url=gcode_source_model_url,
            gcode_source_format=gcode_source_model_format,
        )
        if selected_model_url:
            download_model_url = selected_model_url
        if selected_model_format:
            download_model_format = selected_model_format
        if preview_url and str(preview_url).startswith("oss://"):
            preview_url = oss_manager.generate_presigned_url(str(preview_url)[len("oss://"):], expires=3600) or preview_url
        if model_url and str(model_url).startswith("oss://"):
            model_url = oss_manager.generate_presigned_url(str(model_url)[len("oss://"):], expires=3600) or model_url
        if download_model_url and str(download_model_url).startswith("oss://"):
            download_model_url = oss_manager.generate_presigned_url(str(download_model_url)[len("oss://"):], expires=3600) or download_model_url
        if gcode_source_model_url and str(gcode_source_model_url).startswith("oss://"):
            gcode_source_model_url = oss_manager.generate_presigned_url(str(gcode_source_model_url)[len("oss://"):], expires=3600) or gcode_source_model_url
        await _persist_studio_job_state(
            app.state.db,
            job_id,
            status="COMPLETED",
            last_message="生成完成",
            asset_id=job.get("asset_id"),
            render_model_url=job.get("render_model_url"),
            finished=True,
        )
        return {
            "job_id": job_id,
            "status": "COMPLETED",
            "progress": 100,
            "message": "生成完成",
            "retryable": False,
            "mode": job.get("mode"),
            "prompt": _studio_job_api_display_prompt(
                job.get("mode"),
                job.get("with_texture"),
                job.get("generation_params"),
                job.get("prompt"),
            ),
            "created_at": job.get("created_at"),
            "model_url": selected_model_url,
            "download_model_url": download_model_url,
            "model_format": selected_model_format,
            "download_model_format": download_model_format,
            "selected_model_url": selected_model_url,
            "selected_model_format": selected_model_format,
            "render_model_url": model_url,
            "render_model_format": render_model_format,
            "gcode_source_model_url": gcode_source_model_url,
            "gcode_source_model_format": gcode_source_model_format,
            "preview_url": preview_url,
            "asset_id": job.get("asset_id"),
            "texture_mode": "color" if job.get("with_texture", True) else "white",
            "generation_params": job.get("generation_params"),
            "param_notes": job.get("param_notes"),
            "credits_used": int(job.get("credits_used") or 0),
        }

    if job.get("asset_id"):
        return await _build_completed_response()

    if job.get("status") == "CANCELLED":
        stage = _build_studio_status("CANCELLED")
        preview_url = job.get("preview_url")
        if preview_url and str(preview_url).startswith("oss://"):
            preview_url = oss_manager.generate_presigned_url(str(preview_url)[len("oss://"):], expires=3600) or preview_url
        return {
            "job_id": job_id,
            "status": stage["status"],
            "progress": stage["progress"],
            "message": stage["message"],
            "retryable": stage["retryable"],
            "mode": job.get("mode"),
            "prompt": _studio_job_api_display_prompt(
                job.get("mode"),
                job.get("with_texture"),
                job.get("generation_params"),
                job.get("prompt"),
            ),
            "model_url": None,
            "download_model_url": None,
            "preview_url": preview_url,
            "asset_id": job.get("asset_id"),
            "texture_mode": "color" if job.get("with_texture", True) else "white",
            "generation_params": job.get("generation_params"),
            "param_notes": job.get("param_notes"),
            "credits_used": int(job.get("credits_used") or 0),
            "note": "任务已被用户取消"
        }

    try:
        status_result = await Hunyuan3DService._query_job_status(job_id)
        preferred_format = (
            ((job or {}).get("generation_params") or {}).get("ResultFormat")
            if job else None
        )
        render_parsed = Hunyuan3DService.parse_query_result(status_result)
        download_parsed = _parse_hunyuan_result_with_preferred_format(
            status_result,
            preferred_format=preferred_format,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

    # 成功时写入资产与历史（只写一次，事务防重）
    normalized_remote_status = _normalize_studio_status_name(download_parsed.get("status"))
    if normalized_remote_status == "COMPLETED" and download_parsed.get("model_url") and job:
        try:
            aid = await _complete_studio_job_if_done(
                app.state.db,
                job_id,
                job,
                download_parsed.get("preview_url"),
                download_parsed["model_url"],
                render_parsed.get("model_url") if _is_history_renderable_model_url(render_parsed.get("model_url")) else None,
                current_user["id"],
                status_result,
            )
        except StudioDeferredChargeError as e:
            raise HTTPException(status_code=400, detail=str(e))
        if aid:
            job["asset_id"] = aid
            job["status"] = "COMPLETED"
            return await _build_completed_response()

    if job and job.get("asset_id"):
        stage_resolution = {
            "stage": _build_studio_status("COMPLETED"),
            "finalized": True,
            "clear_candidate": True,
            "candidate_status": None,
            "candidate_count": 0,
        }
    elif normalized_remote_status == "COMPLETED":
        stage_resolution = {
            "stage": _build_studio_finalizing_stage(job.get("status") if job else None),
            "finalized": False,
            "clear_candidate": True,
            "candidate_status": None,
            "candidate_count": 0,
        }
    else:
        stage_resolution = _resolve_studio_polled_stage(
            current_status=job.get("status") if job else None,
            remote_status=normalized_remote_status,
            candidate_status=job.get("terminal_candidate_status") if job else None,
            candidate_count=job.get("terminal_candidate_count") if job else 0,
        )
    stage = stage_resolution["stage"]
    if job:
        stage = _apply_elapsed_progress(
            stage,
            created_at=job.get("created_at"),
            stage_started_at=job.get("terminal_candidate_seen_at") if stage.get("message") == "结果整理中..." else None,
        )
    is_terminal = stage_resolution["finalized"] and stage["status"] in {"COMPLETED", "FAILED", "CANCELLED"}
    await _persist_studio_job_state(
        app.state.db,
        job_id,
        status=stage["status"],
        last_message=stage["message"],
        asset_id=job.get("asset_id") if job else None,
        render_model_url=render_parsed.get("model_url") if _is_history_renderable_model_url(render_parsed.get("model_url")) else None,
        finished=is_terminal,
        clear_notified=is_terminal,
        terminal_candidate_status=stage_resolution["candidate_status"],
        terminal_candidate_count=stage_resolution["candidate_count"],
        terminal_candidate_seen_at=None if stage_resolution["clear_candidate"] else datetime.now(timezone.utc),
        clear_terminal_candidate=stage_resolution["clear_candidate"],
    )

    out_gcode_source_url, out_gcode_source_format = _derive_gcode_source_payload(
        model_url=download_parsed.get("model_url"),
        fallback_format=preferred_format,
        status_result=status_result,
    )
    out_model, out_render_format = _resolve_render_output_payload(
        status_result=status_result,
        fallback_model_url=render_parsed.get("model_url"),
        fallback_model_format=render_parsed.get("model_format"),
    )
    out_selected_model, out_selected_format = _resolve_selected_output_payload(
        status_result=status_result,
        requested_result_format=preferred_format,
        default_model_url=download_parsed.get("model_url"),
        default_model_format=download_parsed.get("model_format"),
        gcode_source_url=out_gcode_source_url,
        gcode_source_format=out_gcode_source_format,
    )
    out_download_model = out_selected_model
    out_preview = render_parsed["preview_url"] or download_parsed["preview_url"] or job.get("preview_url")

    # 一旦资产已落库，“查看模型”优先使用资产最终地址；渲染地址仍优先保持可在线预览的格式。
    asset_id_for_result = job.get("asset_id") if job else None
    if asset_id_for_result:
        try:
            asset_row = await app.state.db.fetchrow(
                "SELECT image_url, model_url FROM assets WHERE id = $1",
                asset_id_for_result,
            )
            if asset_row:
                out_preview = asset_row.get("image_url") or out_preview
                out_selected_model = asset_row.get("model_url") or out_selected_model
                out_download_model = out_selected_model
        except Exception as e:
            logger.warning("query_studio_job load asset result failed: %s", e)
    
    if out_model and out_model.startswith("oss://"):
        out_model = oss_manager.generate_presigned_url(out_model[len("oss://"):], expires=3600) or out_model

    if out_selected_model and out_selected_model.startswith("oss://"):
        out_selected_model = oss_manager.generate_presigned_url(out_selected_model[len("oss://"):], expires=3600) or out_selected_model
    out_download_model = out_selected_model
        
    if out_preview and out_preview.startswith("oss://"):
        out_preview = oss_manager.generate_presigned_url(out_preview[len("oss://"):], expires=3600) or out_preview

    return {
        "job_id": job_id,
        "status": stage["status"],
        "progress": stage["progress"],
        "message": stage["message"],
        "retryable": stage["retryable"],
        "mode": job.get("mode") if job else None,
        "prompt": _studio_job_api_display_prompt(
            job.get("mode") if job else None,
            job.get("with_texture") if job else None,
            job.get("generation_params") if job else None,
            job.get("prompt") if job else None,
        )
        if job
        else None,
        "created_at": job.get("created_at") if job else None,
        "model_url": out_selected_model,
        "download_model_url": out_download_model,
        "model_format": out_selected_format,
        "download_model_format": out_selected_format,
        "selected_model_url": out_selected_model,
        "selected_model_format": out_selected_format,
        "render_model_url": out_model,
        "render_model_format": out_render_format,
        "gcode_source_model_url": out_gcode_source_url,
        "gcode_source_model_format": out_gcode_source_format,
        "preview_url": out_preview,
        "asset_id": job.get("asset_id") if job else None,
        "texture_mode": "color" if (job.get("with_texture", True) if job else True) else "white",
        "generation_params": (job.get("generation_params") if job else None),
        "param_notes": (job.get("param_notes") if job else None),
        "credits_used": int((job.get("credits_used") if job else 0) or 0),
        "note": (None if job else "任务未在本地登记，仅返回实时状态")
    }

@app.get("/api/studio/model-proxy")
@app.get("/api/studio/model-proxy/{file_name:path}")
@app.get("/api/studio/model-proxy/{token}/{file_name:path}")
async def studio_model_proxy(
    token: Optional[str] = None,
    file_name: Optional[str] = None,
    url: Optional[str] = Query(default=None, description="上游模型资源URL")
):
    """
    模型代理：解决浏览器跨域限制，转发3D资源下载流。
    """
    _cleanup_studio_proxy_roots()

    if url and url.startswith("oss://"):
        from utils.oss_util import oss_manager
        oss_key = url[len("oss://"):]
        presigned_url = oss_manager.generate_presigned_url(oss_key, expires=3600)
        if presigned_url:
            url = presigned_url
        else:
            raise HTTPException(status_code=404, detail="OSS文件访问失败")

    resolved_url = url
    now_ts = datetime.now(timezone.utc).timestamp()

    if url and token:
        parsed_for_root = urlparse(url)
        root_url = url.rsplit("/", 1)[0] + "/"
        studio_proxy_roots[token] = {
            "root_url": root_url,
            "host": parsed_for_root.netloc.lower(),
            "updated_at": now_ts,
        }
    elif (not url) and token:
        session_data = studio_proxy_roots.get(token)
        if not session_data:
            raise HTTPException(status_code=404, detail="代理会话不存在或已过期")
        if not file_name:
            raise HTTPException(status_code=400, detail="缺少资源文件名")
        if not _is_safe_relative_path(file_name):
            raise HTTPException(status_code=400, detail="非法资源路径")
        resolved_url = urljoin(session_data["root_url"], file_name)
        session_data["updated_at"] = now_ts

    if not resolved_url:
        raise HTTPException(status_code=400, detail="缺少资源URL")

    parsed = urlparse(resolved_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="无效的资源URL")

    # 安全兜底：仅放行常见对象存储域名，避免开放代理风险
    # 支持通过配置或环境变量扩展允许的域名后缀（Config.STUDIO_PROXY_ALLOWED_SUFFIXES）
    try:
        allowed_raw = getattr(Config, "STUDIO_PROXY_ALLOWED_SUFFIXES", "tencentcos.cn,cos.ap-,myqcloud.com,aliyuncs.com")
        allowed_suffixes = tuple([s.strip() for s in str(allowed_raw or "").split(",") if s.strip()])
    except Exception:
        allowed_suffixes = ("tencentcos.cn", "cos.ap-", "myqcloud.com", "aliyuncs.com")

    host = parsed.netloc.lower()
    if not any(s in host for s in allowed_suffixes):
        raise HTTPException(status_code=400, detail="资源域名不在允许范围")

    safe_name = file_name or Path(parsed.path).name or "model.bin"
    timeout = aiohttp.ClientTimeout(total=120, connect=15, sock_read=90)

    try:
        session = aiohttp.ClientSession(timeout=timeout)
        upstream = await session.get(resolved_url, allow_redirects=True)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"资源代理请求失败: {str(e)}")

    if upstream.status != 200:
        await upstream.release()
        await session.close()
        raise HTTPException(status_code=404, detail=f"资源不存在或已过期: {upstream.status}")

    media_type = upstream.headers.get("Content-Type", "application/octet-stream")
    headers = {
        "Content-Disposition": f'inline; filename="{safe_name}"',
        "Cache-Control": "private, max-age=300",
    }

    async def iterator():
        try:
            async for chunk in upstream.content.iter_chunked(64 * 1024):
                yield chunk
        finally:
            await upstream.release()
            await session.close()

    return StreamingResponse(iterator(), media_type=media_type, headers=headers)

@app.post("/api/studio/job/{job_id}/cancel")
async def cancel_studio_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """将任务标记为已取消（不保证取消上游已提交任务）。"""
    job = studio_jobs.get(job_id)
    if not job:
        row = await app.state.db.fetchrow(
            "SELECT user_id FROM studio_jobs WHERE job_id = $1",
            job_id,
        )
        if not row:
            return {"job_id": job_id, "status": "not_found", "message": "任务不存在或未登记"}
        if str(row["user_id"]) != str(current_user.get("id")):
            raise HTTPException(status_code=403, detail="无权限取消该任务")
        job = {"user_id": str(row["user_id"])}
        studio_jobs[job_id] = job
    if job.get("user_id") != str(current_user.get("id")):
        raise HTTPException(status_code=403, detail="无权限取消该任务")

    await _persist_studio_job_state(
        app.state.db,
        job_id,
        status="CANCELLED",
        last_message="任务已取消",
        finished=True,
        clear_notified=True,
        clear_terminal_candidate=True,
    )
    job["cancelled_at"] = datetime.now(timezone.utc).isoformat()
    return {"job_id": job_id, "status": "cancelled", "message": "任务已取消"}


@app.post("/api/studio/generate")
async def studio_generate(
    generate_data: StudioGenerate,
    current_user: dict = Depends(get_current_user)
):
    """核心生成接口（支持文生图和文生3D）"""
    # 内容审核
    is_valid, reject_reason = ContentFilter.filter_content(generate_data.prompt)
    if not is_valid:
        raise HTTPException(status_code=400, detail=reject_reason)
    
    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    # 根据 model_config_id 判断是文生图还是文生3D
    # 如果 model_config_id 为 "wan2.6-t2i" 或包含 "t2i"，则调用文生图
    # 否则调用文生3D
    is_text_to_image = (
        generate_data.model_config_id and 
        ("t2i" in generate_data.model_config_id.lower() or "wan2.6" in generate_data.model_config_id.lower())
    )
    
    try:
        if is_text_to_image:
            # 文生图：调用阿里云百炼 wan2.6-t2i
            if total_points(current_user) < _T2I_BASE_CREDITS:
                raise HTTPException(status_code=400, detail=f"积分不足，需要至少{_T2I_BASE_CREDITS}积分")
            spec = _normalize_text2image_spec(generate_data)
            quality = _normalize_text2image_quality(generate_data)
            effective_prompt, style_code, style_note = _build_text2image_styled_prompt(
                generate_data.prompt,
                generate_data.style,
            )
            result = await AIService.generate_image(
                effective_prompt,
                model_config_id=generate_data.model_config_id,
                size=spec["image_size"],
                quality=quality,
                db=app.state.db
            )
            
            # 扣除积分（先扣免费，再扣兑换，最后扣付费）
            ok = await deduct_points(
                app.state.db, 
                str(current_user['id']), 
                result['credits_used'],
                reason="generate_image",
                related_id=task_id
            )
            if not ok:
                raise HTTPException(status_code=400, detail="积分不足")
            
            # 保存到assets表（未发布状态）
            asset_id = await app.state.db.fetchrow(
                """
                INSERT INTO assets (author_id, image_url, model_url, prompt, base_model,
                                  seed, steps, sampler, is_published)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, FALSE)
                RETURNING id
                """,
                current_user['id'], result.get('preview_url', result['image_url']),
                result.get('image_url', ''), generate_data.prompt, generate_data.model_config_id or "wan2.6-t2i",
                None, None, None
            )
            await _insert_studio_history(
                app.state.db,
                str(current_user['id']),
                "text2img",
                generate_data.prompt,
                {
                    "model_config_id": generate_data.model_config_id,
                    "lora": generate_data.lora,
                    "aspect_ratio": spec["aspect_ratio"],
                    "resolution_level": spec["resolution_level"],
                    "image_size": spec["image_size"],
                    "output_size": spec["image_size"],
                    "style": style_code,
                    "quality": result.get("quality_used", quality),
                    "quality_fallback_note": result.get("quality_fallback_note"),
                },
                result.get('preview_url') or result.get('image_url'),
                str(asset_id['id']),
            )
            notes: List[str] = []
            if spec.get("note"):
                notes.append(str(spec["note"]))
            if style_note:
                notes.append(style_note)
            if result.get("quality_fallback_note"):
                notes.append(str(result["quality_fallback_note"]))
            return {
                "task_id": task_id,
                "status": "completed",
                "asset_id": str(asset_id['id']),
                "image_url": result.get('image_url'),
                "preview_url": result.get('preview_url', result.get('image_url')),
                "credits_used": result['credits_used'],
                "output_size": spec["image_size"],
                "aspect_ratio": spec["aspect_ratio"],
                "resolution_level": spec["resolution_level"],
                "style": style_code,
                "quality": result.get("quality_used", quality),
                "spec_note": "；".join(notes) if notes else None
            }
        else:
            # 文生3D：调用腾讯混元生3D
            with_texture = generate_data.with_texture if generate_data.with_texture is not None else True
            generation_params, param_notes = _sanitize_hunyuan_text3d_params(generate_data, with_texture)
            credits_needed, credit_notes = _calculate_hunyuan3d_credits(generation_params)
            if total_points(current_user) < credits_needed:
                raise HTTPException(status_code=400, detail=f"积分不足，需要至少{credits_needed}积分")
            result = await AIService.generate_3d_model(
                prompt=generate_data.prompt,
                lora=generate_data.lora,
                model_config_id=generate_data.model_config_id,
                db=app.state.db,
                with_texture=with_texture,
                generation_params=generation_params,
            )
            
            # 扣除积分（先扣免费，再扣兑换，最后扣付费）
            ok = await deduct_points(
                app.state.db, 
                str(current_user['id']), 
                credits_needed,
                reason="generate_3d",
                related_id=task_id
            )
            if not ok:
                raise HTTPException(status_code=400, detail="积分不足")
            
            # 保存到assets表（未发布状态）
            # base_model 不能为 null，如果 lora 为 None，使用默认值
            base_model = generate_data.lora or generate_data.model_config_id or "hunyuan-3d"
            asset_id = await app.state.db.fetchrow(
                """
                INSERT INTO assets (author_id, image_url, model_url, prompt, base_model,
                                  seed, steps, sampler, is_published)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, FALSE)
                RETURNING id
                """,
                current_user['id'], result.get('preview_url', result['model_url']),
            result['model_url'], generate_data.prompt, base_model,
            result.get('seed'), result.get('steps'), result.get('sampler')
        )
            render_model_url, render_model_format = _resolve_render_output_payload(
                status_result=result.get("raw"),
                fallback_model_url=Hunyuan3DService.parse_query_result(result["raw"]).get("model_url") if result.get("raw") else None,
                fallback_model_format=None,
            )
            requested_result_format = generation_params.get("ResultFormat") if isinstance(generation_params, dict) else None
            should_prepare_printable_source = _should_prepare_printable_source(requested_result_format)
            gcode_source_model_url, gcode_source_model_format = (None, None)
            if should_prepare_printable_source:
                gcode_source_model_url, gcode_source_model_format = _derive_gcode_source_payload(
                    model_url=result.get("model_url"),
                    fallback_format=requested_result_format,
                    status_result=result.get("raw"),
                )
            if should_prepare_printable_source and not gcode_source_model_url:
                gcode_source_model_url, gcode_source_model_format = await _build_gcode_source_payload_from_model_candidates(
                    status_result=result.get("raw"),
                    primary_model_url=result.get("model_url"),
                    render_model_url=render_model_url,
                    requested_result_format=requested_result_format,
                    user_id=str(current_user['id']),
                    job_uuid=str(uuid.uuid4()),
                )
            download_model_format = _resolve_model_format(
                result.get("model_url"),
                fallback_format=requested_result_format,
            )
            selected_model_url, selected_model_format = _resolve_selected_output_payload(
                status_result=result.get("raw"),
                requested_result_format=requested_result_format,
                default_model_url=result.get("model_url"),
                default_model_format=download_model_format,
                gcode_source_url=gcode_source_model_url,
                gcode_source_format=gcode_source_model_format,
            )
            selected_model_url, selected_model_format = _prefer_printable_selected_output(
                requested_result_format=requested_result_format,
                selected_model_url=selected_model_url,
                selected_model_format=selected_model_format,
                gcode_source_url=gcode_source_model_url,
                gcode_source_format=gcode_source_model_format,
            )
            if should_prepare_printable_source and not gcode_source_model_url:
                gcode_source_model_url, gcode_source_model_format = await _build_gcode_source_payload_from_model_url(
                    model_url=result.get("model_url"),
                    requested_result_format=generation_params.get("ResultFormat") if isinstance(generation_params, dict) else None,
                    user_id=str(current_user['id']),
                    job_uuid=str(uuid.uuid4()),
                )
            await _insert_studio_history(
                app.state.db,
                str(current_user['id']),
                "text23d",
                generate_data.prompt,
                {
                    "lora": generate_data.lora,
                    "model_config_id": generate_data.model_config_id,
                    "with_texture": with_texture,
                    "generation_params": generation_params,
                    "param_notes": param_notes,
                    "credit_notes": credit_notes,
                    "credits_used": credits_needed,
                    **(
                        {
                            "render_model_url": render_model_url,
                            "render_model_format": render_model_format,
                        }
                        if render_model_url
                        else {}
                    ),
                    **(
                        {
                            "download_model_url": selected_model_url,
                            "selected_model_url": selected_model_url,
                        }
                        if selected_model_url
                        else {}
                    ),
                    **(
                        {
                            "download_model_format": selected_model_format or download_model_format,
                            "selected_model_format": selected_model_format or download_model_format,
                        }
                        if (selected_model_format or download_model_format)
                        else {}
                    ),
                    **(
                        {
                            "gcode_source_model_url": gcode_source_model_url,
                            "gcode_source_model_format": gcode_source_model_format,
                        }
                        if gcode_source_model_url and gcode_source_model_format
                        else {}
                    ),
                },
                result.get('preview_url'),
                str(asset_id['id']),
            )
            finalized_routes = await _finalize_sync_generated_model_routes(
                app.state.db,
                asset_id=str(asset_id["id"]),
                user_id=str(current_user["id"]),
                requested_result_format=requested_result_format,
                history_params={
                    **{
                        "render_model_url": render_model_url,
                        "render_model_format": render_model_format,
                    },
                    **(
                        {
                            "download_model_url": selected_model_url,
                            "selected_model_url": selected_model_url,
                            "download_model_format": selected_model_format or download_model_format,
                            "selected_model_format": selected_model_format or download_model_format,
                        }
                        if selected_model_url
                        else {}
                    ),
                    **(
                        {
                            "gcode_source_model_url": gcode_source_model_url,
                            "gcode_source_model_format": gcode_source_model_format,
                        }
                        if gcode_source_model_url and gcode_source_model_format
                        else {}
                    ),
                },
                asset_model_url=result.get("model_url"),
                selected_model_url=selected_model_url,
                selected_model_format=selected_model_format or download_model_format,
                render_model_url=render_model_url,
                render_model_format=render_model_format,
                gcode_source_model_url=gcode_source_model_url,
                gcode_source_model_format=gcode_source_model_format,
                job_uuid=task_id,
            )
            response_model_url = finalized_routes.get("selected_model_url") or result["model_url"]
            return {
                "task_id": task_id,
                "status": "completed",
                "asset_id": str(asset_id['id']),
                "model_url": response_model_url,
                "preview_url": result.get('preview_url'),
                "credits_used": credits_needed,
                "texture_mode": "color" if with_texture else "white",
                "generation_params": generation_params,
                "param_notes": param_notes,
                "credit_notes": credit_notes,
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")

@app.post("/api/studio/image-to-3d")
async def studio_image_to_3d(
    generate_data: StudioImageTo3D,
    current_user: dict = Depends(get_current_user)
):
    """图生3D接口：通过上传图片生成3D模型"""
    # 内容审核（如果有提示词）
    if generate_data.prompt:
        is_valid, reject_reason = ContentFilter.filter_content(generate_data.prompt)
        if not is_valid:
            raise HTTPException(status_code=400, detail=reject_reason)
    
    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    try:
        with_texture = generate_data.with_texture if generate_data.with_texture is not None else True
        generation_params, param_notes = _sanitize_hunyuan_image3d_params(generate_data, with_texture)
        credits_needed, credit_notes = _calculate_hunyuan3d_credits(generation_params)
        if total_points(current_user) < credits_needed:
            raise HTTPException(status_code=400, detail=f"积分不足，需要至少{credits_needed}积分")
        input_preview_url = await _persist_image_base64_preview(
            generate_data.image_base64,
            str(current_user["id"]),
            task_id,
        )
        result = await AIService.image_to_3d_model(
            image_base64=generate_data.image_base64,
            lora=generate_data.lora,
            prompt=generate_data.prompt,
            model_config_id=generate_data.model_config_id,
            db=app.state.db,
            with_texture=with_texture,
            generation_params=generation_params
        )
        
        ok = await deduct_points(
            app.state.db, 
            str(current_user['id']), 
            credits_needed,
            reason="generate_3d_hunyuan",
            related_id=task_id
        )
        if not ok:
            raise HTTPException(status_code=400, detail="积分不足")
        
        # 保存到assets表（未发布状态）
        prompt_text = _format_hunyuan_image23d_display_prompt(with_texture, generation_params)
        gen_preview = result.get("preview_url") or result.get("model_url")
        card_image_url = input_preview_url or gen_preview
        asset_id = await app.state.db.fetchrow(
            """
            INSERT INTO assets (author_id, image_url, model_url, prompt, base_model,
                              seed, steps, sampler, is_published)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, FALSE)
            RETURNING id
            """,
            current_user['id'], card_image_url,
            result['model_url'], prompt_text, generate_data.lora or "default",
            None, None, None
        )
        render_model_url, render_model_format = _resolve_render_output_payload(
            status_result=result.get("raw"),
            fallback_model_url=Hunyuan3DService.parse_query_result(result["raw"]).get("model_url") if result.get("raw") else None,
            fallback_model_format=None,
        )
        requested_result_format = generation_params.get("ResultFormat") if isinstance(generation_params, dict) else None
        should_prepare_printable_source = _should_prepare_printable_source(requested_result_format)
        gcode_source_model_url, gcode_source_model_format = (None, None)
        if should_prepare_printable_source:
            gcode_source_model_url, gcode_source_model_format = _derive_gcode_source_payload(
                model_url=result.get("model_url"),
                fallback_format=requested_result_format,
                status_result=result.get("raw"),
            )
        if should_prepare_printable_source and not gcode_source_model_url:
            gcode_source_model_url, gcode_source_model_format = await _build_gcode_source_payload_from_model_candidates(
                status_result=result.get("raw"),
                primary_model_url=result.get("model_url"),
                render_model_url=render_model_url,
                requested_result_format=requested_result_format,
                user_id=str(current_user['id']),
                job_uuid=str(uuid.uuid4()),
            )
        download_model_format = _resolve_model_format(
            result.get("model_url"),
            fallback_format=requested_result_format,
        )
        selected_model_url, selected_model_format = _resolve_selected_output_payload(
            status_result=result.get("raw"),
            requested_result_format=requested_result_format,
            default_model_url=result.get("model_url"),
            default_model_format=download_model_format,
            gcode_source_url=gcode_source_model_url,
            gcode_source_format=gcode_source_model_format,
        )
        selected_model_url, selected_model_format = _prefer_printable_selected_output(
            requested_result_format=requested_result_format,
            selected_model_url=selected_model_url,
            selected_model_format=selected_model_format,
            gcode_source_url=gcode_source_model_url,
            gcode_source_format=gcode_source_model_format,
        )
        hist_params: Dict[str, Any] = {
            "lora": generate_data.lora,
            "model_config_id": generate_data.model_config_id,
            "with_texture": with_texture,
            "generation_params": generation_params,
            "param_notes": param_notes,
            "credit_notes": credit_notes,
            "credits_used": credits_needed,
            **(
                {
                    "render_model_url": render_model_url,
                    "render_model_format": render_model_format,
                }
                if render_model_url
                else {}
            ),
            **(
                {
                    "download_model_url": selected_model_url,
                    "selected_model_url": selected_model_url,
                }
                if selected_model_url
                else {}
            ),
            **(
                {
                    "download_model_format": selected_model_format or download_model_format,
                    "selected_model_format": selected_model_format or download_model_format,
                }
                if (selected_model_format or download_model_format)
                else {}
            ),
            **(
                {
                    "gcode_source_model_url": gcode_source_model_url,
                    "gcode_source_model_format": gcode_source_model_format,
                }
                if gcode_source_model_url and gcode_source_model_format
                else {}
            ),
        }
        if input_preview_url and gen_preview:
            hist_params["generated_preview_url"] = gen_preview
        await _insert_studio_history(
            app.state.db,
            str(current_user['id']),
            "image23d",
            prompt_text,
            hist_params,
            card_image_url,
            str(asset_id['id']),
        )
        finalized_routes = await _finalize_sync_generated_model_routes(
            app.state.db,
            asset_id=str(asset_id["id"]),
            user_id=str(current_user["id"]),
            requested_result_format=requested_result_format,
            history_params=hist_params,
            asset_model_url=result.get("model_url"),
            selected_model_url=selected_model_url,
            selected_model_format=selected_model_format or download_model_format,
            render_model_url=render_model_url,
            render_model_format=render_model_format,
            gcode_source_model_url=gcode_source_model_url,
            gcode_source_model_format=gcode_source_model_format,
            job_uuid=task_id,
        )
        response_model_url = finalized_routes.get("selected_model_url") or result["model_url"]
        return {
            "task_id": task_id,
            "status": "completed",
            "asset_id": str(asset_id['id']),
            "model_url": response_model_url,
            "preview_url": result.get('preview_url'),
            "credits_used": credits_needed,
            "texture_mode": "color" if with_texture else "white",
            "generation_params": generation_params,
            "param_notes": param_notes,
            "credit_notes": credit_notes,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图生3D失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")



@app.get("/api/studio/queue-status/{task_id}")
async def get_queue_status(task_id: str, current_user: dict = Depends(get_current_user)):
    """查询生成任务状态"""
    # 这里应该从Redis或数据库查询任务状态
    # 暂时返回模拟数据
    return {
        "task_id": task_id,
        "status": "processing",  # pending/processing/completed/failed
        "progress": 50,  # 0-100
        "message": "AI 正在构建拓扑结构..."
    }


@app.get("/api/studio/pending-jobs")
async def list_studio_pending_jobs(current_user: dict = Depends(get_current_user)):
    """兼容旧前端：返回当前用户左侧任务区仍需展示的 job_id 列表。"""
    if not hasattr(app.state, "db_connected") or not app.state.db_connected:
        return {"job_ids": []}
    cutoff = datetime.now(timezone.utc) - STUDIO_UNSUCCESSFUL_RETENTION
    rows = await app.state.db.fetch(
        """
        SELECT job_id
        FROM studio_jobs
        WHERE user_id = $1
          AND (
            status IN ('SUBMITTED', 'PENDING', 'QUEUED', 'WAITING', 'RUN', 'RUNNING', 'PROCESSING', 'IN_PROGRESS')
            OR (
              asset_id IS NULL
              AND status IN ('FAILED', 'FAIL', 'ERROR', 'CANCELLED')
              AND COALESCE(finished_at, created_at) >= $2
            )
          )
        ORDER BY created_at DESC
        LIMIT 20
        """,
        current_user["id"],
        cutoff,
    )
    return {"job_ids": [r["job_id"] for r in rows]}


@app.get("/api/studio/sidebar-jobs")
async def list_studio_sidebar_jobs(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=50),
):
    """返回左侧历史栏需要展示的进行中/失败/取消 3D 任务。"""
    if not hasattr(app.state, "db_connected") or not app.state.db_connected:
        return {"items": []}

    cutoff = datetime.now(timezone.utc) - STUDIO_UNSUCCESSFUL_RETENTION
    rows = await app.state.db.fetch(
        """
        SELECT job_id, mode, status, last_message, prompt, preview_url, with_texture,
               generation_params, param_notes, credits_used, asset_id, created_at, finished_at
        FROM studio_jobs
        WHERE user_id = $1
          AND (
            status IN ('SUBMITTED', 'PENDING', 'QUEUED', 'WAITING', 'RUN', 'RUNNING', 'PROCESSING', 'IN_PROGRESS')
            OR (
              asset_id IS NULL
              AND status IN ('FAILED', 'FAIL', 'ERROR', 'CANCELLED')
              AND COALESCE(finished_at, created_at) >= $2
            )
          )
        ORDER BY created_at DESC
        LIMIT $3
        """,
        current_user["id"],
        cutoff,
        limit,
    )

    from utils.oss_util import oss_manager

    items = []
    for row in rows:
        stage = _build_studio_status(row["status"] or "")
        preview_url = row["preview_url"]
        if preview_url and preview_url.startswith("oss://"):
            preview_url = oss_manager.generate_presigned_url(preview_url[len("oss://"):], expires=3600) or preview_url
        finished_at = row["finished_at"].isoformat() if row["finished_at"] else None
        expires_at = None
        if stage["status"] in {"FAILED", "CANCELLED"}:
            base_dt = row["finished_at"] or row["created_at"]
            expires_at = (base_dt + STUDIO_UNSUCCESSFUL_RETENTION).isoformat() if base_dt else None
        items.append({
            "job_id": row["job_id"],
            "mode": row["mode"],
            "status": stage["status"],
            "progress": stage["progress"],
            "message": row["last_message"] or stage["message"],
            "prompt": _studio_job_api_display_prompt(
                row["mode"],
                row["with_texture"],
                row["generation_params"],
                row["prompt"],
            ),
            "preview_url": preview_url,
            "asset_id": str(row["asset_id"]) if row["asset_id"] else None,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "finished_at": finished_at,
            "expires_at": expires_at,
            "texture_mode": "color" if (row["with_texture"] if row["with_texture"] is not None else True) else "white",
            "generation_params": _parse_json_object(row["generation_params"]),
            "param_notes": _parse_json_list(row["param_notes"]),
            "credits_used": int(row["credits_used"] or 0),
        })
    return {"items": items}


@app.get("/api/studio/job-notifications")
async def list_studio_job_notifications(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50),
):
    """返回当前用户尚未提醒的终态任务，用于消息提示。"""
    if not hasattr(app.state, "db_connected") or not app.state.db_connected:
        return {"items": []}

    rows = await app.state.db.fetch(
        """
        SELECT job_id, mode, status, last_message, prompt, asset_id, created_at, finished_at,
               with_texture, generation_params
        FROM studio_jobs
        WHERE user_id = $1
          AND status IN ('COMPLETED', 'FAILED', 'FAIL', 'ERROR', 'CANCELLED')
          AND notified_at IS NULL
        ORDER BY COALESCE(finished_at, created_at) ASC
        LIMIT $2
        """,
        current_user["id"],
        limit,
    )

    return {
        "items": [
            {
                "job_id": r["job_id"],
                "mode": r["mode"],
                "status": "COMPLETED" if r["asset_id"] else _normalize_studio_status_name(r["status"]),
                "message": ("生成完成" if r["asset_id"] else (r["last_message"] or "")),
                "prompt": _studio_job_api_display_prompt(
                    r["mode"],
                    r["with_texture"],
                    r["generation_params"],
                    r["prompt"],
                ),
                "asset_id": str(r["asset_id"]) if r["asset_id"] else None,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "finished_at": r["finished_at"].isoformat() if r["finished_at"] else None,
            }
            for r in rows
        ]
    }


@app.post("/api/studio/job-notifications/{job_id}/ack")
async def ack_studio_job_notification(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """确认已提示该任务消息。"""
    if not hasattr(app.state, "db_connected") or not app.state.db_connected:
        raise HTTPException(status_code=503, detail="数据库未连接")

    await app.state.db.execute(
        """
        UPDATE studio_jobs
        SET notified_at = COALESCE(notified_at, now())
        WHERE job_id = $1 AND user_id = $2
        """,
        job_id,
        current_user["id"],
    )
    return {"ok": True, "job_id": job_id}


@app.post("/api/studio/local-preview/upload")
async def upload_local_preview_model(
    files: List[UploadFile] = File(...),
    primary_file_name: Optional[str] = Form(default=None),
    current_user: dict = Depends(get_current_user),
):
    """
    上传本地3D预览文件并写入历史记录（持久化）。
    说明：仅保存用户自己的文件，历史点击后可在主渲染区直接加载。
    """
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一个文件")
    if not hasattr(app.state, "db_connected") or not app.state.db_connected:
        raise HTTPException(status_code=503, detail="数据库未连接")

    model_exts = {"glb"}
    allowed_exts = {"glb"}

    if len(files) != 1:
        raise HTTPException(status_code=400, detail="本地预览当前仅支持上传 1 个 GLB 文件")

    total_size = 0
    saved_urls: Dict[str, str] = {}
    ordered_saved_names: List[str] = []

    bundle_id = str(uuid.uuid4())
    user_id_text = str(current_user["id"])
    subdir = f"studio_local/{user_id_text}/{bundle_id}"
    storage = get_storage_manager()

    primary_hint = _sanitize_local_model_filename(primary_file_name or "")
    model_candidates: List[str] = []
    used_names: set[str] = set()

    for uploaded in files:
        original_name = uploaded.filename or "file.bin"
        safe_name = _sanitize_local_model_filename(original_name)
        ext = safe_name.split(".")[-1].lower() if "." in safe_name else ""
        if ext not in allowed_exts:
            raise HTTPException(status_code=400, detail=f"文件类型不支持: {original_name}")

        # 去重，避免同名覆盖
        if safe_name in used_names:
            stem = safe_name.rsplit(".", 1)[0] if "." in safe_name else safe_name
            suffix = f".{ext}" if ext else ""
            idx = 1
            while f"{stem}_{idx}{suffix}" in used_names:
                idx += 1
            safe_name = f"{stem}_{idx}{suffix}"
        used_names.add(safe_name)

        content = await uploaded.read()
        total_size += len(content)
        if total_size > 250 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="本次上传总大小不能超过 250MB")

        from utils.oss_util import oss_manager
        if oss_manager.bucket:
            # 去掉前导的点号作为扩展名
            oss_ext = f".{ext}" if ext else ""
            # 把文件放进 models/user_id/bundle_id/filename 结构下，避免被 UUID 覆盖原名
            # upload_file_bytes 会自带 file_uuid 这可能改变原名称。这里我们可以直接使用 bucket.put_object
            oss_key = f"models/{user_id_text}/local/{bundle_id}/{safe_name}"
            import asyncio
            result = await asyncio.to_thread(oss_manager.bucket.put_object, oss_key, content)
            if result.status == 200:
                ordered_saved_names.append(safe_name)
                saved_urls[safe_name] = f"/api/studio/local-preview-file/{user_id_text}/{bundle_id}/{quote(safe_name, safe='')}"
            else:
                raise HTTPException(status_code=500, detail="保存至 OSS 失败")
        else:
            await storage.save_file(content, safe_name, subdir=subdir)
            ordered_saved_names.append(safe_name)
            saved_urls[safe_name] = f"/api/studio/local-preview-file/{user_id_text}/{bundle_id}/{quote(safe_name, safe='')}"

        if ext in model_exts:
            model_candidates.append(safe_name)
    if not model_candidates:
        raise HTTPException(status_code=400, detail="本地预览当前仅支持 GLB 格式")

    primary_name = primary_hint if primary_hint in saved_urls and primary_hint in model_candidates else model_candidates[0]
    model_url = saved_urls.get(primary_name)
    preview_url = None

    params = {
        "local_upload": True,
        "bundle_id": bundle_id,
        "primary_file": primary_name,
        "files": ordered_saved_names,
        "model_url": model_url,
    }

    await _insert_studio_history(
        app.state.db,
        user_id_text,
        "local3dpreview",
        f"本地预览：{primary_name}",
        params,
        preview_url,
        None,
    )

    return {
        "mode": "local3dpreview",
        "bundle_id": bundle_id,
        "model_url": model_url,
        "preview_url": preview_url,
        "primary_file": primary_name,
        "files_count": len(ordered_saved_names),
    }


@app.get("/api/studio/local-preview-file/{owner_id}/{bundle_id}/{file_name:path}")
async def get_local_preview_file(
    owner_id: str,
    bundle_id: str,
    file_name: str,
):
    """读取本地预览已上传文件（通过不可预测的 owner_id + bundle_id 路径访问）。"""
    if not _is_safe_relative_path(file_name):
        raise HTTPException(status_code=400, detail="非法文件路径")

    safe_owner_id = _sanitize_local_model_filename(owner_id)
    if safe_owner_id != owner_id:
        raise HTTPException(status_code=400, detail="无效的 owner_id")

    safe_bundle_id = _sanitize_local_model_filename(bundle_id)
    if safe_bundle_id != bundle_id:
        raise HTTPException(status_code=400, detail="无效的 bundle_id")

    from utils.oss_util import oss_manager
    if oss_manager.bucket:
        try:
            oss_key = f"models/{safe_owner_id}/local/{safe_bundle_id}/{file_name}"
            import asyncio
            exists = await asyncio.to_thread(oss_manager.bucket.object_exists, oss_key)
            if exists:
                url = oss_manager.generate_presigned_url(oss_key)
                if url:
                    timeout = aiohttp.ClientTimeout(total=180, connect=15, sock_read=120)
                    session = aiohttp.ClientSession(timeout=timeout)
                    upstream = await session.get(url, allow_redirects=True)
                    if upstream.status != 200:
                        await upstream.release()
                        await session.close()
                        raise HTTPException(status_code=404, detail=f"文件不存在或已过期: {upstream.status}")

                    headers = {
                        "Content-Disposition": f'inline; filename="{Path(file_name).name}"',
                        "Cache-Control": "private, max-age=300",
                    }
                    media_type = upstream.headers.get("Content-Type") or _guess_3d_media_type(file_name)

                    async def iterator():
                        try:
                            async for chunk in upstream.content.iter_chunked(64 * 1024):
                                yield chunk
                        finally:
                            await upstream.release()
                            await session.close()

                    return StreamingResponse(iterator(), media_type=media_type, headers=headers)
        except Exception as e:
            logger.warning(f"获取 OSS 预签名 URL 失败: {e}")

    base_dir = Path(Config.UPLOAD_DIR).resolve()
    root = (base_dir / "studio_local" / owner_id / bundle_id).resolve()
    target = (root / PurePosixPath(file_name)).resolve()

    if not str(target).startswith(str(root)):
        raise HTTPException(status_code=400, detail="非法文件路径")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(path=str(target), filename=target.name)


@app.get("/api/studio/history")
async def list_studio_history(
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
):
    """造梦历史列表：Token 校验身份，从数据库 studio_history 按当前用户 user_id 查询并返回。"""
    if not hasattr(app.state, "db_connected") or not app.state.db_connected:
        raise HTTPException(status_code=503, detail="数据库未连接")
    uid = current_user["id"]
    offset = (page - 1) * page_size
    rows = await app.state.db.fetch(
        """
        SELECT h.id, h.mode, h.prompt, h.params, h.preview_url, h.asset_id, h.created_at,
               a.model_url AS asset_model_url, COALESCE(a.is_published, FALSE) AS asset_is_published
        FROM studio_history h
        LEFT JOIN assets a ON h.asset_id = a.id
        WHERE h.user_id = $1
        ORDER BY h.created_at DESC
        LIMIT $2 OFFSET $3
        """,
        uid,
        page_size,
        offset,
    )
    total = await app.state.db.fetchval(
        "SELECT COUNT(*) FROM studio_history WHERE user_id = $1",
        uid,
    )
    response = {
        "items": [],
        "total": total,
        "page": page,
        "page_size": page_size,
    }

    from utils.oss_util import oss_manager
    for r in rows:
        params = _normalize_studio_params_blob(r["params"])
        requested_result_format = _normalize_requested_result_format(
            ((params.get("generation_params") or {}).get("ResultFormat") if isinstance(params, dict) and isinstance(params.get("generation_params"), dict) else None)
        )
        repaired_routes = await _repair_missing_printable_model_routes(
            app.state.db,
            asset_id=str(r["asset_id"]) if r.get("asset_id") else None,
            user_id=str(uid),
            job_uuid=str(r["id"]),
            requested_result_format=requested_result_format,
            history_params=params,
            asset_model_url=r["asset_model_url"],
            render_model_url=params.get("render_model_url"),
        )
        if repaired_routes.get("render_model_url") and not params.get("render_model_url"):
            params["render_model_url"] = repaired_routes["render_model_url"]
        if repaired_routes.get("render_model_format") and not params.get("render_model_format"):
            params["render_model_format"] = repaired_routes["render_model_format"]
        if repaired_routes.get("selected_model_url"):
            params["download_model_url"] = repaired_routes["selected_model_url"]
            params["selected_model_url"] = repaired_routes["selected_model_url"]
        if repaired_routes.get("selected_model_format"):
            params["download_model_format"] = repaired_routes["selected_model_format"]
            params["selected_model_format"] = repaired_routes["selected_model_format"]
        if repaired_routes.get("gcode_source_model_url"):
            params["gcode_source_model_url"] = repaired_routes["gcode_source_model_url"]
        if repaired_routes.get("gcode_source_model_format"):
            params["gcode_source_model_format"] = repaired_routes["gcode_source_model_format"]
        if repaired_routes.get("selected_model_url"):
            r = dict(r)
            r["asset_model_url"] = repaired_routes["selected_model_url"]
        download_model_url = None
        selected_model_url = None
        render_model_url = None
        download_model_format = None
        selected_model_format = None
        render_model_format = None
        gcode_source_model_url = None
        gcode_source_model_format = None
        if isinstance(params, dict):
            raw_render_model_url = params.get("render_model_url")
            if isinstance(raw_render_model_url, str) and raw_render_model_url.strip():
                render_model_url = raw_render_model_url

            raw_render_model_format = params.get("render_model_format")
            if isinstance(raw_render_model_format, str) and raw_render_model_format.strip():
                render_model_format = raw_render_model_format.strip().lower()

            raw_download_model_url = params.get("download_model_url")
            if isinstance(raw_download_model_url, str) and raw_download_model_url.strip():
                if _matches_requested_result_format(
                    raw_download_model_url,
                    requested_result_format,
                    params.get("download_model_format") or params.get("selected_model_format"),
                ):
                    download_model_url = raw_download_model_url

            raw_selected_model_url = params.get("selected_model_url")
            if isinstance(raw_selected_model_url, str) and raw_selected_model_url.strip():
                if _matches_requested_result_format(
                    raw_selected_model_url,
                    requested_result_format,
                    params.get("selected_model_format") or params.get("download_model_format"),
                ):
                    selected_model_url = raw_selected_model_url

            raw_download_model_format = params.get("download_model_format") or params.get("selected_model_format")
            if isinstance(raw_download_model_format, str) and raw_download_model_format.strip():
                download_model_format = raw_download_model_format.strip().lower()

            raw_selected_model_format = params.get("selected_model_format") or params.get("download_model_format")
            if isinstance(raw_selected_model_format, str) and raw_selected_model_format.strip():
                selected_model_format = raw_selected_model_format.strip().lower()

            raw_gcode_source_model_url = params.get("gcode_source_model_url")
            if isinstance(raw_gcode_source_model_url, str) and raw_gcode_source_model_url.strip():
                gcode_source_model_url = raw_gcode_source_model_url

            raw_gcode_source_model_format = params.get("gcode_source_model_format")
            if isinstance(raw_gcode_source_model_format, str) and raw_gcode_source_model_format.strip():
                gcode_source_model_format = raw_gcode_source_model_format.strip().lower()

            legacy_model_url = params.get("model_url")
            if (
                not download_model_url
                and isinstance(legacy_model_url, str)
                and legacy_model_url.strip()
                and _matches_requested_result_format(
                    legacy_model_url,
                    requested_result_format,
                    selected_model_format or download_model_format,
                )
            ):
                download_model_url = legacy_model_url
            if (
                not selected_model_url
                and isinstance(legacy_model_url, str)
                and legacy_model_url.strip()
                and _matches_requested_result_format(
                    legacy_model_url,
                    requested_result_format,
                    selected_model_format or download_model_format,
                )
            ):
                selected_model_url = legacy_model_url
            if not render_model_url and isinstance(legacy_model_url, str) and legacy_model_url.strip() and _is_history_renderable_model_url(legacy_model_url):
                render_model_url = legacy_model_url

        if not selected_model_format and requested_result_format:
            selected_model_format = requested_result_format
        if not download_model_format and requested_result_format:
            download_model_format = requested_result_format
        if not download_model_url and not selected_model_format:
            download_model_url = r["asset_model_url"]
        if not selected_model_url and not selected_model_format:
            selected_model_url = download_model_url
        if not render_model_url and _is_history_renderable_model_url(r["asset_model_url"]):
            render_model_url = r["asset_model_url"]
        if not download_model_format:
            download_model_format = _resolve_model_format(
                download_model_url,
                fallback_format=requested_result_format,
            )
        if not selected_model_format:
            selected_model_format = _resolve_model_format(
                selected_model_url,
                fallback_format=requested_result_format,
            )
        if not render_model_format:
            render_model_format = _resolve_model_format(render_model_url)
        selected_model_url, selected_model_format = _prefer_printable_selected_output(
            requested_result_format=requested_result_format,
            selected_model_url=selected_model_url,
            selected_model_format=selected_model_format,
            gcode_source_url=gcode_source_model_url,
            gcode_source_format=gcode_source_model_format,
        )
        if selected_model_url:
            download_model_url = selected_model_url
        if selected_model_format:
            download_model_format = selected_model_format
            
        preview_url = r["preview_url"]
        if preview_url and preview_url.startswith("oss://"):
            preview_url = oss_manager.generate_presigned_url(preview_url[len("oss://"):], expires=3600) or preview_url
            
        if render_model_url and render_model_url.startswith("oss://"):
            render_model_url = oss_manager.generate_presigned_url(render_model_url[len("oss://"):], expires=3600) or render_model_url
        if download_model_url and download_model_url.startswith("oss://"):
            download_model_url = oss_manager.generate_presigned_url(download_model_url[len("oss://"):], expires=3600) or download_model_url
        if selected_model_url and selected_model_url.startswith("oss://"):
            selected_model_url = oss_manager.generate_presigned_url(selected_model_url[len("oss://"):], expires=3600) or selected_model_url
        if gcode_source_model_url and gcode_source_model_url.startswith("oss://"):
            gcode_source_model_url = oss_manager.generate_presigned_url(gcode_source_model_url[len("oss://"):], expires=3600) or gcode_source_model_url

        prompt_out = _normalize_studio_prompt(r["mode"], r["prompt"])
        if str(r.get("mode") or "") == "image23d":
            recomputed = prompt_from_studio_history_row("image23d", params)
            if recomputed:
                prompt_out = recomputed

        response["items"].append({
            "id": str(r["id"]),
            "mode": r["mode"],
            "prompt": prompt_out,
            "params": params,
            "preview_url": preview_url,
            "model_url": selected_model_url,
            "download_model_url": download_model_url,
            "download_model_format": download_model_format,
            "selected_model_url": selected_model_url,
            "selected_model_format": selected_model_format,
            "render_model_url": render_model_url,
            "render_model_format": render_model_format,
            "gcode_source_model_url": gcode_source_model_url,
            "gcode_source_model_format": gcode_source_model_format,
            "asset_id": str(r["asset_id"]) if r["asset_id"] else None,
            "is_published": bool(r["asset_is_published"]),
            "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
        })

    return response


@app.delete("/api/studio/history/{history_id}")
async def delete_studio_history(
    history_id: str,
    current_user: dict = Depends(get_current_user),
):
    """删除一条造梦历史；仅本人可删。"""
    if not hasattr(app.state, "db_connected") or not app.state.db_connected:
        raise HTTPException(status_code=503, detail="数据库未连接")
    uid = current_user["id"]
    try:
        hid = uuid.UUID(history_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的历史记录 id")
    row = await app.state.db.fetchrow(
        """
        SELECT h.id, h.preview_url, a.model_url as asset_model_url, COALESCE(a.is_published, FALSE) AS asset_is_published
        FROM studio_history h
        LEFT JOIN assets a ON h.asset_id = a.id
        WHERE h.id = $1 AND h.user_id = $2
        """,
        hid,
        uid,
    )
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在或无权删除")
    if row["asset_is_published"]:
        raise HTTPException(status_code=409, detail="该作品已发布到社区，请先在社区删除后再删除历史记录")

    # 删除 OSS 中的关联文件
    from utils.oss_util import oss_manager
    preview_url = row["preview_url"]
    model_url = row["asset_model_url"]
    if preview_url and preview_url.startswith("oss://"):
        oss_manager.delete_object(preview_url[len("oss://"):])
    if model_url and model_url.startswith("oss://"):
        oss_manager.delete_object(model_url[len("oss://"):])

    await app.state.db.execute("DELETE FROM studio_history WHERE id = $1", hid)
    return {"ok": True}

# ========== 工作流引擎模块已迁移到 api/workflow.py ==========
# ========== 订单与支付模块已迁移到 api/orders.py ==========
# ========== 地址管理已迁移到 api/address.py ==========

# ========== IoT 设备模块 ==========

@app.post("/api/device/sync")
async def sync_device(device_data: Device, current_user: dict = Depends(get_current_user)):
    """底座数据同步"""
    # 更新或创建设备记录
    existing = await app.state.db.fetchrow(
        "SELECT id FROM devices WHERE device_id = $1",
        device_data.device_id
    )
    
    if existing:
        await app.state.db.execute(
            """
            UPDATE devices 
            SET user_id = $1, char_prompt = $2, last_sync_at = CURRENT_TIMESTAMP
            WHERE device_id = $3
            """,
            current_user['id'], device_data.char_prompt, device_data.device_id
        )
    else:
        await app.state.db.execute(
            """
            INSERT INTO devices (user_id, device_id, char_prompt, last_sync_at)
            VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
            """,
            current_user['id'], device_data.device_id, device_data.char_prompt
        )
    
    # 这里应该同步到Redis（用于实时查询）
    # 暂时跳过Redis集成
    
    return {"message": "Device synced successfully"}

@app.get("/api/device")
async def get_devices(current_user: dict = Depends(get_current_user)):
    """获取用户设备列表"""
    devices = await app.state.db.fetch(
        "SELECT * FROM devices WHERE user_id = $1 ORDER BY last_sync_at DESC",
        current_user['id']
    )
    
    return [dict(device) for device in devices]

@app.get("/api/device/{device_id}")
async def get_device_detail(device_id: str, current_user: dict = Depends(get_current_user)):
    """获取设备详情"""
    device = await app.state.db.fetchrow(
        "SELECT * FROM devices WHERE device_id = $1 AND user_id = $2",
        device_id, current_user['id']
    )
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return dict(device)

# ========== Prompt 服务 ==========

PROMPT_LIBRARY = {
    "animal": [
        "一只可爱的小猫，3D模型，卡通风格",
        "一只威武的狮子，写实风格，细节丰富",
        "一只优雅的鹿，自然风格，流畅线条"
    ],
    "mecha": [
        "未来机器人，机械风格，金属质感",
        "机甲战士，科幻风格，细节丰富",
        "机械龙，蒸汽朋克风格"
    ],
    "character": [
        "可爱的角色，卡通风格，大眼睛",
        "英雄角色，写实风格，肌肉线条",
        "魔法师角色，奇幻风格，法袍飘逸"
    ]
}

@app.get("/api/prompt/random")
async def get_random_prompt(category: Optional[str] = None):
    """获取随机Prompt"""
    if category and category in PROMPT_LIBRARY:
        prompts = PROMPT_LIBRARY[category]
    else:
        # 返回所有分类的随机一个
        all_prompts = []
        for cat_prompts in PROMPT_LIBRARY.values():
            all_prompts.extend(cat_prompts)
        prompts = all_prompts
    
    return {"prompt": random.choice(prompts), "category": category}

# ========== 打印任务模块 ==========

@app.post("/api/print/jobs")
async def create_print_job(
    asset_id: str,
    current_user: dict = Depends(get_current_user)
):
    """创建打印任务（当前版本不再扣积分，仅记录任务）"""
    # 检查资产是否存在
    asset = await app.state.db.fetchrow(
        "SELECT id FROM assets WHERE id = $1",
        asset_id
    )
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # 创建打印任务
    job_id = await app.state.db.fetchrow(
        """
        INSERT INTO print_jobs (user_id, asset_id, status, credits_used)
        VALUES ($1, $2, 'pending', $3)
        RETURNING id
        """,
        current_user['id'], asset_id, 0
    )
    
    return {"job_id": str(job_id['id']), "status": "pending"}

@app.get("/api/print/jobs")
async def get_print_jobs(current_user: dict = Depends(get_current_user)):
    """获取用户打印任务列表"""
    jobs = await app.state.db.fetch(
        """
        SELECT pj.*, a.image_url, a.prompt
        FROM print_jobs pj
        JOIN assets a ON pj.asset_id = a.id
        WHERE pj.user_id = $1
        ORDER BY pj.created_at DESC
        """,
        current_user['id']
    )
    
    return [dict(job) for job in jobs]

@app.get("/api/print/jobs/{job_id}")
async def get_print_job_status(job_id: str, current_user: dict = Depends(get_current_user)):
    """获取打印任务状态"""
    job = await app.state.db.fetchrow(
        "SELECT * FROM print_jobs WHERE id = $1 AND user_id = $2",
        job_id, current_user['id']
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Print job not found")
    
    return dict(job)

# ========== 模型配置管理模块 ==========

@app.get("/api/model-configs")
async def get_model_configs(current_user: dict = Depends(get_current_user)):
    """获取用户的所有模型配置（包括系统默认配置）"""
    configs = await app.state.db.fetch(
        """
        SELECT id, user_id, name, api_endpoint, auth_type, model_name, provider, 
               parameters, is_active, is_default, created_at, updated_at
        FROM user_model_configs
        WHERE user_id = $1 OR user_id IS NULL
        ORDER BY is_default DESC, created_at DESC
        """,
        current_user['id']
    )
    
    # 不返回 api_key（敏感信息）
    result = []
    for config in configs:
        config_dict = dict(config)
        result.append(config_dict)
    
    return result

@app.post("/api/model-configs")
async def create_model_config(
    config_data: ModelConfigCreate,
    current_user: dict = Depends(get_current_user)
):
    """创建新的模型配置"""
    # 输入验证
    if not config_data.name or not config_data.api_endpoint:
        raise HTTPException(status_code=400, detail="配置名称和 API 端点不能为空")
    
    # URL 格式验证
    if not re.match(r'^https?://', config_data.api_endpoint):
        raise HTTPException(status_code=400, detail="API 端点必须是有效的 HTTP/HTTPS URL")
    
    # 如果设置为默认，取消其他默认配置
    if config_data.is_default if hasattr(config_data, 'is_default') else False:
        await app.state.db.execute(
            "UPDATE user_model_configs SET is_default = FALSE WHERE user_id = $1",
            current_user['id']
        )
    
    # 加密 API Key
    encrypted_api_key = None
    if config_data.api_key:
        encrypted_api_key = EncryptionManager.encrypt(config_data.api_key)
    
    # 创建配置
    config_id = await app.state.db.fetchrow(
        """
        INSERT INTO user_model_configs 
        (user_id, name, api_endpoint, api_key, auth_type, model_name, provider, parameters, is_default)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id
        """,
        current_user['id'], config_data.name, config_data.api_endpoint,
        encrypted_api_key, config_data.auth_type, config_data.model_name,
        config_data.provider, json.dumps(config_data.parameters or {}),
        config_data.is_default if hasattr(config_data, 'is_default') else False
    )
    
    return {"config_id": str(config_id['id']), "message": "模型配置创建成功"}

@app.get("/api/model-configs/{config_id}")
async def get_model_config(
    config_id: str,
    current_user: dict = Depends(get_current_user)
):
    """获取模型配置详情"""
    config = await app.state.db.fetchrow(
        """
        SELECT id, user_id, name, api_endpoint, auth_type, model_name, provider,
               parameters, is_active, is_default, created_at, updated_at
        FROM user_model_configs
        WHERE id = $1 AND (user_id = $2 OR user_id IS NULL)
        """,
        config_id, current_user['id']
    )
    
    if not config:
        raise HTTPException(status_code=404, detail="模型配置不存在或无权限访问")
    
    config_dict = dict(config)
    return config_dict

@app.put("/api/model-configs/{config_id}")
async def update_model_config(
    config_id: str,
    config_data: ModelConfigUpdate,
    current_user: dict = Depends(get_current_user)
):
    """更新模型配置"""
    # 检查配置是否存在且属于当前用户
    existing = await app.state.db.fetchrow(
        "SELECT user_id FROM user_model_configs WHERE id = $1",
        config_id
    )
    
    if not existing:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    
    # 系统默认配置（user_id 为 NULL）不允许修改
    if existing['user_id'] is None:
        raise HTTPException(status_code=403, detail="系统默认配置不允许修改")
    
    # 只能修改自己的配置
    if str(existing['user_id']) != str(current_user['id']):
        raise HTTPException(status_code=403, detail="无权限修改此配置")
    
    # 构建更新字段
    update_fields = []
    update_values = []
    param_index = 1
    
    if config_data.name is not None:
        update_fields.append(f"name = ${param_index}")
        update_values.append(config_data.name)
        param_index += 1
    
    if config_data.api_endpoint is not None:
        # URL 格式验证
        if not re.match(r'^https?://', config_data.api_endpoint):
            raise HTTPException(status_code=400, detail="API 端点必须是有效的 HTTP/HTTPS URL")
        update_fields.append(f"api_endpoint = ${param_index}")
        update_values.append(config_data.api_endpoint)
        param_index += 1
    
    if config_data.api_key is not None:
        encrypted_api_key = EncryptionManager.encrypt(config_data.api_key)
        update_fields.append(f"api_key = ${param_index}")
        update_values.append(encrypted_api_key)
        param_index += 1
    
    if config_data.auth_type is not None:
        update_fields.append(f"auth_type = ${param_index}")
        update_values.append(config_data.auth_type)
        param_index += 1
    
    if config_data.model_name is not None:
        update_fields.append(f"model_name = ${param_index}")
        update_values.append(config_data.model_name)
        param_index += 1
    
    if config_data.provider is not None:
        update_fields.append(f"provider = ${param_index}")
        update_values.append(config_data.provider)
        param_index += 1
    
    if config_data.parameters is not None:
        update_fields.append(f"parameters = ${param_index}")
        update_values.append(json.dumps(config_data.parameters))
        param_index += 1
    
    if config_data.is_active is not None:
        update_fields.append(f"is_active = ${param_index}")
        update_values.append(config_data.is_active)
        param_index += 1
    
    if config_data.is_default is not None:
        # 如果设置为默认，取消其他默认配置
        if config_data.is_default:
            await app.state.db.execute(
                "UPDATE user_model_configs SET is_default = FALSE WHERE user_id = $1 AND id != $2",
                current_user['id'], config_id
            )
        update_fields.append(f"is_default = ${param_index}")
        update_values.append(config_data.is_default)
        param_index += 1
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="没有提供要更新的字段")
    
    # 添加 updated_at
    update_fields.append(f"updated_at = CURRENT_TIMESTAMP")
    
    # 添加 WHERE 条件
    update_values.append(config_id)
    update_values.append(current_user['id'])
    
    query = f"""
        UPDATE user_model_configs
        SET {', '.join(update_fields)}
        WHERE id = ${param_index} AND user_id = ${param_index + 1}
    """
    
    result = await app.state.db.execute(query, *update_values)
    
    if "0" in str(result):
        raise HTTPException(status_code=404, detail="模型配置不存在或更新失败")
    
    return {"message": "模型配置更新成功"}

@app.delete("/api/model-configs/{config_id}")
async def delete_model_config(
    config_id: str,
    current_user: dict = Depends(get_current_user)
):
    """删除模型配置"""
    # 检查配置是否存在
    existing = await app.state.db.fetchrow(
        "SELECT user_id FROM user_model_configs WHERE id = $1",
        config_id
    )
    
    if not existing:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    
    # 系统默认配置不允许删除
    if existing['user_id'] is None:
        raise HTTPException(status_code=403, detail="系统默认配置不允许删除")
    
    # 只能删除自己的配置
    if str(existing['user_id']) != str(current_user['id']):
        raise HTTPException(status_code=403, detail="无权限删除此配置")
    
    result = await app.state.db.execute(
        "DELETE FROM user_model_configs WHERE id = $1 AND user_id = $2",
        config_id, current_user['id']
    )
    
    if "0" in str(result):
        raise HTTPException(status_code=404, detail="模型配置不存在或删除失败")
    
    return {"message": "模型配置删除成功"}

@app.put("/api/model-configs/{config_id}/set-default")
async def set_default_model_config(
    config_id: str,
    current_user: dict = Depends(get_current_user)
):
    """设置默认模型配置"""
    # 检查配置是否存在且属于当前用户
    existing = await app.state.db.fetchrow(
        "SELECT user_id, is_active FROM user_model_configs WHERE id = $1",
        config_id
    )
    
    if not existing:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    
    # 系统默认配置或他人的配置不能设置为默认
    if existing['user_id'] is None or str(existing['user_id']) != str(current_user['id']):
        raise HTTPException(status_code=403, detail="无权限操作此配置")
    
    if not existing['is_active']:
        raise HTTPException(status_code=400, detail="不能将禁用的配置设置为默认")
    
    # 取消其他默认配置
    await app.state.db.execute(
        "UPDATE user_model_configs SET is_default = FALSE WHERE user_id = $1",
        current_user['id']
    )
    
    # 设置当前配置为默认
    await app.state.db.execute(
        "UPDATE user_model_configs SET is_default = TRUE WHERE id = $1",
        config_id
    )
    
    return {"message": "默认模型配置设置成功"}

@app.post("/api/model-configs/{config_id}/test")
async def test_model_config(
    config_id: str,
    current_user: dict = Depends(get_current_user)
):
    """测试模型配置连接"""
    # 获取配置（包括加密的 API Key）
    config = await app.state.db.fetchrow(
        """
        SELECT id, user_id, name, api_endpoint, api_key, auth_type, model_name, provider, parameters
        FROM user_model_configs
        WHERE id = $1 AND (user_id = $2 OR user_id IS NULL)
        """,
        config_id, current_user['id']
    )
    
    if not config:
        raise HTTPException(status_code=404, detail="模型配置不存在或无权限访问")
    
    if not config['is_active']:
        raise HTTPException(status_code=400, detail="配置已禁用，无法测试")
    
    # 解密 API Key
    api_key = None
    if config['api_key']:
        api_key = EncryptionManager.decrypt(config['api_key'])
    
    # 发送测试请求
    try:
        import aiohttp
        headers = {}
        
        # 根据认证类型设置请求头
        if config['auth_type'] == 'api_key' and api_key:
            headers['Authorization'] = f"Bearer {api_key}"
        elif config['auth_type'] == 'bearer' and api_key:
            headers['Authorization'] = f"Bearer {api_key}"
        elif config['auth_type'] == 'api_key' and api_key:
            headers['X-API-Key'] = api_key
        
        # 构建测试请求体
        test_payload = {
            "model": config['model_name'] or "test",
            "messages": [{"role": "user", "content": "test"}],
            "max_tokens": 10
        }
        
        # 合并自定义参数
        if config['parameters']:
            custom_params = config['parameters'] if isinstance(config['parameters'], dict) else json.loads(config['parameters'])
            test_payload.update(custom_params)
        
        async with aiohttp.ClientSession() as session:
            timeout = aiohttp.ClientTimeout(total=10)  # 10秒超时
            async with session.post(
                config['api_endpoint'],
                json=test_payload,
                headers=headers,
                timeout=timeout
            ) as response:
                if response.status in [200, 201]:
                    return {
                        "status": "success",
                        "message": "连接测试成功",
                        "status_code": response.status
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"连接失败，状态码: {response.status}",
                        "status_code": response.status
                    }
    except aiohttp.ClientError as e:
        return {
            "status": "error",
            "message": f"网络错误: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"测试失败: {str(e)}"
        }

# ========== WebSocket 支持 ==========

@app.websocket("/ws/generation/{task_id}")
async def websocket_generation(websocket: WebSocket, task_id: str):
    """WebSocket端点：实时推送生成进度"""
    await websocket.accept()
    
    try:
        # 模拟进度推送
        for step in range(1, 21):
            await websocket.send_json({
                "step": step,
                "total": 20,
                "message": f"AI 正在构建拓扑结构... Step {step}/20"
            })
            import asyncio
            await asyncio.sleep(0.5)  # 模拟生成时间
        
        # 生成完成
        await websocket.send_json({
            "status": "completed",
            "message": "生成完成！",
            "model_url": f"/models/{task_id}.glb",
            "preview_url": f"/previews/{task_id}.jpg"
        })
    except WebSocketDisconnect:
        pass

# ========== 健康检查增强 ==========

@app.get("/api/health")
async def health_check():
    """系统健康检查（包含数据库连接状态）"""
    db_status = "unknown"
    if hasattr(app.state, 'db_connected') and app.state.db_connected:
        try:
            await app.state.db.fetchrow("SELECT 1")
            db_status = "connected"
        except:
            db_status = "disconnected"
    else:
        db_status = "disconnected"
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "database": db_status
    }

# ========== 管理员相关路由已迁移到 api/admin.py ==========

if __name__ == "__main__":
    import uvicorn
    # 使用127.0.0.1而不是0.0.0.0，避免某些系统的权限问题
    try:
        uvicorn.run(app, host="127.0.0.1", port=3000, log_level="info")
    except OSError as e:
        if "operation not permitted" in str(e).lower():
            print("\n❌ 端口绑定失败：权限不足")
            print("💡 请尝试：")
            print("   1. 检查端口3000是否被其他程序占用")
            print("   2. 尝试使用其他端口（修改backend.py中的port参数）")
            print("   3. 检查系统防火墙设置")
            raise
        else:
            raise
