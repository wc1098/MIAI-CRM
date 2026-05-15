"""create mp profile unlock tables

Revision ID: 20260514_1300
Revises: 20260514_1020
Create Date: 2026-05-14 13:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "20260514_1300"
down_revision = "20260514_1020"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("uuid", sa.String(length=64), nullable=False, comment="UUID全局唯一标识"),
        sa.Column("status", sa.String(length=10), nullable=False, comment="状态(0:正常 1:禁用)"),
        sa.Column("description", sa.Text(), nullable=True, comment="备注/描述"),
        sa.Column("created_time", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_time", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, comment="是否已删除"),
        sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    ]


def _base_indexes(table: str, columns: list[str]) -> None:
    for column in ["id", "uuid", "status", "created_time", "updated_time", "is_deleted", "deleted_time", *columns]:
        op.create_index(op.f(f"ix_{table}_{column}"), table, [column], unique=False)


def upgrade() -> None:
    tables = _tables()
    if "mp_user_profile_action" not in tables:
        op.create_table(
            "mp_user_profile_action",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("viewer_user_id", sa.Integer(), nullable=True, comment="查看/操作用户ID"),
            sa.Column("viewer_person_id", sa.Integer(), nullable=True, comment="查看/操作人员ID"),
            sa.Column("target_user_id", sa.Integer(), nullable=False, comment="目标小程序用户ID"),
            sa.Column("target_person_id", sa.Integer(), nullable=False, comment="目标人员ID"),
            sa.Column("action_type", sa.String(length=32), nullable=False, comment="行为类型"),
            sa.Column("payload", sa.JSON(), nullable=True, comment="行为参数"),
            sa.Column("occurred_at", sa.DateTime(), nullable=False, comment="发生时间"),
            sa.ForeignKeyConstraint(["viewer_user_id"], ["mini_program_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["target_user_id"], ["mini_program_user.id"], ondelete="CASCADE", onupdate="CASCADE"),
            comment="小程序用户资料行为记录表",
        )
        _base_indexes("mp_user_profile_action", ["brand_id", "viewer_user_id", "viewer_person_id", "target_user_id", "target_person_id", "action_type", "occurred_at"])

    for table_name, label_time in [("mp_user_like", "liked_at"), ("mp_user_favorite", "favorited_at")]:
        if table_name not in tables:
            op.create_table(
                table_name,
                *_base_columns(),
                sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
                sa.Column("viewer_user_id", sa.Integer(), nullable=False, comment="发起用户ID"),
                sa.Column("target_user_id", sa.Integer(), nullable=False, comment="目标用户ID"),
                sa.Column("viewer_person_id", sa.Integer(), nullable=False, comment="发起人员ID"),
                sa.Column("target_person_id", sa.Integer(), nullable=False, comment="目标人员ID"),
                sa.Column("is_active", sa.Boolean(), nullable=False, comment="是否有效"),
                sa.Column(label_time, sa.DateTime(), nullable=True, comment="生效时间"),
                sa.Column("cancelled_at", sa.DateTime(), nullable=True, comment="取消时间"),
                sa.ForeignKeyConstraint(["viewer_user_id"], ["mini_program_user.id"], ondelete="CASCADE", onupdate="CASCADE"),
                sa.ForeignKeyConstraint(["target_user_id"], ["mini_program_user.id"], ondelete="CASCADE", onupdate="CASCADE"),
                sa.UniqueConstraint("viewer_user_id", "target_user_id", name=f"uq_{table_name}_viewer_target"),
                comment="小程序用户喜欢关系表" if table_name == "mp_user_like" else "小程序用户收藏关系表",
            )
            _base_indexes(table_name, ["brand_id", "viewer_user_id", "target_user_id", "viewer_person_id", "target_person_id", "is_active", label_time])

    if "mp_heartbeat_progress" not in tables:
        op.create_table(
            "mp_heartbeat_progress",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("viewer_user_id", sa.Integer(), nullable=False, comment="查看用户ID"),
            sa.Column("target_user_id", sa.Integer(), nullable=False, comment="目标用户ID"),
            sa.Column("viewer_person_id", sa.Integer(), nullable=False, comment="查看人员ID"),
            sa.Column("target_person_id", sa.Integer(), nullable=False, comment="目标人员ID"),
            sa.Column("score", sa.Integer(), nullable=False, comment="当前心动值"),
            sa.Column("unlocked_by_score", sa.Boolean(), nullable=False, comment="是否已用心动值解锁"),
            sa.Column("last_action_at", sa.DateTime(), nullable=True, comment="最近加分时间"),
            sa.UniqueConstraint("viewer_user_id", "target_user_id", name="uq_mp_heartbeat_progress_viewer_target"),
            comment="小程序用户心动值进度表",
        )
        _base_indexes("mp_heartbeat_progress", ["brand_id", "viewer_user_id", "target_user_id", "viewer_person_id", "target_person_id"])

    if "mp_contact_unlock" not in tables:
        op.create_table(
            "mp_contact_unlock",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("viewer_user_id", sa.Integer(), nullable=False, comment="查看用户ID"),
            sa.Column("target_user_id", sa.Integer(), nullable=False, comment="目标用户ID"),
            sa.Column("viewer_person_id", sa.Integer(), nullable=False, comment="查看人员ID"),
            sa.Column("target_person_id", sa.Integer(), nullable=False, comment="目标人员ID"),
            sa.Column("unlock_method", sa.String(length=32), nullable=False, comment="解锁方式"),
            sa.Column("unlock_status", sa.String(length=32), nullable=False, comment="解锁状态"),
            sa.Column("amount", sa.Numeric(10, 2), nullable=False, comment="应付金额"),
            sa.Column("order_id", sa.Integer(), nullable=True, comment="支付订单ID"),
            sa.Column("coupon_id", sa.Integer(), nullable=True, comment="免费券ID"),
            sa.Column("source_event_id", sa.Integer(), nullable=True, comment="来源事件ID"),
            sa.Column("unlocked_at", sa.DateTime(), nullable=True, comment="解锁时间"),
            sa.ForeignKeyConstraint(["order_id"], ["payment_order.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.UniqueConstraint("viewer_user_id", "target_user_id", name="uq_mp_contact_unlock_viewer_target"),
            comment="小程序联系方式解锁记录表",
        )
        _base_indexes("mp_contact_unlock", ["brand_id", "viewer_user_id", "target_user_id", "viewer_person_id", "target_person_id", "unlock_method", "unlock_status", "order_id", "coupon_id", "source_event_id", "unlocked_at"])

    if "mp_unlock_coupon" not in tables:
        op.create_table(
            "mp_unlock_coupon",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("user_id", sa.Integer(), nullable=False, comment="持有人小程序用户ID"),
            sa.Column("person_id", sa.Integer(), nullable=True, comment="持有人人员ID"),
            sa.Column("coupon_name", sa.String(length=64), nullable=False, comment="券名称"),
            sa.Column("coupon_status", sa.String(length=32), nullable=False, comment="券状态"),
            sa.Column("valid_from", sa.DateTime(), nullable=True, comment="有效期开始"),
            sa.Column("valid_to", sa.DateTime(), nullable=True, comment="有效期结束"),
            sa.Column("used_at", sa.DateTime(), nullable=True, comment="使用时间"),
            sa.Column("used_unlock_id", sa.Integer(), nullable=True, comment="使用解锁记录ID"),
            sa.Column("grant_reason", sa.Text(), nullable=True, comment="发放原因"),
            sa.ForeignKeyConstraint(["user_id"], ["mini_program_user.id"], ondelete="CASCADE", onupdate="CASCADE"),
            comment="小程序解锁免费券表",
        )
        _base_indexes("mp_unlock_coupon", ["brand_id", "user_id", "person_id", "coupon_status", "valid_to", "used_unlock_id"])


def downgrade() -> None:
    for table in [
        "mp_unlock_coupon",
        "mp_contact_unlock",
        "mp_heartbeat_progress",
        "mp_user_favorite",
        "mp_user_like",
        "mp_user_profile_action",
    ]:
        if table in _tables():
            op.drop_table(table)
