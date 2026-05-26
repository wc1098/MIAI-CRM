from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import PermissionFilterStrategy
from app.core.base_model import ModelMixin, UserMixin


class ServiceCaseModel(ModelMixin, UserMixin):
    """VIP服务工单/服务期"""

    __tablename__: str = "service_case"
    __table_args__ = (
        UniqueConstraint("contract_id", name="uq_service_case_contract_id"),
        {"comment": "VIP服务工单表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    vip_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_vip_profile.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="VIP服务ID")
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="人员ID")
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_customer_profile.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="客户ID")
    contract_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_contract.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="合同ID")
    store_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_dept.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="服务门店ID")
    owner_matchmaker_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="服务红娘ID")
    pool_type: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_assign", index=True, comment="服务池类型")
    case_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_assign", index=True, comment="服务工单状态")
    assigned_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="分配人ID")
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="分配时间")
    close_review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="none", index=True, comment="关单审核状态")
    close_requested_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="关单申请人ID")
    close_requested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="关单申请时间")
    close_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="关单原因")
    close_reviewed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="关单审核人ID")
    close_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="关单审核时间")
    close_review_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="关单审核备注")
    reopened_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="重开人ID")
    reopened_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="重开时间")
    reopen_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="重开原因")


class ServiceEntitlementModel(ModelMixin, UserMixin):
    """服务权益账本"""

    __tablename__: str = "service_entitlement"
    __table_args__ = (
        UniqueConstraint("service_case_id", "source_contract_item_id", "entitlement_type", name="uq_service_entitlement_source"),
        {"comment": "服务权益账本表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    service_case_id: Mapped[int] = mapped_column(Integer, ForeignKey("service_case.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="服务工单ID")
    vip_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_vip_profile.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="VIP服务ID")
    contract_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_contract.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="合同ID")
    source_contract_item_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("crm_contract_item.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="来源合同明细ID")
    entitlement_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="权益类型")
    total_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="总权益")
    used_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="已用权益")
    remaining_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="剩余权益")
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="次", comment="单位")
    allow_overuse: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否允许超额")
    entitlement_status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True, comment="权益状态")


class EntitlementUsageLogModel(ModelMixin, UserMixin):
    """服务权益核销记录"""

    __tablename__: str = "entitlement_usage_log"
    __table_args__: dict[str, str] = {"comment": "服务权益核销记录表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    entitlement_id: Mapped[int] = mapped_column(Integer, ForeignKey("service_entitlement.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="权益ID")
    service_case_id: Mapped[int] = mapped_column(Integer, ForeignKey("service_case.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="服务工单ID")
    vip_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_vip_profile.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="VIP服务ID")
    contract_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_contract.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="合同ID")
    usage_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="核销类型")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="核销数量")
    usage_status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True, comment="核销状态")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="发生时间")
    title: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="核销标题")
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="核销内容")
    candidate_person_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="候选Person ID")
    is_overuse: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True, comment="是否超额")
    overuse_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="超额原因")
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="作废原因")
    voided_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="作废人ID")
    voided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="作废时间")
    customer_confirm_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="客户确认状态")
    customer_signature_url: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="客户签字图片")
    customer_signed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="客户签字时间")
    service_plan_item_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("service_plan_item.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="服务计划节点ID")
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="核销来源类型")
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="核销来源记录ID")
    recommendation_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("service_recommendation.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="推荐记录ID")
    meeting_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("service_meeting.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="相亲约见ID")


class ServicePlanModel(ModelMixin, UserMixin):
    """服务计划"""

    __tablename__: str = "service_plan"
    __table_args__ = (
        UniqueConstraint("service_case_id", name="uq_service_plan_case"),
        {"comment": "VIP服务计划表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    service_case_id: Mapped[int] = mapped_column(Integer, ForeignKey("service_case.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="服务工单ID")
    vip_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_vip_profile.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="VIP服务ID")
    contract_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_contract.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="合同ID")
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="VIP Person ID")
    matchmaker_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="服务红娘ID")
    plan_status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True, comment="计划状态")
    service_start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="计划开始时间")
    service_end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="计划结束时间")
    plan_summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="计划说明")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


