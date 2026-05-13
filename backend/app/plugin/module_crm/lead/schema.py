import re
from datetime import date, datetime

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.base_schema import BaseSchema, CommonSchema, UserBySchema
from app.core.validator import DateTimeStr

MOBILE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
GENDER_VALUES = {"0", "1", "2"}
LEAD_TYPES = {"pending", "new", "second_hand", "invalid", "converted_customer"}
POOL_TYPES = {"hq_pool", "store_pool", "sales_private"}
ACTION_TYPES = {"follow", "invalid", "release", "convert_customer"}
FOLLOW_METHODS = {"phone", "wechat", "meeting", "other"}


class LeadPersonPayload(BaseModel):
    """线索人员资料"""

    mobile: str = Field(..., description="手机号")
    name: str = Field(..., max_length=64, description="姓名")
    gender: str = Field(..., description="性别")
    wechat: str | None = Field(default=None, max_length=64, description="微信号")
    birth_date: date | None = Field(default=None, description="出生日期")
    height_cm: int | None = Field(default=None, ge=80, le=260, description="身高cm")
    ethnicity: str | None = Field(default=None, max_length=32, description="民族")
    occupation: str | None = Field(default=None, max_length=64, description="职业")
    annual_income: str | None = Field(default=None, max_length=32, description="年收入")
    marital_status: str | None = Field(default=None, max_length=32, description="婚况")
    education: str | None = Field(default=None, max_length=32, description="学历")
    hometown: str | None = Field(default=None, max_length=128, description="籍贯")
    residence: str | None = Field(default=None, max_length=128, description="常驻地")
    house_status: str | None = Field(default=None, max_length=32, description="房产信息")
    car_status: str | None = Field(default=None, max_length=32, description="购车信息")
    photo_urls: list[str] = Field(default_factory=list, description="照片相册")

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, value: str) -> str:
        value = value.strip()
        if not MOBILE_PATTERN.match(value):
            raise ValueError("手机号格式不正确")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("姓名不能为空")
        return value

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value: str) -> str:
        if value not in GENDER_VALUES:
            raise ValueError("性别必须为0、1或2")
        return value

    @field_validator(
        "wechat",
        "ethnicity",
        "occupation",
        "annual_income",
        "marital_status",
        "education",
        "hometown",
        "residence",
        "house_status",
        "car_status",
    )
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class LeadCreateSchema(LeadPersonPayload):
    """线索创建模型"""

    source_channel_code: str | None = Field(default="MANUAL_CREATE", max_length=64, description="来源渠道编码")
    store_id: int | None = Field(default=None, description="归属门店ID")
    owner_sales_id: int | None = Field(default=None, description="归属销售ID")
    description: str | None = Field(default=None, max_length=255, description="备注")

    @field_validator("source_channel_code")
    @classmethod
    def normalize_channel(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else value


class LeadUpdateSchema(LeadPersonPayload):
    """线索编辑模型"""

    source_channel_code: str | None = Field(default=None, max_length=64, description="来源渠道编码")
    description: str | None = Field(default=None, max_length=255, description="备注")

    @field_validator("source_channel_code")
    @classmethod
    def normalize_channel(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else value


class LeadAssignSchema(BaseModel):
    """线索分配模型"""

    lead_ids: list[int] = Field(..., min_length=1, description="线索ID")
    store_id: int | None = Field(default=None, description="目标门店ID")
    owner_sales_id: int | None = Field(default=None, description="目标销售ID")
    remark: str | None = Field(default=None, max_length=255, description="备注")


class LeadClaimSchema(BaseModel):
    """销售领取线索模型"""

    lead_ids: list[int] = Field(..., min_length=1, description="线索ID")


class LeadProcessCreateSchema(BaseModel):
    """线索过程记录创建模型"""

    action_type: str = Field(..., description="动作类型")
    follow_method: str | None = Field(default=None, description="跟进方式")
    content: str = Field(..., min_length=1, max_length=2000, description="跟进内容/原因")
    next_follow_at: datetime | None = Field(default=None, description="下次跟进时间")

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, value: str) -> str:
        if value not in ACTION_TYPES:
            raise ValueError("动作类型不正确")
        return value

    @field_validator("follow_method")
    @classmethod
    def validate_follow_method(cls, value: str | None) -> str | None:
        if value is not None and value not in FOLLOW_METHODS:
            raise ValueError("跟进方式不正确")
        return value


class LeadStoreRuleSchema(BaseModel):
    """门店线索规则模型"""

    model_config = ConfigDict(from_attributes=True)

    allow_sales_claim: bool = Field(default=False, description="是否允许销售自领")
    no_follow_reclaim_days: int = Field(default=7, ge=1, le=90, description="无跟进回收天数")


class LeadMobileCheckSchema(BaseModel):
    """手机号查重响应"""

    exists: bool
    person_id: int | None = None
    lead_id: int | None = None
    name: str | None = None
    mobile: str | None = None


class PersonOutSchema(BaseSchema, UserBySchema):
    """人员响应模型"""

    model_config = ConfigDict(from_attributes=True)

    brand_id: int
    name: str
    gender: str
    primary_mobile: str
    wechat: str | None = None
    birth_date: date | None = None
    height_cm: int | None = None
    ethnicity: str | None = None
    occupation: str | None = None
    annual_income: str | None = None
    marital_status: str | None = None
    education: str | None = None
    hometown: str | None = None
    residence: str | None = None
    house_status: str | None = None
    car_status: str | None = None
    photo_urls: list[str] | None = None


class LeadOutSchema(BaseSchema, UserBySchema):
    """线索响应模型"""

    model_config = ConfigDict(from_attributes=True)

    brand_id: int
    person_id: int
    store_id: int | None = None
    owner_sales_id: int | None = None
    pool_type: str
    lead_type: str
    source_channel_code: str | None = None
    latest_source_event_id: int | None = None
    latest_follow_at: DateTimeStr | None = None
    next_follow_at: DateTimeStr | None = None
    assigned_at: DateTimeStr | None = None
    last_recycled_at: DateTimeStr | None = None
    converted_customer_at: DateTimeStr | None = None
    person: PersonOutSchema
    source_channel_name: str | None = None
    store: CommonSchema | None = None
    owner_sales: CommonSchema | None = None
    mobile_masked: str | None = None
    wechat_masked: str | None = None
    can_view_contact: bool = False


class LeadProcessOutSchema(BaseSchema, UserBySchema):
    """线索过程记录响应模型"""

    model_config = ConfigDict(from_attributes=True)

    brand_id: int
    lead_id: int
    person_id: int
    action_type: str
    follow_method: str | None = None
    content: str
    next_follow_at: DateTimeStr | None = None
    operator_user_id: int | None = None


class LeadLifecycleOutSchema(BaseSchema, UserBySchema):
    """线索生命周期响应模型"""

    model_config = ConfigDict(from_attributes=True)

    brand_id: int
    lead_id: int
    person_id: int
    operation_type: str
    operator_user_id: int | None = None
    change_detail: dict | None = None
    remark: str | None = None


class LeadDetailOutSchema(LeadOutSchema):
    """线索详情响应模型"""

    process_records: list[LeadProcessOutSchema] = Field(default_factory=list)
    lifecycle_records: list[LeadLifecycleOutSchema] = Field(default_factory=list)


class LeadImportResultSchema(BaseModel):
    """线索导入结果"""

    success_count: int
    failed_count: int
    failed_rows: list[dict]


class LeadQueryParam:
    """线索查询参数"""

    def __init__(
        self,
        keyword: str | None = Query(None, description="姓名/手机号"),
        lead_type: str | None = Query(None, description="线索类型"),
        source_channel_code: str | None = Query(None, description="来源渠道"),
        store_id: int | None = Query(None, description="归属门店"),
        owner_sales_id: int | None = Query(None, description="归属人"),
        latest_follow_time: list[DateTimeStr] | None = Query(None, description="最后跟进时间范围"),
    ) -> None:
        self.keyword = keyword
        self.lead_type = lead_type
        self.source_channel_code = source_channel_code.upper() if source_channel_code else None
        self.store_id = store_id
        self.owner_sales_id = owner_sales_id
        self.latest_follow_time = latest_follow_time
