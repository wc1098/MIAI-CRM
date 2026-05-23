"""cleanup legacy candidate menu

Revision ID: 20260523_1010
Revises: 20260523_1000
Create Date: 2026-05-23 18:58:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260523_1010"
down_revision: str | None = "20260523_1000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            select id
            from sys_menu
            where route_path = '/miailove/candidate'
               or route_path = '/miailove/candidate/list'
            """
        )
    ).all()
    ids = [row.id for row in rows]
    if not ids:
        return
    bind.execute(sa.text("delete from sys_role_menus where menu_id = any(:ids)").bindparams(sa.bindparam("ids", value=ids)))
    bind.execute(
        sa.text(
            """
            update sys_menu
            set status = '1',
                is_deleted = true,
                deleted_time = now()
            where id = any(:ids)
            """
        ).bindparams(sa.bindparam("ids", value=ids))
    )


def downgrade() -> None:
    pass
