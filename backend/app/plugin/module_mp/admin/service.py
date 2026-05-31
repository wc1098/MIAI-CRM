from datetime import datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import aliased, selectinload

from app.api.v1.module_system.auth.schema import AuthSchema
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.params.model import ParamsModel
from app.core.exceptions import CustomException
from app.plugin.module_certification.service import mask_id_card
from app.plugin.module_crm.lead.model import (
    CrmLeadLifecycleModel,
    CrmLeadProcessRecordModel,
    CrmLeadProfileModel,
    CrmPersonModel,
)
from app.plugin.module_crm.preference.service import PartnerPreferenceService
from app.plugin.module_match.service import MatchProfileService
from app.plugin.module_mp.auth.model import MiniProgramUserModel, SourceEventModel
from app.plugin.module_mp.plaza.model import (
    MpContactUnlockModel,
    MpContactViewLogModel,
    MpUnlockCouponModel,
    MpUnlockQuestionModel,
    MpUnlockTaskModel,
    MpUserFavoriteModel,
    MpUserLikeModel,
    MpUserProfileActionModel,
)
from app.plugin.module_mp.plaza.service import DEFAULT_SETTINGS, MpPlazaService
from app.plugin.module_profile_ai.service import PersonAiProfileService

from .schema import (
    MpActionQueryParam,
    MpCouponGrantSchema,
    MpCouponQueryParam,
    MpOperationSettingsSchema,
    MpPersonBriefSchema,
    MpQuestionUpsertSchema,
    MpTaskUpsertSchema,
    MpUnlockRecordQueryParam,
    MpUnlockRevokeSchema,
    MpUserOutSchema,
    MpUserProfileUpdateSchema,
    MpUserQueryParam,
    MpUserWallUpdateSchema,
)


