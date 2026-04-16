"""
资产相关的数据模型
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict
from datetime import datetime


class Asset(BaseModel):
    """资产模型"""
    model_config = ConfigDict(protected_namespaces=())
    id: Optional[str] = None
    author_id: str
    image_url: str
    model_url: str
    prompt: str
    base_model: str  # LoRA ID
    seed: Optional[int] = None
    steps: Optional[int] = None
    sampler: Optional[str] = None
    tags: Optional[List[str]] = []
    stats: Optional[Dict[str, int]] = {"likes": 0, "downloads": 0}
    is_published: bool = False
    created_at: Optional[datetime] = None


class StudioGenerate(BaseModel):
    """工作室生成模型（文生图和文生3D）"""
    model_config = ConfigDict(protected_namespaces=())
    prompt: str
    lora: Optional[str] = None  # LoRA ID（可选，文生图不需要）
    model_config_id: Optional[str] = None  # 自定义模型配置 ID
    with_texture: Optional[bool] = True  # 3D生成：True=彩模，False=白模
    # 3D高级参数（兼容混元生3D专业版）
    model: Optional[str] = None  # 模型版本：3.0/3.1
    generate_type: Optional[str] = None  # Normal/LowPoly/Geometry/Sketch
    face_count: Optional[int] = None  # 面数：Normal/Geometry/Sketch 10000~1500000；LowPoly 3000~1500000
    enable_pbr: Optional[bool] = None  # 是否开启PBR
    polygon_type: Optional[str] = None  # LowPoly下生效：triangle/quadrilateral
    result_format: Optional[str] = None  # 输出格式：GLB/STL
    multi_view_images: Optional[List[str]] = None  # 多视图图像（可选）
    # 文生图输出规格控制
    aspect_ratio: Optional[str] = None  # 例如 1:1 / 3:4 / 4:3 / 16:9 / 9:16
    resolution_level: Optional[str] = None  # 例如 720p / 1k / 2k（推荐）
    image_size: Optional[str] = None  # 兼容旧端：例如 1024x1024
    # 文生图风格与清晰度控制（quality 仅兼容旧端，推荐用 resolution_level）
    style: Optional[str] = None  # auto/cinematic/photoreal/anime/illustration/watercolor/pixel
    quality: Optional[str] = None  # standard/hd（若上游不支持会自动回退）


class StudioImageTo3D(BaseModel):
    """工作室图生3D模型"""
    model_config = ConfigDict(protected_namespaces=())
    image_base64: str  # Base64编码的图片数据
    lora: Optional[str] = None  # LoRA ID（风格模型，可选）
    prompt: Optional[str] = None  # 可选的文本描述（辅助生成）
    model_config_id: Optional[str] = None  # 自定义模型配置 ID
    with_texture: Optional[bool] = True  # 3D生成：True=彩模，False=白模
    # 以下参数以腾讯混元生3D官方支持为准（SubmitHunyuanTo3DProJob）
    model: Optional[str] = None  # 模型版本：3.0/3.1
    generate_type: Optional[str] = None  # Normal/LowPoly/Geometry/Sketch
    face_count: Optional[int] = None  # 面数：Normal 10000-1500000；LowPoly 3000-1500000
    enable_pbr: Optional[bool] = None  # 是否开启PBR
    polygon_type: Optional[str] = None  # LowPoly下生效：triangle/quadrilateral
    result_format: Optional[str] = None  # 输出格式：GLB/STL
    multi_view_images: Optional[List[str]] = None  # 多视图图像（可选）


# 导出
__all__ = ["Asset", "StudioGenerate", "StudioImageTo3D"]
