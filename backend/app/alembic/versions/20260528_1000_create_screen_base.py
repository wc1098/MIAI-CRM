"""create screen base

Revision ID: 20260528_1000
Revises: 20260527_1100
Create Date: 2026-05-28 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260528_1000"
down_revision: str | None = "20260527_1100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tables = _tables()
    if "screen_device" not in tables:
        op.create_table(
            "screen_device",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("store_id", sa.Integer(), nullable=True, comment="绑定门店ID"),
            sa.Column("device_code", sa.String(length=32), nullable=False, comment="设备码"),
            sa.Column("device_name", sa.String(length=128), nullable=True, comment="设备名称"),
            sa.Column("device_type", sa.String(length=32), nullable=False, comment="设备类型"),
            sa.Column("device_token_hash", sa.String(length=128), nullable=True, comment="设备Token哈希"),
            sa.Column("bind_status", sa.String(length=32), nullable=False, comment="绑定状态"),
            sa.Column("online_status", sa.String(length=32), nullable=False, comment="在线状态"),
            sa.Column("bound_by", sa.Integer(), nullable=True, comment="绑定人ID"),
            sa.Column("bound_at", sa.DateTime(), nullable=True, comment="绑定时间"),
            sa.Column("last_online_at", sa.DateTime(), nullable=True, comment="最近在线时间"),
            sa.Column("last_sync_at", sa.DateTime(), nullable=True, comment="最近同步时间"),
            sa.Column("app_version", sa.String(length=64), nullable=True, comment="应用版本"),
            sa.Column("system_info", sa.JSON(), nullable=True, comment="设备系统信息"),
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
            sa.ForeignKeyConstraint(["bound_by"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["created_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["deleted_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["store_id"], ["sys_dept.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["updated_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("device_code", name="uq_screen_device_code"),
            sa.UniqueConstraint("uuid"),
            comment="大屏设备表",
        )
    if "screen_user_wall_config" not in tables:
        op.create_table(
            "screen_user_wall_config",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("title", sa.String(length=128), nullable=False, comment="标题"),
            sa.Column("user_switch_seconds", sa.Integer(), nullable=False, comment="用户轮播秒数"),
            sa.Column("photo_switch_seconds", sa.Integer(), nullable=False, comment="多图切换秒数"),
            sa.Column("sort_strategy", sa.String(length=32), nullable=False, comment="排序策略"),
            sa.Column("filter_config", sa.JSON(), nullable=True, comment="筛选配置"),
            sa.Column("qr_action", sa.String(length=32), nullable=False, comment="二维码动作"),
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
            sa.UniqueConstraint("brand_id", name="uq_screen_user_wall_config_brand"),
            sa.UniqueConstraint("uuid"),
            comment="大屏用户墙配置表",
        )
    if "screen_user_wall_qrcode" not in tables:
        op.create_table(
            "screen_user_wall_qrcode",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("display_no", sa.String(length=32), nullable=False, comment="展示编号"),
            sa.Column("page_path", sa.String(length=255), nullable=False, comment="小程序页面路径"),
            sa.Column("scene", sa.String(length=128), nullable=False, comment="小程序码场景值"),
            sa.Column("file_url", sa.String(length=1000), nullable=False, comment="文件URL"),
            sa.Column("file_path", sa.String(length=1000), nullable=True, comment="文件路径"),
            sa.Column("generated_at", sa.DateTime(), nullable=False, comment="生成时间"),
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
            sa.Column("uuid", sa.String(length=64), nullable=False, comment="UUID全局唯一标识"),
            sa.Column("status", sa.String(length=10), nullable=False, comment="状态(0:正常 1:禁用)"),
            sa.Column("description", sa.Text(), nullable=True, comment="备注/描述"),
            sa.Column("created_time", sa.DateTime(), nullable=False, comment="创建时间"),
            sa.Column("updated_time", sa.DateTime(), nullable=False, comment="更新时间"),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, comment="是否已删除(0:未删除 1:已删除)"),
            sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("person_id", "display_no", "page_path", name="uq_screen_user_wall_qrcode_target"),
            sa.UniqueConstraint("uuid"),
            comment="大屏用户墙小程序码缓存表",
        )
    if "screen_user_wall_record" not in tables:
        op.create_table(
            "screen_user_wall_record",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("device_id", sa.Integer(), nullable=False, comment="设备ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="展示人员ID"),
            sa.Column("user_id", sa.Integer(), nullable=True, comment="小程序用户ID"),
            sa.Column("display_no", sa.String(length=32), nullable=True, comment="展示编号"),
            sa.Column("display_snapshot", sa.JSON(), nullable=True, comment="展示快照"),
            sa.Column("displayed_at", sa.DateTime(), nullable=False, comment="展示时间"),
            sa.Column("duration_seconds", sa.Integer(), nullable=True, comment="展示秒数"),
            sa.Column("play_result", sa.String(length=32), nullable=False, comment="播放结果"),
            sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
            sa.Column("uuid", sa.String(length=64), nullable=False, comment="UUID全局唯一标识"),
            sa.Column("status", sa.String(length=10), nullable=False, comment="状态(0:正常 1:禁用)"),
            sa.Column("description", sa.Text(), nullable=True, comment="备注/描述"),
            sa.Column("created_time", sa.DateTime(), nullable=False, comment="创建时间"),
            sa.Column("updated_time", sa.DateTime(), nullable=False, comment="更新时间"),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, comment="是否已删除(0:未删除 1:已删除)"),
            sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
            sa.ForeignKeyConstraint(["device_id"], ["screen_device.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["mini_program_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("uuid"),
            comment="大屏用户墙播放记录表",
        )


def downgrade() -> None:
    for table in ["screen_user_wall_record", "screen_user_wall_qrcode", "screen_user_wall_config", "screen_device"]:
        if table in _tables():
            op.drop_table(table)
