"""create crm channel

Revision ID: 20260511_0130
Revises: 20260511_0010
Create Date: 2026-05-11 01:30:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260511_0130"
down_revision: Union[str, None] = "20260511_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crm_channel",
        sa.Column("channel_code", sa.String(length=64), nullable=False, comment="渠道编码"),
        sa.Column("channel_name", sa.String(length=64), nullable=False, comment="渠道名称"),
        sa.Column("channel_type", sa.String(length=32), nullable=False, comment="渠道类型"),
        sa.Column("source_system", sa.String(length=64), nullable=True, comment="来源系统"),
        sa.Column("external_code", sa.String(length=128), nullable=True, comment="外部渠道编码"),
        sa.Column("landing_url", sa.String(length=500), nullable=True, comment="落地页/投放页链接"),
        sa.Column("sort", sa.Integer(), nullable=False, comment="排序"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("uuid", sa.String(length=64), nullable=False, comment="UUID全局唯一标识"),
        sa.Column("status", sa.String(length=10), nullable=False, comment="状态(0:正常 1:禁用)"),
        sa.Column("description", sa.Text(), nullable=True, comment="备注/描述"),
        sa.Column("created_time", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_time", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, comment="是否已删除(0:未删除 1:已删除)"),
        sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
        sa.Column("created_id", sa.Integer(), nullable=True, comment="创建人ID"),
        sa.Column("updated_id", sa.Integer(), nullable=True, comment="更新人ID"),
        sa.Column("deleted_id", sa.Integer(), nullable=True, comment="删除人ID"),
        sa.ForeignKeyConstraint(["created_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["deleted_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["updated_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        comment="CRM渠道表",
    )
    op.create_index(op.f("ix_crm_channel_channel_code"), "crm_channel", ["channel_code"], unique=True)
    op.create_index(op.f("ix_crm_channel_channel_type"), "crm_channel", ["channel_type"], unique=False)
    op.create_index(op.f("ix_crm_channel_created_id"), "crm_channel", ["created_id"], unique=False)
    op.create_index(op.f("ix_crm_channel_created_time"), "crm_channel", ["created_time"], unique=False)
    op.create_index(op.f("ix_crm_channel_deleted_id"), "crm_channel", ["deleted_id"], unique=False)
    op.create_index(op.f("ix_crm_channel_deleted_time"), "crm_channel", ["deleted_time"], unique=False)
    op.create_index(op.f("ix_crm_channel_external_code"), "crm_channel", ["external_code"], unique=False)
    op.create_index(op.f("ix_crm_channel_id"), "crm_channel", ["id"], unique=False)
    op.create_index(op.f("ix_crm_channel_is_deleted"), "crm_channel", ["is_deleted"], unique=False)
    op.create_index(op.f("ix_crm_channel_source_system"), "crm_channel", ["source_system"], unique=False)
    op.create_index(op.f("ix_crm_channel_status"), "crm_channel", ["status"], unique=False)
    op.create_index(op.f("ix_crm_channel_updated_id"), "crm_channel", ["updated_id"], unique=False)
    op.create_index(op.f("ix_crm_channel_updated_time"), "crm_channel", ["updated_time"], unique=False)
    op.create_index(op.f("ix_crm_channel_uuid"), "crm_channel", ["uuid"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_crm_channel_uuid"), table_name="crm_channel")
    op.drop_index(op.f("ix_crm_channel_updated_time"), table_name="crm_channel")
    op.drop_index(op.f("ix_crm_channel_updated_id"), table_name="crm_channel")
    op.drop_index(op.f("ix_crm_channel_status"), table_name="crm_channel")
    op.drop_index(op.f("ix_crm_channel_source_system"), table_name="crm_channel")
    op.drop_index(op.f("ix_crm_channel_is_deleted"), table_name="crm_channel")
    op.drop_index(op.f("ix_crm_channel_id"), table_name="crm_channel")
    op.drop_index(op.f("ix_crm_channel_external_code"), table_name="crm_channel")
    op.drop_index(op.f("ix_crm_channel_deleted_time"), table_name="crm_channel")
    op.drop_index(op.f("ix_crm_channel_deleted_id"), table_name="crm_channel")
    op.drop_index(op.f("ix_crm_channel_created_time"), table_name="crm_channel")
    op.drop_index(op.f("ix_crm_channel_created_id"), table_name="crm_channel")
    op.drop_index(op.f("ix_crm_channel_channel_type"), table_name="crm_channel")
    op.drop_index(op.f("ix_crm_channel_channel_code"), table_name="crm_channel")
    op.drop_table("crm_channel")
