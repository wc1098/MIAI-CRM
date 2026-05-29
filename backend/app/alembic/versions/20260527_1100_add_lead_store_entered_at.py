"""add lead store entered at

Revision ID: 20260527_1100
Revises: 20260527_1000
Create Date: 2026-05-27 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260527_1100"
down_revision: str | None = "20260527_1000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table_name: str) -> set[str]:
    return {row["name"] for row in sa.inspect(op.get_bind()).get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    return {row["name"] for row in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    columns = _columns("crm_lead_profile")
    if "store_entered_at" not in columns:
        op.add_column(
            "crm_lead_profile",
            sa.Column("store_entered_at", sa.DateTime(), nullable=True, comment="首次进入门店时间"),
        )
    indexes = _indexes("crm_lead_profile")
    if "ix_crm_lead_profile_store_entered_at" not in indexes:
        op.create_index("ix_crm_lead_profile_store_entered_at", "crm_lead_profile", ["store_entered_at"])
    op.execute(
        """
        update crm_lead_profile
           set store_entered_at = coalesce(assigned_at, created_time)
         where store_id is not null
           and store_entered_at is null
        """
    )


def downgrade() -> None:
    indexes = _indexes("crm_lead_profile")
    if "ix_crm_lead_profile_store_entered_at" in indexes:
        op.drop_index("ix_crm_lead_profile_store_entered_at", table_name="crm_lead_profile")
    columns = _columns("crm_lead_profile")
    if "store_entered_at" in columns:
        op.drop_column("crm_lead_profile", "store_entered_at")
