"""create service course record

Revision ID: 20260526_1500
Revises: 20260526_1400
Create Date: 2026-05-26 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260526_1500"
down_revision: str | None = "20260526_1400"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _create_indexes(table_name: str, columns: list[str]) -> None:
    indexes = {row["name"] for row in sa.inspect(op.get_bind()).get_indexes(table_name)}
    for column in columns:
        index_name = f"ix_{table_name}_{column}"
        if index_name not in indexes:
            op.create_index(index_name, table_name, [column])


def upgrade() -> None:
    if "service_course_record" not in _tables():
        op.create_table(
            "service_course_record",
            sa.Column("id", sa.Integer(), nullable=False, comment="主键ID"),
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("service_case_id", sa.Integer(), nullable=False, comment="服务工单ID"),
            sa.Column("service_plan_item_id", sa.Integer(), nullable=False, comment="课程计划节点ID"),
            sa.Column("entitlement_id", sa.Integer(), nullable=False, comment="课程权益ID"),
            sa.Column("usage_id", sa.Integer(), nullable=True, comment="核销记录ID"),
            sa.Column("vip_id", sa.Integer(), nullable=False, comment="VIP服务ID"),
            sa.Column("contract_id", sa.Integer(), nullable=False, comment="合同ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="客户Person ID"),
            sa.Column("matchmaker_id", sa.Integer(), nullable=True, comment="服务红娘ID"),
            sa.Column("course_at", sa.DateTime(), nullable=False, comment="课程时间"),
            sa.Column("course_title", sa.String(length=128), nullable=False, comment="课程主题"),
            sa.Column("course_mode", sa.String(length=32), nullable=False, comment="课程形式"),
            sa.Column("content", sa.Text(), nullable=True, comment="课程内容"),
            sa.Column("customer_feedback", sa.Text(), nullable=True, comment="客户反馈/学习情况"),
            sa.Column("matchmaker_remark", sa.Text(), nullable=True, comment="红娘备注"),
            sa.Column("quantity", sa.Integer(), nullable=False, comment="课时数"),
            sa.Column("customer_confirm_status", sa.String(length=32), nullable=False, comment="客户确认状态"),
            sa.Column("customer_signature_url", sa.String(length=1000), nullable=True, comment="客户签字图片"),
            sa.Column("customer_signed_at", sa.DateTime(), nullable=True, comment="客户签字时间"),
            sa.Column("record_status", sa.String(length=32), nullable=False, comment="课程记录状态"),
            sa.Column("revoke_reason", sa.Text(), nullable=True, comment="撤销原因"),
            sa.Column("revoked_by", sa.Integer(), nullable=True, comment="撤销人ID"),
            sa.Column("revoked_at", sa.DateTime(), nullable=True, comment="撤销时间"),
            sa.Column("created_time", sa.DateTime(), nullable=True, comment="创建时间"),
            sa.Column("updated_time", sa.DateTime(), nullable=True, comment="更新时间"),
            sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否删除"),
            sa.Column("created_id", sa.Integer(), nullable=True, comment="创建人ID"),
            sa.Column("updated_id", sa.Integer(), nullable=True, comment="更新人ID"),
            sa.Column("deleted_id", sa.Integer(), nullable=True, comment="删除人ID"),
            sa.ForeignKeyConstraint(["contract_id"], ["crm_contract.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["entitlement_id"], ["service_entitlement.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["matchmaker_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["revoked_by"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["service_case_id"], ["service_case.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["service_plan_item_id"], ["service_plan_item.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["usage_id"], ["entitlement_usage_log.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["vip_id"], ["crm_vip_profile.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            comment="VIP课程服务记录表",
        )
    _create_indexes(
        "service_course_record",
        [
            "brand_id",
            "service_case_id",
            "service_plan_item_id",
            "entitlement_id",
            "usage_id",
            "vip_id",
            "contract_id",
            "person_id",
            "matchmaker_id",
            "course_at",
            "course_mode",
            "customer_confirm_status",
            "customer_signed_at",
            "record_status",
            "revoked_by",
            "revoked_at",
        ],
    )


def downgrade() -> None:
    if "service_course_record" in _tables():
        op.drop_table("service_course_record")
