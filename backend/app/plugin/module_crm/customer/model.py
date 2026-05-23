from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import PermissionFilterStrategy
from app.core.base_model import ModelMixin, UserMixin
from app.plugin.module_crm.lead.model import CrmPersonModel


class CrmCustomerProfileModel(ModelMixin, UserMixin):
    """CRM建档客户身份/经营周期"""

    __tablename__: str = "crm_customer_profile"
    __table_args__: dict[str, str] = {"comment": "CRM建档客户表"}
    __loader_options__: list[str] = ["person", "created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    person_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="人员ID",
    )
    lead_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("crm_lead_profile.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="来源线索ID",
    )
    store_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sys_dept.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="归属门店ID",
    )
    owner_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sys_user.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="归属人ID",
    )
    current_stage: Mapped[str] = mapped_column(
        String(32), nullable=False, default="profiling", index=True, comment="当前阶段"
    )
    max_stage: Mapped[str] = mapped_column(
        String(32), nullable=False, default="profiling", index=True, comment="最高进展"
    )
    latest_follow_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="最近跟进时间")
    next_follow_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="下次跟进时间")
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="客户阶段结束时间")
    end_reason: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="结束原因")
    returned_lead_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="退回后的线索ID")
    converted_vip_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="转VIP时间")

    person: Mapped["CrmPersonModel"] = relationship("CrmPersonModel", lazy="selectin")


class CrmCustomerProcessRecordModel(ModelMixin, UserMixin):
    """CRM客户过程记录"""

    __tablename__: str = "crm_customer_process_record"
    __table_args__: dict[str, str] = {"comment": "CRM客户过程记录表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crm_customer_profile.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="客户ID",
    )
    person_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="人员ID",
    )
    record_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="记录类型")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="发生时间")
    method: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="方式")
    result: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="结果")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="内容")
    next_follow_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="下次跟进时间")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="预约/计划时间")
    appointment_slot: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="预约时段")
    visit_purpose: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="到访目的")
    promised_gift: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="承诺礼品")
    appointment_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="预约状态")
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="核销到店时间")
    checked_in_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="核销人ID",
    )
    need_summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="需求摘要")
    budget_range: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="预算区间")
    main_objection: Mapped[str | None] = mapped_column(Text, nullable=True, comment="主要异议")
    intention_level: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="意向等级")
    next_action: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="下一步动作")
    enter_signing: Mapped[bool | None] = mapped_column(Boolean, nullable=True, comment="是否进入签约推进")
    operator_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="执行人ID",
    )


class CrmCustomerLifecycleModel(ModelMixin, UserMixin):
    """CRM客户生命周期记录"""

    __tablename__: str = "crm_customer_lifecycle"
    __table_args__: dict[str, str] = {"comment": "CRM客户生命周期表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="客户ID")
    person_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="人员ID")
    operation_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="操作类型")
    operator_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="执行人ID")
    change_detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="变更详情")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


class CrmCustomerCertificationMaterialModel(ModelMixin, UserMixin):
    """CRM客户认证资料存档"""

    __tablename__: str = "crm_customer_certification_material"
    __table_args__: dict[str, str] = {"comment": "CRM客户认证资料存档表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crm_customer_profile.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="客户ID",
    )
    person_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="人员ID",
    )
    item_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="资料项编码")
    item_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="资料项名称")
    material_type: Mapped[str] = mapped_column(String(32), nullable=False, default="image", index=True, comment="资料类型")
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="文件名")
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="文件路径")
    file_url: Mapped[str] = mapped_column(String(1000), nullable=False, comment="文件URL")
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="资料扩展")
    collected_by: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="收集人ID")
