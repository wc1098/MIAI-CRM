from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import ModelMixin


class MpUserProfileActionModel(ModelMixin):
    """小程序用户资料行为记录。"""

    __tablename__ = "mp_user_profile_action"
    __table_args__: dict[str, str] = {"comment": "小程序用户资料行为记录表"}

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    viewer_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("mini_program_user.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="查看/操作用户ID",
    )
    viewer_person_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="查看/操作人员ID")
    target_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mini_program_user.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="目标小程序用户ID",
    )
    target_person_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="目标人员ID")
    action_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="行为类型")
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="行为参数")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="发生时间")


class MpUserLikeModel(ModelMixin):
    """小程序用户喜欢关系。"""

    __tablename__ = "mp_user_like"
    __table_args__ = (
        UniqueConstraint("viewer_user_id", "target_user_id", name="uq_mp_user_like_viewer_target"),
        {"comment": "小程序用户喜欢关系表"},
    )

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    viewer_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mini_program_user.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="喜欢发起用户ID",
    )
    target_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mini_program_user.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="被喜欢用户ID",
    )
    viewer_person_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="喜欢发起人员ID")
    target_person_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="被喜欢人员ID")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True, comment="是否有效")
    liked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="喜欢时间")
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="取消时间")


class MpUserFavoriteModel(ModelMixin):
    """小程序用户收藏关系。"""

    __tablename__ = "mp_user_favorite"
    __table_args__ = (
        UniqueConstraint("viewer_user_id", "target_user_id", name="uq_mp_user_favorite_viewer_target"),
        {"comment": "小程序用户收藏关系表"},
    )

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    viewer_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mini_program_user.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="收藏发起用户ID",
    )
    target_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mini_program_user.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="被收藏用户ID",
    )
    viewer_person_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="收藏发起人员ID")
    target_person_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="被收藏人员ID")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True, comment="是否有效")
    favorited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="收藏时间")
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="取消时间")


class MpHeartbeatProgressModel(ModelMixin):
    """小程序用户对目标的心动值进度。"""

    __tablename__ = "mp_heartbeat_progress"
    __table_args__ = (
        UniqueConstraint("viewer_user_id", "target_user_id", name="uq_mp_heartbeat_progress_viewer_target"),
        {"comment": "小程序用户心动值进度表"},
    )

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    viewer_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="查看用户ID")
    target_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="目标用户ID")
    viewer_person_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="查看人员ID")
    target_person_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="目标人员ID")
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="当前心动值")
    target_score: Mapped[int] = mapped_column(Integer, nullable=False, default=100, comment="目标心动值")
    progress_status: Mapped[str] = mapped_column(String(32), nullable=False, default="processing", index=True, comment="进度状态")
    free_unlock_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否可任务免费解锁")
    paid_boost_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否已付费补足")
    unlocked_by_score: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否已用心动值解锁")
    last_action_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最近加分时间")


class MpContactUnlockModel(ModelMixin):
    """小程序联系方式解锁记录。"""

    __tablename__ = "mp_contact_unlock"
    __table_args__ = (
        UniqueConstraint("viewer_user_id", "target_user_id", name="uq_mp_contact_unlock_viewer_target"),
        {"comment": "小程序联系方式解锁记录表"},
    )

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    viewer_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="查看用户ID")
    target_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="目标用户ID")
    viewer_person_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="查看人员ID")
    target_person_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="目标人员ID")
    unlock_source: Mapped[str] = mapped_column(String(32), nullable=False, default="paid_boost", index=True, comment="解锁来源")
    unlock_method: Mapped[str] = mapped_column(String(32), nullable=False, default="paid", index=True, comment="解锁方式")
    unlock_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True, comment="解锁状态")
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0, comment="应付金额")
    order_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("payment_order.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="支付订单ID",
    )
    coupon_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="免费券ID")
    source_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="来源事件ID")
    unlocked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="解锁时间")
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="撤销时间")
    revoked_by: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="撤销人")
    revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="撤销/屏蔽原因")

    order: Mapped[Any] = relationship("PaymentOrderModel", lazy="selectin")


