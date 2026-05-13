"""align crm lead schema

Revision ID: 20260512_1100
Revises: 20260512_1000
Create Date: 2026-05-12 11:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20260512_1100"
down_revision: str | None = "20260512_1000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    return {index["name"] for index in inspect(op.get_bind()).get_indexes(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def _create_index_if_missing(table_name: str, column_name: str, unique: bool = False) -> None:
    index_name = op.f(f"ix_{table_name}_{column_name}")
    if index_name not in _indexes(table_name):
        op.create_index(index_name, table_name, [column_name], unique=unique)


def upgrade() -> None:
    _add_column_if_missing("crm_person", sa.Column("wechat", sa.String(length=64), nullable=True, comment="微信号"))
    _add_column_if_missing("crm_person", sa.Column("height_cm", sa.Integer(), nullable=True, comment="身高cm"))
    _add_column_if_missing("crm_person", sa.Column("ethnicity", sa.String(length=32), nullable=True, comment="民族"))
    _add_column_if_missing("crm_person", sa.Column("occupation", sa.String(length=64), nullable=True, comment="职业"))
    _add_column_if_missing("crm_person", sa.Column("annual_income", sa.String(length=32), nullable=True, comment="年收入"))
    _add_column_if_missing("crm_person", sa.Column("marital_status", sa.String(length=32), nullable=True, comment="婚况"))
    _add_column_if_missing("crm_person", sa.Column("education", sa.String(length=32), nullable=True, comment="学历"))
    _add_column_if_missing("crm_person", sa.Column("hometown", sa.String(length=128), nullable=True, comment="籍贯"))
    _add_column_if_missing("crm_person", sa.Column("residence", sa.String(length=128), nullable=True, comment="常驻地"))
    _add_column_if_missing("crm_person", sa.Column("house_status", sa.String(length=32), nullable=True, comment="房产信息"))
    _add_column_if_missing("crm_person", sa.Column("car_status", sa.String(length=32), nullable=True, comment="购车信息"))
    _add_column_if_missing("crm_person", sa.Column("photo_urls", sa.JSON(), nullable=True, comment="照片相册URL列表"))

    for column_name, unique in [
        ("wechat", False),
        ("ethnicity", False),
        ("occupation", False),
        ("annual_income", False),
        ("marital_status", False),
        ("education", False),
        ("residence", False),
        ("house_status", False),
        ("car_status", False),
    ]:
        _create_index_if_missing("crm_person", column_name, unique=unique)

    lead_columns = _columns("crm_lead_profile")
    if "lead_type" not in lead_columns:
        op.add_column("crm_lead_profile", sa.Column("lead_type", sa.String(length=32), nullable=True, comment="线索类型"))
        op.execute(
            """
            update crm_lead_profile
            set lead_type = case
                when lead_stage = 'invalid' or status = 'invalid' then 'invalid'
                when lead_stage = 'converted' or status = 'converted' then 'converted_customer'
                when owner_sales_id is not null then 'new'
                else 'pending'
            end
            """
        )
        op.alter_column("crm_lead_profile", "lead_type", nullable=False)

    _add_column_if_missing(
        "crm_lead_profile",
        sa.Column("source_channel_code", sa.String(length=64), nullable=True, comment="来源渠道编码"),
    )
    _add_column_if_missing(
        "crm_lead_profile",
        sa.Column("assigned_at", sa.DateTime(), nullable=True, comment="最近分配/领取时间"),
    )
    _add_column_if_missing(
        "crm_lead_profile",
        sa.Column("last_recycled_at", sa.DateTime(), nullable=True, comment="最近自动回收时间"),
    )
    _add_column_if_missing(
        "crm_lead_profile",
        sa.Column("converted_customer_at", sa.DateTime(), nullable=True, comment="转建档客户时间"),
    )

    for column_name in ["lead_type", "source_channel_code", "assigned_at"]:
        _create_index_if_missing("crm_lead_profile", column_name)


def downgrade() -> None:
    for table_name, column_names in {
        "crm_lead_profile": ["converted_customer_at", "last_recycled_at", "assigned_at", "source_channel_code", "lead_type"],
        "crm_person": [
            "photo_urls",
            "car_status",
            "house_status",
            "residence",
            "hometown",
            "education",
            "marital_status",
            "annual_income",
            "occupation",
            "ethnicity",
            "height_cm",
            "wechat",
        ],
    }.items():
        existing_columns = _columns(table_name)
        for column_name in column_names:
            if column_name in existing_columns:
                op.drop_column(table_name, column_name)
