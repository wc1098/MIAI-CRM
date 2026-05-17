from decimal import Decimal

from fastapi import Query
from pydantic import BaseModel, Field


class SubscriptionPlanUpsertSchema(BaseModel):
    plan_code: str = Field(..., max_length=32, description="方案编码")
    plan_name: str = Field(..., max_length=64, description="方案名称")
    pay_period: str = Field(..., pattern="^(month|quarter|year)$", description="支付周期")
    period_days: int = Field(..., ge=1, le=3660, description="权益天数")
    price: Decimal = Field(..., ge=0, description="价格")
    monthly_recommend_count: int = Field(default=4, ge=1, le=99, description="每月推荐数")
    total_quota: int = Field(..., ge=1, le=999, description="总槽位")
    benefit_desc: str | None = Field(default=None, max_length=1000, description="权益说明")
    sort: int = Field(default=0, ge=0, le=9999, description="排序")
    status: str = Field(default="0", description="状态")


class SubscriptionOrderCreateSchema(BaseModel):
    plan_id: int = Field(..., description="订阅方案ID")


class SubscriptionAdminQueryParam:
    def __init__(
        self,
        keyword: str | None = Query(None, description="编号/昵称/手机号/姓名"),
        status: str | None = Query(None, description="状态"),
    ) -> None:
        self.keyword = keyword.strip() if keyword else None
        self.status = status.strip() if status else None
