from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import ModelMixin, UserMixin


class PaymentOrderModel(ModelMixin, UserMixin):
    """统一支付订单。"""

    __tablename__ = "payment_order"
    __table_args__ = {"comment": "统一支付订单表"}
    __loader_options__ = ["records"]

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    store_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sys_dept.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="门店ID",
    )
    order_no: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True, comment="本地订单号")
    biz_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="业务类型")
    biz_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="业务ID")
    person_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("crm_person.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="人员ID",
    )
    mp_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("mini_program_user.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="小程序用户ID",
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False, comment="订单标题")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, comment="订单金额")
    payable_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, comment="应付金额")
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, comment="实付金额")
    order_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True, comment="订单状态")
    pay_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True, comment="支付状态")
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="cloudpay", index=True, comment="支付渠道")
    expire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="超时时间")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="支付成功时间")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="关闭时间")
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="扩展数据")

    records: Mapped[list["PaymentRecordModel"]] = relationship("PaymentRecordModel", lazy="selectin")


class PaymentRecordModel(ModelMixin):
    """支付尝试/流水。"""

    __tablename__ = "payment_record"
    __table_args__ = {"comment": "支付流水表"}

    order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("payment_order.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="订单ID",
    )
    payment_no: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True, comment="支付流水号")
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="cloudpay", index=True, comment="支付渠道")
    pay_method: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="支付方式")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, comment="支付金额")
    payment_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True, comment="支付状态")
    merchant_trade_no: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="商户订单号")
    channel_trade_no: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True, comment="渠道交易号")
    raw_request: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="请求快照")
    raw_response: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="响应快照")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="支付成功时间")


class PaymentCallbackLogModel(ModelMixin):
    """支付回调日志。"""

    __tablename__ = "payment_callback_log"
    __table_args__ = {"comment": "支付回调日志表"}

    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="cloudpay", index=True, comment="支付渠道")
    merchant_trade_no: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="商户订单号")
    channel_trade_no: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True, comment="渠道交易号")
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="回调原文")
    signature: Mapped[str | None] = mapped_column(Text, nullable=True, comment="签名")
    verify_result: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="验签结果")
    process_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True, comment="处理状态")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    received_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="接收时间")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="处理时间")


class PaymentRefundModel(ModelMixin, UserMixin):
    """退款记录预留。"""

    __tablename__ = "payment_refund"
    __table_args__ = {"comment": "退款记录表"}

    order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("payment_order.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="订单ID",
    )
    payment_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("payment_record.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="支付流水ID",
    )
    refund_no: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True, comment="退款单号")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, comment="退款金额")
    refund_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True, comment="退款状态")
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="退款原因")
    raw_response: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="渠道响应")
