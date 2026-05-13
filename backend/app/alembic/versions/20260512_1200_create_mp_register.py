"""create mini program register

Revision ID: 20260512_1200
Revises: 20260512_1100
Create Date: 2026-05-12 12:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20260512_1200"
down_revision: str | None = "20260512_1100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    return {index["name"] for index in inspect(op.get_bind()).get_indexes(table_name)}


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


def _create_index_if_missing(table_name: str, column_name: str, unique: bool = False) -> None:
    index_name = op.f(f"ix_{table_name}_{column_name}")
    if index_name not in _indexes(table_name):
        op.create_index(index_name, table_name, [column_name], unique=unique)


def _base_indexes(table_name: str) -> None:
    for column in ["created_time", "deleted_time", "id", "is_deleted", "status", "updated_time"]:
        _create_index_if_missing(table_name, column)
    _create_index_if_missing(table_name, "uuid", unique=True)


def _drop_index_if_exists(table_name: str, column_name: str) -> None:
    index_name = op.f(f"ix_{table_name}_{column_name}")
    if index_name in _indexes(table_name):
        op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    existing_tables = _tables()
    if "mini_program_user" not in existing_tables:
        op.create_table(
            "mini_program_user",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("person_id", sa.Integer(), nullable=True, comment="关联人员ID"),
            sa.Column("openid", sa.String(length=128), nullable=False, comment="微信openid"),
            sa.Column("unionid", sa.String(length=128), nullable=True, comment="微信unionid"),
            sa.Column("session_key", sa.String(length=255), nullable=True, comment="微信session_key"),
            sa.Column("mobile", sa.String(length=20), nullable=True, comment="微信手机号"),
            sa.Column("nickname", sa.String(length=64), nullable=True, comment="微信昵称"),
            sa.Column("avatar_url", sa.String(length=500), nullable=True, comment="微信头像"),
            sa.Column("is_invisible", sa.Boolean(), nullable=False, comment="是否隐身"),
            sa.Column("allow_user_wall", sa.Boolean(), nullable=False, comment="是否允许上墙"),
            sa.Column("registered_at", sa.DateTime(), nullable=True, comment="注册时间"),
            sa.Column("last_login_at", sa.DateTime(), nullable=True, comment="最近登录时间"),
            *_base_columns(),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="SET NULL", onupdate="CASCADE"),
        )
        _base_indexes("mini_program_user")
        for column_name, unique in [
            ("brand_id", False),
            ("person_id", False),
            ("openid", True),
            ("unionid", False),
            ("mobile", True),
            ("registered_at", False),
            ("last_login_at", False),
        ]:
            _create_index_if_missing("mini_program_user", column_name, unique=unique)

    if "user_agreement_acceptance" not in existing_tables:
        op.create_table(
            "user_agreement_acceptance",
            sa.Column("user_id", sa.Integer(), nullable=False, comment="小程序用户ID"),
            sa.Column("agreement_type", sa.String(length=32), nullable=False, comment="协议类型"),
            sa.Column("agreement_version", sa.String(length=32), nullable=False, comment="协议版本"),
            sa.Column("agreement_title", sa.String(length=128), nullable=False, comment="协议标题快照"),
            sa.Column("accepted_at", sa.DateTime(), nullable=False, comment="同意时间"),
            sa.Column("ip", sa.String(length=64), nullable=True, comment="IP"),
            sa.Column("device_info", sa.String(length=255), nullable=True, comment="设备信息"),
            *_base_columns(),
            sa.ForeignKeyConstraint(["user_id"], ["mini_program_user.id"], ondelete="CASCADE", onupdate="CASCADE"),
        )
        _base_indexes("user_agreement_acceptance")
        for column_name in ["user_id", "agreement_type", "accepted_at"]:
            _create_index_if_missing("user_agreement_acceptance", column_name)

    if "source_event" not in existing_tables:
        op.create_table(
            "source_event",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("user_id", sa.Integer(), nullable=True, comment="小程序用户ID"),
            sa.Column("event_type", sa.String(length=32), nullable=False, comment="事件类型"),
            sa.Column("source_channel", sa.String(length=64), nullable=True, comment="来源渠道"),
            sa.Column("source_id", sa.String(length=128), nullable=True, comment="来源对象ID"),
            sa.Column("source_user_id", sa.Integer(), nullable=True, comment="分享来源用户ID"),
            sa.Column("store_id", sa.Integer(), nullable=True, comment="门店ID"),
            sa.Column("payload", sa.JSON(), nullable=True, comment="原始来源参数"),
            sa.Column("occurred_at", sa.DateTime(), nullable=False, comment="发生时间"),
            *_base_columns(),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["mini_program_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["store_id"], ["sys_dept.id"], ondelete="SET NULL", onupdate="CASCADE"),
        )
        _base_indexes("source_event")
        for column_name in [
            "brand_id",
            "person_id",
            "user_id",
            "event_type",
            "source_channel",
            "source_id",
            "source_user_id",
            "store_id",
            "occurred_at",
        ]:
            _create_index_if_missing("source_event", column_name)

    if "latest_source_event_id" not in _columns("crm_lead_profile"):
        op.add_column("crm_lead_profile", sa.Column("latest_source_event_id", sa.Integer(), nullable=True, comment="最近来源事件ID"))
        _create_index_if_missing("crm_lead_profile", "latest_source_event_id")


def downgrade() -> None:
    if "crm_lead_profile" in _tables() and "latest_source_event_id" in _columns("crm_lead_profile"):
        _drop_index_if_exists("crm_lead_profile", "latest_source_event_id")
        op.drop_column("crm_lead_profile", "latest_source_event_id")

    for table_name in ["source_event", "user_agreement_acceptance", "mini_program_user"]:
        if table_name in _tables():
            op.drop_table(table_name)
