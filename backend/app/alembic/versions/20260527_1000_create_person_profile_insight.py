"""create person profile insight

Revision ID: 20260527_1000
Revises: 20260526_1500
Create Date: 2026-05-27 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260527_1000"
down_revision: str | None = "20260526_1500"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table_name: str) -> set[str]:
    return {row["name"] for row in sa.inspect(op.get_bind()).get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    return {row["name"] for row in sa.inspect(op.get_bind()).get_indexes(table_name)}


def _foreign_keys(table_name: str) -> set[str]:
    return {row["name"] for row in sa.inspect(op.get_bind()).get_foreign_keys(table_name) if row["name"]}


def _add_column(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def _create_indexes(table_name: str, columns: list[str]) -> None:
    indexes = _indexes(table_name)
    for column in columns:
        index_name = f"ix_{table_name}_{column}"
        if index_name not in indexes:
            op.create_index(index_name, table_name, [column])


def upgrade() -> None:
    tables = _tables()
    if "deep_interview" in tables:
        _add_column("deep_interview", sa.Column("customer_id", sa.Integer(), nullable=True, comment="客户ID"))
        _add_column("deep_interview", sa.Column("backup_item_id", sa.Integer(), nullable=True, comment="备选库记录ID"))
        _add_column("deep_interview", sa.Column("interview_scope", sa.String(length=32), nullable=True, comment="深访场景"))
        _add_column("deep_interview", sa.Column("interview_method", sa.String(length=32), nullable=True, comment="深访方式"))
        _add_column("deep_interview", sa.Column("structured_payload", sa.JSON(), nullable=True, comment="结构化深访内容"))
        _add_column("deep_interview", sa.Column("manual_notes", sa.Text(), nullable=True, comment="红娘备注"))
        _add_column("deep_interview", sa.Column("is_current_source", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否当前画像来源"))
        _add_column("deep_interview", sa.Column("voided_by", sa.Integer(), nullable=True, comment="作废人ID"))
        _add_column("deep_interview", sa.Column("voided_at", sa.DateTime(), nullable=True, comment="作废时间"))
        op.execute("UPDATE deep_interview SET interview_scope = 'vip_service' WHERE interview_scope IS NULL")
        op.alter_column("deep_interview", "interview_scope", nullable=False)
        for column in ("service_case_id", "vip_id", "contract_id"):
            if column in _columns("deep_interview"):
                op.alter_column("deep_interview", column, nullable=True)
        fks = _foreign_keys("deep_interview")
        if "fk_deep_interview_customer_id_crm_customer_profile" not in fks:
            op.create_foreign_key("fk_deep_interview_customer_id_crm_customer_profile", "deep_interview", "crm_customer_profile", ["customer_id"], ["id"], ondelete="SET NULL", onupdate="CASCADE")
        if "fk_deep_interview_backup_item_id_backup_pool_item" not in fks:
            op.create_foreign_key("fk_deep_interview_backup_item_id_backup_pool_item", "deep_interview", "backup_pool_item", ["backup_item_id"], ["id"], ondelete="SET NULL", onupdate="CASCADE")
        if "fk_deep_interview_voided_by_sys_user" not in fks:
            op.create_foreign_key("fk_deep_interview_voided_by_sys_user", "deep_interview", "sys_user", ["voided_by"], ["id"], ondelete="SET NULL", onupdate="CASCADE")
        _create_indexes(
            "deep_interview",
            ["customer_id", "backup_item_id", "interview_scope", "interview_method", "is_current_source", "voided_by", "voided_at"],
        )

    if "person_profile_insight" not in tables:
        op.create_table(
            "person_profile_insight",
            sa.Column("id", sa.Integer(), nullable=False, comment="主键ID"),
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("source_interview_id", sa.Integer(), nullable=True, comment="来源深访ID"),
            sa.Column("source_scope", sa.String(length=32), nullable=True, comment="来源深访场景"),
            sa.Column("personality_tags", sa.JSON(), nullable=True, comment="性格标签"),
            sa.Column("family_background", sa.Text(), nullable=True, comment="家庭背景"),
            sa.Column("relationship_history", sa.Text(), nullable=True, comment="情感经历"),
            sa.Column("marriage_view", sa.Text(), nullable=True, comment="婚恋观"),
            sa.Column("communication_style", sa.Text(), nullable=True, comment="沟通方式"),
            sa.Column("emotional_needs", sa.Text(), nullable=True, comment="情感需求"),
            sa.Column("hard_reject_items", sa.JSON(), nullable=True, comment="硬性拒绝项"),
            sa.Column("soft_preference_items", sa.JSON(), nullable=True, comment="软性偏好"),
            sa.Column("compromise_items", sa.JSON(), nullable=True, comment="可妥协项"),
            sa.Column("risk_level", sa.String(length=32), nullable=True, comment="风险等级"),
            sa.Column("risk_notes", sa.Text(), nullable=True, comment="风险提示"),
            sa.Column("communication_taboo", sa.Text(), nullable=True, comment="沟通禁忌"),
            sa.Column("recommendation_strategy", sa.Text(), nullable=True, comment="推荐策略"),
            sa.Column("matchmaker_comment", sa.Text(), nullable=True, comment="红娘评价"),
            sa.Column("public_matchmaker_impression", sa.Text(), nullable=True, comment="脱敏红娘印象"),
            sa.Column("keywords", sa.JSON(), nullable=True, comment="关键词"),
            sa.Column("profile_status", sa.String(length=32), nullable=False, server_default="active", comment="画像状态"),
            sa.Column("profile_payload", sa.JSON(), nullable=True, comment="画像来源结构化快照"),
            sa.Column("updated_by_user_id", sa.Integer(), nullable=True, comment="画像维护人ID"),
            sa.Column("insight_updated_at", sa.DateTime(), nullable=True, comment="画像更新时间"),
            sa.Column("created_time", sa.DateTime(), nullable=True, comment="创建时间"),
            sa.Column("updated_time", sa.DateTime(), nullable=True, comment="更新时间"),
            sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否删除"),
            sa.Column("created_id", sa.Integer(), nullable=True, comment="创建人ID"),
            sa.Column("updated_id", sa.Integer(), nullable=True, comment="更新人ID"),
            sa.Column("deleted_id", sa.Integer(), nullable=True, comment="删除人ID"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["source_interview_id"], ["deep_interview.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["updated_by_user_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("person_id", name="uq_person_profile_insight_person"),
            comment="人员当前深访画像表",
        )
    _create_indexes(
        "person_profile_insight",
        ["brand_id", "person_id", "source_interview_id", "source_scope", "risk_level", "profile_status", "updated_by_user_id", "insight_updated_at"],
    )


def downgrade() -> None:
    if "person_profile_insight" in _tables():
        op.drop_table("person_profile_insight")
    if "deep_interview" in _tables():
        fks = _foreign_keys("deep_interview")
        for name in [
            "fk_deep_interview_customer_id_crm_customer_profile",
            "fk_deep_interview_backup_item_id_backup_pool_item",
            "fk_deep_interview_voided_by_sys_user",
        ]:
            if name in fks:
                op.drop_constraint(name, "deep_interview", type_="foreignkey")
        for column in ["voided_at", "voided_by", "is_current_source", "manual_notes", "structured_payload", "interview_method", "interview_scope", "backup_item_id", "customer_id"]:
            if column in _columns("deep_interview"):
                op.drop_column("deep_interview", column)
