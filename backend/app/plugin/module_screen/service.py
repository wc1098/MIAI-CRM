import hashlib
import json
import secrets
import string
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import aiofiles
import httpx
from redis.asyncio.client import Redis
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.auth.schema import AuthSchema
from app.api.v1.module_system.dict.model import DictDataModel
from app.api.v1.module_system.params.model import ParamsModel
from app.config.setting import settings
from app.core.exceptions import CustomException
from app.plugin.module_certification.service import CertificationService
from app.plugin.module_crm.lead.model import CrmPersonModel
from app.plugin.module_crm.person.model import PersonProfileInsightModel
from app.plugin.module_mp.auth.model import MiniProgramUserModel
from app.plugin.module_profile_ai.model import PersonAiProfileModel
from app.plugin.module_profile_ai.service import MIAI_IMPRESSION
from app.utils.aliyun_oss_util import AliyunOSSUtil
from app.utils.storage_config import StorageConfig

from .model import (
    ScreenDeviceModel,
    ScreenPromoCacheReportModel,
    ScreenPromoConfigModel,
    ScreenPromoItemModel,
    ScreenPromoRecordModel,
    ScreenPromoStaffModel,
    ScreenUserWallConfigModel,
    ScreenUserWallQrcodeModel,
    ScreenUserWallRecordModel,
)
from .schema import (
    ScreenDeviceBindSchema,
    ScreenDeviceBootstrapSchema,
    ScreenDeviceHeartbeatSchema,
    ScreenDeviceQueryParam,
    ScreenPromoCacheReportSchema,
    ScreenPromoConfigSchema,
    ScreenPromoItemSchema,
    ScreenPromoRecordSchema,
    ScreenPromoSortSchema,
    ScreenPromoStaffSchema,
    ScreenUserWallConfigSchema,
    ScreenUserWallRecordSchema,
)

CRM_DICT_MAP = {
    "annual_income": "crm_annual_income",
    "education": "crm_education",
    "marital_status": "crm_marital_status",
    "house_status": "crm_house_status",
    "car_status": "crm_car_status",
    "ethnicity": "crm_ethnicity",
}

MINI_PROFILE_PAGE = "pages/plaza/detail/index"
PENDING_DEVICE_CODE_TTL_SECONDS = 600
PENDING_DEVICE_CODE_PREFIX = "screen:pending_device:"


