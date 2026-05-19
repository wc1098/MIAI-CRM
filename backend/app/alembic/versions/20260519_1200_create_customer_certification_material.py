"""create customer certification material

Revision ID: 20260519_1200
Revises: 20260519_1100
Create Date: 2026-05-19 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260519_1200"
down_revision: str | None = "20260519_1100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _indexes(table_name: str) -> set[str]:
    return {row["name"] for row in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    table_name = "crm_customer_certification_material"
    if table_name not in _tables():
        op.create_table(
            table_name,
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("customer_id", sa.Integer(), nullable=False, comment="客户ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("item_code", sa.String(length=64), nullable=False, comment="资料项编码"),
            sa.Column("item_name", sa.String(length=64), nullable=False, comment="资料项名称"),
            sa.Column("material_type", sa.String(length=32), nullable=False, comment="资料类型"),
            sa.Column("file_name", sa.String(length=255), nullable=True, comment="文件名"),
            sa.Column("file_path", sa.String(length=512), nullable=True, comment="文件路径"),
            sa.Column("file_url", sa.String(length=1000), nullable=False, comment="文件URL"),
            sa.Column("payload", sa.JSON(), nullable=True, comment="资料扩展"),
            sa.Column("collected_by", sa.Integer(), nullable=True, comment="收集人ID"),
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
            sa.ForeignKeyConstraint(["created_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["customer_id"], ["crm_customer_profile.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["deleted_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["updated_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("uuid"),
            comment="CRM客户认证资料存档表",
        )
    existing_indexes = _indexes(table_name)
    for column in [
        "brand_id",
        "customer_id",
        "person_id",
        "item_code",
        "material_type",
        "collected_by",
        "uuid",
        "status",
        "created_time",
        "updated_time",
        "is_deleted",
        "deleted_time",
        "created_id",
        "updated_id",
        "deleted_id",
    ]:
        index_name = f"ix_crm_customer_certification_material_{column}"
        if index_name not in existing_indexes:
            op.create_index(index_name, table_name, [column])


def downgrade() -> None:
    for column in [
        "is_deleted",
        "updated_time",
        "created_time",
        "status",
        "uuid",
        "deleted_id",
        "updated_id",
        "created_id",
        "deleted_time",
        "collected_by",
        "material_type",
        "item_code",
        "person_id",
        "customer_id",
        "brand_id",
    ]:
        op.drop_index(f"ix_crm_customer_certification_material_{column}", table_name="crm_customer_certification_material")
    op.drop_table("crm_customer_certification_material")
