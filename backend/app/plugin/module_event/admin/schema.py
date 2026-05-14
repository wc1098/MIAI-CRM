from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class EventQueryParam(BaseModel):
    page_no: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    keyword: str | None = None
    event_status: str | None = None
    event_type: str | None = None
    store_id: int | None = None
    start_time: list[datetime] | None = None


class EventUpsertSchema(BaseModel):
    store_id: int | None = Field(default=None, description="归属门店ID")
    title: str = Field(..., min_length=1, max_length=128)
    subtitle: str | None = Field(default=None, max_length=255)
    event_type: str = Field(..., min_length=1, max_length=32)
    cover_url: str | None = Field(default=None, max_length=500)
    location: str = Field(..., min_length=1, max_length=255)
    start_time: datetime
    end_time: datetime
    register_deadline: datetime
    detail_html: str | None = None
    effect_html: str | None = None
    male_quota: int = Field(default=0, ge=0)
    female_quota: int = Field(default=0, ge=0)
    male_fee: Decimal = Field(default=Decimal("0.00"), ge=0)
    female_fee: Decimal = Field(default=Decimal("0.00"), ge=0)
    vip_free: bool = False
    require_realname: bool = True
    min_age: int | None = Field(default=None, ge=18, le=100)
    max_age: int | None = Field(default=None, ge=18, le=100)
    description: str | None = None

    @field_validator("cover_url")
    @classmethod
    def _validate_cover_url(cls, value: str | None) -> str | None:
        if value and value.startswith(("wxfile://", "http://tmp", "file://")):
            raise ValueError("活动资源必须先上传到OSS后再保存")
        return value

    @model_validator(mode="after")
    def _validate_time_and_age(self) -> "EventUpsertSchema":
        if self.end_time <= self.start_time:
            raise ValueError("活动结束时间必须晚于开始时间")
        if self.register_deadline > self.start_time:
            raise ValueError("报名截止时间不能晚于活动开始时间")
        if self.min_age and self.max_age and self.min_age > self.max_age:
            raise ValueError("最小年龄不能大于最大年龄")
        if self.male_quota + self.female_quota <= 0:
            raise ValueError("活动名额必须大于0")
        return self


class EventEffectSchema(BaseModel):
    effect_html: str | None = None


class AdminCheckinSchema(BaseModel):
    registration_id: int = Field(..., ge=1)


class EventOutSchema(BaseModel):
    id: int
    store_id: int
    store_name: str | None = None
    created_id: int | None = None
    created_name: str | None = None
    title: str
    subtitle: str | None = None
    event_type: str
    cover_url: str | None = None
    location: str
    start_time: datetime
    end_time: datetime
    register_deadline: datetime
    detail_html: str | None = None
    effect_html: str | None = None
    male_quota: int
    female_quota: int
    male_fee: Decimal
    female_fee: Decimal
    vip_free: bool
    require_realname: bool
    min_age: int | None = None
    max_age: int | None = None
    event_status: str
    published_by: int | None = None
    published_at: datetime | None = None
    male_registered: int = 0
    female_registered: int = 0
    checked_in_count: int = 0
    payment_summary: list[dict[str, Any]] = Field(default_factory=list)

    class Config:
        from_attributes = True
