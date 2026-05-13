"""create crm lead

Revision ID: 20260512_1000
Revises: 20260511_0130
Create Date: 2026-05-12 10:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260512_1000"
down_revision: str | None = "20260511_0130"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _base_columns() -> list[sa.Column]:
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
        sa.ForeignKeyConstraint(["created_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["updated_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["deleted_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    ]


def _base_indexes(table_name: str) -> None:
    for column in [
        "created_id",
        "created_time",
        "deleted_id",
        "deleted_time",
        "id",
        "is_deleted",
        "status",
        "updated_id",
        "updated_time",
    ]:
        op.create_index(op.f(f"ix_{table_name}_{column}"), table_name, [column], unique=False)
    op.create_index(op.f(f"ix_{table_name}_uuid"), table_name, ["uuid"], unique=True)


def _drop_base_indexes(table_name: str) -> None:
    op.drop_index(op.f(f"ix_{table_name}_uuid"), table_name=table_name)
    for column in [
        "updated_time",
        "updated_id",
        "status",
        "is_deleted",
        "id",
        "deleted_time",
        "deleted_id",
        "created_time",
        "created_id",
    ]:
        op.drop_index(op.f(f"ix_{table_name}_{column}"), table_name=table_name)


def upgrade() -> None:
    op.create_table(
        "crm_person",
        sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
        sa.Column("name", sa.String(length=64), nullable=False, comment="姓名"),
        sa.Column("gender", sa.String(length=1), nullable=False, comment="性别"),
        sa.Column("primary_mobile", sa.String(length=20), nullable=False, comment="手机号"),
        sa.Column("wechat", sa.String(length=64), nullable=True, comment="微信号"),
        sa.Column("birth_date", sa.Date(), nullable=True, comment="出生日期"),
        sa.Column("height_cm", sa.Integer(), nullable=True, comment="身高cm"),
        sa.Column("ethnicity", sa.String(length=32), nullable=True, comment="民族"),
        sa.Column("occupation", sa.String(length=64), nullable=True, comment="职业"),
        sa.Column("annual_income", sa.String(length=32), nullable=True, comment="年收入"),
        sa.Column("marital_status", sa.String(length=32), nullable=True, comment="婚况"),
        sa.Column("education", sa.String(length=32), nullable=True, comment="学历"),
        sa.Column("hometown", sa.String(length=128), nullable=True, comment="籍贯"),
        sa.Column("residence", sa.String(length=128), nullable=True, comment="常驻地"),
        sa.Column("house_status", sa.String(length=32), nullable=True, comment="房产信息"),
        sa.Column("car_status", sa.String(length=32), nullable=True, comment="购车信息"),
        sa.Column("photo_urls", sa.JSON(), nullable=True, comment="照片相册URL列表"),
        *_base_columns(),
        comment="CRM人员主体表",
    )
    _base_indexes("crm_person")
    for column, unique in [("primary_mobile", True), ("brand_id", False), ("gender", False), ("wechat", False)]:
        op.create_index(op.f(f"ix_crm_person_{column}"), "crm_person", [column], unique=unique)

    op.create_table(
        "crm_lead_profile",
        sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
        sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
        sa.Column("store_id", sa.Integer(), nullable=True, comment="归属门店ID"),
        sa.Column("owner_sales_id", sa.Integer(), nullable=True, comment="归属销售ID"),
        sa.Column("pool_type", sa.String(length=32), nullable=False, comment="归属池"),
        sa.Column("lead_type", sa.String(length=32), nullable=False, comment="线索类型"),
        sa.Column("source_channel_code", sa.String(length=64), nullable=True, comment="来源渠道编码"),
        sa.Column("latest_follow_at", sa.DateTime(), nullable=True, comment="最后跟进时间"),
        sa.Column("next_follow_at", sa.DateTime(), nullable=True, comment="下次跟进时间"),
        sa.Column("assigned_at", sa.DateTime(), nullable=True, comment="最近分配/领取时间"),
        sa.Column("last_recycled_at", sa.DateTime(), nullable=True, comment="最近自动回收时间"),
        sa.Column("converted_customer_at", sa.DateTime(), nullable=True, comment="转建档客户时间"),
        *_base_columns(),
        sa.ForeignKeyConstraint(["owner_sales_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["store_id"], ["sys_dept.id"], ondelete="SET NULL", onupdate="CASCADE"),
        comment="CRM线索表",
    )
    _base_indexes("crm_lead_profile")
    for column in [
        "brand_id",
        "person_id",
        "store_id",
        "owner_sales_id",
        "pool_type",
        "lead_type",
        "source_channel_code",
        "latest_follow_at",
        "next_follow_at",
        "assigned_at",
    ]:
        op.create_index(op.f(f"ix_crm_lead_profile_{column}"), "crm_lead_profile", [column], unique=False)

    op.create_table(
        "crm_lead_process_record",
        sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
        sa.Column("lead_id", sa.Integer(), nullable=False, comment="线索ID"),
        sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
        sa.Column("action_type", sa.String(length=32), nullable=False, comment="动作类型"),
        sa.Column("follow_method", sa.String(length=32), nullable=True, comment="跟进方式"),
        sa.Column("content", sa.Text(), nullable=False, comment="跟进内容/原因"),
        sa.Column("next_follow_at", sa.DateTime(), nullable=True, comment="下次跟进时间"),
        sa.Column("operator_user_id", sa.Integer(), nullable=True, comment="执行人ID"),
        *_base_columns(),
        sa.ForeignKeyConstraint(["lead_id"], ["crm_lead_profile.id"], ondelete="RESTRICT", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["operator_user_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
        comment="CRM线索过程记录表",
    )
    _base_indexes("crm_lead_process_record")
    for column in ["brand_id", "lead_id", "person_id", "action_type", "follow_method", "next_follow_at", "operator_user_id"]:
        op.create_index(op.f(f"ix_crm_lead_process_record_{column}"), "crm_lead_process_record", [column], unique=False)

    op.create_table(
        "crm_lead_lifecycle",
        sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
        sa.Column("lead_id", sa.Integer(), nullable=False, comment="线索ID"),
        sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
        sa.Column("operation_type", sa.String(length=32), nullable=False, comment="操作类型"),
        sa.Column("operator_user_id", sa.Integer(), nullable=True, comment="执行人ID"),
        sa.Column("change_detail", sa.JSON(), nullable=True, comment="变更详情"),
        sa.Column("remark", sa.Text(), nullable=True, comment="备注"),
        *_base_columns(),
        comment="CRM线索生命周期表",
    )
    _base_indexes("crm_lead_lifecycle")
    for column in ["brand_id", "lead_id", "person_id", "operation_type", "operator_user_id"]:
        op.create_index(op.f(f"ix_crm_lead_lifecycle_{column}"), "crm_lead_lifecycle", [column], unique=False)

    op.create_table(
        "crm_lead_store_rule",
        sa.Column("store_id", sa.Integer(), nullable=False, comment="门店ID"),
        sa.Column("allow_sales_claim", sa.Boolean(), nullable=False, comment="是否允许销售自领"),
        sa.Column("no_follow_reclaim_days", sa.Integer(), nullable=False, comment="无跟进回收天数"),
        *_base_columns(),
        sa.ForeignKeyConstraint(["store_id"], ["sys_dept.id"], ondelete="CASCADE", onupdate="CASCADE"),
        comment="CRM门店线索规则表",
    )
    _base_indexes("crm_lead_store_rule")
    op.create_index(op.f("ix_crm_lead_store_rule_store_id"), "crm_lead_store_rule", ["store_id"], unique=True)

    op.create_table(
        "crm_lead_import_batch",
        sa.Column("file_name", sa.String(length=255), nullable=True, comment="导入文件名"),
        sa.Column("success_count", sa.Integer(), nullable=False, comment="成功条数"),
        sa.Column("failed_count", sa.Integer(), nullable=False, comment="失败条数"),
        sa.Column("result_detail", sa.JSON(), nullable=True, comment="失败详情"),
        *_base_columns(),
        comment="CRM线索导入批次表",
    )
    _base_indexes("crm_lead_import_batch")


def downgrade() -> None:
    tables = [
        ("crm_lead_import_batch", []),
        ("crm_lead_store_rule", ["store_id"]),
        ("crm_lead_lifecycle", ["operator_user_id", "operation_type", "person_id", "lead_id", "brand_id"]),
        (
            "crm_lead_process_record",
            ["operator_user_id", "next_follow_at", "follow_method", "action_type", "person_id", "lead_id", "brand_id"],
        ),
        (
            "crm_lead_profile",
            [
                "assigned_at",
                "next_follow_at",
                "latest_follow_at",
                "source_channel_code",
                "lead_type",
                "pool_type",
                "owner_sales_id",
                "store_id",
                "person_id",
                "brand_id",
            ],
        ),
        ("crm_person", ["wechat", "gender", "brand_id", "primary_mobile"]),
    ]
    for table_name, columns in tables:
        for column in columns:
            op.drop_index(op.f(f"ix_{table_name}_{column}"), table_name=table_name)
        _drop_base_indexes(table_name)
        op.drop_table(table_name)
