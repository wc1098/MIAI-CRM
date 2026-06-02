"""create screen activity barrage

Revision ID: 20260602_1000
Revises: 20260531_1010
Create Date: 2026-06-02 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260602_1000"
down_revision: str | None = "20260531_1010"
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
    ]


def upgrade() -> None:
    if "screen_activity_barrage" in _tables():
        return
    op.create_table(
        "screen_activity_barrage",
        sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
        sa.Column("store_id", sa.Integer(), nullable=True, comment="门店ID"),
        sa.Column("activity_id", sa.Integer(), nullable=False, comment="活动大屏ID"),
        sa.Column("event_id", sa.Integer(), nullable=False, comment="活动ID"),
        sa.Column("mp_user_id", sa.Integer(), nullable=True, comment="小程序用户ID"),
        sa.Column("person_id", sa.Integer(), nullable=True, comment="人员ID"),
        sa.Column("nickname", sa.String(length=64), nullable=True, comment="展示昵称"),
        sa.Column("avatar_url", sa.String(length=1000), nullable=True, comment="头像URL"),
        sa.Column("content", sa.String(length=200), nullable=False, comment="弹幕内容"),
        sa.Column("display_status", sa.String(length=32), nullable=False, comment="展示状态"),
        sa.Column("displayed_at", sa.DateTime(), nullable=True, comment="展示时间"),
        *_mixin_columns(),
        sa.ForeignKeyConstraint(["store_id"], ["sys_dept.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["activity_id"], ["screen_activity_config.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["event.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["mp_user_id"], ["mini_program_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
        comment="活动大屏普通弹幕记录表",
    )
    for column in ["brand_id", "store_id", "activity_id", "event_id", "mp_user_id", "person_id", "display_status", "displayed_at"]:
        op.create_index(f"ix_screen_activity_barrage_{column}", "screen_activity_barrage", [column])


def downgrade() -> None:
    if "screen_activity_barrage" in _tables():
        op.drop_table("screen_activity_barrage")
