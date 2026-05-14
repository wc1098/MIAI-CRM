"""expand agreement device info

Revision ID: 20260513_1508
Revises: 20260512_1210
Create Date: 2026-05-13 15:08:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20260513_1508"
down_revision: str | None = "20260512_1210"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    if "device_info" in _columns("user_agreement_acceptance"):
        op.alter_column(
            "user_agreement_acceptance",
            "device_info",
            existing_type=sa.String(length=255),
            type_=sa.Text(),
            existing_nullable=True,
            comment="设备信息",
        )


def downgrade() -> None:
    if "device_info" in _columns("user_agreement_acceptance"):
        op.alter_column(
            "user_agreement_acceptance",
            "device_info",
            existing_type=sa.Text(),
            type_=sa.String(length=255),
            existing_nullable=True,
            comment="设备信息",
        )
