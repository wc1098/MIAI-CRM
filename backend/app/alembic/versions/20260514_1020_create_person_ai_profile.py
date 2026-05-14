"""create person ai profile

Revision ID: 20260514_1020
Revises: 20260514_1010
Create Date: 2026-05-14 10:20:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20260514_1020"
down_revision: str | None = "20260514_1010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tables = _tables()
    if "person_ai_profile" not in tables:
        op.create_table(
            "person_ai_profile",
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("profile_type", sa.String(length=32), nullable=False, comment="画像类型"),
            sa.Column("source_type", sa.String(length=32), nullable=False, comment="来源类型"),
            sa.Column("source_id", sa.String(length=128), nullable=True, comment="来源对象ID"),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="10", comment="优先级"),
            sa.Column("content", sa.Text(), nullable=True, comment="画像内容"),
            sa.Column("input_snapshot", sa.JSON(), nullable=True, comment="脱敏输入快照"),
            sa.Column("model_name", sa.String(length=128), nullable=True, comment="模型名称"),
            sa.Column("generation_status", sa.String(length=16), nullable=False, server_default="pending", comment="生成状态"),
            sa.Column("is_effective", sa.Boolean(), nullable=False, server_default=sa.false(), comment="是否当前生效"),
            sa.Column("generated_at", sa.DateTime(), nullable=True, comment="生成时间"),
            sa.Column("last_error", sa.Text(), nullable=True, comment="最近错误"),
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
            sa.Column("uuid", sa.String(length=64), nullable=False, comment="UUID全局唯一标识"),
            sa.Column("status", sa.String(length=10), nullable=False, server_default="0", comment="状态(0:正常 1:禁用)"),
            sa.Column("description", sa.Text(), nullable=True, comment="备注/描述"),
            sa.Column("created_time", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="创建时间"),
            sa.Column("updated_time", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="更新时间"),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false(), comment="是否已删除(0:未删除 1:已删除)"),
            sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("uuid"),
            comment="人员AI画像结果表",
        )
        for column in [
            "person_id",
            "profile_type",
            "source_type",
            "source_id",
            "priority",
            "generation_status",
            "is_effective",
            "generated_at",
            "id",
            "uuid",
            "status",
            "created_time",
            "updated_time",
            "is_deleted",
            "deleted_time",
        ]:
            op.create_index(op.f(f"ix_person_ai_profile_{column}"), "person_ai_profile", [column], unique=False)

    if "person_ai_profile_task" not in tables:
        op.create_table(
            "person_ai_profile_task",
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("profile_type", sa.String(length=32), nullable=False, comment="画像类型"),
            sa.Column("source_type", sa.String(length=32), nullable=False, comment="来源类型"),
            sa.Column("source_id", sa.String(length=128), nullable=True, comment="来源对象ID"),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="10", comment="优先级"),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="pending", comment="任务状态"),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0", comment="重试次数"),
            sa.Column("next_retry_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="下次重试时间"),
            sa.Column("locked_at", sa.DateTime(), nullable=True, comment="锁定时间"),
            sa.Column("locked_by", sa.String(length=64), nullable=True, comment="锁定者"),
            sa.Column("last_error", sa.Text(), nullable=True, comment="最近错误"),
            sa.Column("payload_snapshot", sa.JSON(), nullable=True, comment="脱敏载荷快照"),
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
            sa.Column("uuid", sa.String(length=64), nullable=False, comment="UUID全局唯一标识"),
            sa.Column("description", sa.Text(), nullable=True, comment="备注/描述"),
            sa.Column("created_time", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="创建时间"),
            sa.Column("updated_time", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="更新时间"),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false(), comment="是否已删除(0:未删除 1:已删除)"),
            sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("uuid"),
            comment="人员AI画像生成任务表",
        )
        for column in [
            "person_id",
            "profile_type",
            "source_type",
            "source_id",
            "priority",
            "status",
            "next_retry_at",
            "locked_at",
            "locked_by",
            "id",
            "uuid",
            "created_time",
            "updated_time",
            "is_deleted",
            "deleted_time",
        ]:
            op.create_index(op.f(f"ix_person_ai_profile_task_{column}"), "person_ai_profile_task", [column], unique=False)


def downgrade() -> None:
    tables = _tables()
    if "person_ai_profile_task" in tables:
        op.drop_table("person_ai_profile_task")
    if "person_ai_profile" in tables:
        op.drop_table("person_ai_profile")
