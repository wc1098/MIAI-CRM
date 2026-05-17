import re
from decimal import Decimal

from fastapi import Query
from pydantic import BaseModel, Field, field_validator

CERTIFICATION_LEVELS = ("basic", "advanced", "premium")
MANUAL_ITEM_CODES = {"education", "income", "marital", "house", "car", "visit", "occupation"}
ID_CARD_PATTERN = re.compile(r"^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])([0-2]\d|3[01])\d{3}[\dXx]$")


class CertificationItemUpsertSchema(BaseModel):
    item_name: str = Field(..., min_length=1, max_length=64, description="认证项名称")
    verify_mode: str = Field(..., pattern="^(auto_api|manual)$", description="核验方式")
    verifier_code: str | None = Field(default=None, max_length=64, description="核验器编码")
    material_required: bool = Field(default=False, description="是否需要材料")
    material_desc: str | None = Field(default=None, max_length=1000, description="材料说明")
    validity_days: int | None = Field(default=None, ge=1, le=36500, description="有效期天数")
    sort: int = Field(default=0, ge=0, le=9999, description="排序")
    status: str = Field(default="0", description="状态")


class CertificationPackageUpsertSchema(BaseModel):
    level_name: str = Field(..., min_length=1, max_length=64, description="等级名称")
    price: Decimal = Field(..., ge=0, description="价格")
    item_codes: list[str] = Field(..., min_length=1, description="包含认证项")
    reward_coupon_count: int = Field(default=0, ge=0, le=999, description="赠送解锁券数量")
    reward_coupon_valid_days: int = Field(default=7, ge=1, le=3650, description="赠券有效天数")
    benefit_desc: str | None = Field(default=None, max_length=1000, description="权益说明")
    sort: int = Field(default=0, ge=0, le=9999, description="排序")
    status: str = Field(default="0", description="状态")


class CertificationOrderCreateSchema(BaseModel):
    package_id: int = Field(..., description="认证套餐ID")


class RealNameSubmitSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="姓名")
    id_card_no: str = Field(..., min_length=15, max_length=32, description="身份证号")

    @field_validator("name", "id_card_no")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class ManualSubmitSchema(BaseModel):
    item_code: str = Field(..., min_length=1, max_length=64, description="认证项编码")
    payload: dict | None = Field(default=None, description="提交内容")


class ReviewSchema(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$", description="审核动作")
    reject_reason: str | None = Field(default=None, max_length=500, description="驳回原因")


class SensitiveViewSchema(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500, description="查看原因")


class CertificationApplicationQueryParam:
    def __init__(
        self,
        keyword: str | None = Query(None, description="编号/昵称/手机号/姓名"),
        status: str | None = Query(None, description="申请状态"),
        level_code: str | None = Query(None, description="认证等级"),
    ) -> None:
        self.keyword = keyword.strip() if keyword else None
        self.status = status.strip() if status else None
        self.level_code = level_code.strip() if level_code else None


class CertificationRecordQueryParam:
    def __init__(
        self,
        keyword: str | None = Query(None, description="编号/昵称/手机号/姓名"),
        status: str | None = Query(None, description="单项状态"),
        item_code: str | None = Query(None, description="认证项编码"),
    ) -> None:
        self.keyword = keyword.strip() if keyword else None
        self.status = status.strip() if status else None
        self.item_code = item_code.strip() if item_code else None


class CertificationLogQueryParam:
    def __init__(
        self,
        keyword: str | None = Query(None, description="编号/昵称/手机号/姓名"),
        application_id: int | None = Query(None, description="申请ID"),
        record_id: int | None = Query(None, description="单项记录ID"),
        status: str | None = Query(None, description="状态"),
    ) -> None:
        self.keyword = keyword.strip() if keyword else None
        self.application_id = application_id
        self.record_id = record_id
        self.status = status.strip() if status else None
