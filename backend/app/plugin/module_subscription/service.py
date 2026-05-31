import socket
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import and_, create_engine, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload
from sqlalchemy.pool import NullPool

from app.api.v1.module_system.params.model import ParamsModel
from app.config.setting import get_settings, settings
from app.core.database import async_db_session
from app.core.exceptions import CustomException
from app.plugin.module_crm.lead.model import CrmPersonModel
from app.plugin.module_crm.preference.model import PersonPartnerPreferenceModel
from app.plugin.module_match.service import MatchProfileService
from app.plugin.module_mp.admin.service import MpAdminService
from app.plugin.module_mp.auth.model import MiniProgramUserModel
from app.plugin.module_mp.plaza.model import MpContactUnlockModel, MpContactViewLogModel
from app.plugin.module_mp.plaza.service import MpPlazaService
from app.plugin.module_payment.core.model import PaymentOrderModel
from app.plugin.module_payment.core.service import PaymentService
from app.utils.ai_generation import AiGenerationClient

from .model import (
    SubscriptionPlanModel,
    SubscriptionRecommendationModel,
    SubscriptionRecommendationReasonTaskModel,
    UserSubscriptionModel,
)
from .schema import SubscriptionAdminQueryParam, SubscriptionPlanUpsertSchema

SUBSCRIPTION_BIZ_TYPE = "subscription"
WORKER_JOB_ID = "subscription_recommendation_worker"
REASON_WORKER_JOB_ID = "subscription_reason_polish_worker"
DEFAULT_WORKER_INTERVAL_SECONDS = 60
DEFAULT_WORKER_BATCH_SIZE = 20
DEFAULT_WAITING_RETRY_MINUTES = 30
DEFAULT_REASON_WORKER_INTERVAL_SECONDS = 60
DEFAULT_REASON_WORKER_BATCH_SIZE = 10
DEFAULT_REASON_MAX_TOKENS = 260
DEFAULT_REASON_TEMPERATURE = 0.45
MAX_REASON_RETRY_COUNT = 10
REASON_RETRY_DELAYS = [60, 300, 900, 1800, 3600]
GENDER_LABELS = {"0": "男", "1": "女", "2": "未知"}
ANNUAL_INCOME_LABELS = {
    "below_100k": "10万以下",
    "100k_200k": "10-20万",
    "200k_500k": "20-50万",
    "above_500k": "50万以上",
}
MARITAL_STATUS_LABELS = {"single": "未婚", "divorced": "离异", "widowed": "丧偶"}
EDUCATION_LABELS = {
    "high_school_or_below": "高中及以下",
    "college": "大专",
    "bachelor": "本科",
    "master": "硕士",
    "doctor_or_above": "博士及以上",
}
HOUSE_STATUS_LABELS = {"none": "无房", "owned": "有房无贷", "mortgage": "有房有贷", "family": "与父母同住"}
CAR_STATUS_LABELS = {"none": "无车", "owned": "有车无贷", "loan": "有车有贷"}