class MpAdminService:
    """小程序后台管理服务。"""

    @classmethod
    async def page_users(
        cls,
        db,
        page_no: int,
        page_size: int,
        search: MpUserQueryParam | None = None,
    ) -> dict:
        conditions = [MiniProgramUserModel.is_deleted == False]
        join_person = False
        if search:
            if search.is_registered is True:
                conditions.append(MiniProgramUserModel.registered_at.is_not(None))
            elif search.is_registered is False:
                conditions.append(MiniProgramUserModel.registered_at.is_(None))
            if search.keyword:
                join_person = True
                keyword = f"%{search.keyword}%"
                conditions.append(
                    or_(
                        MiniProgramUserModel.nickname.like(keyword),
                        MiniProgramUserModel.mobile.like(keyword),
                        CrmPersonModel.name.like(keyword),
                        CrmPersonModel.primary_mobile.like(keyword),
                        CrmPersonModel.wechat.like(keyword),
                    )
                )

        count_stmt = select(func.count(MiniProgramUserModel.id)).where(and_(*conditions))
        rows_stmt = (
            select(MiniProgramUserModel)
            .where(and_(*conditions))
            .options(selectinload(MiniProgramUserModel.person))
            .order_by(MiniProgramUserModel.registered_at.desc(), MiniProgramUserModel.id.desc())
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        if join_person:
            count_stmt = count_stmt.outerjoin(CrmPersonModel, MiniProgramUserModel.person_id == CrmPersonModel.id)
            rows_stmt = rows_stmt.outerjoin(CrmPersonModel, MiniProgramUserModel.person_id == CrmPersonModel.id)

        total = (await db.execute(count_stmt)).scalar() or 0
        users = list((await db.execute(rows_stmt)).scalars().all())
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": await cls._decorate_users(db, users),
        }

    @classmethod
    async def detail_user(cls, db, user_id: int) -> dict:
        result = await db.execute(
            select(MiniProgramUserModel)
            .where(MiniProgramUserModel.id == user_id, MiniProgramUserModel.is_deleted == False)
            .options(selectinload(MiniProgramUserModel.person))
        )
        user = result.scalars().first()
        if not user:
            raise CustomException(msg="小程序用户不存在")
        return (await cls._decorate_users(db, [user]))[0]

    @classmethod
    async def _decorate_users(cls, db, users: list[MiniProgramUserModel]) -> list[dict]:
        if not users:
            return []
        user_ids = [user.id for user in users]
        person_ids = [user.person_id for user in users if user.person_id]
        person_id_set = set(person_ids)

        lead_map: dict[int, int] = {}
        if person_id_set:
            lead_rows = await db.execute(
                select(CrmLeadProfileModel.person_id, CrmLeadProfileModel.id)
                .where(CrmLeadProfileModel.person_id.in_(person_id_set), CrmLeadProfileModel.is_deleted == False)
                .order_by(CrmLeadProfileModel.updated_time.desc(), CrmLeadProfileModel.id.desc())
            )
            for person_id, lead_id in lead_rows.all():
                lead_map.setdefault(person_id, lead_id)
        ai_profile_map = await PersonAiProfileService.admin_info_map(db, person_id_set)
        preference_map = await PartnerPreferenceService.map_current(db, person_id_set)

        event_count_map: dict[int, int] = {}
        event_rows = await db.execute(
            select(SourceEventModel.user_id, func.count(SourceEventModel.id))
            .where(SourceEventModel.user_id.in_(user_ids), SourceEventModel.is_deleted == False)
            .group_by(SourceEventModel.user_id)
        )
        for user_id, count in event_rows.all():
            event_count_map[user_id] = int(count or 0)

        like_count_map = await cls._aggregate_counts(db, user_ids, MpUserLikeModel.target_user_id, MpUserLikeModel, MpUserLikeModel.is_active == True)
        favorite_count_map = await cls._aggregate_counts(db, user_ids, MpUserFavoriteModel.target_user_id, MpUserFavoriteModel, MpUserFavoriteModel.is_active == True)
        unlock_count_map = await cls._aggregate_counts(db, user_ids, MpContactUnlockModel.target_user_id, MpContactUnlockModel, MpContactUnlockModel.unlock_status == "success")
        coupon_count_map = await cls._aggregate_counts(db, user_ids, MpUnlockCouponModel.user_id, MpUnlockCouponModel, MpUnlockCouponModel.coupon_status == "unused")
        action_map = await cls._recent_action_map(db, user_ids)

        items: list[dict] = []
        for user in users:
            person = user.person
            person_data = None
            if person:
                person_data = MpPersonBriefSchema(
                    id=person.id,
                    description=person.description,
                    name=person.name,
                    gender=person.gender,
                    primary_mobile=person.primary_mobile,
                    wechat=person.wechat,
                    birth_date=person.birth_date.isoformat() if person.birth_date else None,
                    height_cm=person.height_cm,
                    ethnicity=person.ethnicity,
                    occupation=person.occupation,
                    annual_income=person.annual_income,
                    marital_status=person.marital_status,
                    education=person.education,
                    hometown=person.hometown,
                    residence=person.residence,
                    house_status=person.house_status,
                    car_status=person.car_status,
                    photo_urls=person.photo_urls or [],
                    id_card_no_masked=mask_id_card(getattr(person, "id_card_no", None)),
                    certification_level=getattr(person, "certification_level", "none"),
                    certification_summary=getattr(person, "certification_summary", None),
                )
            items.append(
                MpUserOutSchema(
                    id=user.id,
                    uuid=user.uuid,
                    status=user.status,
                    description=user.description,
                    created_time=user.created_time,
                    updated_time=user.updated_time,
                    is_deleted=user.is_deleted,
                    deleted_time=user.deleted_time,
                    brand_id=user.brand_id,
                    person_id=user.person_id,
                    openid=user.openid,
                    unionid=user.unionid,
                    mobile=user.mobile,
                    nickname=user.nickname,
                    avatar_url=user.avatar_url,
                    is_invisible=user.is_invisible,
                    allow_user_wall=user.allow_user_wall,
                    registered_at=user.registered_at,
                    last_login_at=user.last_login_at,
                    is_registered=bool(user.registered_at),
                    lead_id=lead_map.get(user.person_id or 0),
                    source_event_count=event_count_map.get(user.id, 0),
                    person=person_data,
                    ai_profile=ai_profile_map.get(user.person_id or 0, {"profile": None, "latest_task": None}),
                    partner_preference=preference_map.get(user.person_id or 0),
                    interaction_stats={
                        "liked_count": like_count_map.get(user.id, 0),
                        "favorited_count": favorite_count_map.get(user.id, 0),
                        "unlocked_count": unlock_count_map.get(user.id, 0),
                    },
                    recent_actions=action_map.get(user.id, []),
                    coupon_summary={"unused_count": coupon_count_map.get(user.id, 0)},
                ).model_dump()
            )
        return items

    @classmethod
    async def update_user_profile(
        cls,
        auth: AuthSchema,
        user_id: int,
        data: MpUserProfileUpdateSchema,
    ) -> dict:
        result = await auth.db.execute(
            select(MiniProgramUserModel)
            .where(MiniProgramUserModel.id == user_id, MiniProgramUserModel.is_deleted == False)
            .options(selectinload(MiniProgramUserModel.person))
        )
        user = result.scalars().first()
        if not user:
            raise CustomException(msg="小程序用户不存在")
        if not user.person_id or not user.person:
            raise CustomException(msg="该小程序用户尚未完成注册，不能编辑资料")

        person = user.person
        old = {
            "name": person.name,
            "gender": person.gender,
            "wechat": person.wechat,
            "birth_date": person.birth_date.isoformat() if person.birth_date else None,
            "height_cm": person.height_cm,
            "ethnicity": person.ethnicity,
            "occupation": person.occupation,
            "annual_income": person.annual_income,
            "marital_status": person.marital_status,
            "education": person.education,
            "hometown": person.hometown,
            "residence": person.residence,
            "house_status": person.house_status,
            "car_status": person.car_status,
            "photo_urls": person.photo_urls or [],
            "description": person.description,
        }
        payload = data.model_dump()
        compare_payload = {
            **payload,
            "birth_date": payload["birth_date"].isoformat() if payload.get("birth_date") else None,
        }
        for field, value in payload.items():
            setattr(person, field, value)
        user.avatar_url = payload["photo_urls"][0] if payload["photo_urls"] else None
        now = datetime.now()
        operator_id = auth.user.id if auth.user else None
        person.updated_time = now
        person.updated_id = operator_id
        user.updated_time = now
        user.updated_id = operator_id

        changes = {
            field: {"from": old.get(field), "to": compare_payload.get(field)}
            for field in compare_payload
            if old.get(field) != compare_payload.get(field)
        }
        if changes:
            lead_rows = (
                await auth.db.execute(
                    select(CrmLeadProfileModel).where(
                        CrmLeadProfileModel.person_id == person.id,
                        CrmLeadProfileModel.is_deleted == False,
                        CrmLeadProfileModel.lead_type.notin_(["invalid", "converted_customer"]),
                    )
                )
            ).scalars().all()
            for lead in lead_rows:
                lead.updated_time = now
                lead.updated_id = operator_id
                process = CrmLeadProcessRecordModel(
                    brand_id=lead.brand_id,
                    lead_id=lead.id,
                    person_id=lead.person_id,
                    action_type="profile_edit",
                    follow_method="admin_miniprogram",
                    content="Admin 小程序用户资料编辑",
                    operator_user_id=operator_id,
                )
                lifecycle = CrmLeadLifecycleModel(
                    brand_id=lead.brand_id,
                    lead_id=lead.id,
                    person_id=lead.person_id,
                    operation_type="profile_edit",
                    operator_user_id=operator_id,
                    change_detail=changes,
                    remark="Admin 小程序用户资料编辑",
                )
                auth.db.add_all([process, lifecycle])
            await PersonAiProfileService.enqueue_miai_impression(
                db=auth.db,
                person_id=person.id,
                source_type="admin_update",
                source_id=user.id,
            )
            await MatchProfileService.mark_dirty(
                db=auth.db,
                person_id=person.id,
                dirty_parts=["self_profile"],
                source_type="admin_miniprogram_update",
                source_id=user.id,
            )
        await auth.db.flush()
        return await cls.detail_user(auth.db, user_id)

    @classmethod
    async def update_user_wall(
        cls,
        auth: AuthSchema,
        user_id: int,
        data: MpUserWallUpdateSchema,
    ) -> dict:
        result = await auth.db.execute(
            select(MiniProgramUserModel).where(
                MiniProgramUserModel.id == user_id,
                MiniProgramUserModel.is_deleted == False,
            )
        )
        user = result.scalars().first()
        if not user:
            raise CustomException(msg="小程序用户不存在")
        if data.allow_user_wall and user.is_invisible:
            raise CustomException(msg="隐身用户不能开启上墙")
        user.allow_user_wall = data.allow_user_wall
        user.updated_id = auth.user.id if auth.user else None
        await auth.db.flush()
        return await cls.detail_user(auth.db, user_id)

    @classmethod
    async def _recent_action_map(cls, db, user_ids: list[int]) -> dict[int, list[dict]]:
        if not user_ids:
            return {}
        rows = (
            await db.execute(
                select(MpUserProfileActionModel)
                .where(MpUserProfileActionModel.target_user_id.in_(user_ids), MpUserProfileActionModel.is_deleted == False)
                .order_by(MpUserProfileActionModel.occurred_at.desc(), MpUserProfileActionModel.id.desc())
                .limit(len(user_ids) * 5)
            )
        ).scalars().all()
        data: dict[int, list[dict]] = {}
        for row in rows:
            bucket = data.setdefault(row.target_user_id, [])
            if len(bucket) >= 5:
                continue
            bucket.append(
                {
                    "id": row.id,
                    "viewer_user_id": row.viewer_user_id,
                    "target_user_id": row.target_user_id,
                    "action_type": row.action_type,
                    "occurred_at": row.occurred_at,
                    "payload": row.payload,
                }
            )
        return data

    @classmethod
    async def _aggregate_counts(cls, db, user_ids: list[int], column, model, *extra) -> dict[int, int]:
        if not user_ids:
            return {}
        rows = await db.execute(
            select(column, func.count(model.id))
            .where(column.in_(user_ids), model.is_deleted == False, *extra)
            .group_by(column)
        )
        return {int(user_id): int(count or 0) for user_id, count in rows.all()}

    @classmethod
    async def get_settings(cls, db) -> dict:
        raw = {}
        keys = list(DEFAULT_SETTINGS.keys())
        rows = await db.execute(
            select(ParamsModel.config_key, ParamsModel.config_value).where(
                ParamsModel.config_key.in_(keys),
                ParamsModel.is_deleted == False,
            )
        )
        raw.update(dict(rows.all()))
        for key, value in DEFAULT_SETTINGS.items():
            raw.setdefault(key, value)
        default_store_id = cls._to_int(raw.get("miniprogram.unlock.default_store_id"))
        if not default_store_id:
            default_store_id = await cls.default_store_id(db)
        return MpOperationSettingsSchema(
            plaza_show_pending_users=cls._to_bool(raw["miniprogram.plaza.show_pending_users"], False),
            contact_price=raw["miniprogram.unlock.contact_price"],
            allow_coupon=cls._to_bool(raw["miniprogram.unlock.allow_coupon"]),
            allow_paid_boost=cls._to_bool(raw["miniprogram.unlock.allow_paid_boost"]),
            allow_task_free=cls._to_bool(raw["miniprogram.unlock.allow_task_free"]),
            daily_unlock_limit=cls._to_int(raw["miniprogram.unlock.daily_limit"], 5),
            default_store_id=default_store_id,
            heartbeat_initial_min=cls._to_int(raw["miniprogram.heartbeat.initial_min"], 35),
            heartbeat_initial_max=cls._to_int(raw["miniprogram.heartbeat.initial_max"], 55),
            heartbeat_view_score=cls._to_int(raw["miniprogram.heartbeat.view_score"], 1),
            heartbeat_like_score=cls._to_int(raw["miniprogram.heartbeat.like_score"], 8),
            heartbeat_favorite_score=cls._to_int(raw["miniprogram.heartbeat.favorite_score"], 5),
            heartbeat_profile_score=cls._to_int(raw["miniprogram.heartbeat.profile_score"], 0),
            heartbeat_unlock_score=cls._to_int(raw["miniprogram.heartbeat.unlock_score"], 100),
            coupon_enabled=cls._to_bool(raw["miniprogram.coupon.enabled"]),
            coupon_name=raw["miniprogram.coupon.name"],
            coupon_valid_days=cls._to_int(raw["miniprogram.coupon.valid_days"], 30),
            coupon_cycle_days=cls._to_int(raw["miniprogram.coupon.cycle_days"], 2),
            coupon_hold_limit=cls._to_int(raw["miniprogram.coupon.hold_limit"], 1),
            coupon_description=raw["miniprogram.coupon.description"],
            copy_progress=raw["miniprogram.copy.progress"],
            copy_final=raw["miniprogram.copy.final"],
            copy_pay=raw["miniprogram.copy.pay"],
            copy_contact=raw["miniprogram.copy.contact"],
            copy_risk=raw["miniprogram.copy.risk"],
        ).model_dump()

    @classmethod
    async def update_settings(cls, db, data: MpOperationSettingsSchema) -> dict:
        mapping = {
            "miniprogram.plaza.show_pending_users": str(data.plaza_show_pending_users).lower(),
            "miniprogram.unlock.contact_price": data.contact_price,
            "miniprogram.unlock.allow_coupon": str(data.allow_coupon).lower(),
            "miniprogram.unlock.allow_paid_boost": str(data.allow_paid_boost).lower(),
            "miniprogram.unlock.allow_task_free": str(data.allow_task_free).lower(),
            "miniprogram.unlock.daily_limit": str(data.daily_unlock_limit),
            "miniprogram.unlock.default_store_id": str(data.default_store_id or ""),
            "miniprogram.heartbeat.initial_min": str(data.heartbeat_initial_min),
            "miniprogram.heartbeat.initial_max": str(data.heartbeat_initial_max),
            "miniprogram.heartbeat.view_score": str(data.heartbeat_view_score),
            "miniprogram.heartbeat.like_score": str(data.heartbeat_like_score),
            "miniprogram.heartbeat.favorite_score": str(data.heartbeat_favorite_score),
            "miniprogram.heartbeat.profile_score": str(data.heartbeat_profile_score),
            "miniprogram.heartbeat.unlock_score": str(data.heartbeat_unlock_score),
            "miniprogram.coupon.enabled": str(data.coupon_enabled).lower(),
            "miniprogram.coupon.name": data.coupon_name,
            "miniprogram.coupon.valid_days": str(data.coupon_valid_days),
            "miniprogram.coupon.cycle_days": str(data.coupon_cycle_days),
            "miniprogram.coupon.hold_limit": str(data.coupon_hold_limit),
            "miniprogram.coupon.description": data.coupon_description,
            "miniprogram.copy.progress": data.copy_progress,
            "miniprogram.copy.final": data.copy_final,
            "miniprogram.copy.pay": data.copy_pay,
            "miniprogram.copy.contact": data.copy_contact,
            "miniprogram.copy.risk": data.copy_risk,
        }
        for key, value in mapping.items():
            result = await db.execute(select(ParamsModel).where(ParamsModel.config_key == key, ParamsModel.is_deleted == False))
            param = result.scalars().first()
            if param:
                param.config_value = value
            else:
                db.add(
                    ParamsModel(
                        config_name=cls._param_name(key),
                        config_key=key,
                        config_value=value,
                        config_type=True,
                    )
                )
        await db.flush()
        return await cls.get_settings(db)

    @classmethod
    async def default_store_id(cls, db) -> int | None:
        result = await db.execute(
            select(DeptModel.id)
            .where(DeptModel.is_deleted == False, DeptModel.status == "0", DeptModel.parent_id.is_not(None))
            .order_by(DeptModel.order.asc(), DeptModel.id.asc())
        )
        value = result.scalar()
        return int(value) if value else None

    @staticmethod
    def _to_bool(value, default: bool = True) -> bool:
        if value is None:
            return default
        return str(value).lower() in {"true", "1", "yes", "on", "是"}

    @staticmethod
    def _to_int(value, default: int = 0) -> int:
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _param_name(key: str) -> str:
        return {
            "miniprogram.unlock.contact_price": "联系方式解锁价格",
            "miniprogram.unlock.allow_coupon": "允许免费券解锁",
            "miniprogram.unlock.allow_paid_boost": "允许付费补足",
            "miniprogram.unlock.allow_task_free": "允许任务免费解锁",
            "miniprogram.unlock.daily_limit": "每日解锁上限",
            "miniprogram.unlock.default_store_id": "默认收款门店",
            "miniprogram.plaza.show_pending_users": "广场展示待绑定用户",
            "miniprogram.heartbeat.initial_min": "初始心动值下限",
            "miniprogram.heartbeat.initial_max": "初始心动值上限",
            "miniprogram.heartbeat.view_score": "浏览加分",
            "miniprogram.heartbeat.like_score": "喜欢加分",
            "miniprogram.heartbeat.favorite_score": "收藏加分",
            "miniprogram.heartbeat.profile_score": "资料完整加分",
            "miniprogram.heartbeat.unlock_score": "心动值解锁阈值",
            "miniprogram.coupon.enabled": "免费券启用",
            "miniprogram.coupon.name": "免费券名称",
            "miniprogram.coupon.valid_days": "免费券有效天数",
            "miniprogram.coupon.cycle_days": "免费券连续任务周期",
            "miniprogram.coupon.hold_limit": "免费券持有上限",
            "miniprogram.coupon.description": "免费券说明",
            "miniprogram.copy.progress": "解锁进度页文案",
            "miniprogram.copy.final": "解锁最后一步文案",
            "miniprogram.copy.pay": "解锁支付说明文案",
            "miniprogram.copy.contact": "手机号展示提示",
            "miniprogram.copy.risk": "解锁风控提示",
        }.get(key, key)

    @classmethod
    async def page_actions(cls, db, page_no: int, page_size: int, search: MpActionQueryParam | None = None) -> dict:
        viewer_user = aliased(MiniProgramUserModel)
        target_user = aliased(MiniProgramUserModel)
        viewer_person = aliased(CrmPersonModel)
        target_person = aliased(CrmPersonModel)
        conditions = [MpUserProfileActionModel.is_deleted == False]
        stmt = (
            select(MpUserProfileActionModel, viewer_user, viewer_person, target_user, target_person)
            .outerjoin(viewer_user, MpUserProfileActionModel.viewer_user_id == viewer_user.id)
            .outerjoin(viewer_person, viewer_user.person_id == viewer_person.id)
            .outerjoin(target_user, MpUserProfileActionModel.target_user_id == target_user.id)
            .outerjoin(target_person, target_user.person_id == target_person.id)
        )
        count_stmt = (
            select(func.count(MpUserProfileActionModel.id))
            .outerjoin(viewer_user, MpUserProfileActionModel.viewer_user_id == viewer_user.id)
            .outerjoin(viewer_person, viewer_user.person_id == viewer_person.id)
            .outerjoin(target_user, MpUserProfileActionModel.target_user_id == target_user.id)
            .outerjoin(target_person, target_user.person_id == target_person.id)
        )
        if search:
            if search.action_type:
                conditions.append(MpUserProfileActionModel.action_type == search.action_type)
            if search.keyword:
                keyword = f"%{search.keyword}%"
                conditions.append(
                    or_(
                        viewer_user.nickname.like(keyword),
                        viewer_user.mobile.like(keyword),
                        viewer_person.name.like(keyword),
                        viewer_person.display_no.like(keyword),
                        target_user.nickname.like(keyword),
                        target_user.mobile.like(keyword),
                        target_person.name.like(keyword),
                        target_person.display_no.like(keyword),
                    )
                )
        total = (await db.execute(count_stmt.where(and_(*conditions)))).scalar() or 0
        rows = (
            await db.execute(
                stmt.where(and_(*conditions))
                .order_by(MpUserProfileActionModel.occurred_at.desc(), MpUserProfileActionModel.id.desc())
                .offset((page_no - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": [
                {
                    "id": action.id,
                    "action_type": action.action_type,
                    "viewer_user_id": action.viewer_user_id,
                    "viewer_display_no": viewer_person_row.display_no if viewer_person_row else None,
                    "viewer_name": viewer_person_row.name if viewer_person_row else None,
                    "viewer_nickname": viewer_user_row.nickname if viewer_user_row else None,
                    "viewer_mobile": viewer_user_row.mobile if viewer_user_row else None,
                    "target_user_id": action.target_user_id,
                    "target_display_no": target_person_row.display_no if target_person_row else None,
                    "target_name": target_person_row.name if target_person_row else None,
                    "target_nickname": target_user_row.nickname if target_user_row else None,
                    "target_mobile": target_user_row.mobile if target_user_row else None,
                    "occurred_at": action.occurred_at,
                    "payload": action.payload,
                }
                for action, viewer_user_row, viewer_person_row, target_user_row, target_person_row in rows
            ],
        }

    @classmethod
    async def page_coupons(cls, db, page_no: int, page_size: int, search: MpCouponQueryParam | None = None) -> dict:
        conditions = [MpUnlockCouponModel.is_deleted == False]
        stmt = select(MpUnlockCouponModel, MiniProgramUserModel, CrmPersonModel).join(
            MiniProgramUserModel,
            MpUnlockCouponModel.user_id == MiniProgramUserModel.id,
        ).outerjoin(CrmPersonModel, MiniProgramUserModel.person_id == CrmPersonModel.id)
        count_stmt = select(func.count(MpUnlockCouponModel.id)).join(
            MiniProgramUserModel,
            MpUnlockCouponModel.user_id == MiniProgramUserModel.id,
        ).outerjoin(CrmPersonModel, MiniProgramUserModel.person_id == CrmPersonModel.id)
        if search:
            if search.coupon_status:
                conditions.append(MpUnlockCouponModel.coupon_status == search.coupon_status)
            if search.keyword:
                keyword = f"%{search.keyword}%"
                conditions.append(or_(MiniProgramUserModel.nickname.like(keyword), MiniProgramUserModel.mobile.like(keyword), CrmPersonModel.name.like(keyword), CrmPersonModel.display_no.like(keyword)))
        total = (await db.execute(count_stmt.where(and_(*conditions)))).scalar() or 0
        rows = (
            await db.execute(
                stmt.where(and_(*conditions))
                .order_by(MpUnlockCouponModel.created_time.desc(), MpUnlockCouponModel.id.desc())
                .offset((page_no - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": [
                {
                    "id": coupon.id,
                    "user_id": coupon.user_id,
                    "display_no": person.display_no if person else None,
                    "nickname": user.nickname,
                    "mobile": user.mobile,
                    "coupon_name": coupon.coupon_name,
                    "coupon_status": coupon.coupon_status,
                    "valid_from": coupon.valid_from,
                    "valid_to": coupon.valid_to,
                    "used_at": coupon.used_at,
                    "grant_reason": coupon.grant_reason,
                }
                for coupon, user, person in rows
            ],
        }

    @classmethod
    async def grant_coupon(cls, db, data: MpCouponGrantSchema) -> dict:
        result = await db.execute(
            select(MiniProgramUserModel).where(MiniProgramUserModel.id == data.user_id, MiniProgramUserModel.is_deleted == False)
        )
        user = result.scalars().first()
        if not user:
            raise CustomException(msg="小程序用户不存在")
        settings = await cls.get_settings(db)
        name = data.coupon_name or settings["coupon_name"]
        days = data.valid_days or settings["coupon_valid_days"]
        now = datetime.now()
        for _ in range(data.quantity):
            db.add(
                MpUnlockCouponModel(
                    brand_id=1,
                    user_id=user.id,
                    person_id=user.person_id,
                    coupon_name=name,
                    coupon_status="unused",
                    valid_from=now,
                    valid_to=now + timedelta(days=days),
                    grant_reason=data.grant_reason,
                    grant_source="admin",
                )
            )
        await db.flush()
        return {"granted": data.quantity}

    @classmethod
    async def list_tasks(cls, db) -> list[dict]:
        await MpPlazaService._ensure_default_tasks(db)
        rows = (
            await db.execute(
                select(MpUnlockTaskModel)
                .where(MpUnlockTaskModel.is_deleted == False)
                .order_by(MpUnlockTaskModel.sort.asc(), MpUnlockTaskModel.id.asc())
            )
        ).scalars().all()
        return [cls._task_out(row) for row in rows]

    @staticmethod
    def _task_out(row: MpUnlockTaskModel) -> dict:
        return {
            "id": row.id,
            "task_code": row.task_code,
            "task_name": row.task_name,
            "task_type": row.task_type,
            "task_group": row.task_group,
            "score": row.score,
            "is_global": row.is_global,
            "is_target": row.is_target,
            "daily_limit": row.daily_limit,
            "sort": row.sort,
            "status": row.status,
        }

    @classmethod
    async def save_task(cls, db, data: MpTaskUpsertSchema, task_id: int | None = None) -> dict:
        task = await db.get(MpUnlockTaskModel, task_id) if task_id else None
        if not task:
            result = await db.execute(select(MpUnlockTaskModel).where(MpUnlockTaskModel.task_code == data.task_code, MpUnlockTaskModel.is_deleted == False))
            task = result.scalars().first()
        payload = data.model_dump()
        if task:
            for key, value in payload.items():
                setattr(task, key, value)
        else:
            task = MpUnlockTaskModel(brand_id=1, **payload)
            db.add(task)
        await db.flush()
        return cls._task_out(task)

    @classmethod
    async def list_questions(cls, db) -> list[dict]:
        await MpPlazaService._ensure_default_questions(db)
        rows = (
            await db.execute(
                select(MpUnlockQuestionModel)
                .where(MpUnlockQuestionModel.is_deleted == False)
                .order_by(MpUnlockQuestionModel.sort.asc(), MpUnlockQuestionModel.id.asc())
            )
        ).scalars().all()
        return [cls._question_out(row) for row in rows]

    @staticmethod
    def _question_out(row: MpUnlockQuestionModel) -> dict:
        return {
            "id": row.id,
            "question": row.question,
            "options": row.options,
            "recommended_answer": row.recommended_answer,
            "match_tags": row.match_tags,
            "correct_score": row.correct_score,
            "wrong_score": row.wrong_score,
            "category": row.category,
            "sort": row.sort,
            "status": row.status,
        }

    @classmethod
    async def save_question(cls, db, data: MpQuestionUpsertSchema, question_id: int | None = None) -> dict:
        question = await db.get(MpUnlockQuestionModel, question_id) if question_id else None
        payload = data.model_dump()
        if question:
            for key, value in payload.items():
                setattr(question, key, value)
        else:
            question = MpUnlockQuestionModel(brand_id=1, **payload)
            db.add(question)
        await db.flush()
        return cls._question_out(question)

    @classmethod
    async def page_unlock_records(cls, db, page_no: int, page_size: int, search: MpUnlockRecordQueryParam | None = None) -> dict:
        viewer_user = aliased(MiniProgramUserModel)
        target_user = aliased(MiniProgramUserModel)
        viewer_person = aliased(CrmPersonModel)
        target_person = aliased(CrmPersonModel)
        conditions = [MpContactUnlockModel.is_deleted == False]
        stmt = (
            select(
                MpContactUnlockModel,
                viewer_user,
                viewer_person,
                target_user,
                target_person,
                func.count(MpContactViewLogModel.id),
                func.max(MpContactViewLogModel.viewed_at),
            )
            .join(viewer_user, MpContactUnlockModel.viewer_user_id == viewer_user.id)
            .outerjoin(viewer_person, viewer_user.person_id == viewer_person.id)
            .join(target_user, MpContactUnlockModel.target_user_id == target_user.id)
            .outerjoin(target_person, target_user.person_id == target_person.id)
            .outerjoin(MpContactViewLogModel, MpContactViewLogModel.unlock_id == MpContactUnlockModel.id)
            .group_by(MpContactUnlockModel.id, viewer_user.id, viewer_person.id, target_user.id, target_person.id)
        )
        count_stmt = (
            select(func.count(MpContactUnlockModel.id))
            .join(viewer_user, MpContactUnlockModel.viewer_user_id == viewer_user.id)
            .outerjoin(viewer_person, viewer_user.person_id == viewer_person.id)
            .join(target_user, MpContactUnlockModel.target_user_id == target_user.id)
            .outerjoin(target_person, target_user.person_id == target_person.id)
        )
        if search:
            if search.unlock_status:
                conditions.append(MpContactUnlockModel.unlock_status == search.unlock_status)
            if search.keyword:
                keyword = f"%{search.keyword}%"
                conditions.append(
                    or_(
                        viewer_user.nickname.like(keyword),
                        viewer_user.mobile.like(keyword),
                        viewer_person.name.like(keyword),
                        viewer_person.display_no.like(keyword),
                        target_user.nickname.like(keyword),
                        target_user.mobile.like(keyword),
                        target_person.name.like(keyword),
                        target_person.display_no.like(keyword),
                    )
                )
        total = (await db.execute(count_stmt.where(and_(*conditions)))).scalar() or 0
        rows = (
            await db.execute(
                stmt.where(and_(*conditions))
                .order_by(MpContactUnlockModel.created_time.desc(), MpContactUnlockModel.id.desc())
                .offset((page_no - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": [
                {
                    "id": unlock.id,
                    "viewer_user_id": unlock.viewer_user_id,
                    "target_user_id": unlock.target_user_id,
                    "viewer_display_no": viewer_person_row.display_no if viewer_person_row else None,
                    "viewer_name": viewer_person_row.name if viewer_person_row else None,
                    "viewer_nickname": viewer_user_row.nickname,
                    "viewer_mobile": viewer_user_row.mobile,
                    "target_display_no": target_person_row.display_no if target_person_row else None,
                    "target_name": target_person_row.name if target_person_row else None,
                    "target_nickname": target_user_row.nickname,
                    "unlock_source": unlock.unlock_source,
                    "unlock_method": unlock.unlock_method,
                    "unlock_status": unlock.unlock_status,
                    "amount": str(unlock.amount),
                    "order_id": unlock.order_id,
                    "coupon_id": unlock.coupon_id,
                    "unlocked_at": unlock.unlocked_at,
                    "revoked_at": unlock.revoked_at,
                    "revoke_reason": unlock.revoke_reason,
                    "view_count": int(view_count or 0),
                    "last_viewed_at": last_viewed_at,
                }
                for unlock, viewer_user_row, viewer_person_row, target_user_row, target_person_row, view_count, last_viewed_at in rows
            ],
        }

    @classmethod
    async def revoke_unlock_record(cls, db, unlock_id: int, data: MpUnlockRevokeSchema, operator_id: int | None = None) -> dict:
        unlock = await db.get(MpContactUnlockModel, unlock_id)
        if not unlock or unlock.is_deleted:
            raise CustomException(msg="解锁记录不存在")
        unlock.unlock_status = data.status
        unlock.revoked_at = datetime.now()
        unlock.revoked_by = operator_id
        unlock.revoke_reason = data.reason
        await db.flush()
        return {"id": unlock.id, "unlock_status": unlock.unlock_status}

    @classmethod
    async def page_contact_views(cls, db, page_no: int, page_size: int, search: MpUnlockRecordQueryParam | None = None) -> dict:
        conditions = [MpContactViewLogModel.is_deleted == False]
        stmt = select(MpContactViewLogModel, MiniProgramUserModel, CrmPersonModel).join(
            MiniProgramUserModel, MpContactViewLogModel.target_user_id == MiniProgramUserModel.id
        ).outerjoin(CrmPersonModel, MiniProgramUserModel.person_id == CrmPersonModel.id)
        count_stmt = select(func.count(MpContactViewLogModel.id)).join(
            MiniProgramUserModel, MpContactViewLogModel.target_user_id == MiniProgramUserModel.id
        ).outerjoin(CrmPersonModel, MiniProgramUserModel.person_id == CrmPersonModel.id)
        if search and search.keyword:
            keyword = f"%{search.keyword}%"
            conditions.append(or_(MiniProgramUserModel.nickname.like(keyword), MiniProgramUserModel.mobile.like(keyword), CrmPersonModel.name.like(keyword), CrmPersonModel.display_no.like(keyword)))
        total = (await db.execute(count_stmt.where(and_(*conditions)))).scalar() or 0
        rows = (
            await db.execute(
                stmt.where(and_(*conditions))
                .order_by(MpContactViewLogModel.viewed_at.desc(), MpContactViewLogModel.id.desc())
                .offset((page_no - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": [
                {
                    "id": log.id,
                    "unlock_id": log.unlock_id,
                    "viewer_user_id": log.viewer_user_id,
                    "target_user_id": log.target_user_id,
                    "target_display_no": person.display_no if person else None,
                    "target_name": person.name if person else None,
                    "target_nickname": user.nickname,
                    "viewed_at": log.viewed_at,
                    "payload": log.payload,
                }
                for log, user, person in rows
            ],
        }
