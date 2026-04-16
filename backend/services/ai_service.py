"""
AI服务模块
包含AI模型生成等功能
"""

from typing import Dict, Any, Optional
from logger import logger
from database import DatabaseManager
from services.hunyuan3d import Hunyuan3DService
from services.aliyun_bailian import AliyunBailianService
from config import Config


class AIService:
    """AI服务类"""
    
    @staticmethod
    async def generate_3d_model(
        prompt: str,
        lora: Optional[str] = None,
        model_config_id: Optional[str] = None,
        db: Optional[DatabaseManager] = None,
        seed: Optional[int] = None,
        with_texture: bool = True,
        generation_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成3D模型（文生3D）
        
        Args:
            prompt: 提示词
            lora: LoRA ID（风格模型，可选）
            model_config_id: 模型配置ID（可选）
            db: 数据库管理器（可选）
            seed: 随机种子（可选）
        
        Returns:
            生成结果字典
        """
        logger.info(f"开始生成3D模型: prompt={prompt[:50]}..., lora={lora}")
        
        try:
            # 使用腾讯混元生3D服务
            # lora参数映射到模型类型：clay/mecha/anime -> pro, 其他 -> rapid
            model_type = "pro" if lora and lora in ["clay", "mecha", "anime"] else Config.HUNYUAN3D_DEFAULT_MODEL
            
            result = await Hunyuan3DService.text_to_3d(
                prompt=prompt,
                model_type=model_type,
                with_texture=with_texture,
                generation_params=generation_params
            )
            
            # 添加额外的元数据
            result["seed"] = seed or 12345
            result["steps"] = 20
            result["sampler"] = "euler_a"
            
            logger.info(f"3D模型生成完成: {result.get('model_url', 'N/A')}")
            return result
        
        except Exception as e:
            logger.error(f"调用混元生3D失败: {str(e)}")
            # 不再返回模拟数据，直接抛出异常，让前端显示错误信息
            raise Exception(f"3D模型生成失败: {str(e)}")
    
    @staticmethod
    async def image_to_3d_model(
        image_base64: str,
        lora: Optional[str] = None,
        prompt: Optional[str] = None,
        model_config_id: Optional[str] = None,
        db: Optional[DatabaseManager] = None,
        with_texture: bool = True,
        generation_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        图生3D：通过上传图片生成3D模型
        
        Args:
            image_base64: Base64编码的图片数据
            lora: LoRA ID（风格模型，可选）
            prompt: 可选的文本描述（辅助生成）
            model_config_id: 模型配置ID（可选）
            db: 数据库管理器（可选）
        
        Returns:
            生成结果字典
        """
        logger.info(f"开始图生3D: image_size={len(image_base64)}, prompt={prompt[:50] if prompt else 'N/A'}...")
        
        try:
            # 使用腾讯混元生3D服务
            model_type = "pro" if lora in ["clay", "mecha", "anime"] else Config.HUNYUAN3D_DEFAULT_MODEL
            
            result = await Hunyuan3DService.image_to_3d(
                image_base64=image_base64,
                model_type=model_type,
                with_texture=with_texture,
                prompt=prompt,
                generation_params=generation_params
            )
            
            logger.info(f"图生3D完成: {result.get('model_url', 'N/A')}")
            return result
        
        except Exception as e:
            logger.error(f"调用混元生3D失败: {str(e)}")
            # 不再返回模拟数据，直接抛出异常，让前端显示错误信息
            raise Exception(f"图生3D失败: {str(e)}")
    
    @staticmethod
    async def generate_image(
        prompt: str,
        model_config_id: Optional[str] = None,
        size: str = "1024x1024",
        quality: str = "standard",
        db: Optional[DatabaseManager] = None
    ) -> Dict[str, Any]:
        """
        文生图：通过文本提示词生成图片
        
        Args:
            prompt: 提示词
            model_config_id: 模型配置ID（可选，用于指定不同的模型）
            size: 图片尺寸，默认 1024x1024
            quality: 图片清晰度，standard/hd
            db: 数据库管理器（可选）
        
        Returns:
            生成结果字典
        """
        logger.info(f"开始文生图: prompt={prompt[:50]}..., model_config_id={model_config_id}, quality={quality}")
        
        try:
            # 使用阿里云百炼 wan2.6-t2i 模型
            result = await AliyunBailianService.text_to_image(
                prompt=prompt,
                model=Config.ALIYUN_BAILIAN_T2I_MODEL,
                size=size,
                quality=quality
            )
            result["quality_used"] = quality
            
            logger.info(f"文生图完成: {result.get('image_url', 'N/A')}")
            return result
        
        except Exception as e:
            # 部分环境下上游对高清参数支持不稳定，失败时回退标准清晰度。
            if quality != "standard":
                logger.warning(f"高清质量调用失败，回退标准清晰度重试: {str(e)}")
                try:
                    fallback_result = await AliyunBailianService.text_to_image(
                        prompt=prompt,
                        model=Config.ALIYUN_BAILIAN_T2I_MODEL,
                        size=size,
                        quality="standard"
                    )
                    fallback_result["quality_used"] = "standard"
                    fallback_result["quality_fallback_note"] = "高清模式暂不可用，已自动回退为标准清晰度"
                    return fallback_result
                except Exception as retry_e:
                    logger.error(f"高清回退标准清晰度仍失败: {str(retry_e)}")
                    raise Exception(f"文生图失败: {str(retry_e)}")

            logger.error(f"调用阿里云百炼文生图失败: {str(e)}")
            raise Exception(f"文生图失败: {str(e)}")

    @staticmethod
    async def translate_text(
        text: str,
        target_lang: str = "en",
        source_lang: str = "auto",
    ) -> Dict[str, Any]:
        """
        翻译提示词文本（中英互译）
        """
        logger.info(
            f"开始翻译文本: source_lang={source_lang}, target_lang={target_lang}, len={len(text or '')}"
        )
        try:
            return await AliyunBailianService.translate_text(
                text=text,
                target_lang=target_lang,
                source_lang=source_lang,
            )
        except Exception as e:
            logger.error(f"调用阿里云百炼翻译失败: {str(e)}")
            raise Exception(f"翻译失败: {str(e)}")

    @staticmethod
    async def optimize_prompt(
        text: str,
        mode: str = "text2image",
        source_lang: str = "auto",
    ) -> Dict[str, Any]:
        """
        优化造梦提示词，返回更适合当前生成模式的版本。
        """
        logger.info(
            f"开始优化提示词: mode={mode}, source_lang={source_lang}, len={len(text or '')}"
        )
        try:
            return await AliyunBailianService.optimize_prompt(
                text=text,
                mode=mode,
                source_lang=source_lang,
            )
        except Exception as e:
            logger.error(f"调用阿里云百炼提示词优化失败: {str(e)}")
            raise Exception(f"提示词优化失败: {str(e)}")


# 导出
__all__ = ["AIService"]
