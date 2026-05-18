from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import CustomException
from app.plugin.module_certification.model import CertificationApplicationModel
from app.plugin.module_certification.service import CertificationService
from app.plugin.module_crm.lead.model import CrmPersonModel
from app.plugin.module_event.model import EventModel, EventRegistrationModel
from app.plugin.module_mp.auth.model import MiniProgramUserModel
from app.plugin.module_mp.plaza.model import (
    MpContactUnlockModel,
    MpUnlockCouponModel,
    MpUserFavoriteModel,
    MpUserLikeModel,
)
from app.plugin.module_mp.plaza.service import MpPlazaService
from app.plugin.module_subscription.service import SubscriptionService

from .schema import MpMinePrivacyUpdateSchema, MpMineProfileUpdateSchema

PROFILE_COMPLETION_FIELDS = [
    ("name", "姓名"),
    ("gender", "性别"),
    ("wechat", "微信号"),
    ("birth_date", "生日"),
    ("height_cm", "身高"),
    ("ethnicity", "民族"),
    ("occupation", "职业"),
    ("annual_income", "收入"),
    ("marital_status", "婚况"),
    ("education", "学历"),
    ("hometown", "籍贯"),
    ("residence", "常驻地"),
    ("house_status", "房产"),
    ("car_status", "车辆"),
    ("photo_urls", "照片"),
    ("profile_intro", "自我介绍"),
]


