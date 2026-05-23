from datetime import date
from decimal import Decimal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.base_schema import BaseSchema, CommonSchema, UserBySchema
from app.core.validator import DateTimeStr

CONTRACT_STATUSES = {"draft", "signed", "pending_review", "pending_payment", "effective", "expired", "voided"}


class ContractCreateSchema(BaseModel):
    """合同创建模型"""

    customer_id: int = Field(..., description="客户ID")
    product_ids: list[int] = Field(..., min_length=1, description="产品ID列表")
    contract_name: str = Field(..., min_length=1, max_length=128, description="合同名称")
    contract_amount: Decimal = Field(..., ge=0, decimal_places=2, description="合同总金额")
    discount_reason: str | None = Field(default=None, max_length=1000, description="折扣原因")
    start_date: date = Field(..., description="合同开始日期")
    end_date: date = Field(..., description="合同结束日期")
    expire_remind_days: int = Field(default=30, ge=0, le=3650, description="到期提前提醒天数")
    signer_name: str = Field(..., min_length=1, max_length=64, description="签署人")
    vip_level: str = Field(..., min_length=1, max_length=32, description="VIP等级")
    remark: str | None = Field(default=None, max_length=2000, description="备注")

    @field_validator("contract_name", "signer_name", "vip_level", "discount_reason", "remark")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("product_ids")
    @classmethod
    def validate_product_ids(cls, value: list[int]) -> list[int]:
        ids = list(dict.fromkeys(value))
        if not ids:
            raise ValueError("至少选择一个产品套餐")
        return ids

    @model_validator(mode="after")
    def validate_date_range(self) -> "ContractCreateSchema":
        if self.end_date < self.start_date:
            raise ValueError("合同结束日期不能早于开始日期")
        return self


class ContractUpdateSchema(ContractCreateSchema):
    """合同更新模型"""


class ContractSignSchema(BaseModel):
    """合同签署模型"""

    remark: str | None = Field(default=None, max_length=1000, description="备注")


class ContractReviewSchema(BaseModel):
    """合同审核模型"""

    approved: bool = Field(..., description="是否通过")
    review_remark: str | None = Field(default=None, max_length=1000, description="审核备注")


class ContractStoreRuleSchema(BaseModel):
    """门店合同规则模型"""

    model_config = ConfigDict(from_attributes=True)

    require_contract_review: bool = Field(default=True, description="是否需要合同审核")


class ContractVoidSchema(BaseModel):
    """合同作废模型"""

    reason: str = Field(..., min_length=1, max_length=1000, description="作废原因")


class ContractAttachmentSaveSchema(BaseModel):
    """合同影像保存模型"""

    file_name: str | None = Field(default=None, max_length=255, description="文件名")
    file_path: str | None = Field(default=None, max_length=512, description="文件路径")
    file_url: str = Field(..., min_length=1, max_length=1000, description="文件URL")
    file_type: str = Field(default="image", max_length=32, description="文件类型")
    page_count: int | None = Field(default=None, ge=1, description="页数")
    payload: dict | None = Field(default=None, description="扩展信息")


class ContractItemOutSchema(BaseSchema, UserBySchema):
    """合同产品明细响应"""

    model_config = ConfigDict(from_attributes=True)

    brand_id: int
    contract_id: int
    product_id: int | None = None
    product_name_snapshot: str
    price_snapshot: Decimal
    service_days_snapshot: int
    recommendation_quota_snapshot: int
    meeting_quota_snapshot: int
    course_quota_snapshot: int
    supports_online_meeting_snapshot: bool


class ContractAttachmentOutSchema(BaseSchema, UserBySchema):
    """合同影像响应"""

    model_config = ConfigDict(from_attributes=True)

    brand_id: int
    contract_id: int
    file_name: str | None = None
    file_path: str | None = None
    file_url: str
    file_type: str
    page_count: int | None = None
    attachment_status: str
    payload: dict | None = None
    voided_at: DateTimeStr | None = None
    voided_by: int | None = None


class ContractReceiptOutSchema(BaseSchema, UserBySchema):
    """合同收款响应"""

    model_config = ConfigDict(from_attributes=True)

    brand_id: int
    receipt_no: str
    contract_id: int
    customer_id: int
    person_id: int
    store_id: int
    receipt_type: str
    pay_method: str
    amount: Decimal
    receipt_status: str
    payment_scene: str
    order_id: int | None = None
    payment_id: int | None = None
    submitted_at: DateTimeStr
    reviewed_at: DateTimeStr | None = None
    reviewed_by: int | None = None
    review_remark: str | None = None
    paid_at: DateTimeStr | None = None
    confirmed_at: DateTimeStr | None = None
    confirmed_by: int | None = None
    voided_at: DateTimeStr | None = None
    voided_by: int | None = None
    void_reason: str | None = None
    reverse_receipt_id: int | None = None
    reverse_reason: str | None = None
    channel_trade_no: str | None = None
    payment_payload: dict | None = None
    remark: str | None = None


class ContractOutSchema(BaseSchema, UserBySchema):
    """合同响应模型"""

    model_config = ConfigDict(from_attributes=True)

    brand_id: int
    contract_no: str
    contract_name: str
    customer_id: int
    person_id: int
    store_id: int
    owner_user_id: int
    vip_level: str
    contract_status: str
    original_amount: Decimal
    contract_amount: Decimal
    received_amount: Decimal = Decimal("0.00")
    pending_amount: Decimal = Decimal("0.00")
    payment_progress: Decimal = Decimal("0.00")
    payment_status: str = "unpaid"
    validity_period: str | None = None
    discount_amount: Decimal
    discount_rate: Decimal
    discount_reason: str | None = None
    start_date: date
    end_date: date
    expire_remind_days: int
    signer_name: str
    signed_at: DateTimeStr | None = None
    review_submitted_at: DateTimeStr | None = None
    reviewed_at: DateTimeStr | None = None
    reviewed_by: int | None = None
    review_remark: str | None = None
    effective_at: DateTimeStr | None = None
    first_paid_at: DateTimeStr | None = None
    voided_at: DateTimeStr | None = None
    void_reason: str | None = None
    remark: str | None = None
    customer: CommonSchema | None = None
    person: CommonSchema | None = None
    person_display_no: str | None = None
    person_mobile: str | None = None
    owner_user_name: str | None = None
    store_name: str | None = None
    items: list[ContractItemOutSchema] = Field(default_factory=list)
    attachments: list[ContractAttachmentOutSchema] = Field(default_factory=list)
    receipts: list[ContractReceiptOutSchema] = Field(default_factory=list)


class CustomerSearchOutSchema(BaseModel):
    """合同客户搜索响应"""

    id: int
    person_id: int
    display_no: str | None = None
    name: str
    mobile: str
    gender: str
    store_id: int
    owner_user_id: int


class ContractQueryParam:
    """合同查询参数"""

    def __init__(
        self,
        keyword: str | None = Query(None, description="关键词"),
        contract_status: str | None = Query(None, description="合同状态"),
        payment_status: str | None = Query(None, description="支付状态: unpaid/partial/settled"),
        vip_level: str | None = Query(None, description="VIP等级"),
        store_id: int | None = Query(None, description="门店ID"),
        owner_user_id: int | None = Query(None, description="销售ID"),
        customer_id: int | None = Query(None, description="客户ID"),
    ) -> None:
        self.keyword = keyword.strip() if keyword else None
        self.contract_status = contract_status
        self.payment_status = payment_status
        self.vip_level = vip_level
        self.store_id = store_id
        self.owner_user_id = owner_user_id
        self.customer_id = customer_id
