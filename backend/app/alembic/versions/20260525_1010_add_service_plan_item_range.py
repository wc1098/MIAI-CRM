"""add service plan item range

Revision ID: 20260525_1010
Revises: 20260525_1000
Create Date: 2026-05-25 10:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260525_1010"
down_revision: str | None = "20260525_1000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    return {row["name"] for row in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    columns = _columns("service_plan_item")
    if "planned_start_at" not in columns:
        op.add_column("service_plan_item", sa.Column("planned_start_at", sa.DateTime(), nullable=True, comment="计划区间开始"))
    if "planned_end_at" not in columns:
        op.add_column("service_plan_item", sa.Column("planned_end_at", sa.DateTime(), nullable=True, comment="计划区间结束"))

    indexes = _indexes("service_plan_item")
    if "ix_service_plan_item_planned_start_at" not in indexes:
        op.create_index("ix_service_plan_item_planned_start_at", "service_plan_item", ["planned_start_at"])
    if "ix_service_plan_item_planned_end_at" not in indexes:
        op.create_index("ix_service_plan_item_planned_end_at", "service_plan_item", ["planned_end_at"])

    op.execute(
        """
        UPDATE service_plan_item
        SET planned_start_at = COALESCE(planned_start_at, planned_at),
            planned_end_at = COALESCE(planned_end_at, due_at)
        WHERE is_deleted = false
          AND (planned_start_at IS NULL OR planned_end_at IS NULL)
        """
    )


def downgrade() -> None:
    indexes = _indexes("service_plan_item")
    if "ix_service_plan_item_planned_end_at" in indexes:
        op.drop_index("ix_service_plan_item_planned_end_at", table_name="service_plan_item")
    if "ix_service_plan_item_planned_start_at" in indexes:
        op.drop_index("ix_service_plan_item_planned_start_at", table_name="service_plan_item")
    columns = _columns("service_plan_item")
    if "planned_end_at" in columns:
        op.drop_column("service_plan_item", "planned_end_at")
    if "planned_start_at" in columns:
        op.drop_column("service_plan_item", "planned_start_at")
