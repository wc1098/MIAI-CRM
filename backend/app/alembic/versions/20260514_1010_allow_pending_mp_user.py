"""allow pending mini program user

Revision ID: 20260514_1010
Revises: 20260514_0900
Create Date: 2026-05-14 10:10:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "20260514_1010"
down_revision: str | None = "20260514_0900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    if "openid" in _columns("mini_program_user"):
        op.alter_column(
            "mini_program_user",
            "openid",
            existing_type=sa.String(length=128),
            nullable=True,
            existing_comment="微信openid",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if "openid" in _columns("mini_program_user"):
        rows = bind.execute(text("select id from mini_program_user where openid is null order by id")).mappings().all()
        for row in rows:
            bind.execute(
                text("update mini_program_user set openid = :openid where id = :id"),
                {"openid": f"offline:{row['id']}", "id": row["id"]},
            )
        op.alter_column(
            "mini_program_user",
            "openid",
            existing_type=sa.String(length=128),
            nullable=False,
            existing_comment="微信openid",
        )
