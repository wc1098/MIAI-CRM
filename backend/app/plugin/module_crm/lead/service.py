import secrets
from datetime import date, datetime, timedelta
from io import BytesIO
from typing import Any

import pandas as pd
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import UploadFile
from sqlalchemy import and_, create_engine, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool

from app.api.v1.module_system.auth.schema import AuthSchema
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.user.model import UserModel
from app.config.setting import get_settings
from app.core.database import async_db_session
from app.core.exceptions import CustomException
from app.core.logger import log
from app.plugin.module_crm.preference.schema import PartnerPreferenceSaveSchema
from app.plugin.module_crm.preference.service import PartnerPreferenceService
from app.plugin.module_match.service import MatchProfileService
from app.plugin.module_mp.auth.model import MiniProgramUserModel
from app.plugin.module_profile_ai.service import PersonAiProfileService
from app.utils.excel_util import ExcelUtil

from ..channel.model import CrmChannelModel
from .model import (
    CrmLeadImportBatchModel,
    CrmLeadLifecycleModel,
    CrmLeadProcessRecordModel,
    CrmLeadProfileModel,
    CrmLeadStoreRuleModel,
    CrmPersonModel,
)
from .schema import (
    LeadAssignSchema,
    LeadClaimSchema,
    LeadCreateSchema,
    LeadDetailOutSchema,
    LeadImportResultSchema,
    LeadLifecycleOutSchema,
    LeadMobileCheckSchema,
    LeadOutSchema,
    LeadPersonPayload,
    LeadProcessCreateSchema,
    LeadProcessOutSchema,
    LeadQueryParam,
    LeadStoreRuleSchema,
    LeadUpdateSchema,
)

LEAD_RECLAIM_WORKER_JOB_ID = "crm_lead_reclaim_worker"
DEFAULT_RECLAIM_WORKER_INTERVAL_SECONDS = 3600