class MpUnlockCouponModel(ModelMixin):
    """小程序联系方式解锁免费券。"""

    __tablename__ = "mp_unlock_coupon"
    __table_args__: dict[str, str] = {"comment": "小程序解锁免费券表"}

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mini_program_user.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="持有人小程序用户ID",
    )
    person_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="持有人人员ID")
    coupon_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="券名称")
    coupon_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unused", index=True, comment="券状态")
    valid_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="有效期开始")
    valid_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="有效期结束")
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="使用时间")
    used_unlock_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="使用解锁记录ID")
    grant_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="发放原因")
    grant_source: Mapped[str] = mapped_column(String(32), nullable=False, default="admin", index=True, comment="发放来源")


class MpUnlockTaskModel(ModelMixin):
    """小程序联系方式解锁任务配置。"""

    __tablename__ = "mp_unlock_task"
    __table_args__ = (
        UniqueConstraint("task_code", name="uq_mp_unlock_task_code"),
        {"comment": "小程序解锁任务配置表"},
    )

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    task_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="任务编码")
    task_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="任务名称")
    task_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="任务类型")
    task_group: Mapped[str] = mapped_column(String(32), nullable=False, default="quick", index=True, comment="任务分组")
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="加分值")
    is_global: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否全局任务")
    is_target: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否目标任务")
    daily_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="每日次数限制，0表示不限")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True, comment="排序")


class MpUnlockTaskRecordModel(ModelMixin):
    """小程序用户解锁任务完成记录。"""

    __tablename__ = "mp_unlock_task_record"
    __table_args__: dict[str, str] = {"comment": "小程序解锁任务完成记录表"}

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("mp_unlock_task.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="任务ID")
    task_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="任务编码")
    viewer_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="发起用户ID")
    target_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="目标用户ID")
    viewer_person_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="发起人员ID")
    target_person_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="目标人员ID")
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="实际加分")
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual", index=True, comment="完成来源")
    completed_on: Mapped[str] = mapped_column(String(10), nullable=False, index=True, comment="完成日期")
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="扩展参数")
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="完成时间")

    task: Mapped[Any] = relationship("MpUnlockTaskModel", lazy="selectin")


class MpUnlockQuestionModel(ModelMixin):
    """小程序默契题配置。"""

    __tablename__ = "mp_unlock_question"
    __table_args__: dict[str, str] = {"comment": "小程序默契题配置表"}

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    question: Mapped[str] = mapped_column(String(255), nullable=False, comment="题目")
    options: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, comment="选项")
    recommended_answer: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="推荐答案")
    match_tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, comment="匹配标签")
    correct_score: Mapped[int] = mapped_column(Integer, nullable=False, default=10, comment="答对加分")
    wrong_score: Mapped[int] = mapped_column(Integer, nullable=False, default=3, comment="答错加分")
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="default", index=True, comment="题目分类")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True, comment="排序")


class MpUnlockQuestionAnswerModel(ModelMixin):
    """小程序默契题作答记录。"""

    __tablename__ = "mp_unlock_question_answer"
    __table_args__ = (
        UniqueConstraint("viewer_user_id", "target_user_id", "question_id", name="uq_mp_unlock_answer_once"),
        {"comment": "小程序默契题作答记录表"},
    )

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("mp_unlock_question.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="题目ID")
    viewer_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="答题用户ID")
    target_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="目标用户ID")
    viewer_person_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="答题人员ID")
    target_person_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="目标人员ID")
    answer_value: Mapped[str] = mapped_column(String(64), nullable=False, comment="作答值")
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否匹配推荐答案")
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="得分")
    answered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="答题时间")

    question_obj: Mapped[Any] = relationship("MpUnlockQuestionModel", lazy="selectin")


class MpContactViewLogModel(ModelMixin):
    """小程序手机号查看日志。"""

    __tablename__ = "mp_contact_view_log"
    __table_args__: dict[str, str] = {"comment": "小程序联系方式查看日志表"}

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    unlock_id: Mapped[int] = mapped_column(Integer, ForeignKey("mp_contact_unlock.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="解锁记录ID")
    viewer_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="查看用户ID")
    target_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="目标用户ID")
    viewer_person_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="查看人员ID")
    target_person_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="目标人员ID")
    viewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="查看时间")
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="扩展参数")
