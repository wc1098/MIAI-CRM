"""add lead reclaim partial index

Revision ID: 20260529_1020
Revises: 20260529_1010
Create Date: 2026-05-29 10:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_1020"
down_revision: str | None = "20260529_1010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "ix_perf_crm_lead_reclaim_due"


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgresql():
        return
    op.execute(
        sa.text(
            f'CREATE INDEX IF NOT EXISTS "{INDEX_NAME}" '
            'ON "crm_lead_profile" ("pool_type", "lead_type", "store_id", "assigned_at", "id") '
            'WHERE "is_deleted" = false AND "owner_sales_id" IS NOT NULL'
        )
    )


def downgrade() -> None:
    if not _is_postgresql():
        return
    op.execute(sa.text(f'DROP INDEX IF EXISTS "{INDEX_NAME}"'))