class SubscriptionService:
    """小程序订阅推荐服务。"""

    @classmethod
    def register_scheduler(cls) -> None:
        from app.core.ap_scheduler import scheduler

        scheduler.add_job(
            func=cls.process_due_recommendations,
            trigger=IntervalTrigger(seconds=cls._scheduler_interval_seconds(), timezone="Asia/Shanghai"),
            id=WORKER_JOB_ID,
            name="订阅推荐槽位匹配任务",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            jobstore="default",
            executor="default",
        )
        scheduler.add_job(
            func=cls.process_due_reason_tasks,
            trigger=IntervalTrigger(seconds=cls._reason_scheduler_interval_seconds(), timezone="Asia/Shanghai"),
            id=REASON_WORKER_JOB_ID,
            name="订阅推荐理由AI润色任务",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            jobstore="default",
            executor="default",
        )

    @classmethod
    def _scheduler_interval_seconds(cls) -> int:
        return cls._sync_int_param("subscription.worker.interval_seconds", DEFAULT_WORKER_INTERVAL_SECONDS, 10, 3600)

    @classmethod
    def _reason_scheduler_interval_seconds(cls) -> int:
        return cls._sync_int_param("subscription.reason_polish.worker_interval_seconds", DEFAULT_REASON_WORKER_INTERVAL_SECONDS, 10, 3600)

    @classmethod
    def _sync_int_param(cls, key: str, default: int, min_value: int = 1, max_value: int | None = None) -> int:
        try:
            settings = get_settings()
            engine = create_engine(settings.DB_URI, poolclass=NullPool)
            with engine.connect() as conn:
                value = conn.execute(
                    text(
                        """
                        select config_value
                        from sys_param
                        where config_key = :key
                          and is_deleted = false
                          and status = '0'
                        limit 1
                        """
                    ),
                    {"key": key},
                ).scalar()
            engine.dispose()
            return cls._safe_int(value, default, min_value, max_value)
        except Exception:
            return default

    @classmethod
    def _scheduler_redis(cls) -> Any | None:
        try:
            from app.core.ap_scheduler import SchedulerUtil

            return SchedulerUtil.redis_instance
        except ImportError:
            return None

    @classmethod
    async def _param(cls, db: AsyncSession, key: str, default: str) -> str:
        value = (
            await db.execute(
                select(ParamsModel.config_value).where(
                    ParamsModel.config_key == key,
                    ParamsModel.is_deleted == False,
                    ParamsModel.status == "0",
                )
            )
        ).scalar()
        return value if value not in (None, "") else default

    @staticmethod
    def _safe_int(raw: Any, default: int, min_value: int = 1, max_value: int | None = None) -> int:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = default
        value = max(min_value, value)
        return min(value, max_value) if max_value is not None else value

    @classmethod
    async def _int_param(cls, db: AsyncSession, key: str, default: int, min_value: int = 1, max_value: int | None = None) -> int:
        raw = await cls._param(db, key, str(default))
        return cls._safe_int(raw, default, min_value, max_value)

    @classmethod
    async def _bool_param(cls, db: AsyncSession, key: str, default: bool = False) -> bool:
        raw = await cls._param(db, key, "true" if default else "false")
        return str(raw or "").strip().lower() in {"true", "1", "yes", "on"}

    @classmethod
    async def _float_param(cls, db: AsyncSession, key: str, default: float, min_value: float = 0.0, max_value: float | None = None) -> float:
        raw = await cls._param(db, key, str(default))
        try:
            value = float(raw)
        except (TypeError, ValueError):
            value = default
        value = max(min_value, value)
        return min(value, max_value) if max_value is not None else value

    @classmethod
    async def _ensure_default_plans(cls, db: AsyncSession) -> None:
        rows = [
            ("monthly", "月度精准推荐", "month", 30, Decimal("99.00"), 4, 4, "30天内为你开放4位精准推荐，支付后立即开放第1位。", 1),
            ("quarterly", "季度精准推荐", "quarter", 90, Decimal("269.00"), 4, 12, "90天内为你开放12位精准推荐，节奏更稳定。", 2),
            ("yearly", "年度精准推荐", "year", 365, Decimal("999.00"), 4, 48, "365天长期精准推荐，适合认真寻找长期关系。", 3),
        ]
        for code, name, period, days, price, monthly_count, total, desc, sort in rows:
            exists = (
                await db.execute(
                    select(SubscriptionPlanModel).where(
                        SubscriptionPlanModel.plan_code == code,
                        SubscriptionPlanModel.is_deleted == False,
                    )
                )
            ).scalars().first()
            if exists:
                continue
            db.add(
                SubscriptionPlanModel(
                    brand_id=1,
                    plan_code=code,
                    plan_name=name,
                    pay_period=period,
                    period_days=days,
                    price=price,
                    monthly_recommend_count=monthly_count,
                    total_quota=total,
                    benefit_desc=desc,
                    sort=sort,
                    status="0",
                )
            )
        await db.flush()

    @classmethod
    async def _current_user(cls, db: AsyncSession, user_id: int | None) -> MiniProgramUserModel | None:
        if not user_id:
            return None
        return (
            await db.execute(
                select(MiniProgramUserModel)
                .where(MiniProgramUserModel.id == user_id, MiniProgramUserModel.is_deleted == False)
                .options(selectinload(MiniProgramUserModel.person))
            )
        ).scalars().first()

    @classmethod
    async def _active_subscription(cls, db: AsyncSession, user_id: int | None) -> UserSubscriptionModel | None:
        if not user_id:
            return None
        now = datetime.now()
        await cls._expire_old_subscriptions(db)
        row = (
            await db.execute(
                select(UserSubscriptionModel)
                .where(
                    UserSubscriptionModel.user_id == user_id,
                    UserSubscriptionModel.subscription_status == "active",
                    UserSubscriptionModel.expired_at > now,
                    UserSubscriptionModel.is_deleted == False,
                )
                .options(selectinload(UserSubscriptionModel.plan))
                .order_by(UserSubscriptionModel.expired_at.desc(), UserSubscriptionModel.id.desc())
            )
        ).scalars().first()
        return row

    @classmethod
    async def _expire_old_subscriptions(cls, db: AsyncSession) -> None:
        now = datetime.now()
        rows = (
            await db.execute(
                select(UserSubscriptionModel).where(
                    UserSubscriptionModel.subscription_status == "active",
                    UserSubscriptionModel.expired_at <= now,
                    UserSubscriptionModel.is_deleted == False,
                )
            )
        ).scalars().all()
        for row in rows:
            row.subscription_status = "expired"
        if rows:
            rec_rows = (
                await db.execute(
                    select(SubscriptionRecommendationModel).where(
                        SubscriptionRecommendationModel.subscription_id.in_([row.id for row in rows]),
                        SubscriptionRecommendationModel.recommendation_status.in_(["locked", "matching", "waiting_candidate"]),
                        SubscriptionRecommendationModel.is_deleted == False,
                    )
                )
            ).scalars().all()
            for rec in rec_rows:
                rec.recommendation_status = "expired"
            await db.flush()

    @classmethod
    async def _preference_hint(cls, db: AsyncSession, person_id: int | None) -> dict[str, Any]:
        if not person_id:
            return {"completed": False, "message": "注册后完善择偶要求，推荐会更贴近你的期待。"}
        pref = (
            await db.execute(
                select(PersonPartnerPreferenceModel).where(
                    PersonPartnerPreferenceModel.person_id == person_id,
                    PersonPartnerPreferenceModel.is_deleted == False,
                )
            )
        ).scalars().first()
        completed = cls._has_completed_preference(pref)
        return {
            "completed": completed,
            "message": "择偶要求越完整，订阅推荐越精准。" if not completed else "已读取你的择偶要求，推荐会按最新资料临期生成。",
        }

    @staticmethod
    def _has_completed_preference(pref: PersonPartnerPreferenceModel | None) -> bool:
        return bool(pref)

    @classmethod
    async def mp_plans(cls, db: AsyncSession, user_id: int | None) -> dict[str, Any]:
        await cls._ensure_default_plans(db)
        user = await cls._current_user(db, user_id)
        active = await cls._active_subscription(db, user_id)
        plans = (
            await db.execute(
                select(SubscriptionPlanModel)
                .where(SubscriptionPlanModel.is_deleted == False, SubscriptionPlanModel.status == "0")
                .order_by(SubscriptionPlanModel.sort.asc(), SubscriptionPlanModel.id.asc())
            )
        ).scalars().all()
        return {
            "is_registered": bool(user and user.registered_at and user.person_id),
            "has_active_subscription": bool(active),
            "active_subscription_id": active.id if active else None,
            "preference_hint": await cls._preference_hint(db, user.person_id if user else None),
            "plans": [cls._plan_out(plan) for plan in plans],
        }

    @classmethod
    async def mp_me(cls, db: AsyncSession, user_id: int | None) -> dict[str, Any]:
        active = await cls._active_subscription(db, user_id)
        if not active:
            return {"has_active_subscription": False, "subscription": None, "slots": []}
        await cls.process_due_for_subscription(db, active.id)
        await db.flush()
        refreshed = await db.get(UserSubscriptionModel, active.id, options=[selectinload(UserSubscriptionModel.plan)])
        return {
            "has_active_subscription": True,
            "subscription": cls._subscription_out(refreshed),
            "slots": await cls._slots_out(db, active.id),
            "preference_hint": await cls._preference_hint(db, refreshed.person_id if refreshed else None),
        }

    @classmethod
    async def mp_recommendations(cls, db: AsyncSession, user_id: int) -> dict[str, Any]:
        return await cls.mp_me(db, user_id)

    @classmethod
    async def create_order(cls, db: AsyncSession, request, user_id: int, plan_id: int) -> dict[str, Any]:
        user = await cls._current_user(db, user_id)
        if not user or not user.registered_at or not user.person_id:
            raise CustomException(msg="请先完成注册后再购买订阅")
        active = await cls._active_subscription(db, user_id)
        if active:
            return {"already_active": True, "subscription": cls._subscription_out(active)}
        plan = await db.get(SubscriptionPlanModel, plan_id)
        if not plan or plan.is_deleted or plan.status != "0":
            raise CustomException(msg="订阅方案不存在或已停用")
        store_id = await MpAdminService.default_store_id(db)
        if not store_id:
            raise CustomException(msg="请先在后台配置默认收款门店")
        order = await PaymentService.create_order(
            db,
            biz_type=SUBSCRIPTION_BIZ_TYPE,
            biz_id=plan.id,
            subject=f"{plan.plan_name}订阅",
            amount=plan.price,
            store_id=store_id,
            person_id=user.person_id,
            mp_user_id=user.id,
            expire_minutes=24 * 60,
            extra={"plan_id": plan.id, "plan_code": plan.plan_code},
        )
        await db.flush()
        pay = await cls._pay_order(db, request, user, order)
        return {"order": cls._order_out(order), "payment": pay}

    @classmethod
    async def continue_pay(cls, db: AsyncSession, request, user_id: int, order_id: int) -> dict[str, Any]:
        user = await cls._current_user(db, user_id)
        if not user:
            raise CustomException(msg="请先登录")
        order = await db.get(PaymentOrderModel, order_id)
        if not order or order.is_deleted or order.biz_type != SUBSCRIPTION_BIZ_TYPE or order.mp_user_id != user.id:
            raise CustomException(msg="订阅订单不存在")
        if order.pay_status == "paid":
            await cls.on_payment_success(db, order)
            return {"paid": True, "subscription": cls._subscription_out(await cls._active_subscription(db, user.id))}
        if order.expire_at and datetime.now() >= order.expire_at:
            await PaymentService.close_order(db, order)
            raise CustomException(msg="订单已关闭，请重新购买")
        pay = await cls._pay_order(db, request, user, order)
        return {"order": cls._order_out(order), "payment": pay}

    @classmethod
    async def _pay_order(cls, db: AsyncSession, request, user: MiniProgramUserModel, order: PaymentOrderModel) -> dict[str, Any]:
        if not user.openid:
            raise CustomException(msg="当前用户缺少微信openid，无法发起支付")
        notify_url = f"{request.url.scheme}://{request.url.netloc}/api/v1/cloudpay/notify/trade"
        pay = await PaymentService.create_cloudpay_mp_payment(db, order=order, buyer_id=user.openid, notify_url=notify_url)
        if pay.get("paid"):
            await cls.on_payment_success(db, order)
        return pay

    @classmethod
    async def on_payment_success(cls, db: AsyncSession, order: PaymentOrderModel) -> None:
        if order.biz_type != SUBSCRIPTION_BIZ_TYPE:
            return
        exists = (
            await db.execute(
                select(UserSubscriptionModel).where(
                    UserSubscriptionModel.order_id == order.id,
                    UserSubscriptionModel.is_deleted == False,
                )
            )
        ).scalars().first()
        if exists:
            return
        user = await cls._current_user(db, order.mp_user_id)
        plan = await db.get(SubscriptionPlanModel, order.biz_id)
        if not user or not user.person_id or not plan:
            return
        now = datetime.now()
        subscription = UserSubscriptionModel(
            brand_id=1,
            user_id=user.id,
            person_id=user.person_id,
            plan_id=plan.id,
            order_id=order.id,
            started_at=now,
            expired_at=now + timedelta(days=plan.period_days),
            total_quota=plan.total_quota,
            used_quota=0,
            subscription_status="active",
        )
        db.add(subscription)
        await db.flush()
        await cls._create_slots(db, subscription, plan)
        await db.flush()
        await cls.process_due_for_subscription(db, subscription.id)

    @classmethod
    async def _create_slots(cls, db: AsyncSession, subscription: UserSubscriptionModel, plan: SubscriptionPlanModel) -> None:
        total = max(1, plan.total_quota)
        duration_seconds = max(1, int((subscription.expired_at - subscription.started_at).total_seconds()))
        interval = duration_seconds / total
        for index in range(1, total + 1):
            unlock_at = subscription.started_at if index == 1 else subscription.started_at + timedelta(seconds=round(interval * (index - 1)))
            db.add(
                SubscriptionRecommendationModel(
                    brand_id=1,
                    subscription_id=subscription.id,
                    person_id=subscription.person_id,
                    recommend_index=index,
                    unlock_at=unlock_at,
                    recommendation_status="matching" if unlock_at <= datetime.now() else "locked",
                )
            )

    @classmethod
    async def process_due_recommendations(cls, batch_size: int | None = None) -> int:
        processed = 0
        redis = cls._scheduler_redis()
        lock_key = f"subscription:worker:{WORKER_JOB_ID}"
        lock_value = f"{socket.gethostname()}:{datetime.now().timestamp()}"
        acquired = bool(await redis.set(lock_key, lock_value, ex=55, nx=True)) if redis else True
        if not acquired:
            return 0
        try:
            async with async_db_session() as db:
                await cls._expire_old_subscriptions(db)
                now = datetime.now()
                batch_limit = batch_size or await cls._int_param(db, "subscription.worker.batch_size", DEFAULT_WORKER_BATCH_SIZE, 1, 500)
                retry_minutes = await cls._int_param(db, "subscription.waiting_retry_minutes", DEFAULT_WAITING_RETRY_MINUTES, 1, 24 * 60)
                waiting_retry_before = now - timedelta(minutes=retry_minutes)
                rows = (
                    await db.execute(
                        select(SubscriptionRecommendationModel)
                        .join(UserSubscriptionModel, SubscriptionRecommendationModel.subscription_id == UserSubscriptionModel.id)
                        .where(
                            SubscriptionRecommendationModel.is_deleted == False,
                            SubscriptionRecommendationModel.recommendation_status.in_(["locked", "matching", "waiting_candidate"]),
                            SubscriptionRecommendationModel.unlock_at <= now,
                            or_(
                                SubscriptionRecommendationModel.recommendation_status != "waiting_candidate",
                                SubscriptionRecommendationModel.last_match_at.is_(None),
                                SubscriptionRecommendationModel.last_match_at <= waiting_retry_before,
                            ),
                            UserSubscriptionModel.subscription_status == "active",
                            UserSubscriptionModel.expired_at > now,
                            UserSubscriptionModel.is_deleted == False,
                        )
                        .order_by(SubscriptionRecommendationModel.unlock_at.asc(), SubscriptionRecommendationModel.id.asc())
                        .limit(batch_limit)
                    )
                ).scalars().all()
                for row in rows:
                    await cls.process_recommendation(db, row.id)
                    processed += 1
                await db.commit()
        finally:
            if redis:
                script = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end"
                await redis.eval(script, 1, lock_key, lock_value)
        return processed

    @classmethod
    async def process_due_for_subscription(cls, db: AsyncSession, subscription_id: int) -> None:
        now = datetime.now()
        retry_minutes = await cls._int_param(db, "subscription.waiting_retry_minutes", DEFAULT_WAITING_RETRY_MINUTES, 1, 24 * 60)
        waiting_retry_before = now - timedelta(minutes=retry_minutes)
        rows = (
            await db.execute(
                select(SubscriptionRecommendationModel)
                .where(
                    SubscriptionRecommendationModel.subscription_id == subscription_id,
                    SubscriptionRecommendationModel.is_deleted == False,
                    SubscriptionRecommendationModel.recommendation_status.in_(["locked", "matching", "waiting_candidate"]),
                    SubscriptionRecommendationModel.unlock_at <= now,
                    or_(
                        SubscriptionRecommendationModel.recommendation_status != "waiting_candidate",
                        SubscriptionRecommendationModel.last_match_at.is_(None),
                        SubscriptionRecommendationModel.last_match_at <= waiting_retry_before,
                    ),
                )
                .order_by(SubscriptionRecommendationModel.recommend_index.asc())
            )
        ).scalars().all()
        for row in rows:
            await cls.process_recommendation(db, row.id)

    @classmethod
    async def process_recommendation(cls, db: AsyncSession, recommendation_id: int, force: bool = False) -> dict[str, Any]:
        rec = (
            await db.execute(
                select(SubscriptionRecommendationModel)
                .where(SubscriptionRecommendationModel.id == recommendation_id, SubscriptionRecommendationModel.is_deleted == False)
                .options(selectinload(SubscriptionRecommendationModel.subscription))
            )
        ).scalars().first()
        if not rec:
            raise CustomException(msg="订阅推荐槽位不存在")
        sub = rec.subscription
        if not sub or sub.subscription_status != "active" or sub.expired_at <= datetime.now():
            rec.recommendation_status = "expired"
            await db.flush()
            return {"status": rec.recommendation_status}
        if rec.candidate_person_id and rec.recommendation_status in {"unlocked", "viewed"} and not force:
            return {"status": rec.recommendation_status}
        rec.recommendation_status = "matching"
        rec.last_match_at = datetime.now()
        try:
            preference_hint = await cls._preference_hint(db, sub.person_id)
            if not preference_hint["completed"]:
                rec.recommendation_status = "waiting_candidate"
                rec.last_error = "请先完善择偶要求，系统会在条件明确后开始生成订阅推荐"
                await db.flush()
                return {"status": rec.recommendation_status, "need_preference": True}
            excluded = await cls._excluded_person_ids(db, sub)
            result = await MatchProfileService.match_candidates(db, sub.person_id, "subscription", 1, 30)
            candidate = next((item for item in result["items"] if item["person_id"] not in excluded), None)
            if not candidate:
                rec.recommendation_status = "waiting_candidate"
                rec.last_error = None
                await db.flush()
                return {"status": rec.recommendation_status}
            target_conditions = [
                MiniProgramUserModel.person_id == candidate["person_id"],
                MiniProgramUserModel.is_deleted == False,
                MiniProgramUserModel.is_invisible == False,
            ]
            if not await cls._include_pending_users(db):
                target_conditions.append(MiniProgramUserModel.registered_at.is_not(None))
            target_user = (
                await db.execute(
                    select(MiniProgramUserModel)
                    .where(*target_conditions)
                    .options(selectinload(MiniProgramUserModel.person))
                )
            ).scalars().first()
            viewer = await cls._current_user(db, sub.user_id)
            if not target_user or not viewer:
                rec.recommendation_status = "waiting_candidate"
                await db.flush()
                return {"status": rec.recommendation_status}
            unlock = await MpPlazaService._unlock_record(db, viewer, target_user, source="subscription", method="subscription", amount=Decimal("0.00"))
            await MpPlazaService._mark_unlock_success(
                db,
                unlock,
                viewer,
                target_user,
                {"subscription_id": sub.id, "recommendation_id": rec.id},
            )
            rec.candidate_person_id = candidate["person_id"]
            rec.candidate_user_id = target_user.id
            rec.match_score = candidate.get("match_score")
            rule_reason = candidate.get("user_reason")
            rec.match_reason = rule_reason
            rec.match_reason_rule = rule_reason
            rec.match_reason_ai = None
            rec.reason_generation_status = "none"
            rec.reason_model_name = None
            rec.reason_generated_at = None
            rec.reason_last_error = None
            rec.match_snapshot = candidate
            rec.recommendation_status = "unlocked"
            rec.unlock_id = unlock.id
            rec.last_error = None
            await db.flush()
            await cls.enqueue_reason_polish_task(db, rec, viewer, target_user)
            sub.used_quota = (
                await db.execute(
                    select(func.count(SubscriptionRecommendationModel.id)).where(
                        SubscriptionRecommendationModel.subscription_id == sub.id,
                        SubscriptionRecommendationModel.recommendation_status.in_(["unlocked", "viewed"]),
                        SubscriptionRecommendationModel.is_deleted == False,
                    )
                )
            ).scalar() or 0
            sub.last_unlock_at = datetime.now()
            await db.flush()
            return {"status": rec.recommendation_status, "candidate_person_id": rec.candidate_person_id}
        except Exception as exc:
            rec.recommendation_status = "waiting_candidate"
            rec.last_error = str(exc)[:2000]
            await db.flush()
            return {"status": rec.recommendation_status, "error": rec.last_error}

    @classmethod
    async def enqueue_reason_polish_task(
        cls,
        db: AsyncSession,
        rec: SubscriptionRecommendationModel,
        viewer: MiniProgramUserModel,
        target_user: MiniProgramUserModel,
    ) -> SubscriptionRecommendationReasonTaskModel | None:
        """投递订阅推荐理由 AI 润色任务，失败不影响推荐槽位开放。"""

        if not await cls._bool_param(db, "subscription.reason_polish.enabled", True):
            return None
        if not rec.candidate_person_id or not rec.match_reason_rule:
            return None
        snapshot = await cls._build_reason_snapshot(db, rec, viewer, target_user)
        task = (
            await db.execute(
                select(SubscriptionRecommendationReasonTaskModel).where(
                    SubscriptionRecommendationReasonTaskModel.recommendation_id == rec.id,
                    SubscriptionRecommendationReasonTaskModel.is_deleted == False,
                )
            )
        ).scalars().first()
        if task:
            task.subscription_id = rec.subscription_id
            task.viewer_person_id = rec.person_id
            task.target_person_id = rec.candidate_person_id
            task.status = "pending"
            task.retry_count = 0
            task.next_retry_at = datetime.now()
            task.locked_at = None
            task.locked_by = None
            task.last_error = None
            task.payload_snapshot = snapshot
        else:
            task = SubscriptionRecommendationReasonTaskModel(
                brand_id=1,
                recommendation_id=rec.id,
                subscription_id=rec.subscription_id,
                viewer_person_id=rec.person_id,
                target_person_id=rec.candidate_person_id,
                status="pending",
                retry_count=0,
                next_retry_at=datetime.now(),
                payload_snapshot=snapshot,
            )
            db.add(task)
        rec.reason_generation_status = "pending"
        rec.reason_last_error = None
        await db.flush()
        return task

    @classmethod
    async def process_due_reason_tasks(cls, batch_size: int | None = None) -> int:
        """扫描并处理到期的订阅推荐理由润色任务。"""

        processed = 0
        worker_id = f"{socket.gethostname()}:{REASON_WORKER_JOB_ID}"
        now = datetime.now()
        async with async_db_session() as db:
            if not await cls._bool_param(db, "subscription.reason_polish.enabled", True):
                return 0
            batch_limit = batch_size or await cls._int_param(db, "subscription.reason_polish.batch_size", DEFAULT_REASON_WORKER_BATCH_SIZE, 1, 200)
            rows = (
                await db.execute(
                    select(SubscriptionRecommendationReasonTaskModel)
                    .where(
                        SubscriptionRecommendationReasonTaskModel.is_deleted == False,
                        SubscriptionRecommendationReasonTaskModel.status.in_(["pending", "failed"]),
                        SubscriptionRecommendationReasonTaskModel.retry_count < MAX_REASON_RETRY_COUNT,
                        SubscriptionRecommendationReasonTaskModel.next_retry_at <= now,
                    )
                    .order_by(SubscriptionRecommendationReasonTaskModel.next_retry_at.asc(), SubscriptionRecommendationReasonTaskModel.id.asc())
                    .limit(batch_limit)
                )
            ).scalars().all()
            redis = cls._scheduler_redis()
            for task in rows:
                lock_key = f"subscription:reason:task:{task.id}"
                lock_value = f"{worker_id}:{datetime.now().timestamp()}"
                acquired = bool(await redis.set(lock_key, lock_value, ex=600, nx=True)) if redis else True
                if not acquired:
                    continue
                try:
                    task.status = "processing"
                    task.locked_at = datetime.now()
                    task.locked_by = worker_id
                    rec = await db.get(SubscriptionRecommendationModel, task.recommendation_id)
                    if rec:
                        rec.reason_generation_status = "processing"
                    await db.commit()
                    await cls._process_one_reason_task(task.id)
                    processed += 1
                finally:
                    if redis:
                        script = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end"
                        await redis.eval(script, 1, lock_key, lock_value)
        return processed

    @classmethod
    async def _process_one_reason_task(cls, task_id: int) -> None:
        async with async_db_session() as db:
            task = (
                await db.execute(
                    select(SubscriptionRecommendationReasonTaskModel).where(
                        SubscriptionRecommendationReasonTaskModel.id == task_id,
                        SubscriptionRecommendationReasonTaskModel.is_deleted == False,
                    )
                )
            ).scalars().first()
            if not task or task.status == "cancelled":
                return
            rec = await db.get(SubscriptionRecommendationModel, task.recommendation_id)
            if not rec or rec.is_deleted or not rec.candidate_person_id:
                task.status = "cancelled"
                await db.commit()
                return
            try:
                content = await cls._generate_polished_reason(db, task.payload_snapshot or {})
                now = datetime.now()
                rec.match_reason_ai = content
                rec.match_reason = content
                rec.reason_generation_status = "success"
                rec.reason_model_name = settings.OPENAI_MODEL
                rec.reason_generated_at = now
                rec.reason_last_error = None
                task.status = "success"
                task.last_error = None
                task.locked_at = None
                task.locked_by = None
                await db.commit()
            except Exception as exc:
                await db.rollback()
                await cls._mark_reason_failed(task_id, exc)

    @classmethod
    async def _mark_reason_failed(cls, task_id: int, exc: Exception) -> None:
        async with async_db_session() as db:
            task = await db.get(SubscriptionRecommendationReasonTaskModel, task_id)
            if not task:
                return
            retry_count = int(task.retry_count or 0) + 1
            delay_index = min(retry_count - 1, len(REASON_RETRY_DELAYS) - 1)
            task.retry_count = retry_count
            task.status = "failed"
            task.last_error = str(exc)[:2000]
            task.locked_at = None
            task.locked_by = None
            task.next_retry_at = datetime.now() + timedelta(seconds=REASON_RETRY_DELAYS[delay_index] if retry_count < MAX_REASON_RETRY_COUNT else 86400)
            rec = await db.get(SubscriptionRecommendationModel, task.recommendation_id)
            if rec:
                rec.reason_generation_status = "failed"
                rec.reason_last_error = task.last_error
            await db.commit()

    @classmethod
    async def _generate_polished_reason(cls, db: AsyncSession, snapshot: dict[str, Any]) -> str:
        max_tokens = await cls._int_param(db, "subscription.reason_polish.max_tokens", DEFAULT_REASON_MAX_TOKENS, 80, 1000)
        temperature = await cls._float_param(db, "subscription.reason_polish.temperature", DEFAULT_REASON_TEMPERATURE, 0.0, 1.2)
        content = await AiGenerationClient.chat(
            system_prompt="你是婚恋平台的专业推荐理由文案助手，只输出安全、脱敏、温和、可信的中文短文。",
            user_prompt=cls._build_reason_prompt(snapshot),
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return cls._clean_reason(content)

    @classmethod
    def _build_reason_prompt(cls, snapshot: dict[str, Any]) -> str:
        return (
            "请基于以下脱敏匹配信息，为订阅推荐卡片润色一段推荐理由。\n"
            "要求：60-100个中文汉字左右；不要写标题；必须自然完整收束；"
            "文案面向订阅购买者，输入中的 viewer 才是“你”，target 是“对方/TA”，不得反向称呼；"
            "说明双方契合点、为什么值得进一步了解、可以从什么轻松话题开始；"
            "只能依据明确字段、匹配分、命中点和用户一手填写的非结构化偏好表达；"
            "不要使用AI印象、系统摘要或内部备注作为事实依据；不要做人格判断，不要使用“理性、优雅、独立、温柔、成熟”等无法由一手资料直接证明的标签；"
            "不要使用“绝配、命中注定、保证合适”等绝对承诺；不要编造资料；"
            "不要输出手机号、微信号、真实姓名、身份证、证明材料、支付或内部备注。\n"
            f"脱敏匹配信息：{snapshot}"
        )

    @staticmethod
    def _clean_reason(content: str) -> str:
        content = content.strip().replace("\n", " ")
        for prefix in ["推荐理由：", "推荐理由:", "AI推荐理由：", "AI推荐理由:"]:
            if content.startswith(prefix):
                content = content[len(prefix):].strip()
        return content

    @classmethod
    async def _build_reason_snapshot(
        cls,
        db: AsyncSession,
        rec: SubscriptionRecommendationModel,
        viewer: MiniProgramUserModel,
        target_user: MiniProgramUserModel,
    ) -> dict[str, Any]:
        return {
            "recommendation_id": rec.id,
            "match_score": rec.match_score,
            "structured_score": (rec.match_snapshot or {}).get("structured_score"),
            "vector_score": (rec.match_snapshot or {}).get("vector_score"),
            "rule_reason": rec.match_reason_rule or rec.match_reason,
            "matched_points": (rec.match_snapshot or {}).get("matched_points") or [],
            "risk_points": (rec.match_snapshot or {}).get("risk_points") or [],
            "viewer": cls._safe_person_summary(viewer),
            "target": cls._safe_person_summary(target_user),
            "viewer_first_party_preference": await cls._safe_preference_summary(db, rec.person_id),
            "target_first_party_preference": await cls._safe_preference_summary(db, rec.candidate_person_id) if rec.candidate_person_id else None,
        }

    @classmethod
    def _safe_person_summary(cls, user: MiniProgramUserModel) -> dict[str, Any]:
        person = user.person
        if not person:
            return {"display_no": None, "nickname": user.nickname}
        return {
            "display_no": person.display_no,
            "nickname": user.nickname,
            "gender": GENDER_LABELS.get(person.gender, person.gender),
            "age": cls._age(person),
            "height_cm": person.height_cm,
            "residence": person.residence,
            "hometown": person.hometown,
            "education": EDUCATION_LABELS.get(person.education, person.education),
            "occupation": person.occupation,
            "annual_income": ANNUAL_INCOME_LABELS.get(person.annual_income, person.annual_income),
            "marital_status": MARITAL_STATUS_LABELS.get(person.marital_status, person.marital_status),
            "house_status": HOUSE_STATUS_LABELS.get(person.house_status, person.house_status),
            "car_status": CAR_STATUS_LABELS.get(person.car_status, person.car_status),
        }

    @classmethod
    async def _safe_preference_summary(cls, db: AsyncSession, person_id: int) -> dict[str, Any] | None:
        pref = (
            await db.execute(
                select(PersonPartnerPreferenceModel).where(
                    PersonPartnerPreferenceModel.person_id == person_id,
                    PersonPartnerPreferenceModel.is_effective == True,
                    PersonPartnerPreferenceModel.is_deleted == False,
                )
            )
        ).scalars().first()
        if not pref:
            return None

        def clean_list(value: Any) -> list[str]:
            if not value:
                return []
            if isinstance(value, list):
                return [str(item).strip() for item in value if str(item).strip()][:8]
            return []

        def clean_text(value: str | None, limit: int = 180) -> str | None:
            if not value:
                return None
            text = value.strip()
            return text[:limit] if text else None

        summary = {
            "preferred_personality_tags": clean_list(pref.preferred_personality_tags),
            "preferred_lifestyle_tags": clean_list(pref.preferred_lifestyle_tags),
            "preferred_relationship_tags": clean_list(pref.preferred_relationship_tags),
            "hard_reject_items": clean_list(pref.hard_reject_items),
            "soft_preference_items": clean_list(pref.soft_preference_items),
            "preferred_occupation_text": clean_text(pref.preferred_occupation_text),
            "preference_text": clean_text(pref.preference_text, 260),
            "children_requirement": clean_text(pref.children_requirement),
        }
        return {key: value for key, value in summary.items() if value}

    @classmethod
    async def _excluded_person_ids(cls, db: AsyncSession, sub: UserSubscriptionModel) -> set[int]:
        days = int(await cls._param(db, "subscription.repeat_exclude_days", "180"))
        since = datetime.now() - timedelta(days=days)
        ids = {sub.person_id}
        rows = await db.execute(
            select(MpContactUnlockModel.target_person_id).where(
                MpContactUnlockModel.viewer_person_id == sub.person_id,
                MpContactUnlockModel.unlock_status == "success",
                MpContactUnlockModel.is_deleted == False,
            )
        )
        ids.update(int(row[0]) for row in rows.all() if row[0])
        rec_rows = await db.execute(
            select(SubscriptionRecommendationModel.candidate_person_id).where(
                SubscriptionRecommendationModel.person_id == sub.person_id,
                SubscriptionRecommendationModel.candidate_person_id.is_not(None),
                SubscriptionRecommendationModel.created_time >= since,
                SubscriptionRecommendationModel.is_deleted == False,
            )
        )
        ids.update(int(row[0]) for row in rec_rows.all() if row[0])
        return ids

    @classmethod
    async def _include_pending_users(cls, db: AsyncSession) -> bool:
        value = await cls._param(db, "miniprogram.plaza.show_pending_users", "false")
        return str(value or "").lower() in {"true", "1", "yes", "on"}

    @classmethod
    async def contact(cls, db: AsyncSession, user_id: int, recommendation_id: int) -> dict[str, Any]:
        rec = (
            await db.execute(
                select(SubscriptionRecommendationModel)
                .where(SubscriptionRecommendationModel.id == recommendation_id, SubscriptionRecommendationModel.is_deleted == False)
                .options(selectinload(SubscriptionRecommendationModel.subscription))
            )
        ).scalars().first()
        if not rec or rec.subscription.user_id != user_id:
            raise CustomException(msg="订阅推荐不存在")
        if rec.recommendation_status not in {"unlocked", "viewed"} or not rec.candidate_user_id:
            raise CustomException(msg="该推荐暂未开放")
        unlock = await db.get(MpContactUnlockModel, rec.unlock_id)
        if not unlock or unlock.unlock_status != "success" or unlock.revoked_at:
            raise CustomException(msg="订阅解锁记录不可用")
        target = await cls._current_user(db, rec.candidate_user_id)
        if not target or not target.person or not target.person.primary_mobile:
            raise CustomException(msg="该用户暂无可展示手机号")
        db.add(
            MpContactViewLogModel(
                brand_id=1,
                unlock_id=unlock.id,
                viewer_user_id=user_id,
                target_user_id=target.id,
                viewer_person_id=rec.person_id,
                target_person_id=target.person_id,
                viewed_at=datetime.now(),
                payload={"source": "subscription", "recommendation_id": rec.id},
            )
        )
        rec.recommendation_status = "viewed"
        rec.viewed_at = datetime.now()
        await db.flush()
        return {
            "mobile": target.person.primary_mobile,
            "target": cls._target_out(target, target.person),
            "recommendation_id": rec.id,
        }

    @classmethod
    async def _slots_out(cls, db: AsyncSession, subscription_id: int) -> list[dict[str, Any]]:
        rows = (
            await db.execute(
                select(SubscriptionRecommendationModel)
                .where(SubscriptionRecommendationModel.subscription_id == subscription_id, SubscriptionRecommendationModel.is_deleted == False)
                .order_by(SubscriptionRecommendationModel.recommend_index.asc())
            )
        ).scalars().all()
        user_ids = [row.candidate_user_id for row in rows if row.candidate_user_id]
        users = {}
        if user_ids:
            user_rows = (
                await db.execute(
                    select(MiniProgramUserModel)
                    .where(MiniProgramUserModel.id.in_(user_ids), MiniProgramUserModel.is_deleted == False)
                    .options(selectinload(MiniProgramUserModel.person))
                )
            ).scalars().all()
            users = {user.id: user for user in user_rows}
        data = []
        for row in rows:
            user = users.get(row.candidate_user_id)
            data.append(
                {
                    "id": row.id,
                    "recommend_index": row.recommend_index,
                    "unlock_at": row.unlock_at,
                    "status": row.recommendation_status,
                    "viewed_at": row.viewed_at,
                    "match_score": row.match_score,
                    "match_reason": cls._display_match_reason(row),
                    "reason_generation_status": row.reason_generation_status,
                    "last_error": row.last_error,
                    "target": cls._target_out(user, user.person) if user and user.person else None,
                }
            )
        return data

    @staticmethod
    def _display_match_reason(row: SubscriptionRecommendationModel) -> str | None:
        return row.match_reason_ai or row.match_reason_rule or row.match_reason

    @staticmethod
    def _age(person: CrmPersonModel) -> int | None:
        if not person.birth_date:
            return None
        today = datetime.now().date()
        return today.year - person.birth_date.year - ((today.month, today.day) < (person.birth_date.month, person.birth_date.day))

    @classmethod
    def _target_out(cls, user: MiniProgramUserModel, person: CrmPersonModel) -> dict[str, Any]:
        photos = person.photo_urls or []
        return {
            "user_id": user.id,
            "person_id": person.id,
            "display_no": person.display_no,
            "nickname": user.nickname,
            "avatar_url": user.avatar_url or (photos[0] if photos else None),
            "age": cls._age(person),
            "gender": person.gender,
            "height_cm": person.height_cm,
            "residence": person.residence,
            "occupation": person.occupation,
            "education": person.education,
            "annual_income": person.annual_income,
            "marital_status": person.marital_status,
        }

    @staticmethod
    def _plan_out(plan: SubscriptionPlanModel) -> dict[str, Any]:
        return {
            "id": plan.id,
            "plan_code": plan.plan_code,
            "plan_name": plan.plan_name,
            "pay_period": plan.pay_period,
            "period_days": plan.period_days,
            "price": str(plan.price),
            "monthly_recommend_count": plan.monthly_recommend_count,
            "total_quota": plan.total_quota,
            "benefit_desc": plan.benefit_desc,
            "sort": plan.sort,
            "status": plan.status,
        }

    @classmethod
    def _subscription_out(cls, sub: UserSubscriptionModel | None) -> dict[str, Any] | None:
        if not sub:
            return None
        return {
            "id": sub.id,
            "plan": cls._plan_out(sub.plan) if sub.plan else None,
            "started_at": sub.started_at,
            "expired_at": sub.expired_at,
            "total_quota": sub.total_quota,
            "used_quota": sub.used_quota,
            "status": sub.subscription_status,
        }

    @staticmethod
    def _order_out(order: PaymentOrderModel) -> dict[str, Any]:
        return {
            "id": order.id,
            "order_no": order.order_no,
            "amount": str(order.payable_amount),
            "pay_status": order.pay_status,
            "expire_at": order.expire_at,
        }


class SubscriptionAdminService:
    """订阅后台服务。"""

    @classmethod
    async def list_plans(cls, db: AsyncSession) -> list[dict[str, Any]]:
        await SubscriptionService._ensure_default_plans(db)
        rows = (
            await db.execute(
                select(SubscriptionPlanModel)
                .where(SubscriptionPlanModel.is_deleted == False)
                .order_by(SubscriptionPlanModel.sort.asc(), SubscriptionPlanModel.id.asc())
            )
        ).scalars().all()
        return [SubscriptionService._plan_out(row) for row in rows]

    @classmethod
    async def save_plan(cls, db: AsyncSession, data: SubscriptionPlanUpsertSchema, plan_id: int | None = None) -> dict[str, Any]:
        plan = await db.get(SubscriptionPlanModel, plan_id) if plan_id else None
        if not plan:
            plan = (
                await db.execute(
                    select(SubscriptionPlanModel).where(
                        SubscriptionPlanModel.plan_code == data.plan_code,
                        SubscriptionPlanModel.is_deleted == False,
                    )
                )
            ).scalars().first()
        payload = data.model_dump()
        if plan:
            for key, value in payload.items():
                setattr(plan, key, value)
        else:
            plan = SubscriptionPlanModel(brand_id=1, **payload)
            db.add(plan)
        await db.flush()
        return SubscriptionService._plan_out(plan)

    @classmethod
    async def page_subscriptions(cls, db: AsyncSession, page_no: int, page_size: int, search: SubscriptionAdminQueryParam | None) -> dict[str, Any]:
        conditions = [UserSubscriptionModel.is_deleted == False]
        stmt = select(UserSubscriptionModel, MiniProgramUserModel, CrmPersonModel, SubscriptionPlanModel).join(
            MiniProgramUserModel, UserSubscriptionModel.user_id == MiniProgramUserModel.id
        ).join(CrmPersonModel, UserSubscriptionModel.person_id == CrmPersonModel.id).join(SubscriptionPlanModel, UserSubscriptionModel.plan_id == SubscriptionPlanModel.id)
        count_stmt = select(func.count(UserSubscriptionModel.id)).join(MiniProgramUserModel, UserSubscriptionModel.user_id == MiniProgramUserModel.id).join(CrmPersonModel, UserSubscriptionModel.person_id == CrmPersonModel.id)
        if search:
            if search.status:
                conditions.append(UserSubscriptionModel.subscription_status == search.status)
            if search.keyword:
                keyword = f"%{search.keyword}%"
                conditions.append(or_(MiniProgramUserModel.nickname.like(keyword), MiniProgramUserModel.mobile.like(keyword), CrmPersonModel.name.like(keyword), CrmPersonModel.display_no.like(keyword)))
        total = (await db.execute(count_stmt.where(and_(*conditions)))).scalar() or 0
        rows = (
            await db.execute(
                stmt.where(and_(*conditions))
                .order_by(UserSubscriptionModel.created_time.desc(), UserSubscriptionModel.id.desc())
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
                    "id": sub.id,
                    "user_id": user.id,
                    "display_no": person.display_no,
                    "nickname": user.nickname,
                    "mobile": user.mobile,
                    "plan_name": plan.plan_name,
                    "started_at": sub.started_at,
                    "expired_at": sub.expired_at,
                    "total_quota": sub.total_quota,
                    "used_quota": sub.used_quota,
                    "status": sub.subscription_status,
                    "order_id": sub.order_id,
                }
                for sub, user, person, plan in rows
            ],
        }

    @classmethod
    async def page_recommendations(cls, db: AsyncSession, page_no: int, page_size: int, search: SubscriptionAdminQueryParam | None) -> dict[str, Any]:
        source_user = aliased(MiniProgramUserModel)
        source_person = aliased(CrmPersonModel)
        target_user = aliased(MiniProgramUserModel)
        target_person = aliased(CrmPersonModel)
        conditions = [SubscriptionRecommendationModel.is_deleted == False]
        stmt = (
            select(SubscriptionRecommendationModel, source_user, source_person, target_user, target_person)
            .join(UserSubscriptionModel, SubscriptionRecommendationModel.subscription_id == UserSubscriptionModel.id)
            .join(source_user, UserSubscriptionModel.user_id == source_user.id)
            .join(source_person, UserSubscriptionModel.person_id == source_person.id)
            .outerjoin(target_user, SubscriptionRecommendationModel.candidate_user_id == target_user.id)
            .outerjoin(target_person, SubscriptionRecommendationModel.candidate_person_id == target_person.id)
        )
        count_stmt = select(func.count(SubscriptionRecommendationModel.id)).join(UserSubscriptionModel, SubscriptionRecommendationModel.subscription_id == UserSubscriptionModel.id).join(source_user, UserSubscriptionModel.user_id == source_user.id).join(source_person, UserSubscriptionModel.person_id == source_person.id).outerjoin(target_user, SubscriptionRecommendationModel.candidate_user_id == target_user.id).outerjoin(target_person, SubscriptionRecommendationModel.candidate_person_id == target_person.id)
        if search:
            if search.status:
                conditions.append(SubscriptionRecommendationModel.recommendation_status == search.status)
            if search.keyword:
                keyword = f"%{search.keyword}%"
                conditions.append(or_(source_user.nickname.like(keyword), source_user.mobile.like(keyword), source_person.display_no.like(keyword), target_user.nickname.like(keyword), target_person.display_no.like(keyword)))
        total = (await db.execute(count_stmt.where(and_(*conditions)))).scalar() or 0
        rows = (
            await db.execute(
                stmt.where(and_(*conditions))
                .order_by(SubscriptionRecommendationModel.unlock_at.desc(), SubscriptionRecommendationModel.id.desc())
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
                    "id": rec.id,
                    "subscription_id": rec.subscription_id,
                    "viewer_display_no": viewer_person.display_no,
                    "viewer_nickname": viewer_user.nickname,
                    "target_display_no": target_person_row.display_no if target_person_row else None,
                    "target_nickname": target_user_row.nickname if target_user_row else None,
                    "recommend_index": rec.recommend_index,
                    "unlock_at": rec.unlock_at,
                    "status": rec.recommendation_status,
                    "viewed_at": rec.viewed_at,
                    "match_score": rec.match_score,
                    "match_reason": SubscriptionService._display_match_reason(rec),
                    "match_reason_rule": rec.match_reason_rule,
                    "match_reason_ai": rec.match_reason_ai,
                    "reason_generation_status": rec.reason_generation_status,
                    "reason_model_name": rec.reason_model_name,
                    "reason_generated_at": rec.reason_generated_at,
                    "reason_last_error": rec.reason_last_error,
                    "last_error": rec.last_error,
                }
                for rec, viewer_user, viewer_person, target_user_row, target_person_row in rows
            ],
        }
