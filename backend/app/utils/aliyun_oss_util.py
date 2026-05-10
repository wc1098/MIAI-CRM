import asyncio
from pathlib import PurePosixPath
from urllib.parse import urljoin

from app.core.exceptions import CustomException
from app.core.logger import log
from app.utils.storage_config import AliyunOSSConfig


class AliyunOSSUtil:
    """
    阿里云 OSS 上传工具。
    """

    @staticmethod
    def build_object_key(prefix: str, date_path: str, filename: str) -> str:
        clean_prefix = prefix.strip().strip("/")
        parts = [part for part in (clean_prefix, date_path.strip("/"), filename) if part]
        return str(PurePosixPath(*parts))

    @staticmethod
    def build_file_url(config: AliyunOSSConfig, object_key: str) -> str:
        if config.public_base_url:
            return urljoin(config.public_base_url.rstrip("/") + "/", object_key)

        endpoint = config.endpoint.replace("https://", "").replace("http://", "").rstrip("/")
        return f"https://{config.bucket}.{endpoint}/{object_key}"

    @classmethod
    async def upload_bytes(
        cls,
        *,
        config: AliyunOSSConfig,
        object_key: str,
        content: bytes,
        content_type: str | None = None,
    ) -> str:
        missing_fields = config.missing_fields
        if missing_fields:
            raise CustomException(msg=f"阿里云OSS配置不完整，请在参数管理补充: {', '.join(missing_fields)}")

        try:
            import oss2
        except ImportError as e:
            raise CustomException(msg="缺少阿里云OSS SDK，请安装依赖 oss2") from e

        def _put_object() -> None:
            auth = oss2.Auth(config.access_key_id, config.access_key_secret)
            bucket = oss2.Bucket(auth, config.endpoint, config.bucket)
            headers = {"Content-Type": content_type} if content_type else None
            result = bucket.put_object(object_key, content, headers=headers)
            if result.status < 200 or result.status >= 300:
                raise CustomException(msg=f"阿里云OSS上传失败，状态码: {result.status}")

        try:
            await asyncio.to_thread(_put_object)
            log.info(f"阿里云OSS上传成功: {object_key}")
            return cls.build_file_url(config, object_key)
        except CustomException:
            raise
        except Exception as e:
            log.error(f"阿里云OSS上传失败: {e}")
            raise CustomException(msg=f"阿里云OSS上传失败: {e}") from e
