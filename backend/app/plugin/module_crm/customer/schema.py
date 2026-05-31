import re
from datetime import date, datetime

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.base_schema import BaseSchema, CommonSchema, UserBySchema
from app.core.validator import DateTimeStr
from app.plugin.module_crm.preference.schema import (
    PartnerPreferenceOutSchema,
    PartnerPreferencePayload,
    PartnerPreferenceVersionOutSchema,
)

MOBILE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
GENDER_VALUES = {"0", "1", "2"}
CUSTOMER_STAGES = {
    "profiling",
    "following",
    "appointed",
    "visited",
    "consulted",
    "signing",
    "contracted",
    "converted_vip",
}
PROCESS_TYPES = {"follow", "appointment", "visit", "visit_checkin", "consultation", "no_show", "appointment_cancel"}
FOLLOW_METHODS = {"phone", "wechat", "appointment", "consultation"}
APPOINTMENT_STATUSES = {"pending", "checked_in", "consulted", "no_show", "cancelled"}
RETURN_REASONS = {
    "invalid",
    "no_response",
    "not_ready",
    "budget_mismatch",
    "requirement_mismatch",
    "duplicate",
    "rejected",
    "other",
}


class CustomerPersonPayload(BaseModel):
    """客户主档案资料"""

    mobile: str = Field(..., description="手机号")
    name: str = Field(..., max_length=64, description="姓名")
    gender: str = Field(..., description="性别")
    wechat: str | None = Field(default=None, max_length=64, description="微信号")
    birth_date: date | None = Field(default=None, description="出生日期")
    height_cm: int | None = Field(default=None, ge=80, le=260, description="身高cm")
    weight_kg: int | None = Field(default=None, ge=30, le=250, description="体重kg")
    ethnicity: str | None = Field(default=None, max_length=32, description="民族")
    occupation: str | None = Field(default=None, max_length=64, description="职业")
    occupation_code: str | None = Field(default=None, max_length=32, description="标准职业")
    annual_income: str | None = Field(default=None, max_length=32, description="年收入")
    marital_status: str | None = Field(default=None, max_length=32, description="婚况")
    education: str | None = Field(default=None, max_length=32, description="学历")
    graduated_school: str | None = Field(default=None, max_length=128, description="毕业院校")
    major: str | None = Field(default=None, max_length=128, description="专业")
    unit_type: str | None = Field(default=None, max_length=32, description="单位类型")
    job_title: str | None = Field(default=None, max_length=64, description="职务")
    work_company: str | None = Field(default=None, max_length=128, description="工作单位")
    hometown: str | None = Field(default=None, max_length=128, description="籍贯")
    residence: str | None = Field(default=None, max_length=128, description="常驻地")
    house_status: str | None = Field(default=None, max_length=32, description="房产信息")
    car_status: str | None = Field(default=None, max_length=32, description="购车信息")
    accept_long_distance_self: bool | None = Field(default=None, description="本人是否接受异地")
    accept_flash_marriage: bool | None = Field(default=None, description="本人是否接受闪婚")
    willing_relocate: bool | None = Field(default=None, description="本人是否愿意搬家")
    marriage_plan: str | None = Field(default=None, max_length=32, description="结婚计划")
    family_background: str | None = Field(default=None, max_length=2000, description="家庭情况")
    profile_remark: str | None = Field(default=None, max_length=2000, description="档案备注")
    photo_urls: list[str] = Field(default_factory=list, description="照片相册")
    profile_intro: str | None = Field(default=None, max_length=2000, description="个人介绍")
    id_card_no: str | None = Field(default=None, max_length=32, description="身份证号")

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
        "occupation_code",
        "annual_income",
        "marital_status",
        "education",
        "graduated_school",
        "major",
        "unit_type",
        "job_title",
        "work_company",
        "hometown",
        "residence",
        "house_status",
        "car_status",
        "marriage_plan",
        "family_background",
        "profile_remark",
        "profile_intro",
        "id_card_no",
    )
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class CustomerUpdateSchema(CustomerPersonPayload):
    """客户编辑模型"""

    current_stage: str | None = Field(default=None, description="当前阶段")
    next_follow_at: datetime | None = Field(default=None, description="下次跟进时间")
    partner_preference: PartnerPreferencePayload | None = Field(default=None, description="择偶要求")
    description: str | None = Field(default=None, max_length=255, description="备注")

    @field_validator("current_stage")
    @classmethod
    def validate_stage(cls, value: str | None) -> str | None:
        if value is not None and value not in CUSTOMER_STAGES:
            raise ValueError("客户阶段不正确")
        return value