class MpMineService:
    """小程序我的中心服务。"""

    @classmethod
    async def _current_user(cls, db: AsyncSession, user_id: int) -> MiniProgramUserModel:
        result = await db.execute(
            select(MiniProgramUserModel)
            .where(MiniProgramUserModel.id == user_id, MiniProgramUserModel.is_deleted == False)
            .options(selectinload(MiniProgramUserModel.person))
        )
        user = result.scalars().first()
        if not user:
            raise CustomException(msg="请先登录小程序", code=10401, status_code=401)
        return user

    @classmethod
    async def _registered_user(cls, db: AsyncSession, user_id: int) -> MiniProgramUserModel:
        user = await cls._current_user(db, user_id)
        if not user.person_id or not user.person:
            raise CustomException(msg="请先完成注册资料", code=10402, status_code=401)
        return user

    @staticmethod
    def _filled(value: Any, field: str) -> bool:
        if field == "gender":
            return value in {"0", "1"}
        if isinstance(value, list):
            return bool([item for item in value if item])
        return value not in (None, "")

    @classmethod
    def profile_completion(cls, person: CrmPersonModel | None) -> dict[str, Any]:
        if not person:
            return {
                "percent": 0,
                "filled_count": 0,
                "total_count": len(PROFILE_COMPLETION_FIELDS),
                "missing_fields": [label for _field, label in PROFILE_COMPLETION_FIELDS],
            }
        missing = []
        for field, label in PROFILE_COMPLETION_FIELDS:
            if not cls._filled(getattr(person, field, None), field):
                missing.append(label)
        total = len(PROFILE_COMPLETION_FIELDS)
        filled_count = total - len(missing)
        percent = round(filled_count / total * 100) if total else 0
        return {
            "percent": percent,
            "filled_count": filled_count,
            "total_count": total,
            "missing_fields": missing,
        }

    @classmethod
    def _profile_out(cls, user: MiniProgramUserModel, person: CrmPersonModel) -> dict[str, Any]:
        photos = person.photo_urls or []
        return {
            "user": {
                "id": user.id,
                "nickname": user.nickname,
                "avatar_url": user.avatar_url or (photos[0] if photos else None),
                "mobile": user.mobile,
                "is_invisible": user.is_invisible,
            },
            "person": {
                "id": person.id,
                "display_no": person.display_no,
                "name": person.name,
                "gender": person.gender,
                "primary_mobile": person.primary_mobile,
                "wechat": person.wechat,
                "birth_date": person.birth_date,
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
                "photo_urls": photos,
                "profile_intro": person.profile_intro,
                **CertificationService.certification_level_out(person),
                "certification_summary": person.certification_summary,
            },
            "profile_completion": cls.profile_completion(person),
        }

    @classmethod
    async def _relation_counts(cls, db: AsyncSession, user_id: int) -> dict[str, int]:
        received = (
            await db.execute(
                select(func.count(MpUserLikeModel.id))
                .join(MiniProgramUserModel, MpUserLikeModel.viewer_user_id == MiniProgramUserModel.id)
                .where(
                    MpUserLikeModel.target_user_id == user_id,
                    MpUserLikeModel.is_active == True,
                    MpUserLikeModel.is_deleted == False,
                    MiniProgramUserModel.is_invisible == False,
                    MiniProgramUserModel.is_deleted == False,
                )
            )
        ).scalar() or 0
        sent = (
            await db.execute(
                select(func.count(MpUserLikeModel.id))
                .join(MiniProgramUserModel, MpUserLikeModel.target_user_id == MiniProgramUserModel.id)
                .where(
                    MpUserLikeModel.viewer_user_id == user_id,
                    MpUserLikeModel.is_active == True,
                    MpUserLikeModel.is_deleted == False,
                    MiniProgramUserModel.is_invisible == False,
                    MiniProgramUserModel.is_deleted == False,
                )
            )
        ).scalar() or 0
        favorites = (
            await db.execute(
                select(func.count(MpUserFavoriteModel.id))
                .join(MiniProgramUserModel, MpUserFavoriteModel.target_user_id == MiniProgramUserModel.id)
                .where(
                    MpUserFavoriteModel.viewer_user_id == user_id,
                    MpUserFavoriteModel.is_active == True,
                    MpUserFavoriteModel.is_deleted == False,
                    MiniProgramUserModel.is_invisible == False,
                    MiniProgramUserModel.is_deleted == False,
                )
            )
        ).scalar() or 0
        unlocks = (
            await db.execute(
                select(func.count(MpContactUnlockModel.id))
                .join(MiniProgramUserModel, MpContactUnlockModel.target_user_id == MiniProgramUserModel.id)
                .where(
                    MpContactUnlockModel.viewer_user_id == user_id,
                    MpContactUnlockModel.unlock_status == "success",
                    MpContactUnlockModel.is_deleted == False,
                    MiniProgramUserModel.is_invisible == False,
                    MiniProgramUserModel.is_deleted == False,
                )
            )
        ).scalar() or 0
        return {"likes_received": received, "likes_sent": sent, "favorites": favorites, "unlocks": unlocks}

    @classmethod
    async def _coupon_count(cls, db: AsyncSession, user: MiniProgramUserModel) -> int:
        now = datetime.now()
        return (
            await db.execute(
                select(func.count(MpUnlockCouponModel.id)).where(
                    MpUnlockCouponModel.user_id == user.id,
                    MpUnlockCouponModel.coupon_status == "unused",
                    MpUnlockCouponModel.is_deleted == False,
                    or_(MpUnlockCouponModel.valid_to.is_(None), MpUnlockCouponModel.valid_to >= now),
                )
            )
        ).scalar() or 0

    @classmethod
    async def _event_summary(cls, db: AsyncSession, user_id: int) -> dict[str, int]:
        rows = (
            await db.execute(
                select(EventRegistrationModel.registration_status, func.count(EventRegistrationModel.id))
                .where(EventRegistrationModel.mp_user_id == user_id, EventRegistrationModel.is_deleted == False)
                .group_by(EventRegistrationModel.registration_status)
            )
        ).all()
        data = {"total": 0, "pending_payment": 0, "registered": 0, "checked_in": 0}
        for status, count in rows:
            data["total"] += count
            if status in data:
                data[status] = count
        return data

    @classmethod
    async def _certification_todo(cls, db: AsyncSession, user: MiniProgramUserModel) -> dict[str, Any] | None:
        if not user.person_id:
            return None
        application = (
            await db.execute(
                select(CertificationApplicationModel)
                .where(
                    CertificationApplicationModel.user_id == user.id,
                    CertificationApplicationModel.person_id == user.person_id,
                    CertificationApplicationModel.application_status.in_(["pending_payment", "paid_pending_submit", "in_progress", "rejected"]),
                    CertificationApplicationModel.is_deleted == False,
                )
                .order_by(CertificationApplicationModel.id.desc())
            )
        ).scalars().first()
        if application:
            return {
                "type": "certification",
                "title": "认证资料待完成",
                "desc": "继续补齐认证项目，提升真实可信度。",
                "status": application.application_status,
                "url": "/pages/certification/index",
            }
        if user.person and user.person.certification_level == "none":
            return {
                "type": "certification",
                "title": "还未完成认证",
                "desc": "认证后会展示真实等级，并可获得联系方式解锁券。",
                "status": "none",
                "url": "/pages/certification/index",
            }
        return None

    @classmethod
    async def center(cls, db: AsyncSession, user_id: int) -> dict[str, Any]:
        user = await cls._current_user(db, user_id)
        person = user.person if user.person_id else None
        if not person:
            return {"is_registered": False, "user": {"id": user.id, "nickname": user.nickname, "avatar_url": user.avatar_url}, "todos": [{"type": "register", "title": "先完成注册资料", "desc": "补齐真实资料后，才能使用喜欢、认证、活动和订阅。", "url": "/pages/register/index"}]}

        completion = cls.profile_completion(person)
        todos: list[dict[str, Any]] = []
        if completion["percent"] < 100:
            todos.append({"type": "profile", "title": f"资料完整度 {completion['percent']}%", "desc": f"还缺：{'、'.join(completion['missing_fields'][:3])}", "url": "/pages/mine/profile"})
        cert_todo = await cls._certification_todo(db, user)
        if cert_todo:
            todos.append(cert_todo)
        events = await cls._event_summary(db, user.id)
        if events["pending_payment"]:
            todos.append({"type": "event_pay", "title": "有活动待支付", "desc": f"{events['pending_payment']} 个活动报名还未支付", "url": "/pages/mine/events"})
        subscription = await SubscriptionService.mp_me(db, user.id)
        if not subscription.get("has_active_subscription"):
            todos.append({"type": "subscription", "title": "订阅推荐未开启", "desc": "开启订阅后，可按择偶要求获得推荐。", "url": "/pages/subscription/index"})
        return {
            "is_registered": True,
            **cls._profile_out(user, person),
            "stats": {**await cls._relation_counts(db, user.id), "coupon_count": await cls._coupon_count(db, user), "events": events["total"]},
            "event_summary": events,
            "subscription": subscription,
            "todos": todos[:5],
        }

    @classmethod
    async def profile(cls, db: AsyncSession, user_id: int) -> dict[str, Any]:
        user = await cls._registered_user(db, user_id)
        return cls._profile_out(user, user.person)

    @classmethod
    async def update_profile(cls, db: AsyncSession, user_id: int, data: MpMineProfileUpdateSchema) -> dict[str, Any]:
        user = await cls._registered_user(db, user_id)
        person = user.person
        payload = data.model_dump()
        for key, value in payload.items():
            setattr(person, key, value)
        user.avatar_url = payload["photo_urls"][0] if payload["photo_urls"] else user.avatar_url
        user.nickname = user.nickname or person.name
        await db.flush()
        return cls._profile_out(user, person)

    @classmethod
    async def update_privacy(cls, db: AsyncSession, user_id: int, data: MpMinePrivacyUpdateSchema) -> dict[str, Any]:
        user = await cls._registered_user(db, user_id)
        user.is_invisible = data.is_invisible
        if data.is_invisible:
            user.allow_user_wall = False
        await db.flush()
        return {"is_invisible": user.is_invisible}

    @classmethod
    async def _cards_by_user_ids(cls, db: AsyncSession, ids: list[int]) -> dict[int, dict[str, Any]]:
        if not ids:
            return {}
        rows = (
            await db.execute(
                select(MiniProgramUserModel, CrmPersonModel)
                .join(CrmPersonModel, MiniProgramUserModel.person_id == CrmPersonModel.id)
                .where(
                    MiniProgramUserModel.id.in_(ids),
                    MiniProgramUserModel.is_invisible == False,
                    MiniProgramUserModel.is_deleted == False,
                    CrmPersonModel.is_deleted == False,
                )
            )
        ).all()
        labels = await MpPlazaService._dict_labels(db)
        return {user.id: MpPlazaService._item_out(user, person, labels) for user, person in rows}

    @classmethod
    async def likes(cls, db: AsyncSession, user_id: int, like_type: str, page_no: int, page_size: int) -> dict[str, Any]:
        user = await cls._registered_user(db, user_id)
        if like_type not in {"received", "sent"}:
            raise CustomException(msg="喜欢类型不正确")
        if like_type == "received":
            where = [MpUserLikeModel.target_user_id == user.id]
            order_col = MpUserLikeModel.liked_at
        else:
            where = [MpUserLikeModel.viewer_user_id == user.id]
            order_col = MpUserLikeModel.liked_at
        where.extend([MpUserLikeModel.is_active == True, MpUserLikeModel.is_deleted == False])
        total = (await db.execute(select(func.count(MpUserLikeModel.id)).where(*where))).scalar() or 0
        rows = (
            await db.execute(
                select(MpUserLikeModel).where(*where).order_by(order_col.desc().nullslast(), MpUserLikeModel.id.desc()).offset((page_no - 1) * page_size).limit(page_size)
            )
        ).scalars().all()
        target_ids = [row.viewer_user_id if like_type == "received" else row.target_user_id for row in rows]
        cards = await cls._cards_by_user_ids(db, target_ids)
        return {"page_no": page_no, "page_size": page_size, "total": total, "has_next": page_no * page_size < total, "items": [{**cards[target_id], "related_at": row.liked_at} for row, target_id in zip(rows, target_ids, strict=False) if target_id in cards]}

    @classmethod
    async def favorites(cls, db: AsyncSession, user_id: int, page_no: int, page_size: int) -> dict[str, Any]:
        user = await cls._registered_user(db, user_id)
        where = [MpUserFavoriteModel.viewer_user_id == user.id, MpUserFavoriteModel.is_active == True, MpUserFavoriteModel.is_deleted == False]
        total = (await db.execute(select(func.count(MpUserFavoriteModel.id)).where(*where))).scalar() or 0
        rows = (
            await db.execute(
                select(MpUserFavoriteModel).where(*where).order_by(MpUserFavoriteModel.favorited_at.desc().nullslast(), MpUserFavoriteModel.id.desc()).offset((page_no - 1) * page_size).limit(page_size)
            )
        ).scalars().all()
        target_ids = [row.target_user_id for row in rows]
        cards = await cls._cards_by_user_ids(db, target_ids)
        return {"page_no": page_no, "page_size": page_size, "total": total, "has_next": page_no * page_size < total, "items": [{**cards[target_id], "related_at": row.favorited_at} for row, target_id in zip(rows, target_ids, strict=False) if target_id in cards]}

    @classmethod
    async def unlocks(cls, db: AsyncSession, user_id: int, page_no: int, page_size: int) -> dict[str, Any]:
        user = await cls._registered_user(db, user_id)
        where = [MpContactUnlockModel.viewer_user_id == user.id, MpContactUnlockModel.unlock_status == "success", MpContactUnlockModel.is_deleted == False]
        total = (await db.execute(select(func.count(MpContactUnlockModel.id)).where(*where))).scalar() or 0
        rows = (
            await db.execute(
                select(MpContactUnlockModel).where(*where).order_by(MpContactUnlockModel.unlocked_at.desc().nullslast(), MpContactUnlockModel.id.desc()).offset((page_no - 1) * page_size).limit(page_size)
            )
        ).scalars().all()
        target_ids = [row.target_user_id for row in rows]
        cards = await cls._cards_by_user_ids(db, target_ids)
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": [
                {**cards[target_id], "unlock_id": row.id, "unlock_source": row.unlock_source, "unlock_method": row.unlock_method, "unlocked_at": row.unlocked_at}
                for row, target_id in zip(rows, target_ids, strict=False)
                if target_id in cards
            ],
        }

    @classmethod
    async def events(cls, db: AsyncSession, user_id: int, page_no: int, page_size: int) -> dict[str, Any]:
        user = await cls._registered_user(db, user_id)
        total = (
            await db.execute(select(func.count(EventRegistrationModel.id)).where(EventRegistrationModel.mp_user_id == user.id, EventRegistrationModel.is_deleted == False))
        ).scalar() or 0
        rows = (
            await db.execute(
                select(EventRegistrationModel)
                .where(EventRegistrationModel.mp_user_id == user.id, EventRegistrationModel.is_deleted == False)
                .options(selectinload(EventRegistrationModel.event).selectinload(EventModel.store), selectinload(EventRegistrationModel.order))
                .order_by(EventRegistrationModel.registered_at.desc(), EventRegistrationModel.id.desc())
                .offset((page_no - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        items = []
        for row in rows:
            event = row.event
            items.append(
                {
                    "registration": {
                        "id": row.id,
                        "registration_no": row.registration_no,
                        "registration_status": row.registration_status,
                        "payable_amount": row.payable_amount,
                        "paid_amount": row.paid_amount,
                        "order_id": row.order_id,
                        "payment_expire_at": row.payment_expire_at,
                        "registered_at": row.registered_at,
                    },
                    "event": {
                        "id": event.id,
                        "title": event.title,
                        "subtitle": event.subtitle,
                        "cover_url": event.cover_url,
                        "location": event.location,
                        "store_name": event.store.name if event.store else None,
                        "start_time": event.start_time,
                        "end_time": event.end_time,
                        "event_status": event.event_status,
                    },
                }
            )
        return {"page_no": page_no, "page_size": page_size, "total": total, "has_next": page_no * page_size < total, "items": items}
