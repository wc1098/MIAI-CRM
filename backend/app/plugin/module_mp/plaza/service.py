import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import Request
from sqlalchemy import and_, func, literal, or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.dict.model import DictDataModel
from app.api.v1.module_system.params.model import ParamsModel
from app.core.exceptions import CustomException
from app.plugin.module_certification.service import CertificationService
from app.plugin.module_crm.lead.model import (
    CrmLeadLifecycleModel,
    CrmLeadProfileModel,
    CrmPersonModel,
)
from app.plugin.module_mp.auth.model import MiniProgramUserModel, SourceEventModel
from app.plugin.module_payment.core.model import PaymentOrderModel
from app.plugin.module_payment.core.service import PaymentService
from app.plugin.module_profile_ai.model import PersonAiProfileModel

from .model import (
    MpContactUnlockModel,
    MpContactViewLogModel,
    MpHeartbeatProgressModel,
    MpUnlockCouponModel,
    MpUnlockQuestionAnswerModel,
    MpUnlockQuestionModel,
    MpUnlockTaskModel,
    MpUnlockTaskRecordModel,
    MpUserFavoriteModel,
    MpUserLikeModel,
    MpUserProfileActionModel,
)

MINIAPP_CONTACT_UNLOCK_CHANNEL = "MINIAPP_CONTACT_UNLOCK"
CONTACT_UNLOCK_BIZ_TYPE = "contact_unlock"
UNLOCK_QUESTION_PICK_COUNT = 3


DEFAULT_SETTINGS = {
    "miniprogram.plaza.show_pending_users": "false",
    "miniprogram.unlock.contact_price": "19.90",
    "miniprogram.unlock.allow_coupon": "true",
    "miniprogram.unlock.allow_paid_boost": "true",
    "miniprogram.unlock.allow_task_free": "true",
    "miniprogram.unlock.daily_limit": "5",
    "miniprogram.unlock.default_store_id": "",
    "miniprogram.heartbeat.initial_min": "35",
    "miniprogram.heartbeat.initial_max": "55",
    "miniprogram.heartbeat.view_score": "1",
    "miniprogram.heartbeat.like_score": "8",
    "miniprogram.heartbeat.favorite_score": "5",
    "miniprogram.heartbeat.profile_score": "0",
    "miniprogram.heartbeat.unlock_score": "100",
    "miniprogram.coupon.enabled": "true",
    "miniprogram.coupon.name": "联系方式解锁券",
    "miniprogram.coupon.valid_days": "7",
    "miniprogram.coupon.cycle_days": "2",
    "miniprogram.coupon.hold_limit": "1",
    "miniprogram.coupon.description": "可免费解锁一次心仪用户手机号",
    "miniprogram.copy.progress": "完成互动任务提升心动值，达到目标后即可查看手机号。",
    "miniprogram.copy.final": "解锁后可查看对方手机号，本次解锁后可重复查看，不重复收费。",
    "miniprogram.copy.pay": "付费补足会直接加满当前心动值并解锁手机号。",
    "miniprogram.copy.contact": "请真诚沟通，尊重对方意愿；若对方明确拒绝，请停止打扰。",
    "miniprogram.copy.risk": "今日解锁次数已用完，请明天再试。",
}

CRM_DICT_MAP = {
    "annual_income": "crm_annual_income",
    "education": "crm_education",
    "marital_status": "crm_marital_status",
    "house_status": "crm_house_status",
    "car_status": "crm_car_status",
    "ethnicity": "crm_ethnicity",
}

DEFAULT_UNLOCK_TASKS = [
    {"task_code": "view_profile", "task_name": "查看完整资料", "task_type": "view", "task_group": "quick", "score": 5, "is_global": False, "is_target": True, "daily_limit": 1, "sort": 10},
    {"task_code": "like_profile", "task_name": "喜欢TA", "task_type": "like", "task_group": "quick", "score": 5, "is_global": False, "is_target": True, "daily_limit": 1, "sort": 20},
    {"task_code": "favorite_profile", "task_name": "收藏TA", "task_type": "favorite", "task_group": "quick", "score": 5, "is_global": False, "is_target": True, "daily_limit": 1, "sort": 30},
    {"task_code": "share_card", "task_name": "转发这张名片", "task_type": "share", "task_group": "quick", "score": 10, "is_global": False, "is_target": True, "daily_limit": 3, "sort": 40},
    {"task_code": "daily_login", "task_name": "每日登录", "task_type": "daily_login", "task_group": "daily", "score": 3, "is_global": True, "is_target": False, "daily_limit": 1, "sort": 100},
]

DIRECT_TASK_TYPES = {"view", "daily_login"}
DETAIL_ACTION_TASK_TYPES = {"view"}
DISABLED_LEGACY_TASK_CODES = {"read_ai_profile", "daily_browse"}

DEFAULT_UNLOCK_QUESTIONS = [
    {
        "question": "TA周末更可能喜欢哪种相处方式？",
        "options": [{"label": "安静散步聊天", "value": "walk"}, {"label": "热闹朋友聚会", "value": "party"}, {"label": "一起学习充电", "value": "study"}],
        "recommended_answer": "walk",
        "match_tags": ["生活方式", "陪伴感"],
        "correct_score": 10,
        "wrong_score": 3,
        "category": "dating",
        "sort": 10,
    },
    {
        "question": "如果开始一段关系，TA可能更看重什么？",
        "options": [{"label": "稳定可靠", "value": "stable"}, {"label": "浪漫惊喜", "value": "romantic"}, {"label": "共同成长", "value": "growth"}],
        "recommended_answer": "stable",
        "match_tags": ["关系观", "安全感"],
        "correct_score": 10,
        "wrong_score": 3,
        "category": "relationship",
        "sort": 20,
    },
]


