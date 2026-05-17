from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from app.api.v1.module_system.auth.schema import AuthSchema
from app.api.v1.module_system.dept.model import DeptModel
from app.core.exceptions import CustomException
from app.plugin.module_event.model import EventModel, EventParticipantModel, EventRegistrationModel
from app.plugin.module_payment.core.model import PaymentOrderModel

from .schema import EventEffectSchema, EventQueryParam, EventUpsertSchema


class EventAdminService:
    """后台活动管理服务。"""

    ACTIVE_REGISTRATION_STATUSES = {"registered", "checked_in"}

    @classmethod
    def _effective_status(cls, event: EventModel, now: datetime | None = None) -> str:
        if event.event_status == "published" and event.end_time <= (now or datetime.now()):
            return "finished"
        return event.event_status

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
    def _scope_conditions(cls, auth: AuthSchema) -> list[Any]:
        conditions: list[Any] = [EventModel.is_deleted == False]
        if cls._is_brand_admin(auth):
            return conditions
        if cls._is_store_mgr(auth) and auth.user:
            conditions.extend([EventModel.store_id == auth.user.dept_id, EventModel.created_id == auth.user.id])
            return conditions
        conditions.append(EventModel.created_id == (auth.user.id if auth.user else -1))
        return conditions

    @classmethod
    async def _ensure_manage_access(cls, auth: AuthSchema, event: EventModel) -> None:
        if cls._is_brand_admin(auth):
            return
        if cls._is_store_mgr(auth) and auth.user and event.store_id == auth.user.dept_id and event.created_id == auth.user.id:
            return
        if auth.user and event.created_id == auth.user.id:
            return
        raise CustomException(msg="无权限维护该活动", code=10403, status_code=403)

    @classmethod
    async def _get_event(cls, auth: AuthSchema, event_id: int) -> EventModel:
        result = await auth.db.execute(
            select(EventModel)
            .where(EventModel.id == event_id, EventModel.is_deleted == False)
            .options(selectinload(EventModel.store), selectinload(EventModel.created_by))
        )
        event = result.scalars().first()
        if not event:
            raise CustomException(msg="活动不存在")
        await cls._ensure_manage_access(auth, event)
        return event

    @classmethod
    async def _counts(cls, auth: AuthSchema, event_ids: list[int]) -> dict[int, dict[str, int]]:
        if not event_ids:
            return {}
        reg_rows = (
            await auth.db.execute(
                select(
                    EventRegistrationModel.event_id,
                    EventRegistrationModel.gender_snapshot,
                    func.count(EventRegistrationModel.id),
                )
                .where(
                    EventRegistrationModel.event_id.in_(event_ids),
                    EventRegistrationModel.registration_status.in_(cls.ACTIVE_REGISTRATION_STATUSES),
                    EventRegistrationModel.is_deleted == False,
                )
                .group_by(EventRegistrationModel.event_id, EventRegistrationModel.gender_snapshot)
            )
        ).all()
        check_rows = (
            await auth.db.execute(
                select(EventParticipantModel.event_id, func.count(EventParticipantModel.id))
                .where(
                    EventParticipantModel.event_id.in_(event_ids),
                    EventParticipantModel.participant_status == "checked_in",
                    EventParticipantModel.is_deleted == False,
                )
                .group_by(EventParticipantModel.event_id)
            )
        ).all()
        data = {event_id: {"male_registered": 0, "female_registered": 0, "checked_in_count": 0} for event_id in event_ids}
        for event_id, gender, count in reg_rows:
            if gender == "0":
                data[event_id]["male_registered"] = count
            elif gender == "1":
                data[event_id]["female_registered"] = count
        for event_id, count in check_rows:
            data[event_id]["checked_in_count"] = count
        return data

    @classmethod
    def _event_out(cls, event: EventModel, counts: dict[str, int] | None = None, payment_summary: list[dict] | None = None) -> dict:
        data = {
            "id": event.id,
            "store_id": event.store_id,
            "store_name": event.store.name if event.store else None,
            "created_id": event.created_id,
            "created_name": event.created_by.name if event.created_by else None,
            "title": event.title,
            "subtitle": event.subtitle,
            "event_type": event.event_type,
            "cover_url": event.cover_url,
            "location": event.location,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "register_deadline": event.register_deadline,
            "detail_html": event.detail_html,
            "effect_html": event.effect_html,
            "male_quota": event.male_quota,
            "female_quota": event.female_quota,
            "male_fee": event.male_fee,
            "female_fee": event.female_fee,
            "vip_free": event.vip_free,
            "require_realname": event.require_realname,
            "min_age": event.min_age,
            "max_age": event.max_age,
            "event_status": cls._effective_status(event),
            "published_by": event.published_by,
            "published_at": event.published_at,
            "payment_summary": payment_summary or [],
        }
        data.update(counts or {"male_registered": 0, "female_registered": 0, "checked_in_count": 0})
        return data

    @classmethod
    def _resolve_store_id(cls, auth: AuthSchema, data: EventUpsertSchema) -> int:
        if cls._is_brand_admin(auth):
            if not data.store_id:
                raise CustomException(msg="请选择活动归属门店")
            return data.store_id
        if cls._is_store_mgr(auth) and auth.user and auth.user.dept_id:
            if data.store_id and data.store_id != auth.user.dept_id:
                raise CustomException(msg="门店管理员只能创建自己门店活动", code=10403, status_code=403)
            return auth.user.dept_id
        if not data.store_id:
            raise CustomException(msg="当前账号缺少活动归属门店")
        return data.store_id

    @classmethod
    async def _validate_paid_store(cls, auth: AuthSchema, store_id: int, data: EventUpsertSchema) -> None:
        if data.male_fee <= 0 and data.female_fee <= 0:
            return
        store = await auth.db.get(DeptModel, store_id)
        if not store or store.is_deleted or store.status != "0":
            raise CustomException(msg="付费活动归属门店不存在或已停用")
        if store.parent_id is None:
            raise CustomException(msg="付费活动请选择实际门店，不能选择总部/品牌节点")
        if not store.code:
            raise CustomException(msg="付费活动归属门店缺少云支付门店编码")

    @classmethod
    async def list_service(cls, auth: AuthSchema, search: EventQueryParam) -> dict:
        conditions = cls._scope_conditions(auth)
        if search.keyword:
            keyword = f"%{search.keyword.strip()}%"
            conditions.append(or_(EventModel.title.ilike(keyword), EventModel.location.ilike(keyword)))
        now = datetime.now()
        if search.event_status == "finished":
            conditions.append(or_(EventModel.event_status == "finished", and_(EventModel.event_status == "published", EventModel.end_time <= now)))
        elif search.event_status == "published":
            conditions.append(and_(EventModel.event_status == "published", EventModel.end_time > now))
        elif search.event_status:
            conditions.append(EventModel.event_status == search.event_status)
        if search.event_type:
            conditions.append(EventModel.event_type == search.event_type)
        if search.store_id:
            conditions.append(EventModel.store_id == search.store_id)
        if search.start_time and len(search.start_time) == 2:
            conditions.append(EventModel.start_time.between(search.start_time[0], search.start_time[1]))
        total = (
            await auth.db.execute(select(func.count(EventModel.id)).where(and_(*conditions)))
        ).scalar() or 0
        rows = (
            await auth.db.execute(
                select(EventModel)
                .where(and_(*conditions))
                .options(selectinload(EventModel.store), selectinload(EventModel.created_by))
                .order_by(EventModel.id.desc())
                .offset((search.page_no - 1) * search.page_size)
                .limit(search.page_size)
            )
        ).scalars().all()
        counts = await cls._counts(auth, [row.id for row in rows])
        return {
            "page_no": search.page_no,
            "page_size": search.page_size,
            "total": total,
            "has_next": search.page_no * search.page_size < total,
            "items": [cls._event_out(row, counts.get(row.id)) for row in rows],
        }

    @classmethod
    async def detail_service(cls, auth: AuthSchema, event_id: int) -> dict:
        event = await cls._get_event(auth, event_id)
        counts = await cls._counts(auth, [event.id])
        rows = (
            await auth.db.execute(
                select(PaymentOrderModel.order_status, PaymentOrderModel.pay_status, func.count(PaymentOrderModel.id), func.coalesce(func.sum(PaymentOrderModel.paid_amount), Decimal("0.00")))
                .where(PaymentOrderModel.biz_type == "event_registration", PaymentOrderModel.is_deleted == False)
                .join(EventRegistrationModel, EventRegistrationModel.order_id == PaymentOrderModel.id)
                .where(EventRegistrationModel.event_id == event.id)
                .group_by(PaymentOrderModel.order_status, PaymentOrderModel.pay_status)
            )
        ).all()
        payment_summary = [
            {"order_status": row[0], "pay_status": row[1], "count": row[2], "paid_amount": row[3]} for row in rows
        ]
        return cls._event_out(event, counts.get(event.id), payment_summary)

    @classmethod
    async def create_service(cls, auth: AuthSchema, data: EventUpsertSchema) -> dict:
        store_id = cls._resolve_store_id(auth, data)
        await cls._validate_paid_store(auth, store_id, data)
        event = EventModel(
            brand_id=1,
            store_id=store_id,
            **data.model_dump(exclude={"store_id"}),
            event_status="draft",
        )
        cls._stamp_create(auth, event)
        auth.db.add(event)
        await auth.db.flush()
        await auth.db.refresh(event)
        return await cls.detail_service(auth, event.id)

    @classmethod
    async def update_service(cls, auth: AuthSchema, event_id: int, data: EventUpsertSchema) -> dict:
        event = await cls._get_event(auth, event_id)
        if cls._effective_status(event) in {"finished", "cancelled"}:
            raise CustomException(msg="已结束或已取消活动不能编辑")
        store_id = cls._resolve_store_id(auth, data)
        await cls._validate_paid_store(auth, store_id, data)
        for field, value in data.model_dump().items():
            if field == "store_id":
                event.store_id = store_id
            else:
                setattr(event, field, value)
        cls._stamp_update(auth, event)
        await auth.db.flush()
        return await cls.detail_service(auth, event.id)

    @classmethod
    async def publish_service(cls, auth: AuthSchema, event_id: int) -> dict:
        event = await cls._get_event(auth, event_id)
        if event.event_status not in {"draft", "cancelled"}:
            raise CustomException(msg="只有草稿或已取消活动可以发布")
        now = datetime.now()
        if event.end_time <= now:
            raise CustomException(msg="活动已结束，不能发布")
        if event.register_deadline <= now:
            raise CustomException(msg="报名截止时间已过，不能发布")
        event.event_status = "published"
        event.published_by = auth.user.id if auth.user else None
        event.published_at = now
        cls._stamp_update(auth, event)
        await auth.db.flush()
        return await cls.detail_service(auth, event.id)

    @classmethod
    async def cancel_service(cls, auth: AuthSchema, event_id: int) -> dict:
        event = await cls._get_event(auth, event_id)
        if cls._effective_status(event) == "finished":
            raise CustomException(msg="已结束活动不能取消")
        event.event_status = "cancelled"
        cls._stamp_update(auth, event)
        await auth.db.flush()
        return await cls.detail_service(auth, event.id)

    @classmethod
    async def finish_service(cls, auth: AuthSchema, event_id: int) -> dict:
        event = await cls._get_event(auth, event_id)
        if event.event_status == "cancelled":
            raise CustomException(msg="已取消活动不能结束")
        event.event_status = "finished"
        cls._stamp_update(auth, event)
        await auth.db.flush()
        return await cls.detail_service(auth, event.id)

    @classmethod
    async def effect_service(cls, auth: AuthSchema, event_id: int, data: EventEffectSchema) -> dict:
        event = await cls._get_event(auth, event_id)
        event.effect_html = data.effect_html
        cls._stamp_update(auth, event)
        await auth.db.flush()
        return await cls.detail_service(auth, event.id)

    @classmethod
    async def registration_list_service(cls, auth: AuthSchema, event_id: int) -> list[dict]:
        event = await cls._get_event(auth, event_id)
        rows = (
            await auth.db.execute(
                select(EventRegistrationModel)
                .where(EventRegistrationModel.event_id == event.id, EventRegistrationModel.is_deleted == False)
                .options(
                    selectinload(EventRegistrationModel.person),
                    selectinload(EventRegistrationModel.mp_user),
                    selectinload(EventRegistrationModel.order),
                )
                .order_by(EventRegistrationModel.created_time.desc(), EventRegistrationModel.id.desc())
            )
        ).scalars().all()
        data: list[dict] = []
        for row in rows:
            data.append(
                {
                    "id": row.id,
                    "registration_no": row.registration_no,
                    "name": row.person.name if row.person else None,
                    "mobile_masked": cls._mask_mobile(row.person.primary_mobile if row.person else None),
                    "gender": row.gender_snapshot,
                    "registration_status": row.registration_status,
                    "payable_amount": row.payable_amount,
                    "paid_amount": row.paid_amount,
                    "registered_at": row.registered_at,
                    "order_id": row.order_id,
                    "order_no": row.order.order_no if row.order else None,
                    "order_status": row.order.order_status if row.order else None,
                    "pay_status": row.order.pay_status if row.order else None,
                }
            )
        return data

    @classmethod
    async def participant_list_service(cls, auth: AuthSchema, event_id: int) -> list[dict]:
        event = await cls._get_event(auth, event_id)
        rows = (
            await auth.db.execute(
                select(EventParticipantModel)
                .where(EventParticipantModel.event_id == event.id, EventParticipantModel.is_deleted == False)
                .options(selectinload(EventParticipantModel.person), selectinload(EventParticipantModel.mp_user))
                .order_by(EventParticipantModel.checked_in_at.desc(), EventParticipantModel.id.desc())
            )
        ).scalars().all()
        return [
            {
                "id": row.id,
                "onsite_no": row.onsite_no,
                "name": row.person.name if row.person else None,
                "nickname": row.display_nickname,
                "gender": row.gender_snapshot,
                "checkin_type": row.checkin_type,
                "checked_in_at": row.checked_in_at,
                "participant_status": row.participant_status,
            }
            for row in rows
        ]

    @classmethod
    async def admin_checkin_service(cls, auth: AuthSchema, registration_id: int) -> dict:
        result = await auth.db.execute(
            select(EventRegistrationModel)
            .where(EventRegistrationModel.id == registration_id, EventRegistrationModel.is_deleted == False)
            .options(selectinload(EventRegistrationModel.event))
        )
        registration = result.scalars().first()
        if not registration:
            raise CustomException(msg="报名记录不存在")
        await cls._ensure_manage_access(auth, registration.event)
        if registration.registration_status == "pending_payment":
            raise CustomException(msg="报名未支付，不能签到")
        from app.plugin.module_mp.event.schema import MpEventCheckinSchema
        from app.plugin.module_mp.event.service import MpEventService

        return await MpEventService.checkin_service(
            db=auth.db,
            event_id=registration.event_id,
            user_id=registration.mp_user_id,
            data=MpEventCheckinSchema(registration_id=registration.id, payload={"admin_checkin_by": auth.user.id if auth.user else None}),
        )

    @classmethod
    def _mask_mobile(cls, mobile: str | None) -> str | None:
        if not mobile or len(mobile) < 7:
            return mobile
        return f"{mobile[:3]}****{mobile[-4:]}"

    @classmethod
    async def delete_service(cls, auth: AuthSchema, ids: list[int]) -> None:
        for event_id in ids:
            event = await cls._get_event(auth, event_id)
            if cls._effective_status(event) == "published":
                raise CustomException(msg="已发布活动请先取消后再删除")
            event.is_deleted = True
            event.deleted_time = datetime.now()
            if auth.user:
                event.deleted_id = auth.user.id
        await auth.db.flush()
