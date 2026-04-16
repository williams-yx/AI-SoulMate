"""
配置管理模块
统一管理应用配置
"""

import os
from pathlib import Path
from typing import Optional

# 本地运行时从项目根目录加载 .env（Docker 下由 env_file 注入，可不依赖此文件）
# 服务器专用覆盖配置放在 backend/.env.server.local，避免被 get-develop.sh reset --hard 覆盖。
try:
    from dotenv import load_dotenv
    _config_dir = Path(__file__).resolve().parent
    _root_env_path = _config_dir.parent / ".env"
    _server_override_path = _config_dir / ".env.server.local"

    if _root_env_path.exists():
        load_dotenv(_root_env_path)
    if _server_override_path.exists():
        load_dotenv(_server_override_path, override=True)
except ImportError:
    pass

from logger import logger


class Config:
    """应用配置类"""
    
    # 数据库配置
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@localhost:5432/ai_soulmate"
    )
    
    # Redis配置
    REDIS_URL: str = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0"
    )
    
    # 安全配置
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "your-secret-key-here-change-in-production"
    )
    ALGORITHM: str = "HS256"
    # 前端按「无操作 15 分钟」登出；JWT 为会话绝对上限（默认 24h），避免持续操作时 15 分钟一到就被后端拒掉
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    # 后端 Redis 滑动会话窗口（秒），与前端 IDLE 一致；任意受保护 API 会刷新 TTL
    SESSION_IDLE_SECONDS: int = int(os.getenv("SESSION_IDLE_SECONDS", str(15 * 60)))
    
    # 文件存储配置
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # 微信配置
    WECHAT_APPID: str = os.getenv("WECHAT_APPID", "your-wechat-appid")
    WECHAT_SECRET: str = os.getenv("WECHAT_SECRET", "your-wechat-secret")
    
    # GitHub OAuth 配置
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    # 换票失败或开发兜底时写入 user_identities 的占位 identifier（须绑定与登录共用同一串）。
    # 若用「每次 OAuth code 前 12 位」则绑定与下次 GitHub 登录永不同步，会像两个账号。
    DEV_GITHUB_OAUTH_IDENTITY: str = (
        (os.getenv("DEV_GITHUB_OAUTH_IDENTITY", "dev_github_local_oauth_user") or "dev_github_local_oauth_user").strip()
    )
    
    # API Key 加密密钥
    ENCRYPTION_KEY: str = os.getenv(
        "ENCRYPTION_KEY",
        "default-encryption-key-change-in-production"
    )

    # CDK 兑换码哈希盐
    CDK_CODE_PEPPER: str = os.getenv("CDK_CODE_PEPPER", "")
    
    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # 邮箱验证码（发件用，不配置则仅记录日志不真实发信）
    EMAIL_CODE_EXPIRE_SECONDS: int = 900  # 15 分钟
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "465"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "")  # 发件邮箱，通常与 SMTP_USER 一致
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")

    # 手机验证码（短信）；不配置则仅存服务端，接口返回 code 供测试
    SMS_PHONE_CODE_EXPIRE_SECONDS: int = 300  # 5 分钟
    # 阿里云短信（可选）：开通短信服务、申请签名与模板后配置
    ALIYUN_ACCESS_KEY_ID: str = os.getenv("ALIYUN_ACCESS_KEY_ID", "")
    ALIYUN_ACCESS_KEY_SECRET: str = os.getenv("ALIYUN_ACCESS_KEY_SECRET", "")
    SMS_SIGN_NAME: str = os.getenv("SMS_SIGN_NAME", "")
    SMS_TEMPLATE_CODE: str = os.getenv("SMS_TEMPLATE_CODE", "")
    
    # 阿里云 OSS (模型与生成文件的对象存储)
    OSS_ENDPOINT: str = os.getenv("OSS_ENDPOINT", "")
    OSS_BUCKET_NAME: str = os.getenv("OSS_BUCKET_NAME", "")

    # 打印执行端配置
    PRINT_CLIENT_SHARED_TOKEN: str = os.getenv("PRINT_CLIENT_SHARED_TOKEN", "")
    PRINT_DEFAULT_TARGET_CLIENT_ID: str = os.getenv(
        "PRINT_DEFAULT_TARGET_CLIENT_ID",
        "",
    )
    PRINT_ALLOWED_CLIENT_ID: str = os.getenv(
        "PRINT_ALLOWED_CLIENT_ID",
        os.getenv("PRINT_DEFAULT_TARGET_CLIENT_ID", "mlkj-mac-u1") or "mlkj-mac-u1",
    )

    # 切片配置
    PRINT_SLICER_CMD_TEMPLATE: str = os.getenv("PRINT_SLICER_CMD_TEMPLATE", "")
    PRINT_SLICER_TIMEOUT_SECONDS: int = int(
        os.getenv("PRINT_SLICER_TIMEOUT_SECONDS", "900")
    )
    PRINT_ENABLE_MOCK_SLICER: bool = os.getenv(
        "PRINT_ENABLE_MOCK_SLICER",
        "false",
    ).lower() in ("1", "true", "yes")
    PRINT_SLICER_RESULT_FILE_NAME: str = os.getenv(
        "PRINT_SLICER_RESULT_FILE_NAME",
        "slice-result.json",
    )
    PRINT_ORCA_SLICER_BINARY: str = os.getenv(
        "PRINT_ORCA_SLICER_BINARY",
        "snapmaker-orca",
    )
    PRINT_ORCA_CMD_TEMPLATE: str = os.getenv("PRINT_ORCA_CMD_TEMPLATE", "")
    PRINT_ORCA_PRINTER_PROFILE: str = os.getenv("PRINT_ORCA_PRINTER_PROFILE", "")
    PRINT_ORCA_MATERIAL_PROFILE_MAP: str = os.getenv(
        "PRINT_ORCA_MATERIAL_PROFILE_MAP",
        "{}",
    )
    PRINT_ORCA_HEIGHT_PROFILE_MAP: str = os.getenv(
        "PRINT_ORCA_HEIGHT_PROFILE_MAP",
        "{}",
    )
    PRINT_ORCA_EXTRA_ARGS: str = os.getenv("PRINT_ORCA_EXTRA_ARGS", "")
    PRINT_ORCA_TOOL_COMMAND_MAP: str = os.getenv(
        "PRINT_ORCA_TOOL_COMMAND_MAP",
        "{}",
    )
    PRINT_ORCA_DEFAULT_TOOL_COMMAND: str = os.getenv(
        "PRINT_ORCA_DEFAULT_TOOL_COMMAND",
        "",
    )
    PRINT_ORCA_BOTTOM_SURFACE_PATTERN: str = os.getenv(
        "PRINT_ORCA_BOTTOM_SURFACE_PATTERN",
        "",
    )
    PRINT_ORCA_TOP_SURFACE_PATTERN: str = os.getenv(
        "PRINT_ORCA_TOP_SURFACE_PATTERN",
        "",
    )
    PRINT_ORCA_BOTTOM_SHELL_LAYERS: str = os.getenv(
        "PRINT_ORCA_BOTTOM_SHELL_LAYERS",
        "",
    )
    PRINT_ORCA_INITIAL_LAYER_LINE_WIDTH: str = os.getenv(
        "PRINT_ORCA_INITIAL_LAYER_LINE_WIDTH",
        "",
    )
    PRINT_ORCA_SUPPORT_INTERFACE_SPACING: str = os.getenv(
        "PRINT_ORCA_SUPPORT_INTERFACE_SPACING",
        "",
    )
    PRINT_ORCA_SUPPORT_BASE_PATTERN_SPACING: str = os.getenv(
        "PRINT_ORCA_SUPPORT_BASE_PATTERN_SPACING",
        "",
    )
    PRINT_ORCA_SUPPORT_SPEED: str = os.getenv(
        "PRINT_ORCA_SUPPORT_SPEED",
        "",
    )
    PRINT_ORCA_TREE_SUPPORT_WITH_INFILL: str = os.getenv(
        "PRINT_ORCA_TREE_SUPPORT_WITH_INFILL",
        "",
    )
    
    # 腾讯混元生3D配置
    HUNYUAN3D_API_KEY: str = os.getenv(
        "HUNYUAN3D_API_KEY",
        ""
    )
    # 参考官方文档：https://cloud.tencent.com/document/product/1804/126189
    # OpenAI 兼容接口 base_url
    HUNYUAN3D_BASE_URL: str = os.getenv(
        "HUNYUAN3D_BASE_URL",
        "https://api.ai3d.cloud.tencent.com"
    )
    HUNYUAN3D_MODEL_PRO: str = os.getenv(
        "HUNYUAN3D_MODEL_PRO",
        "hunyuan-3d-pro-3.1"
    )
    HUNYUAN3D_MODEL_RAPID: str = os.getenv(
        "HUNYUAN3D_MODEL_RAPID",
        "hunyuan-3d-rapid"
    )
    HUNYUAN3D_DEFAULT_MODEL: str = os.getenv(
        "HUNYUAN3D_DEFAULT_MODEL",
        "pro"
    )

    # Studio 模型代理允许的域名后缀（以逗号分隔），用于限定可被后端代理的外部资源域名
    # 可通过环境变量 STUDIO_PROXY_ALLOWED_SUFFIXES 覆盖，示例：
    # "tencentcos.cn,cos.ap-,myqcloud.com,aliyuncs.com,cloud.tencent.com"
    STUDIO_PROXY_ALLOWED_SUFFIXES: str = os.getenv(
        "STUDIO_PROXY_ALLOWED_SUFFIXES",
        "tencentcos.cn,cos.ap-,myqcloud.com,aliyuncs.com"
    )
    
    # 阿里云百炼平台配置
    ALIYUN_BAILIAN_API_KEY: str = os.getenv(
        "ALIYUN_BAILIAN_API_KEY",
        ""
    )
    # 阿里云百炼 API base_url
    # 标准API接口：https://dashscope.aliyuncs.com/api/v1
    # OpenAI兼容接口：https://dashscope.aliyuncs.com/compatible-mode/v1
    ALIYUN_BAILIAN_BASE_URL: str = os.getenv(
        "ALIYUN_BAILIAN_BASE_URL",
        "https://dashscope.aliyuncs.com/api/v1"  # 使用标准API接口
    )
    # 文生图模型名称
    # 根据阿里云百炼官方文档，模型名称可能是 wan2.6-t2i 或 wanx-v2.6-t2i
    # 请根据控制台实际显示的模型名称调整
    ALIYUN_BAILIAN_T2I_MODEL: str = os.getenv(
        "ALIYUN_BAILIAN_T2I_MODEL",
        "wan2.6-t2i"  # 尝试使用原始模型名称
    )
    # 阿里云百炼文本模型（用于提示词翻译）
    ALIYUN_BAILIAN_TEXT_MODEL: str = os.getenv(
        "ALIYUN_BAILIAN_TEXT_MODEL",
        "qwen-plus"
    )
    
    @classmethod
    def validate(cls) -> bool:
        """
        验证配置是否有效
        
        Returns:
            配置是否有效
        """
        errors = []
        
        if cls.SECRET_KEY == "your-secret-key-here-change-in-production":
            errors.append("SECRET_KEY 未设置，请使用环境变量设置")
        
        if cls.ENCRYPTION_KEY == "default-encryption-key-change-in-production":
            errors.append("ENCRYPTION_KEY 未设置，请使用环境变量设置")
        
        if errors:
            logger.warning("配置验证警告:")
            for error in errors:
                logger.warning(f"  - {error}")
            return False
        
        return True


# 导出
__all__ = ["Config"]
