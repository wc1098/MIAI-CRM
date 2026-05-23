"""create contract store rule

Revision ID: 20260522_1000
Revises: 20260520_1200
Create Date: 2026-05-22 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260522_1000"
down_revision: str | None = "20260520_1200"
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
    if "crm_contract_store_rule" not in _tables():
        op.create_table(
            "crm_contract_store_rule",
            sa.Column("store_id", sa.Integer(), nullable=False, comment="门店ID"),
            sa.Column("require_contract_review", sa.Boolean(), nullable=False, server_default=sa.true(), comment="是否需要合同审核"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["store_id"], ["sys_dept.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.UniqueConstraint("store_id"),
            *_audit_constraints(),
            comment="CRM门店合同规则表",
        )
    _create_indexes("crm_contract_store_rule", ["store_id"])


def downgrade() -> None:
    if "crm_contract_store_rule" in _tables():
        op.drop_table("crm_contract_store_rule")
