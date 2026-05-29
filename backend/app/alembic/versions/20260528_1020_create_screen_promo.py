"""create screen promo

Revision ID: 20260528_1020
Revises: 20260528_1010
Create Date: 2026-05-28 10:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260528_1020"
down_revision: str | None = "20260528_1010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _mixin_columns(with_user: bool = False) -> list[sa.Column]:
    columns = [
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("uuid", sa.String(length=64), nullable=False, comment="UUID全局唯一标识"),
        sa.Column("status", sa.String(length=10), nullable=False, comment="状态(0:正常 1:禁用)"),
        sa.Column("description", sa.Text(), nullable=True, comment="备注/描述"),
        sa.Column("created_time", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_time", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, comment="是否已删除(0:未删除 1:已删除)"),
        sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
    ]
    if with_user:
        columns.extend(
            [
                sa.Column("created_id", sa.Integer(), nullable=True, comment="创建人ID"),
                sa.Column("updated_id", sa.Integer(), nullable=True, comment="更新人ID"),
                sa.Column("deleted_id", sa.Integer(), nullable=True, comment="删除人ID"),
            ]
        )
    return columns


def _user_constraints() -> list[sa.ForeignKeyConstraint]:
    return [
        sa.ForeignKeyConstraint(["created_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["updated_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["deleted_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
    ]


def upgrade() -> None:
    tables = _tables()
    if "screen_promo_config" not in tables:
        op.create_table(
            "screen_promo_config",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("enabled", sa.Boolean(), nullable=False, comment="是否启用"),
            sa.Column("image_duration_seconds", sa.Integer(), nullable=False, comment="默认图片轮播秒数"),
            sa.Column("staff_duration_seconds", sa.Integer(), nullable=False, comment="默认员工轮播秒数"),
            sa.Column("sync_interval_seconds", sa.Integer(), nullable=False, comment="安卓同步间隔秒数"),
            sa.Column("cache_limit_gb", sa.Integer(), nullable=False, comment="安卓缓存上限GB"),
            *_mixin_columns(with_user=True),
            *_user_constraints(),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("brand_id", name="uq_screen_promo_config_brand"),
            sa.UniqueConstraint("uuid"),
            comment="宣传大屏配置表",
        )
    if "screen_promo_staff" not in tables:
        op.create_table(
            "screen_promo_staff",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("avatar_url", sa.String(length=1000), nullable=True, comment="头像/形象照URL"),
            sa.Column("display_name", sa.String(length=64), nullable=False, comment="展示姓名/花名"),
            sa.Column("role_title", sa.String(length=128), nullable=True, comment="岗位"),
            sa.Column("years_experience", sa.Integer(), nullable=True, comment="从业年限"),
            sa.Column("specialties", sa.String(length=500), nullable=True, comment="擅长方向"),
            sa.Column("service_slogan", sa.Text(), nullable=True, comment="服务宣言"),
            sa.Column("public_tags", sa.JSON(), nullable=True, comment="公开成绩/标签"),
            sa.Column("sort", sa.Integer(), nullable=False, comment="排序"),
            *_mixin_columns(with_user=True),
            *_user_constraints(),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("uuid"),
            comment="宣传大屏员工展示资料表",
        )
    if "screen_promo_item" not in tables:
        op.create_table(
            "screen_promo_item",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("item_type", sa.String(length=16), nullable=False, comment="类型:image/video/staff"),
            sa.Column("title", sa.String(length=128), nullable=False, comment="标题"),
            sa.Column("file_url", sa.String(length=1000), nullable=True, comment="素材URL"),
            sa.Column("cover_url", sa.String(length=1000), nullable=True, comment="封面URL"),
            sa.Column("file_hash", sa.String(length=128), nullable=True, comment="文件Hash"),
            sa.Column("file_size", sa.BigInteger(), nullable=True, comment="文件大小"),
            sa.Column("version", sa.Integer(), nullable=False, comment="素材版本"),
            sa.Column("duration_seconds", sa.Integer(), nullable=True, comment="展示秒数"),
            sa.Column("sort", sa.Integer(), nullable=False, comment="排序"),
            sa.Column("staff_id", sa.Integer(), nullable=True, comment="员工资料ID"),
            *_mixin_columns(with_user=True),
            sa.ForeignKeyConstraint(["staff_id"], ["screen_promo_staff.id"], ondelete="SET NULL", onupdate="CASCADE"),
            *_user_constraints(),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("uuid"),
            comment="宣传大屏播放序列表",
        )
    if "screen_promo_record" not in tables:
        op.create_table(
            "screen_promo_record",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("device_id", sa.Integer(), nullable=False, comment="设备ID"),
            sa.Column("item_id", sa.Integer(), nullable=True, comment="播放项ID"),
            sa.Column("item_type", sa.String(length=16), nullable=False, comment="播放项类型"),
            sa.Column("play_result", sa.String(length=32), nullable=False, comment="播放结果"),
            sa.Column("duration_seconds", sa.Integer(), nullable=True, comment="播放秒数"),
            sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
            sa.Column("played_at", sa.DateTime(), nullable=False, comment="播放时间"),
            *_mixin_columns(),
            sa.ForeignKeyConstraint(["device_id"], ["screen_device.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["item_id"], ["screen_promo_item.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("uuid"),
            comment="宣传大屏播放记录表",
        )
    if "screen_promo_cache_report" not in tables:
        op.create_table(
            "screen_promo_cache_report",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("device_id", sa.Integer(), nullable=False, comment="设备ID"),
            sa.Column("item_id", sa.Integer(), nullable=True, comment="播放项ID"),
            sa.Column("version", sa.Integer(), nullable=False, comment="素材版本"),
            sa.Column("cache_status", sa.String(length=32), nullable=False, comment="缓存状态"),
            sa.Column("local_path", sa.String(length=1000), nullable=True, comment="本地路径"),
            sa.Column("downloaded_bytes", sa.BigInteger(), nullable=True, comment="已下载字节"),
            sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
            sa.Column("reported_at", sa.DateTime(), nullable=False, comment="上报时间"),
            *_mixin_columns(),
            sa.ForeignKeyConstraint(["device_id"], ["screen_device.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["item_id"], ["screen_promo_item.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("uuid"),
            comment="宣传大屏缓存状态表",
        )


def downgrade() -> None:
    for table in [
        "screen_promo_cache_report",
        "screen_promo_record",
        "screen_promo_item",
        "screen_promo_staff",
        "screen_promo_config",
    ]:
        if table in _tables():
            op.drop_table(table)