class CustomerProcessCreateSchema(BaseModel):
    """客户过程记录创建模型"""

    method: str | None = Field(default=None, max_length=32, description="方式")
    result: str | None = Field(default=None, max_length=32, description="结果")
    content: str = Field(..., min_length=1, max_length=2000, description="内容")
    next_follow_at: datetime | None = Field(default=None, description="下次跟进时间")
    scheduled_at: datetime | None = Field(default=None, description="预约/计划时间")
    appointment_slot: str | None = Field(default=None, max_length=32, description="预约时段")
    visit_purpose: str | None = Field(default=None, max_length=32, description="到访目的")
    promised_gift: str | None = Field(default=None, max_length=255, description="承诺礼品")
    need_summary: str | None = Field(default=None, max_length=2000, description="需求摘要")
    budget_range: str | None = Field(default=None, max_length=64, description="预算区间")
    main_objection: str | None = Field(default=None, max_length=2000, description="主要异议")
    intention_level: str | None = Field(default=None, max_length=32, description="意向等级")
    next_action: str | None = Field(default=None, max_length=255, description="下一步动作")
    enter_signing: bool = Field(default=False, description="是否进入签约推进")

    @field_validator("next_follow_at", "scheduled_at", mode="before")
    @classmethod
    def empty_datetime_to_none(cls, value: datetime | str | None) -> datetime | str | None:
        if value == "":
            return None
        return value

    @field_validator("method")
    @classmethod
    def validate_method(cls, value: str | None) -> str | None:
        if value is not None and value not in FOLLOW_METHODS:
            raise ValueError("跟进方式不正确")
        return value


class CustomerVisitConsultationSchema(BaseModel):
    """到店管理记录面谈模型"""

    content: str = Field(..., min_length=1, max_length=2000, description="面谈内容")
    need_summary: str | None = Field(default=None, max_length=2000, description="需求摘要")
    budget_range: str | None = Field(default=None, max_length=64, description="预算区间")
    main_objection: str | None = Field(default=None, max_length=2000, description="主要异议")
    intention_level: str | None = Field(default=None, max_length=32, description="意向等级")
    next_follow_at: datetime | None = Field(default=None, description="下次跟进时间")
    enter_signing: bool = Field(default=False, description="是否进入签约推进")


class CustomerCertificationMaterialSaveSchema(BaseModel):
    """客户认证资料存档保存模型"""

    item_code: str = Field(..., min_length=1, max_length=64, description="资料项编码")
    item_name: str | None = Field(default=None, max_length=64, description="资料项名称")
    file_name: str | None = Field(default=None, max_length=255, description="文件名")
    file_path: str | None = Field(default=None, max_length=512, description="文件路径")
    file_url: str = Field(..., min_length=1, max_length=1000, description="文件URL")
    material_type: str = Field(default="image", max_length=32, description="资料类型")
    payload: dict | None = Field(default=None, description="资料扩展")


class CustomerTransferOwnerSchema(BaseModel):
    """同店转派模型"""

    customer_id: int = Field(..., description="客户ID")
    owner_user_id: int = Field(..., description="目标归属人ID")
    remark: str | None = Field(default=None, max_length=255, description="备注")


class CustomerTransferStoreSchema(BaseModel):
    """跨店转交模型"""

    customer_id: int = Field(..., description="客户ID")
    store_id: int = Field(..., description="目标门店ID")
    owner_user_id: int = Field(..., description="目标归属人ID")
    remark: str | None = Field(default=None, max_length=255, description="备注")


class CustomerReturnLeadSchema(BaseModel):
    """客户退回线索模型"""

    reason_type: str = Field(..., description="退回原因分类")
    reason: str = Field(..., min_length=1, max_length=1000, description="退回说明")

    @field_validator("reason_type")
    @classmethod
    def validate_reason_type(cls, value: str) -> str:
        if value not in RETURN_REASONS:
            raise ValueError("退回原因分类不正确")
        return value