class ScreenService:
    """大屏底座与用户墙服务"""

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _new_token() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def _age(birth_date) -> int | None:
        if not birth_date:
            return None
        today = datetime.now().date()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    @staticmethod
    def _display_name(user: MiniProgramUserModel | None, person: CrmPersonModel) -> str:
        if user and user.nickname and user.nickname != person.name:
            return user.nickname
        suffix = {"0": "先生", "1": "女士"}.get(person.gender or "", "")
        prefix = (person.name or "觅")[:1]
        return f"{prefix}{suffix}" if suffix else f"{prefix}**"

    @classmethod
    async def _param(cls, db: AsyncSession, key: str) -> str | None:
        value = await db.scalar(
            select(ParamsModel.config_value).where(
                ParamsModel.config_key == key,
                ParamsModel.status == "0",
                ParamsModel.is_deleted == False,
            )
        )
        return value or None

    @classmethod
    async def _dict_labels(cls, db: AsyncSession) -> dict[str, dict[str, str]]:
        rows = (
            await db.execute(
                select(DictDataModel).where(
                    DictDataModel.dict_type.in_(CRM_DICT_MAP.values()),
                    DictDataModel.status == "0",
                    DictDataModel.is_deleted == False,
                )
            )
        ).scalars().all()
        labels = {key: {} for key in CRM_DICT_MAP}
        reverse = {value: key for key, value in CRM_DICT_MAP.items()}
        for row in rows:
            key = reverse.get(row.dict_type)
            if key:
                labels[key][row.dict_value] = row.dict_label
        return labels

    @staticmethod
    def _dict_label(labels: dict[str, dict[str, str]], key: str, value: str | None) -> str | None:
        if not value:
            return None
        return labels.get(key, {}).get(value, value)

    @classmethod
    async def _config(cls, db: AsyncSession) -> ScreenUserWallConfigModel:
        row = await db.scalar(
            select(ScreenUserWallConfigModel).where(
                ScreenUserWallConfigModel.brand_id == 1,
                ScreenUserWallConfigModel.is_deleted == False,
            )
        )
        if row:
            return row
        row = ScreenUserWallConfigModel(brand_id=1)
        db.add(row)
        await db.flush()
        return row

    @classmethod
    async def _new_device_code(cls, db: AsyncSession, redis: Redis | None = None) -> str:
        alphabet = string.ascii_uppercase + string.digits
        for _ in range(20):
            code = "".join(secrets.choice(alphabet) for _ in range(4)) + "-" + "".join(secrets.choice(alphabet) for _ in range(4))
            exists = await db.scalar(select(ScreenDeviceModel.id).where(ScreenDeviceModel.device_code == code))
            pending = await redis.exists(cls._pending_device_key(code)) if redis else False
            if not exists and not pending:
                return code
        raise CustomException(msg="设备码生成失败，请重试")

    @staticmethod
    def _pending_device_key(device_code: str) -> str:
        return f"{PENDING_DEVICE_CODE_PREFIX}{device_code.strip().upper()}"

    @classmethod
    async def _pending_device_payload(cls, redis: Redis, device_code: str) -> dict[str, Any] | None:
        raw = await redis.get(cls._pending_device_key(device_code))
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    @classmethod
    async def bootstrap(cls, db: AsyncSession, redis: Redis, data: ScreenDeviceBootstrapSchema) -> dict[str, Any]:
        device_code = await cls._new_device_code(db, redis)
        payload = {
            "device_code": device_code,
            "device_type": data.device_type,
            "app_version": data.app_version,
            "system_info": data.system_info or {},
            "created_at": datetime.now().isoformat(),
        }
        await redis.set(cls._pending_device_key(device_code), json.dumps(payload, ensure_ascii=False), ex=PENDING_DEVICE_CODE_TTL_SECONDS)
        return {"device_id": None, "device_code": device_code, "bind_status": "unbound", "expires_at": None}

    @classmethod
    async def bind_status(cls, db: AsyncSession, redis: Redis, device_code: str) -> dict[str, Any]:
        clean_code = device_code.strip().upper()
        device = await db.scalar(
            select(ScreenDeviceModel).where(
                ScreenDeviceModel.device_code == clean_code,
                ScreenDeviceModel.is_deleted == False,
            )
        )
        if not device:
            pending = await cls._pending_device_payload(redis, clean_code)
            if pending:
                return {
                    "device_id": None,
                    "device_code": clean_code,
                    "bind_status": "unbound",
                    "device_token": None,
                    "device_name": None,
                }
            raise CustomException(msg="设备码不存在或已过期")
        token = None
        if device.bind_status == "bound":
            token = cls._new_token()
            device.device_token_hash = cls._hash_token(token)
            device.online_status = "online"
            device.last_online_at = datetime.now()
            await db.flush()
        return {
            "device_id": device.id,
            "device_code": device.device_code,
            "bind_status": device.bind_status,
            "device_token": token,
            "device_name": device.device_name,
        }

    @classmethod
    async def device_by_token(cls, db: AsyncSession, token: str) -> ScreenDeviceModel:
        token_hash = cls._hash_token(token)
        device = await db.scalar(
            select(ScreenDeviceModel).where(
                ScreenDeviceModel.device_token_hash == token_hash,
                ScreenDeviceModel.is_deleted == False,
            )
        )
        if not device or device.bind_status != "bound":
            raise CustomException(msg="大屏设备授权无效", code=10401, status_code=401)
        return device

    @classmethod
    async def page_devices(cls, auth: AuthSchema, page_no: int, page_size: int, search: ScreenDeviceQueryParam) -> dict[str, Any]:
        conditions: list[Any] = [ScreenDeviceModel.is_deleted == False]
        if search.keyword:
            like = f"%{search.keyword}%"
            conditions.append(or_(ScreenDeviceModel.device_code.like(like), ScreenDeviceModel.device_name.like(like)))
        if search.bind_status:
            conditions.append(ScreenDeviceModel.bind_status == search.bind_status)
        if search.online_status:
            conditions.append(ScreenDeviceModel.online_status == search.online_status)
        total = await auth.db.scalar(select(func.count(ScreenDeviceModel.id)).where(*conditions)) or 0
        rows = (
            await auth.db.execute(
                select(ScreenDeviceModel)
                .where(*conditions)
                .order_by(ScreenDeviceModel.updated_time.desc(), ScreenDeviceModel.id.desc())
                .offset((page_no - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": [cls._device_out(row) for row in rows],
        }

    @staticmethod
    def _device_out(row: ScreenDeviceModel) -> dict[str, Any]:
        return {
            "id": row.id,
            "brand_id": row.brand_id,
            "store_id": row.store_id,
            "device_code": row.device_code,
            "device_name": row.device_name,
            "device_type": row.device_type,
            "bind_status": row.bind_status,
            "online_status": row.online_status,
            "bound_by": row.bound_by,
            "bound_at": row.bound_at,
            "last_online_at": row.last_online_at,
            "last_sync_at": row.last_sync_at,
            "app_version": row.app_version,
            "system_info": row.system_info or {},
            "created_time": row.created_time,
        }

    @classmethod
    async def bind_device(cls, auth: AuthSchema, redis: Redis, data: ScreenDeviceBindSchema) -> dict[str, Any]:
        device = await auth.db.scalar(
            select(ScreenDeviceModel).where(
                ScreenDeviceModel.device_code == data.device_code,
                ScreenDeviceModel.is_deleted == False,
            )
        )
        pending = await cls._pending_device_payload(redis, data.device_code)
        if not device and not pending:
            raise CustomException(msg="设备码不存在或已过期，请确认大屏页面显示的设备码")
        if not device:
            device = ScreenDeviceModel(
                brand_id=1,
                device_code=data.device_code,
                device_type=str(pending.get("device_type") or "web"),
                bind_status="unbound",
                online_status="offline",
                app_version=pending.get("app_version"),
                system_info=pending.get("system_info") or {},
            )
            auth.db.add(device)
        device.device_name = data.device_name or device.device_name or f"大屏设备 {device.device_code}"
        device.store_id = data.store_id
        device.bind_status = "bound"
        device.bound_by = auth.user.id if auth.user else None
        device.bound_at = datetime.now()
        device.updated_id = auth.user.id if auth.user else None
        await auth.db.flush()
        await redis.delete(cls._pending_device_key(data.device_code))
        return cls._device_out(device)

    @classmethod
    async def _device_by_id(cls, auth: AuthSchema, device_id: int) -> ScreenDeviceModel:
        device = await auth.db.scalar(
            select(ScreenDeviceModel).where(ScreenDeviceModel.id == device_id, ScreenDeviceModel.is_deleted == False)
        )
        if not device:
            raise CustomException(msg="设备不存在")
        return device

    @classmethod
    async def unbind_device(cls, auth: AuthSchema, device_id: int) -> dict[str, Any]:
        device = await cls._device_by_id(auth, device_id)
        device.bind_status = "unbound"
        device.device_token_hash = None
        device.online_status = "offline"
        device.updated_id = auth.user.id if auth.user else None
        await auth.db.flush()
        return cls._device_out(device)

    @classmethod
    async def delete_device(cls, auth: AuthSchema, device_id: int) -> dict[str, Any]:
        device = await cls._device_by_id(auth, device_id)
        device.device_token_hash = None
        device.online_status = "offline"
        device.is_deleted = True
        device.deleted_time = datetime.now()
        device.deleted_id = auth.user.id if auth.user else None
        await auth.db.flush()
        return cls._device_out(device)

    @classmethod
    async def reset_device_token(cls, auth: AuthSchema, device_id: int) -> dict[str, Any]:
        device = await cls._device_by_id(auth, device_id)
        if device.bind_status != "bound":
            raise CustomException(msg="只有已绑定设备可以重置授权")
        device.device_token_hash = None
        device.online_status = "offline"
        device.updated_id = auth.user.id if auth.user else None
        await auth.db.flush()
        return cls._device_out(device)

    @classmethod
    async def heartbeat(cls, db: AsyncSession, device: ScreenDeviceModel, data: ScreenDeviceHeartbeatSchema) -> dict[str, Any]:
        now = datetime.now()
        device.online_status = "online"
        device.last_online_at = now
        device.last_sync_at = now
        device.app_version = data.app_version or device.app_version
        if data.system_info:
            device.system_info = data.system_info
        await db.flush()
        return {"device_id": device.id, "online_status": device.online_status, "last_online_at": device.last_online_at}

    @classmethod
    def _config_out(cls, row: ScreenUserWallConfigModel) -> dict[str, Any]:
        return {
            "id": row.id,
            "title": row.title,
            "user_switch_seconds": row.user_switch_seconds,
            "photo_switch_seconds": row.photo_switch_seconds,
            "sort_strategy": row.sort_strategy,
            "filter_config": row.filter_config or {},
            "qr_action": row.qr_action,
            "status": row.status,
        }

    @classmethod
    async def get_user_wall_config(cls, db: AsyncSession) -> dict[str, Any]:
        return cls._config_out(await cls._config(db))

    @classmethod
    async def save_user_wall_config(cls, auth: AuthSchema, data: ScreenUserWallConfigSchema) -> dict[str, Any]:
        row = await cls._config(auth.db)
        payload = data.model_dump()
        for key, value in payload.items():
            setattr(row, key, value)
        row.updated_id = auth.user.id if auth.user else None
        await auth.db.flush()
        return cls._config_out(row)

    @classmethod
    async def player_config(cls, db: AsyncSession, device: ScreenDeviceModel) -> dict[str, Any]:
        config = await cls._config(db)
        device.last_sync_at = datetime.now()
        await db.flush()
        return {
            "device": cls._device_out(device),
            "user_wall": cls._config_out(config),
        }

    @classmethod
    async def _wechat_access_token(cls, db: AsyncSession) -> str:
        app_id = await cls._param(db, "miniprogram.wechat.app_id")
        app_secret = await cls._param(db, "miniprogram.wechat.app_secret")
        if not app_id or not app_secret:
            raise CustomException(msg="请先配置微信小程序AppID和AppSecret")
        async with httpx.AsyncClient(timeout=settings.HTTPX_DEFAULT_TIMEOUT) as client:
            response = await client.get(
                "https://api.weixin.qq.com/cgi-bin/token",
                params={"grant_type": "client_credential", "appid": app_id, "secret": app_secret},
            )
        payload = response.json()
        if payload.get("errcode"):
            raise CustomException(msg=f"获取微信接口调用凭证失败: {payload.get('errmsg')}", data=payload)
        return payload["access_token"]

    @classmethod
    async def _upload_qrcode_bytes(cls, content: bytes, filename: str) -> tuple[str, str]:
        date_path = datetime.now().strftime("%Y/%m/%d")
        storage_driver = await StorageConfig.get_storage_driver()
        if storage_driver == "aliyun_oss":
            config = await StorageConfig.get_aliyun_oss_config()
            object_key = AliyunOSSUtil.build_object_key(config.object_prefix, f"screen/qrcode/{date_path}", filename)
            url = await AliyunOSSUtil.upload_bytes(config=config, object_key=object_key, content=content, content_type="image/png")
            return url, object_key
        if storage_driver != "local":
            raise CustomException(msg=f"不支持的资源存储类型: {storage_driver}")
        dir_path = settings.STATIC_ROOT.joinpath("upload", "screen", "qrcode", date_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path.joinpath(filename)
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        rel = file_path.relative_to(settings.STATIC_ROOT).as_posix()
        return urljoin(settings.STATIC_URL.rstrip("/") + "/", rel), str(file_path)

    @classmethod
    async def _qrcode_url(cls, db: AsyncSession, person: CrmPersonModel) -> str:
        if not person.display_no:
            return ""
        row = await db.scalar(
            select(ScreenUserWallQrcodeModel).where(
                ScreenUserWallQrcodeModel.person_id == person.id,
                ScreenUserWallQrcodeModel.display_no == person.display_no,
                ScreenUserWallQrcodeModel.page_path == MINI_PROFILE_PAGE,
            )
        )
        if row:
            if row.is_deleted:
                row.is_deleted = False
                row.deleted_time = None
                row.deleted_id = None
            return row.file_url
        access_token = await cls._wechat_access_token(db)
        async with httpx.AsyncClient(timeout=settings.HTTPX_DEFAULT_TIMEOUT) as client:
            response = await client.post(
                "https://api.weixin.qq.com/wxa/getwxacodeunlimit",
                params={"access_token": access_token},
                json={"scene": person.display_no, "page": MINI_PROFILE_PAGE, "check_path": False},
            )
        content_type = response.headers.get("content-type", "")
        content = response.content
        if "application/json" in content_type:
            payload = response.json()
            raise CustomException(msg=f"生成小程序码失败: {payload.get('errmsg')}", data=payload)
        filename = f"screen_user_{person.id}_{person.display_no}.png"
        file_url, file_path = await cls._upload_qrcode_bytes(content, filename)
        row = ScreenUserWallQrcodeModel(
            brand_id=1,
            person_id=person.id,
            display_no=person.display_no,
            page_path=MINI_PROFILE_PAGE,
            scene=person.display_no,
            file_url=file_url,
            file_path=file_path,
            generated_at=datetime.now(),
        )
        db.add(row)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            cached = await db.scalar(
                select(ScreenUserWallQrcodeModel).where(
                    ScreenUserWallQrcodeModel.person_id == person.id,
                    ScreenUserWallQrcodeModel.display_no == person.display_no,
                    ScreenUserWallQrcodeModel.page_path == MINI_PROFILE_PAGE,
                )
            )
            if cached:
                return cached.file_url
            raise
        return file_url

    @classmethod
    async def _user_wall_rows(cls, db: AsyncSession, limit: int = 100) -> list[tuple[MiniProgramUserModel, CrmPersonModel, PersonProfileInsightModel | None, PersonAiProfileModel | None]]:
        config = await cls._config(db)
        filters = config.filter_config or {}
        conditions: list[Any] = [
            MiniProgramUserModel.person_id.is_not(None),
            MiniProgramUserModel.is_invisible == False,
            MiniProgramUserModel.allow_user_wall == True,
            MiniProgramUserModel.is_deleted == False,
            CrmPersonModel.is_deleted == False,
            CrmPersonModel.display_no.is_not(None),
        ]
        if filters.get("gender") in {"0", "1"}:
            conditions.append(CrmPersonModel.gender == filters["gender"])
        if filters.get("certification_level"):
            conditions.append(CrmPersonModel.certification_level == filters["certification_level"])
        stmt = (
            select(MiniProgramUserModel, CrmPersonModel, PersonProfileInsightModel, PersonAiProfileModel)
            .join(CrmPersonModel, MiniProgramUserModel.person_id == CrmPersonModel.id)
            .outerjoin(
                PersonProfileInsightModel,
                and_(
                    PersonProfileInsightModel.person_id == CrmPersonModel.id,
                    PersonProfileInsightModel.is_deleted == False,
                ),
            )
            .outerjoin(
                PersonAiProfileModel,
                and_(
                    PersonAiProfileModel.person_id == CrmPersonModel.id,
                    PersonAiProfileModel.profile_type == MIAI_IMPRESSION,
                    PersonAiProfileModel.is_effective == True,
                    PersonAiProfileModel.is_deleted == False,
                ),
            )
            .where(*conditions)
        )
        if config.sort_strategy == "certified":
            stmt = stmt.order_by(
                CrmPersonModel.certification_level.desc(),
                func.coalesce(MiniProgramUserModel.registered_at, CrmPersonModel.created_time).desc(),
                MiniProgramUserModel.id.desc(),
            )
        else:
            stmt = stmt.order_by(
                func.coalesce(MiniProgramUserModel.registered_at, CrmPersonModel.created_time).desc(),
                MiniProgramUserModel.id.desc(),
            )
        return list((await db.execute(stmt.limit(limit))).all())

    @classmethod
    async def user_wall_items(cls, db: AsyncSession, limit: int = 100, with_qrcode: bool = True) -> list[dict[str, Any]]:
        labels = await cls._dict_labels(db)
        items: list[dict[str, Any]] = []
        for user, person, insight, ai_profile in await cls._user_wall_rows(db, limit):
            photos = person.photo_urls or []
            impression = (ai_profile.content if ai_profile else None) or (insight.public_matchmaker_impression if insight else None) or person.profile_intro
            item = {
                "user_id": user.id,
                "person_id": person.id,
                "display_no": person.display_no,
                "display_name": cls._display_name(user, person),
                "avatar_url": user.avatar_url or (photos[0] if photos else None),
                "photos": photos,
                "age": cls._age(person.birth_date),
                "gender": person.gender,
                "height_cm": person.height_cm,
                "ethnicity": cls._dict_label(labels, "ethnicity", person.ethnicity),
                "occupation": person.occupation,
                "annual_income": cls._dict_label(labels, "annual_income", person.annual_income),
                "marital_status": cls._dict_label(labels, "marital_status", person.marital_status),
                "education": cls._dict_label(labels, "education", person.education),
                "hometown": person.hometown,
                "residence": person.residence,
                "house_status": cls._dict_label(labels, "house_status", person.house_status),
                "car_status": cls._dict_label(labels, "car_status", person.car_status),
                "miai_impression": impression,
                "matchmaker_impression": impression,
                "qrcode_url": await cls._qrcode_url(db, person) if with_qrcode else "",
            }
            item.update(CertificationService.certification_level_out(person))
            items.append(item)
        return items

    @classmethod
    async def player_user_wall(cls, db: AsyncSession, device: ScreenDeviceModel) -> dict[str, Any]:
        config = await cls._config(db)
        return {
            "config": cls._config_out(config),
            "items": await cls.user_wall_items(db, 100, True),
        }

    @classmethod
    async def record_user_wall(cls, db: AsyncSession, device: ScreenDeviceModel, data: ScreenUserWallRecordSchema) -> dict[str, Any]:
        record = ScreenUserWallRecordModel(
            brand_id=1,
            device_id=device.id,
            person_id=data.person_id,
            user_id=data.user_id,
            display_no=data.display_no,
            display_snapshot=data.display_snapshot or {},
            displayed_at=datetime.now(),
            duration_seconds=data.duration_seconds,
            play_result=data.play_result,
            error_message=data.error_message,
        )
        db.add(record)
        await db.flush()
        return {"id": record.id}

    @classmethod
    async def _promo_config(cls, db: AsyncSession) -> ScreenPromoConfigModel:
        row = await db.scalar(
            select(ScreenPromoConfigModel).where(
                ScreenPromoConfigModel.brand_id == 1,
                ScreenPromoConfigModel.is_deleted == False,
            )
        )
        if row:
            return row
        row = ScreenPromoConfigModel(brand_id=1)
        db.add(row)
        await db.flush()
        return row

    @staticmethod
    def _promo_config_out(row: ScreenPromoConfigModel) -> dict[str, Any]:
        return {
            "id": row.id,
            "enabled": row.enabled,
            "image_duration_seconds": row.image_duration_seconds,
            "staff_duration_seconds": row.staff_duration_seconds,
            "sync_interval_seconds": row.sync_interval_seconds,
            "cache_limit_gb": row.cache_limit_gb,
            "status": row.status,
        }

    @classmethod
    def _promo_staff_out(cls, row: ScreenPromoStaffModel | None) -> dict[str, Any] | None:
        if not row:
            return None
        specialties = cls._split_tags(row.specialties)
        return {
            "id": row.id,
            "avatar_url": row.avatar_url,
            "display_name": row.display_name,
            "role_title": row.role_title,
            "years_experience": row.years_experience,
            "specialties": specialties,
            "specialties_text": row.specialties,
            "service_slogan": row.service_slogan,
            "public_tags": row.public_tags or [],
            "sort": row.sort,
            "status": row.status,
        }

    @staticmethod
    def _split_tags(value: str | None) -> list[str]:
        if not value:
            return []
        return [item.strip() for item in value.replace("，", "、").replace(",", "、").replace("；", "、").replace(";", "、").split("、") if item.strip()]

    @staticmethod
    def _join_tags(values: list[str] | None) -> str | None:
        cleaned = [item.strip() for item in values or [] if item and item.strip()]
        return "、".join(cleaned) if cleaned else None

    @classmethod
    def _promo_item_out(cls, row: ScreenPromoItemModel, staff: ScreenPromoStaffModel | None = None) -> dict[str, Any]:
        return {
            "id": row.id,
            "type": row.item_type,
            "item_type": row.item_type,
            "title": row.title,
            "file_url": row.file_url,
            "cover_url": row.cover_url,
            "file_hash": row.file_hash,
            "file_size": row.file_size,
            "version": row.version,
            "duration_seconds": row.duration_seconds,
            "sort": row.sort,
            "staff_id": row.staff_id,
            "staff": cls._promo_staff_out(staff),
            "status": row.status,
        }

    @classmethod
    async def get_promo_manage(cls, db: AsyncSession) -> dict[str, Any]:
        config = await cls._promo_config(db)
        staffs = (
            await db.execute(
                select(ScreenPromoStaffModel)
                .where(ScreenPromoStaffModel.brand_id == 1, ScreenPromoStaffModel.is_deleted == False)
                .order_by(ScreenPromoStaffModel.sort.asc(), ScreenPromoStaffModel.id.asc())
            )
        ).scalars().all()
        staff_map = {row.id: row for row in staffs}
        items = (
            await db.execute(
                select(ScreenPromoItemModel)
                .where(ScreenPromoItemModel.brand_id == 1, ScreenPromoItemModel.is_deleted == False)
                .order_by(ScreenPromoItemModel.sort.asc(), ScreenPromoItemModel.id.asc())
            )
        ).scalars().all()
        return {
            "config": cls._promo_config_out(config),
            "items": [cls._promo_item_out(row, staff_map.get(row.staff_id or 0)) for row in items],
            "staffs": [cls._promo_staff_out(row) for row in staffs],
        }

    @classmethod
    async def save_promo_config(cls, auth: AuthSchema, data: ScreenPromoConfigSchema) -> dict[str, Any]:
        row = await cls._promo_config(auth.db)
        for key, value in data.model_dump().items():
            setattr(row, key, value)
        row.updated_id = auth.user.id if auth.user else None
        await auth.db.flush()
        return cls._promo_config_out(row)

    @classmethod
    async def create_promo_staff(cls, auth: AuthSchema, data: ScreenPromoStaffSchema) -> dict[str, Any]:
        payload = data.model_dump()
        payload["specialties"] = cls._join_tags(data.specialties)
        row = ScreenPromoStaffModel(brand_id=1, **payload)
        row.created_id = auth.user.id if auth.user else None
        auth.db.add(row)
        await auth.db.flush()
        max_sort = await auth.db.scalar(
            select(func.max(ScreenPromoItemModel.sort)).where(
                ScreenPromoItemModel.brand_id == 1,
                ScreenPromoItemModel.is_deleted == False,
            )
        )
        item = ScreenPromoItemModel(
            brand_id=1,
            item_type="staff",
            title=row.display_name,
            version=1,
            duration_seconds=None,
            sort=(max_sort or 0) + 1,
            staff_id=row.id,
            status=row.status,
        )
        item.created_id = auth.user.id if auth.user else None
        auth.db.add(item)
        await auth.db.flush()
        return cls._promo_staff_out(row) or {}

    @classmethod
    async def _promo_staff_by_id(cls, db: AsyncSession, staff_id: int) -> ScreenPromoStaffModel:
        row = await db.scalar(
            select(ScreenPromoStaffModel).where(
                ScreenPromoStaffModel.id == staff_id,
                ScreenPromoStaffModel.is_deleted == False,
            )
        )
        if not row:
            raise CustomException(msg="员工展示资料不存在")
        return row

    @classmethod
    async def update_promo_staff(cls, auth: AuthSchema, staff_id: int, data: ScreenPromoStaffSchema) -> dict[str, Any]:
        row = await cls._promo_staff_by_id(auth.db, staff_id)
        payload = data.model_dump()
        payload["specialties"] = cls._join_tags(data.specialties)
        for key, value in payload.items():
            setattr(row, key, value)
        row.updated_id = auth.user.id if auth.user else None
        items = (
            await auth.db.execute(
                select(ScreenPromoItemModel).where(ScreenPromoItemModel.staff_id == staff_id, ScreenPromoItemModel.is_deleted == False)
            )
        ).scalars().all()
        for item in items:
            item.title = row.display_name
            item.status = row.status
            item.updated_id = auth.user.id if auth.user else None
        await auth.db.flush()
        return cls._promo_staff_out(row) or {}

    @classmethod
    async def delete_promo_staff(cls, auth: AuthSchema, staff_id: int) -> dict[str, Any]:
        row = await cls._promo_staff_by_id(auth.db, staff_id)
        row.is_deleted = True
        row.deleted_time = datetime.now()
        row.deleted_id = auth.user.id if auth.user else None
        items = (
            await auth.db.execute(
                select(ScreenPromoItemModel).where(ScreenPromoItemModel.staff_id == staff_id, ScreenPromoItemModel.is_deleted == False)
            )
        ).scalars().all()
        for item in items:
            item.is_deleted = True
            item.deleted_time = datetime.now()
            item.deleted_id = auth.user.id if auth.user else None
        await auth.db.flush()
        return {"id": staff_id}

    @classmethod
    async def _validate_promo_item(cls, db: AsyncSession, data: ScreenPromoItemSchema, item_id: int | None = None) -> ScreenPromoStaffModel | None:
        if data.item_type in {"image", "video"} and not data.title.strip():
            raise CustomException(msg="请填写播放项标题")
        if data.item_type in {"image", "video"} and not data.file_url:
            raise CustomException(msg="图片/视频播放项必须上传素材")
        if data.item_type == "video" and data.file_url and not data.file_url.split("?", 1)[0].lower().endswith(".mp4"):
            raise CustomException(msg="宣传视频首版只支持 MP4")
        if data.item_type == "staff":
            if not data.staff_id:
                raise CustomException(msg="员工播放项必须选择员工展示资料")
            await cls._promo_staff_by_id(db, data.staff_id)
            conditions: list[Any] = [
                ScreenPromoItemModel.staff_id == data.staff_id,
                ScreenPromoItemModel.item_type == "staff",
                ScreenPromoItemModel.is_deleted == False,
            ]
            if item_id:
                conditions.append(ScreenPromoItemModel.id != item_id)
            exists = await db.scalar(select(ScreenPromoItemModel.id).where(*conditions))
            if exists:
                raise CustomException(msg="该上墙员工已在播放序列中")
            return await cls._promo_staff_by_id(db, data.staff_id)
        return None

    @classmethod
    async def create_promo_item(cls, auth: AuthSchema, data: ScreenPromoItemSchema) -> dict[str, Any]:
        staff = await cls._validate_promo_item(auth.db, data)
        payload = data.model_dump()
        if data.item_type == "staff" and staff and not payload["title"].strip():
            payload["title"] = staff.display_name
        row = ScreenPromoItemModel(brand_id=1, **payload)
        row.created_id = auth.user.id if auth.user else None
        auth.db.add(row)
        await auth.db.flush()
        return cls._promo_item_out(row, staff)

    @classmethod
    async def _promo_item_by_id(cls, db: AsyncSession, item_id: int) -> ScreenPromoItemModel:
        row = await db.scalar(
            select(ScreenPromoItemModel).where(
                ScreenPromoItemModel.id == item_id,
                ScreenPromoItemModel.is_deleted == False,
            )
        )
        if not row:
            raise CustomException(msg="宣传播放项不存在")
        return row

    @classmethod
    async def update_promo_item(cls, auth: AuthSchema, item_id: int, data: ScreenPromoItemSchema) -> dict[str, Any]:
        staff = await cls._validate_promo_item(auth.db, data, item_id)
        row = await cls._promo_item_by_id(auth.db, item_id)
        old_identity = (row.file_url, row.cover_url, row.staff_id)
        payload = data.model_dump()
        if data.item_type == "staff" and staff and not payload["title"].strip():
            payload["title"] = staff.display_name
        for key, value in payload.items():
            setattr(row, key, value)
        if (row.file_url, row.cover_url, row.staff_id) != old_identity and data.version <= row.version:
            row.version += 1
        row.updated_id = auth.user.id if auth.user else None
        await auth.db.flush()
        return cls._promo_item_out(row, staff)

    @classmethod
    async def delete_promo_item(cls, auth: AuthSchema, item_id: int) -> dict[str, Any]:
        row = await cls._promo_item_by_id(auth.db, item_id)
        row.is_deleted = True
        row.deleted_time = datetime.now()
        row.deleted_id = auth.user.id if auth.user else None
        await auth.db.flush()
        return {"id": item_id}

    @classmethod
    async def sort_promo_items(cls, auth: AuthSchema, data: ScreenPromoSortSchema) -> dict[str, Any]:
        rows = (
            await auth.db.execute(
                select(ScreenPromoItemModel).where(
                    ScreenPromoItemModel.id.in_(data.ids),
                    ScreenPromoItemModel.is_deleted == False,
                )
            )
        ).scalars().all()
        row_map = {row.id: row for row in rows}
        for index, item_id in enumerate(data.ids, start=1):
            if item_id in row_map:
                row_map[item_id].sort = index
                row_map[item_id].updated_id = auth.user.id if auth.user else None
        await auth.db.flush()
        return {"ids": data.ids}

    @classmethod
    async def player_promo(cls, db: AsyncSession, device: ScreenDeviceModel) -> dict[str, Any]:
        config = await cls._promo_config(db)
        staffs = (
            await db.execute(
                select(ScreenPromoStaffModel).where(
                    ScreenPromoStaffModel.brand_id == 1,
                    ScreenPromoStaffModel.status == "0",
                    ScreenPromoStaffModel.is_deleted == False,
                )
            )
        ).scalars().all()
        staff_map = {row.id: row for row in staffs}
        rows = (
            await db.execute(
                select(ScreenPromoItemModel)
                .where(
                    ScreenPromoItemModel.brand_id == 1,
                    ScreenPromoItemModel.status == "0",
                    ScreenPromoItemModel.is_deleted == False,
                )
                .order_by(ScreenPromoItemModel.sort.asc(), ScreenPromoItemModel.id.asc())
            )
        ).scalars().all()
        items: list[dict[str, Any]] = []
        for row in rows:
            staff = staff_map.get(row.staff_id or 0)
            if row.item_type == "staff" and not staff:
                continue
            item = cls._promo_item_out(row, staff)
            if not item["duration_seconds"]:
                item["duration_seconds"] = config.staff_duration_seconds if row.item_type == "staff" else config.image_duration_seconds
            items.append(item)
        device.last_sync_at = datetime.now()
        await db.flush()
        return {"config": cls._promo_config_out(config), "items": items}

    @classmethod
    async def report_promo_cache(cls, db: AsyncSession, device: ScreenDeviceModel, data: ScreenPromoCacheReportSchema) -> dict[str, Any]:
        row = ScreenPromoCacheReportModel(
            brand_id=1,
            device_id=device.id,
            item_id=data.item_id,
            version=data.version,
            cache_status=data.cache_status,
            local_path=data.local_path,
            downloaded_bytes=data.downloaded_bytes,
            error_message=data.error_message,
            reported_at=datetime.now(),
        )
        db.add(row)
        await db.flush()
        return {"id": row.id}

    @classmethod
    async def record_promo(cls, db: AsyncSession, device: ScreenDeviceModel, data: ScreenPromoRecordSchema) -> dict[str, Any]:
        row = ScreenPromoRecordModel(
            brand_id=1,
            device_id=device.id,
            item_id=data.item_id,
            item_type=data.item_type,
            play_result=data.play_result,
            duration_seconds=data.duration_seconds,
            error_message=data.error_message,
            played_at=datetime.now(),
        )
        db.add(row)
        await db.flush()
        return {"id": row.id}
