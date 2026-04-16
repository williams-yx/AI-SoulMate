"""造梦 Studio：作品/历史展示用文案（与前端参数选项一致，供 main 与 assets 路由复用）。"""

import json
from typing import Any, Dict, List


def parse_json_object(value: Any) -> Dict[str, Any]:
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


def format_hunyuan_image23d_display_prompt(with_texture: bool, generation_params: Any) -> str:
    """图生3D：参数摘要（中文），与造梦页选项一致。"""
    gp = parse_json_object(generation_params)
    parts: List[str] = ["图生3D"]
    model = gp.get("Model")
    if model:
        parts.append(f"模型{model}")
    gt_raw = str(gp.get("GenerateType") or ("Normal" if with_texture else "Geometry"))
    gt_map = {
        "Normal": "标准",
        "LowPoly": "低多边形",
        "Geometry": "几何白模",
        "Sketch": "草图",
    }
    gt_zh = gt_map.get(gt_raw, gt_raw)
    tex_zh = "彩色" if with_texture else "白模"
    parts.append(f"{gt_zh}·{tex_zh}")
    fc = gp.get("FaceCount")
    try:
        fc_int = int(fc) if fc is not None else 0
    except (TypeError, ValueError):
        fc_int = 0
    if fc_int > 0:
        if fc_int >= 10000 and fc_int % 10000 == 0:
            parts.append(f"{fc_int // 10000}万面")
        else:
            parts.append(f"面数{fc_int}")
    if gp.get("EnablePBR"):
        parts.append("PBR")
    pt = gp.get("PolygonType")
    if pt:
        pt_map = {"triangle": "三角面", "quadrilateral": "四边面"}
        pk = str(pt).lower()
        parts.append(pt_map.get(pk, str(pt)))
    rf = gp.get("ResultFormat")
    if rf and str(rf).upper() != "GLB":
        parts.append(f"输出{str(rf).upper()}")
    return " · ".join(parts)


def prompt_from_studio_history_row(mode: str | None, params_blob: Any) -> str | None:
    """若存在对应造梦历史行，返回应对外展示的 prompt 摘要（当前支持 image23d）。"""
    if not mode or str(mode) != "image23d":
        return None
    pobj = parse_json_object(params_blob) if not isinstance(params_blob, dict) else dict(params_blob)
    wt_raw = pobj.get("with_texture")
    wt = bool(True if wt_raw is None else wt_raw)
    gp = pobj.get("generation_params")
    return format_hunyuan_image23d_display_prompt(wt, gp)
