"""create user quick login device

Revision ID: 20260520_1100
Revises: 20260520_1000
Create Date: 2026-05-20 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260520_1100"
down_revision: str | None = "20260520_1000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _indexes(table_name: str) -> set[str]:
    return {row["name"] for row in sa.inspect(op.get_bind()).get_indexes(table_name)}


def _create_index(table_name: str, column: str, unique: bool = False) -> None:
    index_name = f"ix_{table_name}_{column}"
    if index_name not in _indexes(table_name):
        op.create_index(index_name, table_name, [column], unique=unique)


def upgrade() -> None:
    table_name = "sys_user_quick_login_device"
    if table_name not in _tables():
        op.create_table(
            table_name,
            sa.Column("user_id", sa.Integer(), nullable=False, comment="用户ID"),
            sa.Column("token_hash", sa.String(length=128), nullable=False, comment="快速登录凭证哈希"),
            sa.Column("expires_at", sa.DateTime(), nullable=False, comment="过期时间"),
            sa.Column("last_used_at", sa.DateTime(), nullable=True, comment="最近使用时间"),
            sa.Column("revoked_at", sa.DateTime(), nullable=True, comment="撤销时间"),
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
            sa.Column("uuid", sa.String(length=64), nullable=False, comment="UUID全局唯一标识"),
            sa.Column("status", sa.String(length=10), nullable=False, comment="状态(0:正常 1:禁用)"),
            sa.Column("description", sa.Text(), nullable=True, comment="备注/描述"),
            sa.Column("created_time", sa.DateTime(), nullable=False, comment="创建时间"),
            sa.Column("updated_time", sa.DateTime(), nullable=False, comment="更新时间"),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, comment="是否已删除(0:未删除 1:已删除)"),
            sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
            sa.ForeignKeyConstraint(["user_id"], ["sys_user.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("uuid"),
            sa.UniqueConstraint("token_hash"),
            comment="用户本机快速登录凭证表",
        )

    for column in [
        "user_id",
        "token_hash",
        "expires_at",
        "last_used_at",
        "revoked_at",
        "uuid",
        "status",
        "created_time",
        "updated_time",
        "is_deleted",
        "deleted_time",
    ]:
        _create_index(table_name, column, unique=column == "token_hash")

    op.execute(
        sa.text(
            """
            UPDATE sys_param
            SET config_value = :config_value
            WHERE config_key = 'white_api_list_path'
            """
        ).bindparams(
            config_value=(
                '["/api/v1/system/auth/login", '
                '"/api/v1/system/auth/token/refresh", '
                '"/api/v1/system/auth/captcha/get", '
                '"/api/v1/system/auth/logout", '
                '"/api/v1/system/config/info", '
                '"/api/v1/system/user/current/info", '
                '"/api/v1/system/notice/available", '
                '"/api/v1/system/auth/auto-login/device", '
                '"/api/v1/system/auth/auto-login"]'
            )
        )
    )


def downgrade() -> None:
    table_name = "sys_user_quick_login_device"
    if table_name in _tables():
        op.drop_table(table_name)
