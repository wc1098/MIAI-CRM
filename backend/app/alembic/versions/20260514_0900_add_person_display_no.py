"""add person display no

Revision ID: 20260514_0900
Revises: 20260513_1630
Create Date: 2026-05-14 09:00:00

"""

from collections.abc import Sequence
from random import SystemRandom

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "20260514_0900"
down_revision: str | None = "20260513_1630"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    return {index["name"] for index in inspect(op.get_bind()).get_indexes(table_name)}


def _generate(existing: set[str]) -> str:
    random = SystemRandom()
    for _ in range(200):
        value = str(random.randrange(1000000, 10000000))
        if value not in existing:
            existing.add(value)
            return value
    raise RuntimeError("无法生成唯一人员展示编号")


def upgrade() -> None:
    bind = op.get_bind()
    if "display_no" not in _columns("crm_person"):
        op.add_column("crm_person", sa.Column("display_no", sa.String(length=7), nullable=True, comment="对外展示编号"))

    rows = bind.execute(text("select id, display_no from crm_person where is_deleted = false order by id")).mappings().all()
    existing = {str(row["display_no"]) for row in rows if row["display_no"]}
    for row in rows:
        if row["display_no"]:
            continue
        bind.execute(
            text("update crm_person set display_no = :display_no where id = :id"),
            {"display_no": _generate(existing), "id": row["id"]},
        )

    index_name = op.f("ix_crm_person_display_no")
    if index_name not in _indexes("crm_person"):
        op.create_index(index_name, "crm_person", ["display_no"], unique=True)


def downgrade() -> None:
    index_name = op.f("ix_crm_person_display_no")
    if index_name in _indexes("crm_person"):
        op.drop_index(index_name, table_name="crm_person")
    if "display_no" in _columns("crm_person"):
        op.drop_column("crm_person", "display_no")
