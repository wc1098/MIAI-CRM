"""expand sys_param config value

Revision ID: 20260511_0010
Revises: 20260510_2238
Create Date: 2026-05-11 00:10:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260511_0010"
down_revision: Union[str, None] = "20260510_2238"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "sys_param",
        "config_value",
        existing_type=sa.String(length=500),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "sys_param",
        "config_value",
        existing_type=sa.Text(),
        type_=sa.String(length=500),
        existing_nullable=True,
    )
