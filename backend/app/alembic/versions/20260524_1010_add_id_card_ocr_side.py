"""add id card ocr side

Revision ID: 20260524_1010
Revises: 20260524_1000
Create Date: 2026-05-24 14:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260524_1010"
down_revision: str | None = "20260524_1000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    table_name = "id_card_ocr_log"
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return
    columns = {row["name"] for row in inspector.get_columns(table_name)}
    if "id_card_side" not in columns:
        op.add_column(table_name, sa.Column("id_card_side", sa.String(length=16), nullable=True, comment="身份证面"))
    indexes = {row["name"] for row in inspector.get_indexes(table_name)}
    if "ix_id_card_ocr_log_id_card_side" not in indexes:
        op.create_index("ix_id_card_ocr_log_id_card_side", table_name, ["id_card_side"], unique=False)


def downgrade() -> None:
    table_name = "id_card_ocr_log"
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return
    indexes = {row["name"] for row in inspector.get_indexes(table_name)}
    if "ix_id_card_ocr_log_id_card_side" in indexes:
        op.drop_index("ix_id_card_ocr_log_id_card_side", table_name=table_name)
    columns = {row["name"] for row in inspector.get_columns(table_name)}
    if "id_card_side" in columns:
        op.drop_column(table_name, "id_card_side")
