"""create service plan match meeting

Revision ID: 20260525_1000
Revises: 20260524_1010
Create Date: 2026-05-25 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260525_1000"
down_revision: str | None = "20260524_1010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


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


def _add_column(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def upgrade() -> None:
    tables = _tables()
    if "service_plan" not in tables:
        op.create_table(
            "service_plan",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("service_case_id", sa.Integer(), nullable=False, comment="服务工单ID"),
            sa.Column("vip_id", sa.Integer(), nullable=False, comment="VIP服务ID"),
            sa.Column("contract_id", sa.Integer(), nullable=False, comment="合同ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="VIP Person ID"),
            sa.Column("matchmaker_id", sa.Integer(), nullable=True, comment="服务红娘ID"),
            sa.Column("plan_status", sa.String(length=32), nullable=False, comment="计划状态"),
            sa.Column("service_start_at", sa.DateTime(), nullable=True, comment="计划开始时间"),
            sa.Column("service_end_at", sa.DateTime(), nullable=True, comment="计划结束时间"),
            sa.Column("plan_summary", sa.Text(), nullable=True, comment="计划说明"),
            sa.Column("remark", sa.Text(), nullable=True, comment="备注"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["contract_id"], ["crm_contract.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["matchmaker_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["service_case_id"], ["service_case.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["vip_id"], ["crm_vip_profile.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            *_audit_constraints(),
            sa.UniqueConstraint("service_case_id", name="uq_service_plan_case"),
            comment="VIP服务计划表",
        )
    _create_indexes("service_plan", ["brand_id", "service_case_id", "vip_id", "contract_id", "person_id", "matchmaker_id", "plan_status", "service_start_at", "service_end_at"])

    if "service_plan_item" not in tables:
        op.create_table(
            "service_plan_item",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("plan_id", sa.Integer(), nullable=False, comment="服务计划ID"),
            sa.Column("service_case_id", sa.Integer(), nullable=False, comment="服务工单ID"),
            sa.Column("entitlement_id", sa.Integer(), nullable=True, comment="权益ID"),
            sa.Column("entitlement_type", sa.String(length=32), nullable=True, comment="权益类型"),
            sa.Column("item_type", sa.String(length=32), nullable=False, comment="节点类型"),
            sa.Column("item_status", sa.String(length=32), nullable=False, comment="节点状态"),
            sa.Column("sequence_no", sa.Integer(), nullable=False, comment="序号"),
            sa.Column("title", sa.String(length=128), nullable=False, comment="节点标题"),
            sa.Column("planned_at", sa.DateTime(), nullable=True, comment="计划时间"),
            sa.Column("due_at", sa.DateTime(), nullable=True, comment="截止时间"),
            sa.Column("candidate_person_id", sa.Integer(), nullable=True, comment="候选Person ID"),
            sa.Column("related_recommendation_id", sa.Integer(), nullable=True, comment="推荐记录ID"),
            sa.Column("related_meeting_id", sa.Integer(), nullable=True, comment="相亲约见ID"),
            sa.Column("related_usage_id", sa.Integer(), nullable=True, comment="核销记录ID"),
            sa.Column("remark", sa.Text(), nullable=True, comment="备注"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["candidate_person_id"], ["crm_person.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["entitlement_id"], ["service_entitlement.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["plan_id"], ["service_plan.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["service_case_id"], ["service_case.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            *_audit_constraints(),
            comment="VIP服务计划节点表",
        )
    _create_indexes("service_plan_item", ["brand_id", "plan_id", "service_case_id", "entitlement_id", "entitlement_type", "item_type", "item_status", "sequence_no", "planned_at", "due_at", "candidate_person_id"])

    if "service_recommendation" not in tables:
        op.create_table(
            "service_recommendation",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("service_case_id", sa.Integer(), nullable=False, comment="服务工单ID"),
            sa.Column("plan_item_id", sa.Integer(), nullable=False, comment="推荐服务项ID"),
            sa.Column("vip_person_id", sa.Integer(), nullable=False, comment="VIP Person ID"),
            sa.Column("candidate_person_id", sa.Integer(), nullable=False, comment="候选Person ID"),
            sa.Column("recommendation_status", sa.String(length=32), nullable=False, comment="推荐状态"),
            sa.Column("recommend_reason", sa.Text(), nullable=True, comment="推荐理由"),
            sa.Column("match_score", sa.Integer(), nullable=True, comment="匹配分"),
            sa.Column("matched_points", sa.JSON(), nullable=True, comment="匹配点"),
            sa.Column("unmatched_points", sa.JSON(), nullable=True, comment="未匹配点"),
            sa.Column("risk_notes", sa.Text(), nullable=True, comment="风险提示"),
            sa.Column("matchmaker_remark", sa.Text(), nullable=True, comment="红娘备注"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["candidate_person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["plan_item_id"], ["service_plan_item.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["service_case_id"], ["service_case.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["vip_person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            *_audit_constraints(),
            comment="VIP服务推荐记录表",
        )
    _create_indexes("service_recommendation", ["brand_id", "service_case_id", "plan_item_id", "vip_person_id", "candidate_person_id", "recommendation_status"])

    if "service_meeting" not in tables:
        op.create_table(
            "service_meeting",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("recommendation_id", sa.Integer(), nullable=False, comment="推荐记录ID"),
            sa.Column("initiator_service_case_id", sa.Integer(), nullable=False, comment="发起方服务工单ID"),
            sa.Column("initiator_plan_item_id", sa.Integer(), nullable=True, comment="发起方约见节点ID"),
            sa.Column("initiator_person_id", sa.Integer(), nullable=False, comment="发起方Person ID"),
            sa.Column("initiator_matchmaker_id", sa.Integer(), nullable=True, comment="发起方红娘ID"),
            sa.Column("target_service_case_id", sa.Integer(), nullable=True, comment="对方服务工单ID"),
            sa.Column("target_plan_item_id", sa.Integer(), nullable=True, comment="对方约见节点ID"),
            sa.Column("target_person_id", sa.Integer(), nullable=False, comment="对方Person ID"),
            sa.Column("target_matchmaker_id", sa.Integer(), nullable=True, comment="对方红娘ID"),
            sa.Column("target_is_vip", sa.Boolean(), nullable=False, comment="对方是否VIP"),
            sa.Column("meeting_type", sa.String(length=32), nullable=False, comment="约见类型"),
            sa.Column("meeting_status", sa.String(length=32), nullable=False, comment="约见状态"),
            sa.Column("scheduled_at", sa.DateTime(), nullable=True, comment="约见时间"),
            sa.Column("appointment_slot", sa.String(length=32), nullable=True, comment="约见时段"),
            sa.Column("location", sa.String(length=255), nullable=True, comment="约见地点"),
            sa.Column("meeting_result", sa.String(length=32), nullable=True, comment="约见结果"),
            sa.Column("next_action", sa.String(length=255), nullable=True, comment="下一步动作"),
            sa.Column("matchmaker_opinion", sa.Text(), nullable=True, comment="红娘意见"),
            sa.Column("completed_at", sa.DateTime(), nullable=True, comment="完成时间"),
            sa.Column("cancelled_at", sa.DateTime(), nullable=True, comment="取消时间"),
            sa.Column("cancel_reason", sa.Text(), nullable=True, comment="取消/爽约原因"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["initiator_matchmaker_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["initiator_person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["initiator_plan_item_id"], ["service_plan_item.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["initiator_service_case_id"], ["service_case.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["recommendation_id"], ["service_recommendation.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["target_matchmaker_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["target_person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["target_plan_item_id"], ["service_plan_item.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["target_service_case_id"], ["service_case.id"], ondelete="SET NULL", onupdate="CASCADE"),
            *_audit_constraints(),
            comment="VIP相亲约见记录表",
        )
    _create_indexes("service_meeting", ["brand_id", "recommendation_id", "initiator_service_case_id", "initiator_plan_item_id", "initiator_person_id", "initiator_matchmaker_id", "target_service_case_id", "target_plan_item_id", "target_person_id", "target_matchmaker_id", "target_is_vip", "meeting_type", "meeting_status", "scheduled_at", "meeting_result", "completed_at", "cancelled_at"])

    if "service_meeting_feedback" not in tables:
        op.create_table(
            "service_meeting_feedback",
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("meeting_id", sa.Integer(), nullable=False, comment="约见ID"),
            sa.Column("feedback_person_id", sa.Integer(), nullable=False, comment="反馈归属Person ID"),
            sa.Column("feedback_service_case_id", sa.Integer(), nullable=True, comment="反馈归属服务工单ID"),
            sa.Column("feedback_matchmaker_id", sa.Integer(), nullable=True, comment="填写红娘ID"),
            sa.Column("feedback_content", sa.Text(), nullable=False, comment="反馈内容"),
            sa.Column("interest_level", sa.String(length=32), nullable=True, comment="意向等级"),
            sa.Column("meeting_result", sa.String(length=32), nullable=True, comment="约见结果"),
            sa.Column("next_action", sa.String(length=255), nullable=True, comment="下一步动作"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["feedback_matchmaker_id"], ["sys_user.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["feedback_person_id"], ["crm_person.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["feedback_service_case_id"], ["service_case.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["meeting_id"], ["service_meeting.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            *_audit_constraints(),
            sa.UniqueConstraint("meeting_id", "feedback_person_id", name="uq_service_meeting_feedback_person"),
            comment="VIP相亲约见反馈表",
        )
    _create_indexes("service_meeting_feedback", ["brand_id", "meeting_id", "feedback_person_id", "feedback_service_case_id", "feedback_matchmaker_id", "interest_level", "meeting_result"])

    if "entitlement_usage_log" in _tables():
        for column in [
            sa.Column("service_plan_item_id", sa.Integer(), nullable=True, comment="服务计划节点ID"),
            sa.Column("source_type", sa.String(length=32), nullable=True, comment="核销来源类型"),
            sa.Column("source_id", sa.Integer(), nullable=True, comment="核销来源记录ID"),
            sa.Column("recommendation_id", sa.Integer(), nullable=True, comment="推荐记录ID"),
            sa.Column("meeting_id", sa.Integer(), nullable=True, comment="相亲约见ID"),
        ]:
            _add_column("entitlement_usage_log", column)
        _create_indexes("entitlement_usage_log", ["service_plan_item_id", "source_type", "source_id", "recommendation_id", "meeting_id"])


def downgrade() -> None:
    for table_name in [
        "service_meeting_feedback",
        "service_meeting",
        "service_recommendation",
        "service_plan_item",
        "service_plan",
    ]:
        if table_name in _tables():
            op.drop_table(table_name)
