"""extend contract receipt payment fields

Revision ID: 20260519_1420
Revises: 20260519_1410
Create Date: 2026-05-19 20:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260519_1420"
down_revision: str | None = "20260519_1410"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table_name: str) -> set[str]:
    return {row["name"] for row in sa.inspect(op.get_bind()).get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    return {row["name"] for row in sa.inspect(op.get_bind()).get_indexes(table_name)}


def _create_index(table_name: str, column_name: str) -> None:
    index_name = f"ix_{table_name}_{column_name}"
    if index_name not in _indexes(table_name):
        op.create_index(index_name, table_name, [column_name])


def upgrade() -> None:
    table_name = "crm_contract_receipt"
    columns = _columns(table_name)
    additions = [
        ("order_id", sa.Column("order_id", sa.Integer(), nullable=True, comment="支付订单ID")),
        ("payment_id", sa.Column("payment_id", sa.Integer(), nullable=True, comment="支付流水ID")),
        ("paid_at", sa.Column("paid_at", sa.DateTime(), nullable=True, comment="支付成功时间")),
        ("confirmed_at", sa.Column("confirmed_at", sa.DateTime(), nullable=True, comment="确认时间")),
        ("confirmed_by", sa.Column("confirmed_by", sa.Integer(), nullable=True, comment="确认人ID")),
        ("voided_at", sa.Column("voided_at", sa.DateTime(), nullable=True, comment="作废时间")),
        ("voided_by", sa.Column("voided_by", sa.Integer(), nullable=True, comment="作废人ID")),
        ("void_reason", sa.Column("void_reason", sa.Text(), nullable=True, comment="作废原因")),
        ("reverse_receipt_id", sa.Column("reverse_receipt_id", sa.Integer(), nullable=True, comment="关联原收款单ID")),
        ("reverse_reason", sa.Column("reverse_reason", sa.Text(), nullable=True, comment="冲正/退款原因")),
        ("channel_trade_no", sa.Column("channel_trade_no", sa.String(length=128), nullable=True, comment="渠道交易号")),
        ("payment_payload", sa.Column("payment_payload", sa.JSON(), nullable=True, comment="支付/确认扩展信息")),
    ]
    for column_name, column in additions:
        if column_name not in columns:
            op.add_column(table_name, column)
            if column_name != "payment_payload":
                _create_index(table_name, column_name)

    fks = {fk["name"] for fk in sa.inspect(op.get_bind()).get_foreign_keys(table_name)}
    if "fk_crm_contract_receipt_order_id_payment_order" not in fks:
        op.create_foreign_key(
            "fk_crm_contract_receipt_order_id_payment_order",
            table_name,
            "payment_order",
            ["order_id"],
            ["id"],
            ondelete="SET NULL",
            onupdate="CASCADE",
        )
    if "fk_crm_contract_receipt_payment_id_payment_record" not in fks:
        op.create_foreign_key(
            "fk_crm_contract_receipt_payment_id_payment_record",
            table_name,
            "payment_record",
            ["payment_id"],
            ["id"],
            ondelete="SET NULL",
            onupdate="CASCADE",
        )


def downgrade() -> None:
    table_name = "crm_contract_receipt"
    fks = {fk["name"] for fk in sa.inspect(op.get_bind()).get_foreign_keys(table_name)}
    if "fk_crm_contract_receipt_payment_id_payment_record" in fks:
        op.drop_constraint("fk_crm_contract_receipt_payment_id_payment_record", table_name, type_="foreignkey")
    if "fk_crm_contract_receipt_order_id_payment_order" in fks:
        op.drop_constraint("fk_crm_contract_receipt_order_id_payment_order", table_name, type_="foreignkey")

    columns = _columns(table_name)
    for column_name in [
        "payment_payload",
        "channel_trade_no",
        "reverse_reason",
        "reverse_receipt_id",
        "void_reason",
        "voided_by",
        "voided_at",
        "confirmed_by",
        "confirmed_at",
        "paid_at",
        "payment_id",
        "order_id",
    ]:
        if column_name in columns:
            op.drop_column(table_name, column_name)