class CustomerPersonOutSchema(BaseSchema, UserBySchema):
    """客户人员响应模型"""

    model_config = ConfigDict(from_attributes=True)

    brand_id: int
    display_no: str | None = None
    name: str
    gender: str
    primary_mobile: str
    wechat: str | None = None
    birth_date: date | None = None
    height_cm: int | None = None
    weight_kg: int | None = None
    ethnicity: str | None = None
    occupation: str | None = None
    occupation_code: str | None = None
    annual_income: str | None = None
    marital_status: str | None = None
    education: str | None = None
    graduated_school: str | None = None
    major: str | None = None
    unit_type: str | None = None
    job_title: str | None = None
    work_company: str | None = None
    hometown: str | None = None
    residence: str | None = None
    house_status: str | None = None
    car_status: str | None = None
    accept_long_distance_self: bool | None = None
    accept_flash_marriage: bool | None = None
    willing_relocate: bool | None = None
    marriage_plan: str | None = None
    family_background: str | None = None
    profile_remark: str | None = None
    photo_urls: list[str] | None = None
    profile_intro: str | None = None
    id_card_no: str | None = None
    certification_level: str
    certification_summary: dict | None = None


class CustomerOutSchema(BaseSchema, UserBySchema):
    """客户列表响应模型"""

    model_config = ConfigDict(from_attributes=True)

    brand_id: int
    person_id: int
    lead_id: int | None = None
    store_id: int
    owner_user_id: int
    current_stage: str
    max_stage: str
    latest_follow_at: DateTimeStr | None = None
    next_follow_at: DateTimeStr | None = None
    ended_at: DateTimeStr | None = None
    end_reason: str | None = None
    returned_lead_id: int | None = None
    converted_vip_at: DateTimeStr | None = None
    person: CustomerPersonOutSchema
    store: CommonSchema | None = None
    owner_user: CommonSchema | None = None
    mobile_masked: str | None = None
    wechat_masked: str | None = None
    id_card_no_masked: str | None = None
    can_view_contact: bool = False
    can_view_id_card: bool = False
    age: int | None = None
    constellation: str | None = None
    zodiac: str | None = None
    ai_profile: dict | None = None
    partner_preference: PartnerPreferenceOutSchema | None = None


class CustomerProcessOutSchema(BaseSchema, UserBySchema):
    """客户过程记录响应模型"""

    model_config = ConfigDict(from_attributes=True)

    brand_id: int
    customer_id: int | None = None
    person_id: int
    record_type: str
    occurred_at: DateTimeStr
    method: str | None = None
    result: str | None = None
    content: str
    next_follow_at: DateTimeStr | None = None
    scheduled_at: DateTimeStr | None = None
    appointment_slot: str | None = None
    visit_purpose: str | None = None
    promised_gift: str | None = None
    appointment_status: str | None = None
    checked_in_at: DateTimeStr | None = None
    checked_in_user_id: int | None = None
    checked_in_user_name: str | None = None
    need_summary: str | None = None
    budget_range: str | None = None
    main_objection: str | None = None
    intention_level: str | None = None
    next_action: str | None = None
    enter_signing: bool | None = None
    operator_user_id: int | None = None
    operator_user_name: str | None = None


class CustomerLifecycleOutSchema(BaseSchema, UserBySchema):
    """客户生命周期响应模型"""

    model_config = ConfigDict(from_attributes=True)

    brand_id: int
    customer_id: int
    person_id: int
    operation_type: str
    operator_user_id: int | None = None
    change_detail: dict | None = None
    remark: str | None = None


class CustomerCertificationMaterialOutSchema(BaseSchema, UserBySchema):
    """客户认证资料存档响应模型"""

    model_config = ConfigDict(from_attributes=True)

    brand_id: int
    customer_id: int
    person_id: int
    item_code: str
    item_name: str
    material_type: str
    file_name: str | None = None
    file_path: str | None = None
    file_url: str
    payload: dict | None = None
    collected_by: int | None = None
    certification_record_id: int | None = None
    certification_record_status: str | None = None
    certification_reject_reason: str | None = None
    certification_reviewed_at: datetime | None = None


class CustomerDetailOutSchema(CustomerOutSchema):
    """客户总档案响应模型"""

    process_records: list[CustomerProcessOutSchema] = Field(default_factory=list)
    lead_process_records: list[dict] = Field(default_factory=list)
    lifecycle_records: list[CustomerLifecycleOutSchema] = Field(default_factory=list)
    lead_lifecycle_records: list[dict] = Field(default_factory=list)
    partner_preference_versions: list[PartnerPreferenceVersionOutSchema] = Field(default_factory=list)
    certification: dict | None = None


