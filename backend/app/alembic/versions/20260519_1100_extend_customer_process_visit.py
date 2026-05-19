"""extend customer process visit fields

Revision ID: 20260519_1100
Revises: 20260519_0900
Create Date: 2026-05-19 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260519_1100"
down_revision: str | None = "20260519_0900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("crm_customer_process_record", sa.Column("appointment_slot", sa.String(length=32), nullable=True, comment="预约时段"))
    op.add_column("crm_customer_process_record", sa.Column("visit_purpose", sa.String(length=32), nullable=True, comment="到访目的"))
    op.add_column("crm_customer_process_record", sa.Column("promised_gift", sa.String(length=255), nullable=True, comment="承诺礼品"))
    op.add_column("crm_customer_process_record", sa.Column("appointment_status", sa.String(length=32), nullable=True, comment="预约状态"))
    op.add_column("crm_customer_process_record", sa.Column("checked_in_at", sa.DateTime(), nullable=True, comment="核销到店时间"))
    op.add_column("crm_customer_process_record", sa.Column("checked_in_user_id", sa.Integer(), nullable=True, comment="核销人ID"))
    op.create_index("ix_crm_customer_process_record_appointment_slot", "crm_customer_process_record", ["appointment_slot"], unique=False)
    op.create_index("ix_crm_customer_process_record_visit_purpose", "crm_customer_process_record", ["visit_purpose"], unique=False)
    op.create_index("ix_crm_customer_process_record_appointment_status", "crm_customer_process_record", ["appointment_status"], unique=False)
    op.create_index("ix_crm_customer_process_record_checked_in_at", "crm_customer_process_record", ["checked_in_at"], unique=False)
    op.create_index("ix_crm_customer_process_record_checked_in_user_id", "crm_customer_process_record", ["checked_in_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_crm_customer_process_record_checked_in_user_id", table_name="crm_customer_process_record")
    op.drop_index("ix_crm_customer_process_record_checked_in_at", table_name="crm_customer_process_record")
    op.drop_index("ix_crm_customer_process_record_appointment_status", table_name="crm_customer_process_record")
    op.drop_index("ix_crm_customer_process_record_visit_purpose", table_name="crm_customer_process_record")
    op.drop_index("ix_crm_customer_process_record_appointment_slot", table_name="crm_customer_process_record")
    op.drop_column("crm_customer_process_record", "checked_in_user_id")
    op.drop_column("crm_customer_process_record", "checked_in_at")
    op.drop_column("crm_customer_process_record", "appointment_status")
    op.drop_column("crm_customer_process_record", "promised_gift")
    op.drop_column("crm_customer_process_record", "visit_purpose")
    op.drop_column("crm_customer_process_record", "appointment_slot")
