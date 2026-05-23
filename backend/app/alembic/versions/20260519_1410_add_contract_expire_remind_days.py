"""add contract expire remind days

Revision ID: 20260519_1410
Revises: 20260519_1400
Create Date: 2026-05-19 19:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260519_1410"
down_revision: str | None = "20260519_1400"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table_name: str) -> set[str]:
    return {row["name"] for row in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    columns = _columns("crm_contract")
    if "expire_remind_days" not in columns:
        op.add_column(
            "crm_contract",
            sa.Column(
                "expire_remind_days",
                sa.Integer(),
                nullable=False,
                server_default="30",
                comment="到期提前提醒天数",
            ),
        )
        op.alter_column("crm_contract", "expire_remind_days", server_default=None)


def downgrade() -> None:
    columns = _columns("crm_contract")
    if "expire_remind_days" in columns:
        op.drop_column("crm_contract", "expire_remind_days")
