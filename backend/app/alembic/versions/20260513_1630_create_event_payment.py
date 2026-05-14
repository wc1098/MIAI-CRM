"""create event and payment base

Revision ID: 20260513_1630
Revises: 20260513_1508
Create Date: 2026-05-13 16:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20260513_1630"
down_revision: str | None = "20260513_1508"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _indexes(table_name: str) -> set[str]:
    return {index["name"] for index in inspect(op.get_bind()).get_indexes(table_name)}


def _create_index_if_missing(table_name: str, column_name: str, unique: bool = False) -> None:
    index_name = op.f(f"ix_{table_name}_{column_name}")
    if index_name not in _indexes(table_name):
        op.create_index(index_name, table_name, [column_name], unique=unique)


def _base_columns() -> list[sa.Column | sa.Constraint]:
    return [
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("uuid", sa.String(length=64), nullable=False, comment="UUID全局唯一标识"),
        sa.Column("status", sa.String(length=10), nullable=False, comment="状态(0:正常 1:禁用)"),
        sa.Column("description", sa.Text(), nullable=True, comment="备注/描述"),
        sa.Column("created_time", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_time", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, comment="是否已删除(0:未删除 1:已删除)"),
        sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
        sa.PrimaryKeyConstraint("id"),
    ]


def _user_columns() -> list[sa.Column | sa.Constraint]:
    return [
        sa.Column("created_id", sa.Integer(), nullable=True, comment="创建人ID"),
        sa.Column("updated_id", sa.Integer(), nullable=True, comment="更新人ID"),
        sa.Column("deleted_id", sa.Integer(), nullable=True, comment="删除人ID"),
        sa.ForeignKeyConstraint(["created_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["updated_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["deleted_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
    ]


def _base_indexes(table_name: str) -> None:
    for column in ["created_time", "deleted_time", "id", "is_deleted", "status", "updated_time"]:
        _create_index_if_missing(table_name, column)
    _create_index_if_missing(table_name, "uuid", unique=True)


def _add_indexes(table_name: str, columns: list[str], unique_columns: list[str] | None = None) -> None:
    for column in columns:
        _create_index_if_missing(table_name, column)
    for column in unique_columns or []:
        _create_index_if_missing(table_name, column, unique=True)


def upgrade() -> None:
    existing_tables = _tables()
    if "payment_order" not in existing_tables:
        op.create_table(
            "payment_order",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("store_id", sa.Integer(), nullable=True, comment="门店ID"),
            sa.Column("order_no", sa.String(length=32), nullable=False, comment="本地订单号"),
            sa.Column("biz_type", sa.String(length=64), nullable=False, comment="业务类型"),
            sa.Column("biz_id", sa.Integer(), nullable=False, comment="业务ID"),
            sa.Column("person_id", sa.Integer(), nullable=True, comment="人员ID"),
            sa.Column("mp_user_id", sa.Integer(), nullable=True, comment="小程序用户ID"),
            sa.Column("subject", sa.String(length=255), nullable=False, comment="订单标题"),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False, comment="订单金额"),
            sa.Column("payable_amount", sa.Numeric(12, 2), nullable=False, comment="应付金额"),
            sa.Column("paid_amount", sa.Numeric(12, 2), nullable=False, comment="实付金额"),
            sa.Column("order_status", sa.String(length=32), nullable=False, comment="订单状态"),
            sa.Column("pay_status", sa.String(length=32), nullable=False, comment="支付状态"),
            sa.Column("channel", sa.String(length=32), nullable=False, comment="支付渠道"),
            sa.Column("expire_at", sa.DateTime(), nullable=True, comment="超时时间"),
            sa.Column("paid_at", sa.DateTime(), nullable=True, comment="支付成功时间"),
            sa.Column("closed_at", sa.DateTime(), nullable=True, comment="关闭时间"),
            sa.Column("extra", sa.JSON(), nullable=True, comment="扩展数据"),
            *_base_columns(),
            *_user_columns(),
            sa.ForeignKeyConstraint(["store_id"], ["sys_dept.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["mp_user_id"], ["mini_program_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        )
        _base_indexes("payment_order")
        _add_indexes(
            "payment_order",
            ["brand_id", "store_id", "biz_type", "biz_id", "person_id", "mp_user_id", "order_status", "pay_status", "channel", "expire_at", "paid_at", "closed_at", "created_id", "updated_id", "deleted_id"],
            ["order_no"],
        )

    if "payment_record" not in existing_tables:
        op.create_table(
            "payment_record",
            sa.Column("order_id", sa.Integer(), nullable=False, comment="订单ID"),
            sa.Column("payment_no", sa.String(length=32), nullable=False, comment="支付流水号"),
            sa.Column("channel", sa.String(length=32), nullable=False, comment="支付渠道"),
            sa.Column("pay_method", sa.String(length=32), nullable=True, comment="支付方式"),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False, comment="支付金额"),
            sa.Column("payment_status", sa.String(length=32), nullable=False, comment="支付状态"),
            sa.Column("merchant_trade_no", sa.String(length=64), nullable=True, comment="商户订单号"),
            sa.Column("channel_trade_no", sa.String(length=128), nullable=True, comment="渠道交易号"),
            sa.Column("raw_request", sa.JSON(), nullable=True, comment="请求快照"),
            sa.Column("raw_response", sa.JSON(), nullable=True, comment="响应快照"),
            sa.Column("paid_at", sa.DateTime(), nullable=True, comment="支付成功时间"),
            *_base_columns(),
            sa.ForeignKeyConstraint(["order_id"], ["payment_order.id"], ondelete="CASCADE", onupdate="CASCADE"),
        )
        _base_indexes("payment_record")
        _add_indexes("payment_record", ["order_id", "channel", "payment_status", "merchant_trade_no", "channel_trade_no", "paid_at"], ["payment_no"])

    if "payment_callback_log" not in existing_tables:
        op.create_table(
            "payment_callback_log",
            sa.Column("channel", sa.String(length=32), nullable=False, comment="支付渠道"),
            sa.Column("merchant_trade_no", sa.String(length=64), nullable=True, comment="商户订单号"),
            sa.Column("channel_trade_no", sa.String(length=128), nullable=True, comment="渠道交易号"),
            sa.Column("payload", sa.JSON(), nullable=True, comment="回调原文"),
            sa.Column("signature", sa.Text(), nullable=True, comment="签名"),
            sa.Column("verify_result", sa.Boolean(), nullable=False, comment="验签结果"),
            sa.Column("process_status", sa.String(length=32), nullable=False, comment="处理状态"),
            sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
            sa.Column("received_at", sa.DateTime(), nullable=False, comment="接收时间"),
            sa.Column("processed_at", sa.DateTime(), nullable=True, comment="处理时间"),
            *_base_columns(),
        )
        _base_indexes("payment_callback_log")
        _add_indexes("payment_callback_log", ["channel", "merchant_trade_no", "channel_trade_no", "process_status", "received_at", "processed_at"])

    if "payment_refund" not in existing_tables:
        op.create_table(
            "payment_refund",
            sa.Column("order_id", sa.Integer(), nullable=False, comment="订单ID"),
            sa.Column("payment_id", sa.Integer(), nullable=True, comment="支付流水ID"),
            sa.Column("refund_no", sa.String(length=32), nullable=False, comment="退款单号"),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False, comment="退款金额"),
            sa.Column("refund_status", sa.String(length=32), nullable=False, comment="退款状态"),
            sa.Column("reason", sa.String(length=255), nullable=True, comment="退款原因"),
            sa.Column("raw_response", sa.JSON(), nullable=True, comment="渠道响应"),
            *_base_columns(),
            *_user_columns(),
            sa.ForeignKeyConstraint(["order_id"], ["payment_order.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["payment_id"], ["payment_record.id"], ondelete="SET NULL", onupdate="CASCADE"),
        )
        _base_indexes("payment_refund")
        _add_indexes("payment_refund", ["order_id", "payment_id", "refund_status", "created_id", "updated_id", "deleted_id"], ["refund_no"])

    if "event" not in existing_tables:
        op.create_table(
            "event",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("store_id", sa.Integer(), nullable=False, comment="归属门店ID"),
            sa.Column("title", sa.String(length=128), nullable=False, comment="活动标题"),
            sa.Column("subtitle", sa.String(length=255), nullable=True, comment="活动副标题"),
            sa.Column("event_type", sa.String(length=32), nullable=False, comment="活动类型"),
            sa.Column("cover_url", sa.String(length=500), nullable=True, comment="封面图URL"),
            sa.Column("location", sa.String(length=255), nullable=False, comment="活动地点"),
            sa.Column("start_time", sa.DateTime(), nullable=False, comment="开始时间"),
            sa.Column("end_time", sa.DateTime(), nullable=False, comment="结束时间"),
            sa.Column("register_deadline", sa.DateTime(), nullable=False, comment="报名截止时间"),
            sa.Column("detail_html", sa.Text(), nullable=True, comment="活动详情富文本"),
            sa.Column("effect_html", sa.Text(), nullable=True, comment="活动效果富文本"),
            sa.Column("male_quota", sa.Integer(), nullable=False, comment="男生名额"),
            sa.Column("female_quota", sa.Integer(), nullable=False, comment="女生名额"),
            sa.Column("male_fee", sa.Numeric(12, 2), nullable=False, comment="男生费用"),
            sa.Column("female_fee", sa.Numeric(12, 2), nullable=False, comment="女生费用"),
            sa.Column("vip_free", sa.Boolean(), nullable=False, comment="VIP是否免费"),
            sa.Column("require_realname", sa.Boolean(), nullable=False, comment="是否要求实名"),
            sa.Column("min_age", sa.Integer(), nullable=True, comment="最小年龄"),
            sa.Column("max_age", sa.Integer(), nullable=True, comment="最大年龄"),
            sa.Column("event_status", sa.String(length=32), nullable=False, comment="活动状态"),
            sa.Column("published_by", sa.Integer(), nullable=True, comment="发布人ID"),
            sa.Column("published_at", sa.DateTime(), nullable=True, comment="发布时间"),
            *_base_columns(),
            *_user_columns(),
            sa.ForeignKeyConstraint(["store_id"], ["sys_dept.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["published_by"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        )
        _base_indexes("event")
        _add_indexes(
            "event",
            ["brand_id", "store_id", "title", "event_type", "start_time", "end_time", "register_deadline", "event_status", "published_by", "published_at", "created_id", "updated_id", "deleted_id"],
        )

    if "event_registration" not in existing_tables:
        op.create_table(
            "event_registration",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("event_id", sa.Integer(), nullable=False, comment="活动ID"),
            sa.Column("mp_user_id", sa.Integer(), nullable=False, comment="小程序用户ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("registration_no", sa.String(length=32), nullable=False, comment="报名编号"),
            sa.Column("gender_snapshot", sa.String(length=1), nullable=False, comment="性别快照"),
            sa.Column("payable_amount", sa.Numeric(12, 2), nullable=False, comment="应付金额"),
            sa.Column("paid_amount", sa.Numeric(12, 2), nullable=False, comment="实付金额"),
            sa.Column("order_id", sa.Integer(), nullable=True, comment="支付订单ID"),
            sa.Column("registration_status", sa.String(length=32), nullable=False, comment="报名状态"),
            sa.Column("registered_at", sa.DateTime(), nullable=False, comment="报名时间"),
            sa.Column("payment_expire_at", sa.DateTime(), nullable=True, comment="支付超时时间"),
            sa.Column("source_event_id", sa.Integer(), nullable=True, comment="报名成功来源事件ID"),
            *_base_columns(),
            sa.ForeignKeyConstraint(["event_id"], ["event.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["mp_user_id"], ["mini_program_user.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["order_id"], ["payment_order.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.UniqueConstraint("event_id", "mp_user_id", name="uq_event_registration_event_user"),
        )
        _base_indexes("event_registration")
        _add_indexes(
            "event_registration",
            ["brand_id", "event_id", "mp_user_id", "person_id", "gender_snapshot", "order_id", "registration_status", "registered_at", "payment_expire_at", "source_event_id"],
            ["registration_no"],
        )

    if "event_participant" not in existing_tables:
        op.create_table(
            "event_participant",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("event_id", sa.Integer(), nullable=False, comment="活动ID"),
            sa.Column("registration_id", sa.Integer(), nullable=True, comment="报名ID"),
            sa.Column("mp_user_id", sa.Integer(), nullable=False, comment="小程序用户ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("onsite_no", sa.String(length=32), nullable=False, comment="现场编号"),
            sa.Column("display_nickname", sa.String(length=64), nullable=True, comment="展示昵称"),
            sa.Column("gender_snapshot", sa.String(length=1), nullable=False, comment="性别快照"),
            sa.Column("profile_snapshot", sa.JSON(), nullable=True, comment="资料快照"),
            sa.Column("checkin_type", sa.String(length=32), nullable=False, comment="签到类型"),
            sa.Column("checked_in_at", sa.DateTime(), nullable=False, comment="签到时间"),
            sa.Column("participant_status", sa.String(length=32), nullable=False, comment="参会状态"),
            sa.Column("source_event_id", sa.Integer(), nullable=True, comment="签到来源事件ID"),
            *_base_columns(),
            sa.ForeignKeyConstraint(["event_id"], ["event.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["registration_id"], ["event_registration.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["mp_user_id"], ["mini_program_user.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.UniqueConstraint("event_id", "mp_user_id", name="uq_event_participant_event_user"),
        )
        _base_indexes("event_participant")
        _add_indexes(
            "event_participant",
            ["brand_id", "event_id", "registration_id", "mp_user_id", "person_id", "gender_snapshot", "checkin_type", "checked_in_at", "participant_status", "source_event_id"],
            ["onsite_no"],
        )


def downgrade() -> None:
    for table_name in [
        "event_participant",
        "event_registration",
        "event",
        "payment_refund",
        "payment_callback_log",
        "payment_record",
        "payment_order",
    ]:
        if table_name in _tables():
            op.drop_table(table_name)
