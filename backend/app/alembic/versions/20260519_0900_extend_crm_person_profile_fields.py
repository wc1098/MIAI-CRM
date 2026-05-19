"""extend crm person profile fields

Revision ID: 20260519_0900
Revises: 20260518_1500
Create Date: 2026-05-19 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260519_0900"
down_revision: str | None = "20260518_1500"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("crm_person", sa.Column("weight_kg", sa.Integer(), nullable=True, comment="体重kg"))
    op.add_column("crm_person", sa.Column("occupation_code", sa.String(length=32), nullable=True, comment="标准职业"))
    op.add_column("crm_person", sa.Column("graduated_school", sa.String(length=128), nullable=True, comment="毕业院校"))
    op.add_column("crm_person", sa.Column("major", sa.String(length=128), nullable=True, comment="专业"))
    op.add_column("crm_person", sa.Column("unit_type", sa.String(length=32), nullable=True, comment="单位类型"))
    op.add_column("crm_person", sa.Column("job_title", sa.String(length=64), nullable=True, comment="职务"))
    op.add_column("crm_person", sa.Column("work_company", sa.String(length=128), nullable=True, comment="工作单位"))
    op.add_column(
        "crm_person",
        sa.Column("accept_long_distance_self", sa.Boolean(), nullable=True, comment="本人是否接受异地"),
    )
    op.add_column(
        "crm_person",
        sa.Column("accept_flash_marriage", sa.Boolean(), nullable=True, comment="本人是否接受闪婚"),
    )
    op.add_column("crm_person", sa.Column("willing_relocate", sa.Boolean(), nullable=True, comment="本人是否愿意搬家"))
    op.add_column("crm_person", sa.Column("marriage_plan", sa.String(length=32), nullable=True, comment="结婚计划"))
    op.add_column("crm_person", sa.Column("family_background", sa.Text(), nullable=True, comment="家庭情况"))
    op.add_column("crm_person", sa.Column("profile_remark", sa.Text(), nullable=True, comment="档案备注"))
    op.create_index("ix_crm_person_occupation_code", "crm_person", ["occupation_code"], unique=False)
    op.create_index("ix_crm_person_unit_type", "crm_person", ["unit_type"], unique=False)
    op.create_index("ix_crm_person_marriage_plan", "crm_person", ["marriage_plan"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_crm_person_marriage_plan", table_name="crm_person")
    op.drop_index("ix_crm_person_unit_type", table_name="crm_person")
    op.drop_index("ix_crm_person_occupation_code", table_name="crm_person")
    op.drop_column("crm_person", "profile_remark")
    op.drop_column("crm_person", "family_background")
    op.drop_column("crm_person", "marriage_plan")
    op.drop_column("crm_person", "willing_relocate")
    op.drop_column("crm_person", "accept_flash_marriage")
    op.drop_column("crm_person", "accept_long_distance_self")
    op.drop_column("crm_person", "work_company")
    op.drop_column("crm_person", "job_title")
    op.drop_column("crm_person", "unit_type")
    op.drop_column("crm_person", "major")
    op.drop_column("crm_person", "graduated_school")
    op.drop_column("crm_person", "occupation_code")
    op.drop_column("crm_person", "weight_kg")
