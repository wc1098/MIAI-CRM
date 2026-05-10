import re
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


ORDER_NO_PATTERN = re.compile(r"^[A-Za-z0-9_]{1,32}$")


def validate_order_no(value: str) -> str:
    v = value.strip()
    if not ORDER_NO_PATTERN.match(v):
        raise ValueError("订单号仅允许字母/数字/下划线，长度1-32")
    return v


def validate_amount(value: str) -> str:
    v = value.strip()
    try:
        amount = Decimal(v)
    except InvalidOperation as e:
        raise ValueError("金额必须为数字字符串") from e
    if amount < 0:
        raise ValueError("金额不能为负数")
    if amount.as_tuple().exponent < -2:
        raise ValueError("金额最多支持两位小数")
    return v


class CloudPayResponseSchema(BaseModel):
    code: str | None = Field(default=None, description="云支付返回码")
    msg: str | None = Field(default=None, description="云支付返回描述")
    sub_code: str | None = Field(default=None, description="云支付业务错误码")
    sub_msg: str | None = Field(default=None, description="云支付业务错误描述")
    method: str | None = Field(default=None, description="接口方法")
    data: dict[str, Any] | list[Any] | str | None = Field(default=None, description="业务数据")
    sign: str | None = Field(default=None, description="响应签名")
    sign_valid: bool | None = Field(default=None, description="响应签名是否通过")


class CloudPayBaseTradeSchema(BaseModel):
    dept_id: int = Field(..., ge=1, description="本系统门店ID")
    out_order_no: str = Field(..., max_length=32, description="商户订单号")

    @field_validator("out_order_no")
    @classmethod
    def _validate_out_order_no(cls, value: str) -> str:
        return validate_order_no(value)


class CloudPayPaySchema(CloudPayBaseTradeSchema):
    total_amount: str = Field(..., max_length=28, description="订单总金额，单位元")
    auth_code: str = Field(..., min_length=1, max_length=32, description="支付授权码")
    subject: str = Field(..., min_length=1, max_length=256, description="订单标题")
    scene: str = Field(default="bar_code", description="支付场景")
    pay_channel: str | None = Field(default=None, max_length=32, description="支付渠道")
    body: str | None = Field(default=None, max_length=128, description="订单描述")
    operator_id: str | None = Field(default=None, max_length=28, description="操作员编号")
    notify_url: str | None = Field(default=None, max_length=255, description="异步回调地址")

    @field_validator("total_amount")
    @classmethod
    def _validate_total_amount(cls, value: str) -> str:
        return validate_amount(value)


class CloudPayPrecreateSchema(CloudPayBaseTradeSchema):
    total_amount: str = Field(..., max_length=28, description="订单总金额，单位元")
    subject: str = Field(..., min_length=1, max_length=256, description="订单标题")
    pay_channel: str = Field(..., max_length=32, description="支付渠道")
    body: str | None = Field(default=None, max_length=128, description="订单描述")
    operator_id: str | None = Field(default=None, max_length=28, description="操作员编号")
    notify_url: str | None = Field(default=None, max_length=255, description="异步回调地址")

    @field_validator("total_amount")
    @classmethod
    def _validate_total_amount(cls, value: str) -> str:
        return validate_amount(value)


class CloudPayCreateSchema(CloudPayBaseTradeSchema):
    total_amount: str = Field(..., max_length=28, description="订单总金额，单位元")
    buyer_id: str = Field(..., min_length=1, max_length=28, description="买家用户号")
    subject: str = Field(..., min_length=1, max_length=256, description="订单标题")
    pay_channel: str = Field(..., max_length=32, description="支付渠道")
    body: str | None = Field(default=None, max_length=128, description="订单描述")
    operator_id: str | None = Field(default=None, max_length=28, description="操作员编号")
    notify_url: str | None = Field(default=None, max_length=255, description="异步回调地址")
    sub_app_id: str | None = Field(default=None, max_length=32, description="微信子应用ID")

    @field_validator("total_amount")
    @classmethod
    def _validate_total_amount(cls, value: str) -> str:
        return validate_amount(value)


class CloudPayQuerySchema(CloudPayBaseTradeSchema):
    trans_no: str | None = Field(default=None, max_length=64, description="第三方支付交易号")


class CloudPayRefundSchema(BaseModel):
    dept_id: int = Field(..., ge=1, description="本系统门店ID")
    out_order_no: str | None = Field(default=None, max_length=32, description="商户订单号")
    trans_no: str | None = Field(default=None, max_length=64, description="第三方支付交易号")
    refund_amount: str = Field(..., max_length=28, description="退款金额，单位元")
    out_request_no: str = Field(..., max_length=32, description="外部退款单号")
    refund_reason: str | None = Field(default=None, max_length=256, description="退款原因")
    operator_id: str | None = Field(default=None, max_length=28, description="操作员编号")
    pay_channel: str | None = Field(default=None, max_length=32, description="支付渠道")

    @field_validator("out_order_no")
    @classmethod
    def _validate_out_order_no(cls, value: str | None) -> str | None:
        return validate_order_no(value) if value else value

    @field_validator("out_request_no")
    @classmethod
    def _validate_out_request_no(cls, value: str) -> str:
        return validate_order_no(value)

    @field_validator("refund_amount")
    @classmethod
    def _validate_refund_amount(cls, value: str) -> str:
        return validate_amount(value)

    @model_validator(mode="after")
    def _validate_order_reference(self) -> "CloudPayRefundSchema":
        if not self.out_order_no and not self.trans_no:
            raise ValueError("out_order_no 和 trans_no 不能同时为空")
        return self


class CloudPayRefundQuerySchema(BaseModel):
    dept_id: int = Field(..., ge=1, description="本系统门店ID")
    out_order_no: str = Field(..., max_length=32, description="商户订单号")
    out_request_no: str = Field(..., max_length=32, description="外部退款单号")

    @field_validator("out_order_no", "out_request_no")
    @classmethod
    def _validate_order_no(cls, value: str) -> str:
        return validate_order_no(value)
