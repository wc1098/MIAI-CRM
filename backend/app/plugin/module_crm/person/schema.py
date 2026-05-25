from datetime import date, datetime
from typing import Any

from fastapi import Query
from pydantic import BaseModel, Field

from app.core.validator import DateTimeStr


class PersonQueryParam:
    """用户资源中心查询参数"""

    def __init__(
        self,
        keyword: str | None = Query(None, description="编号/姓名/手机号"),
        store_id: int | None = Query(None, description="门店ID"),
        owner_sales_id: int | None = Query(None, description="当前销售ID"),
        service_owner_user_id: int | None = Query(None, description="当前服务红娘ID"),
        identity_tag: str | None = Query(None, description="身份标签"),
        certification_level: str | None = Query(None, description="认证等级"),
        quality_level: str | None = Query(None, description="资料完整度等级"),
        latest_activity_start: datetime | None = Query(None, description="最近活动开始时间"),
        latest_activity_end: datetime | None = Query(None, description="最近活动结束时间"),
    ) -> None:
        self.keyword = keyword.strip() if keyword else None
        self.store_id = store_id
        self.owner_sales_id = owner_sales_id
        self.service_owner_user_id = service_owner_user_id
        self.identity_tag = identity_tag
        self.certification_level = certification_level
        self.quality_level = quality_level
        self.latest_activity_start = latest_activity_start
        self.latest_activity_end = latest_activity_end


class SensitiveViewSchema(BaseModel):
    """敏感信息查看请求"""

    reason: str = Field(..., min_length=1, max_length=500, description="查看原因")


class PersonUserOptionSchema(BaseModel):
    """用户资源中心人员筛选选项"""

    id: int
    name: str | None = None
    username: str | None = None
    dept_id: int | None = None


class PersonBriefSchema(BaseModel):
    id: int
    display_no: str | None = None
    name: str
    gender: str
    primary_mobile: str | None = None
    mobile_masked: str | None = None
    wechat: str | None = None
    birth_date: date | None = None
    age: int | None = None
    height_cm: int | None = None
    education: str | None = None
    annual_income: str | None = None
    marital_status: str | None = None
    occupation: str | None = None
    occupation_code: str | None = None
    residence: str | None = None
    photo_urls: list[str] = Field(default_factory=list)
    certification_level: str | None = None
    id_card_no_masked: str | None = None


class PersonQualitySchema(BaseModel):
    score: int
    quality_level: str
    basic_score: int
    display_score: int
    service_score: int
    missing_basic: list[str] = Field(default_factory=list)
    missing_display: list[str] = Field(default_factory=list)
    missing_service: list[str] = Field(default_factory=list)
    risk_flags: list[dict[str, str]] = Field(default_factory=list)


class PersonListOutSchema(BaseModel):
    person: PersonBriefSchema
    store: dict[str, Any] | None = None
    owner_sales: dict[str, Any] | None = None
    service_owner: dict[str, Any] | None = None
    identity_tags: list[str] = Field(default_factory=list)
    identity_summary: dict[str, Any] = Field(default_factory=dict)
    quality: PersonQualitySchema
    latest_activity_at: DateTimeStr | None = None
    created_time: DateTimeStr | None = None


class PersonRelationSchema(BaseModel):
    lead: dict[str, Any] | None = None
    customer: dict[str, Any] | None = None
    vip: dict[str, Any] | None = None
    service_case: dict[str, Any] | None = None
    candidate: dict[str, Any] | None = None
    backup_items: list[dict[str, Any]] = Field(default_factory=list)
    join_requests: list[dict[str, Any]] = Field(default_factory=list)
    miniprogram_user: dict[str, Any] | None = None
    subscription: dict[str, Any] | None = None
    certification: dict[str, Any] | None = None
    partner_preference: dict[str, Any] | None = None
    ai_profile: dict[str, Any] | None = None


class PersonDetailOutSchema(BaseModel):
    person: PersonBriefSchema
    relations: PersonRelationSchema
    quality: PersonQualitySchema
    sensitive_log_count: int = 0


class PersonTimelineOutSchema(BaseModel):
    id: str
    source_type: str
    title: str
    occurred_at: DateTimeStr
    content: str | None = None
    operator_user_id: int | None = None
    operator_user_name: str | None = None
    related_id: int | None = None
    payload: dict[str, Any] | None = None


class SensitiveLogOutSchema(BaseModel):
    id: int
    access_type: str
    permission_result: str
    reason: str | None = None
    operator_id: int | None = None
    operator_name: str | None = None
    accessed_at: DateTimeStr | None = None
