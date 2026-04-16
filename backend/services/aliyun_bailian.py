"""
阿里云百炼平台服务模块
用于调用阿里云百炼平台的文生图等API
"""

import json
import aiohttp
import asyncio
from typing import Dict, Any, Optional
from logger import logger
from config import Config


class AliyunBailianService:
    """阿里云百炼平台服务类"""

    @staticmethod
    def _normalize_base_url() -> str:
        base_url = (Config.ALIYUN_BAILIAN_BASE_URL or "").strip().rstrip("/")
        if not base_url:
            return "https://dashscope.aliyuncs.com/api/v1"
        if base_url.startswith("http://") or base_url.startswith("https://"):
            return base_url
        return f"https://{base_url}"

    @staticmethod
    def _standard_api_base() -> str:
        base_url = AliyunBailianService._normalize_base_url()
        if base_url.endswith("/compatible-model/v1"):
            return base_url[: -len("/compatible-model/v1")] + "/api/v1"
        if base_url.endswith("/compatible-mode/v1"):
            return base_url[: -len("/compatible-mode/v1")] + "/api/v1"
        if base_url.endswith("/api/v1"):
            return base_url
        return f"{base_url}/api/v1"

    @staticmethod
    def _compatible_api_base() -> str:
        base_url = AliyunBailianService._normalize_base_url()
        if base_url.endswith("/compatible-model/v1") or base_url.endswith("/compatible-mode/v1"):
            return base_url
        if base_url.endswith("/api/v1"):
            root = base_url[: -len("/api/v1")]
        else:
            root = base_url
        if ".maas.aliyuncs.com" in root:
            return f"{root}/compatible-model/v1"
        if "dashscope.aliyuncs.com" in root:
            return f"{root}/compatible-mode/v1"
        return f"{root}/compatible-model/v1"
    
    @staticmethod
    async def text_to_image(
        prompt: str,
        model: str = "wanx-v2.6-t2i",
        size: str = "1024x1024",
        n: int = 1,
        quality: str = "standard"
    ) -> Dict[str, Any]:
        """
        文生图：通过文本提示词生成图片
        
        Args:
            prompt: 文本提示词
            model: 模型名称，默认 wan2.6-t2i
            size: 图片尺寸，可选 "1024x1024", "1024x768", "768x1024" 等
            n: 生成图片数量，默认 1
            quality: 图片质量，可选 "standard" 或 "hd"
        
        Returns:
            生成结果字典，包含 image_url, preview_url, credits_used 等
        """
        try:
            # 阿里云百炼文生图API端点
            # 根据阿里云百炼官方文档（北京地域）：
            # POST https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation
            standard_base = AliyunBailianService._standard_api_base()
            
            # 使用正确的多模态生成端点
            url = f"{standard_base}/services/aigc/multimodal-generation/generation"
            
            # 阿里云百炼多模态生成API请求格式
            # 根据官方文档，multimodal-generation端点需要 input.messages 字段
            # size格式需要是 "width*height"（用星号），而不是 "widthxheight"
            # 将 "1024x1024" 转换为 "1024*1024"
            size_formatted = size.replace("x", "*") if "x" in size else size
            
            # 多模态生成API的请求格式：input.messages 是必需字段
            request_body = {
                "model": model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ]
                },
                "parameters": {
                    "size": size_formatted,
                    "n": n,
                    "quality": quality
                }
            }
            
            logger.info(f"使用阿里云百炼多模态生成API接口: {url}")
            
            logger.info(f"调用阿里云百炼文生图接口: url={url}, model={model}, prompt={prompt[:50]}...")
            logger.info(f"请求体: {json.dumps(request_body, ensure_ascii=False)[:200]}...")
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {Config.ALIYUN_BAILIAN_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                async with session.post(url, json=request_body, headers=headers) as response:
                    text = await response.text()
                    logger.info(f"阿里云百炼文生图返回: status={response.status}, body={text}")
                    
                    if response.status != 200:
                        # 记录完整的错误信息
                        error_msg = f"API调用失败: status={response.status}, body={text}"
                        logger.error(error_msg)
                        raise Exception(error_msg)
                    
                    result = json.loads(text) if text else {}
                    
                    logger.info(f"解析API返回结果: {json.dumps(result, ensure_ascii=False)[:500]}...")
                    
                    # 处理阿里云百炼多模态生成API返回格式
                    # 实际返回格式：
                    # {
                    #   "output": {
                    #     "choices": [{
                    #       "message": {
                    #         "content": [{
                    #           "image": "https://...",
                    #           "type": "image"
                    #         }]
                    #       }
                    #     }],
                    #     "finished": true
                    #   }
                    # }
                    
                    # 优先检查是否有直接返回的结果
                    if "output" in result:
                        output = result.get("output", {})
                        
                        # 检查是否有 choices 格式（多模态生成API）
                        if "choices" in output:
                            choices = output.get("choices", [])
                            if choices and len(choices) > 0:
                                message = choices[0].get("message", {})
                                content = message.get("content", [])
                                if content and len(content) > 0:
                                    # 查找图片类型的content
                                    for item in content:
                                        if item.get("type") == "image":
                                            image_url = item.get("image", "")
                                            if image_url:
                                                logger.info(f"✅ 文生图成功: image_url={image_url[:80]}...")
                                                return {
                                                    "image_url": image_url,
                                                    "preview_url": image_url,
                                                    "credits_used": 20,
                                                    "revised_prompt": prompt
                                                }
                                    raise Exception("未找到图片内容")
                                else:
                                    raise Exception("content为空")
                            else:
                                raise Exception("choices为空")
                        
                        # 兼容旧格式：results 格式
                        elif "results" in output:
                            results = output.get("results", [])
                            if results and len(results) > 0:
                                image_url = results[0].get("url", "")
                                revised_prompt = results[0].get("revised_prompt", prompt)
                                
                                if not image_url:
                                    raise Exception("未返回图片URL")
                                
                                logger.info(f"✅ 文生图成功: image_url={image_url[:80]}...")
                                return {
                                    "image_url": image_url,
                                    "preview_url": image_url,
                                    "credits_used": 20,
                                    "revised_prompt": revised_prompt
                                }
                        else:
                            raise Exception(f"未知的返回格式: {output}")
                    
                    # 处理异步任务接口返回
                    elif "task_id" in result:
                        # 异步任务接口返回格式：
                        # {
                        #   "task_id": "...",
                        #   "task_status": "PENDING",
                        #   ...
                        # }
                        task_id = result.get("task_id")
                        task_status = result.get("task_status", "PENDING")
                        
                        logger.info(f"获取到任务ID: {task_id}, 状态: {task_status}")
                        
                        # 如果任务已完成，直接返回结果
                        if task_status == "SUCCEEDED" and "output" in result:
                            output = result.get("output", {})
                            results = output.get("results", [])
                            if results and len(results) > 0:
                                image_url = results[0].get("url", "")
                                revised_prompt = results[0].get("revised_prompt", prompt)
                                
                                if not image_url:
                                    raise Exception("未返回图片URL")
                                
                                logger.info(f"✅ 文生图成功: image_url={image_url[:80]}...")
                                return {
                                    "image_url": image_url,
                                    "preview_url": image_url,
                                    "credits_used": 20,
                                    "revised_prompt": revised_prompt
                                }
                        
                        # 如果任务还在处理中，需要轮询
                        if task_status in ["PENDING", "RUNNING"]:
                            # 轮询任务状态（最多等待2分钟）
                            max_attempts = 24
                            for attempt in range(max_attempts):
                                await asyncio.sleep(5)  # 每5秒查询一次
                                
                                # 查询任务状态
                                query_url = f"{standard_base}/tasks/{task_id}"
                                async with session.get(query_url, headers=headers) as query_response:
                                    query_text = await query_response.text()
                                    query_result = json.loads(query_text) if query_text else {}
                                    
                                    query_status = query_result.get("task_status", "")
                                    logger.info(f"查询任务状态 ({attempt+1}/{max_attempts}): task_id={task_id}, status={query_status}")
                                    
                                    if query_status == "SUCCEEDED":
                                        output = query_result.get("output", {})
                                        results = output.get("results", [])
                                        if results and len(results) > 0:
                                            image_url = results[0].get("url", "")
                                            revised_prompt = results[0].get("revised_prompt", prompt)
                                            
                                            if not image_url:
                                                raise Exception("未返回图片URL")
                                            
                                            logger.info(f"✅ 文生图成功: image_url={image_url[:80]}...")
                                            return {
                                                "image_url": image_url,
                                                "preview_url": image_url,
                                                "credits_used": 20,
                                                "revised_prompt": revised_prompt
                                            }
                                    elif query_status in ["FAILED", "CANCELLED"]:
                                        error_msg = query_result.get("message", "未知错误")
                                        raise Exception(f"任务失败: {error_msg}")
                            
                            raise Exception("任务超时，请稍后查询")
                        else:
                            raise Exception(f"任务状态异常: {task_status}")
                    
                    # 处理OpenAI兼容接口返回格式
                    elif "data" in result and len(result["data"]) > 0:
                        image_url = result["data"][0].get("url", "")
                        revised_prompt = result["data"][0].get("revised_prompt", prompt)
                        
                        if not image_url:
                            raise Exception("未返回图片URL")
                        
                        logger.info(f"✅ 文生图成功: image_url={image_url[:80]}...")
                        return {
                            "image_url": image_url,
                            "preview_url": image_url,
                            "credits_used": 20,
                            "revised_prompt": revised_prompt
                        }
                    else:
                        raise Exception(f"返回格式异常: {result}")
        
        except Exception as e:
            logger.error(f"文生图失败: {str(e)}")
            raise

    @staticmethod
    async def translate_text(
        text: str,
        target_lang: str = "en",
        source_lang: str = "auto",
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        文本翻译：调用阿里云百炼兼容 Chat Completions 接口

        Args:
            text: 待翻译文本
            target_lang: 目标语言（en / zh）
            source_lang: 源语言（auto / en / zh）
            model: 可选模型名称，默认使用配置项

        Returns:
            {"translated_text": "..."}
        """
        cleaned = (text or "").strip()
        if not cleaned:
            raise Exception("翻译内容不能为空")
        if len(cleaned) > 5000:
            raise Exception("翻译内容过长，请控制在5000字符以内")

        src = (source_lang or "auto").lower()
        tgt = (target_lang or "en").lower()
        if src not in {"auto", "en", "zh"}:
            raise Exception("source_lang 仅支持 auto/en/zh")
        if tgt not in {"en", "zh"}:
            raise Exception("target_lang 仅支持 en/zh")
        if src != "auto" and src == tgt:
            return {"translated_text": cleaned}

        compatible_base = AliyunBailianService._compatible_api_base()

        url = f"{compatible_base}/chat/completions"
        model_name = model or Config.ALIYUN_BAILIAN_TEXT_MODEL
        language_map = {"en": "English", "zh": "Chinese", "auto": "Auto"}
        source_label = language_map.get(src, "Auto")
        target_label = language_map.get(tgt, "English")

        request_body = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a professional translator. "
                        "Translate the user text accurately and naturally. "
                        "Return translated text only, without explanation or quotes."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Source language: {source_label}\n"
                        f"Target language: {target_label}\n"
                        "Text:\n"
                        f"{cleaned}"
                    ),
                },
            ],
            "temperature": 0.1,
        }

        logger.info(
            f"调用百炼翻译接口: model={model_name}, source={src}, target={tgt}, len={len(cleaned)}"
        )

        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {Config.ALIYUN_BAILIAN_API_KEY}",
                "Content-Type": "application/json",
            }
            async with session.post(url, json=request_body, headers=headers) as response:
                text_body = await response.text()
                logger.info(
                    f"百炼翻译返回: status={response.status}, body={text_body[:300]}"
                )
                if response.status != 200:
                    raise Exception(f"翻译服务调用失败: {response.status}, {text_body}")
                result = json.loads(text_body) if text_body else {}

        choices = result.get("choices") if isinstance(result, dict) else None
        if not choices or not isinstance(choices, list):
            raise Exception(f"翻译服务返回格式异常: {result}")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict):
                    txt = part.get("text")
                    if txt:
                        parts.append(str(txt))
                elif isinstance(part, str):
                    parts.append(part)
            translated = "\n".join(parts).strip()
        else:
            translated = str(content or "").strip()

        if not translated:
            raise Exception("翻译服务未返回有效文本")
        return {"translated_text": translated}

    @staticmethod
    async def optimize_prompt(
        text: str,
        mode: str = "text2image",
        source_lang: str = "auto",
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        使用百炼文本模型优化造梦提示词，保持原语言输出。

        Args:
            text: 原始提示词
            mode: text2image / text23d
            source_lang: auto / zh / en
            model: 可选模型名称，默认使用配置项

        Returns:
            {"optimized_text": "..."}
        """
        cleaned = (text or "").strip()
        if not cleaned:
            raise Exception("提示词不能为空")
        if len(cleaned) > 5000:
            raise Exception("提示词过长，请控制在5000字符以内")

        studio_mode = (mode or "text2image").strip().lower()
        if studio_mode not in {"text2image", "text23d"}:
            raise Exception("mode 仅支持 text2image/text23d")

        src = (source_lang or "auto").lower()
        if src not in {"auto", "en", "zh"}:
            raise Exception("source_lang 仅支持 auto/en/zh")

        compatible_base = AliyunBailianService._compatible_api_base()
        url = f"{compatible_base}/chat/completions"
        model_name = model or Config.ALIYUN_BAILIAN_TEXT_MODEL

        mode_guidance = {
            "text2image": (
                "Optimize the prompt for text-to-image generation. "
                "Make it more vivid, specific, and visually descriptive. "
                "Keep the original subject and intent. "
                "Add useful details like composition, lighting, materials, colors, mood, style, and quality when appropriate. "
                "Do not add safety disclaimers, numbering, or explanation. "
                "Return one polished prompt only."
            ),
            "text23d": (
                "Optimize the prompt for text-to-3D generation. "
                "Focus on a single clear main object or character. "
                "Make shape, silhouette, material, pose, and structural details more explicit. "
                "Prefer details helpful for 3D modeling and printing, and avoid camera instructions, long scene descriptions, and cluttered backgrounds unless the user explicitly asks for them. "
                "Keep the original subject and intent. "
                "Return one polished prompt only."
            ),
        }[studio_mode]

        language_hint = {
            "zh": "Return the optimized prompt in Chinese only.",
            "en": "Return the optimized prompt in English only.",
            "auto": "Return the optimized prompt in the same language as the user's input.",
        }[src]

        request_body = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an expert prompt engineer for AI creative generation. "
                        f"{mode_guidance} "
                        f"{language_hint} "
                        "Do not use markdown, quotes, labels, or explanation."
                    ),
                },
                {
                    "role": "user",
                    "content": cleaned,
                },
            ],
            "temperature": 0.4,
        }

        logger.info(
            f"调用百炼提示词优化接口: model={model_name}, mode={studio_mode}, source={src}, len={len(cleaned)}"
        )

        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {Config.ALIYUN_BAILIAN_API_KEY}",
                "Content-Type": "application/json",
            }
            async with session.post(url, json=request_body, headers=headers) as response:
                text_body = await response.text()
                logger.info(
                    f"百炼提示词优化返回: status={response.status}, body={text_body[:300]}"
                )
                if response.status != 200:
                    raise Exception(f"提示词优化服务调用失败: {response.status}, {text_body}")
                result = json.loads(text_body) if text_body else {}

        choices = result.get("choices") if isinstance(result, dict) else None
        if not choices or not isinstance(choices, list):
            raise Exception(f"提示词优化服务返回格式异常: {result}")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict):
                    txt = part.get("text")
                    if txt:
                        parts.append(str(txt))
                elif isinstance(part, str):
                    parts.append(part)
            optimized = "\n".join(parts).strip()
        else:
            optimized = str(content or "").strip()

        if not optimized:
            raise Exception("提示词优化服务未返回有效文本")
        return {"optimized_text": optimized}


# 导出
__all__ = ["AliyunBailianService"]
