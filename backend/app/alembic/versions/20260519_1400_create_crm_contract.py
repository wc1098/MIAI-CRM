"""create crm contract

Revision ID: 20260519_1400
Revises: 20260519_1300
Create Date: 2026-05-19 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260519_1400"
down_revision: str | None = "20260519_1300"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _indexes(table_name: str) -> set[str]:
    return {row["name"] for row in sa.inspect(op.get_bind()).get_indexes(table_name)}


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("uuid", sa.String(length=64), nullable=False, comment="UUID全局唯一标识"),
        sa.Column("status", sa.String(length=10), nullable=False, comment="状态(0:正常 1:禁用)"),
        sa.Column("description", sa.Text(), nullable=True, comment="备注/描述"),
        sa.Column("created_time", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_time", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, comment="是否已删除(0:未删除 1:已删除)"),
        sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
        sa.Column("created_id", sa.Integer(), nullable=True, comment="创建人ID"),
        sa.Column("updated_id", sa.Integer(), nullable=True, comment="更新人ID"),
        sa.Column("deleted_id", sa.Integer(), nullable=True, comment="删除人ID"),
    ]


def _audit_constraints() -> list[sa.ForeignKeyConstraint | sa.UniqueConstraint | sa.PrimaryKeyConstraint]:
    return [
        sa.ForeignKeyConstraint(["created_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["deleted_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["updated_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    ]


def _create_indexes(table_name: str, columns: list[str]) -> None:
    existing = _indexes(table_name)
    for column in columns + ["uuid", "status", "created_time", "updated_time", "is_deleted", "deleted_time", "created_id", "updated_id", "deleted_id"]:
        index_name = f"ix_{table_name}_{column}"
        if index_name not in existing:
            op.create_index(index_name, table_name, [column])


def upgrade() -> None:
    tables = _tables()
    if "crm_contract" not in tables:
        op.create_table(
            "crm_contract",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("contract_no", sa.String(length=64), nullable=False, comment="合同编号"),
            sa.Column("contract_name", sa.String(length=128), nullable=False, comment="合同名称"),
            sa.Column("customer_id", sa.Integer(), nullable=False, comment="客户ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("store_id", sa.Integer(), nullable=False, comment="门店ID"),
            sa.Column("owner_user_id", sa.Integer(), nullable=False, comment="销售ID"),
            sa.Column("vip_level", sa.String(length=32), nullable=False, comment="授予VIP等级"),
            sa.Column("contract_status", sa.String(length=32), nullable=False, comment="合同状态"),
            sa.Column("original_amount", sa.Numeric(12, 2), nullable=False, comment="产品原价合计"),
            sa.Column("contract_amount", sa.Numeric(12, 2), nullable=False, comment="合同总金额"),
            sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, comment="折扣金额"),
            sa.Column("discount_rate", sa.Numeric(8, 4), nullable=False, comment="折扣率"),
            sa.Column("discount_reason", sa.Text(), nullable=True, comment="折扣原因"),
            sa.Column("start_date", sa.Date(), nullable=False, comment="合同开始日期"),
            sa.Column("end_date", sa.Date(), nullable=False, comment="合同结束日期"),
            sa.Column("signer_name", sa.String(length=64), nullable=False, comment="合同签署人"),
            sa.Column("signed_at", sa.DateTime(), nullable=True, comment="签署时间"),
            sa.Column("effective_at", sa.DateTime(), nullable=True, comment="生效时间"),
            sa.Column("first_paid_at", sa.DateTime(), nullable=True, comment="首付款到账时间"),
            sa.Column("voided_at", sa.DateTime(), nullable=True, comment="作废时间"),
            sa.Column("void_reason", sa.Text(), nullable=True, comment="作废原因"),
            sa.Column("remark", sa.Text(), nullable=True, comment="备注"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["customer_id"], ["crm_customer_profile.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["owner_user_id"], ["sys_user.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["store_id"], ["sys_dept.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            *_audit_constraints(),
            sa.UniqueConstraint("contract_no"),
            comment="CRM合同表",
        )
    _create_indexes("crm_contract", ["brand_id", "contract_no", "customer_id", "person_id", "store_id", "owner_user_id", "vip_level", "contract_status", "signed_at", "effective_at", "first_paid_at", "voided_at"])

    if "crm_contract_item" not in tables:
        op.create_table(
            "crm_contract_item",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("contract_id", sa.Integer(), nullable=False, comment="合同ID"),
            sa.Column("product_id", sa.Integer(), nullable=True, comment="产品ID"),
            sa.Column("product_name_snapshot", sa.String(length=128), nullable=False, comment="产品名称快照"),
            sa.Column("price_snapshot", sa.Numeric(12, 2), nullable=False, comment="价格快照"),
            sa.Column("service_days_snapshot", sa.Integer(), nullable=False, comment="服务时长快照"),
            sa.Column("recommendation_quota_snapshot", sa.Integer(), nullable=False, comment="推荐次数快照"),
            sa.Column("meeting_quota_snapshot", sa.Integer(), nullable=False, comment="约见次数快照"),
            sa.Column("course_quota_snapshot", sa.Integer(), nullable=False, comment="课程次数快照"),
            sa.Column("supports_online_meeting_snapshot", sa.Boolean(), nullable=False, comment="线上约见快照"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["contract_id"], ["crm_contract.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["product_id"], ["crm_product_package.id"], ondelete="SET NULL", onupdate="CASCADE"),
            *_audit_constraints(),
            comment="CRM合同产品明细表",
        )
    _create_indexes("crm_contract_item", ["brand_id", "contract_id", "product_id"])

    if "crm_contract_attachment" not in tables:
        op.create_table(
            "crm_contract_attachment",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("contract_id", sa.Integer(), nullable=False, comment="合同ID"),
            sa.Column("file_name", sa.String(length=255), nullable=True, comment="文件名"),
            sa.Column("file_path", sa.String(length=512), nullable=True, comment="文件路径"),
            sa.Column("file_url", sa.String(length=1000), nullable=False, comment="文件URL"),
            sa.Column("file_type", sa.String(length=32), nullable=False, comment="文件类型"),
            sa.Column("page_count", sa.Integer(), nullable=True, comment="页数"),
            sa.Column("attachment_status", sa.String(length=32), nullable=False, comment="附件状态"),
            sa.Column("payload", sa.JSON(), nullable=True, comment="扩展信息"),
            sa.Column("voided_at", sa.DateTime(), nullable=True, comment="作废时间"),
            sa.Column("voided_by", sa.Integer(), nullable=True, comment="作废人ID"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["contract_id"], ["crm_contract.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            *_audit_constraints(),
            comment="CRM合同影像附件表",
        )
    _create_indexes("crm_contract_attachment", ["brand_id", "contract_id", "file_type", "attachment_status", "voided_at", "voided_by"])

    if "crm_contract_receipt" not in tables:
        op.create_table(
            "crm_contract_receipt",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("receipt_no", sa.String(length=64), nullable=False, comment="收款单号"),
            sa.Column("contract_id", sa.Integer(), nullable=False, comment="合同ID"),
            sa.Column("customer_id", sa.Integer(), nullable=False, comment="客户ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("store_id", sa.Integer(), nullable=False, comment="门店ID"),
            sa.Column("receipt_type", sa.String(length=32), nullable=False, comment="收款类型"),
            sa.Column("pay_method", sa.String(length=32), nullable=False, comment="支付方式"),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False, comment="收款金额"),
            sa.Column("receipt_status", sa.String(length=32), nullable=False, comment="收款状态"),
            sa.Column("payment_scene", sa.String(length=32), nullable=False, comment="支付场景"),
            sa.Column("submitted_at", sa.DateTime(), nullable=False, comment="提交时间"),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True, comment="复核时间"),
            sa.Column("reviewed_by", sa.Integer(), nullable=True, comment="复核人ID"),
            sa.Column("review_remark", sa.Text(), nullable=True, comment="复核备注"),
            sa.Column("remark", sa.Text(), nullable=True, comment="备注"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["contract_id"], ["crm_contract.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            *_audit_constraints(),
            sa.UniqueConstraint("receipt_no"),
            comment="CRM合同收款记录表",
        )
    _create_indexes("crm_contract_receipt", ["brand_id", "receipt_no", "contract_id", "customer_id", "person_id", "store_id", "receipt_type", "pay_method", "receipt_status", "payment_scene", "submitted_at", "reviewed_at", "reviewed_by"])

    if "crm_vip_profile" not in tables:
        op.create_table(
            "crm_vip_profile",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("customer_id", sa.Integer(), nullable=False, comment="来源客户ID"),
            sa.Column("contract_id", sa.Integer(), nullable=False, comment="来源合同ID"),
            sa.Column("store_id", sa.Integer(), nullable=False, comment="服务门店ID"),
            sa.Column("service_owner_user_id", sa.Integer(), nullable=True, comment="服务红娘ID"),
            sa.Column("vip_level", sa.String(length=32), nullable=False, comment="VIP等级"),
            sa.Column("vip_status", sa.String(length=32), nullable=False, comment="VIP状态"),
            sa.Column("started_at", sa.DateTime(), nullable=False, comment="开始时间"),
            sa.Column("ended_at", sa.DateTime(), nullable=True, comment="结束时间"),
            sa.Column("source_receipt_id", sa.Integer(), nullable=True, comment="触发收款ID"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["contract_id"], ["crm_contract.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["customer_id"], ["crm_customer_profile.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["service_owner_user_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["store_id"], ["sys_dept.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            *_audit_constraints(),
            comment="CRM VIP服务身份表",
        )
    _create_indexes("crm_vip_profile", ["brand_id", "person_id", "customer_id", "contract_id", "store_id", "service_owner_user_id", "vip_level", "vip_status", "started_at", "ended_at", "source_receipt_id"])


def downgrade() -> None:
    for table_name in ["crm_vip_profile", "crm_contract_receipt", "crm_contract_attachment", "crm_contract_item", "crm_contract"]:
        if table_name in _tables():
            op.drop_table(table_name)
