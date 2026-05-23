from datetime import datetime
from decimal import Decimal

from fastapi import Query
from pydantic import BaseModel, Field, field_validator

from app.core.validator import DateTimeStr

RECEIPT_TYPES = {"deposit", "final", "full", "additional", "refund", "other"}
PAY_METHODS = {"pending", "cash", "alipay", "wechat", "bank_transfer"}
PAYMENT_SCENES = {"pending", "offline", "qrcode", "barcode"}
TERMINAL_STATUSES = {"approved", "voided", "reversed", "refund_registered"}


class ReceiptCreateSchema(BaseModel):
    """线下收款提交模型"""

    receipt_type: str = Field(..., description="收款类型")
    pay_method: str = Field(..., description="支付方式")
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="收款金额")
    remark: str | None = Field(default=None, max_length=1000, description="备注")

    @field_validator("receipt_type")
    @classmethod
    def validate_receipt_type(cls, value: str) -> str:
        if value not in RECEIPT_TYPES - {"refund"}:
            raise ValueError("收款类型不正确")
        return value

    @field_validator("pay_method")
    @classmethod
    def validate_pay_method(cls, value: str) -> str:
        if value not in {"cash", "bank_transfer"}:
            raise ValueError("线下确认只支持现金或银行转账")
        return value


class ReceiptPendingCreateSchema(BaseModel):
    """合同创建待收款单模型"""

    receipt_type: str = Field(..., description="收款类型")
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="收款金额")
    remark: str | None = Field(default=None, max_length=1000, description="备注")

    @field_validator("receipt_type")
    @classmethod
    def validate_receipt_type(cls, value: str) -> str:
        if value not in RECEIPT_TYPES - {"refund"}:
            raise ValueError("收款类型不正确")
        return value


class ReceiptOfflineConfirmSchema(BaseModel):
    """待收款单转线下确认模型"""

    pay_method: str = Field(..., description="支付方式")
    remark: str | None = Field(default=None, max_length=1000, description="备注")

    @field_validator("pay_method")
    @classmethod
    def validate_pay_method(cls, value: str) -> str:
        if value not in {"cash", "bank_transfer"}:
            raise ValueError("线下确认只支持现金或银行转账")
        return value


class OnlineReceiptCreateSchema(BaseModel):
    """在线扫码收款创建模型"""

    receipt_type: str = Field(..., description="收款类型")
    pay_channel: str = Field(default="wechat", description="支付渠道")
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="收款金额")
    operator_id: str | None = Field(default=None, max_length=28, description="操作员编号")
    remark: str | None = Field(default=None, max_length=1000, description="备注")

    @field_validator("receipt_type")
    @classmethod
    def validate_receipt_type(cls, value: str) -> str:
        if value not in RECEIPT_TYPES - {"refund"}:
            raise ValueError("收款类型不正确")
        return value

    @field_validator("pay_channel")
    @classmethod
    def validate_pay_channel(cls, value: str) -> str:
        if value not in {"wechat", "alipay"}:
            raise ValueError("支付渠道不正确")
        return value


class BarcodeReceiptCreateSchema(BaseModel):
    """按合同直接发起条码收款模型"""

    receipt_type: str = Field(..., description="收款类型")
    pay_channel: str = Field(default="wechat", description="支付渠道")
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="收款金额")
    auth_code: str = Field(..., min_length=1, max_length=32, description="付款码")
    operator_id: str | None = Field(default=None, max_length=28, description="操作员编号")
    remark: str | None = Field(default=None, max_length=1000, description="备注")

    @field_validator("receipt_type")
    @classmethod
    def validate_receipt_type(cls, value: str) -> str:
        if value not in RECEIPT_TYPES - {"refund"}:
            raise ValueError("收款类型不正确")
        return value

    @field_validator("pay_channel")
    @classmethod
    def validate_pay_channel(cls, value: str) -> str:
        if value not in {"wechat", "alipay"}:
            raise ValueError("支付渠道不正确")
        return value


class BarcodePaySchema(BaseModel):
    """条码支付模型"""

    auth_code: str = Field(..., min_length=1, max_length=32, description="付款码")
    pay_channel: str | None = Field(default=None, max_length=32, description="支付渠道")
    operator_id: str | None = Field(default=None, max_length=28, description="操作员编号")


class QrcodePaySchema(BaseModel):
    """扫码支付模型"""

    pay_channel: str = Field(default="wechat", description="支付渠道")
    operator_id: str | None = Field(default=None, max_length=28, description="操作员编号")

    @field_validator("pay_channel")
    @classmethod
    def validate_pay_channel(cls, value: str) -> str:
        if value not in {"wechat", "alipay"}:
            raise ValueError("支付渠道不正确")
        return value


