"""add vip assignment

Revision ID: 20260520_1000
Revises: 20260520_0900
Create Date: 2026-05-20 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260520_1000"
down_revision: str | None = "20260520_0900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table_name: str) -> set[str]:
    return {row["name"] for row in sa.inspect(op.get_bind()).get_columns(table_name)}


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
    if "crm_vip_profile" in _tables():
        columns = _columns("crm_vip_profile")
        if "assigned_at" not in columns:
            op.add_column("crm_vip_profile", sa.Column("assigned_at", sa.DateTime(), nullable=True, comment="分配时间"))
            op.create_index("ix_crm_vip_profile_assigned_at", "crm_vip_profile", ["assigned_at"])
        if "assigned_by" not in columns:
            op.add_column("crm_vip_profile", sa.Column("assigned_by", sa.Integer(), nullable=True, comment="分配人ID"))
            op.create_foreign_key("fk_crm_vip_profile_assigned_by_sys_user", "crm_vip_profile", "sys_user", ["assigned_by"], ["id"], ondelete="SET NULL", onupdate="CASCADE")
            op.create_index("ix_crm_vip_profile_assigned_by", "crm_vip_profile", ["assigned_by"])

    if "crm_vip_service_log" not in _tables():
        op.create_table(
            "crm_vip_service_log",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("vip_id", sa.Integer(), nullable=False, comment="VIP服务ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("customer_id", sa.Integer(), nullable=False, comment="客户ID"),
            sa.Column("contract_id", sa.Integer(), nullable=False, comment="合同ID"),
            sa.Column("operation_type", sa.String(length=32), nullable=False, comment="操作类型"),
            sa.Column("operator_user_id", sa.Integer(), nullable=True, comment="操作人ID"),
            sa.Column("before_owner_user_id", sa.Integer(), nullable=True, comment="原服务红娘ID"),
            sa.Column("after_owner_user_id", sa.Integer(), nullable=True, comment="新服务红娘ID"),
            sa.Column("before_status", sa.String(length=32), nullable=True, comment="原状态"),
            sa.Column("after_status", sa.String(length=32), nullable=True, comment="新状态"),
            sa.Column("change_detail", sa.JSON(), nullable=True, comment="变更详情"),
            sa.Column("remark", sa.Text(), nullable=True, comment="备注"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["contract_id"], ["crm_contract.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["customer_id"], ["crm_customer_profile.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["operator_user_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["vip_id"], ["crm_vip_profile.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            *_audit_constraints(),
            comment="CRM VIP服务流转日志表",
        )
    _create_indexes(
        "crm_vip_service_log",
        [
            "brand_id",
            "vip_id",
            "person_id",
            "customer_id",
            "contract_id",
            "operation_type",
            "operator_user_id",
            "before_owner_user_id",
            "after_owner_user_id",
            "before_status",
            "after_status",
        ],
    )


def downgrade() -> None:
    if "crm_vip_service_log" in _tables():
        op.drop_table("crm_vip_service_log")
    if "crm_vip_profile" in _tables():
        columns = _columns("crm_vip_profile")
        if "assigned_by" in columns:
            op.drop_index("ix_crm_vip_profile_assigned_by", table_name="crm_vip_profile")
            op.drop_constraint("fk_crm_vip_profile_assigned_by_sys_user", "crm_vip_profile", type_="foreignkey")
            op.drop_column("crm_vip_profile", "assigned_by")
        if "assigned_at" in columns:
            op.drop_index("ix_crm_vip_profile_assigned_at", table_name="crm_vip_profile")
            op.drop_column("crm_vip_profile", "assigned_at")
