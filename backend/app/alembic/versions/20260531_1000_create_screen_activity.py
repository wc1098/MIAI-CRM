"""create screen activity

Revision ID: 20260531_1000
Revises: 20260529_1020
Create Date: 2026-05-31 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260531_1000"
down_revision: str | None = "20260529_1020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _mixin_columns() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    if "screen_activity_config" in _tables():
        return
    op.create_table(
        "screen_activity_config",
        sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
        sa.Column("store_id", sa.Integer(), nullable=True, comment="门店ID"),
        sa.Column("event_id", sa.Integer(), nullable=False, comment="活动ID"),
        sa.Column("screen_name", sa.String(length=128), nullable=True, comment="大屏名称"),
        sa.Column("title", sa.String(length=128), nullable=True, comment="大屏标题"),
        sa.Column("subtitle", sa.String(length=255), nullable=True, comment="大屏副标题"),
        sa.Column("background_url", sa.String(length=1000), nullable=True, comment="背景图URL"),
        sa.Column("theme_config", sa.JSON(), nullable=True, comment="画面配置"),
        sa.Column("module_config", sa.JSON(), nullable=True, comment="功能模块配置"),
        sa.Column("enabled", sa.Boolean(), nullable=False, comment="是否启用"),
        sa.Column("current_scene", sa.String(length=32), nullable=False, comment="当前场景:home/checkin"),
        sa.Column("show_qrcode", sa.Boolean(), nullable=False, comment="是否显示二维码"),
        sa.Column("qrcode_url", sa.String(length=1000), nullable=True, comment="小程序码URL"),
        sa.Column("qrcode_file_path", sa.String(length=1000), nullable=True, comment="小程序码文件路径"),
        sa.Column("qrcode_page", sa.String(length=255), nullable=False, comment="小程序码页面"),
        sa.Column("checkin_scene", sa.String(length=64), nullable=False, comment="扫码签到场景值"),
        sa.Column("qrcode_generated_at", sa.DateTime(), nullable=True, comment="二维码生成时间"),
        sa.Column("last_command", sa.JSON(), nullable=True, comment="最近遥控命令"),
        sa.Column("last_command_at", sa.DateTime(), nullable=True, comment="最近遥控时间"),
        *_mixin_columns(),
        sa.ForeignKeyConstraint(["store_id"], ["sys_dept.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["event.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["created_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["updated_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["deleted_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
        sa.UniqueConstraint("event_id", name="uq_screen_activity_config_event"),
        sa.UniqueConstraint("checkin_scene", name="uq_screen_activity_config_scene"),
        comment="活动大屏配置表",
    )
    for column in ["brand_id", "store_id", "event_id", "enabled", "current_scene", "checkin_scene", "qrcode_generated_at", "last_command_at"]:
        op.create_index(f"ix_screen_activity_config_{column}", "screen_activity_config", [column])


def downgrade() -> None:
    if "screen_activity_config" in _tables():
        op.drop_table("screen_activity_config")