class ServicePlanItemModel(ModelMixin, UserMixin):
    """服务计划节点"""

    __tablename__: str = "service_plan_item"
    __table_args__: dict[str, str] = {"comment": "VIP服务计划节点表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("service_plan.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="服务计划ID")
    service_case_id: Mapped[int] = mapped_column(Integer, ForeignKey("service_case.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="服务工单ID")
    entitlement_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("service_entitlement.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="权益ID")
    entitlement_type: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="权益类型")
    item_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="节点类型")
    item_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True, comment="节点状态")
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="序号")
    title: Mapped[str] = mapped_column(String(128), nullable=False, comment="节点标题")
    planned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="计划时间")
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="截止时间")
    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="计划区间开始")
    planned_end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="计划区间结束")
    candidate_person_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="候选Person ID")
    related_recommendation_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("service_recommendation.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="推荐记录ID")
    related_meeting_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("service_meeting.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="相亲约见ID")
    related_usage_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("entitlement_usage_log.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="核销记录ID")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


class ServiceRecommendationModel(ModelMixin, UserMixin):
    """服务推荐记录"""

    __tablename__: str = "service_recommendation"
    __table_args__: dict[str, str] = {"comment": "VIP服务推荐记录表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    service_case_id: Mapped[int] = mapped_column(Integer, ForeignKey("service_case.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="服务工单ID")
    plan_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("service_plan_item.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="推荐服务项ID")
    vip_person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="VIP Person ID")
    candidate_person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="候选Person ID")
    recommendation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="recommended", index=True, comment="推荐状态")
    recommend_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="推荐理由")
    match_score: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="匹配分")
    matched_points: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, comment="匹配点")
    unmatched_points: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, comment="未匹配点")
    risk_notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="风险提示")
    matchmaker_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="红娘备注")


class ServiceMeetingModel(ModelMixin, UserMixin):
    """服务相亲约见"""

    __tablename__: str = "service_meeting"
    __table_args__: dict[str, str] = {"comment": "VIP相亲约见记录表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    recommendation_id: Mapped[int] = mapped_column(Integer, ForeignKey("service_recommendation.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="推荐记录ID")
    initiator_service_case_id: Mapped[int] = mapped_column(Integer, ForeignKey("service_case.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="发起方服务工单ID")
    initiator_plan_item_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("service_plan_item.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="发起方约见节点ID")
    initiator_person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="发起方Person ID")
    initiator_matchmaker_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="发起方红娘ID")
    target_service_case_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("service_case.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="对方服务工单ID")
    target_plan_item_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("service_plan_item.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="对方约见节点ID")
    target_person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="对方Person ID")
    target_matchmaker_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="对方红娘ID")
    target_is_vip: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True, comment="对方是否VIP")
    meeting_type: Mapped[str] = mapped_column(String(32), nullable=False, default="store", index=True, comment="约见类型")
    meeting_status: Mapped[str] = mapped_column(String(32), nullable=False, default="confirmed", index=True, comment="约见状态")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="约见时间")
    appointment_slot: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="约见时段")
    location: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="约见地点")
    meeting_result: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="约见结果")
    next_action: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="下一步动作")
    matchmaker_opinion: Mapped[str | None] = mapped_column(Text, nullable=True, comment="红娘意见")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="完成时间")
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="取消时间")
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="取消/爽约原因")


class ServiceMeetingFeedbackModel(ModelMixin, UserMixin):
    """相亲约见反馈"""

    __tablename__: str = "service_meeting_feedback"
    __table_args__ = (
        UniqueConstraint("meeting_id", "feedback_person_id", name="uq_service_meeting_feedback_person"),
        {"comment": "VIP相亲约见反馈表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    meeting_id: Mapped[int] = mapped_column(Integer, ForeignKey("service_meeting.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="约见ID")
    feedback_person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="反馈归属Person ID")
    feedback_service_case_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("service_case.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="反馈归属服务工单ID")
    feedback_matchmaker_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="填写红娘ID")
    feedback_content: Mapped[str] = mapped_column(Text, nullable=False, comment="反馈内容")
    interest_level: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="意向等级")
    meeting_result: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="约见结果")
    next_action: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="下一步动作")


