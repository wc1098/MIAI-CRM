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

from app.core.base_model import ModelMixin, UserMixin


class EventModel(ModelMixin, UserMixin):
    """品牌活动主表。"""

    __tablename__ = "event"
    __table_args__ = {"comment": "活动主表"}
    __loader_options__ = ["store", "created_by", "updated_by"]

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    store_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sys_dept.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="归属门店ID",
    )
    title: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment="活动标题")
    subtitle: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="活动副标题")
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="活动类型")
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="封面图URL")
    location: Mapped[str] = mapped_column(String(255), nullable=False, comment="活动地点")
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, comment="开始时间")
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, comment="结束时间")
    register_deadline: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, comment="报名截止时间")
    detail_html: Mapped[str | None] = mapped_column(Text, nullable=True, comment="活动详情富文本")
    effect_html: Mapped[str | None] = mapped_column(Text, nullable=True, comment="活动效果富文本")
    male_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="男生名额")
    female_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="女生名额")
    male_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, comment="男生费用")
    female_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, comment="女生费用")
    vip_free: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="VIP是否免费")
    require_realname: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否要求实名")
    min_age: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="最小年龄")
    max_age: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="最大年龄")
    event_status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True, comment="活动状态")
    published_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="发布人ID",
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="发布时间")

    store: Mapped[Any] = relationship("DeptModel", lazy="selectin")


class EventRegistrationModel(ModelMixin):
    """活动报名表。"""

    __tablename__ = "event_registration"
    __table_args__ = (
        UniqueConstraint("event_id", "mp_user_id", name="uq_event_registration_event_user"),
        {"comment": "活动报名表"},
    )
    __loader_options__ = ["event", "mp_user", "person", "order"]

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    event_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("event.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="活动ID",
    )
    mp_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mini_program_user.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="小程序用户ID",
    )
    person_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="人员ID",
    )
    registration_no: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True, comment="报名编号")
    gender_snapshot: Mapped[str] = mapped_column(String(1), nullable=False, index=True, comment="性别快照")
    payable_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, comment="应付金额")
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, comment="实付金额")
    order_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("payment_order.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="支付订单ID",
    )
    registration_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_payment", index=True, comment="报名状态")
    registered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="报名时间")
    payment_expire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="支付超时时间")
    source_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="报名成功来源事件ID")

    event: Mapped[EventModel] = relationship("EventModel", lazy="selectin")
    mp_user: Mapped[Any] = relationship("MiniProgramUserModel", lazy="selectin")
    person: Mapped[Any] = relationship("CrmPersonModel", lazy="selectin")
    order: Mapped[Any] = relationship("PaymentOrderModel", lazy="selectin")


class EventParticipantModel(ModelMixin):
    """活动签到/参会表。"""

    __tablename__ = "event_participant"
    __table_args__ = (
        UniqueConstraint("event_id", "mp_user_id", name="uq_event_participant_event_user"),
        {"comment": "活动签到参会表"},
    )
    __loader_options__ = ["event", "registration", "mp_user", "person"]

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    event_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("event.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="活动ID",
    )
    registration_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("event_registration.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="报名ID",
    )
    mp_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mini_program_user.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="小程序用户ID",
    )
    person_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="人员ID",
    )
    onsite_no: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True, comment="现场编号")
    display_nickname: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="展示昵称")
    gender_snapshot: Mapped[str] = mapped_column(String(1), nullable=False, index=True, comment="性别快照")
    profile_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="资料快照")
    checkin_type: Mapped[str] = mapped_column(String(32), nullable=False, default="registered", index=True, comment="签到类型")
    checked_in_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="签到时间")
    participant_status: Mapped[str] = mapped_column(String(32), nullable=False, default="checked_in", index=True, comment="参会状态")
    source_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="签到来源事件ID")

    event: Mapped[EventModel] = relationship("EventModel", lazy="selectin")
    registration: Mapped[EventRegistrationModel | None] = relationship("EventRegistrationModel", lazy="selectin")
    mp_user: Mapped[Any] = relationship("MiniProgramUserModel", lazy="selectin")
    person: Mapped[Any] = relationship("CrmPersonModel", lazy="selectin")
