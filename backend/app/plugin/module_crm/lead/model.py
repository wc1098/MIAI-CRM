from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import PermissionFilterStrategy
from app.core.base_model import ModelMixin, UserMixin


class CrmPersonModel(ModelMixin, UserMixin):
    """CRM统一人员主体"""

    __tablename__: str = "crm_person"
    __table_args__: dict[str, str] = {"comment": "CRM人员主体表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    display_no: Mapped[str | None] = mapped_column(String(7), nullable=True, unique=True, index=True, comment="对外展示编号")
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="姓名")
    gender: Mapped[str] = mapped_column(String(1), nullable=False, default="2", index=True, comment="性别")
    primary_mobile: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True, comment="手机号")
    wechat: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="微信号")
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="出生日期")
    height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="身高cm")
    ethnicity: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="民族")
    occupation: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="职业")
    annual_income: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="年收入")
    marital_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="婚况")
    education: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="学历")
    hometown: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="籍贯")
    residence: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True, comment="常驻地")
    house_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="房产信息")
    car_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="购车信息")
    photo_urls: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, comment="照片相册URL列表")
    profile_intro: Mapped[str | None] = mapped_column(Text, nullable=True, comment="个人介绍")
    id_card_no: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="身份证号")
    certification_level: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="none",
        index=True,
        comment="当前认证等级",
    )
    certification_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="认证摘要")


class CrmLeadProfileModel(ModelMixin, UserMixin):
    """CRM线索身份"""

    __tablename__: str = "crm_lead_profile"
    __table_args__: dict[str, str] = {"comment": "CRM线索表"}
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
    store_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sys_dept.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="归属门店ID",
    )
    owner_sales_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="归属销售ID",
    )
    pool_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="hq_pool", index=True, comment="归属池"
    )
    lead_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", index=True, comment="线索类型"
    )
    source_channel_code: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, comment="来源渠道编码"
    )
    latest_source_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="最近来源事件ID")
    latest_follow_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="最后跟进时间")
    next_follow_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="下次跟进时间")
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="最近分配/领取时间")
    last_recycled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最近自动回收时间")
    converted_customer_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="转建档客户时间")

    person: Mapped["CrmPersonModel"] = relationship("CrmPersonModel", lazy="selectin")


class CrmLeadProcessRecordModel(ModelMixin, UserMixin):
    """CRM线索过程记录"""

    __tablename__: str = "crm_lead_process_record"
    __table_args__: dict[str, str] = {"comment": "CRM线索过程记录表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    lead_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crm_lead_profile.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="线索ID",
    )
    person_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="人员ID",
    )
    action_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="动作类型")
    follow_method: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="跟进方式")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="跟进内容/原因")
    next_follow_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="下次跟进时间")
    operator_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="执行人ID",
    )


class CrmLeadLifecycleModel(ModelMixin, UserMixin):
    """CRM线索生命周期记录"""

    __tablename__: str = "crm_lead_lifecycle"
    __table_args__: dict[str, str] = {"comment": "CRM线索生命周期表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    lead_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="线索ID")
    person_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="人员ID")
    operation_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="操作类型")
    operator_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="执行人ID")
    change_detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="变更详情")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


class CrmLeadStoreRuleModel(ModelMixin, UserMixin):
    """CRM门店线索规则"""

    __tablename__: str = "crm_lead_store_rule"
    __table_args__: dict[str, str] = {"comment": "CRM门店线索规则表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    store_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sys_dept.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="门店ID",
    )
    allow_sales_claim: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否允许销售自领")
    no_follow_reclaim_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7, comment="无跟进回收天数")


class CrmLeadImportBatchModel(ModelMixin, UserMixin):
    """CRM线索导入批次"""

    __tablename__: str = "crm_lead_import_batch"
    __table_args__: dict[str, str] = {"comment": "CRM线索导入批次表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="导入文件名")
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="成功条数")
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="失败条数")
    result_detail: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True, comment="失败详情")