class CustomerPrintCardSchema(BaseModel):
    """A4对外资料卡数据"""

    brand_name: str = "觅AI"
    printed_at: DateTimeStr
    customer_no: str | None = None
    display_name: str
    gender: str
    age: int | None = None
    constellation: str | None = None
    zodiac: str | None = None
    height_cm: int | None = None
    weight_kg: int | None = None
    education: str | None = None
    occupation: str | None = None
    occupation_code: str | None = None
    graduated_school: str | None = None
    major: str | None = None
    unit_type: str | None = None
    job_title: str | None = None
    work_company: str | None = None
    annual_income: str | None = None
    marital_status: str | None = None
    hometown: str | None = None
    residence: str | None = None
    house_status: str | None = None
    car_status: str | None = None
    profile_intro: str | None = None
    family_background: str | None = None
    first_photo_url: str | None = None
    partner_preference: PartnerPreferenceOutSchema | None = None
    miai_impression: str | None = None


class CustomerQueryParam:  # noqa: B903
    """客户查询参数"""

    def __init__(
        self,
        keyword: str | None = Query(None, description="客户编号/姓名/手机号"),
        current_stage: str | None = Query(None, description="当前阶段"),
        max_stage: str | None = Query(None, description="最高进展"),
        gender: str | None = Query(None, description="性别"),
        age_min: int | None = Query(None, description="最小年龄"),
        age_max: int | None = Query(None, description="最大年龄"),
        height_min_cm: int | None = Query(None, description="最小身高cm"),
        height_max_cm: int | None = Query(None, description="最大身高cm"),
        ethnicity: str | None = Query(None, description="民族"),
        occupation_codes: list[str] | None = Query(None, description="职业"),
        annual_income: list[str] | None = Query(None, description="年收入"),
        marital_status: str | None = Query(None, description="婚况"),
        education: list[str] | None = Query(None, description="学历"),
        unit_type: list[str] | None = Query(None, description="单位类型"),
        house_status: list[str] | None = Query(None, description="住房情况"),
        car_status: list[str] | None = Query(None, description="购车情况"),
        hometown: str | None = Query(None, description="籍贯"),
        residence: str | None = Query(None, description="常驻地"),
        store_id: int | None = Query(None, description="归属门店"),
        owner_user_id: int | None = Query(None, description="归属人"),
        latest_follow_time: list[DateTimeStr] | None = Query(None, description="最近跟进时间范围"),
        next_follow_time: list[DateTimeStr] | None = Query(None, description="下次跟进时间范围"),
        created_time: list[DateTimeStr] | None = Query(None, description="建档时间范围"),
    ) -> None:
        self.keyword = keyword
        self.current_stage = current_stage
        self.max_stage = max_stage
        self.gender = gender
        self.age_min = age_min
        self.age_max = age_max
        self.height_min_cm = height_min_cm
        self.height_max_cm = height_max_cm
        self.ethnicity = ethnicity
        self.occupation_codes = occupation_codes
        self.annual_income = annual_income
        self.marital_status = marital_status
        self.education = education
        self.unit_type = unit_type
        self.house_status = house_status
        self.car_status = car_status
        self.hometown = hometown
        self.residence = residence
        self.store_id = store_id
        self.owner_user_id = owner_user_id
        self.latest_follow_time = latest_follow_time
        self.next_follow_time = next_follow_time
        self.created_time = created_time


class CustomerVisitQueryParam:  # noqa: B903
    """到店管理查询参数"""

    def __init__(
        self,
        keyword: str | None = Query(None, description="客户编号/姓名/手机号"),
        scheduled_time: list[DateTimeStr] | None = Query(None, description="预约时间范围"),
        appointment_slot: str | None = Query(None, description="预约时段"),
        visit_purpose: str | None = Query(None, description="到访目的"),
        appointment_status: str | None = Query(None, description="预约状态"),
        operator_user_id: int | None = Query(None, description="邀约人ID"),
        store_id: int | None = Query(None, description="门店ID"),
    ) -> None:
        self.keyword = keyword
        self.scheduled_time = scheduled_time
        self.appointment_slot = appointment_slot
        self.visit_purpose = visit_purpose
        self.appointment_status = appointment_status
        self.operator_user_id = operator_user_id
        self.store_id = store_id
