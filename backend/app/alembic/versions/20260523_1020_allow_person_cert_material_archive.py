"""allow person certification material archive

Revision ID: 20260523_1020
Revises: 20260523_1010
Create Date: 2026-05-23 20:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260523_1020"
down_revision: str | None = "20260523_1010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "crm_customer_certification_material",
        "customer_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "crm_customer_certification_material",
        "customer_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
