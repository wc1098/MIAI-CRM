import secrets
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any

import pandas as pd
from fastapi import UploadFile
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from app.api.v1.module_system.auth.schema import AuthSchema
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.user.model import UserModel
from app.core.exceptions import CustomException
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
    async def _dept_names(cls, auth: AuthSchema, ids: set[int]) -> dict[int, str]:
        if not ids:
            return {}
        result = await auth.db.execute(select(DeptModel.id, DeptModel.name).where(DeptModel.id.in_(ids)))
        return {row[0]: row[1] for row in result.all()}

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
            item["ai_profile"] = ai_profile_map.get(lead.person_id, {"profile": None, "latest_task": None})
            data.append(item)
        return data

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
        result = await auth.db.execute(
            select(CrmLeadStoreRuleModel).where(
                CrmLeadStoreRuleModel.store_id == store_id,
                CrmLeadStoreRuleModel.is_deleted == False,
            )
        )
        rule = result.scalars().first()
        if rule:
            return rule
        rule = CrmLeadStoreRuleModel(store_id=store_id, allow_sales_claim=False, no_follow_reclaim_days=7)
        cls._stamp_create(auth, rule)
        auth.db.add(rule)
        await auth.db.flush()
        return rule

    @classmethod
    async def recycle_overdue_service(cls, auth: AuthSchema) -> int:
        result = await auth.db.execute(
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
            rule = await cls._store_rule(auth, lead.store_id)
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
            cls._stamp_update(auth, lead)
            await cls._write_lifecycle(
                auth,
                lead,
                "auto_reclaim",
                {
                    "from_pool": "sales_private",
                    "to_pool": "store_pool",
                    "from_owner_sales_id": old_owner,
                    "to_owner_sales_id": None,
                    "reason": f"{rule.no_follow_reclaim_days}天未跟进自动回门店公海",
                },
            )
            count += 1
        if count:
            await auth.db.flush()
        return count

    @classmethod
    def _scope_conditions(cls, auth: AuthSchema, view: str) -> list[Any]:
        user = auth.user
        conditions: list[Any] = [CrmLeadProfileModel.is_deleted == False]
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
    async def _get_lead(cls, auth: AuthSchema, id: int) -> CrmLeadProfileModel:
        result = await auth.db.execute(
            select(CrmLeadProfileModel)
            .where(CrmLeadProfileModel.id == id, CrmLeadProfileModel.is_deleted == False)
            .options(selectinload(CrmLeadProfileModel.person))
        )
        lead = result.scalars().first()
        if not lead:
            raise CustomException(msg="线索不存在")
        await cls._ensure_access(auth, lead)
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
            .where(CrmLeadLifecycleModel.lead_id == id, CrmLeadLifecycleModel.is_deleted == False)
            .order_by(CrmLeadLifecycleModel.created_time.desc(), CrmLeadLifecycleModel.id.desc())
        )
        data["process_records"] = [
            LeadProcessOutSchema.model_validate(row).model_dump() for row in process_result.scalars().all()
        ]
        data["lifecycle_records"] = [
            LeadLifecycleOutSchema.model_validate(row).model_dump() for row in lifecycle_result.scalars().all()
        ]
        return LeadDetailOutSchema.model_validate(data).model_dump()

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
            ethnicity=data.ethnicity,
            occupation=data.occupation,
            annual_income=data.annual_income,
            marital_status=data.marital_status,
            education=data.education,
            hometown=data.hometown,
            residence=data.residence,
            house_status=data.house_status,
            car_status=data.car_status,
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
            data.description,
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
        await PersonAiProfileService.enqueue_miai_impression(
            db=auth.db,
            person_id=person.id,
            source_type="admin_update",
            source_id=lead.id,
        )
        await auth.db.flush()
        await auth.db.refresh(lead)
        return (await cls._decorate_list(auth, [lead]))[0]

    @classmethod
    async def update_service(cls, auth: AuthSchema, id: int, data: LeadUpdateSchema) -> dict:
        lead = await cls._get_lead(auth, id)
        old = LeadPersonPayload(
            mobile=lead.person.primary_mobile,
            name=lead.person.name,
            gender=lead.person.gender,
            wechat=lead.person.wechat,
            birth_date=lead.person.birth_date,
            height_cm=lead.person.height_cm,
            ethnicity=lead.person.ethnicity,
            occupation=lead.person.occupation,
            annual_income=lead.person.annual_income,
            marital_status=lead.person.marital_status,
            education=lead.person.education,
            hometown=lead.person.hometown,
            residence=lead.person.residence,
            house_status=lead.person.house_status,
            car_status=lead.person.car_status,
            photo_urls=lead.person.photo_urls or [],
        ).model_dump()
        if data.mobile != lead.person.primary_mobile:
            exists = await auth.db.execute(
                select(CrmPersonModel).where(
                    CrmPersonModel.primary_mobile == data.mobile,
                    CrmPersonModel.id != lead.person_id,
                    CrmPersonModel.is_deleted == False,
                )
            )
            if exists.scalars().first():
                raise CustomException(msg="更新失败，手机号已存在")
        for field, value in data.model_dump(exclude={"source_channel_code", "description"}).items():
            target = "primary_mobile" if field == "mobile" else field
            setattr(lead.person, target, value)
        old_source_channel_code = lead.source_channel_code
        old_description = lead.description
        cls._stamp_update(auth, lead.person)
        cls._stamp_update(auth, lead)
        new = data.model_dump(exclude={"source_channel_code", "description"})
        changes = {
            field: {"from": old.get(field), "to": new.get(field)}
            for field in new
            if old.get(field) != new.get(field)
        }
        if data.source_channel_code != old_source_channel_code:
            changes["source_channel_code"] = {"from": old_source_channel_code, "to": data.source_channel_code}
        lead.source_channel_code = data.source_channel_code
        lead.description = data.description
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
            change["from_lead_type"] = lead.lead_type
            lead.lead_type = "converted_customer"
            lead.converted_customer_at = now
            lead.latest_follow_at = now
        cls._stamp_update(auth, lead)
        await cls._write_lifecycle(auth, lead, data.action_type, change, data.content)
        await auth.db.flush()
        await auth.db.refresh(record)
        return LeadProcessOutSchema.model_validate(record).model_dump()

    @classmethod
    async def get_store_rule_service(cls, auth: AuthSchema, store_id: int) -> dict:
        if not (cls._is_brand_admin(auth) or (cls._is_store_mgr(auth) and auth.user and auth.user.dept_id == store_id)):
            raise CustomException(msg="无权限查看门店线索规则", code=10403, status_code=403)
        rule = await cls._store_rule(auth, store_id)
        return LeadStoreRuleSchema.model_validate(rule).model_dump()

    @classmethod
    async def set_store_rule_service(cls, auth: AuthSchema, store_id: int, data: LeadStoreRuleSchema) -> None:
        if not (cls._is_brand_admin(auth) or (cls._is_store_mgr(auth) and auth.user and auth.user.dept_id == store_id)):
            raise CustomException(msg="无权限设置门店线索规则", code=10403, status_code=403)
        rule = await cls._store_rule(auth, store_id)
        rule.allow_sales_claim = data.allow_sales_claim
        rule.no_follow_reclaim_days = data.no_follow_reclaim_days
        cls._stamp_update(auth, rule)
        await auth.db.flush()

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
