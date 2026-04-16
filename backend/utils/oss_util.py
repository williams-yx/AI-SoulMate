import os
import oss2
import uuid
from typing import Optional
from config import Config
from logger import logger

try:
    from alibabacloud_credentials.client import Client as CredentialClient
    from alibabacloud_credentials.models import Config as CredentialConfig
    HAS_ALICLOUD_CREDENTIALS = True
except ImportError:
    HAS_ALICLOUD_CREDENTIALS = False

class AlibabaCloudCredentialsProvider(oss2.credentials.CredentialsProvider):
    """包装 alibabacloud_credentials 为 OSS2 提供自动刷新的临时凭证（含 IMDSv2 支持）。"""
    def __init__(self, role_name: str = ""):
        config = CredentialConfig(
            type='ecs_ram_role',
            role_name=role_name,
            disable_imds_v1=True  # 采用用户请求中的加固模式
        )
        self.client = CredentialClient(config)

    def get_credentials(self):
        cred = self.client.get_credential()
        return oss2.credentials.Credentials(
            access_key_id=cred.get_access_key_id(),
            access_key_secret=cred.get_access_key_secret(),
            security_token=cred.get_security_token()
        )

class OSSManager:
    def __init__(self):
        self.endpoint = os.getenv("OSS_ENDPOINT", "")
        self.bucket_name = os.getenv("OSS_BUCKET_NAME", "")
        
        self.bucket = None
        if not self.endpoint or not self.bucket_name:
            logger.warning("⚠️ 阿里云 OSS 配置不全 (缺 Endpoint/BucketName)，OSS 功能将被禁用")
            return
            
        access_key_id = os.getenv("ALIYUN_ACCESS_KEY_ID", Config.ALIYUN_ACCESS_KEY_ID)
        access_key_secret = os.getenv("ALIYUN_ACCESS_KEY_SECRET", Config.ALIYUN_ACCESS_KEY_SECRET)
        
        try:
            if access_key_id and access_key_secret:
                auth = oss2.Auth(access_key_id, access_key_secret)
                logger.info("✅ OSS 获取凭证成功: 使用固定 AccessKey")
            elif HAS_ALICLOUD_CREDENTIALS:
                role_name = os.getenv("ALIYUN_ECS_ROLE_NAME", "")
                provider = AlibabaCloudCredentialsProvider(role_name)
                auth = oss2.ProviderAuth(provider)
                logger.info("✅ OSS 获取凭证成功: 使用 ECS RAM 角色免密方式")
            else:
                logger.warning("⚠️ 没有配置 AK 也缺少 alibabacloud_credentials 库支持")
                return

            self.bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
            logger.info(f"✅ 阿里云 OSS 初始化成功 Bucket={self.bucket_name}")
        except Exception as e:
            logger.error(f"⚠️ 阿里云 OSS 初始化失败: {str(e)}")

    def upload_file_bytes(self, user_id: str, file_bytes: bytes, extension: str = ".glb", file_uuid: Optional[str] = None) -> Optional[str]:
        """
        将文件字节流上传到 OSS 的私有 bucket 中
        """
        if not self.bucket:
            logger.error("OSS 未初始化，无法上传")
            return None
            
        try:
            import time
            if not file_uuid:
                file_uuid = str(uuid.uuid4())
            
            # 为了区分图片和模型，加一个小后缀
            suffix = "_preview" if extension.lower() in [".png", ".jpg", ".jpeg"] else "_model"
            
            # 路径设计：models/{user_id}/{uuid}/object
            oss_key = f"models/{user_id}/{file_uuid}/{file_uuid[:8]}{suffix}{extension}"
            
            result = self.bucket.put_object(oss_key, file_bytes)
            if result.status == 200:
                logger.info(f"✅ OSS 上传成功: {oss_key}")
                return oss_key
            else:
                logger.error(f"OSS 上传失败，状态码: {result.status}")
                return None
        except Exception as e:
            logger.error(f"OSS 上传异常: {str(e)}")
            return None

    def upload_object_bytes(self, oss_key: str, file_bytes: bytes) -> Optional[str]:
        """按指定 object key 上传字节流。"""
        if not self.bucket:
            logger.error("OSS 未初始化，无法上传")
            return None

        try:
            result = self.bucket.put_object(oss_key, file_bytes)
            if result.status == 200:
                logger.info(f"✅ OSS 上传成功: {oss_key}")
                return oss_key
            logger.error(f"OSS 上传失败，状态码: {result.status}")
            return None
        except Exception as e:
            logger.error(f"OSS 上传异常: {str(e)}")
            return None

    def generate_presigned_url(self, oss_key: str, expires: int = 3600) -> Optional[str]:
        """
        为私有 Object 生成预签名 URL，默认一小时有效
        """
        if not self.bucket:
            return None
            
        try:
            url = self.bucket.sign_url('GET', oss_key, expires)
            if "-internal" in url:
                url = url.replace("-internal", "")
            return url
        except Exception as e:
            logger.error(f"生成 OSS 签名 URL 异常: {str(e)}")
            return None

    def download_file_bytes(self, oss_key: str) -> Optional[bytes]:
        """从 OSS 读取完整对象内容。"""
        if not self.bucket:
            logger.error("OSS 未初始化，无法下载")
            return None

        try:
            return self.bucket.get_object(oss_key).read()
        except Exception as e:
            logger.error(f"OSS 下载异常: {str(e)}")
            return None

    def delete_object(self, oss_key: str) -> bool:
        """从私有 bucket 中删除 OSS 文件"""
        if not self.bucket:
            return False
        try:
            result = self.bucket.delete_object(oss_key)
            if result.status == 204:
                logger.info(f"✅ OSS 删除成功: {oss_key}")
                return True
            else:
                logger.error(f"OSS 删除失败，状态码: {result.status}")
                return False
        except Exception as e:
            logger.error(f"OSS 删除异常: {str(e)}")
            return False

# 单例
oss_manager = OSSManager()
