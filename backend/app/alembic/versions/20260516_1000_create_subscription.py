"""create subscription module

Revision ID: 20260516_1000
Revises: 20260515_1900
Create Date: 2026-05-16 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "20260516_1000"
down_revision = "20260515_1900"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("uuid", sa.String(length=64), nullable=False, comment="UUID全局唯一标识"),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="0", comment="状态"),
        sa.Column("description", sa.Text(), nullable=True, comment="备注"),
        sa.Column("created_time", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.Column("updated_time", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="更新时间"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false(), comment="是否已删除"),
        sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
    ]


def _user_columns() -> list[sa.Column]:
    return [
        sa.Column("created_id", sa.Integer(), nullable=True, comment="创建人ID"),
        sa.Column("updated_id", sa.Integer(), nullable=True, comment="更新人ID"),
        sa.Column("deleted_id", sa.Integer(), nullable=True, comment="删除人ID"),
    ]


def _idx(table: str, columns: list[str], unique: bool = False) -> None:
    op.create_index(op.f(f"ix_{table}_{'_'.join(columns)}"), table, columns, unique=unique)


def upgrade() -> None:
    tables = _tables()
    if "subscription_plan" not in tables:
        op.create_table(
            "subscription_plan",
            *_base_columns(),
            *_user_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, server_default="1", comment="品牌ID"),
            sa.Column("plan_code", sa.String(length=32), nullable=False, comment="方案编码"),
            sa.Column("plan_name", sa.String(length=64), nullable=False, comment="方案名称"),
            sa.Column("pay_period", sa.String(length=16), nullable=False, comment="支付周期"),
            sa.Column("period_days", sa.Integer(), nullable=False, comment="权益天数"),
            sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="0", comment="价格"),
            sa.Column("monthly_recommend_count", sa.Integer(), nullable=False, server_default="4", comment="每月推荐数"),
            sa.Column("total_quota", sa.Integer(), nullable=False, server_default="4", comment="总推荐槽位"),
            sa.Column("benefit_desc", sa.Text(), nullable=True, comment="权益说明"),
            sa.Column("sort", sa.Integer(), nullable=False, server_default="0", comment="排序"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("plan_code", name="uq_subscription_plan_code"),
            comment="小程序订阅方案表",
        )
        for col in ["uuid", "status", "created_time", "updated_time", "is_deleted", "deleted_time", "brand_id", "plan_code", "pay_period", "sort"]:
            _idx("subscription_plan", [col], unique=(col == "uuid"))

    if "user_subscription" not in tables:
        op.create_table(
            "user_subscription",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, server_default="1", comment="品牌ID"),
            sa.Column("user_id", sa.Integer(), nullable=False, comment="小程序用户ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("plan_id", sa.Integer(), nullable=False, comment="订阅方案ID"),
            sa.Column("order_id", sa.Integer(), nullable=True, comment="订单ID"),
            sa.Column("started_at", sa.DateTime(), nullable=False, comment="开始时间"),
            sa.Column("expired_at", sa.DateTime(), nullable=False, comment="过期时间"),
            sa.Column("total_quota", sa.Integer(), nullable=False, server_default="0", comment="总槽位"),
            sa.Column("used_quota", sa.Integer(), nullable=False, server_default="0", comment="已开放槽位"),
            sa.Column("last_unlock_at", sa.DateTime(), nullable=True, comment="最近开放时间"),
            sa.Column("subscription_status", sa.String(length=32), nullable=False, server_default="active", comment="订阅状态"),
            sa.Column("extra", sa.JSON(), nullable=True, comment="扩展数据"),
            sa.ForeignKeyConstraint(["user_id"], ["mini_program_user.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["plan_id"], ["subscription_plan.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["order_id"], ["payment_order.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            comment="小程序用户订阅表",
        )
        for col in ["uuid", "status", "created_time", "updated_time", "is_deleted", "deleted_time", "brand_id", "user_id", "person_id", "plan_id", "order_id", "started_at", "expired_at", "last_unlock_at", "subscription_status"]:
            _idx("user_subscription", [col], unique=(col == "uuid"))

    if "subscription_recommendation" not in tables:
        op.create_table(
            "subscription_recommendation",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, server_default="1", comment="品牌ID"),
            sa.Column("subscription_id", sa.Integer(), nullable=False, comment="订阅ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="订阅人Person"),
            sa.Column("candidate_person_id", sa.Integer(), nullable=True, comment="候选Person"),
            sa.Column("candidate_user_id", sa.Integer(), nullable=True, comment="候选小程序用户"),
            sa.Column("recommend_index", sa.Integer(), nullable=False, comment="推荐序号"),
            sa.Column("unlock_at", sa.DateTime(), nullable=False, comment="开放时间"),
            sa.Column("recommendation_status", sa.String(length=32), nullable=False, server_default="locked", comment="推荐状态"),
            sa.Column("viewed_at", sa.DateTime(), nullable=True, comment="查看手机号时间"),
            sa.Column("source", sa.String(length=32), nullable=False, server_default="match", comment="推荐来源"),
            sa.Column("match_score", sa.Integer(), nullable=True, comment="匹配度"),
            sa.Column("match_reason", sa.Text(), nullable=True, comment="推荐理由"),
            sa.Column("match_snapshot", sa.JSON(), nullable=True, comment="匹配快照"),
            sa.Column("unlock_id", sa.Integer(), nullable=True, comment="联系方式解锁记录"),
            sa.Column("last_match_at", sa.DateTime(), nullable=True, comment="最近匹配时间"),
            sa.Column("last_error", sa.Text(), nullable=True, comment="最近错误"),
            sa.ForeignKeyConstraint(["subscription_id"], ["user_subscription.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["candidate_person_id"], ["crm_person.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["candidate_user_id"], ["mini_program_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["unlock_id"], ["mp_contact_unlock.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            comment="小程序订阅推荐槽位表",
        )
        for col in ["uuid", "status", "created_time", "updated_time", "is_deleted", "deleted_time", "brand_id", "subscription_id", "person_id", "candidate_person_id", "candidate_user_id", "recommend_index", "unlock_at", "recommendation_status", "viewed_at", "source", "last_match_at"]:
            _idx("subscription_recommendation", [col], unique=(col == "uuid"))


def downgrade() -> None:
    tables = _tables()
    if "subscription_recommendation" in tables:
        op.drop_table("subscription_recommendation")
    if "user_subscription" in tables:
        op.drop_table("user_subscription")
    if "subscription_plan" in tables:
        op.drop_table("subscription_plan")
