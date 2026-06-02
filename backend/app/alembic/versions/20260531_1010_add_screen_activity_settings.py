"""add screen activity settings columns

Revision ID: 20260531_1010
Revises: 20260531_1000
Create Date: 2026-05-31 10:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260531_1010"
down_revision: str | None = "20260531_1000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "screen_activity_config" not in _tables():
        return
    columns = _columns("screen_activity_config")
    if "screen_name" not in columns:
        op.add_column("screen_activity_config", sa.Column("screen_name", sa.String(length=128), nullable=True, comment="大屏名称"))
    if "theme_config" not in columns:
        op.add_column("screen_activity_config", sa.Column("theme_config", sa.JSON(), nullable=True, comment="画面配置"))
    if "module_config" not in columns:
        op.add_column("screen_activity_config", sa.Column("module_config", sa.JSON(), nullable=True, comment="功能模块配置"))


def downgrade() -> None:
    if "screen_activity_config" not in _tables():
        return
    columns = _columns("screen_activity_config")
    for column in ["module_config", "theme_config", "screen_name"]:
        if column in columns:
            op.drop_column("screen_activity_config", column)
