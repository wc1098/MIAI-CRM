import json
import secrets
from datetime import datetime, timedelta
from typing import Any

import httpx
import jwt
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.module_system.dict.model import DictDataModel
from app.api.v1.module_system.params.model import ParamsModel
from app.config.setting import settings
from app.core.base_schema import UploadResponseSchema
from app.core.exceptions import CustomException
from app.plugin.module_crm.lead.model import (
    CrmLeadLifecycleModel,
    CrmLeadProfileModel,
    CrmPersonModel,
)
from app.plugin.module_profile_ai.service import PersonAiProfileService
from app.utils.upload_util import UploadUtil

from .model import MiniProgramUserModel, SourceEventModel, UserAgreementAcceptanceModel
from .schema import MOBILE_PATTERN, MpAuthOutSchema, MpLoginSchema, MpRegisterSchema

MINIAPP_CHANNEL = "MINIAPP_REGISTER"
MP_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 30


class MpAuthService:
    """微信小程序认证与注册服务。"""

    @classmethod
    async def _generate_person_display_no(cls, db: AsyncSession) -> str:
        for _ in range(50):
            display_no = str(1000000 + secrets.randbelow(9000000))
            exists = (
                await db.execute(
                    select(CrmPersonModel.id).where(
                        CrmPersonModel.display_no == display_no,
                        CrmPersonModel.is_deleted == False,
                    )
                )
            ).scalar()
            if not exists:
                return display_no
        raise CustomException(msg="人员展示编号生成失败，请稍后重试")

    @classmethod
    async def _ensure_person_display_no(cls, db: AsyncSession, person: CrmPersonModel) -> None:
        if not person.display_no:
            person.display_no = await cls._generate_person_display_no(db)

    @classmethod
    async def _param(cls, db: AsyncSession, key: str, default: str | None = None) -> str | None:
        result = await db.execute(
            select(ParamsModel.config_value).where(
                ParamsModel.config_key == key,
                ParamsModel.status == "0",
                ParamsModel.is_deleted == False,
            )
        )
        value = result.scalar()
        return value if value not in (None, "") else default

    @classmethod
    async def register_options(cls, db: AsyncSession) -> dict[str, list[dict[str, str]]]:
        """返回小程序注册页使用的CRM字典选项。"""
        dict_map = {
            "ethnicity": "crm_ethnicity",
            "annual_income": "crm_annual_income",
            "marital_status": "crm_marital_status",
            "education": "crm_education",
            "house_status": "crm_house_status",
            "car_status": "crm_car_status",
        }
        rows = (
            await db.execute(
                select(DictDataModel)
                .where(
                    DictDataModel.dict_type.in_(dict_map.values()),
                    DictDataModel.status == "0",
                    DictDataModel.is_deleted == False,
                )
                .order_by(DictDataModel.dict_sort.asc(), DictDataModel.id.asc())
            )
        ).scalars().all()
        result = {key: [] for key in dict_map}
        reverse_map = {value: key for key, value in dict_map.items()}
        for row in rows:
            key = reverse_map.get(row.dict_type)
            if key:
                result[key].append({"label": row.dict_label, "value": row.dict_value})
        return result

    @classmethod
    async def upload_register_photo(cls, base_url: str, file: UploadFile) -> dict:
        """上传小程序注册照片。"""
        content_type = (file.content_type or "").lower()
        if not content_type.startswith("image/"):
            raise CustomException(msg="只能上传图片文件")
        filename, filepath, file_url = await UploadUtil.upload_file(file=file, base_url=base_url)
        return UploadResponseSchema(
            file_path=f"{filepath}",
            file_name=filename,
            origin_name=file.filename,
            file_url=f"{file_url}",
        ).model_dump()

    @classmethod
    async def _wechat_code_to_session(cls, db: AsyncSession, code: str) -> dict[str, str]:
        if code.startswith("mock:"):
            openid = code.split(":", 1)[1].strip() or "mock-openid"
            return {"openid": openid, "session_key": "mock-session-key"}

        app_id = await cls._param(db, "miniprogram.wechat.app_id")
        app_secret = await cls._param(db, "miniprogram.wechat.app_secret")
        if not app_id or not app_secret:
            raise CustomException(msg="请先配置微信小程序AppID和AppSecret，或使用mock:开头的本地调试code")

        async with httpx.AsyncClient(timeout=settings.HTTPX_DEFAULT_TIMEOUT) as client:
            response = await client.get(
                "https://api.weixin.qq.com/sns/jscode2session",
                params={
                    "appid": app_id,
                    "secret": app_secret,
                    "js_code": code,
                    "grant_type": "authorization_code",
                },
            )
        payload = response.json()
        if payload.get("errcode"):
            raise CustomException(msg=f"微信登录失败: {payload.get('errmsg')}", data=payload)
        if not payload.get("openid"):
            raise CustomException(msg="微信登录失败：未返回openid", data=payload)
        return payload

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
    async def _wechat_phone_number(cls, db: AsyncSession, phone_code: str) -> str:
        if MOBILE_PATTERN.match(phone_code):
            return phone_code
        if phone_code.startswith("mock:"):
            mobile = phone_code.split(":", 1)[1].strip()
            if not MOBILE_PATTERN.match(mobile):
                raise CustomException(msg="mock手机号格式不正确")
            return mobile

        access_token = await cls._wechat_access_token(db)
        async with httpx.AsyncClient(timeout=settings.HTTPX_DEFAULT_TIMEOUT) as client:
            response = await client.post(
                "https://api.weixin.qq.com/wxa/business/getuserphonenumber",
                params={"access_token": access_token},
                json={"code": phone_code},
        )
        payload = response.json()
        if payload.get("errcode"):
            if payload.get("errcode") == 40029:
                raise CustomException(msg="微信手机号授权已过期，请重新授权手机号", data=payload)
            raise CustomException(msg=f"获取微信手机号失败: {payload.get('errmsg')}", data=payload)
        mobile = (payload.get("phone_info") or {}).get("phoneNumber")
        if not mobile or not MOBILE_PATTERN.match(mobile):
            raise CustomException(msg="微信手机号格式不正确", data=payload)
        return mobile

    @classmethod
    def _create_mp_token(cls, user: MiniProgramUserModel) -> str:
        now = datetime.now()
        payload = {
            "sub": json.dumps({"mp_user_id": user.id, "openid": user.openid}, ensure_ascii=False),
            "token_type": "mp",
            "exp": now + timedelta(seconds=MP_TOKEN_EXPIRE_SECONDS),
        }
        return jwt.encode(payload=payload, key=settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @classmethod
    def decode_mp_token(cls, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(jwt=token, key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if payload.get("token_type") != "mp":
                raise CustomException(msg="非法小程序凭证", code=10401, status_code=401)
            return json.loads(payload["sub"])
        except (jwt.InvalidTokenError, KeyError, json.JSONDecodeError) as e:
            raise CustomException(msg="小程序登录已失效，请重新登录", code=10401, status_code=401) from e

    @classmethod
    async def _get_or_create_user(
        cls,
        db: AsyncSession,
        session: dict[str, str],
        mobile: str | None = None,
    ) -> MiniProgramUserModel:
        openid = session["openid"]
        openid_result = await db.execute(
            select(MiniProgramUserModel).where(
                MiniProgramUserModel.openid == openid,
                MiniProgramUserModel.is_deleted == False,
            )
        )
        user = openid_result.scalars().first()
        mobile_user = None
        if mobile:
            mobile_result = await db.execute(
                select(MiniProgramUserModel).where(
                    MiniProgramUserModel.mobile == mobile,
                    MiniProgramUserModel.is_deleted == False,
                )
            )
            mobile_user = mobile_result.scalars().first()
        now = datetime.now()
        if user and mobile_user and mobile_user.id != user.id:
            if mobile_user.openid:
                raise CustomException(msg="该手机号已绑定其他微信账号")
            if user.person_id or user.mobile:
                raise CustomException(msg="当前微信账号已绑定其他小程序用户")
            user.person_id = mobile_user.person_id
            user.mobile = mobile_user.mobile
            user.nickname = user.nickname or mobile_user.nickname
            user.avatar_url = user.avatar_url or mobile_user.avatar_url
            mobile_user.mobile = None
            mobile_user.person_id = None
            mobile_user.is_deleted = True
            mobile_user.deleted_time = now
        if not user:
            if mobile_user and not mobile_user.openid:
                user = mobile_user
                user.openid = openid
                user.last_login_at = now
            elif mobile_user and mobile_user.openid != openid:
                raise CustomException(msg="该手机号已绑定其他微信账号")
            else:
                user = MiniProgramUserModel(
                    brand_id=1,
                    openid=openid,
                    unionid=session.get("unionid"),
                    session_key=session.get("session_key"),
                    last_login_at=now,
                )
                db.add(user)
                await db.flush()
        else:
            user.unionid = session.get("unionid") or user.unionid
            user.session_key = session.get("session_key") or user.session_key
            user.last_login_at = now
        return user

    @classmethod
    def _person_payload(cls, data: MpRegisterSchema, mobile: str) -> dict[str, Any]:
        photo_urls = data.photo_urls[:]
        if data.avatar_url and data.avatar_url not in photo_urls:
            photo_urls.insert(0, data.avatar_url)
        return {
            "brand_id": 1,
            "name": data.name,
            "gender": data.gender,
            "primary_mobile": mobile,
            "wechat": data.wechat,
            "birth_date": data.birth_date,
            "height_cm": data.height_cm,
            "ethnicity": data.ethnicity,
            "occupation": data.occupation,
            "annual_income": data.annual_income,
            "marital_status": data.marital_status,
            "education": data.education,
            "hometown": data.hometown,
            "residence": data.residence,
            "house_status": data.house_status,
            "car_status": data.car_status,
            "photo_urls": photo_urls,
        }

    @classmethod
    def _fill_person_missing(cls, person: CrmPersonModel, payload: dict[str, Any]) -> None:
        for key, value in payload.items():
            if key in {"brand_id", "primary_mobile"}:
                continue
            current = getattr(person, key)
            if current in (None, "", []):
                setattr(person, key, value)

    @classmethod
    async def _append_source_event(
        cls,
        db: AsyncSession,
        person: CrmPersonModel,
        user: MiniProgramUserModel,
        data: MpRegisterSchema,
    ) -> SourceEventModel:
        event = SourceEventModel(
            brand_id=1,
            person_id=person.id,
            user_id=user.id,
            event_type="register",
            source_channel=MINIAPP_CHANNEL,
            source_id=data.source_id,
            source_user_id=data.source_user_id,
            payload=data.payload,
            occurred_at=datetime.now(),
        )
        db.add(event)
        await db.flush()
        return event

    @classmethod
    async def _write_lifecycle(cls, db: AsyncSession, lead: CrmLeadProfileModel, operation_type: str, detail: dict[str, Any]) -> None:
        record = CrmLeadLifecycleModel(
            brand_id=lead.brand_id,
            lead_id=lead.id,
            person_id=lead.person_id,
            operation_type=operation_type,
            change_detail=detail,
            remark="小程序注册入池",
        )
        db.add(record)

    @classmethod
    async def _upsert_register_lead(
        cls,
        db: AsyncSession,
        person: CrmPersonModel,
        event: SourceEventModel,
    ) -> CrmLeadProfileModel | None:
        push_lead = (await cls._param(db, "miniprogram.register.push_lead", "true") or "true").lower()
        if push_lead not in {"1", "true", "yes", "on"}:
            return None

        result = await db.execute(
            select(CrmLeadProfileModel).where(
                CrmLeadProfileModel.person_id == person.id,
                CrmLeadProfileModel.is_deleted == False,
                CrmLeadProfileModel.lead_type.notin_(["invalid", "converted_customer"]),
            )
        )
        lead = result.scalars().first()
        if lead:
            lead.source_channel_code = MINIAPP_CHANNEL
            if hasattr(lead, "latest_source_event_id"):
                lead.latest_source_event_id = event.id
            await cls._write_lifecycle(db, lead, "source_event", {"source_event_id": event.id, "source_channel_code": MINIAPP_CHANNEL})
            return lead

        lead = CrmLeadProfileModel(
            brand_id=1,
            person_id=person.id,
            store_id=None,
            owner_sales_id=None,
            pool_type="hq_pool",
            lead_type="pending",
            source_channel_code=MINIAPP_CHANNEL,
        )
        if hasattr(lead, "latest_source_event_id"):
            lead.latest_source_event_id = event.id
        db.add(lead)
        await db.flush()
        await cls._write_lifecycle(db, lead, "create", {"pool_type": "hq_pool", "source_event_id": event.id})
        return lead

    @classmethod
    def _out(cls, user: MiniProgramUserModel, person: CrmPersonModel | None = None, lead_id: int | None = None) -> dict:
        return MpAuthOutSchema(
            token=cls._create_mp_token(user),
            expires_in=MP_TOKEN_EXPIRE_SECONDS,
            is_registered=bool(user.person_id),
            user=user,
            person=person,
            lead_id=lead_id,
        ).model_dump()

    @classmethod
    async def login(cls, db: AsyncSession, data: MpLoginSchema) -> dict:
        session = await cls._wechat_code_to_session(db, data.code)
        user = await cls._get_or_create_user(db, session)
        person = None
        if user.person_id:
            result = await db.execute(select(CrmPersonModel).where(CrmPersonModel.id == user.person_id))
            person = result.scalars().first()
        return cls._out(user, person)

    @classmethod
    async def register(cls, db: AsyncSession, data: MpRegisterSchema, ip: str | None = None, device_info: str | None = None) -> dict:
        session = await cls._wechat_code_to_session(db, data.login_code)
        mobile = await cls._wechat_phone_number(db, data.phone_code)
        user = await cls._get_or_create_user(db, session, mobile=mobile)

        result = await db.execute(
            select(CrmPersonModel).where(
                CrmPersonModel.primary_mobile == mobile,
                CrmPersonModel.is_deleted == False,
            )
        )
        person = result.scalars().first()
        person_payload = cls._person_payload(data, mobile)
        if not person:
            person = CrmPersonModel(**person_payload)
            await cls._ensure_person_display_no(db, person)
            db.add(person)
            await db.flush()
        else:
            cls._fill_person_missing(person, person_payload)
            await cls._ensure_person_display_no(db, person)

        user.person_id = person.id
        user.mobile = mobile
        user.nickname = data.nickname
        user.avatar_url = data.avatar_url
        user.registered_at = user.registered_at or datetime.now()

        db.add(
            UserAgreementAcceptanceModel(
                user_id=user.id,
                agreement_type="register",
                agreement_version=data.agreement_version,
                agreement_title=data.agreement_title,
                accepted_at=datetime.now(),
                ip=ip,
                device_info=device_info,
            )
        )
        event = await cls._append_source_event(db, person, user, data)
        lead = await cls._upsert_register_lead(db, person, event)
        await PersonAiProfileService.enqueue_miai_impression(
            db=db,
            person_id=person.id,
            source_type="register",
            source_id=event.id,
        )
        await db.flush()
        await db.refresh(user)
        await db.refresh(person)
        return cls._out(user, person, lead.id if lead else None)

    @classmethod
    async def me(cls, db: AsyncSession, user_id: int) -> dict:
        result = await db.execute(
            select(MiniProgramUserModel)
            .where(MiniProgramUserModel.id == user_id, MiniProgramUserModel.is_deleted == False)
            .options(selectinload(MiniProgramUserModel.person))
        )
        user = result.scalars().first()
        if not user:
            raise CustomException(msg="小程序用户不存在", code=10401, status_code=401)
        lead_id = None
        if user.person_id:
            lead_result = await db.execute(
                select(CrmLeadProfileModel.id).where(
                    CrmLeadProfileModel.person_id == user.person_id,
                    CrmLeadProfileModel.is_deleted == False,
                    CrmLeadProfileModel.lead_type.notin_(["invalid", "converted_customer"]),
                )
            )
            lead_id = lead_result.scalar()
        return cls._out(user, user.person, lead_id)
