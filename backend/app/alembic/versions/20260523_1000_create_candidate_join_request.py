"""create candidate join request

Revision ID: 20260523_1000
Revises: 20260522_1000
Create Date: 2026-05-23 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260523_1000"
down_revision: str | None = "20260522_1000"
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


def _add_column(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def upgrade() -> None:
    tables = _tables()
    if "candidate_join_request" not in tables:
        op.create_table(
            "candidate_join_request",
            sa.Column("brand_id", sa.Integer(), nullable=False, server_default="1", comment="品牌ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("person_store_id", sa.Integer(), nullable=True, comment="人员归属门店ID"),
            sa.Column("request_scope", sa.String(length=16), nullable=False, comment="申请范围"),
            sa.Column("request_matchmaker_id", sa.Integer(), nullable=False, comment="申请红娘ID"),
            sa.Column("request_store_id", sa.Integer(), nullable=True, comment="申请门店ID"),
            sa.Column("private_tags_snapshot", sa.JSON(), nullable=True, comment="私有标签快照"),
            sa.Column("private_remark_snapshot", sa.Text(), nullable=True, comment="私有备注快照"),
            sa.Column("request_reason", sa.Text(), nullable=True, comment="申请理由"),
            sa.Column("review_status", sa.String(length=16), nullable=False, server_default="pending", comment="审核状态"),
            sa.Column("reviewer_id", sa.Integer(), nullable=True, comment="审核人ID"),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True, comment="审核时间"),
            sa.Column("review_remark", sa.Text(), nullable=True, comment="审核备注"),
            sa.Column("approved_backup_item_id", sa.Integer(), nullable=True, comment="审批通过备选库记录ID"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["approved_backup_item_id"], ["backup_pool_item.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["person_store_id"], ["sys_dept.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["request_matchmaker_id"], ["sys_user.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["request_store_id"], ["sys_dept.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["reviewer_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            *_audit_constraints(),
            comment="备选库加入申请表",
        )
    _create_indexes(
        "candidate_join_request",
        ["brand_id", "person_id", "person_store_id", "request_scope", "request_matchmaker_id", "request_store_id", "review_status", "reviewer_id", "reviewed_at", "approved_backup_item_id"],
    )

    if "backup_pool_item" in _tables():
        _add_column("backup_pool_item", sa.Column("join_request_id", sa.Integer(), nullable=True, comment="加入申请ID"))
        _add_column("backup_pool_item", sa.Column("approved_by", sa.Integer(), nullable=True, comment="审批人ID"))
        _add_column("backup_pool_item", sa.Column("approved_at", sa.DateTime(), nullable=True, comment="审批通过时间"))
        _add_column(
            "backup_pool_item",
            sa.Column("contact_unmasked_after_approval", sa.Boolean(), nullable=False, server_default=sa.false(), comment="审批通过后备选库内解除脱敏"),
        )
        constraints = {row["name"] for row in sa.inspect(op.get_bind()).get_foreign_keys("backup_pool_item")}
        if "fk_backup_pool_item_join_request_id_candidate_join_request" not in constraints:
            op.create_foreign_key("fk_backup_pool_item_join_request_id_candidate_join_request", "backup_pool_item", "candidate_join_request", ["join_request_id"], ["id"], ondelete="SET NULL", onupdate="CASCADE")
        if "fk_backup_pool_item_approved_by_sys_user" not in constraints:
            op.create_foreign_key("fk_backup_pool_item_approved_by_sys_user", "backup_pool_item", "sys_user", ["approved_by"], ["id"], ondelete="SET NULL", onupdate="CASCADE")
        _create_indexes("backup_pool_item", ["join_request_id", "approved_by", "approved_at"])


def downgrade() -> None:
    if "backup_pool_item" in _tables():
        constraints = {row["name"] for row in sa.inspect(op.get_bind()).get_foreign_keys("backup_pool_item")}
        for name in ["fk_backup_pool_item_join_request_id_candidate_join_request", "fk_backup_pool_item_approved_by_sys_user"]:
            if name in constraints:
                op.drop_constraint(name, "backup_pool_item", type_="foreignkey")
        for column in ["contact_unmasked_after_approval", "approved_at", "approved_by", "join_request_id"]:
            if column in _columns("backup_pool_item"):
                op.drop_column("backup_pool_item", column)
    if "candidate_join_request" in _tables():
        op.drop_table("candidate_join_request")
