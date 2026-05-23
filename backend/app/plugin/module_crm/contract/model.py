from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import PermissionFilterStrategy
from app.core.base_model import ModelMixin, UserMixin
from app.plugin.module_crm.customer.model import CrmCustomerProfileModel
from app.plugin.module_crm.lead.model import CrmPersonModel


class CrmContractModel(ModelMixin, UserMixin):
    """CRM合同主表"""

    __tablename__: str = "crm_contract"
    __table_args__: dict[str, str] = {"comment": "CRM合同表"}
    __loader_options__: list[str] = ["customer", "person", "items", "attachments", "receipts", "created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    contract_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True, comment="合同编号")
    contract_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="合同名称")
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_customer_profile.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="客户ID")
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="人员ID")
    store_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_dept.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="门店ID")
    owner_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="销售ID")
    vip_level: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="授予VIP等级")
    contract_status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True, comment="合同状态")
    original_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"), comment="产品原价合计")
    contract_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"), comment="合同总金额")
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"), comment="折扣金额")
    discount_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=Decimal("0.0000"), comment="折扣率")
    discount_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="折扣原因")
    start_date: Mapped[date] = mapped_column(Date, nullable=False, comment="合同开始日期")
    end_date: Mapped[date] = mapped_column(Date, nullable=False, comment="合同结束日期")
    expire_remind_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30, comment="到期提前提醒天数")
    signer_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="合同签署人")
    signed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="签署时间")
    review_submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="提交审核时间")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="审核时间")
    reviewed_by: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="审核人ID")
    review_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审核备注")
    effective_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="生效时间")
    first_paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="首付款到账时间")
    voided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="作废时间")
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="作废原因")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    customer: Mapped["CrmCustomerProfileModel"] = relationship("CrmCustomerProfileModel", lazy="selectin")
    person: Mapped["CrmPersonModel"] = relationship("CrmPersonModel", lazy="selectin")
    items: Mapped[list["CrmContractItemModel"]] = relationship("CrmContractItemModel", lazy="selectin")
    attachments: Mapped[list["CrmContractAttachmentModel"]] = relationship("CrmContractAttachmentModel", lazy="selectin")
    receipts: Mapped[list["CrmContractReceiptModel"]] = relationship("CrmContractReceiptModel", lazy="selectin")


class CrmContractItemModel(ModelMixin, UserMixin):
    """CRM合同产品快照"""

    __tablename__: str = "crm_contract_item"
    __table_args__: dict[str, str] = {"comment": "CRM合同产品明细表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    contract_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_contract.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="合同ID")
    product_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("crm_product_package.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="产品ID")
    product_name_snapshot: Mapped[str] = mapped_column(String(128), nullable=False, comment="产品名称快照")
    price_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, comment="价格快照")
    service_days_snapshot: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="服务时长快照")
    recommendation_quota_snapshot: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="推荐次数快照")
    meeting_quota_snapshot: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="约见次数快照")
    course_quota_snapshot: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="课程次数快照")
    supports_online_meeting_snapshot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="线上约见快照")


class CrmContractAttachmentModel(ModelMixin, UserMixin):
    """CRM合同影像附件"""

    __tablename__: str = "crm_contract_attachment"
    __table_args__: dict[str, str] = {"comment": "CRM合同影像附件表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    contract_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_contract.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="合同ID")
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="文件名")
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="文件路径")
    file_url: Mapped[str] = mapped_column(String(1000), nullable=False, comment="文件URL")
    file_type: Mapped[str] = mapped_column(String(32), nullable=False, default="image", index=True, comment="文件类型")
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="页数")
    attachment_status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True, comment="附件状态")
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="扩展信息")
    voided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="作废时间")
    voided_by: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="作废人ID")


class CrmContractStoreRuleModel(ModelMixin, UserMixin):
    """CRM门店合同规则"""

    __tablename__: str = "crm_contract_store_rule"
    __table_args__: dict[str, str] = {"comment": "CRM门店合同规则表"}
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
    require_contract_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否需要合同审核")


class CrmContractReceiptModel(ModelMixin, UserMixin):
    """CRM合同收款记录"""

    __tablename__: str = "crm_contract_receipt"
    __table_args__: dict[str, str] = {"comment": "CRM合同收款记录表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    receipt_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True, comment="收款单号")
    contract_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_contract.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="合同ID")
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="客户ID")
    person_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="人员ID")
    store_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="门店ID")
    receipt_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="收款类型")
    pay_method: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="支付方式")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, comment="收款金额")
    receipt_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True, comment="收款状态")
    payment_scene: Mapped[str] = mapped_column(String(32), nullable=False, default="offline", index=True, comment="支付场景")
    order_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("payment_order.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="支付订单ID")
    payment_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("payment_record.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="支付流水ID")
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="提交时间")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="复核时间")
    reviewed_by: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="复核人ID")
    review_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="复核备注")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="支付成功时间")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="确认时间")
    confirmed_by: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="确认人ID")
    voided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="作废时间")
    voided_by: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="作废人ID")
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="作废原因")
    reverse_receipt_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="关联原收款单ID")
    reverse_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="冲正/退款原因")
    channel_trade_no: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True, comment="渠道交易号")
    payment_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="支付/确认扩展信息")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


class CrmVipProfileModel(ModelMixin, UserMixin):
    """CRM VIP服务身份最小表"""

    __tablename__: str = "crm_vip_profile"
    __table_args__: dict[str, str] = {"comment": "CRM VIP服务身份表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="人员ID")
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_customer_profile.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="来源客户ID")
    contract_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_contract.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="来源合同ID")
    store_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_dept.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="服务门店ID")
    service_owner_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="服务红娘ID")
    vip_level: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="VIP等级")
    vip_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_assign", index=True, comment="VIP状态")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="开始时间")
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="结束时间")
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="分配时间")
    assigned_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="分配人ID")
    source_receipt_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="触发收款ID")