class MpPlazaService:
    """小程序广场用户列表服务。"""

    @classmethod
    def _age(cls, birth_date: date | None) -> int | None:
        if not birth_date:
            return None
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    @classmethod
    def _age_cutoff(cls, age: int) -> date:
        today = date.today()
        try:
            return today.replace(year=today.year - age)
        except ValueError:
            return today.replace(year=today.year - age, day=28)

    @classmethod
    def _masked_name(cls, name: str | None, gender: str | None) -> str:
        prefix = (name or "觅")[:1]
        suffix = {"0": "先生", "1": "女士"}.get(gender or "", "")
        return f"{prefix}{suffix}" if suffix else f"{prefix}**"

    @classmethod
    def _split_values(cls, value: str | None) -> list[str]:
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

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
    def _bool(cls, value: str | None, default: bool = False) -> bool:
        if value is None:
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "on", "是", "启用"}

    @classmethod
    def _int(cls, value: str | None, default: int = 0) -> int:
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return default

    @classmethod
    def _decimal(cls, value: str | None, default: str = "0") -> Decimal:
        try:
            return Decimal(str(value))
        except Exception:
            return Decimal(default)

    @staticmethod
    def _today_key() -> str:
        return date.today().isoformat()

    @staticmethod
    def _seconds_until_tomorrow() -> int:
        tomorrow = datetime.combine(date.today() + timedelta(days=1), datetime.min.time())
        return max(60, int((tomorrow - datetime.now()).total_seconds()))

    @staticmethod
    def _question_lock_key(viewer_id: int, target_id: int) -> str:
        return f"mp:unlock:questions:{date.today().isoformat()}:{viewer_id}:{target_id}"

    @classmethod
    async def _settings(cls, db: AsyncSession) -> dict[str, Any]:
        keys = list(DEFAULT_SETTINGS.keys())
        rows = await db.execute(
            select(ParamsModel.config_key, ParamsModel.config_value).where(
                ParamsModel.config_key.in_(keys),
                ParamsModel.status == "0",
                ParamsModel.is_deleted == False,
            )
        )
        raw = dict(rows.all())
        for key, value in DEFAULT_SETTINGS.items():
            raw.setdefault(key, value)
        return {
            "target_score": cls._int(raw["miniprogram.heartbeat.unlock_score"], 100),
            "initial_min": cls._int(raw["miniprogram.heartbeat.initial_min"], 35),
            "initial_max": cls._int(raw["miniprogram.heartbeat.initial_max"], 55),
            "daily_limit": cls._int(raw["miniprogram.unlock.daily_limit"], 5),
            "allow_coupon": cls._bool(raw["miniprogram.unlock.allow_coupon"], True),
            "allow_paid_boost": cls._bool(raw["miniprogram.unlock.allow_paid_boost"], True),
            "allow_task_free": cls._bool(raw["miniprogram.unlock.allow_task_free"], True),
            "contact_price": cls._decimal(raw["miniprogram.unlock.contact_price"], "19.90"),
            "coupon_enabled": cls._bool(raw["miniprogram.coupon.enabled"], True),
            "coupon_name": raw["miniprogram.coupon.name"],
            "coupon_valid_days": cls._int(raw["miniprogram.coupon.valid_days"], 7),
            "coupon_cycle_days": cls._int(raw["miniprogram.coupon.cycle_days"], 2),
            "coupon_hold_limit": cls._int(raw["miniprogram.coupon.hold_limit"], 1),
            "copy": {
                "progress": raw["miniprogram.copy.progress"],
                "final": raw["miniprogram.copy.final"],
                "pay": raw["miniprogram.copy.pay"],
                "contact": raw["miniprogram.copy.contact"],
                "risk": raw["miniprogram.copy.risk"],
            },
        }

    @classmethod
    async def _ensure_default_tasks(cls, db: AsyncSession) -> None:
        legacy_rows = (
            await db.execute(
                select(MpUnlockTaskModel).where(
                    MpUnlockTaskModel.task_code.in_(DISABLED_LEGACY_TASK_CODES),
                    MpUnlockTaskModel.is_deleted == False,
                )
            )
        ).scalars().all()
        for legacy in legacy_rows:
            if legacy.status == "0":
                legacy.status = "1"
        existing_rows = (await db.execute(select(MpUnlockTaskModel).where(MpUnlockTaskModel.is_deleted == False))).scalars().all()
        existing_by_code = {task.task_code: task for task in existing_rows}
        for item in DEFAULT_UNLOCK_TASKS:
            existing = existing_by_code.get(item["task_code"])
            if existing:
                if item["task_code"] == "share_card" and existing.status != "0":
                    existing.status = "0"
                continue
            if item["task_code"] not in existing_by_code:
                db.add(MpUnlockTaskModel(brand_id=1, **item))
        await db.flush()

    @classmethod
    async def _ensure_default_questions(cls, db: AsyncSession) -> None:
        count = (await db.execute(select(func.count(MpUnlockQuestionModel.id)).where(MpUnlockQuestionModel.is_deleted == False))).scalar() or 0
        if count:
            return
        for item in DEFAULT_UNLOCK_QUESTIONS:
            db.add(MpUnlockQuestionModel(brand_id=1, **item))
        await db.flush()

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
        reverse_map = {value: key for key, value in CRM_DICT_MAP.items()}
        for row in rows:
            key = reverse_map.get(row.dict_type)
            if key:
                labels[key][row.dict_value] = row.dict_label
        return labels

    @classmethod
    def _dict_label(cls, labels: dict[str, dict[str, str]], key: str, value: str | None) -> str | None:
        if not value:
            return None
        return labels.get(key, {}).get(value, value)

    @classmethod
    def _with_label(cls, data: dict[str, Any], labels: dict[str, dict[str, str]], key: str) -> None:
        value = data.get(key)
        data[f"{key}_value"] = value
        data[key] = cls._dict_label(labels, key, value)

    @classmethod
    def _decorate_dict_fields(cls, data: dict[str, Any], labels: dict[str, dict[str, str]]) -> dict[str, Any]:
        for key in CRM_DICT_MAP:
            cls._with_label(data, labels, key)
        return data

    @classmethod
    def _item_out(
        cls,
        user: MiniProgramUserModel,
        person: CrmPersonModel,
        labels: dict[str, dict[str, str]],
    ) -> dict[str, Any]:
        photo_urls = person.photo_urls or []
        data = {
            "user_id": user.id,
            "person_id": person.id,
            "display_no": person.display_no,
            "nickname": user.nickname if user.nickname and user.nickname != person.name else cls._masked_name(person.name, person.gender),
            "avatar_url": user.avatar_url or (photo_urls[0] if photo_urls else None),
            "age": cls._age(person.birth_date),
            "gender": person.gender,
            "residence": person.residence,
            "height_cm": person.height_cm,
            "occupation": person.occupation,
            "annual_income": person.annual_income,
            "education": person.education,
            "marital_status": person.marital_status,
            "house_status": person.house_status,
            "car_status": person.car_status,
            "registered_at": user.registered_at,
        }
        data.update(CertificationService.certification_level_out(person))
        data["certification_status"] = data["certification_level_name"]
        return cls._decorate_dict_fields(data, labels)

    @classmethod
    async def _current_user(cls, db: AsyncSession, user_id: int | None) -> MiniProgramUserModel | None:
        if not user_id:
            return None
        result = await db.execute(
            select(MiniProgramUserModel)
            .where(MiniProgramUserModel.id == user_id, MiniProgramUserModel.is_deleted == False)
            .options(selectinload(MiniProgramUserModel.person))
        )
        return result.scalars().first()

    @classmethod
    async def _required_user(cls, db: AsyncSession, user_id: int) -> MiniProgramUserModel:
        user = await cls._current_user(db, user_id)
        if not user:
            raise CustomException(msg="请先登录小程序", code=10401, status_code=401)
        if not user.person_id or not user.person:
            raise CustomException(msg="请先完成注册资料", code=10401, status_code=401)
        return user

    @classmethod
    async def _target_by_display_no(cls, db: AsyncSession, display_no: str) -> tuple[MiniProgramUserModel, CrmPersonModel]:
        conditions: list[Any] = [
            CrmPersonModel.display_no == display_no,
            CrmPersonModel.is_deleted == False,
            MiniProgramUserModel.is_deleted == False,
            MiniProgramUserModel.person_id.is_not(None),
        ]
        show_pending_users = cls._bool(
            await cls._param(
                db,
                "miniprogram.plaza.show_pending_users",
                DEFAULT_SETTINGS["miniprogram.plaza.show_pending_users"],
            ),
            False,
        )
        if not show_pending_users:
            conditions.append(MiniProgramUserModel.registered_at.is_not(None))
        result = await db.execute(
            select(MiniProgramUserModel, CrmPersonModel)
            .join(CrmPersonModel, MiniProgramUserModel.person_id == CrmPersonModel.id)
            .where(*conditions)
            .options(selectinload(MiniProgramUserModel.person))
        )
        row = result.first()
        if not row:
            raise CustomException(msg="该用户不存在或暂不可见", code=10404, status_code=404)
        return row[0], row[1]

    @classmethod
    def _display_name(cls, user: MiniProgramUserModel, person: CrmPersonModel) -> str:
        if user.nickname and user.nickname != person.name:
            return user.nickname
        suffix = {"0": "先生", "1": "女士"}.get(person.gender or "", "")
        prefix = (person.name or "觅")[:1]
        return f"{prefix}{suffix}" if suffix else "觅AI用户"

    @classmethod
    async def _progress(
        cls,
        db: AsyncSession,
        viewer: MiniProgramUserModel,
        target: MiniProgramUserModel,
        *,
        create: bool = True,
    ) -> MpHeartbeatProgressModel | None:
        if not viewer.person_id or not target.person_id:
            return None
        result = await db.execute(
            select(MpHeartbeatProgressModel).where(
                MpHeartbeatProgressModel.viewer_user_id == viewer.id,
                MpHeartbeatProgressModel.target_user_id == target.id,
                MpHeartbeatProgressModel.is_deleted == False,
            )
        )
        progress = result.scalars().first()
        if progress or not create:
            return progress
        settings = await cls._settings(db)
        min_score = settings["initial_min"]
        max_score = settings["initial_max"]
        if max_score < min_score:
            max_score = min_score
        seed = (viewer.id * 31 + target.id * 17) % (max_score - min_score + 1)
        progress = MpHeartbeatProgressModel(
            brand_id=1,
            viewer_user_id=viewer.id,
            target_user_id=target.id,
            viewer_person_id=viewer.person_id,
            target_person_id=target.person_id,
            score=min_score + seed,
            target_score=settings["target_score"],
            progress_status="processing",
            last_action_at=datetime.now(),
        )
        db.add(progress)
        await db.flush()
        return progress

    @classmethod
    async def _add_score(
        cls,
        db: AsyncSession,
        viewer: MiniProgramUserModel,
        target: MiniProgramUserModel,
        key: str,
    ) -> MpHeartbeatProgressModel:
        progress = await cls._progress(db, viewer, target)
        if not progress:
            raise CustomException(msg="请先完成注册资料")
        inc = cls._int(await cls._param(db, key, DEFAULT_SETTINGS.get(key, "0")), 0)
        if inc > 0 and not progress.unlocked_by_score:
            progress.score = max(progress.score + inc, 0)
            if progress.score >= progress.target_score:
                progress.score = progress.target_score
                progress.free_unlock_eligible = True
                progress.progress_status = "ready"
            progress.last_action_at = datetime.now()
            await db.flush()
        return progress

    @classmethod
    async def _is_unlocked(cls, db: AsyncSession, viewer_id: int | None, target_id: int) -> bool:
        if not viewer_id:
            return False
        result = await db.execute(
            select(MpContactUnlockModel.id).where(
                MpContactUnlockModel.viewer_user_id == viewer_id,
                MpContactUnlockModel.target_user_id == target_id,
                MpContactUnlockModel.unlock_status == "success",
                MpContactUnlockModel.is_deleted == False,
            )
        )
        return result.scalar() is not None

    @classmethod
    async def _relation_state(cls, db: AsyncSession, viewer_id: int | None, target_id: int) -> dict[str, bool]:
        if not viewer_id:
            return {"liked": False, "favorited": False}
        relation_stmt = union_all(
            select(literal("liked").label("relation_type")).where(
                MpUserLikeModel.viewer_user_id == viewer_id,
                MpUserLikeModel.target_user_id == target_id,
                MpUserLikeModel.is_active == True,
                MpUserLikeModel.is_deleted == False,
            ),
            select(literal("favorited").label("relation_type")).where(
                MpUserFavoriteModel.viewer_user_id == viewer_id,
                MpUserFavoriteModel.target_user_id == target_id,
                MpUserFavoriteModel.is_active == True,
                MpUserFavoriteModel.is_deleted == False,
            ),
        )
        relation_types = {row[0] for row in (await db.execute(relation_stmt)).all()}
        return {"liked": "liked" in relation_types, "favorited": "favorited" in relation_types}

    @classmethod
    async def _coupon_count(cls, db: AsyncSession, user_id: int | None) -> int:
        if not user_id:
            return 0
        now = datetime.now()
        return (
            await db.execute(
                select(func.count(MpUnlockCouponModel.id)).where(
                    MpUnlockCouponModel.user_id == user_id,
                    MpUnlockCouponModel.coupon_status == "unused",
                    MpUnlockCouponModel.is_deleted == False,
                    or_(MpUnlockCouponModel.valid_to.is_(None), MpUnlockCouponModel.valid_to >= now),
                )
            )
        ).scalar() or 0

    @classmethod
    async def _daily_unlock_count(cls, db: AsyncSession, user_id: int) -> int:
        start = datetime.combine(date.today(), datetime.min.time())
        return (
            await db.execute(
                select(func.count(MpContactUnlockModel.id)).where(
                    MpContactUnlockModel.viewer_user_id == user_id,
                    MpContactUnlockModel.unlock_status == "success",
                    MpContactUnlockModel.unlocked_at >= start,
                    MpContactUnlockModel.is_deleted == False,
                )
            )
        ).scalar() or 0

    @classmethod
    async def _viewer_unlock_counts(cls, db: AsyncSession, user_id: int | None) -> dict[str, int]:
        if not user_id:
            return {"coupon_count": 0, "daily_unlock_count": 0}
        now = datetime.now()
        start = datetime.combine(date.today(), datetime.min.time())
        counts_stmt = union_all(
            select(literal("coupon_count").label("count_type"), func.count(MpUnlockCouponModel.id)).where(
                MpUnlockCouponModel.user_id == user_id,
                MpUnlockCouponModel.coupon_status == "unused",
                MpUnlockCouponModel.is_deleted == False,
                or_(MpUnlockCouponModel.valid_to.is_(None), MpUnlockCouponModel.valid_to >= now),
            ),
            select(literal("daily_unlock_count").label("count_type"), func.count(MpContactUnlockModel.id)).where(
                MpContactUnlockModel.viewer_user_id == user_id,
                MpContactUnlockModel.unlock_status == "success",
                MpContactUnlockModel.unlocked_at >= start,
                MpContactUnlockModel.is_deleted == False,
            ),
        )
        counts = {row[0]: row[1] for row in (await db.execute(counts_stmt)).all()}
        return {
            "coupon_count": counts.get("coupon_count", 0),
            "daily_unlock_count": counts.get("daily_unlock_count", 0),
        }

    @classmethod
    async def _assert_can_unlock_today(cls, db: AsyncSession, viewer_id: int) -> None:
        settings = await cls._settings(db)
        used = await cls._daily_unlock_count(db, viewer_id)
        if settings["daily_limit"] > 0 and used >= settings["daily_limit"]:
            raise CustomException(msg=settings["copy"]["risk"])

    @classmethod
    async def _available_coupon(cls, db: AsyncSession, user_id: int) -> MpUnlockCouponModel | None:
        now = datetime.now()
        result = await db.execute(
            select(MpUnlockCouponModel)
            .where(
                MpUnlockCouponModel.user_id == user_id,
                MpUnlockCouponModel.coupon_status == "unused",
                MpUnlockCouponModel.is_deleted == False,
                or_(MpUnlockCouponModel.valid_to.is_(None), MpUnlockCouponModel.valid_to >= now),
            )
            .order_by(MpUnlockCouponModel.valid_to.asc().nullslast(), MpUnlockCouponModel.id.asc())
        )
        return result.scalars().first()

    @classmethod
    async def _auto_grant_coupon_if_needed(cls, db: AsyncSession, user: MiniProgramUserModel, settings: dict[str, Any]) -> None:
        if not settings["coupon_enabled"] or not user.person_id:
            return
        unused = await cls._coupon_count(db, user.id)
        if unused >= settings["coupon_hold_limit"]:
            return
        today = date.today()
        days = [today - timedelta(days=i) for i in range(settings["coupon_cycle_days"])]
        for day in days:
            count = (
                await db.execute(
                    select(func.count(MpUnlockTaskRecordModel.id)).where(
                        MpUnlockTaskRecordModel.viewer_user_id == user.id,
                        MpUnlockTaskRecordModel.completed_on == day.isoformat(),
                        MpUnlockTaskRecordModel.source.in_(["daily", "task"]),
                        MpUnlockTaskRecordModel.is_deleted == False,
                    )
                )
            ).scalar() or 0
            if count <= 0:
                return
        now = datetime.now()
        db.add(
            MpUnlockCouponModel(
                brand_id=1,
                user_id=user.id,
                person_id=user.person_id,
                coupon_name=settings["coupon_name"],
                coupon_status="unused",
                valid_from=now,
                valid_to=now + timedelta(days=settings["coupon_valid_days"]),
                grant_source="auto_daily",
                grant_reason=f"连续{settings['coupon_cycle_days']}天完成每日任务自动发放",
            )
        )
        await db.flush()

    @classmethod
    async def _task_record_count(cls, db: AsyncSession, task_id: int, user_id: int, target_id: int | None = None) -> int:
        conditions = [
            MpUnlockTaskRecordModel.task_id == task_id,
            MpUnlockTaskRecordModel.viewer_user_id == user_id,
            MpUnlockTaskRecordModel.completed_on == cls._today_key(),
            MpUnlockTaskRecordModel.is_deleted == False,
        ]
        if target_id:
            conditions.append(MpUnlockTaskRecordModel.target_user_id == target_id)
        return (await db.execute(select(func.count(MpUnlockTaskRecordModel.id)).where(*conditions))).scalar() or 0

    @classmethod
    async def _task_record_counts(
        cls,
        db: AsyncSession,
        tasks: list[MpUnlockTaskModel],
        user_id: int,
        target_id: int,
    ) -> dict[int, int]:
        task_ids = [task.id for task in tasks]
        if not task_ids:
            return {}
        rows = (
            await db.execute(
                select(
                    MpUnlockTaskRecordModel.task_id,
                    MpUnlockTaskRecordModel.target_user_id,
                    func.count(MpUnlockTaskRecordModel.id),
                )
                .where(
                    MpUnlockTaskRecordModel.task_id.in_(task_ids),
                    MpUnlockTaskRecordModel.viewer_user_id == user_id,
                    MpUnlockTaskRecordModel.completed_on == cls._today_key(),
                    MpUnlockTaskRecordModel.is_deleted == False,
                )
                .group_by(MpUnlockTaskRecordModel.task_id, MpUnlockTaskRecordModel.target_user_id)
            )
        ).all()
        by_task_target = {(row[0], row[1]): row[2] for row in rows}
        by_task_total: dict[int, int] = {}
        for task_id, _, count in rows:
            by_task_total[task_id] = by_task_total.get(task_id, 0) + count
        return {
            task.id: by_task_target.get((task.id, target_id), 0) if task.is_target else by_task_total.get(task.id, 0)
            for task in tasks
        }

    @classmethod
    async def _complete_task(
        cls,
        db: AsyncSession,
        viewer: MiniProgramUserModel,
        target: MiniProgramUserModel | None,
        task: MpUnlockTaskModel,
        source: str = "task",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not viewer.person_id:
            return {"completed": False, "score": 0, "reason": "请先完成注册资料"}
        target_id = target.id if target and task.is_target else None
        if task.daily_limit > 0 and await cls._task_record_count(db, task.id, viewer.id, target_id) >= task.daily_limit:
            return {"completed": False, "score": 0, "reason": "今日该任务已达上限"}
        progress = None
        if task.is_target and target:
            progress = await cls._progress(db, viewer, target)
        db.add(
            MpUnlockTaskRecordModel(
                brand_id=1,
                task_id=task.id,
                task_code=task.task_code,
                viewer_user_id=viewer.id,
                target_user_id=target.id if target else None,
                viewer_person_id=viewer.person_id,
                target_person_id=target.person_id if target else None,
                score=task.score,
                source=source,
                completed_on=cls._today_key(),
                payload=payload,
                completed_at=datetime.now(),
            )
        )
        if progress and task.score > 0 and not progress.unlocked_by_score:
            progress.score = min(progress.target_score, progress.score + task.score)
            if progress.score >= progress.target_score:
                progress.free_unlock_eligible = True
                progress.progress_status = "ready"
            progress.last_action_at = datetime.now()
        await cls._record_action(db, f"task_{task.task_code}", target or viewer, viewer, {"score": task.score, **(payload or {})})
        await db.flush()
        settings = await cls._settings(db)
        await cls._auto_grant_coupon_if_needed(db, viewer, settings)
        return {"completed": True, "score": task.score}

    @classmethod
    async def _effective_ai_profile(cls, db: AsyncSession, person_id: int) -> dict | None:
        result = await db.execute(
            select(PersonAiProfileModel)
            .where(
                PersonAiProfileModel.person_id == person_id,
                PersonAiProfileModel.profile_type == "miai_impression",
                PersonAiProfileModel.is_effective == True,
                PersonAiProfileModel.is_deleted == False,
            )
            .order_by(PersonAiProfileModel.priority.desc(), PersonAiProfileModel.generated_at.desc(), PersonAiProfileModel.id.desc())
        )
        profile = result.scalars().first()
        if not profile:
            return None
        return {
            "content": profile.content,
            "source_type": profile.source_type,
            "generated_at": profile.generated_at,
        }

    @classmethod
    def _public_person_out(
        cls,
        user: MiniProgramUserModel,
        person: CrmPersonModel,
        unlocked: bool,
        labels: dict[str, dict[str, str]],
    ) -> dict[str, Any]:
        photos = person.photo_urls or []
        public_photos = [
            {"url": url, "blurred": False if unlocked or index == 0 else True}
            for index, url in enumerate(photos)
        ]
        data = {
            "user_id": user.id,
            "person_id": person.id,
            "display_no": person.display_no,
            "display_name": cls._display_name(user, person),
            "avatar_url": user.avatar_url or (photos[0] if photos else None),
            "photos": public_photos,
            "photo_count": len(photos),
            "age": cls._age(person.birth_date),
            "gender": person.gender,
            "residence": person.residence,
            "height_cm": person.height_cm,
            "occupation": person.occupation,
            "annual_income": person.annual_income,
            "education": person.education,
            "marital_status": person.marital_status,
            "house_status": person.house_status,
            "car_status": person.car_status,
            "hometown": person.hometown,
            "ethnicity": person.ethnicity,
        }
        data.update(CertificationService.certification_level_out(person))
        data["certification_status"] = data["certification_level_name"]
        if unlocked:
            data["mobile"] = person.primary_mobile
        return cls._decorate_dict_fields(data, labels)

    @classmethod
    async def _record_action(
        cls,
        db: AsyncSession,
        action_type: str,
        target: MiniProgramUserModel,
        viewer: MiniProgramUserModel | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if not target.person_id:
            return
        db.add(
            MpUserProfileActionModel(
                brand_id=1,
                viewer_user_id=viewer.id if viewer else None,
                viewer_person_id=viewer.person_id if viewer else None,
                target_user_id=target.id,
                target_person_id=target.person_id,
                action_type=action_type,
                payload=payload,
                occurred_at=datetime.now(),
            )
        )

    @classmethod
    async def detail_service(cls, db: AsyncSession, display_no: str, user_id: int | None = None) -> dict[str, Any]:
        target, person = await cls._target_by_display_no(db, display_no)
        await cls._ensure_default_tasks(db)
        labels = await cls._dict_labels(db)
        viewer = await cls._current_user(db, user_id)
        is_self = bool(viewer and viewer.id == target.id)
        if target.is_invisible and not is_self:
            await cls._record_action(db, "view_invisible", target, viewer, {"display_no": display_no})
            return {"visible": False, "message": "该用户暂不可见", "display_no": display_no}
        unlocked = is_self or await cls._is_unlocked(db, viewer.id if viewer else None, target.id)
        relation = await cls._relation_state(db, viewer.id if viewer else None, target.id)
        progress = None
        if viewer and viewer.person_id and not is_self:
            progress = await cls._progress(db, viewer, target)
            task_result = await db.execute(
                select(MpUnlockTaskModel).where(
                    MpUnlockTaskModel.task_code == "view_profile",
                    MpUnlockTaskModel.status == "0",
                    MpUnlockTaskModel.is_deleted == False,
                )
            )
            task = task_result.scalars().first()
            if task:
                await cls._complete_task(db, viewer, target, task, "task")
                progress = await cls._progress(db, viewer, target)
        settings = await cls._settings(db)
        unlock_score = settings["target_score"]
        price = settings["contact_price"]
        unlock_counts = await cls._viewer_unlock_counts(db, viewer.id if viewer else None)
        coupon_count = unlock_counts["coupon_count"]
        daily_used = unlock_counts["daily_unlock_count"]
        await cls._record_action(db, "view", target, viewer, {"display_no": display_no})
        return {
            "visible": True,
            "is_self": is_self,
            "is_registered_viewer": bool(viewer and viewer.person_id),
            "is_unlocked": unlocked,
            "person": cls._public_person_out(target, person, unlocked, labels),
            "ai_profile": await cls._effective_ai_profile(db, person.id),
            "interaction": {
                **relation,
                "heartbeat_score": progress.score if progress else 0,
                "heartbeat_unlock_score": unlock_score,
                "heartbeat_status": progress.progress_status if progress else "guest",
                "coupon_count": coupon_count,
                "contact_price": f"{price:.2f}",
                "allow_coupon": settings["allow_coupon"],
                "allow_paid_boost": settings["allow_paid_boost"],
                "allow_task_free": settings["allow_task_free"],
                "daily_unlock_limit": settings["daily_limit"],
                "daily_unlock_used": daily_used,
                "daily_unlock_remaining": max(settings["daily_limit"] - daily_used, 0) if settings["daily_limit"] > 0 else 999,
            },
        }

    @classmethod
    async def list_service(
        cls,
        db: AsyncSession,
        user_id: int | None = None,
        page_no: int = 1,
        page_size: int = 20,
        display_no: str | None = None,
        gender: str | None = None,
        age_min: int | None = None,
        age_max: int | None = None,
        height_min: int | None = None,
        height_max: int | None = None,
        residence: str | None = None,
        education: str | None = None,
        marital_status: str | None = None,
        annual_income: str | None = None,
        house_status: str | None = None,
        car_status: str | None = None,
    ) -> dict[str, Any]:
        current_user = await cls._current_user(db, user_id)
        current_person = current_user.person if current_user and current_user.person_id else None
        effective_gender = gender
        if not effective_gender and current_person and current_person.gender in {"0", "1"}:
            effective_gender = "1" if current_person.gender == "0" else "0"

        conditions: list[Any] = [
            MiniProgramUserModel.person_id.is_not(None),
            MiniProgramUserModel.is_invisible == False,
            MiniProgramUserModel.is_deleted == False,
            CrmPersonModel.is_deleted == False,
            CrmPersonModel.display_no.is_not(None),
        ]
        show_pending_users = cls._bool(
            await cls._param(
                db,
                "miniprogram.plaza.show_pending_users",
                DEFAULT_SETTINGS["miniprogram.plaza.show_pending_users"],
            ),
            False,
        )
        if not show_pending_users:
            conditions.append(MiniProgramUserModel.registered_at.is_not(None))
        if current_person:
            conditions.append(CrmPersonModel.id != current_person.id)
        if display_no:
            conditions.append(CrmPersonModel.display_no == display_no.strip())
        if effective_gender in {"0", "1"}:
            conditions.append(CrmPersonModel.gender == effective_gender)
        if age_min is not None:
            conditions.append(CrmPersonModel.birth_date <= cls._age_cutoff(age_min))
        if age_max is not None:
            conditions.append(CrmPersonModel.birth_date >= cls._age_cutoff(age_max + 1) + timedelta(days=1))
        if height_min is not None:
            conditions.append(CrmPersonModel.height_cm >= height_min)
        if height_max is not None:
            conditions.append(CrmPersonModel.height_cm <= height_max)
        if residence:
            conditions.append(CrmPersonModel.residence.like(f"%{residence.strip()}%"))
        education_values = cls._split_values(education)
        marital_status_values = cls._split_values(marital_status)
        annual_income_values = cls._split_values(annual_income)
        house_status_values = cls._split_values(house_status)
        car_status_values = cls._split_values(car_status)
        if education_values:
            conditions.append(CrmPersonModel.education.in_(education_values))
        if marital_status_values:
            conditions.append(CrmPersonModel.marital_status.in_(marital_status_values))
        if annual_income_values:
            conditions.append(CrmPersonModel.annual_income.in_(annual_income_values))
        if house_status_values:
            conditions.append(CrmPersonModel.house_status.in_(house_status_values))
        if car_status_values:
            conditions.append(CrmPersonModel.car_status.in_(car_status_values))

        total = (
            await db.execute(
                select(func.count(MiniProgramUserModel.id))
                .join(CrmPersonModel, MiniProgramUserModel.person_id == CrmPersonModel.id)
                .where(and_(*conditions))
            )
        ).scalar() or 0
        rows = (
            await db.execute(
                select(MiniProgramUserModel, CrmPersonModel)
                .join(CrmPersonModel, MiniProgramUserModel.person_id == CrmPersonModel.id)
                .where(and_(*conditions))
                .order_by(MiniProgramUserModel.registered_at.desc(), MiniProgramUserModel.id.desc())
                .offset((page_no - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        labels = await cls._dict_labels(db)
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": [cls._item_out(user, person, labels) for user, person in rows],
        }

    @classmethod
    def _target_summary(cls, target: MiniProgramUserModel, person: CrmPersonModel) -> dict[str, Any]:
        photos = person.photo_urls or []
        return {
            "user_id": target.id,
            "person_id": person.id,
            "display_no": person.display_no,
            "display_name": cls._display_name(target, person),
            "avatar_url": target.avatar_url or (photos[0] if photos else None),
            "age": cls._age(person.birth_date),
            "height_cm": person.height_cm,
            "residence": person.residence,
            "occupation": person.occupation,
        }

    @classmethod
    async def unlock_progress_service(cls, db: AsyncSession, display_no: str, user_id: int) -> dict[str, Any]:
        viewer = await cls._required_user(db, user_id)
        target, person = await cls._target_by_display_no(db, display_no)
        if viewer.id == target.id:
            raise CustomException(msg="查看自己的资料不需要解锁")
        if target.is_invisible:
            raise CustomException(msg="该用户暂不可见")
        await cls._ensure_default_tasks(db)
        await cls._ensure_default_questions(db)
        settings = await cls._settings(db)
        progress = await cls._progress(db, viewer, target)
        await cls._auto_grant_coupon_if_needed(db, viewer, settings)
        unlocked = await cls._is_unlocked(db, viewer.id, target.id)
        daily_used = await cls._daily_unlock_count(db, viewer.id)
        coupon = await cls._available_coupon(db, viewer.id)
        task_rows = (
            await db.execute(
                select(MpUnlockTaskModel)
                .where(MpUnlockTaskModel.status == "0", MpUnlockTaskModel.is_deleted == False)
                .order_by(MpUnlockTaskModel.sort.asc(), MpUnlockTaskModel.id.asc())
            )
        ).scalars().all()
        done_counts = await cls._task_record_counts(db, task_rows, viewer.id, target.id)
        tasks: list[dict[str, Any]] = []
        for task in task_rows:
            done_count = done_counts.get(task.id, 0)
            tasks.append(
                {
                    "id": task.id,
                    "task_code": task.task_code,
                    "task_name": task.task_name,
                    "task_type": task.task_type,
                    "task_group": task.task_group,
                    "score": task.score,
                    "daily_limit": task.daily_limit,
                    "completed_today": done_count,
                    "available": task.daily_limit <= 0 or done_count < task.daily_limit,
                    "complete_mode": "detail_action" if task.task_type in DETAIL_ACTION_TASK_TYPES else ("share" if task.task_type == "share" else "manual"),
                }
            )
        unanswered = (
            await db.execute(
                select(func.count(MpUnlockQuestionModel.id)).where(
                    MpUnlockQuestionModel.status == "0",
                    MpUnlockQuestionModel.is_deleted == False,
                    ~MpUnlockQuestionModel.id.in_(
                        select(MpUnlockQuestionAnswerModel.question_id).where(
                            MpUnlockQuestionAnswerModel.viewer_user_id == viewer.id,
                            MpUnlockQuestionAnswerModel.target_user_id == target.id,
                            MpUnlockQuestionAnswerModel.is_deleted == False,
                        )
                    ),
                )
            )
        ).scalar() or 0
        return {
            "target": cls._target_summary(target, person),
            "progress": {
                "score": progress.score,
                "target_score": progress.target_score,
                "percent": min(100, round(progress.score * 100 / max(progress.target_score, 1))),
                "status": "unlocked" if unlocked else progress.progress_status,
                "free_unlock_eligible": progress.score >= progress.target_score,
                "paid_boost_used": progress.paid_boost_used,
            },
            "daily_unlock": {
                "limit": settings["daily_limit"],
                "used": daily_used,
                "remaining": max(settings["daily_limit"] - daily_used, 0) if settings["daily_limit"] > 0 else 999,
            },
            "coupon": {
                "available": bool(coupon),
                "coupon_id": coupon.id if coupon else None,
                "coupon_name": coupon.coupon_name if coupon else settings["coupon_name"],
                "valid_to": coupon.valid_to if coupon else None,
            },
            "payment": {
                "allow_paid_boost": settings["allow_paid_boost"],
                "price": f"{settings['contact_price']:.2f}",
            },
            "task_free": {"allow_task_free": settings["allow_task_free"]},
            "tasks": tasks,
            "question_summary": {"unanswered_count": unanswered},
            "copy": settings["copy"],
            "is_unlocked": unlocked,
        }

    @classmethod
    async def complete_task_service(cls, db: AsyncSession, display_no: str, task_code: str, user_id: int) -> dict[str, Any]:
        viewer = await cls._required_user(db, user_id)
        target, _person = await cls._target_by_display_no(db, display_no)
        if target.is_invisible or viewer.id == target.id:
            raise CustomException(msg="当前资料不可执行任务")
        await cls._ensure_default_tasks(db)
        result = await db.execute(
            select(MpUnlockTaskModel).where(
                MpUnlockTaskModel.task_code == task_code,
                MpUnlockTaskModel.status == "0",
                MpUnlockTaskModel.is_deleted == False,
            )
        )
        task = result.scalars().first()
        if not task:
            raise CustomException(msg="任务不存在或已停用")
        if task.task_type in {"like", "favorite"}:
            relation_type = "like" if task.task_type == "like" else "favorite"
            await cls._set_relation(db, viewer, target, relation_type=relation_type, active=True)
            return await cls.unlock_progress_service(db, display_no, user_id)
        if task.task_type in DIRECT_TASK_TYPES:
            raise CustomException(msg="该任务需通过对应页面行为完成")
        await cls._complete_task(db, viewer, target if task.is_target else None, task, "task")
        return await cls.unlock_progress_service(db, display_no, user_id)

    @classmethod
    async def unlock_questions_service(cls, db: AsyncSession, display_no: str, user_id: int, redis: Any | None = None) -> dict[str, Any]:
        viewer = await cls._required_user(db, user_id)
        target, _person = await cls._target_by_display_no(db, display_no)
        await cls._ensure_default_questions(db)
        selected_ids = await cls._locked_unlock_question_ids(db, viewer.id, target.id, redis)
        if not selected_ids:
            return {"limit": UNLOCK_QUESTION_PICK_COUNT, "total": 0, "answered": 0, "remaining": 0, "items": []}
        selected_rows = (
            await db.execute(
                select(MpUnlockQuestionModel)
                .where(
                    MpUnlockQuestionModel.id.in_(selected_ids),
                    MpUnlockQuestionModel.status == "0",
                    MpUnlockQuestionModel.is_deleted == False,
                )
                .order_by(MpUnlockQuestionModel.sort.asc(), MpUnlockQuestionModel.id.asc())
            )
        ).scalars().all()
        answered_rows = (
            await db.execute(
                select(MpUnlockQuestionAnswerModel.question_id).where(
                    MpUnlockQuestionAnswerModel.viewer_user_id == viewer.id,
                    MpUnlockQuestionAnswerModel.target_user_id == target.id,
                    MpUnlockQuestionAnswerModel.question_id.in_(selected_ids),
                    MpUnlockQuestionAnswerModel.is_deleted == False,
                )
            )
        ).scalars().all()
        answered_ids = set(answered_rows)
        rows = [row for row in selected_rows if row.id not in answered_ids]
        return {
            "limit": UNLOCK_QUESTION_PICK_COUNT,
            "total": len(selected_rows),
            "answered": len(answered_ids),
            "remaining": len(rows),
            "items": [
                {
                    "id": row.id,
                    "question": row.question,
                    "options": row.options,
                    "category": row.category,
                    "correct_score": row.correct_score,
                    "wrong_score": row.wrong_score,
                }
                for row in rows
            ]
        }

    @classmethod
    async def _selected_unlock_question_ids(cls, db: AsyncSession, viewer_id: int, target_id: int) -> set[int]:
        await cls._ensure_default_questions(db)
        rows = (
            await db.execute(
                select(MpUnlockQuestionModel.id)
                .where(MpUnlockQuestionModel.status == "0", MpUnlockQuestionModel.is_deleted == False)
                .order_by(MpUnlockQuestionModel.sort.asc(), MpUnlockQuestionModel.id.asc())
            )
        ).scalars().all()
        selected = list(rows)
        rng = random.Random(f"{viewer_id}:{target_id}:unlock_questions")
        rng.shuffle(selected)
        return set(selected[:UNLOCK_QUESTION_PICK_COUNT])

    @classmethod
    async def _locked_unlock_question_ids(cls, db: AsyncSession, viewer_id: int, target_id: int, redis: Any | None = None) -> set[int]:
        if redis:
            key = cls._question_lock_key(viewer_id, target_id)
            cached = await redis.get(key)
            if cached:
                return {int(item) for item in str(cached).split(",") if item.strip().isdigit()}
            selected = await cls._selected_unlock_question_ids(db, viewer_id, target_id)
            if selected:
                await redis.set(key, ",".join(str(item) for item in sorted(selected)), ex=cls._seconds_until_tomorrow())
            return selected
        return await cls._selected_unlock_question_ids(db, viewer_id, target_id)

    @classmethod
    async def answer_question_service(cls, db: AsyncSession, display_no: str, question_id: int, answer_value: str, user_id: int, redis: Any | None = None) -> dict[str, Any]:
        viewer = await cls._required_user(db, user_id)
        target, _person = await cls._target_by_display_no(db, display_no)
        question = await db.get(MpUnlockQuestionModel, question_id)
        if not question or question.is_deleted or question.status != "0":
            raise CustomException(msg="题目不存在或已停用")
        selected_ids = await cls._locked_unlock_question_ids(db, viewer.id, target.id, redis)
        if question_id not in selected_ids:
            raise CustomException(msg="该题不在本次默契挑战中")
        exists = (
            await db.execute(
                select(MpUnlockQuestionAnswerModel).where(
                    MpUnlockQuestionAnswerModel.viewer_user_id == viewer.id,
                    MpUnlockQuestionAnswerModel.target_user_id == target.id,
                    MpUnlockQuestionAnswerModel.question_id == question_id,
                    MpUnlockQuestionAnswerModel.is_deleted == False,
                )
            )
        ).scalars().first()
        if exists:
            raise CustomException(msg="该题已作答")
        is_correct = bool(question.recommended_answer and answer_value == question.recommended_answer)
        score = question.correct_score if is_correct else question.wrong_score
        progress = await cls._progress(db, viewer, target)
        progress.score = min(progress.target_score, progress.score + score)
        if progress.score >= progress.target_score:
            progress.free_unlock_eligible = True
            progress.progress_status = "ready"
        progress.last_action_at = datetime.now()
        db.add(
            MpUnlockQuestionAnswerModel(
                brand_id=1,
                question_id=question.id,
                viewer_user_id=viewer.id,
                target_user_id=target.id,
                viewer_person_id=viewer.person_id,
                target_person_id=target.person_id,
                answer_value=answer_value,
                is_correct=is_correct,
                score=score,
                answered_at=datetime.now(),
            )
        )
        await cls._record_action(db, "question_answer", target, viewer, {"question_id": question.id, "score": score, "is_correct": is_correct})
        await db.flush()
        return await cls.unlock_progress_service(db, display_no, user_id)

    @classmethod
    async def _toggle_relation(
        cls,
        db: AsyncSession,
        display_no: str,
        user_id: int,
        *,
        relation_type: str,
        active: bool,
    ) -> dict[str, Any]:
        viewer = await cls._required_user(db, user_id)
        target, _person = await cls._target_by_display_no(db, display_no)
        if viewer.id == target.id:
            raise CustomException(msg="不能对自己进行该操作")
        if target.is_invisible:
            raise CustomException(msg="该用户暂不可见")
        await cls._set_relation(db, viewer, target, relation_type=relation_type, active=active)
        return await cls.detail_service(db, display_no, user_id)

    @classmethod
    async def _set_relation(
        cls,
        db: AsyncSession,
        viewer: MiniProgramUserModel,
        target: MiniProgramUserModel,
        *,
        relation_type: str,
        active: bool,
    ) -> None:
        model = MpUserLikeModel if relation_type == "like" else MpUserFavoriteModel
        result = await db.execute(
            select(model).where(
                model.viewer_user_id == viewer.id,
                model.target_user_id == target.id,
                model.is_deleted == False,
            )
        )
        row = result.scalars().first()
        now = datetime.now()
        if not row:
            row = model(
                brand_id=1,
                viewer_user_id=viewer.id,
                target_user_id=target.id,
                viewer_person_id=viewer.person_id,
                target_person_id=target.person_id,
                is_active=active,
            )
            if relation_type == "like":
                row.liked_at = now if active else None
            else:
                row.favorited_at = now if active else None
            db.add(row)
        else:
            row.is_active = active
            if relation_type == "like":
                row.liked_at = now if active else row.liked_at
            else:
                row.favorited_at = now if active else row.favorited_at
            row.cancelled_at = None if active else now
        action = relation_type if active else f"cancel_{relation_type}"
        await cls._record_action(db, action, target, viewer)
        if active:
            await cls._ensure_default_tasks(db)
            task_code = "like_profile" if relation_type == "like" else "favorite_profile"
            task = (
                await db.execute(
                    select(MpUnlockTaskModel).where(
                        MpUnlockTaskModel.task_code == task_code,
                        MpUnlockTaskModel.status == "0",
                        MpUnlockTaskModel.is_deleted == False,
                    )
                )
            ).scalars().first()
            if task:
                await cls._complete_task(db, viewer, target, task, "task")
        await db.flush()

    @classmethod
    async def like_service(cls, db: AsyncSession, display_no: str, user_id: int) -> dict[str, Any]:
        return await cls._toggle_relation(db, display_no, user_id, relation_type="like", active=True)

    @classmethod
    async def unlike_service(cls, db: AsyncSession, display_no: str, user_id: int) -> dict[str, Any]:
        return await cls._toggle_relation(db, display_no, user_id, relation_type="like", active=False)

    @classmethod
    async def favorite_service(cls, db: AsyncSession, display_no: str, user_id: int) -> dict[str, Any]:
        return await cls._toggle_relation(db, display_no, user_id, relation_type="favorite", active=True)

    @classmethod
    async def unfavorite_service(cls, db: AsyncSession, display_no: str, user_id: int) -> dict[str, Any]:
        return await cls._toggle_relation(db, display_no, user_id, relation_type="favorite", active=False)

    @classmethod
    async def _unlock_record(
        cls,
        db: AsyncSession,
        viewer: MiniProgramUserModel,
        target: MiniProgramUserModel,
        *,
        source: str,
        method: str,
        amount: Decimal = Decimal("0.00"),
    ) -> MpContactUnlockModel:
        result = await db.execute(
            select(MpContactUnlockModel).where(
                MpContactUnlockModel.viewer_user_id == viewer.id,
                MpContactUnlockModel.target_user_id == target.id,
                MpContactUnlockModel.is_deleted == False,
            )
        )
        unlock = result.scalars().first()
        if unlock:
            if unlock.unlock_status == "success":
                return unlock
            unlock.unlock_source = source
            unlock.unlock_method = method
            unlock.amount = amount
        else:
            unlock = MpContactUnlockModel(
                brand_id=1,
                viewer_user_id=viewer.id,
                target_user_id=target.id,
                viewer_person_id=viewer.person_id,
                target_person_id=target.person_id,
                unlock_source=source,
                unlock_method=method,
                unlock_status="pending",
                amount=amount,
            )
            db.add(unlock)
        await db.flush()
        return unlock

    @classmethod
    async def _append_unlock_source_event(
        cls,
        db: AsyncSession,
        viewer: MiniProgramUserModel,
        target: MiniProgramUserModel,
        unlock: MpContactUnlockModel,
        payload: dict[str, Any] | None = None,
    ) -> SourceEventModel:
        event = SourceEventModel(
            brand_id=1,
            person_id=viewer.person_id,
            user_id=viewer.id,
            event_type="contact_unlock",
            source_channel=MINIAPP_CONTACT_UNLOCK_CHANNEL,
            source_id=str(target.person_id),
            payload={
                "target_user_id": target.id,
                "target_person_id": target.person_id,
                "target_display_no": target.person.display_no if target.person else None,
                "unlock_id": unlock.id,
                **(payload or {}),
            },
            occurred_at=datetime.now(),
        )
        db.add(event)
        await db.flush()
        return event

    @classmethod
    async def _write_lifecycle(cls, db: AsyncSession, lead: CrmLeadProfileModel, event: SourceEventModel, remark: str) -> None:
        db.add(
            CrmLeadLifecycleModel(
                brand_id=lead.brand_id,
                lead_id=lead.id,
                person_id=lead.person_id,
                operation_type="source_event",
                change_detail={"source_event_id": event.id, "source_channel_code": MINIAPP_CONTACT_UNLOCK_CHANNEL},
                remark=remark,
            )
        )

    @classmethod
    async def _upsert_lead(cls, db: AsyncSession, viewer: MiniProgramUserModel, event: SourceEventModel) -> CrmLeadProfileModel:
        result = await db.execute(
            select(CrmLeadProfileModel).where(
                CrmLeadProfileModel.person_id == viewer.person_id,
                CrmLeadProfileModel.is_deleted == False,
                CrmLeadProfileModel.lead_type.notin_(["invalid", "converted_customer"]),
            )
        )
        lead = result.scalars().first()
        if lead:
            lead.source_channel_code = MINIAPP_CONTACT_UNLOCK_CHANNEL
            lead.latest_source_event_id = event.id
            await cls._write_lifecycle(db, lead, event, "小程序联系方式解锁更新线索来源")
            return lead
        lead = CrmLeadProfileModel(
            brand_id=1,
            person_id=viewer.person_id,
            store_id=None,
            owner_sales_id=None,
            pool_type="hq_pool",
            lead_type="pending",
            source_channel_code=MINIAPP_CONTACT_UNLOCK_CHANNEL,
            latest_source_event_id=event.id,
        )
        db.add(lead)
        await db.flush()
        await cls._write_lifecycle(db, lead, event, "小程序联系方式解锁创建线索")
        return lead

    @classmethod
    async def _mark_unlock_success(
        cls,
        db: AsyncSession,
        unlock: MpContactUnlockModel,
        viewer: MiniProgramUserModel,
        target: MiniProgramUserModel,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if unlock.unlock_status == "success":
            return
        unlock.unlock_status = "success"
        unlock.revoke_reason = None
        unlock.revoked_at = None
        unlock.revoked_by = None
        unlock.unlocked_at = datetime.now()
        source_event = await cls._append_unlock_source_event(db, viewer, target, unlock, payload)
        unlock.source_event_id = source_event.id
        await cls._upsert_lead(db, viewer, source_event)
        await cls._record_action(db, "unlock_success", target, viewer, {"unlock_method": unlock.unlock_method, **(payload or {})})
        await db.flush()

    @classmethod
    async def unlock_by_heartbeat_service(cls, db: AsyncSession, display_no: str, user_id: int) -> dict[str, Any]:
        viewer = await cls._required_user(db, user_id)
        target, _person = await cls._target_by_display_no(db, display_no)
        if viewer.id == target.id:
            raise CustomException(msg="查看自己的资料不需要解锁")
        if target.is_invisible:
            raise CustomException(msg="该用户暂不可见")
        settings = await cls._settings(db)
        if not settings["allow_task_free"]:
            raise CustomException(msg="当前未开启任务免费解锁")
        await cls._assert_can_unlock_today(db, viewer.id)
        await cls._record_action(db, "unlock_heartbeat_attempt", target, viewer)
        progress = await cls._progress(db, viewer, target)
        unlock_score = progress.target_score
        if progress.score < unlock_score:
            raise CustomException(msg="心动值还不够，继续互动后再解锁")
        unlock = await cls._unlock_record(db, viewer, target, source="task_free", method="heartbeat", amount=Decimal("0.00"))
        progress.unlocked_by_score = True
        progress.progress_status = "unlocked"
        await cls._mark_unlock_success(db, unlock, viewer, target, {"score": progress.score})
        return await cls.detail_service(db, display_no, user_id)

    @classmethod
    async def unlock_by_coupon_service(cls, db: AsyncSession, display_no: str, user_id: int) -> dict[str, Any]:
        if not cls._bool(await cls._param(db, "miniprogram.unlock.allow_coupon", DEFAULT_SETTINGS["miniprogram.unlock.allow_coupon"]), True):
            raise CustomException(msg="当前未开启免费券解锁")
        viewer = await cls._required_user(db, user_id)
        target, _person = await cls._target_by_display_no(db, display_no)
        if viewer.id == target.id:
            raise CustomException(msg="查看自己的资料不需要解锁")
        if target.is_invisible:
            raise CustomException(msg="该用户暂不可见")
        await cls._assert_can_unlock_today(db, viewer.id)
        await cls._record_action(db, "unlock_coupon_attempt", target, viewer)
        now = datetime.now()
        coupon = await cls._available_coupon(db, viewer.id)
        if not coupon:
            raise CustomException(msg="暂无可用免费券")
        unlock = await cls._unlock_record(db, viewer, target, source="free_coupon", method="coupon", amount=Decimal("0.00"))
        coupon.coupon_status = "used"
        coupon.used_at = now
        coupon.used_unlock_id = unlock.id
        unlock.coupon_id = coupon.id
        await cls._mark_unlock_success(db, unlock, viewer, target, {"coupon_id": coupon.id})
        return await cls.detail_service(db, display_no, user_id)

    @classmethod
    async def _default_store_id(cls, db: AsyncSession) -> int:
        configured = cls._int(await cls._param(db, "miniprogram.unlock.default_store_id", DEFAULT_SETTINGS["miniprogram.unlock.default_store_id"]), 0)
        if configured:
            dept = await db.get(DeptModel, configured)
            if dept and not dept.is_deleted and dept.status == "0" and dept.parent_id is not None:
                return configured
        result = await db.execute(
            select(DeptModel.id)
            .where(DeptModel.is_deleted == False, DeptModel.status == "0", DeptModel.parent_id.is_not(None))
            .order_by(DeptModel.order.asc(), DeptModel.id.asc())
        )
        store_id = result.scalar()
        if not store_id:
            raise CustomException(msg="请先在小程序设置中配置默认收款门店")
        return int(store_id)

    @staticmethod
    def _notify_url(request: Request) -> str:
        try:
            return str(request.url_for("cloudpay_notify_controller"))
        except Exception:
            root_path = request.scope.get("root_path", "")
            return f"{str(request.base_url).rstrip('/')}{root_path}/cloudpay/notify/trade"

    @classmethod
    async def unlock_by_pay_service(cls, db: AsyncSession, request: Request, display_no: str, user_id: int) -> dict[str, Any]:
        viewer = await cls._required_user(db, user_id)
        target, person = await cls._target_by_display_no(db, display_no)
        if viewer.id == target.id:
            raise CustomException(msg="查看自己的资料不需要解锁")
        if target.is_invisible:
            raise CustomException(msg="该用户暂不可见")
        settings = await cls._settings(db)
        if not settings["allow_paid_boost"]:
            raise CustomException(msg="当前未开启付费补足")
        await cls._assert_can_unlock_today(db, viewer.id)
        await cls._record_action(db, "unlock_pay_attempt", target, viewer)
        price = settings["contact_price"]
        if price <= 0:
            unlock = await cls._unlock_record(db, viewer, target, source="task_free", method="free", amount=Decimal("0.00"))
            await cls._mark_unlock_success(db, unlock, viewer, target, {"reason": "zero_price"})
            return {"detail": await cls.detail_service(db, display_no, user_id), "payment": None}
        if not viewer.openid:
            raise CustomException(msg="请重新登录后再支付")
        unlock = await cls._unlock_record(db, viewer, target, source="paid_boost", method="paid", amount=price)
        if unlock.unlock_status == "success":
            return {"detail": await cls.detail_service(db, display_no, user_id), "payment": None}
        if unlock.order_id:
            order = await db.get(PaymentOrderModel, unlock.order_id)
            if not order:
                unlock.order_id = None
            elif order.pay_status == "paid":
                await cls._mark_unlock_success(db, unlock, viewer, target, {"order_id": order.id, "order_no": order.order_no})
                return {"detail": await cls.detail_service(db, display_no, user_id), "payment": {"paid": True, "order_id": order.id}}
            elif not (order.expire_at and datetime.now() >= order.expire_at) and order.pay_status not in {"timeout", "closed", "failed"}:
                payment = await PaymentService.create_cloudpay_mp_payment(db, order=order, buyer_id=viewer.openid, notify_url=cls._notify_url(request))
                return {"detail": await cls.detail_service(db, display_no, user_id), "payment": payment}
            else:
                await PaymentService.close_order(db, order)
        order = await PaymentService.create_order(
            db,
            biz_type=CONTACT_UNLOCK_BIZ_TYPE,
            biz_id=unlock.id,
            subject=f"解锁联系方式-ID{person.display_no}",
            amount=price,
            store_id=await cls._default_store_id(db),
            person_id=viewer.person_id,
            mp_user_id=viewer.id,
            expire_minutes=24 * 60,
            extra={"target_user_id": target.id, "target_person_id": target.person_id, "target_display_no": person.display_no},
        )
        unlock.order_id = order.id
        await db.flush()
        payment = await PaymentService.create_cloudpay_mp_payment(db, order=order, buyer_id=viewer.openid, notify_url=cls._notify_url(request))
        return {"detail": await cls.detail_service(db, display_no, user_id), "payment": payment}

    @classmethod
    async def continue_unlock_pay_service(cls, db: AsyncSession, request: Request, order_id: int, user_id: int) -> dict[str, Any]:
        viewer = await cls._required_user(db, user_id)
        result = await db.execute(
            select(MpContactUnlockModel)
            .where(
                MpContactUnlockModel.order_id == order_id,
                MpContactUnlockModel.viewer_user_id == viewer.id,
                MpContactUnlockModel.is_deleted == False,
            )
            .options(selectinload(MpContactUnlockModel.order))
        )
        unlock = result.scalars().first()
        if not unlock:
            raise CustomException(msg="解锁订单不存在")
        target = await cls._current_user(db, unlock.target_user_id)
        if not target or not target.person:
            raise CustomException(msg="目标用户不存在")
        return await cls.unlock_by_pay_service(db, request, target.person.display_no, user_id)

    @classmethod
    async def final_task_free_service(cls, db: AsyncSession, display_no: str, user_id: int) -> dict[str, Any]:
        return await cls.unlock_by_heartbeat_service(db, display_no, user_id)

    @classmethod
    async def final_coupon_service(cls, db: AsyncSession, display_no: str, user_id: int) -> dict[str, Any]:
        return await cls.unlock_by_coupon_service(db, display_no, user_id)

    @classmethod
    async def final_pay_service(cls, db: AsyncSession, request: Request, display_no: str, user_id: int) -> dict[str, Any]:
        return await cls.unlock_by_pay_service(db, request, display_no, user_id)

    @classmethod
    async def contact_service(cls, db: AsyncSession, display_no: str, user_id: int) -> dict[str, Any]:
        viewer = await cls._required_user(db, user_id)
        target, person = await cls._target_by_display_no(db, display_no)
        if target.is_invisible and viewer.id != target.id:
            raise CustomException(msg="该用户暂不可见")
        unlock = (
            await db.execute(
                select(MpContactUnlockModel).where(
                    MpContactUnlockModel.viewer_user_id == viewer.id,
                    MpContactUnlockModel.target_user_id == target.id,
                    MpContactUnlockModel.unlock_status == "success",
                    MpContactUnlockModel.is_deleted == False,
                )
            )
        ).scalars().first()
        if viewer.id != target.id and not unlock:
            raise CustomException(msg="尚未解锁联系方式")
        if unlock and unlock.revoked_at:
            raise CustomException(msg="该解锁记录已被撤销，暂不可查看")
        if not person.primary_mobile:
            raise CustomException(msg="该用户暂无可展示手机号")
        if unlock:
            db.add(
                MpContactViewLogModel(
                    brand_id=1,
                    unlock_id=unlock.id,
                    viewer_user_id=viewer.id,
                    target_user_id=target.id,
                    viewer_person_id=viewer.person_id,
                    target_person_id=target.person_id,
                    viewed_at=datetime.now(),
                    payload={"display_no": display_no},
                )
            )
            await cls._record_action(db, "contact_view", target, viewer, {"unlock_id": unlock.id})
            await db.flush()
        settings = await cls._settings(db)
        return {
            "target": cls._target_summary(target, person),
            "mobile": person.primary_mobile,
            "copy": {"contact": settings["copy"]["contact"]},
            "unlock": {
                "unlock_id": unlock.id if unlock else None,
                "unlock_source": unlock.unlock_source if unlock else "self",
                "unlocked_at": unlock.unlocked_at if unlock else None,
            },
        }

    @classmethod
    async def on_payment_success(cls, db: AsyncSession, order: PaymentOrderModel) -> None:
        if order.biz_type != CONTACT_UNLOCK_BIZ_TYPE:
            return
        result = await db.execute(
            select(MpContactUnlockModel)
            .where(MpContactUnlockModel.id == order.biz_id, MpContactUnlockModel.is_deleted == False)
            .options(selectinload(MpContactUnlockModel.order))
        )
        unlock = result.scalars().first()
        if not unlock:
            return
        viewer = await cls._current_user(db, unlock.viewer_user_id)
        target = await cls._current_user(db, unlock.target_user_id)
        if not viewer or not target:
            return
        progress = await cls._progress(db, viewer, target)
        progress.score = progress.target_score
        progress.paid_boost_used = True
        progress.progress_status = "unlocked"
        progress.free_unlock_eligible = True
        await cls._mark_unlock_success(db, unlock, viewer, target, {"order_id": order.id, "order_no": order.order_no})
