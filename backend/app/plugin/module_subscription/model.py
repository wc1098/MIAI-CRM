from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import ModelMixin, UserMixin


class SubscriptionPlanModel(ModelMixin, UserMixin):
    """小程序订阅方案。"""

    __tablename__ = "subscription_plan"
    __table_args__ = (
        UniqueConstraint("plan_code", name="uq_subscription_plan_code"),
        {"comment": "小程序订阅方案表"},
    )

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    plan_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="方案编码")
    plan_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="方案名称")
    pay_period: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="支付周期")
    period_days: Mapped[int] = mapped_column(Integer, nullable=False, comment="权益天数")
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0, comment="价格")
    monthly_recommend_count: Mapped[int] = mapped_column(Integer, nullable=False, default=4, comment="每月推荐数")
    total_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=4, comment="总推荐槽位")
    benefit_desc: Mapped[str | None] = mapped_column(Text, nullable=True, comment="权益说明")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True, comment="排序")


class UserSubscriptionModel(ModelMixin):
    """小程序用户订阅。"""

    __tablename__ = "user_subscription"
    __table_args__: dict[str, str] = {"comment": "小程序用户订阅表"}

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("mini_program_user.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="小程序用户ID")
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="人员ID")
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("subscription_plan.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="订阅方案ID")
    order_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("payment_order.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="订单ID")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, comment="开始时间")
    expired_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, comment="过期时间")
    total_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="总槽位")
    used_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="已开放槽位")
    last_unlock_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="最近开放时间")
    subscription_status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True, comment="订阅状态")
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="扩展数据")

    plan: Mapped[SubscriptionPlanModel] = relationship("SubscriptionPlanModel", lazy="selectin")


class SubscriptionRecommendationModel(ModelMixin):
    """小程序订阅推荐槽位。"""

    __tablename__ = "subscription_recommendation"
    __table_args__: dict[str, str] = {"comment": "小程序订阅推荐槽位表"}

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    subscription_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_subscription.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="订阅ID")
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="订阅人Person")
    candidate_person_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="候选Person")
    candidate_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("mini_program_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="候选小程序用户")
    recommend_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="推荐序号")
    unlock_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, comment="开放时间")
    recommendation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="locked", index=True, comment="推荐状态")
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="查看手机号时间")
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="match", index=True, comment="推荐来源")
    match_score: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="匹配度")
    match_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="推荐理由")
    match_reason_rule: Mapped[str | None] = mapped_column(Text, nullable=True, comment="规则推荐理由")
    match_reason_ai: Mapped[str | None] = mapped_column(Text, nullable=True, comment="AI润色推荐理由")
    reason_generation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="none", index=True, comment="推荐理由生成状态")
    reason_model_name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="推荐理由模型名称")
    reason_generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="推荐理由生成时间")
    reason_last_error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="推荐理由最近错误")
    match_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="匹配快照")
    unlock_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("mp_contact_unlock.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="联系方式解锁记录")
    last_match_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="最近匹配时间")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="最近错误")

    subscription: Mapped[UserSubscriptionModel] = relationship("UserSubscriptionModel", lazy="selectin")


class SubscriptionRecommendationReasonTaskModel(ModelMixin):
    """订阅推荐理由 AI 润色任务。"""

    __tablename__ = "subscription_recommendation_reason_task"
    __table_args__ = (
        UniqueConstraint("recommendation_id", name="uq_subscription_reason_task_recommendation"),
        {"comment": "订阅推荐理由AI润色任务表"},
    )

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    recommendation_id: Mapped[int] = mapped_column(Integer, ForeignKey("subscription_recommendation.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="推荐槽位ID")
    subscription_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_subscription.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="订阅ID")
    viewer_person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="查看人Person")
    target_person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="被推荐Person")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="重试次数")
    next_retry_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="下次执行时间")
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="锁定时间")
    locked_by: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="锁定者")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="最近错误")
    payload_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="脱敏输入快照")
