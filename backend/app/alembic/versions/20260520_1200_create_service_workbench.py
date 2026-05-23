"""create service workbench

Revision ID: 20260520_1200
Revises: 20260520_1100
Create Date: 2026-05-20 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260520_1200"
down_revision: str | None = "20260520_1100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _indexes(table_name: str) -> set[str]:
    return {row["name"] for row in sa.inspect(op.get_bind()).get_indexes(table_name)}


def _audit_columns() -> list[sa.Column]:
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


def _audit_constraints() -> list[sa.ForeignKeyConstraint | sa.UniqueConstraint | sa.PrimaryKeyConstraint]:
    return [
        sa.ForeignKeyConstraint(["created_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["deleted_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["updated_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    ]


def _create_indexes(table_name: str, columns: list[str]) -> None:
    existing = _indexes(table_name)
    for column in columns + ["uuid", "status", "created_time", "updated_time", "is_deleted", "deleted_time", "created_id", "updated_id", "deleted_id"]:
        index_name = f"ix_{table_name}_{column}"
        if index_name not in existing:
            op.create_index(index_name, table_name, [column])


def upgrade() -> None:
    tables = _tables()
    if "service_case" not in tables:
        op.create_table(
            "service_case",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("vip_id", sa.Integer(), nullable=False, comment="VIP服务ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("customer_id", sa.Integer(), nullable=False, comment="客户ID"),
            sa.Column("contract_id", sa.Integer(), nullable=False, comment="合同ID"),
            sa.Column("store_id", sa.Integer(), nullable=False, comment="服务门店ID"),
            sa.Column("owner_matchmaker_id", sa.Integer(), nullable=True, comment="服务红娘ID"),
            sa.Column("pool_type", sa.String(length=32), nullable=False, comment="服务池类型"),
            sa.Column("case_status", sa.String(length=32), nullable=False, comment="服务工单状态"),
            sa.Column("assigned_by", sa.Integer(), nullable=True, comment="分配人ID"),
            sa.Column("assigned_at", sa.DateTime(), nullable=True, comment="分配时间"),
            sa.Column("close_review_status", sa.String(length=32), nullable=False, comment="关单审核状态"),
            sa.Column("close_requested_by", sa.Integer(), nullable=True, comment="关单申请人ID"),
            sa.Column("close_requested_at", sa.DateTime(), nullable=True, comment="关单申请时间"),
            sa.Column("close_reason", sa.Text(), nullable=True, comment="关单原因"),
            sa.Column("close_reviewed_by", sa.Integer(), nullable=True, comment="关单审核人ID"),
            sa.Column("close_reviewed_at", sa.DateTime(), nullable=True, comment="关单审核时间"),
            sa.Column("close_review_remark", sa.Text(), nullable=True, comment="关单审核备注"),
            sa.Column("reopened_by", sa.Integer(), nullable=True, comment="重开人ID"),
            sa.Column("reopened_at", sa.DateTime(), nullable=True, comment="重开时间"),
            sa.Column("reopen_reason", sa.Text(), nullable=True, comment="重开原因"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["assigned_by"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["close_requested_by"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["close_reviewed_by"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["contract_id"], ["crm_contract.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["customer_id"], ["crm_customer_profile.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["owner_matchmaker_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["reopened_by"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["store_id"], ["sys_dept.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["vip_id"], ["crm_vip_profile.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            *_audit_constraints(),
            sa.UniqueConstraint("contract_id", name="uq_service_case_contract_id"),
            comment="VIP服务工单表",
        )
    _create_indexes("service_case", ["brand_id", "vip_id", "person_id", "customer_id", "contract_id", "store_id", "owner_matchmaker_id", "pool_type", "case_status", "assigned_by", "assigned_at", "close_review_status", "close_requested_by", "close_requested_at", "close_reviewed_by", "close_reviewed_at", "reopened_by", "reopened_at"])

    if "service_entitlement" not in tables:
        op.create_table(
            "service_entitlement",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("service_case_id", sa.Integer(), nullable=False, comment="服务工单ID"),
            sa.Column("vip_id", sa.Integer(), nullable=False, comment="VIP服务ID"),
            sa.Column("contract_id", sa.Integer(), nullable=False, comment="合同ID"),
            sa.Column("source_contract_item_id", sa.Integer(), nullable=True, comment="来源合同明细ID"),
            sa.Column("entitlement_type", sa.String(length=32), nullable=False, comment="权益类型"),
            sa.Column("total_quota", sa.Integer(), nullable=False, comment="总权益"),
            sa.Column("used_quota", sa.Integer(), nullable=False, comment="已用权益"),
            sa.Column("remaining_quota", sa.Integer(), nullable=False, comment="剩余权益"),
            sa.Column("unit", sa.String(length=16), nullable=False, comment="单位"),
            sa.Column("allow_overuse", sa.Boolean(), nullable=False, comment="是否允许超额"),
            sa.Column("entitlement_status", sa.String(length=32), nullable=False, comment="权益状态"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["contract_id"], ["crm_contract.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["service_case_id"], ["service_case.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["source_contract_item_id"], ["crm_contract_item.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["vip_id"], ["crm_vip_profile.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            *_audit_constraints(),
            sa.UniqueConstraint("service_case_id", "source_contract_item_id", "entitlement_type", name="uq_service_entitlement_source"),
            comment="服务权益账本表",
        )
    _create_indexes("service_entitlement", ["brand_id", "service_case_id", "vip_id", "contract_id", "source_contract_item_id", "entitlement_type", "entitlement_status"])

    if "entitlement_usage_log" not in tables:
        op.create_table(
            "entitlement_usage_log",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("entitlement_id", sa.Integer(), nullable=False, comment="权益ID"),
            sa.Column("service_case_id", sa.Integer(), nullable=False, comment="服务工单ID"),
            sa.Column("vip_id", sa.Integer(), nullable=False, comment="VIP服务ID"),
            sa.Column("contract_id", sa.Integer(), nullable=False, comment="合同ID"),
            sa.Column("usage_type", sa.String(length=32), nullable=False, comment="核销类型"),
            sa.Column("quantity", sa.Integer(), nullable=False, comment="核销数量"),
            sa.Column("usage_status", sa.String(length=32), nullable=False, comment="核销状态"),
            sa.Column("occurred_at", sa.DateTime(), nullable=False, comment="发生时间"),
            sa.Column("title", sa.String(length=128), nullable=True, comment="核销标题"),
            sa.Column("content", sa.Text(), nullable=True, comment="核销内容"),
            sa.Column("candidate_person_id", sa.Integer(), nullable=True, comment="候选Person ID"),
            sa.Column("is_overuse", sa.Boolean(), nullable=False, comment="是否超额"),
            sa.Column("overuse_reason", sa.Text(), nullable=True, comment="超额原因"),
            sa.Column("void_reason", sa.Text(), nullable=True, comment="作废原因"),
            sa.Column("voided_by", sa.Integer(), nullable=True, comment="作废人ID"),
            sa.Column("voided_at", sa.DateTime(), nullable=True, comment="作废时间"),
            sa.Column("customer_confirm_status", sa.String(length=32), nullable=True, comment="客户确认状态"),
            sa.Column("customer_signature_url", sa.String(length=1000), nullable=True, comment="客户签字图片"),
            sa.Column("customer_signed_at", sa.DateTime(), nullable=True, comment="客户签字时间"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["candidate_person_id"], ["crm_person.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["contract_id"], ["crm_contract.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["entitlement_id"], ["service_entitlement.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["service_case_id"], ["service_case.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["voided_by"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["vip_id"], ["crm_vip_profile.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            *_audit_constraints(),
            comment="服务权益核销记录表",
        )
    _create_indexes("entitlement_usage_log", ["brand_id", "entitlement_id", "service_case_id", "vip_id", "contract_id", "usage_type", "usage_status", "occurred_at", "candidate_person_id", "is_overuse", "voided_by", "voided_at", "customer_confirm_status", "customer_signed_at"])

    if "deep_interview" not in tables:
        op.create_table(
            "deep_interview",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("service_case_id", sa.Integer(), nullable=False, comment="服务工单ID"),
            sa.Column("vip_id", sa.Integer(), nullable=False, comment="VIP服务ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("contract_id", sa.Integer(), nullable=False, comment="合同ID"),
            sa.Column("matchmaker_id", sa.Integer(), nullable=True, comment="服务红娘ID"),
            sa.Column("interview_type", sa.String(length=32), nullable=False, comment="深访类型"),
            sa.Column("interviewed_at", sa.DateTime(), nullable=False, comment="深访时间"),
            sa.Column("content", sa.Text(), nullable=False, comment="深访内容"),
            sa.Column("keywords", sa.JSON(), nullable=True, comment="关键词"),
            sa.Column("summary", sa.Text(), nullable=True, comment="人工摘要"),
            sa.Column("ai_summary", sa.Text(), nullable=True, comment="AI摘要预留"),
            sa.Column("ai_dimension_scores", sa.JSON(), nullable=True, comment="AI量表预留"),
            sa.Column("audio_file_url", sa.String(length=1000), nullable=True, comment="录音文件预留"),
            sa.Column("interview_status", sa.String(length=32), nullable=False, comment="深访状态"),
            sa.Column("void_reason", sa.Text(), nullable=True, comment="作废原因"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["contract_id"], ["crm_contract.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["matchmaker_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["service_case_id"], ["service_case.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["vip_id"], ["crm_vip_profile.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            *_audit_constraints(),
            comment="VIP服务深访记录表",
        )
    _create_indexes("deep_interview", ["brand_id", "service_case_id", "vip_id", "person_id", "contract_id", "matchmaker_id", "interview_type", "interviewed_at", "interview_status"])

    if "candidate_profile" not in tables:
        op.create_table(
            "candidate_profile",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("candidate_status", sa.String(length=32), nullable=False, comment="候选状态"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            *_audit_constraints(),
            sa.UniqueConstraint("person_id", name="uq_candidate_profile_person_id"),
            comment="服务备选资源身份表",
        )
    _create_indexes("candidate_profile", ["brand_id", "person_id", "candidate_status"])

    if "backup_pool_item" not in tables:
        op.create_table(
            "backup_pool_item",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("candidate_id", sa.Integer(), nullable=False, comment="候选身份ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("store_id", sa.Integer(), nullable=True, comment="来源门店ID"),
            sa.Column("matchmaker_id", sa.Integer(), nullable=False, comment="服务红娘ID"),
            sa.Column("source_type", sa.String(length=32), nullable=False, comment="加入来源"),
            sa.Column("private_tags", sa.JSON(), nullable=True, comment="红娘私有标签"),
            sa.Column("private_remark", sa.Text(), nullable=True, comment="红娘私有备注"),
            sa.Column("last_used_at", sa.DateTime(), nullable=True, comment="最近使用时间"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["candidate_id"], ["candidate_profile.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["matchmaker_id"], ["sys_user.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["store_id"], ["sys_dept.id"], ondelete="SET NULL", onupdate="CASCADE"),
            *_audit_constraints(),
            sa.UniqueConstraint("matchmaker_id", "person_id", name="uq_backup_pool_matchmaker_person"),
            comment="红娘私有备选库表",
        )
    _create_indexes("backup_pool_item", ["brand_id", "candidate_id", "person_id", "store_id", "matchmaker_id", "source_type", "last_used_at"])


def downgrade() -> None:
    for table_name in [
        "backup_pool_item",
        "candidate_profile",
        "deep_interview",
        "entitlement_usage_log",
        "service_entitlement",
        "service_case",
    ]:
        if table_name in _tables():
            op.drop_table(table_name)