class ServiceCourseRecordModel(ModelMixin, UserMixin):
    """课程服务记录"""

    __tablename__: str = "service_course_record"
    __table_args__: dict[str, str] = {"comment": "VIP课程服务记录表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    service_case_id: Mapped[int] = mapped_column(Integer, ForeignKey("service_case.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="服务工单ID")
    service_plan_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("service_plan_item.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="课程计划节点ID")
    entitlement_id: Mapped[int] = mapped_column(Integer, ForeignKey("service_entitlement.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="课程权益ID")
    usage_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("entitlement_usage_log.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="核销记录ID")
    vip_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_vip_profile.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="VIP服务ID")
    contract_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_contract.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="合同ID")
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="客户Person ID")
    matchmaker_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="服务红娘ID")
    course_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="课程时间")
    course_title: Mapped[str] = mapped_column(String(128), nullable=False, comment="课程主题")
    course_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="offline", index=True, comment="课程形式")
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="课程内容")
    customer_feedback: Mapped[str | None] = mapped_column(Text, nullable=True, comment="客户反馈/学习情况")
    matchmaker_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="红娘备注")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="课时数")
    customer_confirm_status: Mapped[str] = mapped_column(String(32), nullable=False, default="matchmaker_confirmed", index=True, comment="客户确认状态")
    customer_signature_url: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="客户签字图片")
    customer_signed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="客户签字时间")
    record_status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True, comment="课程记录状态")
    revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="撤销原因")
    revoked_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="撤销人ID")
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="撤销时间")


class DeepInterviewModel(ModelMixin, UserMixin):
    """VIP服务深访记录"""

    __tablename__: str = "deep_interview"
    __table_args__: dict[str, str] = {"comment": "VIP服务深访记录表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    service_case_id: Mapped[int] = mapped_column(Integer, ForeignKey("service_case.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="服务工单ID")
    vip_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_vip_profile.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="VIP服务ID")
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="人员ID")
    contract_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_contract.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="合同ID")
    matchmaker_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="服务红娘ID")
    interview_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="深访类型")
    interviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="深访时间")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="深访内容")
    keywords: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, comment="关键词")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="人工摘要")
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="AI摘要预留")
    ai_dimension_scores: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="AI量表预留")
    audio_file_url: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="录音文件预留")
    interview_status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True, comment="深访状态")
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="作废原因")


class CandidateProfileModel(ModelMixin, UserMixin):
    """红娘服务备选资源身份"""

    __tablename__: str = "candidate_profile"
    __table_args__ = (
        UniqueConstraint("person_id", name="uq_candidate_profile_person_id"),
        {"comment": "服务备选资源身份表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="人员ID")
    candidate_status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True, comment="候选状态")


class BackupPoolItemModel(ModelMixin, UserMixin):
    """红娘私有备选库关系"""

    __tablename__: str = "backup_pool_item"
    __table_args__ = (
        UniqueConstraint("matchmaker_id", "person_id", name="uq_backup_pool_matchmaker_person"),
        {"comment": "红娘私有备选库表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    candidate_id: Mapped[int] = mapped_column(Integer, ForeignKey("candidate_profile.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="候选身份ID")
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="人员ID")
    store_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_dept.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="来源门店ID")
    matchmaker_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="服务红娘ID")
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="加入来源")
    private_tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, comment="红娘私有标签")
    private_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="红娘私有备注")
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="最近使用时间")
    join_request_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("candidate_join_request.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="加入申请ID")
    approved_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="审批人ID")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="审批通过时间")
    contact_unmasked_after_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="审批通过后备选库内解除脱敏")


class CandidateJoinRequestModel(ModelMixin, UserMixin):
    """备选库加入申请"""

    __tablename__: str = "candidate_join_request"
    __table_args__: dict[str, str] = {"comment": "备选库加入申请表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="人员ID")
    person_store_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_dept.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="人员归属门店ID")
    request_scope: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="申请范围")
    request_matchmaker_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="申请红娘ID")
    request_store_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_dept.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="申请门店ID")
    private_tags_snapshot: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, comment="私有标签快照")
    private_remark_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True, comment="私有备注快照")
    request_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="申请理由")
    review_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True, comment="审核状态")
    reviewer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="审核人ID")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="审核时间")
    review_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审核备注")
    approved_backup_item_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("backup_pool_item.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="审批通过备选库记录ID")


class VipServiceLogModel(ModelMixin, UserMixin):
    """VIP服务流转日志"""

    __tablename__: str = "crm_vip_service_log"
    __table_args__: dict[str, str] = {"comment": "CRM VIP服务流转日志表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    vip_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_vip_profile.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="VIP服务ID")
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="人员ID")
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_customer_profile.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="客户ID")
    contract_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_contract.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="合同ID")
    operation_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="操作类型")
    operator_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="操作人ID")
    before_owner_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="原服务红娘ID")
    after_owner_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="新服务红娘ID")
    before_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="原状态")
    after_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="新状态")
    change_detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="变更详情")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
