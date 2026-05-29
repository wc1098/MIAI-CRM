import base64
import hashlib
import hmac
import json
import posixpath
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from urllib.parse import urlparse

from app.core.exceptions import CustomException
from app.utils.aliyun_oss_util import AliyunOSSUtil
from app.utils.storage_config import StorageConfig

from .schema import (
    OssPolicyRequestSchema,
    OssPolicyResponseSchema,
    UploadConfirmRequestSchema,
    UploadConfirmResponseSchema,
)


@dataclass(frozen=True)
class UploadSceneConfig:
    prefix: str
    max_size: int
    mime_types: tuple[str, ...]


IMAGE_MIME_TYPES = ("image/jpeg", "image/png", "image/webp")
VIDEO_MIME_TYPES = ("video/mp4",)
SCENE_CONFIG: dict[str, UploadSceneConfig] = {
    "mp_register_photo": UploadSceneConfig("mp/register-photo", 4 * 1024 * 1024, IMAGE_MIME_TYPES),
    "certification_material": UploadSceneConfig("certification/material", 6 * 1024 * 1024, IMAGE_MIME_TYPES),
    "crm_lead_photo": UploadSceneConfig("crm/lead-photo", 6 * 1024 * 1024, IMAGE_MIME_TYPES),
    "crm_contract_attachment": UploadSceneConfig("crm/contract-attachment", 12 * 1024 * 1024, (*IMAGE_MIME_TYPES, "application/pdf")),
    "event_cover": UploadSceneConfig("event/cover", 6 * 1024 * 1024, IMAGE_MIME_TYPES),
    "common_image": UploadSceneConfig("common/image", 6 * 1024 * 1024, IMAGE_MIME_TYPES),
    "screen_promo_image": UploadSceneConfig("screen/promo-image", 12 * 1024 * 1024, IMAGE_MIME_TYPES),
    "screen_promo_video": UploadSceneConfig("screen/promo-video", 5 * 1024 * 1024 * 1024, VIDEO_MIME_TYPES),
}
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
}


class CommonUploadService:
    """统一上传基座：签发 OSS 直传凭证并确认上传结果。"""

    @staticmethod
    def _scene(scene: str) -> UploadSceneConfig:
        config = SCENE_CONFIG.get(scene)
        if not config:
            raise CustomException(msg="不支持的上传场景")
        return config

    @staticmethod
    def _host(endpoint: str, bucket: str) -> str:
        parsed = urlparse(endpoint if endpoint.startswith(("http://", "https://")) else f"https://{endpoint}")
        scheme = parsed.scheme or "https"
        netloc = parsed.netloc or parsed.path
        return f"{scheme}://{bucket}.{netloc.rstrip('/')}"

    @staticmethod
    def _safe_stem(filename: str) -> str:
        stem = filename.rsplit(".", 1)[0] if "." in filename else filename
        stem = re.sub(r"[^a-zA-Z0-9_\-\u4e00-\u9fa5]", "", stem.strip())
        return (stem[:40] or "image").strip("_-") or "image"

    @classmethod
    def _object_key(cls, object_prefix: str, scene: str, filename: str, content_type: str) -> str:
        scene_config = cls._scene(scene)
        ext = CONTENT_TYPE_EXTENSIONS.get(content_type, "")
        if not ext:
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ".jpg"
        date_path = datetime.now().strftime("%Y/%m/%d")
        file_name = f"{cls._safe_stem(filename)}_{datetime.now().strftime('%H%M%S')}_{uuid.uuid4().hex[:10]}{ext}"
        clean_prefix = object_prefix.strip().strip("/")
        return str(PurePosixPath(clean_prefix, scene_config.prefix, date_path, file_name))

    @classmethod
    async def create_oss_policy(cls, data: OssPolicyRequestSchema) -> OssPolicyResponseSchema:
        scene_config = cls._scene(data.scene)
        content_type = (data.content_type or "").split(";", 1)[0].strip().lower()
        if content_type not in scene_config.mime_types:
            raise CustomException(msg="上传文件类型不符合当前场景要求")
        if data.size and data.size > scene_config.max_size:
            raise CustomException(msg=f"文件超过上传限制，最大 {scene_config.max_size // 1024 // 1024}MB")

        if await StorageConfig.get_storage_driver() != "aliyun_oss":
            raise CustomException(msg="当前资源存储未启用阿里云 OSS，不能使用直传")
        config = await StorageConfig.get_aliyun_oss_config()
        if config.missing_fields:
            raise CustomException(msg=f"阿里云OSS配置不完整，请在参数管理补充: {', '.join(config.missing_fields)}")

        object_key = cls._object_key(config.object_prefix, data.scene, data.filename, content_type)
        expire_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        policy_dict = {
            "expiration": expire_at.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "conditions": [
                ["eq", "$key", object_key],
                ["content-length-range", 1, scene_config.max_size],
                ["eq", "$Content-Type", content_type],
                ["eq", "$success_action_status", "200"],
            ],
        }
        policy = base64.b64encode(json.dumps(policy_dict, separators=(",", ":")).encode()).decode()
        signature = base64.b64encode(
            hmac.new(config.access_key_secret.encode(), policy.encode(), hashlib.sha1).digest()
        ).decode()
        return OssPolicyResponseSchema(
            host=cls._host(config.endpoint, config.bucket),
            object_key=object_key,
            file_url=AliyunOSSUtil.build_file_url(config, object_key),
            policy=policy,
            signature=signature,
            access_key_id=config.access_key_id,
            expire_at=expire_at.isoformat(),
            max_size=scene_config.max_size,
        )

    @classmethod
    async def confirm_uploaded_object(cls, data: UploadConfirmRequestSchema) -> UploadConfirmResponseSchema:
        scene_config = cls._scene(data.scene)
        config = await StorageConfig.get_aliyun_oss_config()
        object_key = posixpath.normpath(data.object_key.strip().lstrip("/"))
        if object_key.startswith("../") or object_key == ".":
            raise CustomException(msg="上传文件路径非法")

        expected_prefix = str(PurePosixPath(config.object_prefix.strip().strip("/"), scene_config.prefix))
        if not object_key.startswith(expected_prefix.rstrip("/") + "/"):
            raise CustomException(msg="上传文件不属于当前业务场景")

        expected_url = AliyunOSSUtil.build_file_url(config, object_key)
        if data.file_url.split("?", 1)[0] != expected_url:
            raise CustomException(msg="上传文件地址不合法")

        file_name = object_key.rsplit("/", 1)[-1]
        return UploadConfirmResponseSchema(
            file_name=file_name,
            origin_name=file_name,
            file_path=object_key,
            file_url=expected_url,
            object_key=object_key,
            content_type=None,
            scene=data.scene,
        )