class LeadService:
    """线索服务层"""

    IMPORT_HEADERS = [
        "手机号",
        "姓名",
        "性别",
        "微信号",
        "出生日期",
        "身高",
        "民族",
        "职业",
        "年收入",
        "婚况",
        "学历",
        "籍贯",
        "常驻地",
        "房产信息",
        "购车信息",
        "来源渠道",
        "归属门店",
        "归属人",
        "备注",
    ]

    @classmethod
    def register_scheduler(cls) -> None:
        """注册线索自动回公海任务。"""

        from app.core.ap_scheduler import scheduler

        scheduler.add_job(
            func=cls.process_overdue_reclaim_tasks,
            trigger=IntervalTrigger(seconds=cls._reclaim_worker_interval_seconds(), timezone="Asia/Shanghai"),
            id=LEAD_RECLAIM_WORKER_JOB_ID,
            name="CRM线索无跟进自动回公海任务",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            jobstore="default",
            executor="default",
        )

    @classmethod
    def _reclaim_worker_interval_seconds(cls) -> int:
        return cls._sync_int_param(
            "crm.lead.reclaim.worker_interval_seconds",
            DEFAULT_RECLAIM_WORKER_INTERVAL_SECONDS,
            300,
            86400,
        )

    @classmethod
    def _sync_int_param(cls, key: str, default: int, min_value: int = 1, max_value: int | None = None) -> int:
        engine = None
        try:
            settings = get_settings()
            engine = create_engine(settings.SYNC_DB_URI, poolclass=NullPool)
            with engine.connect() as conn:
                value = conn.execute(
                    text(
                        """
                        select config_value
                        from sys_param
                        where config_key = :key
                          and is_deleted = false
                        limit 1
                        """
                    ),
                    {"key": key},
                ).scalar()
        except Exception:
            log.exception(f"读取系统参数失败，使用默认值: {key}={default}")
            return default
        finally:
            if engine is not None:
                engine.dispose()
        try:
            parsed = int(value) if value not in (None, "") else default
        except (TypeError, ValueError):
            parsed = default
        if parsed < min_value:
            return min_value
        if max_value is not None and parsed > max_value:
            return max_value
        return parsed

    @classmethod
    def _role_codes(cls, auth: AuthSchema) -> set[str]:
        if not auth.user:
            return set()
        return {role.code for role in auth.user.roles or [] if role.status == "0"}

    @classmethod
    def _is_brand_admin(cls, auth: AuthSchema) -> bool:
        if auth.user and auth.user.is_superuser:
            return True
        return bool(cls._role_codes(auth) & {"ADMIN", "HQ_OPS"})

    @classmethod
    def _is_store_mgr(cls, auth: AuthSchema) -> bool:
        return "STORE_MGR" in cls._role_codes(auth)

    @classmethod
    def _is_sales(cls, auth: AuthSchema) -> bool:
        return "SALES" in cls._role_codes(auth)

    @classmethod
    def _stamp_create(cls, auth: AuthSchema, obj: Any) -> None:
        if auth.user:
            if hasattr(obj, "created_id"):
                obj.created_id = auth.user.id
            if hasattr(obj, "updated_id"):
                obj.updated_id = auth.user.id

    @classmethod
    def _stamp_update(cls, auth: AuthSchema, obj: Any) -> None:
        if auth.user and hasattr(obj, "updated_id"):
            obj.updated_id = auth.user.id

    @classmethod
    def _mask_mobile(cls, mobile: str | None) -> str | None:
        if not mobile or len(mobile) < 7:
            return mobile
        return f"{mobile[:3]}****{mobile[-4:]}"

    @classmethod
    def _mask_wechat(cls, wechat: str | None) -> str | None:
        if not wechat:
            return wechat
        if len(wechat) <= 4:
            return "****"
        return f"{wechat[:2]}****{wechat[-2:]}"

    @classmethod
    def _age(cls, birth_date: date | None) -> int | None:
        if not birth_date:
            return None
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    @classmethod
    def _constellation(cls, birth_date: date | None) -> str | None:
        if not birth_date:
            return None
        boundaries = [
            ((1, 20), "水瓶座"),
            ((2, 19), "双鱼座"),
            ((3, 21), "白羊座"),
            ((4, 20), "金牛座"),
            ((5, 21), "双子座"),
            ((6, 22), "巨蟹座"),
            ((7, 23), "狮子座"),
            ((8, 23), "处女座"),
            ((9, 23), "天秤座"),
            ((10, 24), "天蝎座"),
            ((11, 23), "射手座"),
            ((12, 22), "摩羯座"),
        ]
        month_day = (birth_date.month, birth_date.day)
        for index, (boundary, _) in enumerate(boundaries):
            if month_day < boundary:
                return "摩羯座" if index == 0 else boundaries[index - 1][1]
        return "摩羯座"

    @classmethod
    def _zodiac(cls, birth_date: date | None) -> str | None:
        if not birth_date:
            return None
        animals = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
        return animals[(birth_date.year - 1900) % 12]

    @classmethod
    async def _generate_person_display_no(cls, auth: AuthSchema) -> str:
        for _ in range(50):
            display_no = str(1000000 + secrets.randbelow(9000000))
            exists = (
                await auth.db.execute(
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
    async def _ensure_person_display_no(cls, auth: AuthSchema, person: CrmPersonModel) -> None:
        if not person.display_no:
            person.display_no = await cls._generate_person_display_no(auth)

    @classmethod
    async def _sync_person_to_miniprogram_user(cls, auth: AuthSchema, person: CrmPersonModel) -> MiniProgramUserModel:
        """创建或补全后台预置的小程序待绑定用户。"""

        result = await auth.db.execute(
            select(MiniProgramUserModel).where(
                MiniProgramUserModel.mobile == person.primary_mobile,
                MiniProgramUserModel.is_deleted == False,
            )
        )
        user = result.scalars().first()
        first_photo = (person.photo_urls or [None])[0]
        if user:
            if not user.person_id:
                user.person_id = person.id
            if not user.nickname:
                user.nickname = person.name
            if not user.avatar_url and first_photo:
                user.avatar_url = first_photo
            return user

        user = MiniProgramUserModel(
            brand_id=person.brand_id,
            person_id=person.id,
            openid=None,
            mobile=person.primary_mobile,
            nickname=person.name,
            avatar_url=first_photo,
            registered_at=None,
        )
        auth.db.add(user)
        await auth.db.flush()
        return user

    @classmethod
    def _validate_miniprogram_sync_required(cls, data: LeadCreateSchema) -> None:
        missing = []
        required_fields = [
            ("mobile", "手机号"),
            ("name", "姓名"),
            ("gender", "性别"),
            ("wechat", "微信号"),
            ("birth_date", "出生日期"),
            ("height_cm", "身高"),
            ("ethnicity", "民族"),
            ("occupation", "职业"),
            ("annual_income", "年收入"),
            ("marital_status", "婚况"),
            ("education", "学历"),
            ("hometown", "籍贯"),
            ("residence", "常驻地"),
            ("house_status", "房产信息"),
            ("car_status", "购车信息"),
        ]
        for field, label in required_fields:
            value = getattr(data, field)
            if value is None or value == "":
                missing.append(label)
        if not data.photo_urls:
            missing.append("照片")
        if missing:
            raise CustomException(msg=f"同步到小程序前请补齐：{'、'.join(missing)}")

    @classmethod
    def _can_view_contact(cls, auth: AuthSchema, lead: CrmLeadProfileModel) -> bool:
        if cls._is_brand_admin(auth) or cls._is_store_mgr(auth):
            return True
        return bool(auth.user and lead.owner_sales_id == auth.user.id)

    @classmethod
    async def _channel_names(cls, auth: AuthSchema) -> dict[str, str]:
        result = await auth.db.execute(select(CrmChannelModel).where(CrmChannelModel.is_deleted == False))
        return {row.channel_code: row.channel_name for row in result.scalars().all()}

    @classmethod
    async def _user_names(cls, auth: AuthSchema, ids: set[int]) -> dict[int, str]:
        if not ids:
            return {}
        result = await auth.db.execute(select(UserModel.id, UserModel.name).where(UserModel.id.in_(ids)))
        return {row[0]: row[1] for row in result.all()}

    @classmethod
    async def sales_options_service(cls, auth: AuthSchema, store_id: int | None = None) -> list[dict]:
        conditions: list[Any] = [UserModel.is_deleted == False, UserModel.status == "0"]
        if cls._is_brand_admin(auth):
            if store_id:
                conditions.append(UserModel.dept_id == store_id)
        elif auth.user and auth.user.dept_id:
            conditions.append(UserModel.dept_id == auth.user.dept_id)
        else:
            return []

        result = await auth.db.execute(
            select(UserModel)
            .where(and_(*conditions))
            .options(selectinload(UserModel.roles), selectinload(UserModel.positions))
            .order_by(UserModel.id.asc())
        )
        users = result.scalars().all()
        data: list[dict] = []
        for user in users:
            role_codes = {role.code for role in user.roles or [] if role.status == "0"}
            position_names = {position.name for position in user.positions or [] if position.status == "0"}
            if "SALES" not in role_codes and "销售" not in position_names:
                continue
            data.append({"id": user.id, "name": user.name, "dept_id": user.dept_id})
        return data

    @classmethod
    async def _dept_names(cls, auth: AuthSchema, ids: set[int]) -> dict[int, str]:
        if not ids:
            return {}
        result = await auth.db.execute(select(DeptModel.id, DeptModel.name).where(DeptModel.id.in_(ids)))
        return {row[0]: row[1] for row in result.all()}

    @classmethod
    async def store_options_service(cls, auth: AuthSchema) -> list[dict]:
        conditions: list[Any] = [
            DeptModel.is_deleted == False,
            DeptModel.status == "0",
            DeptModel.parent_id.is_not(None),
        ]
        if not cls._is_brand_admin(auth):
            if not auth.user or not auth.user.dept_id:
                return []
            conditions.append(DeptModel.id == auth.user.dept_id)
        result = await auth.db.execute(select(DeptModel.id, DeptModel.name).where(and_(*conditions)).order_by(DeptModel.order.asc(), DeptModel.id.asc()))
        return [{"id": row[0], "name": row[1]} for row in result.all()]

    @classmethod
    async def source_options_service(cls, auth: AuthSchema) -> list[dict]:
        result = await auth.db.execute(
            select(CrmChannelModel.channel_code, CrmChannelModel.channel_name)
            .where(CrmChannelModel.is_deleted == False, CrmChannelModel.status == "0")
            .order_by(CrmChannelModel.sort.asc(), CrmChannelModel.id.asc())
        )
        return [{"id": index + 1, "name": row[1], "code": row[0]} for index, row in enumerate(result.all())]

    @classmethod
    async def check_mobile_service(cls, auth: AuthSchema, mobile: str) -> dict:
        result = await auth.db.execute(
            select(CrmPersonModel).where(
                CrmPersonModel.primary_mobile == mobile.strip(),
                CrmPersonModel.is_deleted == False,
            )
        )
        person = result.scalars().first()
        if not person:
            return LeadMobileCheckSchema(exists=False, mobile=mobile.strip()).model_dump()
        lead_result = await auth.db.execute(
            select(CrmLeadProfileModel.id).where(
                CrmLeadProfileModel.person_id == person.id,
                CrmLeadProfileModel.is_deleted == False,
            )
        )
        return LeadMobileCheckSchema(
            exists=True,
            person_id=person.id,
            lead_id=lead_result.scalar(),
            name=person.name,
            mobile=person.primary_mobile,
        ).model_dump()

    @classmethod
    async def _decorate_list(cls, auth: AuthSchema, leads: list[CrmLeadProfileModel]) -> list[dict]:
        channel_names = await cls._channel_names(auth)
        user_names = await cls._user_names(auth, {lead.owner_sales_id for lead in leads if lead.owner_sales_id})
        dept_names = await cls._dept_names(auth, {lead.store_id for lead in leads if lead.store_id})
        ai_profile_map = await PersonAiProfileService.admin_info_map(auth.db, {lead.person_id for lead in leads})
        preference_map = await PartnerPreferenceService.map_current(auth.db, {lead.person_id for lead in leads})
        store_rules = await cls._store_rules_map(auth.db, {lead.store_id for lead in leads if lead.store_id})
        data = []
        for lead in leads:
            item = LeadOutSchema.model_validate(lead).model_dump()
            can_view = cls._can_view_contact(auth, lead)
            item["can_view_contact"] = can_view
            item["mobile_masked"] = lead.person.primary_mobile if can_view else cls._mask_mobile(lead.person.primary_mobile)
            item["wechat_masked"] = lead.person.wechat if can_view else cls._mask_wechat(lead.person.wechat)
            item["source_channel_name"] = channel_names.get(lead.source_channel_code or "")
            item["owner_sales"] = (
                {"id": lead.owner_sales_id, "name": user_names.get(lead.owner_sales_id)}
                if lead.owner_sales_id
                else None
            )
            item["store"] = (
                {"id": lead.store_id, "name": dept_names.get(lead.store_id)}
                if lead.store_id
                else None
            )
            if not can_view:
                item["person"]["primary_mobile"] = item["mobile_masked"]
                item["person"]["wechat"] = item["wechat_masked"]
            item["age"] = cls._age(lead.person.birth_date)
            item["constellation"] = cls._constellation(lead.person.birth_date)
            item["zodiac"] = cls._zodiac(lead.person.birth_date)
            item["ai_profile"] = ai_profile_map.get(lead.person_id, {"profile": None, "latest_task": None})
            item["partner_preference"] = preference_map.get(lead.person_id)
            item.update(cls._protect_info(lead, store_rules.get(lead.store_id or 0)))
            data.append(item)
        return data

    @classmethod
    async def _store_rules_map(cls, db: AsyncSession, store_ids: set[int]) -> dict[int, CrmLeadStoreRuleModel]:
        if not store_ids:
            return {}
        result = await db.execute(
            select(CrmLeadStoreRuleModel).where(
                CrmLeadStoreRuleModel.store_id.in_(store_ids),
                CrmLeadStoreRuleModel.is_deleted == False,
            )
        )
        return {rule.store_id: rule for rule in result.scalars().all()}

    @classmethod
    def _protect_info(cls, lead: CrmLeadProfileModel, rule: CrmLeadStoreRuleModel | None) -> dict:
        empty = {"protect_due_at": None, "protect_remaining_days": None, "protect_warning_level": None}
        if lead.pool_type != "sales_private" or not lead.assigned_at or not lead.owner_sales_id or lead.lead_type not in {"new", "second_hand"}:
            return empty
        days = rule.no_follow_reclaim_days if rule else 7
        due_at = lead.assigned_at + timedelta(days=days)
        if lead.latest_follow_at and lead.latest_follow_at >= lead.assigned_at:
            return {"protect_due_at": due_at, "protect_remaining_days": None, "protect_warning_level": "followed"}
        now = datetime.now()
        remaining_seconds = (due_at - now).total_seconds()
        remaining_days = max(0, int((remaining_seconds + 86399) // 86400))
        if remaining_seconds <= 0:
            level = "expired"
        elif remaining_days <= 1:
            level = "danger"
        elif remaining_days <= 2:
            level = "warning"
        else:
            level = "normal"
        return {"protect_due_at": due_at, "protect_remaining_days": remaining_days, "protect_warning_level": level}

    @classmethod
    async def _write_lifecycle(
        cls,
        auth: AuthSchema,
        lead: CrmLeadProfileModel,
        operation_type: str,
        change_detail: dict[str, Any] | None = None,
        remark: str | None = None,
    ) -> None:
        record = CrmLeadLifecycleModel(
            brand_id=lead.brand_id,
            lead_id=lead.id,
            person_id=lead.person_id,
            operation_type=operation_type,
            operator_user_id=auth.user.id if auth.user else None,
            change_detail=change_detail,
            remark=remark,
        )
        cls._stamp_create(auth, record)
        auth.db.add(record)

    @classmethod
    async def _store_rule(cls, auth: AuthSchema, store_id: int) -> CrmLeadStoreRuleModel:
        return await cls._store_rule_by_db(auth.db, store_id, operator_id=auth.user.id if auth.user else None)

    @classmethod
    async def _store_rule_by_db(cls, db: AsyncSession, store_id: int, operator_id: int | None = None) -> CrmLeadStoreRuleModel:
        result = await db.execute(
            select(CrmLeadStoreRuleModel).where(
                CrmLeadStoreRuleModel.store_id == store_id,
                CrmLeadStoreRuleModel.is_deleted == False,
            )
        )
        rule = result.scalars().first()
        if rule:
            return rule
        rule = CrmLeadStoreRuleModel(store_id=store_id, allow_sales_claim=False, no_follow_reclaim_days=7)
        if operator_id:
            rule.created_id = operator_id
            rule.updated_id = operator_id
        db.add(rule)
        await db.flush()
        return rule

    @classmethod
    async def recycle_overdue_service(cls, auth: AuthSchema) -> int:
        return await cls.recycle_overdue_by_db(auth.db, operator_id=auth.user.id if auth.user else None)

    @classmethod
    async def process_overdue_reclaim_tasks(cls) -> None:
        async with async_db_session() as db:
            try:
                count = await cls.recycle_overdue_by_db(db)
                await db.commit()
                if count:
                    log.info(f"CRM线索无跟进自动回公海完成: {count}条")
            except Exception:
                await db.rollback()
                log.exception("CRM线索无跟进自动回公海任务执行失败")
                raise

    @classmethod
    async def recycle_overdue_by_db(cls, db: AsyncSession, operator_id: int | None = None) -> int:
        result = await db.execute(
            select(CrmLeadProfileModel)
            .where(
                CrmLeadProfileModel.pool_type == "sales_private",
                CrmLeadProfileModel.lead_type.in_(["new", "second_hand"]),
                CrmLeadProfileModel.owner_sales_id.is_not(None),
                CrmLeadProfileModel.assigned_at.is_not(None),
                CrmLeadProfileModel.is_deleted == False,
            )
            .options(selectinload(CrmLeadProfileModel.person))
        )
        now = datetime.now()
        count = 0
        for lead in result.scalars().all():
            if not lead.store_id or not lead.assigned_at:
                continue
            rule = await cls._store_rule_by_db(db, lead.store_id, operator_id=operator_id)
            due_at = lead.assigned_at + timedelta(days=rule.no_follow_reclaim_days)
            if now < due_at:
                continue
            if lead.latest_follow_at and lead.latest_follow_at >= lead.assigned_at:
                continue
            old_owner = lead.owner_sales_id
            lead.pool_type = "store_pool"
            lead.owner_sales_id = None
            lead.lead_type = "second_hand"
            lead.last_recycled_at = now
            if operator_id:
                lead.updated_id = operator_id
            record = CrmLeadLifecycleModel(
                brand_id=lead.brand_id,
                lead_id=lead.id,
                person_id=lead.person_id,
                operation_type="auto_reclaim",
                operator_user_id=operator_id,
                change_detail={
                    "from_pool": "sales_private",
                    "to_pool": "store_pool",
                    "from_owner_sales_id": old_owner,
                    "to_owner_sales_id": None,
                    "reason": f"{rule.no_follow_reclaim_days}天未跟进自动回门店公海",
                },
            )
            if operator_id:
                record.created_id = operator_id
                record.updated_id = operator_id
            db.add(record)
            count += 1
        if count:
            await db.flush()
        return count

    @classmethod
    def _scope_conditions(cls, auth: AuthSchema, view: str) -> list[Any]:
        user = auth.user
        conditions: list[Any] = [
            CrmLeadProfileModel.is_deleted == False,
            CrmLeadProfileModel.lead_type != "converted_customer",
        ]
        if view == "all":
            if not cls._is_brand_admin(auth):
                raise CustomException(msg="无权限访问全量线索", code=10403, status_code=403)
            return conditions
        if view == "store_pool":
            conditions.append(CrmLeadProfileModel.pool_type == "store_pool")
            if cls._is_brand_admin(auth):
                return conditions
            if not user or not user.dept_id:
                conditions.append(CrmLeadProfileModel.store_id == -1)
                return conditions
            conditions.append(CrmLeadProfileModel.store_id == user.dept_id)
            return conditions
        if view == "sales_private":
            conditions.append(CrmLeadProfileModel.pool_type == "sales_private")
            if cls._is_brand_admin(auth):
                return conditions
            if cls._is_store_mgr(auth) and user and user.dept_id:
                conditions.append(CrmLeadProfileModel.store_id == user.dept_id)
                return conditions
            conditions.append(CrmLeadProfileModel.owner_sales_id == (user.id if user else -1))
            return conditions
        raise CustomException(msg="线索视图不正确")

    @classmethod
    async def _ensure_access(cls, auth: AuthSchema, lead: CrmLeadProfileModel, action: str = "read") -> None:
        if cls._is_brand_admin(auth):
            return
        user = auth.user
        if not user:
            raise CustomException(msg="无权限访问该线索", code=10403, status_code=403)
        if cls._is_store_mgr(auth) and lead.store_id == user.dept_id:
            return
        if lead.owner_sales_id == user.id:
            return
        if action in {"read", "claim"} and lead.pool_type == "store_pool" and lead.store_id == user.dept_id:
            rule = await cls._store_rule(auth, lead.store_id)
            if rule.allow_sales_claim and cls._is_sales(auth):
                return
        raise CustomException(msg="无权限访问该线索", code=10403, status_code=403)

    @classmethod
    async def _get_lead(cls, auth: AuthSchema, id: int, action: str = "read") -> CrmLeadProfileModel:
        result = await auth.db.execute(
            select(CrmLeadProfileModel)
            .where(CrmLeadProfileModel.id == id, CrmLeadProfileModel.is_deleted == False)
            .options(selectinload(CrmLeadProfileModel.person))
        )
        lead = result.scalars().first()
        if not lead:
            raise CustomException(msg="线索不存在")
        await cls._ensure_access(auth, lead, action=action)
        return lead

    @classmethod
    async def page_service(
        cls,
        auth: AuthSchema,
        view: str,
        page_no: int,
        page_size: int,
        search: LeadQueryParam | None = None,
    ) -> dict:
        await cls.recycle_overdue_service(auth)
        if (
            view == "store_pool"
            and cls._is_sales(auth)
            and not cls._is_brand_admin(auth)
            and not cls._is_store_mgr(auth)
        ):
            if not auth.user or not auth.user.dept_id:
                return {"page_no": page_no, "page_size": page_size, "total": 0, "has_next": False, "items": []}
            rule = await cls._store_rule(auth, auth.user.dept_id)
            if not rule.allow_sales_claim:
                return {"page_no": page_no, "page_size": page_size, "total": 0, "has_next": False, "items": []}
        conditions = cls._scope_conditions(auth, view)
        if search:
            if search.keyword:
                conditions.append(
                    or_(
                        CrmPersonModel.name.like(f"%{search.keyword}%"),
                        CrmPersonModel.primary_mobile.like(f"%{search.keyword}%"),
                    )
                )
            if search.lead_type:
                conditions.append(CrmLeadProfileModel.lead_type == search.lead_type)
            if search.source_channel_code:
                conditions.append(CrmLeadProfileModel.source_channel_code == search.source_channel_code)
            if search.store_id:
                conditions.append(CrmLeadProfileModel.store_id == search.store_id)
            if search.owner_sales_id:
                conditions.append(CrmLeadProfileModel.owner_sales_id == search.owner_sales_id)
            if search.latest_follow_time and len(search.latest_follow_time) == 2:
                conditions.append(
                    CrmLeadProfileModel.latest_follow_at.between(
                        search.latest_follow_time[0], search.latest_follow_time[1]
                    )
                )
        total_result = await auth.db.execute(
            select(func.count(CrmLeadProfileModel.id))
            .join(CrmPersonModel, CrmLeadProfileModel.person_id == CrmPersonModel.id)
            .where(and_(*conditions))
        )
        rows_result = await auth.db.execute(
            select(CrmLeadProfileModel)
            .join(CrmPersonModel, CrmLeadProfileModel.person_id == CrmPersonModel.id)
            .where(and_(*conditions))
            .options(selectinload(CrmLeadProfileModel.person))
            .order_by(CrmLeadProfileModel.updated_time.desc(), CrmLeadProfileModel.id.desc())
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        total = total_result.scalar() or 0
        items = await cls._decorate_list(auth, list(rows_result.scalars().all()))
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": items,
        }

    @classmethod
    async def detail_service(cls, auth: AuthSchema, id: int) -> dict:
        lead = await cls._get_lead(auth, id)
        data = (await cls._decorate_list(auth, [lead]))[0]
        process_result = await auth.db.execute(
            select(CrmLeadProcessRecordModel)
            .where(CrmLeadProcessRecordModel.lead_id == id, CrmLeadProcessRecordModel.is_deleted == False)
            .order_by(CrmLeadProcessRecordModel.created_time.desc(), CrmLeadProcessRecordModel.id.desc())
        )
        lifecycle_result = await auth.db.execute(
            select(CrmLeadLifecycleModel)
            .where(
                CrmLeadLifecycleModel.lead_id == id,
                CrmLeadLifecycleModel.is_deleted == False,
                CrmLeadLifecycleModel.operation_type != "follow",
            )
            .order_by(CrmLeadLifecycleModel.created_time.desc(), CrmLeadLifecycleModel.id.desc())
        )
        data["process_records"] = [
            LeadProcessOutSchema.model_validate(row).model_dump() for row in process_result.scalars().all()
        ]
        lifecycle_rows = list(lifecycle_result.scalars().all())
        lifecycle_records = [
            LeadLifecycleOutSchema.model_validate(row).model_dump() for row in lifecycle_rows
        ]
        await cls._decorate_lifecycle_change_detail(auth, lifecycle_records)
        data["lifecycle_records"] = lifecycle_records
        data["partner_preference_versions"] = await PartnerPreferenceService.versions_out(auth.db, lead.person_id, 10)
        return LeadDetailOutSchema.model_validate(data).model_dump()

    @classmethod
    async def _decorate_lifecycle_change_detail(cls, auth: AuthSchema, records: list[dict]) -> None:
        user_ids: set[int] = set()
        dept_ids: set[int] = set()

        def collect(value: Any) -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    if key.endswith("owner_sales_id") and item:
                        user_ids.add(int(item))
                    elif key == "store_id" and item:
                        dept_ids.add(int(item))
                    else:
                        collect(item)
            elif isinstance(value, list):
                for item in value:
                    collect(item)

        for record in records:
            collect(record.get("change_detail"))

        user_names = await cls._user_names(auth, user_ids)
        dept_names = await cls._dept_names(auth, dept_ids)

        def decorate(value: Any) -> None:
            if isinstance(value, dict):
                for key, item in list(value.items()):
                    if key.endswith("owner_sales_id") and item:
                        value[f"{key}_name"] = user_names.get(int(item))
                    elif key == "store_id" and item:
                        value["store_name"] = dept_names.get(int(item))
                    else:
                        decorate(item)
            elif isinstance(value, list):
                for item in value:
                    decorate(item)

        for record in records:
            decorate(record.get("change_detail"))

    @classmethod
    async def _resolve_owner_defaults(
        cls, auth: AuthSchema, store_id: int | None, owner_sales_id: int | None
    ) -> tuple[int | None, int | None]:
        if cls._is_brand_admin(auth):
            return store_id, owner_sales_id
        if cls._is_store_mgr(auth):
            return auth.user.dept_id if auth.user else store_id, owner_sales_id
        if cls._is_sales(auth):
            return auth.user.dept_id if auth.user else store_id, auth.user.id if auth.user else owner_sales_id
        return store_id, owner_sales_id

    @classmethod
    async def _validate_owner_in_store(
        cls, auth: AuthSchema, store_id: int | None, owner_sales_id: int | None
    ) -> None:
        if not owner_sales_id:
            return
        result = await auth.db.execute(select(UserModel).where(UserModel.id == owner_sales_id, UserModel.is_deleted == False))
        user = result.scalars().first()
        if not user:
            raise CustomException(msg="归属人不存在")
        if store_id and user.dept_id != store_id:
            raise CustomException(msg="归属人不属于目标门店")

    @classmethod
    async def create_service(cls, auth: AuthSchema, data: LeadCreateSchema) -> dict:
        if data.sync_to_miniprogram:
            cls._validate_miniprogram_sync_required(data)
        exist_result = await auth.db.execute(
            select(CrmPersonModel).where(
                CrmPersonModel.primary_mobile == data.mobile,
                CrmPersonModel.is_deleted == False,
            )
        )
        if exist_result.scalars().first():
            raise CustomException(msg="创建失败，手机号已存在")
        store_id, owner_sales_id = await cls._resolve_owner_defaults(auth, data.store_id, data.owner_sales_id)
        await cls._validate_owner_in_store(auth, store_id, owner_sales_id)
        person = CrmPersonModel(
            brand_id=1,
            name=data.name,
            gender=data.gender,
            primary_mobile=data.mobile,
            wechat=data.wechat,
            birth_date=data.birth_date,
            height_cm=data.height_cm,
            weight_kg=data.weight_kg,
            ethnicity=data.ethnicity,
            occupation=data.occupation,
            occupation_code=data.occupation_code,
            annual_income=data.annual_income,
            marital_status=data.marital_status,
            education=data.education,
            graduated_school=data.graduated_school,
            major=data.major,
            unit_type=data.unit_type,
            job_title=data.job_title,
            work_company=data.work_company,
            hometown=data.hometown,
            residence=data.residence,
            house_status=data.house_status,
            car_status=data.car_status,
            accept_long_distance_self=data.accept_long_distance_self,
            accept_flash_marriage=data.accept_flash_marriage,
            willing_relocate=data.willing_relocate,
            marriage_plan=data.marriage_plan,
            family_background=data.family_background,
            profile_remark=data.profile_remark,
            photo_urls=data.photo_urls,
        )
        await cls._ensure_person_display_no(auth, person)
        cls._stamp_create(auth, person)
        auth.db.add(person)
        await auth.db.flush()

        if owner_sales_id:
            pool_type, lead_type, assigned_at = "sales_private", "new", datetime.now()
        elif store_id:
            pool_type, lead_type, assigned_at = "store_pool", "pending", None
        else:
            pool_type, lead_type, assigned_at = "hq_pool", "pending", None
        lead = CrmLeadProfileModel(
            brand_id=1,
            person_id=person.id,
            store_id=store_id,
            owner_sales_id=owner_sales_id,
            pool_type=pool_type,
            lead_type=lead_type,
            source_channel_code=data.source_channel_code,
            assigned_at=assigned_at,
            description=data.description,
        )
        cls._stamp_create(auth, lead)
        auth.db.add(lead)
        await auth.db.flush()
        await cls._write_lifecycle(
            auth,
            lead,
            "create",
            {"pool_type": pool_type, "store_id": store_id, "owner_sales_id": owner_sales_id},
            data.description or "后台新增线索",
        )
        if data.sync_to_miniprogram:
            mp_user = await cls._sync_person_to_miniprogram_user(auth, person)
            await cls._write_lifecycle(
                auth,
                lead,
                "sync_mp_user",
                {"mp_user_id": mp_user.id, "person_id": person.id, "mobile": person.primary_mobile},
                "后台新增线索同步为小程序待绑定用户",
            )
        if data.partner_preference:
            await PartnerPreferenceService.save(
                auth.db,
                person.id,
                PartnerPreferenceSaveSchema(**data.partner_preference.model_dump(), source_type="admin", source_id=str(lead.id)),
                auth=auth,
            )
        await PersonAiProfileService.enqueue_miai_impression(
            db=auth.db,
            person_id=person.id,
            source_type="admin_update",
            source_id=lead.id,
        )
        await MatchProfileService.mark_dirty(
            db=auth.db,
            person_id=person.id,
            dirty_parts=["self_profile", "preference"],
            source_type="admin_lead_create",
            source_id=lead.id,
        )
        await auth.db.flush()
        await auth.db.refresh(lead)
        return (await cls._decorate_list(auth, [lead]))[0]

    @classmethod
    async def update_service(cls, auth: AuthSchema, id: int, data: LeadUpdateSchema) -> dict:
        lead = await cls._get_lead(auth, id, action="update")
        old = LeadPersonPayload(
            mobile=lead.person.primary_mobile,
            name=lead.person.name,
            gender=lead.person.gender,
            wechat=lead.person.wechat,
            birth_date=lead.person.birth_date,
            height_cm=lead.person.height_cm,
            weight_kg=lead.person.weight_kg,
            ethnicity=lead.person.ethnicity,
            occupation=lead.person.occupation,
            occupation_code=lead.person.occupation_code,
            annual_income=lead.person.annual_income,
            marital_status=lead.person.marital_status,
            education=lead.person.education,
            graduated_school=lead.person.graduated_school,
            major=lead.person.major,
            unit_type=lead.person.unit_type,
            job_title=lead.person.job_title,
            work_company=lead.person.work_company,
            hometown=lead.person.hometown,
            residence=lead.person.residence,
            house_status=lead.person.house_status,
            car_status=lead.person.car_status,
            accept_long_distance_self=lead.person.accept_long_distance_self,
            accept_flash_marriage=lead.person.accept_flash_marriage,
            willing_relocate=lead.person.willing_relocate,
            marriage_plan=lead.person.marriage_plan,
            family_background=lead.person.family_background,
            profile_remark=lead.person.profile_remark,
            photo_urls=lead.person.photo_urls or [],
        ).model_dump()
        if data.mobile != lead.person.primary_mobile:
            raise CustomException(msg="手机号不允许编辑")
        for field, value in data.model_dump(exclude={"source_channel_code", "description", "partner_preference"}).items():
            target = "primary_mobile" if field == "mobile" else field
            setattr(lead.person, target, value)
        old_source_channel_code = lead.source_channel_code
        old_description = lead.description
        cls._stamp_update(auth, lead.person)
        cls._stamp_update(auth, lead)
        new = data.model_dump(exclude={"source_channel_code", "description", "partner_preference"})
        changes = {
            field: {"from": old.get(field), "to": new.get(field)}
            for field in new
            if old.get(field) != new.get(field)
        }
        if data.source_channel_code != old_source_channel_code:
            changes["source_channel_code"] = {"from": old_source_channel_code, "to": data.source_channel_code}
        lead.source_channel_code = data.source_channel_code
        lead.description = data.description
        if data.partner_preference is not None:
            await PartnerPreferenceService.save(
                auth.db,
                lead.person_id,
                PartnerPreferenceSaveSchema(**data.partner_preference.model_dump(), source_type="admin", source_id=str(lead.id)),
                auth=auth,
            )
            changes["partner_preference"] = "已更新"
        if data.description != old_description:
            changes["description"] = {"from": old_description, "to": data.description}
        if changes:
            await cls._write_lifecycle(auth, lead, "edit", changes, data.description)
            await PersonAiProfileService.enqueue_miai_impression(
                db=auth.db,
                person_id=lead.person_id,
                source_type="admin_update",
                source_id=lead.id,
            )
            base_change_fields = set(changes) - {"partner_preference", "description", "source_channel_code"}
            if base_change_fields:
                await MatchProfileService.mark_dirty(
                    db=auth.db,
                    person_id=lead.person_id,
                    dirty_parts=["self_profile"],
                    source_type="admin_lead_update",
                    source_id=lead.id,
                )
        await auth.db.flush()
        await auth.db.refresh(lead)
        return (await cls._decorate_list(auth, [lead]))[0]

    @classmethod
    async def assign_service(cls, auth: AuthSchema, data: LeadAssignSchema) -> None:
        for lead_id in data.lead_ids:
            lead = await cls._get_lead(auth, lead_id)
            old = {
                "pool_type": lead.pool_type,
                "store_id": lead.store_id,
                "owner_sales_id": lead.owner_sales_id,
                "lead_type": lead.lead_type,
            }
            store_id = data.store_id if data.store_id is not None else lead.store_id
            owner_sales_id = data.owner_sales_id
            if not cls._is_brand_admin(auth) and cls._is_store_mgr(auth) and store_id != (auth.user.dept_id if auth.user else None):
                raise CustomException(msg="门店管理员只能分配本门店线索", code=10403, status_code=403)
            await cls._validate_owner_in_store(auth, store_id, owner_sales_id)
            lead.store_id = store_id
            lead.owner_sales_id = owner_sales_id
            if owner_sales_id:
                lead.pool_type = "sales_private"
                lead.lead_type = "second_hand" if lead.assigned_at else "new"
                lead.assigned_at = datetime.now()
            elif store_id:
                lead.pool_type = "store_pool"
                lead.lead_type = "pending" if not lead.assigned_at else "second_hand"
            else:
                lead.pool_type = "hq_pool"
                lead.lead_type = "pending"
            cls._stamp_update(auth, lead)
            await cls._write_lifecycle(
                auth,
                lead,
                "assign",
                {
                    "from": old,
                    "to": {
                        "pool_type": lead.pool_type,
                        "store_id": lead.store_id,
                        "owner_sales_id": lead.owner_sales_id,
                        "lead_type": lead.lead_type,
                    },
                },
                data.remark,
            )
        await auth.db.flush()

    @classmethod
    async def claim_service(cls, auth: AuthSchema, data: LeadClaimSchema) -> None:
        for lead_id in data.lead_ids:
            lead = await cls._get_lead(auth, lead_id)
            await cls._ensure_access(auth, lead, action="claim")
            if lead.pool_type != "store_pool" or not lead.store_id:
                raise CustomException(msg=f"线索{lead_id}不在门店公海，无法领取")
            old_owner = lead.owner_sales_id
            lead.owner_sales_id = auth.user.id if auth.user else None
            lead.pool_type = "sales_private"
            lead.lead_type = "second_hand" if lead.assigned_at else "new"
            lead.assigned_at = datetime.now()
            cls._stamp_update(auth, lead)
            await cls._write_lifecycle(
                auth,
                lead,
                "claim",
                {
                    "from_pool": "store_pool",
                    "to_pool": "sales_private",
                    "from_owner_sales_id": old_owner,
                    "to_owner_sales_id": lead.owner_sales_id,
                },
            )
        await auth.db.flush()

    @classmethod
    async def process_service(cls, auth: AuthSchema, id: int, data: LeadProcessCreateSchema) -> dict:
        lead = await cls._get_lead(auth, id)
        if lead.pool_type == "sales_private" and lead.owner_sales_id != (auth.user.id if auth.user else None):
            if not (cls._is_brand_admin(auth) or cls._is_store_mgr(auth)):
                raise CustomException(msg="只能处理自己线索库中的线索", code=10403, status_code=403)
        record = CrmLeadProcessRecordModel(
            brand_id=lead.brand_id,
            lead_id=lead.id,
            person_id=lead.person_id,
            action_type=data.action_type,
            follow_method=data.follow_method,
            content=data.content,
            next_follow_at=data.next_follow_at,
            operator_user_id=auth.user.id if auth.user else None,
        )
        cls._stamp_create(auth, record)
        auth.db.add(record)
        now = datetime.now()
        change: dict[str, Any] = {"action_type": data.action_type}
        if data.action_type == "follow":
            lead.latest_follow_at = now
            lead.next_follow_at = data.next_follow_at
        elif data.action_type == "invalid":
            change["from_lead_type"] = lead.lead_type
            lead.lead_type = "invalid"
            lead.latest_follow_at = now
            lead.next_follow_at = data.next_follow_at
        elif data.action_type == "release":
            if lead.pool_type != "sales_private":
                raise CustomException(msg="只有销售私海线索可以释放")
            change.update({"from_pool": lead.pool_type, "to_pool": "store_pool", "from_owner_sales_id": lead.owner_sales_id})
            lead.pool_type = "store_pool"
            lead.owner_sales_id = None
            lead.lead_type = "second_hand"
            lead.latest_follow_at = now
            lead.next_follow_at = None
        elif data.action_type == "convert_customer":
            from app.plugin.module_crm.customer.service import CustomerService

            old_lead_type = lead.lead_type
            await CustomerService.create_from_lead_service(auth, id, data.content)
            change["from_lead_type"] = old_lead_type
            lead.lead_type = "converted_customer"
            lead.converted_customer_at = now
            lead.latest_follow_at = now
        cls._stamp_update(auth, lead)
        if data.action_type != "follow":
            await cls._write_lifecycle(auth, lead, data.action_type, change, data.content)
        await auth.db.flush()
        await auth.db.refresh(record)
        return LeadProcessOutSchema.model_validate(record).model_dump()

    @classmethod
    async def get_store_rule_service(cls, auth: AuthSchema, store_id: int) -> dict:
        if not (cls._is_brand_admin(auth) or (cls._is_store_mgr(auth) and auth.user and auth.user.dept_id == store_id)):
            raise CustomException(msg="无权限查看门店线索规则", code=10403, status_code=403)
        await cls._ensure_actual_store(auth.db, store_id)
        rule = await cls._store_rule(auth, store_id)
        return LeadStoreRuleSchema.model_validate(rule).model_dump()

    @classmethod
    async def set_store_rule_service(cls, auth: AuthSchema, store_id: int, data: LeadStoreRuleSchema) -> None:
        if not (cls._is_brand_admin(auth) or (cls._is_store_mgr(auth) and auth.user and auth.user.dept_id == store_id)):
            raise CustomException(msg="无权限设置门店线索规则", code=10403, status_code=403)
        await cls._ensure_actual_store(auth.db, store_id)
        rule = await cls._store_rule(auth, store_id)
        rule.allow_sales_claim = data.allow_sales_claim
        rule.no_follow_reclaim_days = data.no_follow_reclaim_days
        cls._stamp_update(auth, rule)
        await auth.db.flush()

    @classmethod
    async def _ensure_actual_store(cls, db: AsyncSession, store_id: int) -> None:
        store = await db.get(DeptModel, store_id)
        if not store or store.is_deleted or store.status != "0":
            raise CustomException(msg="门店不存在或已停用")
        if store.parent_id is None:
            raise CustomException(msg="线索规则只能配置实际门店，不能配置品牌/总部节点")

    @classmethod
    async def download_template_service(cls) -> bytes:
        return ExcelUtil.get_excel_template(
            header_list=cls.IMPORT_HEADERS,
            selector_header_list=["性别"],
            option_list=[{"性别": ["男", "女", "未知"]}],
        )

    @classmethod
    def _gender_value(cls, value: Any) -> str:
        text = str(value or "").strip()
        return {"男": "0", "女": "1", "未知": "2", "0": "0", "1": "1", "2": "2"}.get(text, "")

    @classmethod
    async def import_service(cls, auth: AuthSchema, file: UploadFile) -> dict:
        if not (cls._is_brand_admin(auth) or cls._is_store_mgr(auth)):
            raise CustomException(msg="无权限导入线索", code=10403, status_code=403)
        content = await file.read()
        df = pd.read_excel(BytesIO(content), dtype=str).fillna("")
        failed_rows: list[dict[str, Any]] = []
        success_count = 0
        for idx, row in df.iterrows():
            row_no = int(idx) + 2
            try:
                mobile = str(row.get("手机号", "")).strip()
                name = str(row.get("姓名", "")).strip()
                gender = cls._gender_value(row.get("性别", ""))
                if not mobile or not name or not gender:
                    raise ValueError("手机号、姓名、性别必填")
                exists = await auth.db.execute(
                    select(CrmPersonModel).where(
                        CrmPersonModel.primary_mobile == mobile,
                        CrmPersonModel.is_deleted == False,
                    )
                )
                if exists.scalars().first():
                    raise ValueError("手机号已存在")
                store_id = int(row.get("归属门店")) if str(row.get("归属门店", "")).strip() else None
                owner_sales_id = int(row.get("归属人")) if str(row.get("归属人", "")).strip() else None
                if cls._is_store_mgr(auth) and auth.user:
                    store_id = auth.user.dept_id
                payload = LeadCreateSchema(
                    mobile=mobile,
                    name=name,
                    gender=gender,
                    wechat=str(row.get("微信号", "")).strip() or None,
                    birth_date=row.get("出生日期") or None,
                    height_cm=int(row.get("身高")) if str(row.get("身高", "")).strip() else None,
                    ethnicity=str(row.get("民族", "")).strip() or None,
                    occupation=str(row.get("职业", "")).strip() or None,
                    annual_income=str(row.get("年收入", "")).strip() or None,
                    marital_status=str(row.get("婚况", "")).strip() or None,
                    education=str(row.get("学历", "")).strip() or None,
                    hometown=str(row.get("籍贯", "")).strip() or None,
                    residence=str(row.get("常驻地", "")).strip() or None,
                    house_status=str(row.get("房产信息", "")).strip() or None,
                    car_status=str(row.get("购车信息", "")).strip() or None,
                    source_channel_code=str(row.get("来源渠道", "")).strip().upper() or "IMPORT",
                    store_id=store_id,
                    owner_sales_id=owner_sales_id,
                    description=str(row.get("备注", "")).strip() or None,
                )
                await cls.create_service(auth, payload)
                success_count += 1
            except Exception as exc:
                failed_rows.append({"row": row_no, "reason": str(exc)})
        batch = CrmLeadImportBatchModel(
            file_name=file.filename,
            success_count=success_count,
            failed_count=len(failed_rows),
            result_detail=failed_rows,
        )
        cls._stamp_create(auth, batch)
        auth.db.add(batch)
        await auth.db.flush()
        return LeadImportResultSchema(
            success_count=success_count, failed_count=len(failed_rows), failed_rows=failed_rows
        ).model_dump()
