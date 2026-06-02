import hashlib
import json
import secrets
import string
from copy import deepcopy
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import aiofiles
import httpx
from redis.asyncio.client import Redis
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.module_system.auth.schema import AuthSchema
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.dict.model import DictDataModel
from app.api.v1.module_system.params.model import ParamsModel
from app.config.setting import settings
from app.core.exceptions import CustomException
from app.plugin.module_certification.service import CertificationService
from app.plugin.module_crm.lead.model import CrmPersonModel
from app.plugin.module_crm.person.model import PersonProfileInsightModel
from app.plugin.module_event.model import EventModel, EventParticipantModel, EventRegistrationModel
from app.plugin.module_mp.auth.model import MiniProgramUserModel
from app.plugin.module_profile_ai.model import PersonAiProfileModel
from app.plugin.module_profile_ai.service import MIAI_IMPRESSION
from app.utils.aliyun_oss_util import AliyunOSSUtil
from app.utils.storage_config import StorageConfig

from .model import (
    ScreenActivityBarrageModel,
    ScreenActivityConfigModel,
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
    ScreenActivityBarrageSettingsSchema,
    ScreenActivityCheckinWallSettingsSchema,
    ScreenActivityCommandSchema,
    ScreenActivityConfigSchema,
    ScreenActivityDominateSettingsSchema,
    ScreenActivityMusicSettingsSchema,
    ScreenActivityQrcodeSettingsSchema,
    ScreenActivityQueryParam,
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
MINI_ACTIVITY_CHECKIN_PAGE = "pages/activity/checkin/index"
PENDING_DEVICE_CODE_TTL_SECONDS = 600
PENDING_DEVICE_CODE_PREFIX = "screen:pending_device:"
DEFAULT_ACTIVITY_MODULE_CONFIG = {
    "checkin_wall": {"enabled": True, "settings": {}},
    "barrage": {"enabled": False, "settings": {"max_length": 50, "duration_seconds": 16, "need_review": False}},
    "dominate": {
        "enabled": False,
        "settings": {
            "durations": [20, 45, 90, 180, 300, 600],
            "default_duration": 20,
            "price": 20,
            "max_length": 20,
            "allow_image": True,
            "need_review": False,
            "templates": [],
        },
    },
    "gift": {"enabled": False, "settings": {}},
    "welfare": {"enabled": False, "settings": {}},
    "music": {"enabled": False, "settings": {}},
    "activity_qrcode": {"enabled": True, "settings": {}},
    "lottery": {"enabled": False, "placeholder": True, "settings": {}},
    "game": {"enabled": False, "placeholder": True, "settings": {}},
    "message_wall": {"enabled": False, "placeholder": True, "settings": {}},
}
DEFAULT_ACTIVITY_THEME_CONFIG = {
    "backgrounds": [],
    "active_background_id": "",
    "mobile_background_url": "",
    "welcome_message": "欢迎来到觅爱互动大厅，倡导文明用语，共建快乐活动现场！",
    "show_people_count": False,
}
DEFAULT_ACTIVITY_BARRAGE_SETTINGS = {"max_length": 50, "duration_seconds": 16, "size": "medium", "need_review": False}
DEFAULT_ACTIVITY_DOMINATE_SETTINGS = {"max_length": 20, "duration_seconds": 8, "need_review": False}
DEFAULT_ACTIVITY_QRCODE_SETTINGS = {"position": "3", "size": "medium"}
DEFAULT_ACTIVITY_CHECKIN_WALL_SETTINGS = {"title": "签到墙", "show_count": True, "show_avatar": True, "show_nickname": True, "list_size": "medium"}
DEFAULT_ACTIVITY_MUSIC_SETTINGS = {
    "volume": 60,
    "play_mode": "list_loop",
    "categories": [
        {"id": "cat_warmup", "name": "暖场"},
        {"id": "cat_romantic", "name": "浪漫"},
        {"id": "cat_interaction", "name": "互动"},
        {"id": "cat_ending", "name": "结束"},
    ],
    "tracks": [],
}
ACTIVITY_BARRAGE_SETTINGS_PARAM_KEY = "screen.activity.plugin.barrage.settings"
ACTIVITY_DOMINATE_SETTINGS_PARAM_KEY = "screen.activity.plugin.dominate.settings"
ACTIVITY_QRCODE_SETTINGS_PARAM_KEY = "screen.activity.plugin.qrcode.settings"
ACTIVITY_CHECKIN_WALL_SETTINGS_PARAM_KEY = "screen.activity.plugin.checkin_wall.settings"
ACTIVITY_MUSIC_SETTINGS_PARAM_KEY = "screen.activity.plugin.music.settings"
CONTROL_TOKEN_TTL_SECONDS = 24 * 60 * 60
CONTROL_TOKEN_PREFIX = "screen:activity_control:"
CONTROL_TOKEN_ACTIVITY_PREFIX = "screen:activity_control_by_activity:"


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
    def _normalize_barrage_settings(cls, value: dict[str, Any] | None) -> dict[str, Any]:
        config = {**DEFAULT_ACTIVITY_BARRAGE_SETTINGS, **(value or {})}
        config["max_length"] = min(max(int(config.get("max_length") or 50), 1), 100)
        config["duration_seconds"] = min(max(int(config.get("duration_seconds") or 16), 8), 60)
        size = str(config.get("size") or "medium").lower()
        config["size"] = size if size in {"large", "medium", "small"} else "medium"
        config["need_review"] = bool(config.get("need_review"))
        return config

    @classmethod
    async def activity_barrage_settings(cls, db: AsyncSession) -> dict[str, Any]:
        raw = await cls._param(db, ACTIVITY_BARRAGE_SETTINGS_PARAM_KEY)
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {}
        return cls._normalize_barrage_settings(data)

    @classmethod
    async def update_activity_barrage_settings(cls, auth: AuthSchema, data: ScreenActivityBarrageSettingsSchema) -> dict[str, Any]:
        settings_value = cls._normalize_barrage_settings(data.model_dump())
        value = json.dumps(settings_value, ensure_ascii=False)
        param = await auth.db.scalar(select(ParamsModel).where(ParamsModel.config_key == ACTIVITY_BARRAGE_SETTINGS_PARAM_KEY, ParamsModel.is_deleted == False))
        if param is None:
            param = ParamsModel(
                config_name="活动大屏普通弹幕设置",
                config_key=ACTIVITY_BARRAGE_SETTINGS_PARAM_KEY,
                config_value=value,
                config_type=True,
                status="0",
                description="活动大屏普通弹幕插件全局配置",
            )
            param.created_id = auth.user.id if auth.user else None
            auth.db.add(param)
        else:
            param.config_name = "活动大屏普通弹幕设置"
            param.config_value = value
            param.config_type = True
            param.status = "0"
            param.description = "活动大屏普通弹幕插件全局配置"
            param.updated_id = auth.user.id if auth.user else None
        await auth.db.flush()
        return settings_value

    @classmethod
    def _normalize_dominate_settings(cls, value: dict[str, Any] | None) -> dict[str, Any]:
        config = {**DEFAULT_ACTIVITY_DOMINATE_SETTINGS, **(value or {})}
        config["max_length"] = min(max(int(config.get("max_length") or 20), 1), 60)
        config["duration_seconds"] = min(max(int(config.get("duration_seconds") or 8), 3), 30)
        config["need_review"] = bool(config.get("need_review"))
        return config

    @classmethod
    async def activity_dominate_settings(cls, db: AsyncSession) -> dict[str, Any]:
        raw = await cls._param(db, ACTIVITY_DOMINATE_SETTINGS_PARAM_KEY)
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {}
        return cls._normalize_dominate_settings(data)

    @classmethod
    async def update_activity_dominate_settings(cls, auth: AuthSchema, data: ScreenActivityDominateSettingsSchema) -> dict[str, Any]:
        settings_value = cls._normalize_dominate_settings(data.model_dump())
        value = json.dumps(settings_value, ensure_ascii=False)
        param = await auth.db.scalar(select(ParamsModel).where(ParamsModel.config_key == ACTIVITY_DOMINATE_SETTINGS_PARAM_KEY, ParamsModel.is_deleted == False))
        if param is None:
            param = ParamsModel(
                config_name="活动大屏头像霸屏设置",
                config_key=ACTIVITY_DOMINATE_SETTINGS_PARAM_KEY,
                config_value=value,
                config_type=True,
                status="0",
                description="活动大屏头像霸屏插件全局配置",
            )
            param.created_id = auth.user.id if auth.user else None
            auth.db.add(param)
        else:
            param.config_name = "活动大屏头像霸屏设置"
            param.config_value = value
            param.config_type = True
            param.status = "0"
            param.description = "活动大屏头像霸屏插件全局配置"
            param.updated_id = auth.user.id if auth.user else None
        await auth.db.flush()
        return settings_value

    @classmethod
    def _apply_dominate_settings(cls, config: dict[str, Any], dominate_settings: dict[str, Any]) -> dict[str, Any]:
        module_config = deepcopy(config.get("module_config") or {})
        dominate_config = {**(module_config.get("dominate") or {"enabled": False, "settings": {}})}
        dominate_config["settings"] = cls._normalize_dominate_settings(dominate_settings)
        module_config["dominate"] = dominate_config
        config["module_config"] = module_config
        return config

    @classmethod
    def _normalize_qrcode_settings(cls, value: dict[str, Any] | None) -> dict[str, Any]:
        config = {**DEFAULT_ACTIVITY_QRCODE_SETTINGS, **(value or {})}
        position = str(config.get("position") or "3")
        size = str(config.get("size") or "medium").lower()
        config["position"] = position if position in {"1", "2", "3", "4", "5", "6", "7", "8", "9"} else "3"
        config["size"] = size if size in {"large", "medium", "small"} else "medium"
        return config

    @classmethod
    async def activity_qrcode_settings(cls, db: AsyncSession) -> dict[str, Any]:
        raw = await cls._param(db, ACTIVITY_QRCODE_SETTINGS_PARAM_KEY)
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {}
        return cls._normalize_qrcode_settings(data)

    @classmethod
    async def update_activity_qrcode_settings(cls, auth: AuthSchema, data: ScreenActivityQrcodeSettingsSchema) -> dict[str, Any]:
        settings_value = cls._normalize_qrcode_settings(data.model_dump())
        value = json.dumps(settings_value, ensure_ascii=False)
        param = await auth.db.scalar(select(ParamsModel).where(ParamsModel.config_key == ACTIVITY_QRCODE_SETTINGS_PARAM_KEY, ParamsModel.is_deleted == False))
        if param is None:
            param = ParamsModel(
                config_name="活动大屏签到二维码设置",
                config_key=ACTIVITY_QRCODE_SETTINGS_PARAM_KEY,
                config_value=value,
                config_type=True,
                status="0",
                description="活动大屏签到二维码插件全局配置",
            )
            param.created_id = auth.user.id if auth.user else None
            auth.db.add(param)
        else:
            param.config_name = "活动大屏签到二维码设置"
            param.config_value = value
            param.config_type = True
            param.status = "0"
            param.description = "活动大屏签到二维码插件全局配置"
            param.updated_id = auth.user.id if auth.user else None
        await auth.db.flush()
        return settings_value

    @classmethod
    def _apply_qrcode_settings(cls, config: dict[str, Any], qrcode_settings: dict[str, Any]) -> dict[str, Any]:
        module_config = deepcopy(config.get("module_config") or {})
        qrcode_config = {**(module_config.get("activity_qrcode") or {"enabled": True, "settings": {}})}
        qrcode_config["settings"] = cls._normalize_qrcode_settings(qrcode_settings)
        module_config["activity_qrcode"] = qrcode_config
        config["module_config"] = module_config
        return config

    @classmethod
    def _normalize_checkin_wall_settings(cls, value: dict[str, Any] | None) -> dict[str, Any]:
        config = {**DEFAULT_ACTIVITY_CHECKIN_WALL_SETTINGS, **(value or {})}
        title = str(config.get("title") or "签到墙").strip()
        list_size = str(config.get("list_size") or "medium").lower()
        config["title"] = title[:64] or "签到墙"
        config["show_count"] = bool(config.get("show_count"))
        config["show_avatar"] = bool(config.get("show_avatar"))
        config["show_nickname"] = bool(config.get("show_nickname"))
        config["list_size"] = list_size if list_size in {"large", "medium", "small"} else "medium"
        return config

    @classmethod
    async def activity_checkin_wall_settings(cls, db: AsyncSession) -> dict[str, Any]:
        raw = await cls._param(db, ACTIVITY_CHECKIN_WALL_SETTINGS_PARAM_KEY)
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {}
        return cls._normalize_checkin_wall_settings(data)

    @classmethod
    async def update_activity_checkin_wall_settings(cls, auth: AuthSchema, data: ScreenActivityCheckinWallSettingsSchema) -> dict[str, Any]:
        settings_value = cls._normalize_checkin_wall_settings(data.model_dump())
        value = json.dumps(settings_value, ensure_ascii=False)
        param = await auth.db.scalar(select(ParamsModel).where(ParamsModel.config_key == ACTIVITY_CHECKIN_WALL_SETTINGS_PARAM_KEY, ParamsModel.is_deleted == False))
        if param is None:
            param = ParamsModel(
                config_name="活动大屏签到墙设置",
                config_key=ACTIVITY_CHECKIN_WALL_SETTINGS_PARAM_KEY,
                config_value=value,
                config_type=True,
                status="0",
                description="活动大屏签到墙插件全局配置",
            )
            param.created_id = auth.user.id if auth.user else None
            auth.db.add(param)
        else:
            param.config_name = "活动大屏签到墙设置"
            param.config_value = value
            param.config_type = True
            param.status = "0"
            param.description = "活动大屏签到墙插件全局配置"
            param.updated_id = auth.user.id if auth.user else None
        await auth.db.flush()
        return settings_value

    @classmethod
    def _apply_checkin_wall_settings(cls, config: dict[str, Any], checkin_wall_settings: dict[str, Any]) -> dict[str, Any]:
        module_config = deepcopy(config.get("module_config") or {})
        wall_config = {**(module_config.get("checkin_wall") or {"enabled": True, "settings": {}})}
        wall_config["settings"] = cls._normalize_checkin_wall_settings(checkin_wall_settings)
        module_config["checkin_wall"] = wall_config
        config["module_config"] = module_config
        return config

    @classmethod
    def _normalize_music_settings(cls, value: dict[str, Any] | None) -> dict[str, Any]:
        config = deepcopy(DEFAULT_ACTIVITY_MUSIC_SETTINGS)
        if value:
            config.update(value)
        mode = str(config.get("play_mode") or "list_loop").lower()
        config["volume"] = min(max(int(config.get("volume") or 60), 0), 100)
        config["play_mode"] = mode if mode in {"list_loop", "single_loop", "random"} else "list_loop"
        categories = []
        seen_categories = set()
        for item in config.get("categories") or []:
            category_id = str(item.get("id") or "").strip()
            name = str(item.get("name") or "").strip()
            if not category_id or not name or category_id in seen_categories:
                continue
            seen_categories.add(category_id)
            categories.append({"id": category_id[:64], "name": name[:32]})
        config["categories"] = categories or deepcopy(DEFAULT_ACTIVITY_MUSIC_SETTINGS["categories"])
        category_ids = {item["id"] for item in config["categories"]}
        tracks = []
        seen_tracks = set()
        for index, item in enumerate(config.get("tracks") or []):
            track_id = str(item.get("id") or "").strip()
            url = str(item.get("url") or "").strip()
            if not track_id or not url or track_id in seen_tracks:
                continue
            category_id = str(item.get("category_id") or "").strip()
            seen_tracks.add(track_id)
            tracks.append(
                {
                    "id": track_id[:64],
                    "name": (str(item.get("name") or item.get("file_name") or "未命名音乐").strip()[:64] or "未命名音乐"),
                    "url": url[:1000],
                    "file_name": str(item.get("file_name") or "").strip()[:255],
                    "category_id": category_id if category_id in category_ids else "",
                    "enabled": item.get("enabled") is not False,
                    "sort": int(item.get("sort") if item.get("sort") is not None else index + 1),
                }
            )
        config["tracks"] = sorted(tracks, key=lambda row: row["sort"])
        return config

    @classmethod
    async def activity_music_settings(cls, db: AsyncSession) -> dict[str, Any]:
        raw = await cls._param(db, ACTIVITY_MUSIC_SETTINGS_PARAM_KEY)
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {}
        return cls._normalize_music_settings(data)

    @classmethod
    async def update_activity_music_settings(cls, auth: AuthSchema, data: ScreenActivityMusicSettingsSchema) -> dict[str, Any]:
        settings_value = cls._normalize_music_settings(data.model_dump())
        value = json.dumps(settings_value, ensure_ascii=False)
        param = await auth.db.scalar(select(ParamsModel).where(ParamsModel.config_key == ACTIVITY_MUSIC_SETTINGS_PARAM_KEY, ParamsModel.is_deleted == False))
        if param is None:
            param = ParamsModel(config_name="活动大屏背景音乐设置", config_key=ACTIVITY_MUSIC_SETTINGS_PARAM_KEY, config_value=value, config_type=True, status="0", description="活动大屏背景音乐插件全局配置")
            param.created_id = auth.user.id if auth.user else None
            auth.db.add(param)
        else:
            param.config_name = "活动大屏背景音乐设置"
            param.config_value = value
            param.config_type = True
            param.status = "0"
            param.description = "活动大屏背景音乐插件全局配置"
            param.updated_id = auth.user.id if auth.user else None
        await auth.db.flush()
        return settings_value

    @classmethod
    def _apply_music_settings(cls, config: dict[str, Any], music_settings: dict[str, Any]) -> dict[str, Any]:
        module_config = deepcopy(config.get("module_config") or {})
        music_config = {**(module_config.get("music") or {"enabled": False, "settings": {}})}
        music_config["settings"] = cls._normalize_music_settings(music_settings)
        module_config["music"] = music_config
        config["module_config"] = module_config
        return config

    @classmethod
    async def _apply_activity_plugin_settings(cls, db: AsyncSession, config: dict[str, Any]) -> dict[str, Any]:
        config = cls._apply_qrcode_settings(config, await cls.activity_qrcode_settings(db))
        config = cls._apply_checkin_wall_settings(config, await cls.activity_checkin_wall_settings(db))
        config = cls._apply_dominate_settings(config, await cls.activity_dominate_settings(db))
        config = cls._apply_music_settings(config, await cls.activity_music_settings(db))
        return config

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

    @staticmethod
    def _new_activity_scene() -> str:
        return f"as{secrets.token_hex(10)}"

    @staticmethod
    def _activity_theme_config(value: dict[str, Any] | None) -> dict[str, Any]:
        config = deepcopy(DEFAULT_ACTIVITY_THEME_CONFIG)
        config.update(value or {})
        backgrounds = config.get("backgrounds")
        config["backgrounds"] = backgrounds if isinstance(backgrounds, list) else []
        config["show_people_count"] = bool(config.get("show_people_count"))
        return config

    @staticmethod
    def _activity_module_config(value: dict[str, Any] | None) -> dict[str, Any]:
        config = deepcopy(DEFAULT_ACTIVITY_MODULE_CONFIG)
        for key, item in (value or {}).items():
            if isinstance(item, dict):
                base = config.get(key, {"enabled": False, "settings": {}})
                merged = {**base, **item}
                merged["settings"] = {**(base.get("settings") or {}), **(item.get("settings") or {})}
                config[key] = merged
        return config

    @staticmethod
    def _active_background(theme_config: dict[str, Any]) -> dict[str, Any] | None:
        active_id = str(theme_config.get("active_background_id") or "")
        backgrounds = theme_config.get("backgrounds") or []
        if active_id:
            for item in backgrounds:
                if str(item.get("id") or "") == active_id:
                    return item
        return backgrounds[0] if backgrounds else None

    @classmethod
    async def _generate_activity_qrcode(cls, db: AsyncSession, row: ScreenActivityConfigModel, user_id: int | None = None) -> None:
        access_token = await cls._wechat_access_token(db)
        async with httpx.AsyncClient(timeout=settings.HTTPX_DEFAULT_TIMEOUT) as client:
            response = await client.post(
                "https://api.weixin.qq.com/wxa/getwxacodeunlimit",
                params={"access_token": access_token},
                json={"scene": row.checkin_scene, "page": MINI_ACTIVITY_CHECKIN_PAGE, "check_path": False},
            )
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            payload = response.json()
            raise CustomException(msg=f"生成活动签到小程序码失败: {payload.get('errmsg')}", data=payload)
        file_url, file_path = await cls._upload_qrcode_bytes(response.content, f"screen_activity_{row.id}_{row.checkin_scene}.png")
        row.qrcode_url = file_url
        row.qrcode_file_path = file_path
        row.qrcode_generated_at = datetime.now()
        row.updated_id = user_id

    @classmethod
    async def _activity_by_id(cls, db: AsyncSession, activity_id: int) -> ScreenActivityConfigModel:
        row = await db.scalar(
            select(ScreenActivityConfigModel)
            .where(ScreenActivityConfigModel.id == activity_id, ScreenActivityConfigModel.is_deleted == False)
            .options(selectinload(ScreenActivityConfigModel.event).selectinload(EventModel.store))
        )
        if not row:
            raise CustomException(msg="活动大屏不存在")
        return row

    @classmethod
    async def _activity_by_scene(cls, db: AsyncSession, scene: str) -> ScreenActivityConfigModel:
        row = await db.scalar(
            select(ScreenActivityConfigModel)
            .where(
                ScreenActivityConfigModel.checkin_scene == scene,
                ScreenActivityConfigModel.enabled == True,
                ScreenActivityConfigModel.status == "0",
                ScreenActivityConfigModel.is_deleted == False,
            )
            .options(selectinload(ScreenActivityConfigModel.event).selectinload(EventModel.store))
        )
        if not row or not row.event or row.event.is_deleted or row.event.event_status not in {"published", "finished"}:
            raise CustomException(msg="签到二维码无效或活动未发布")
        return row

    @classmethod
    async def _activity_by_event(cls, db: AsyncSession, event_id: int) -> ScreenActivityConfigModel:
        row = await db.scalar(
            select(ScreenActivityConfigModel)
            .where(
                ScreenActivityConfigModel.event_id == event_id,
                ScreenActivityConfigModel.enabled == True,
                ScreenActivityConfigModel.status == "0",
                ScreenActivityConfigModel.is_deleted == False,
            )
            .options(selectinload(ScreenActivityConfigModel.event).selectinload(EventModel.store))
        )
        if not row or not row.event or row.event.is_deleted or row.event.event_status not in {"published", "finished"}:
            raise CustomException(msg="活动大屏未启用")
        return row

    @classmethod
    def _event_brief(cls, event: EventModel | None) -> dict[str, Any] | None:
        if not event:
            return None
        return {
            "id": event.id,
            "title": event.title,
            "subtitle": event.subtitle,
            "event_type": event.event_type,
            "cover_url": event.cover_url,
            "location": event.location,
            "store_id": event.store_id,
            "store_name": event.store.name if event.store else None,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "register_deadline": event.register_deadline,
            "event_status": event.event_status,
        }

    @classmethod
    async def _activity_counts(cls, db: AsyncSession, event_ids: list[int]) -> dict[int, dict[str, int]]:
        if not event_ids:
            return {}
        registered_rows = (
            await db.execute(
                select(EventRegistrationModel.event_id, func.count(EventRegistrationModel.id))
                .where(
                    EventRegistrationModel.event_id.in_(event_ids),
                    EventRegistrationModel.registration_status.in_(["registered", "checked_in"]),
                    EventRegistrationModel.is_deleted == False,
                )
                .group_by(EventRegistrationModel.event_id)
            )
        ).all()
        participant_rows = (
            await db.execute(
                select(EventParticipantModel.event_id, func.count(EventParticipantModel.id))
                .where(
                    EventParticipantModel.event_id.in_(event_ids),
                    EventParticipantModel.participant_status == "checked_in",
                    EventParticipantModel.is_deleted == False,
                )
                .group_by(EventParticipantModel.event_id)
            )
        ).all()
        data = {event_id: {"registered_count": 0, "checkin_count": 0} for event_id in event_ids}
        for event_id, count in registered_rows:
            data[event_id]["registered_count"] = count
        for event_id, count in participant_rows:
            data[event_id]["checkin_count"] = count
        return data

    @classmethod
    def _activity_out(cls, row: ScreenActivityConfigModel, counts: dict[str, int] | None = None, online: bool = False) -> dict[str, Any]:
        counts = counts or {"registered_count": 0, "checkin_count": 0}
        theme_config = cls._activity_theme_config(row.theme_config)
        module_config = cls._activity_module_config(row.module_config)
        active_background = cls._active_background(theme_config)
        return {
            "id": row.id,
            "brand_id": row.brand_id,
            "store_id": row.store_id,
            "event_id": row.event_id,
            "event": cls._event_brief(row.event),
            "screen_name": row.screen_name or row.title or (row.event.title if row.event else ""),
            "title": row.event.title if row.event else row.title or "",
            "subtitle": row.event.subtitle if row.event else row.subtitle or "",
            "background_url": row.background_url,
            "active_background": active_background,
            "theme_config": theme_config,
            "module_config": module_config,
            "enabled": row.enabled,
            "current_scene": "blank" if row.current_scene == "home" else row.current_scene,
            "show_qrcode": row.show_qrcode,
            "qrcode_url": row.qrcode_url,
            "qrcode_page": row.qrcode_page,
            "checkin_scene": row.checkin_scene,
            "qrcode_generated_at": row.qrcode_generated_at,
            "last_command": row.last_command or {},
            "last_command_at": row.last_command_at,
            "status": row.status,
            "registered_count": counts.get("registered_count", 0),
            "checkin_count": counts.get("checkin_count", 0),
            "online": online,
            "created_time": row.created_time,
            "updated_time": row.updated_time,
        }

    @classmethod
    async def page_activities(cls, auth: AuthSchema, page_no: int, page_size: int, search: ScreenActivityQueryParam) -> dict[str, Any]:
        conditions: list[Any] = [ScreenActivityConfigModel.is_deleted == False]
        if search.enabled is not None:
            conditions.append(ScreenActivityConfigModel.enabled == search.enabled)
        stmt = select(ScreenActivityConfigModel).join(EventModel, ScreenActivityConfigModel.event_id == EventModel.id).outerjoin(DeptModel, EventModel.store_id == DeptModel.id)
        if search.keyword:
            like = f"%{search.keyword}%"
            conditions.append(or_(ScreenActivityConfigModel.screen_name.ilike(like), EventModel.title.ilike(like), DeptModel.name.ilike(like)))
        total = await auth.db.scalar(select(func.count(ScreenActivityConfigModel.id)).select_from(ScreenActivityConfigModel).join(EventModel, ScreenActivityConfigModel.event_id == EventModel.id).outerjoin(DeptModel, EventModel.store_id == DeptModel.id).where(*conditions)) or 0
        rows = (
            await auth.db.execute(
                stmt.where(*conditions)
                .options(selectinload(ScreenActivityConfigModel.event).selectinload(EventModel.store))
                .order_by(ScreenActivityConfigModel.updated_time.desc(), ScreenActivityConfigModel.id.desc())
                .offset((page_no - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        counts = await cls._activity_counts(auth.db, [row.event_id for row in rows])
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": [cls._activity_out(row, counts.get(row.event_id)) for row in rows],
        }

    @classmethod
    async def _event_for_activity(cls, db: AsyncSession, event_id: int) -> EventModel:
        row = await db.scalar(
            select(EventModel)
            .where(EventModel.id == event_id, EventModel.is_deleted == False)
            .options(selectinload(EventModel.store))
        )
        if not row:
            raise CustomException(msg="活动不存在")
        return row

    @classmethod
    async def create_activity(cls, auth: AuthSchema, data: ScreenActivityConfigSchema) -> dict[str, Any]:
        event = await cls._event_for_activity(auth.db, data.event_id)
        exists = await auth.db.scalar(select(ScreenActivityConfigModel.id).where(ScreenActivityConfigModel.event_id == data.event_id, ScreenActivityConfigModel.is_deleted == False))
        if exists:
            raise CustomException(msg="该活动已创建活动大屏")
        payload = data.model_dump()
        payload.pop("event_id", None)
        row = ScreenActivityConfigModel(
            brand_id=event.brand_id,
            store_id=event.store_id,
            event_id=event.id,
            checkin_scene=cls._new_activity_scene(),
            qrcode_page=MINI_ACTIVITY_CHECKIN_PAGE,
            screen_name=payload.pop("screen_name", None) or event.title,
            module_config=cls._activity_module_config(payload.pop("module_config", None)),
            theme_config=cls._activity_theme_config(payload.pop("theme_config", None)),
            current_scene=payload.pop("current_scene", "blank") or "blank",
            **payload,
        )
        row.created_id = auth.user.id if auth.user else None
        auth.db.add(row)
        await auth.db.flush()
        await cls._generate_activity_qrcode(auth.db, row, auth.user.id if auth.user else None)
        await auth.db.flush()
        row.event = event
        return cls._activity_out(row)

    @classmethod
    async def update_activity(cls, auth: AuthSchema, activity_id: int, data: ScreenActivityConfigSchema) -> dict[str, Any]:
        row = await cls._activity_by_id(auth.db, activity_id)
        event = await cls._event_for_activity(auth.db, data.event_id)
        if event.id != row.event_id:
            exists = await auth.db.scalar(select(ScreenActivityConfigModel.id).where(ScreenActivityConfigModel.event_id == event.id, ScreenActivityConfigModel.is_deleted == False))
            if exists:
                raise CustomException(msg="该活动已创建活动大屏")
        payload = data.model_dump()
        payload["screen_name"] = payload.get("screen_name") or event.title
        payload["module_config"] = cls._activity_module_config(payload.get("module_config"))
        payload["theme_config"] = cls._activity_theme_config(payload.get("theme_config"))
        for key, value in payload.items():
            setattr(row, key, value)
        row.store_id = event.store_id
        row.updated_id = auth.user.id if auth.user else None
        await auth.db.flush()
        row.event = event
        return cls._activity_out(row, (await cls._activity_counts(auth.db, [row.event_id])).get(row.event_id))

    @classmethod
    async def delete_activity(cls, auth: AuthSchema, activity_id: int) -> dict[str, Any]:
        row = await cls._activity_by_id(auth.db, activity_id)
        row.is_deleted = True
        row.deleted_time = datetime.now()
        row.deleted_id = auth.user.id if auth.user else None
        await auth.db.flush()
        return {"id": activity_id}

    @classmethod
    async def detail_activity(cls, db: AsyncSession, activity_id: int) -> dict[str, Any]:
        row = await cls._activity_by_id(db, activity_id)
        counts = await cls._activity_counts(db, [row.event_id])
        return await cls._apply_activity_plugin_settings(db, cls._activity_out(row, counts.get(row.event_id)))

    @classmethod
    async def regenerate_activity_qrcode(cls, auth: AuthSchema, activity_id: int) -> dict[str, Any]:
        row = await cls._activity_by_id(auth.db, activity_id)
        row.checkin_scene = cls._new_activity_scene()
        row.qrcode_page = MINI_ACTIVITY_CHECKIN_PAGE
        await cls._generate_activity_qrcode(auth.db, row, auth.user.id if auth.user else None)
        await auth.db.flush()
        return cls._activity_out(row, (await cls._activity_counts(auth.db, [row.event_id])).get(row.event_id))

    @classmethod
    async def activity_participants(cls, db: AsyncSession, activity_id: int, limit: int = 30) -> dict[str, Any]:
        row = await cls._activity_by_id(db, activity_id)
        participants = (
            await db.execute(
                select(EventParticipantModel)
                .where(
                    EventParticipantModel.event_id == row.event_id,
                    EventParticipantModel.participant_status == "checked_in",
                    EventParticipantModel.is_deleted == False,
                )
                .options(selectinload(EventParticipantModel.mp_user), selectinload(EventParticipantModel.person))
                .order_by(EventParticipantModel.checked_in_at.desc(), EventParticipantModel.id.desc())
                .limit(limit)
            )
        ).scalars().all()
        items = []
        for item in participants:
            snapshot = item.profile_snapshot or {}
            photos = snapshot.get("photo_urls") or []
            items.append(
                {
                    "id": item.id,
                    "onsite_no": item.onsite_no,
                    "display_nickname": item.display_nickname or snapshot.get("name") or "现场嘉宾",
                    "gender": item.gender_snapshot,
                    "avatar_url": (photos[0] if photos else None) or (item.mp_user.avatar_url if item.mp_user else None),
                    "checkin_type": item.checkin_type,
                    "checked_in_at": item.checked_in_at,
                }
            )
        counts = await cls._activity_counts(db, [row.event_id])
        return {"items": items, "counts": counts.get(row.event_id, {"registered_count": 0, "checkin_count": 0})}

    @staticmethod
    def _barrage_out(row: ScreenActivityBarrageModel, settings: dict[str, Any] | None = None) -> dict[str, Any]:
        settings = settings or DEFAULT_ACTIVITY_BARRAGE_SETTINGS
        return {
            "id": row.id,
            "activity_id": row.activity_id,
            "event_id": row.event_id,
            "mp_user_id": row.mp_user_id,
            "nickname": row.nickname,
            "avatar_url": row.avatar_url,
            "content": row.content,
            "display_status": row.display_status,
            "displayed_at": row.displayed_at,
            "created_time": row.created_time,
            "duration_seconds": settings["duration_seconds"],
            "size": settings["size"],
        }

    @classmethod
    async def activity_barrages(cls, db: AsyncSession, activity_id: int, limit: int = 30) -> dict[str, Any]:
        await cls._activity_by_id(db, activity_id)
        rows = (
            await db.execute(
                select(ScreenActivityBarrageModel)
                .where(
                    ScreenActivityBarrageModel.activity_id == activity_id,
                    ScreenActivityBarrageModel.display_status == "displayed",
                    ScreenActivityBarrageModel.is_deleted == False,
                )
                .order_by(ScreenActivityBarrageModel.id.desc())
                .limit(limit)
            )
        ).scalars().all()
        settings = await cls.activity_barrage_settings(db)
        return {"items": [cls._barrage_out(row, settings) for row in reversed(rows)]}

    @classmethod
    async def create_barrage(cls, db: AsyncSession, event_id: int, user_id: int, content: str) -> dict[str, Any]:
        activity = await cls._activity_by_event(db, event_id)
        module_config = cls._activity_module_config(activity.module_config)
        barrage_config = module_config.get("barrage") or {}
        if barrage_config.get("enabled") is not True:
            raise CustomException(msg="现场弹幕暂未开启")
        settings_config = await cls.activity_barrage_settings(db)
        max_length = int(settings_config.get("max_length") or 50)
        clean = " ".join(content.strip().split())
        if not clean:
            raise CustomException(msg="请输入弹幕内容")
        if len(clean) > max_length:
            raise CustomException(msg=f"弹幕内容不能超过{max_length}个字")
        user = await db.scalar(
            select(MiniProgramUserModel)
            .where(MiniProgramUserModel.id == user_id, MiniProgramUserModel.is_deleted == False)
            .options(selectinload(MiniProgramUserModel.person))
        )
        if not user:
            raise CustomException(msg="用户不存在")
        person = user.person if user.person and not user.person.is_deleted else None
        photos = (person.photo_urls or []) if person else []
        row = ScreenActivityBarrageModel(
            brand_id=activity.brand_id,
            store_id=activity.store_id,
            activity_id=activity.id,
            event_id=activity.event_id,
            mp_user_id=user.id,
            person_id=user.person_id,
            nickname=cls._display_name(user, person) if person else user.nickname or "现场嘉宾",
            avatar_url=user.avatar_url or (photos[0] if photos else None),
            content=clean,
            display_status="displayed",
            displayed_at=datetime.now(),
        )
        db.add(row)
        await db.flush()
        return cls._barrage_out(row, settings_config)

    @classmethod
    async def player_activity_list(cls, db: AsyncSession, device: ScreenDeviceModel) -> dict[str, Any]:
        rows = (
            await db.execute(
                select(ScreenActivityConfigModel)
                .join(EventModel, ScreenActivityConfigModel.event_id == EventModel.id)
                .where(
                    ScreenActivityConfigModel.enabled == True,
                    ScreenActivityConfigModel.status == "0",
                    ScreenActivityConfigModel.is_deleted == False,
                    EventModel.is_deleted == False,
                    EventModel.event_status.in_(["published", "finished"]),
                )
                .options(selectinload(ScreenActivityConfigModel.event).selectinload(EventModel.store))
                .order_by(EventModel.start_time.desc(), ScreenActivityConfigModel.id.desc())
            )
        ).scalars().all()
        counts = await cls._activity_counts(db, [row.event_id for row in rows])
        device.last_sync_at = datetime.now()
        await db.flush()
        return {"items": [cls._activity_out(row, counts.get(row.event_id)) for row in rows]}

    @classmethod
    async def player_activity_detail(cls, db: AsyncSession, device: ScreenDeviceModel, activity_id: int) -> dict[str, Any]:
        row = await cls._activity_by_id(db, activity_id)
        if not row.enabled or row.status != "0" or not row.event or row.event.event_status not in {"published", "finished"}:
            raise CustomException(msg="活动大屏未启用")
        device.last_sync_at = datetime.now()
        await db.flush()
        config = await cls._apply_activity_plugin_settings(db, cls._activity_out(row, (await cls._activity_counts(db, [row.event_id])).get(row.event_id)))
        return {
            "config": config,
            "participants": (await cls.activity_participants(db, row.id, 30))["items"],
            "barrages": (await cls.activity_barrages(db, row.id, 30))["items"],
        }

    @classmethod
    async def activity_command(cls, auth: AuthSchema, activity_id: int, data: ScreenActivityCommandSchema) -> dict[str, Any]:
        row = await cls._activity_by_id(auth.db, activity_id)
        if data.command == "set_scene":
            value = str(data.value or "").strip().lower()
            if value not in {"blank", "checkin"}:
                raise CustomException(msg="场景只支持空白舞台或签到墙")
            row.current_scene = value
        elif data.command == "set_background":
            value = data.value if isinstance(data.value, dict) else {}
            background_id = str(value.get("background_id") or "")
            theme_config = cls._activity_theme_config(row.theme_config)
            if background_id and not any(str(item.get("id") or "") == background_id for item in theme_config["backgrounds"]):
                raise CustomException(msg="背景不存在")
            theme_config["active_background_id"] = background_id
            row.theme_config = theme_config
            active = cls._active_background(theme_config)
            row.background_url = active.get("url") if active and active.get("type") == "image" else None
        elif data.command == "toggle_module":
            value = data.value if isinstance(data.value, dict) else {}
            key = str(value.get("key") or "").strip()
            if not key:
                raise CustomException(msg="模块标识不能为空")
            module_config = cls._activity_module_config(row.module_config)
            module_config.setdefault(key, {"enabled": False, "settings": {}})
            module_config[key]["enabled"] = bool(value.get("enabled"))
            row.module_config = module_config
        elif data.command == "toggle_people_count":
            theme_config = cls._activity_theme_config(row.theme_config)
            theme_config["show_people_count"] = bool(data.value)
            row.theme_config = theme_config
        elif data.command == "toggle_qrcode":
            row.show_qrcode = bool(data.value)
        elif data.command == "clear_screen":
            row.current_scene = "blank"
        elif data.command == "dominate_play":
            module_config = cls._activity_module_config(row.module_config)
            if module_config.get("dominate", {}).get("enabled") is not True:
                raise CustomException(msg="当前活动未开启霸屏")
            settings = await cls.activity_dominate_settings(auth.db)
            value = data.value if isinstance(data.value, dict) else {}
            content = str(value.get("content") or "").strip()
            if not content:
                raise CustomException(msg="霸屏内容不能为空")
            max_length = int(settings["max_length"])
            data.value = {
                "id": cls._new_token()[:12],
                "nickname": (str(value.get("nickname") or "现场嘉宾").strip()[:24] or "现场嘉宾"),
                "avatar_url": str(value.get("avatar_url") or "").strip()[:1000],
                "content": content[:max_length],
                "duration_seconds": int(settings["duration_seconds"]),
                "created_at": datetime.now().isoformat(),
            }
        row.last_command = data.model_dump()
        row.last_command_at = datetime.now()
        row.updated_id = auth.user.id if auth.user else None
        await auth.db.flush()
        return await cls._apply_activity_plugin_settings(auth.db, cls._activity_out(row, (await cls._activity_counts(auth.db, [row.event_id])).get(row.event_id)))

    @classmethod
    async def create_activity_control_token(cls, auth: AuthSchema, redis: Redis, activity_id: int, origin: str) -> dict[str, Any]:
        await cls._activity_by_id(auth.db, activity_id)
        token = cls._new_token()
        payload = {
            "activity_id": activity_id,
            "user_id": auth.user.id if auth.user else None,
            "created_at": datetime.now().isoformat(),
        }
        await redis.setex(f"{CONTROL_TOKEN_PREFIX}{token}", CONTROL_TOKEN_TTL_SECONDS, json.dumps(payload, ensure_ascii=False))
        await redis.setex(f"{CONTROL_TOKEN_ACTIVITY_PREFIX}{activity_id}", CONTROL_TOKEN_TTL_SECONDS, token)
        return {
            "token": token,
            "expires_in": CONTROL_TOKEN_TTL_SECONDS,
            "control_url": f"{origin.rstrip('/')}/#/screen/activity-control?token={token}",
        }

    @classmethod
    async def verify_activity_control_token(cls, db: AsyncSession, redis: Redis, token: str) -> dict[str, Any]:
        if not token:
            raise CustomException(msg="活动控制台未授权", code=10401, status_code=401)
        raw = await redis.get(f"{CONTROL_TOKEN_PREFIX}{token}")
        if not raw:
            raise CustomException(msg="活动控制台授权已失效", code=10401, status_code=401)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        payload = json.loads(raw)
        activity_id = int(payload.get("activity_id") or 0)
        if not activity_id:
            raise CustomException(msg="活动控制台授权无效", code=10401, status_code=401)
        await cls._activity_by_id(db, activity_id)
        payload["activity_id"] = activity_id
        return payload

    @classmethod
    async def control_activity_detail(cls, db: AsyncSession, redis: Redis, token: str) -> dict[str, Any]:
        payload = await cls.verify_activity_control_token(db, redis, token)
        activity_id = payload["activity_id"]
        return {
            "config": await cls.detail_activity(db, activity_id),
            "participants": await cls.activity_participants(db, activity_id),
        }

    @classmethod
    async def control_activity_command(cls, db: AsyncSession, redis: Redis, token: str, data: ScreenActivityCommandSchema) -> dict[str, Any]:
        payload = await cls.verify_activity_control_token(db, redis, token)
        auth = AuthSchema(db=db, user=None, check_data_scope=False)
        return await cls.activity_command(auth, payload["activity_id"], data)

    @classmethod
    async def checkin_scene_context(cls, db: AsyncSession, scene: str, user_id: int | None = None) -> dict[str, Any]:
        row = await cls._activity_by_scene(db, scene)
        registration = None
        participant = None
        if user_id:
            user = await db.scalar(select(MiniProgramUserModel).where(MiniProgramUserModel.id == user_id, MiniProgramUserModel.is_deleted == False))
            if user:
                registration = await db.scalar(
                    select(EventRegistrationModel).where(
                        EventRegistrationModel.event_id == row.event_id,
                        EventRegistrationModel.mp_user_id == user.id,
                        EventRegistrationModel.is_deleted == False,
                    )
                )
                participant = await db.scalar(
                    select(EventParticipantModel).where(
                        EventParticipantModel.event_id == row.event_id,
                        EventParticipantModel.mp_user_id == user.id,
                        EventParticipantModel.is_deleted == False,
                    )
                )
        return {
            "activity_screen": cls._activity_out(row, (await cls._activity_counts(db, [row.event_id])).get(row.event_id)),
            "event": cls._event_brief(row.event),
            "registration": {"id": registration.id, "registration_status": registration.registration_status, "registration_no": registration.registration_no} if registration else None,
            "participant": {"id": participant.id, "onsite_no": participant.onsite_no, "participant_status": participant.participant_status} if participant else None,
            "can_checkin": not participant,
        }
