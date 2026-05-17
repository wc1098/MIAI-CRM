"""subscription reason polish

Revision ID: 20260517_0900
Revises: 20260516_1000
Create Date: 2026-05-17 09:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "20260517_0900"
down_revision = "20260516_1000"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


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


def _idx(table: str, columns: list[str], unique: bool = False) -> None:
    op.create_index(op.f(f"ix_{table}_{'_'.join(columns)}"), table, columns, unique=unique)


def upgrade() -> None:
    tables = _tables()
    if "subscription_recommendation" in tables:
        cols = _columns("subscription_recommendation")
        if "match_reason_rule" not in cols:
            op.add_column("subscription_recommendation", sa.Column("match_reason_rule", sa.Text(), nullable=True, comment="规则推荐理由"))
        if "match_reason_ai" not in cols:
            op.add_column("subscription_recommendation", sa.Column("match_reason_ai", sa.Text(), nullable=True, comment="AI润色推荐理由"))
        if "reason_generation_status" not in cols:
            op.add_column("subscription_recommendation", sa.Column("reason_generation_status", sa.String(length=32), nullable=False, server_default="none", comment="推荐理由生成状态"))
            _idx("subscription_recommendation", ["reason_generation_status"])
        if "reason_model_name" not in cols:
            op.add_column("subscription_recommendation", sa.Column("reason_model_name", sa.String(length=128), nullable=True, comment="推荐理由模型名称"))
        if "reason_generated_at" not in cols:
            op.add_column("subscription_recommendation", sa.Column("reason_generated_at", sa.DateTime(), nullable=True, comment="推荐理由生成时间"))
            _idx("subscription_recommendation", ["reason_generated_at"])
        if "reason_last_error" not in cols:
            op.add_column("subscription_recommendation", sa.Column("reason_last_error", sa.Text(), nullable=True, comment="推荐理由最近错误"))
        op.execute("UPDATE subscription_recommendation SET match_reason_rule = match_reason WHERE match_reason_rule IS NULL AND match_reason IS NOT NULL")

    if "subscription_recommendation_reason_task" not in tables:
        op.create_table(
            "subscription_recommendation_reason_task",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, server_default="1", comment="品牌ID"),
            sa.Column("recommendation_id", sa.Integer(), nullable=False, comment="推荐槽位ID"),
            sa.Column("subscription_id", sa.Integer(), nullable=False, comment="订阅ID"),
            sa.Column("viewer_person_id", sa.Integer(), nullable=False, comment="查看人Person"),
            sa.Column("target_person_id", sa.Integer(), nullable=False, comment="被推荐Person"),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0", comment="重试次数"),
            sa.Column("next_retry_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="下次执行时间"),
            sa.Column("locked_at", sa.DateTime(), nullable=True, comment="锁定时间"),
            sa.Column("locked_by", sa.String(length=64), nullable=True, comment="锁定者"),
            sa.Column("last_error", sa.Text(), nullable=True, comment="最近错误"),
            sa.Column("payload_snapshot", sa.JSON(), nullable=True, comment="脱敏输入快照"),
            sa.ForeignKeyConstraint(["recommendation_id"], ["subscription_recommendation.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["subscription_id"], ["user_subscription.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["viewer_person_id"], ["crm_person.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["target_person_id"], ["crm_person.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("recommendation_id", name="uq_subscription_reason_task_recommendation"),
            comment="订阅推荐理由AI润色任务表",
        )
        for col in ["uuid", "status", "created_time", "updated_time", "is_deleted", "deleted_time", "brand_id", "recommendation_id", "subscription_id", "viewer_person_id", "target_person_id", "next_retry_at", "locked_at", "locked_by"]:
            _idx("subscription_recommendation_reason_task", [col], unique=(col == "uuid"))


def downgrade() -> None:
    tables = _tables()
    if "subscription_recommendation_reason_task" in tables:
        op.drop_table("subscription_recommendation_reason_task")
    if "subscription_recommendation" in tables:
        cols = _columns("subscription_recommendation")
        for col in ["reason_last_error", "reason_generated_at", "reason_model_name", "reason_generation_status", "match_reason_ai", "match_reason_rule"]:
            if col in cols:
                op.drop_column("subscription_recommendation", col)
