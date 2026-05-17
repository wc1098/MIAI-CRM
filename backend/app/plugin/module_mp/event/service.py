from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.module_system.dept.model import DeptModel
from app.core.exceptions import CustomException
from app.plugin.module_crm.lead.model import (
    CrmLeadLifecycleModel,
    CrmLeadProfileModel,
    CrmPersonModel,
)
from app.plugin.module_event.model import EventModel, EventParticipantModel, EventRegistrationModel
from app.plugin.module_mp.auth.model import MiniProgramUserModel, SourceEventModel
from app.plugin.module_payment.core.model import PaymentOrderModel
from app.plugin.module_payment.core.service import PaymentService

from .schema import MpEventCheckinSchema, MpEventRegisterSchema

MINIAPP_EVENT_CHANNEL = "MINIAPP_EVENT"
EVENT_PAYMENT_EXPIRE_MINUTES = 24 * 60


class MpEventService:
    """小程序活动服务。"""

    ACTIVE_REGISTRATION_STATUSES = {"registered", "checked_in"}

    @classmethod
    def _effective_status(cls, event: EventModel, now: datetime | None = None) -> str:
        if event.event_status == "published" and event.end_time <= (now or datetime.now()):
            return "finished"
        return event.event_status

    @staticmethod
    def _registration_no(prefix: str) -> str:
        return f"{prefix}{datetime.now():%y%m%d%H%M%S}{uuid4().hex[:8].upper()}"

    @classmethod
    async def _get_mp_user(cls, db: AsyncSession, user_id: int) -> MiniProgramUserModel:
        result = await db.execute(
            select(MiniProgramUserModel)
            .where(MiniProgramUserModel.id == user_id, MiniProgramUserModel.is_deleted == False)
            .options(selectinload(MiniProgramUserModel.person))
        )
        user = result.scalars().first()
        if not user:
            raise CustomException(msg="小程序用户不存在", code=10401, status_code=401)
        if not user.person_id or not user.person:
            raise CustomException(msg="请先完成注册资料", code=10401, status_code=401)
        return user

    @classmethod
    async def _get_published_event(cls, db: AsyncSession, event_id: int) -> EventModel:
        result = await db.execute(
            select(EventModel)
            .where(EventModel.id == event_id, EventModel.is_deleted == False)
            .options(selectinload(EventModel.store))
        )
        event = result.scalars().first()
        if not event or event.event_status not in {"published", "finished"}:
            raise CustomException(msg="活动不存在或未发布")
        return event

    @classmethod
    async def _counts(cls, db: AsyncSession, event_ids: list[int]) -> dict[int, dict[str, int]]:
        if not event_ids:
            return {}
        rows = (
            await db.execute(
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
        data = {event_id: {"male_registered": 0, "female_registered": 0} for event_id in event_ids}
        for event_id, gender, count in rows:
            if gender == "0":
                data[event_id]["male_registered"] = count
            elif gender == "1":
                data[event_id]["female_registered"] = count
        return data

    @classmethod
    def _event_out(cls, event: EventModel, counts: dict[str, int] | None = None, registration: EventRegistrationModel | None = None) -> dict:
        counts = counts or {"male_registered": 0, "female_registered": 0}
        return {
            "id": event.id,
            "title": event.title,
            "subtitle": event.subtitle,
            "event_type": event.event_type,
            "cover_url": event.cover_url,
            "location": event.location,
            "store_name": event.store.name if event.store else None,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "register_deadline": event.register_deadline,
            "detail_html": event.detail_html,
            "effect_html": event.effect_html,
            "display_html": event.effect_html if cls._effective_status(event) == "finished" else event.detail_html,
            "male_quota": event.male_quota,
            "female_quota": event.female_quota,
            "male_fee": event.male_fee,
            "female_fee": event.female_fee,
            "vip_free": event.vip_free,
            "require_realname": event.require_realname,
            "min_age": event.min_age,
            "max_age": event.max_age,
            "event_status": cls._effective_status(event),
            "male_remaining": max(event.male_quota - counts["male_registered"], 0),
            "female_remaining": max(event.female_quota - counts["female_registered"], 0),
            "my_registration": cls._registration_out(registration) if registration else None,
        }

    @classmethod
    def _registration_out(cls, registration: EventRegistrationModel | None) -> dict | None:
        if not registration:
            return None
        return {
            "id": registration.id,
            "registration_no": registration.registration_no,
            "registration_status": registration.registration_status,
            "payable_amount": registration.payable_amount,
            "paid_amount": registration.paid_amount,
            "order_id": registration.order_id,
            "payment_expire_at": registration.payment_expire_at,
        }

    @classmethod
    async def list_service(cls, db: AsyncSession, page_no: int = 1, page_size: int = 10, user_id: int | None = None) -> dict:
        conditions = [EventModel.event_status == "published", EventModel.end_time > datetime.now(), EventModel.is_deleted == False]
        total = (await db.execute(select(func.count(EventModel.id)).where(*conditions))).scalar() or 0
        rows = (
            await db.execute(
                select(EventModel)
                .where(*conditions)
                .options(selectinload(EventModel.store))
                .order_by(EventModel.start_time.asc(), EventModel.id.desc())
                .offset((page_no - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        event_ids = [row.id for row in rows]
        counts = await cls._counts(db, event_ids)
        registrations: dict[int, EventRegistrationModel] = {}
        if user_id and event_ids:
            registration_rows = (
                await db.execute(
                    select(EventRegistrationModel).where(
                        EventRegistrationModel.event_id.in_(event_ids),
                        EventRegistrationModel.mp_user_id == user_id,
                        EventRegistrationModel.is_deleted == False,
                    )
                )
            ).scalars().all()
            registrations = {row.event_id: row for row in registration_rows}
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": [cls._event_out(row, counts.get(row.id), registrations.get(row.id)) for row in rows],
        }

    @classmethod
    async def detail_service(cls, db: AsyncSession, event_id: int, user_id: int | None = None) -> dict:
        event = await cls._get_published_event(db, event_id)
        registration = None
        if user_id:
            result = await db.execute(
                select(EventRegistrationModel).where(
                    EventRegistrationModel.event_id == event_id,
                    EventRegistrationModel.mp_user_id == user_id,
                    EventRegistrationModel.is_deleted == False,
                )
            )
            registration = result.scalars().first()
        counts = await cls._counts(db, [event.id])
        return cls._event_out(event, counts.get(event.id), registration)

    @classmethod
    def _age(cls, birth_date: date | None) -> int | None:
        if not birth_date:
            return None
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    @classmethod
    async def _validate_register(cls, db: AsyncSession, event: EventModel, user: MiniProgramUserModel) -> None:
        now = datetime.now()
        if cls._effective_status(event) != "published":
            raise CustomException(msg="活动暂不可报名")
        if event.register_deadline <= now:
            raise CustomException(msg="活动报名已截止")
        person = user.person
        if not person:
            raise CustomException(msg="请先完成注册资料")
        if event.require_realname and not person.id_card_no:
            raise CustomException(msg="该活动要求实名认证，请先到认证中心完成实名认证")
        age = cls._age(person.birth_date)
        if event.min_age and age is not None and age < event.min_age:
            raise CustomException(msg="年龄不符合活动报名要求")
        if event.max_age and age is not None and age > event.max_age:
            raise CustomException(msg="年龄不符合活动报名要求")
        if person.gender == "0":
            counts = await cls._counts(db, [event.id])
            if counts[event.id]["male_registered"] >= event.male_quota:
                raise CustomException(msg="男生名额已满")
        elif person.gender == "1":
            counts = await cls._counts(db, [event.id])
            if counts[event.id]["female_registered"] >= event.female_quota:
                raise CustomException(msg="女生名额已满")
        else:
            raise CustomException(msg="请先完善性别后再报名")

    @classmethod
    def _fee_for_person(cls, event: EventModel, person: CrmPersonModel) -> Decimal:
        if person.gender == "0":
            return event.male_fee
        if person.gender == "1":
            return event.female_fee
        return Decimal("0.00")

    @classmethod
    async def _validate_paid_event_store(cls, db: AsyncSession, event: EventModel, amount: Decimal) -> None:
        if amount <= 0:
            return
        store = await db.get(DeptModel, event.store_id)
        if not store or store.is_deleted or store.status != "0":
            raise CustomException(msg="活动归属门店不存在或已停用，无法发起支付")
        if store.parent_id is None:
            raise CustomException(msg="付费活动必须归属实际门店，请在活动后台选择非顶级门店后再报名")
        if not store.code:
            raise CustomException(msg="活动归属门店缺少云支付门店编码，无法发起支付")

    @classmethod
    async def _create_registration_order(
        cls,
        db: AsyncSession,
        request: Request,
        event: EventModel,
        user: MiniProgramUserModel,
        registration: EventRegistrationModel,
        amount: Decimal,
    ) -> dict:
        order = await PaymentService.create_order(
            db,
            biz_type="event_registration",
            biz_id=registration.id,
            subject=f"活动报名-{event.title}",
            amount=amount,
            store_id=event.store_id,
            person_id=user.person_id,
            mp_user_id=user.id,
            expire_minutes=EVENT_PAYMENT_EXPIRE_MINUTES,
            extra={"event_id": event.id},
        )
        registration.order_id = order.id
        registration.payment_expire_at = order.expire_at
        registration.registration_status = "pending_payment"
        registration.payable_amount = amount
        registration.paid_amount = Decimal("0.00")
        await db.flush()
        payment = await PaymentService.create_cloudpay_mp_payment(
            db,
            order=order,
            buyer_id=user.openid,
            notify_url=cls._notify_url(request),
        )
        return payment

    @classmethod
    def _order_can_continue(cls, registration: EventRegistrationModel) -> bool:
        order = registration.order
        if not order:
            return False
        if order.pay_status in {"paid", "timeout", "closed", "failed"}:
            return False
        if order.order_status in {"paid", "closed", "cancelled"}:
            return False
        if registration.payment_expire_at and datetime.now() >= registration.payment_expire_at:
            return False
        if order.expire_at and datetime.now() >= order.expire_at:
            return False
        return True

    @classmethod
    async def _append_source_event(
        cls,
        db: AsyncSession,
        *,
        event_type: str,
        event: EventModel,
        user: MiniProgramUserModel,
        payload: dict | None = None,
    ) -> SourceEventModel:
        source_event = SourceEventModel(
            brand_id=1,
            person_id=user.person_id,
            user_id=user.id,
            event_type=event_type,
            source_channel=MINIAPP_EVENT_CHANNEL,
            source_id=str(event.id),
            store_id=event.store_id,
            payload=payload,
            occurred_at=datetime.now(),
        )
        db.add(source_event)
        await db.flush()
        return source_event

    @classmethod
    async def _write_lifecycle(cls, db: AsyncSession, lead: CrmLeadProfileModel, event: SourceEventModel, remark: str) -> None:
        db.add(
            CrmLeadLifecycleModel(
                brand_id=lead.brand_id,
                lead_id=lead.id,
                person_id=lead.person_id,
                operation_type="source_event",
                change_detail={"source_event_id": event.id, "source_channel_code": MINIAPP_EVENT_CHANNEL},
                remark=remark,
            )
        )

    @classmethod
    async def _upsert_lead(cls, db: AsyncSession, person_id: int, source_event: SourceEventModel) -> CrmLeadProfileModel:
        result = await db.execute(
            select(CrmLeadProfileModel).where(
                CrmLeadProfileModel.person_id == person_id,
                CrmLeadProfileModel.is_deleted == False,
                CrmLeadProfileModel.lead_type.notin_(["invalid", "converted_customer"]),
            )
        )
        lead = result.scalars().first()
        if lead:
            lead.source_channel_code = MINIAPP_EVENT_CHANNEL
            lead.latest_source_event_id = source_event.id
            await cls._write_lifecycle(db, lead, source_event, "小程序活动事件更新线索来源")
            return lead
        lead = CrmLeadProfileModel(
            brand_id=1,
            person_id=person_id,
            store_id=None,
            owner_sales_id=None,
            pool_type="hq_pool",
            lead_type="pending",
            source_channel_code=MINIAPP_EVENT_CHANNEL,
            latest_source_event_id=source_event.id,
        )
        db.add(lead)
        await db.flush()
        await cls._write_lifecycle(db, lead, source_event, "小程序活动事件创建线索")
        return lead

    @classmethod
    async def _mark_registration_success(
        cls,
        db: AsyncSession,
        registration: EventRegistrationModel,
        event: EventModel,
        user: MiniProgramUserModel,
        paid_amount: Decimal,
        payload: dict | None = None,
    ) -> None:
        if registration.registration_status in cls.ACTIVE_REGISTRATION_STATUSES:
            return
        registration.registration_status = "registered"
        registration.paid_amount = paid_amount
        source_event = await cls._append_source_event(db, event_type="event_register", event=event, user=user, payload=payload)
        registration.source_event_id = source_event.id
        await cls._upsert_lead(db, user.person_id, source_event)
        await db.flush()

    @classmethod
    async def register_service(
        cls,
        db: AsyncSession,
        request: Request,
        event_id: int,
        user_id: int,
        data: MpEventRegisterSchema,
    ) -> dict:
        event = await cls._get_published_event(db, event_id)
        user = await cls._get_mp_user(db, user_id)
        await cls._validate_register(db, event, user)
        result = await db.execute(
            select(EventRegistrationModel)
            .where(
                EventRegistrationModel.event_id == event_id,
                EventRegistrationModel.mp_user_id == user_id,
                EventRegistrationModel.is_deleted == False,
            )
            .options(selectinload(EventRegistrationModel.order))
        )
        registration = result.scalars().first()
        if registration and registration.registration_status in cls.ACTIVE_REGISTRATION_STATUSES:
            raise CustomException(msg="您已报名该活动")
        if registration and registration.registration_status == "pending_payment" and cls._order_can_continue(registration):
            payment = await PaymentService.create_cloudpay_mp_payment(
                db,
                order=registration.order,
                buyer_id=user.openid,
                notify_url=cls._notify_url(request),
            )
            return {"registration": cls._registration_out(registration), "payment": payment}
        if registration and registration.registration_status == "pending_payment":
            if registration.order:
                await PaymentService.close_order(db, registration.order)
            registration.registration_status = "timeout"
            await db.flush()

        amount = cls._fee_for_person(event, user.person)
        await cls._validate_paid_event_store(db, event, amount)
        if registration:
            registration.registration_status = "pending_payment" if amount > 0 else "registered"
            registration.payable_amount = amount
            registration.paid_amount = Decimal("0.00")
            registration.order_id = None
            registration.payment_expire_at = None
        else:
            registration = EventRegistrationModel(
                brand_id=1,
                event_id=event.id,
                mp_user_id=user.id,
                person_id=user.person_id,
                registration_no=cls._registration_no("R"),
                gender_snapshot=user.person.gender,
                payable_amount=amount,
                paid_amount=Decimal("0.00"),
                registration_status="pending_payment" if amount > 0 else "registered",
                registered_at=datetime.now(),
            )
            db.add(registration)
            await db.flush()

        if amount <= 0:
            await cls._mark_registration_success(db, registration, event, user, Decimal("0.00"), data.payload)
            return {"registration": cls._registration_out(registration), "payment": None}

        payment = await cls._create_registration_order(db, request, event, user, registration, amount)
        await db.flush()
        return {"registration": cls._registration_out(registration), "payment": payment}

    @staticmethod
    def _notify_url(request: Request) -> str:
        try:
            return str(request.url_for("cloudpay_notify_controller"))
        except Exception:
            root_path = request.scope.get("root_path", "")
            return f"{str(request.base_url).rstrip('/')}{root_path}/cloudpay/notify/trade"

    @classmethod
    async def continue_pay_service(cls, db: AsyncSession, request: Request, registration_id: int, user_id: int) -> dict:
        user = await cls._get_mp_user(db, user_id)
        result = await db.execute(
            select(EventRegistrationModel)
            .where(
                EventRegistrationModel.id == registration_id,
                EventRegistrationModel.mp_user_id == user_id,
                EventRegistrationModel.is_deleted == False,
            )
            .options(selectinload(EventRegistrationModel.order))
        )
        registration = result.scalars().first()
        if not registration:
            raise CustomException(msg="待支付报名不存在")
        if registration.registration_status not in {"pending_payment", "timeout"}:
            raise CustomException(msg="当前报名状态不需要支付")
        event = await cls._get_published_event(db, registration.event_id)
        amount = registration.payable_amount
        await cls._validate_paid_event_store(db, event, amount)
        if cls._order_can_continue(registration):
            payment = await PaymentService.create_cloudpay_mp_payment(
                db,
                order=registration.order,
                buyer_id=user.openid,
                notify_url=cls._notify_url(request),
            )
        else:
            if registration.order:
                await PaymentService.close_order(db, registration.order)
            payment = await cls._create_registration_order(db, request, event, user, registration, amount)
        return {"registration": cls._registration_out(registration), "payment": payment}

    @classmethod
    async def on_payment_success(cls, db: AsyncSession, order: PaymentOrderModel) -> None:
        if order.biz_type != "event_registration":
            return
        result = await db.execute(
            select(EventRegistrationModel)
            .where(EventRegistrationModel.id == order.biz_id, EventRegistrationModel.is_deleted == False)
            .options(
                selectinload(EventRegistrationModel.event),
                selectinload(EventRegistrationModel.mp_user).selectinload(MiniProgramUserModel.person),
            )
        )
        registration = result.scalars().first()
        if not registration:
            return
        await cls._mark_registration_success(
            db,
            registration,
            registration.event,
            registration.mp_user,
            order.paid_amount,
            {"order_id": order.id, "order_no": order.order_no},
        )

    @classmethod
    async def checkin_service(cls, db: AsyncSession, event_id: int, user_id: int, data: MpEventCheckinSchema) -> dict:
        event = await cls._get_published_event(db, event_id)
        user = await cls._get_mp_user(db, user_id)
        result = await db.execute(
            select(EventParticipantModel).where(
                EventParticipantModel.event_id == event_id,
                EventParticipantModel.mp_user_id == user_id,
                EventParticipantModel.is_deleted == False,
            )
        )
        participant = result.scalars().first()
        if participant:
            return {"participant_id": participant.id, "onsite_no": participant.onsite_no, "participant_status": participant.participant_status}
        registration = None
        if data.registration_id:
            result = await db.execute(
                select(EventRegistrationModel).where(
                    EventRegistrationModel.id == data.registration_id,
                    EventRegistrationModel.event_id == event_id,
                    EventRegistrationModel.mp_user_id == user_id,
                    EventRegistrationModel.is_deleted == False,
                )
            )
            registration = result.scalars().first()
        if not registration:
            result = await db.execute(
                select(EventRegistrationModel).where(
                    EventRegistrationModel.event_id == event_id,
                    EventRegistrationModel.mp_user_id == user_id,
                    EventRegistrationModel.registration_status.in_(cls.ACTIVE_REGISTRATION_STATUSES),
                    EventRegistrationModel.is_deleted == False,
                )
            )
            registration = result.scalars().first()
        if registration and registration.registration_status == "pending_payment":
            raise CustomException(msg="报名未支付，不能签到")
        source_event = await cls._append_source_event(db, event_type="event_checkin", event=event, user=user, payload=data.payload)
        participant = EventParticipantModel(
            brand_id=1,
            event_id=event.id,
            registration_id=registration.id if registration else None,
            mp_user_id=user.id,
            person_id=user.person_id,
            onsite_no=cls._registration_no("C"),
            display_nickname=user.nickname,
            gender_snapshot=user.person.gender,
            profile_snapshot={
                "name": user.person.name,
                "mobile": user.mobile,
                "height_cm": user.person.height_cm,
                "occupation": user.person.occupation,
                "photo_urls": user.person.photo_urls or [],
            },
            checkin_type="registered" if registration else "walk_in",
            checked_in_at=datetime.now(),
            participant_status="checked_in",
            source_event_id=source_event.id,
        )
        db.add(participant)
        if registration:
            registration.registration_status = "checked_in"
        await cls._upsert_lead(db, user.person_id, source_event)
        await db.flush()
        return {"participant_id": participant.id, "onsite_no": participant.onsite_no, "participant_status": participant.participant_status}
