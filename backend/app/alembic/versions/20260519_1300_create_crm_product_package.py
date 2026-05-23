"""create crm product package

Revision ID: 20260519_1300
Revises: 20260519_1200
Create Date: 2026-05-19 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260519_1300"
down_revision: str | None = "20260519_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _indexes(table_name: str) -> set[str]:
    return {row["name"] for row in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    table_name = "crm_product_package"
    if table_name not in _tables():
        op.create_table(
            table_name,
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("package_name", sa.String(length=128), nullable=False, comment="套餐名称"),
            sa.Column("standard_price", sa.Numeric(12, 2), nullable=False, comment="标准价"),
            sa.Column("service_days", sa.Integer(), nullable=False, comment="服务时长天数"),
            sa.Column("recommendation_quota", sa.Integer(), nullable=False, comment="推荐次数"),
            sa.Column("meeting_quota", sa.Integer(), nullable=False, comment="约见次数"),
            sa.Column("course_quota", sa.Integer(), nullable=False, comment="课程次数"),
            sa.Column("supports_online_meeting", sa.Boolean(), nullable=False, comment="是否支持线上约见"),
            sa.Column("internal_remark", sa.Text(), nullable=True, comment="内部备注"),
            sa.Column("sort", sa.Integer(), nullable=False, comment="排序"),
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
            sa.Column("uuid", sa.String(length=64), nullable=False, comment="UUID全局唯一标识"),
            sa.Column("status", sa.String(length=10), nullable=False, comment="状态(0:正常 1:禁用)"),
            sa.Column("description", sa.Text(), nullable=True, comment="套餐说明"),
            sa.Column("created_time", sa.DateTime(), nullable=False, comment="创建时间"),
            sa.Column("updated_time", sa.DateTime(), nullable=False, comment="更新时间"),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, comment="是否已删除(0:未删除 1:已删除)"),
            sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
            sa.Column("created_id", sa.Integer(), nullable=True, comment="创建人ID"),
            sa.Column("updated_id", sa.Integer(), nullable=True, comment="更新人ID"),
            sa.Column("deleted_id", sa.Integer(), nullable=True, comment="删除人ID"),
            sa.ForeignKeyConstraint(["created_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["deleted_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["updated_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("uuid"),
            comment="CRM产品套餐表",
        )
    existing_indexes = _indexes(table_name)
    for column in [
        "brand_id",
        "package_name",
        "sort",
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
        index_name = f"ix_crm_product_package_{column}"
        if index_name not in existing_indexes:
            op.create_index(index_name, table_name, [column])


def downgrade() -> None:
    existing_indexes = _indexes("crm_product_package") if "crm_product_package" in _tables() else set()
    for column in [
        "deleted_id",
        "updated_id",
        "created_id",
        "deleted_time",
        "is_deleted",
        "updated_time",
        "created_time",
        "status",
        "uuid",
        "sort",
        "package_name",
        "brand_id",
    ]:
        index_name = f"ix_crm_product_package_{column}"
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="crm_product_package")
    if "crm_product_package" in _tables():
        op.drop_table("crm_product_package")
