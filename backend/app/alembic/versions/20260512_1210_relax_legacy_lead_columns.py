"""relax legacy lead columns

Revision ID: 20260512_1210
Revises: 20260512_1200
Create Date: 2026-05-12 12:10:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20260512_1210"
down_revision: str | None = "20260512_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    columns = _columns("crm_lead_profile")
    for column_name in ["lead_stage", "no_first_follow_reminded", "no_follow_7d_reminded"]:
        if column_name in columns:
            op.alter_column("crm_lead_profile", column_name, existing_type=sa.String(length=32) if column_name == "lead_stage" else sa.Boolean(), nullable=True)


def downgrade() -> None:
    columns = _columns("crm_lead_profile")
    for column_name in ["lead_stage", "no_first_follow_reminded", "no_follow_7d_reminded"]:
        if column_name in columns:
            op.alter_column("crm_lead_profile", column_name, existing_type=sa.String(length=32) if column_name == "lead_stage" else sa.Boolean(), nullable=False)
