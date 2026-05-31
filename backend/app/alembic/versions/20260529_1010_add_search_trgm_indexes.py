"""add search trigram indexes

Revision ID: 20260529_1010
Revises: 20260529_1000
Create Date: 2026-05-29 10:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_1010"
down_revision: str | None = "20260529_1000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TRGM_INDEXES: tuple[tuple[str, str, str], ...] = (
    ("ix_perf_trgm_crm_person_name", "crm_person", "name"),
    ("ix_perf_trgm_crm_person_primary_mobile", "crm_person", "primary_mobile"),
    ("ix_perf_trgm_crm_person_display_no", "crm_person", "display_no"),
    ("ix_perf_trgm_crm_contract_no", "crm_contract", "contract_no"),
    ("ix_perf_trgm_crm_contract_name", "crm_contract", "contract_name"),
    ("ix_perf_trgm_crm_receipt_no", "crm_contract_receipt", "receipt_no"),
    ("ix_perf_trgm_mp_user_nickname", "mini_program_user", "nickname"),
    ("ix_perf_trgm_mp_user_mobile", "mini_program_user", "mobile"),
)


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if not _is_postgresql():
        return
    tables = _tables()
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for index_name, table_name, column_name in TRGM_INDEXES:
        if table_name not in tables:
            continue
        op.execute(
            sa.text(
                f'CREATE INDEX IF NOT EXISTS "{index_name}" '
                f'ON "{table_name}" USING gin ("{column_name}" gin_trgm_ops)'
            )
        )


def downgrade() -> None:
    if not _is_postgresql():
        return
    for index_name, _, _ in reversed(TRGM_INDEXES):
        op.execute(sa.text(f'DROP INDEX IF EXISTS "{index_name}"'))
