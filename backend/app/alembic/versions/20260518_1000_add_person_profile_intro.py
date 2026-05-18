"""add person profile intro

Revision ID: 20260518_1000
Revises: 20260517_1200
Create Date: 2026-05-18 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "20260518_1000"
down_revision = "20260517_1200"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "profile_intro" not in _columns("crm_person"):
        op.add_column("crm_person", sa.Column("profile_intro", sa.Text(), nullable=True, comment="个人介绍"))


def downgrade() -> None:
    if "profile_intro" in _columns("crm_person"):
        op.drop_column("crm_person", "profile_intro")
