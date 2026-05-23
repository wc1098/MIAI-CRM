"""add contract review fields

Revision ID: 20260520_0900
Revises: 20260519_1420
Create Date: 2026-05-20 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260520_0900"
down_revision: str | None = "20260519_1420"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("crm_contract", sa.Column("review_submitted_at", sa.DateTime(), nullable=True, comment="提交审核时间"))
    op.add_column("crm_contract", sa.Column("reviewed_at", sa.DateTime(), nullable=True, comment="审核时间"))
    op.add_column("crm_contract", sa.Column("reviewed_by", sa.Integer(), nullable=True, comment="审核人ID"))
    op.add_column("crm_contract", sa.Column("review_remark", sa.Text(), nullable=True, comment="审核备注"))
    op.create_index(op.f("ix_crm_contract_review_submitted_at"), "crm_contract", ["review_submitted_at"], unique=False)
    op.create_index(op.f("ix_crm_contract_reviewed_at"), "crm_contract", ["reviewed_at"], unique=False)
    op.create_index(op.f("ix_crm_contract_reviewed_by"), "crm_contract", ["reviewed_by"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_crm_contract_reviewed_by"), table_name="crm_contract")
    op.drop_index(op.f("ix_crm_contract_reviewed_at"), table_name="crm_contract")
    op.drop_index(op.f("ix_crm_contract_review_submitted_at"), table_name="crm_contract")
    op.drop_column("crm_contract", "review_remark")
    op.drop_column("crm_contract", "reviewed_by")
    op.drop_column("crm_contract", "reviewed_at")
    op.drop_column("crm_contract", "review_submitted_at")
