"""person based staff certification

Revision ID: 20260528_1010
Revises: 20260528_1000
Create Date: 2026-05-28 10:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260528_1010"
down_revision: str | None = "20260528_1000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table_name: str) -> set[str]:
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table_name)}


def _drop_fk(table_name: str, constrained_columns: list[str], referred_table: str) -> None:
    inspector = sa.inspect(op.get_bind())
    for fk in inspector.get_foreign_keys(table_name):
        if fk.get("constrained_columns") == constrained_columns and fk.get("referred_table") == referred_table and fk.get("name"):
            op.drop_constraint(fk["name"], table_name, type_="foreignkey")


def upgrade() -> None:
    tables = _tables()
    if "certification_application" in tables and "user_id" in _columns("certification_application"):
        _drop_fk("certification_application", ["user_id"], "mini_program_user")
        op.alter_column("certification_application", "user_id", existing_type=sa.Integer(), nullable=True)
        op.create_foreign_key(
            "fk_certification_application_user_id_mini_program_user",
            "certification_application",
            "mini_program_user",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
            onupdate="CASCADE",
        )
    if "certification_record" in tables and "user_id" in _columns("certification_record"):
        op.alter_column("certification_record", "user_id", existing_type=sa.Integer(), nullable=True)
    if "certification_material" in tables and "user_id" in _columns("certification_material"):
        op.alter_column("certification_material", "user_id", existing_type=sa.Integer(), nullable=True)

    if {"mini_program_user", "certification_application", "certification_record", "certification_material"}.issubset(tables):
        bind = op.get_bind()
        bind.execute(
            sa.text(
                """
                with staff_apps as (
                    select ca.id as app_id, ca.user_id
                    from certification_application ca
                    join mini_program_user mu on mu.id = ca.user_id
                    where ca.description = 'staff_upload'
                      and ca.is_deleted = false
                      and mu.openid is null
                      and mu.registered_at is null
                      and mu.mobile is null
                )
                update certification_material cm
                   set user_id = null
                  from staff_apps sa
                 where cm.application_id = sa.app_id
                """
            )
        )
        bind.execute(
            sa.text(
                """
                with staff_apps as (
                    select ca.id as app_id, ca.user_id
                    from certification_application ca
                    join mini_program_user mu on mu.id = ca.user_id
                    where ca.description = 'staff_upload'
                      and ca.is_deleted = false
                      and mu.openid is null
                      and mu.registered_at is null
                      and mu.mobile is null
                )
                update certification_record cr
                   set user_id = null
                  from staff_apps sa
                 where cr.application_id = sa.app_id
                """
            )
        )
        bind.execute(
            sa.text(
                """
                with staff_apps as (
                    select ca.id as app_id, ca.user_id
                    from certification_application ca
                    join mini_program_user mu on mu.id = ca.user_id
                    where ca.description = 'staff_upload'
                      and ca.is_deleted = false
                      and mu.openid is null
                      and mu.registered_at is null
                      and mu.mobile is null
                )
                update certification_application ca
                   set user_id = null
                  from staff_apps sa
                 where ca.id = sa.app_id
                """
            )
        )
        bind.execute(
            sa.text(
                """
                update mini_program_user mu
                   set is_deleted = true,
                       deleted_time = now(),
                       description = coalesce(mu.description, '工作人员认证资料历史占位用户已迁移为person维度认证')
                 where mu.openid is null
                   and mu.registered_at is null
                   and mu.mobile is null
                   and exists (
                       select 1
                         from certification_application ca
                        where ca.person_id = mu.person_id
                          and ca.description = 'staff_upload'
                          and ca.user_id is null
                   )
                """
            )
        )


def downgrade() -> None:
    tables = _tables()
    if "certification_application" in tables and "user_id" in _columns("certification_application"):
        _drop_fk("certification_application", ["user_id"], "mini_program_user")
        op.alter_column("certification_application", "user_id", existing_type=sa.Integer(), nullable=False)
        op.create_foreign_key(
            "fk_certification_application_user_id_mini_program_user",
            "certification_application",
            "mini_program_user",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
        )
    if "certification_record" in tables and "user_id" in _columns("certification_record"):
        op.alter_column("certification_record", "user_id", existing_type=sa.Integer(), nullable=False)
    if "certification_material" in tables and "user_id" in _columns("certification_material"):
        op.alter_column("certification_material", "user_id", existing_type=sa.Integer(), nullable=False)
