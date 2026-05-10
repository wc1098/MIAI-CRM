from dataclasses import dataclass

from sqlalchemy import select

from app.api.v1.module_system.params.model import ParamsModel
from app.core.database import async_db_session


STORAGE_DRIVER_KEY = "storage.default_driver"
ALIYUN_OSS_ACCESS_KEY_ID = "storage.aliyun_oss.access_key_id"
ALIYUN_OSS_ACCESS_KEY_SECRET = "storage.aliyun_oss.access_key_secret"
ALIYUN_OSS_ENDPOINT = "storage.aliyun_oss.endpoint"
ALIYUN_OSS_BUCKET = "storage.aliyun_oss.bucket"
ALIYUN_OSS_PUBLIC_BASE_URL = "storage.aliyun_oss.public_base_url"
ALIYUN_OSS_OBJECT_PREFIX = "storage.aliyun_oss.object_prefix"


@dataclass(frozen=True)
class AliyunOSSConfig:
    access_key_id: str
    access_key_secret: str
    endpoint: str
    bucket: str
    public_base_url: str | None = None
    object_prefix: str = "uploads"

    @property
    def missing_fields(self) -> list[str]:
        fields = {
            ALIYUN_OSS_ACCESS_KEY_ID: self.access_key_id,
            ALIYUN_OSS_ACCESS_KEY_SECRET: self.access_key_secret,
            ALIYUN_OSS_ENDPOINT: self.endpoint,
            ALIYUN_OSS_BUCKET: self.bucket,
        }
        return [key for key, value in fields.items() if not value]


class StorageConfig:
    """
    从系统参数表读取资源存储配置。
    """

    @staticmethod
    async def get_values(keys: list[str]) -> dict[str, str]:
        async with async_db_session() as session:
            result = await session.execute(
                select(ParamsModel.config_key, ParamsModel.config_value).where(
                    ParamsModel.config_key.in_(keys),
                    ParamsModel.status == "0",
                    ParamsModel.is_deleted == False,
                )
            )
            return {key: value or "" for key, value in result.all()}

    @classmethod
    async def get_storage_driver(cls) -> str:
        values = await cls.get_values([STORAGE_DRIVER_KEY])
        return (values.get(STORAGE_DRIVER_KEY) or "local").strip().lower()

    @classmethod
    async def get_aliyun_oss_config(cls) -> AliyunOSSConfig:
        values = await cls.get_values(
            [
                ALIYUN_OSS_ACCESS_KEY_ID,
                ALIYUN_OSS_ACCESS_KEY_SECRET,
                ALIYUN_OSS_ENDPOINT,
                ALIYUN_OSS_BUCKET,
                ALIYUN_OSS_PUBLIC_BASE_URL,
                ALIYUN_OSS_OBJECT_PREFIX,
            ]
        )
        return AliyunOSSConfig(
            access_key_id=values.get(ALIYUN_OSS_ACCESS_KEY_ID, "").strip(),
            access_key_secret=values.get(ALIYUN_OSS_ACCESS_KEY_SECRET, "").strip(),
            endpoint=values.get(ALIYUN_OSS_ENDPOINT, "").strip(),
            bucket=values.get(ALIYUN_OSS_BUCKET, "").strip(),
            public_base_url=(values.get(ALIYUN_OSS_PUBLIC_BASE_URL, "").strip() or None),
            object_prefix=values.get(ALIYUN_OSS_OBJECT_PREFIX, "").strip() or "uploads",
        )