class ReceiptReviewSchema(BaseModel):
    """线下收款复核模型"""

    approved: bool = Field(..., description="是否通过")
    review_remark: str | None = Field(default=None, max_length=1000, description="复核备注")


class ReceiptVoidSchema(BaseModel):
    """收款作废模型"""

    reason: str = Field(..., min_length=1, max_length=1000, description="作废原因")


class ReceiptReverseSchema(BaseModel):
    """收款冲正模型"""

    reason: str = Field(..., min_length=1, max_length=1000, description="冲正原因")


class ReceiptRefundRegisterSchema(BaseModel):
    """退款登记模型"""

    amount: Decimal = Field(..., gt=0, decimal_places=2, description="退款金额")
    reason: str = Field(..., min_length=1, max_length=1000, description="退款原因")


class ReceiptOutSchema(BaseModel):
    """收款单响应"""

    id: int
    brand_id: int
    receipt_no: str
    contract_id: int
    contract_no: str | None = None
    contract_name: str | None = None
    customer_id: int
    person_id: int
    person_name: str | None = None
    person_display_no: str | None = None
    person_mobile: str | None = None
    store_id: int
    store_name: str | None = None
    owner_user_id: int | None = None
    owner_user_name: str | None = None
    receipt_type: str
    pay_method: str
    amount: Decimal
    receipt_status: str
    payment_scene: str
    order_id: int | None = None
    order_no: str | None = None
    order_pay_status: str | None = None
    payment_id: int | None = None
    channel_trade_no: str | None = None
    submitted_at: DateTimeStr
    reviewed_at: DateTimeStr | None = None
    reviewed_by: int | None = None
    reviewed_by_name: str | None = None
    review_remark: str | None = None
    paid_at: DateTimeStr | None = None
    confirmed_at: DateTimeStr | None = None
    confirmed_by: int | None = None
    confirmed_by_name: str | None = None
    voided_at: DateTimeStr | None = None
    voided_by: int | None = None
    voided_by_name: str | None = None
    void_reason: str | None = None
    reverse_receipt_id: int | None = None
    reverse_reason: str | None = None
    payment_payload: dict | None = None
    remark: str | None = None
    created_time: DateTimeStr | None = None
    updated_time: DateTimeStr | None = None


class ReceiptPaymentOutSchema(BaseModel):
    """在线支付创建响应"""

    receipt: ReceiptOutSchema
    payment: dict


class ReceiptSummaryOutSchema(BaseModel):
    """收款汇总响应"""

    contract_id: int | None = None
    contract_amount: Decimal
    received_amount: Decimal = Decimal("0.00")
    pending_amount: Decimal = Decimal("0.00")
    payment_status: str = "unpaid"
    received_amount: Decimal
    pending_amount: Decimal
    first_payment_received: bool
    balance_paid: bool


class ReceiptContractSearchOutSchema(BaseModel):
    """收款选择合同响应"""

    id: int
    contract_no: str
    contract_name: str
    contract_status: str
    contract_amount: Decimal
    customer_id: int
    person_id: int
    person_name: str | None = None
    person_display_no: str | None = None
    person_mobile: str | None = None
    store_id: int
    store_name: str | None = None
    owner_user_id: int | None = None
    owner_user_name: str | None = None


class ReceiptQueryParam:
    """收款查询参数"""

    def __init__(
        self,
        keyword: str | None = Query(None, description="关键词"),
        contract_id: int | None = Query(None, description="合同ID"),
        receipt_type: str | None = Query(None, description="收款类型"),
        payment_scene: str | None = Query(None, description="支付场景"),
        pay_method: str | None = Query(None, description="支付方式"),
        receipt_status: str | None = Query(None, description="收款状态"),
        store_id: int | None = Query(None, description="门店ID"),
        owner_user_id: int | None = Query(None, description="销售ID"),
        submitted_start: datetime | None = Query(None, description="提交开始时间"),
        submitted_end: datetime | None = Query(None, description="提交结束时间"),
        confirmed_start: datetime | None = Query(None, description="确认开始时间"),
        confirmed_end: datetime | None = Query(None, description="确认结束时间"),
    ) -> None:
        self.keyword = keyword.strip() if keyword else None
        self.contract_id = contract_id
        self.receipt_type = receipt_type
        self.payment_scene = payment_scene
        self.pay_method = pay_method
        self.receipt_status = receipt_status
        self.store_id = store_id
        self.owner_user_id = owner_user_id
        self.submitted_start = submitted_start
        self.submitted_end = submitted_end
        self.confirmed_start = confirmed_start
        self.confirmed_end = confirmed_end
