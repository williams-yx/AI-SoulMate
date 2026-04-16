"""
腾讯混元生3D服务模块
支持文生3D和图生3D功能
"""

import aiohttp
import base64
import json
import asyncio
import uuid
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from PIL import Image, UnidentifiedImageError
from logger import logger
from config import Config


class Hunyuan3DService:
    """腾讯混元生3D服务类"""

    @staticmethod
    def _url_ext(url: str) -> str:
        try:
            path = urlparse(url).path
            if "." not in path:
                return ""
            return path.rsplit(".", 1)[-1].lower()
        except Exception:
            return ""

    @staticmethod
    def _result_file_type(file_info: Dict[str, Any]) -> str:
        url_ext = Hunyuan3DService._url_ext(file_info.get("Url", ""))
        if url_ext:
            return url_ext
        declared = (file_info.get("Type") or file_info.get("FileType") or "").strip().lower()
        if declared:
            return declared
        return url_ext

    @staticmethod
    def _extract_image_base64_payload(image_base64: str) -> tuple[str, str]:
        """提取图生3D请求体需要的纯 base64 和图片格式。"""
        if image_base64.startswith("data:image"):
            header, encoded = image_base64.split(",", 1)
            image_format = header.split("/")[1].split(";")[0]
        else:
            encoded = image_base64
            image_format = ""

        try:
            raw = base64.b64decode(encoded, validate=True)
        except Exception as e:
            raise Exception(f"Base64数据格式无效: {str(e)}")

        normalized_image_format = str(image_format or "").strip().lower()
        if not normalized_image_format:
            try:
                detected = Image.open(BytesIO(raw)).format
            except UnidentifiedImageError as e:
                raise Exception(f"无法识别图片格式: {str(e)}")
            normalized_image_format = str(detected or "").strip().lower()

        if normalized_image_format == "jpg":
            normalized_image_format = "jpeg"

        allowed_formats = {"jpeg", "png", "bmp", "tiff", "webp"}
        if normalized_image_format not in allowed_formats:
            allowed = ", ".join(sorted(allowed_formats | {"jpg"}))
            raise Exception(f"图片格式不支持，仅支持: {allowed}")

        return encoded, normalized_image_format

    @staticmethod
    def _pick_model_type_order(preferred_format: Optional[str] = None) -> list[str]:
        preferred = str(preferred_format or "").strip().lower()
        if preferred == "glb":
            return ["glb", "gltf", "obj", "stl", "fbx", "usdz", "ply"]
        if preferred == "stl":
            # STL 请求优先取渲染主模型（GLB/GLTF），后续由服务端统一转 STL，
            # 避免上游把 ZIP/OBJ 结果误标成 STL 时直接走错下载链路。
            return ["glb", "gltf", "stl", "obj", "fbx", "usdz", "ply", "zip"]
        return ["glb", "gltf", "obj", "stl", "fbx", "usdz", "ply"]



    @staticmethod
    def _build_generation_variants(
        with_texture: bool,
        generation_params: Optional[Dict[str, Any]] = None
    ) -> list[Dict[str, Any]]:
        """
        构建参数候选，兼容不同版本参数差异：
        1) 优先尝试完整参数（腾讯官方支持参数）
        2) 参数不兼容时，逐步降级到最小可用参数
        """
        base = dict(generation_params or {})
        generate_type = "Normal" if with_texture else "Geometry"
        if "GenerateType" not in base:
            base["GenerateType"] = generate_type

        # 尽量保留显式格式选择；如果上游不支持，会在后续降级到不带 ResultFormat 的请求。
        keep_keys = {"GenerateType", "ResultFormat", "Model", "FaceCount", "EnablePBR"}
        
        variants: list[Dict[str, Any]] = [
            base,
            {k: v for k, v in base.items() if k in keep_keys},
            {k: v for k, v in base.items() if k in {"GenerateType", "ResultFormat"}},
            {"GenerateType": generate_type, "ResultFormat": base.get("ResultFormat", "STL")},
            {"GenerateType": generate_type},
        ]
        # 去重，避免重复请求
        dedup: list[Dict[str, Any]] = []
        seen = set()
        for variant in variants:
            key = json.dumps(variant, sort_keys=True, ensure_ascii=False)
            if key not in seen:
                seen.add(key)
                dedup.append(variant)
        return dedup

    @staticmethod
    def _is_param_compat_error(resp_text: str) -> bool:
        text = (resp_text or "").lower()
        keywords = [
            "invalid parameter",
            "invalidparameter",
            "unknown parameter",
            "unexpected field",
            "unknown field",
            "not support",
            "generatetype",
            "不支持",
            "参数",
        ]
        return any(key in text for key in keywords)

    @staticmethod
    async def _submit_job_with_texture_fallback(
        session: aiohttp.ClientSession,
        url: str,
        headers: Dict[str, str],
        base_body: Dict[str, Any],
        with_texture: bool,
        generation_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        提交任务并尝试白模/彩模参数兼容。
        若上游不识别参数，会自动降级重试。
        """
        variants = Hunyuan3DService._build_generation_variants(with_texture, generation_params)
        last_error = "unknown"

        for idx, extra in enumerate(variants):
            body = {**base_body, **extra}
            async with session.post(url, json=body, headers=headers) as response:
                text = await response.text()
                logger.info(
                    f"混元生3D submit 尝试#{idx + 1}: status={response.status}, "
                    f"mode={extra if extra else 'default'}, body={text}"
                )
                if response.status == 200:
                    result = json.loads(text) if text else {}
                    response_data = result.get("Response", result)
                    job_id = (
                        response_data.get("JobId")
                        or response_data.get("job_id")
                        or result.get("JobId")
                        or result.get("job_id")
                    )
                    api_error = response_data.get("Error") or result.get("Error")
                    if api_error:
                        error_text = json.dumps(api_error, ensure_ascii=False)
                        # 有些版本返回200但Body里是参数错误，继续降级重试
                        if extra and Hunyuan3DService._is_param_compat_error(error_text):
                            logger.warning(f"参数不兼容(200+Error)，继续降级重试: {extra}, err={error_text}")
                            continue
                        raise Exception(f"API返回错误: {error_text}")
                    if job_id:
                        if extra:
                            logger.info(f"✅ 白模/彩模参数生效: {extra}")
                        else:
                            logger.warning("⚠️ 白模/彩模参数未生效，已降级为默认提交")
                        return result
                    # 200但没有JobId：优先按兼容场景处理
                    if extra:
                        logger.warning(f"响应未返回JobId，继续降级重试: {extra}, body={result}")
                        continue
                    raise Exception(f"未返回 JobId，返回内容: {result}")

                last_error = f"{response.status}, {text}"
                if extra and Hunyuan3DService._is_param_compat_error(text):
                    logger.warning(f"参数不兼容，继续降级重试: {extra}")
                    continue
                raise Exception(f"API调用失败: {response.status}, {text}")

        raise Exception(f"API调用失败: {last_error}")

    @staticmethod
    async def submit_text_to_3d(
        prompt: str,
        with_texture: bool = True,
        generation_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        提交文生3D任务，返回 JobId（不轮询）

        Args:
            prompt: 文本描述
            with_texture: 是否生成纹理（True=彩模，False=白模）

        Returns:
            job_id
        """
        request_body = {
            "Prompt": prompt
        }

        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": Config.HUNYUAN3D_API_KEY,
                "Content-Type": "application/json"
            }
            url = f"{Config.HUNYUAN3D_BASE_URL}/v1/ai3d/submit"

            logger.info(f"提交混元生3D文生3D任务: url={url}, prompt={prompt[:50]}..., with_texture={with_texture}")
            result = await Hunyuan3DService._submit_job_with_texture_fallback(
                session=session,
                url=url,
                headers=headers,
                base_body=request_body,
                with_texture=with_texture,
                generation_params=generation_params,
            )
            response_data = result.get("Response", result)
            job_id = response_data.get("JobId") or response_data.get("job_id") or result.get("JobId") or result.get("job_id")
            if not job_id:
                raise Exception(f"未返回 JobId，返回内容: {result}")

            logger.info(f"✅ 获取到 JobId: {job_id}")
            return job_id

    @staticmethod
    async def submit_image_to_3d(
        image_base64: str,
        with_texture: bool = True,
        generation_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        提交图生3D任务（ImageBase64），返回 JobId（不轮询）

        Args:
            image_base64: Base64编码的图片数据（可带 data:image/... 前缀）
            with_texture: 是否生成纹理（True=彩模，False=白模）

        Returns:
            job_id
        """
        encoded, image_format = Hunyuan3DService._extract_image_base64_payload(image_base64)

        request_body: Dict[str, Any] = {
            "ImageBase64": encoded,
            "ImageFormat": image_format,
        }

        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": Config.HUNYUAN3D_API_KEY,
                "Content-Type": "application/json"
            }
            url = f"{Config.HUNYUAN3D_BASE_URL}/v1/ai3d/submit"

            logger.info(
                f"提交混元生3D图生3D任务: url={url}, image_format={image_format}, "
                f"base64_len={len(encoded)}, with_texture={with_texture}"
            )
            result = await Hunyuan3DService._submit_job_with_texture_fallback(
                session=session,
                url=url,
                headers=headers,
                base_body=request_body,
                with_texture=with_texture,
                generation_params=generation_params,
            )
            response_data = result.get("Response", result)
            job_id = response_data.get("JobId") or response_data.get("job_id") or result.get("JobId") or result.get("job_id")
            if not job_id:
                raise Exception(f"未返回 JobId，返回内容: {result}")

            logger.info(f"✅ 获取到 JobId: {job_id}")
            return job_id

    @staticmethod
    def parse_query_result(
        status_result: Dict[str, Any],
        preferred_model_format: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        解析查询结果，抽取 status / model_url / preview_url

        Returns:
            {"status": str, "model_url": str|None, "preview_url": str|None, "raw": dict}
        """
        response_data = status_result.get("Response", status_result)
        status = (response_data.get("Status") or response_data.get("status") or status_result.get("Status") or status_result.get("status") or "").upper()

        model_url = ""
        preview_url = ""
        model_format = ""

        model_type_order = Hunyuan3DService._pick_model_type_order(preferred_model_format)
        image_types = {"png", "jpg", "jpeg", "webp", "bmp", "gif", "preview"}

        if status in ["SUCCEED", "COMPLETED", "SUCCESS", "DONE"]:
            result_files = response_data.get("ResultFile3Ds", []) or []
            chosen_file: Dict[str, Any] = {}
            files = [f for f in result_files if isinstance(f, dict) and f.get("Url")]
            # 先按明确3D格式优先级选模型文件，避免误选到预览图
            for t in model_type_order:
                hit = next((f for f in files if Hunyuan3DService._result_file_type(f) == t), None)
                if hit:
                    chosen_file = hit
                    model_format = t
                    break

            # 兜底：选择非图片类型的文件
            if not chosen_file:
                hit = next(
                    (
                        f
                        for f in files
                        if Hunyuan3DService._result_file_type(f) not in image_types and Hunyuan3DService._result_file_type(f) != "zip"
                    ),
                    None,
                )
                if hit:
                    chosen_file = hit
                    model_format = Hunyuan3DService._result_file_type(hit)

            if not chosen_file:
                hit = next((f for f in files if Hunyuan3DService._result_file_type(f) not in image_types), None)
                if hit:
                    chosen_file = hit
                    model_format = Hunyuan3DService._result_file_type(hit)

            if chosen_file:
                model_url = chosen_file.get("Url", "")
                preview_url = chosen_file.get("PreviewImageUrl", "")

            if not preview_url:
                # 从结果中找可用预览图
                preview_file = next((f for f in files if Hunyuan3DService._result_file_type(f) in image_types), None)
                preview_url = (
                    (chosen_file.get("PreviewImageUrl", "") if chosen_file else "")
                    or (preview_file.get("Url", "") if preview_file else "")
                    or model_url
                )

        return {
            "status": status or "UNKNOWN",
            "model_url": model_url or None,
            "preview_url": preview_url or None,
            "model_format": model_format or None,
            "raw": status_result,
        }

    
    @staticmethod
    async def text_to_3d(
        prompt: str,
        model_type: str = "pro",
        with_texture: bool = True,
        generation_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        文生3D：通过文本描述生成3D模型
        
        Args:
            prompt: 文本描述
            model_type: 模型类型，"pro"（专业版）或 "rapid"（极速版）
            with_texture: 是否生成纹理
        
        Returns:
            生成结果字典，包含 model_url, preview_url, credits_used 等
        """
        try:
            # 注意：根据官方 OpenAI 兼容接口示例：
            # base_url: https://api.ai3d.cloud.tencent.com
            # 提交接口: POST /v1/ai3d/submit  Body: { "Prompt": "小狗" }
            # 查询接口: POST /v1/ai3d/query   Body: { "JobId": "xxxx" }
            # 参考文档：https://cloud.tencent.com/document/product/1804/126189

            request_body = {
                "Prompt": prompt
            }
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    # 文档示例直接使用 Authorization: sk-XXXX
                    "Authorization": Config.HUNYUAN3D_API_KEY,
                    "Content-Type": "application/json"
                }
                
                url = f"{Config.HUNYUAN3D_BASE_URL}/v1/ai3d/submit"
                
                logger.info(
                    f"调用混元生3D文生3D接口: url={url}, prompt={prompt[:50]}..., "
                    f"with_texture={with_texture}"
                )
                result = await Hunyuan3DService._submit_job_with_texture_fallback(
                    session=session,
                    url=url,
                    headers=headers,
                    base_body=request_body,
                    with_texture=with_texture,
                    generation_params=generation_params,
                )
                # 腾讯云API返回格式：{"Response": {"JobId": "..."}}
                response_data = result.get("Response", result)
                job_id = response_data.get("JobId") or response_data.get("job_id") or result.get("JobId") or result.get("job_id")
                if not job_id:
                    raise Exception(f"未返回 JobId，返回内容: {result}")
                
                logger.info(f"✅ 获取到 JobId: {job_id}")
                
                # 轮询任务状态（最多等待5分钟）
                max_attempts = 60
                for attempt in range(max_attempts):
                    await asyncio.sleep(5)  # 每5秒查询一次
                    
                    status_result = await Hunyuan3DService._query_job_status(job_id)
                    # 腾讯云API返回格式：{"Response": {"Status": "...", "ResultFile3Ds": [...]}}
                    response_data = status_result.get("Response", status_result)
                    status = (response_data.get("Status") or response_data.get("status") or status_result.get("Status") or status_result.get("status") or "").upper()
                    logger.info(f"查询任务状态 job_id={job_id}, status={status}, resp={status_result}")
                    
                    # 约定：Status 为 SUCCEED / COMPLETED / SUCCESS / DONE 视为成功
                    if status in ["SUCCEED", "COMPLETED", "SUCCESS", "DONE"]:
                        # 从 ResultFile3Ds 数组中提取 GLB 文件（优先）或 OBJ 文件
                        result_files = response_data.get("ResultFile3Ds", []) or []
                        model_url = ""
                        preview_url = ""
                        
                        preferred_format = (
                            generation_params.get("ResultFormat")
                            if isinstance(generation_params, dict)
                            else None
                        )
                        model_type_order = Hunyuan3DService._pick_model_type_order(preferred_format)
                        for t in model_type_order:
                            hit = next((f for f in result_files if isinstance(f, dict) and Hunyuan3DService._result_file_type(f) == t), None)
                            if hit:
                                model_url = hit.get("Url", "")
                                preview_url = hit.get("PreviewImageUrl", "") or model_url
                                model_format = t
                                break
                        
                        # 如果没有 GLB，使用第一个文件
                        if not model_url and result_files:
                            first_file = result_files[0] if isinstance(result_files[0], dict) else {}
                            model_url = first_file.get("Url", "")
                            preview_url = first_file.get("PreviewImageUrl", "") or model_url
                        
                        if not model_url:
                            logger.warning(f"未找到模型文件 URL，result_files={result_files}")
                            continue  # 继续轮询，可能文件还在生成中
                        
                        logger.info(f"✅ 生成成功: model_url={model_url[:80]}..., preview_url={preview_url[:80]}...")
                        parsed_result = Hunyuan3DService.parse_query_result(
                            status_result,
                            preferred_model_format=preferred_format,
                        )
                        return {
                            "model_url": parsed_result.get("model_url") or model_url,
                            "preview_url": parsed_result.get("preview_url") or preview_url,
                            "model_format": parsed_result.get("model_format") or model_format,
                            "raw": status_result,
                            "credits_used": 10,
                            "job_id": job_id,
                        }
                    # 失败状态
                    if status in ["FAILED", "FAIL", "ERROR"]:
                        raise Exception(f"生成失败: {status_result}")
                
                raise Exception("生成超时，请稍后重试或在任务列表中查询状态")
        
        except Exception as e:
            logger.error(f"文生3D失败: {str(e)}")
            raise
    
    @staticmethod
    async def image_to_3d(
        image_base64: str,
        model_type: str = "pro",
        with_texture: bool = True,
        prompt: Optional[str] = None,
        generation_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        图生3D：通过上传图片生成3D模型
        
        Args:
            image_base64: Base64编码的图片数据（包含data:image/...前缀）
            model_type: 模型类型，"pro"（专业版）或 "rapid"（极速版）
            with_texture: 是否生成纹理
            prompt: 可选的文本描述（辅助生成）
        
        Returns:
            生成结果字典，包含 model_url, preview_url, credits_used 等
        """
        try:
            # 腾讯云混元3D API 支持两种方式：
            # 1. ImageUrl: 需要公网可访问的HTTPS URL（腾讯云可能无法访问内网地址）
            # 2. ImageBase64: 直接传递Base64编码的图片数据（推荐，更可靠）
            # 这里使用ImageBase64方式，避免URL访问问题
            encoded, image_format = Hunyuan3DService._extract_image_base64_payload(image_base64)
            
            logger.info(f"图生3D使用Base64方式: image_format={image_format}, base64_len={len(encoded)}")
            
            # 构建请求体 - 使用ImageBase64而不是ImageUrl
            # 注意：腾讯云API不允许同时传递Prompt和ImageBase64/ImageUrl
            # 图生3D时只传递ImageBase64，不传递Prompt
            request_body: Dict[str, Any] = {
                "ImageBase64": encoded,
                "ImageFormat": image_format,
            }
            # 图生3D不支持Prompt参数，如果用户提供了prompt，记录日志但不传递
            if prompt:
                logger.info(f"⚠️  图生3D不支持Prompt参数，已忽略用户提供的prompt: {prompt[:50]}")
            
            logger.info(f"图生3D请求参数: ImageBase64长度={len(encoded)}, prompt={prompt[:50] if prompt else 'N/A'}")
            logger.info(f"图生3D完整请求体（前200字符）: {json.dumps({**request_body, 'ImageBase64': request_body.get('ImageBase64', '')[:50] + '...' if request_body.get('ImageBase64') else ''}, ensure_ascii=False)[:200]}...")
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": Config.HUNYUAN3D_API_KEY,
                    "Content-Type": "application/json"
                }
                
                url = f"{Config.HUNYUAN3D_BASE_URL}/v1/ai3d/submit"
                
                logger.info(
                    f"调用混元生3D图生3D接口: url={url}, headers={headers.get('Authorization')[:20]}..., "
                    f"with_texture={with_texture}"
                )
                result = await Hunyuan3DService._submit_job_with_texture_fallback(
                    session=session,
                    url=url,
                    headers=headers,
                    base_body=request_body,
                    with_texture=with_texture,
                    generation_params=generation_params,
                )
                # 腾讯云API返回格式：{"Response": {"JobId": "..."}}
                response_data = result.get("Response", result)
                job_id = response_data.get("JobId") or response_data.get("job_id") or result.get("JobId") or result.get("job_id")
                if not job_id:
                    raise Exception(f"未返回 JobId，返回内容: {result}")
                
                logger.info(f"✅ 获取到 JobId: {job_id}")
                
                # 轮询任务状态（最多等待5分钟）
                max_attempts = 60
                for attempt in range(max_attempts):
                    await asyncio.sleep(5)  # 每5秒查询一次
                    
                    status_result = await Hunyuan3DService._query_job_status(job_id)
                    # 腾讯云API返回格式：{"Response": {"Status": "...", "ResultFile3Ds": [...]}}
                    response_data = status_result.get("Response", status_result)
                    status = (response_data.get("Status") or response_data.get("status") or status_result.get("Status") or status_result.get("status") or "").upper()
                    logger.info(f"查询图生3D任务状态 job_id={job_id}, status={status}, resp={status_result}")
                    
                    if status in ["SUCCEED", "COMPLETED", "SUCCESS", "DONE"]:
                        # 从 ResultFile3Ds 数组中提取 GLB 文件（优先）或 OBJ 文件
                        result_files = response_data.get("ResultFile3Ds", []) or []
                        model_url = ""
                        preview_url = ""
                        
                        preferred_format = (
                            generation_params.get("ResultFormat")
                            if isinstance(generation_params, dict)
                            else None
                        )
                        model_type_order = Hunyuan3DService._pick_model_type_order(preferred_format)
                        for t in model_type_order:
                            hit = next((f for f in result_files if isinstance(f, dict) and Hunyuan3DService._result_file_type(f) == t), None)
                            if hit:
                                model_url = hit.get("Url", "")
                                preview_url = hit.get("PreviewImageUrl", "") or model_url
                                model_format = t
                                break
                        
                        # 如果没有 GLB，使用第一个文件
                        if not model_url and result_files:
                            first_file = result_files[0] if isinstance(result_files[0], dict) else {}
                            model_url = first_file.get("Url", "")
                            preview_url = first_file.get("PreviewImageUrl", "") or model_url
                        
                        if not model_url:
                            logger.warning(f"未找到模型文件 URL，result_files={result_files}")
                            continue  # 继续轮询，可能文件还在生成中
                        
                        logger.info(f"✅ 图生3D成功: model_url={model_url[:80]}..., preview_url={preview_url[:80]}...")
                        parsed_result = Hunyuan3DService.parse_query_result(
                            status_result,
                            preferred_model_format=preferred_format,
                        )
                        return {
                            "model_url": parsed_result.get("model_url") or model_url,
                            "preview_url": parsed_result.get("preview_url") or preview_url,
                            "model_format": parsed_result.get("model_format") or model_format,
                            "raw": status_result,
                            "credits_used": 10,
                            "job_id": job_id,
                        }
                    if status in ["FAILED", "FAIL", "ERROR"]:
                        raise Exception(f"生成失败: {status_result}")
                
                raise Exception("生成超时，请稍后重试或在任务列表中查询状态")
        
        except Exception as e:
            logger.error(f"图生3D失败: {str(e)}")
            raise
    
    @staticmethod
    async def _query_job_status(job_id: str) -> Dict[str, Any]:
        """
        查询任务状态（内部方法）
        
        Args:
            job_id: 任务ID
        
        Returns:
            任务状态字典
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": Config.HUNYUAN3D_API_KEY,
                    "Content-Type": "application/json"
                }
                
                url = f"{Config.HUNYUAN3D_BASE_URL}/v1/ai3d/query"
                
                async with session.post(url, json={"JobId": job_id}, headers=headers) as response:
                    text = await response.text()
                    if response.status == 200:
                        result = json.loads(text) if text else {}
                        # 腾讯云API返回格式：{"Response": {"Status": "...", ...}}
                        # 直接返回完整结果，让调用方处理
                        return result
                    else:
                        logger.error(f"查询任务状态失败: status={response.status}, error={text}")
                        return {"Response": {"Status": "failed", "Error": text}}
        except Exception as e:
            logger.error(f"查询任务状态异常: {str(e)}")
            return {"status": "failed", "error": str(e)}


# 导出
__all__ = ["Hunyuan3DService"]
