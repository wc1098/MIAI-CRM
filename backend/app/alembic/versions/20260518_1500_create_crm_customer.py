"""create crm customer

Revision ID: 20260518_1500
Revises: 20260518_1000
Create Date: 2026-05-18 15:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "20260518_1500"
down_revision = "20260518_1000"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tables = _tables()
    if "crm_customer_profile" not in tables:
        op.create_table(
            "crm_customer_profile",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("lead_id", sa.Integer(), nullable=True, comment="来源线索ID"),
            sa.Column("store_id", sa.Integer(), nullable=False, comment="归属门店ID"),
            sa.Column("owner_user_id", sa.Integer(), nullable=False, comment="归属人ID"),
            sa.Column("current_stage", sa.String(length=32), nullable=False, comment="当前阶段"),
            sa.Column("max_stage", sa.String(length=32), nullable=False, comment="最高进展"),
            sa.Column("latest_follow_at", sa.DateTime(), nullable=True, comment="最近跟进时间"),
            sa.Column("next_follow_at", sa.DateTime(), nullable=True, comment="下次跟进时间"),
            sa.Column("ended_at", sa.DateTime(), nullable=True, comment="客户阶段结束时间"),
            sa.Column("end_reason", sa.String(length=32), nullable=True, comment="结束原因"),
            sa.Column("returned_lead_id", sa.Integer(), nullable=True, comment="退回后的线索ID"),
            sa.Column("converted_vip_at", sa.DateTime(), nullable=True, comment="转VIP时间"),
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
            sa.ForeignKeyConstraint(["deleted_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["lead_id"], ["crm_lead_profile.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["owner_user_id"], ["sys_user.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["store_id"], ["sys_dept.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["updated_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("uuid"),
            comment="CRM建档客户表",
        )
        for name in (
            "brand_id",
            "person_id",
            "lead_id",
            "store_id",
            "owner_user_id",
            "current_stage",
            "max_stage",
            "latest_follow_at",
            "next_follow_at",
            "ended_at",
            "end_reason",
            "returned_lead_id",
            "id",
            "uuid",
            "status",
            "created_time",
            "updated_time",
            "is_deleted",
            "deleted_time",
            "created_id",
            "updated_id",
            "deleted_id",
        ):
            op.create_index(f"ix_crm_customer_profile_{name}", "crm_customer_profile", [name], unique=False)

    if "crm_customer_process_record" not in tables:
        op.create_table(
            "crm_customer_process_record",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("customer_id", sa.Integer(), nullable=False, comment="客户ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("record_type", sa.String(length=32), nullable=False, comment="记录类型"),
            sa.Column("occurred_at", sa.DateTime(), nullable=False, comment="发生时间"),
            sa.Column("method", sa.String(length=32), nullable=True, comment="方式"),
            sa.Column("result", sa.String(length=32), nullable=True, comment="结果"),
            sa.Column("content", sa.Text(), nullable=False, comment="内容"),
            sa.Column("next_follow_at", sa.DateTime(), nullable=True, comment="下次跟进时间"),
            sa.Column("scheduled_at", sa.DateTime(), nullable=True, comment="预约/计划时间"),
            sa.Column("need_summary", sa.Text(), nullable=True, comment="需求摘要"),
            sa.Column("budget_range", sa.String(length=64), nullable=True, comment="预算区间"),
            sa.Column("main_objection", sa.Text(), nullable=True, comment="主要异议"),
            sa.Column("intention_level", sa.String(length=32), nullable=True, comment="意向等级"),
            sa.Column("next_action", sa.String(length=255), nullable=True, comment="下一步动作"),
            sa.Column("enter_signing", sa.Boolean(), nullable=True, comment="是否进入签约推进"),
            sa.Column("operator_user_id", sa.Integer(), nullable=True, comment="执行人ID"),
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
            sa.ForeignKeyConstraint(["customer_id"], ["crm_customer_profile.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["deleted_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["operator_user_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["updated_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("uuid"),
            comment="CRM客户过程记录表",
        )
        for name in (
            "brand_id",
            "customer_id",
            "person_id",
            "record_type",
            "occurred_at",
            "method",
            "result",
            "next_follow_at",
            "scheduled_at",
            "intention_level",
            "operator_user_id",
            "id",
            "uuid",
            "status",
            "created_time",
            "updated_time",
            "is_deleted",
            "deleted_time",
            "created_id",
            "updated_id",
            "deleted_id",
        ):
            op.create_index(f"ix_crm_customer_process_record_{name}", "crm_customer_process_record", [name], unique=False)

    if "crm_customer_lifecycle" not in tables:
        op.create_table(
            "crm_customer_lifecycle",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("customer_id", sa.Integer(), nullable=False, comment="客户ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("operation_type", sa.String(length=32), nullable=False, comment="操作类型"),
            sa.Column("operator_user_id", sa.Integer(), nullable=True, comment="执行人ID"),
            sa.Column("change_detail", sa.JSON(), nullable=True, comment="变更详情"),
            sa.Column("remark", sa.Text(), nullable=True, comment="备注"),
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
            sa.ForeignKeyConstraint(["deleted_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["updated_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("uuid"),
            comment="CRM客户生命周期表",
        )
        for name in (
            "brand_id",
            "customer_id",
            "person_id",
            "operation_type",
            "operator_user_id",
            "id",
            "uuid",
            "status",
            "created_time",
            "updated_time",
            "is_deleted",
            "deleted_time",
            "created_id",
            "updated_id",
            "deleted_id",
        ):
            op.create_index(f"ix_crm_customer_lifecycle_{name}", "crm_customer_lifecycle", [name], unique=False)


def downgrade() -> None:
    for table in ("crm_customer_lifecycle", "crm_customer_process_record", "crm_customer_profile"):
        if table in _tables():
            op.drop_table(table)
