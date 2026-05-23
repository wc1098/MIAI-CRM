from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import Query
from pydantic import BaseModel, Field

from app.core.validator import DateTimeStr
from app.plugin.module_crm.customer.schema import CustomerCertificationMaterialSaveSchema
from app.plugin.module_crm.preference.schema import PartnerPreferencePayload

VIP_STATUSES = {"pending_assign", "serving", "paused", "closed", "expired"}
SERVICE_CASE_STATUSES = {"pending_assign", "serving", "pending_close_review", "closed", "expired", "reopened"}
ENTITLEMENT_TYPES = {"recommendation", "meeting", "course"}


class VipAssignSchema(BaseModel):
    """VIP服务分配模型"""

    service_owner_user_id: int = Field(..., description="服务红娘ID")
    remark: str | None = Field(default=None, max_length=1000, description="备注")


class DeepInterviewCreateSchema(BaseModel):
    """服务深访创建模型"""

    interview_type: str = Field(..., min_length=1, max_length=32, description="深访类型")
    interviewed_at: datetime | None = Field(default=None, description="深访时间")
    content: str = Field(..., min_length=1, max_length=20000, description="深访内容")
    keywords: list[str] = Field(default_factory=list, description="关键词")
    summary: str | None = Field(default=None, max_length=5000, description="人工摘要")


class UsageCreateSchema(BaseModel):
    """权益核销创建模型"""

    entitlement_id: int = Field(..., description="权益ID")
    quantity: int = Field(default=1, ge=1, le=999, description="核销数量")
    occurred_at: datetime | None = Field(default=None, description="发生时间")
    title: str | None = Field(default=None, max_length=128, description="核销标题")
    content: str | None = Field(default=None, max_length=5000, description="核销内容")
    candidate_person_id: int | None = Field(default=None, description="候选Person ID")
    overuse_reason: str | None = Field(default=None, max_length=1000, description="超额原因")
    customer_confirm_status: str | None = Field(default=None, max_length=32, description="客户确认状态")
    customer_signature_url: str | None = Field(default=None, max_length=1000, description="客户签字图片")
    customer_signed_at: datetime | None = Field(default=None, description="客户签字时间")


class UsageVoidSchema(BaseModel):
    """权益核销作废模型"""

    reason: str = Field(..., min_length=1, max_length=1000, description="作废/回滚原因")


class CloseApplySchema(BaseModel):
    """关单申请模型"""

    reason: str = Field(..., min_length=1, max_length=2000, description="关单原因")


class CloseReviewSchema(BaseModel):
    """关单审核模型"""

    approved: bool = Field(..., description="是否通过")
    review_remark: str | None = Field(default=None, max_length=2000, description="审核备注")


class ReopenSchema(BaseModel):
    """服务重开模型"""

    reason: str = Field(..., min_length=1, max_length=2000, description="重开原因")


class VipOutSchema(BaseModel):
    """VIP服务响应"""

    id: int
    case_id: int | None = None
    brand_id: int
    vip_id: int | None = None
    person_id: int
    customer_id: int
    contract_id: int
    store_id: int
    service_owner_user_id: int | None = None
    owner_matchmaker_id: int | None = None
    case_status: str | None = None
    pool_type: str | None = None
    close_review_status: str | None = None
    close_requested_at: DateTimeStr | None = None
    close_requested_by: int | None = None
    close_requested_by_name: str | None = None
    close_reason: str | None = None
    close_reviewed_at: DateTimeStr | None = None
    close_reviewed_by: int | None = None
    close_reviewed_by_name: str | None = None
    close_review_remark: str | None = None
    vip_level: str
    vip_status: str
    started_at: DateTimeStr
    ended_at: DateTimeStr | None = None
    assigned_at: DateTimeStr | None = None
    assigned_by: int | None = None
    source_receipt_id: int | None = None
    person_display_no: str | None = None
    person_name: str | None = None
    person_gender: str | None = None
    person_age: int | None = None
    person_mobile: str | None = None
    contract_no: str | None = None
    contract_name: str | None = None
    contract_amount: Decimal = Decimal("0.00")
    received_amount: Decimal = Decimal("0.00")
    pending_amount: Decimal = Decimal("0.00")
    payment_status: str = "unpaid"
    contract_effective_at: DateTimeStr | None = None
    owner_user_id: int | None = None
    owner_user_name: str | None = None
    service_owner_user_name: str | None = None
    assigned_by_name: str | None = None
    store_name: str | None = None
    waiting_hours: int | None = None
    remaining_days: int | None = None
    entitlement_summary: dict[str, dict[str, int]] = Field(default_factory=dict)
    deep_interview_count: int = 0
    usage_count: int = 0


class VipLogOutSchema(BaseModel):
    """VIP服务日志响应"""

    id: int
    operation_type: str
    operator_user_id: int | None = None
    operator_user_name: str | None = None
    before_owner_user_id: int | None = None
    before_owner_user_name: str | None = None
    after_owner_user_id: int | None = None
    after_owner_user_name: str | None = None
    before_status: str | None = None
    after_status: str | None = None
    remark: str | None = None
    created_time: DateTimeStr


class VipContractItemOutSchema(BaseModel):
    """VIP关联合同产品快照响应"""

    id: int
    product_id: int | None = None
    product_name_snapshot: str
    price_snapshot: Decimal = Decimal("0.00")
    service_days_snapshot: int = 0
    recommendation_quota_snapshot: int = 0
    meeting_quota_snapshot: int = 0
    course_quota_snapshot: int = 0
    supports_online_meeting_snapshot: bool = False


class EntitlementOutSchema(BaseModel):
    """服务权益响应"""

    id: int
    entitlement_type: str
    total_quota: int
    used_quota: int
    remaining_quota: int
    unit: str
    allow_overuse: bool
    entitlement_status: str
    source_contract_item_id: int | None = None


class UsageOutSchema(BaseModel):
    """权益核销响应"""

    id: int
    entitlement_id: int
    usage_type: str
    quantity: int
    usage_status: str
    occurred_at: DateTimeStr
    title: str | None = None
    content: str | None = None
    candidate_person_id: int | None = None
    candidate_name: str | None = None
    is_overuse: bool = False
    overuse_reason: str | None = None
    void_reason: str | None = None
    customer_confirm_status: str | None = None
    customer_signature_url: str | None = None
    customer_signed_at: DateTimeStr | None = None
    created_by_name: str | None = None


class DeepInterviewOutSchema(BaseModel):
    """服务深访响应"""

    id: int
    interview_type: str
    interviewed_at: DateTimeStr
    content: str
    keywords: list[str] = Field(default_factory=list)
    summary: str | None = None
    interview_status: str
    matchmaker_id: int | None = None
    matchmaker_name: str | None = None
    created_by_name: str | None = None


class VipDetailOutSchema(VipOutSchema):
    """VIP服务详情响应"""

    logs: list[VipLogOutSchema] = Field(default_factory=list)
    contract_status: str | None = None
    original_amount: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    discount_rate: Decimal = Decimal("0.0000")
    discount_reason: str | None = None
    signer_name: str | None = None
    signed_at: DateTimeStr | None = None
    effective_at: DateTimeStr | None = None
    start_date: date | None = None
    end_date: date | None = None
    contract_items: list[VipContractItemOutSchema] = Field(default_factory=list)
    entitlements: list[EntitlementOutSchema] = Field(default_factory=list)
    usages: list[UsageOutSchema] = Field(default_factory=list)
    deep_interviews: list[DeepInterviewOutSchema] = Field(default_factory=list)


class ServiceCustomerProfileOutSchema(BaseModel):
    """服务上下文客户资料响应"""

    person_id: int
    person_brand_id: int | None = None
    customer_id: int | None = None
    customer_brand_id: int | None = None
    lead_id: int | None = None
    store_id: int | None = None
    store_name: str | None = None
    owner_user_id: int | None = None
    owner_user_name: str | None = None
    service_owner_user_id: int | None = None
    service_owner_user_name: str | None = None
    display_no: str | None = None
    name: str | None = None
    gender: str | None = None
    mobile: str | None = None
    wechat: str | None = None
    id_card_no: str | None = None
    birth_date: date | None = None
    age: int | None = None
    constellation: str | None = None
    zodiac: str | None = None
    height_cm: int | None = None
    weight_kg: int | None = None
    education: str | None = None
    annual_income: str | None = None
    marital_status: str | None = None
    ethnicity: str | None = None
    occupation: str | None = None
    occupation_code: str | None = None
    unit_type: str | None = None
    graduated_school: str | None = None
    major: str | None = None
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
    photo_urls: list[str] = Field(default_factory=list)
    profile_intro: str | None = None
    certification_level: str | None = None
    certification_summary: dict[str, Any] | None = None
    partner_preference: dict[str, Any] | None = None
    current_stage: str | None = None
    max_stage: str | None = None
    latest_follow_at: DateTimeStr | None = None
    next_follow_at: DateTimeStr | None = None
    ended_at: DateTimeStr | None = None
    end_reason: str | None = None
    returned_lead_id: int | None = None
    converted_vip_at: DateTimeStr | None = None
    created_time: DateTimeStr | None = None
    updated_time: DateTimeStr | None = None


class ServiceCertificationOutSchema(BaseModel):
    """服务上下文认证资料响应"""

    id: int
    item_code: str
    item_name: str
    material_type: str
    file_name: str | None = None
    file_path: str | None = None
    file_url: str
    payload: dict[str, Any] | None = None
    collected_by: int | None = None
    collected_by_name: str | None = None
    created_time: DateTimeStr | None = None


class ServiceTimelineOutSchema(BaseModel):
    """统一过程时间轴响应"""

    id: str
    source_type: str
    record_type: str
    occurred_at: DateTimeStr
    title: str
    content: str | None = None
    operator_user_id: int | None = None
    operator_user_name: str | None = None
    related_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ServiceCustomerProcessCreateSchema(BaseModel):
    """服务上下文新增客户过程记录"""

    record_type: str = Field(..., min_length=1, max_length=32, description="记录类型")
    occurred_at: datetime | None = Field(default=None, description="发生时间")
    method: str | None = Field(default=None, max_length=32, description="方式")
    result: str | None = Field(default=None, max_length=32, description="结果")
    content: str = Field(..., min_length=1, max_length=20000, description="内容")
    next_follow_at: datetime | None = Field(default=None, description="下次跟进时间")
    scheduled_at: datetime | None = Field(default=None, description="预约/计划时间")
    appointment_slot: str | None = Field(default=None, max_length=32, description="预约时段")
    visit_purpose: str | None = Field(default=None, max_length=32, description="到访目的")
    promised_gift: str | None = Field(default=None, max_length=255, description="承诺礼品")
    need_summary: str | None = Field(default=None, max_length=5000, description="需求摘要")
    intention_level: str | None = Field(default=None, max_length=32, description="意向等级")
    next_action: str | None = Field(default=None, max_length=255, description="下一步动作")
    enter_signing: bool | None = Field(default=None, description="是否进入签约推进")


class ServiceLifecycleOutSchema(BaseModel):
    """统一生命周期响应"""

    id: str
    stage_group: str
    operation_type: str
    occurred_at: DateTimeStr
    title: str
    remark: str | None = None
    operator_user_id: int | None = None
    operator_user_name: str | None = None
    related_id: int | None = None
    change_detail: dict[str, Any] | None = None


class ServiceContractOutSchema(BaseModel):
    """服务上下文合同收款响应"""

    id: int
    contract_no: str
    contract_name: str
    contract_status: str
    vip_level: str
    store_id: int
    owner_user_id: int
    owner_user_name: str | None = None
    original_amount: Decimal = Decimal("0.00")
    contract_amount: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    discount_rate: Decimal = Decimal("0.0000")
    discount_reason: str | None = None
    signer_name: str | None = None
    signed_at: DateTimeStr | None = None
    review_submitted_at: DateTimeStr | None = None
    reviewed_at: DateTimeStr | None = None
    review_remark: str | None = None
    effective_at: DateTimeStr | None = None
    start_date: date | None = None
    end_date: date | None = None
    validity_period: str | None = None
    expire_remind_days: int | None = None
    remark: str | None = None
    received_amount: Decimal = Decimal("0.00")
    pending_amount: Decimal = Decimal("0.00")
    payment_status: str = "unpaid"
    items: list[dict[str, Any]] = Field(default_factory=list)
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    receipts: list[dict[str, Any]] = Field(default_factory=list)


class ServiceWorkSummaryOutSchema(BaseModel):
    """服务工作小计响应"""

    entitlement_summary: dict[str, dict[str, int]] = Field(default_factory=dict)
    deep_interview_count: int = 0
    active_usage_count: int = 0
    process_record_count: int = 0
    contract_count: int = 0
    contract_amount: Decimal = Decimal("0.00")
    received_amount: Decimal = Decimal("0.00")
    pending_amount: Decimal = Decimal("0.00")
    remaining_days: int | None = None


class MatchmakerOptionSchema(BaseModel):
    """服务红娘候选响应"""

    id: int
    name: str
    mobile: str | None = None
    dept_id: int | None = None


class VipQueryParam:
    """VIP服务查询参数"""

    def __init__(
        self,
        keyword: str | None = Query(None, description="关键词"),
        vip_status: str | None = Query(None, description="VIP状态"),
        vip_level: str | None = Query(None, description="VIP等级"),
        store_id: int | None = Query(None, description="门店ID"),
        service_owner_user_id: int | None = Query(None, description="服务红娘ID"),
        owner_user_id: int | None = Query(None, description="成交销售ID"),
        effective_start: date | None = Query(None, description="合同生效开始日期"),
        effective_end: date | None = Query(None, description="合同生效结束日期"),
        ended_start: date | None = Query(None, description="服务结束开始日期"),
        ended_end: date | None = Query(None, description="服务结束结束日期"),
        mine: bool | None = Query(None, description="是否我的VIP"),
        close_review_status: str | None = Query(None, description="关单审核状态"),
    ) -> None:
        self.keyword = keyword.strip() if keyword else None
        self.vip_status = vip_status
        self.vip_level = vip_level
        self.store_id = store_id
        self.service_owner_user_id = service_owner_user_id
        self.owner_user_id = owner_user_id
        self.effective_start = effective_start
        self.effective_end = effective_end
        self.ended_start = ended_start
        self.ended_end = ended_end
        self.mine = mine
        self.close_review_status = close_review_status


class CandidateAddExistingSchema(BaseModel):
    """加入已有Person到备选库"""

    person_id: int = Field(..., description="Person ID")
    matchmaker_id: int | None = Field(default=None, description="归属服务红娘ID")
    private_tags: list[str] = Field(default_factory=list, description="私有标签")
    private_remark: str | None = Field(default=None, max_length=2000, description="私有备注")


class CandidateCreateSchema(BaseModel):
    """手动新增备选资源"""

    name: str = Field(..., min_length=1, max_length=64, description="姓名")
    gender: str = Field(..., min_length=1, max_length=8, description="性别")
    primary_mobile: str = Field(..., min_length=3, max_length=20, description="手机号")
    wechat: str | None = Field(default=None, max_length=64, description="微信号")
    birth_date: date | None = Field(default=None, description="出生日期")
    height_cm: int | None = Field(default=None, ge=80, le=260, description="身高")
    weight_kg: int | None = Field(default=None, ge=30, le=250, description="体重kg")
    ethnicity: str | None = Field(default=None, max_length=32, description="民族")
    occupation: str | None = Field(default=None, max_length=64, description="职业补充")
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
    partner_preference: PartnerPreferencePayload | None = Field(default=None, description="择偶要求")
    certification_materials: list[CustomerCertificationMaterialSaveSchema] = Field(default_factory=list, description="认证资料存档")
    matchmaker_id: int | None = Field(default=None, description="归属服务红娘ID")
    private_tags: list[str] = Field(default_factory=list, description="私有标签")
    private_remark: str | None = Field(default=None, max_length=2000, description="私有备注")


class CandidateOutSchema(BaseModel):
    """备选库响应"""

    id: int
    candidate_id: int
    person_id: int
    matchmaker_id: int
    matchmaker_name: str | None = None
    store_id: int | None = None
    store_name: str | None = None
    source_type: str
    name: str
    gender: str
    mobile: str | None = None
    wechat: str | None = None
    birth_date: date | None = None
    age: int | None = None
    height_cm: int | None = None
    residence: str | None = None
    education: str | None = None
    annual_income: str | None = None
    marital_status: str | None = None
    private_tags: list[str] = Field(default_factory=list)
    private_remark: str | None = None
    join_request_id: int | None = None
    approved_by: int | None = None
    approved_at: DateTimeStr | None = None
    contact_unmasked_after_approval: bool = False
    created_time: DateTimeStr


class CandidateDiscoverSchema(BaseModel):
    """候选发现联合搜索模型"""

    scope: str = Field(default="store", description="搜索范围: store/brand")
    page_no: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")
    keyword: str | None = Field(default=None, max_length=64, description="关键词")
    person_id: int | None = Field(default=None, description="Person ID")
    display_no: str | None = Field(default=None, max_length=32, description="展示编号")
    mobile: str | None = Field(default=None, max_length=20, description="手机号")
    name: str | None = Field(default=None, max_length=64, description="姓名")
    matchmaker_id: int | None = Field(default=None, description="目标红娘ID")
    gender: str | None = Field(default=None, max_length=8, description="性别")
    age_min: int | None = Field(default=None, ge=18, le=120, description="最小年龄")
    age_max: int | None = Field(default=None, ge=18, le=120, description="最大年龄")
    height_min: int | None = Field(default=None, ge=80, le=260, description="最小身高")
    height_max: int | None = Field(default=None, ge=80, le=260, description="最大身高")
    weight_min: int | None = Field(default=None, ge=20, le=300, description="最小体重")
    weight_max: int | None = Field(default=None, ge=20, le=300, description="最大体重")
    education: str | None = None
    annual_income: str | None = None
    marital_status: str | None = None
    ethnicity: str | None = None
    occupation_code: str | None = None
    unit_type: str | None = None
    residence: str | None = None
    hometown: str | None = None
    house_status: str | None = None
    car_status: str | None = None
    accept_long_distance_self: bool | None = None
    accept_flash_marriage: bool | None = None
    willing_relocate: bool | None = None
    marriage_plan: str | None = None
    has_photo: bool | None = None
    certification_level: str | None = None
    pref_age_min: int | None = Field(default=None, ge=18, le=120)
    pref_age_max: int | None = Field(default=None, ge=18, le=120)
    pref_height_min: int | None = Field(default=None, ge=80, le=260)
    pref_height_max: int | None = Field(default=None, ge=80, le=260)
    pref_weight_min: int | None = Field(default=None, ge=20, le=300)
    pref_weight_max: int | None = Field(default=None, ge=20, le=300)
    preferred_residence_region_codes: list[str] = Field(default_factory=list)
    preferred_hometown_region_codes: list[str] = Field(default_factory=list)
    preferred_education_codes: list[str] = Field(default_factory=list)
    preferred_marital_status_codes: list[str] = Field(default_factory=list)
    preferred_annual_income_codes: list[str] = Field(default_factory=list)
    preferred_house_status_codes: list[str] = Field(default_factory=list)
    preferred_car_status_codes: list[str] = Field(default_factory=list)
    pref_accept_long_distance: bool | None = None
    pref_accept_divorced: bool | None = None
    pref_accept_children: bool | None = None
    children_requirement: str | None = None
    preferred_occupation_text: str | None = None
    preference_text: str | None = None
    hard_reject_items: list[str] = Field(default_factory=list)
    soft_preference_items: list[str] = Field(default_factory=list)
    preferred_personality_tags: list[str] = Field(default_factory=list)
    preferred_lifestyle_tags: list[str] = Field(default_factory=list)
    preferred_relationship_tags: list[str] = Field(default_factory=list)
    strictness_level: str | None = None
    must_match_fields: list[str] = Field(default_factory=list)
    preferred_match_fields: list[str] = Field(default_factory=list)


class CandidateDiscoverOutSchema(BaseModel):
    """候选发现脱敏响应"""

    id: int
    display_no: str | None = None
    name: str
    gender: str
    mobile: str | None = None
    wechat: str | None = None
    store_id: int | None = None
    store_name: str | None = None
    age: int | None = None
    height_cm: int | None = None
    weight_kg: int | None = None
    residence: str | None = None
    hometown: str | None = None
    education: str | None = None
    annual_income: str | None = None
    marital_status: str | None = None
    has_photo: bool = False
    certification_level: str | None = None
    already_in_backup: bool = False
    pending_request: bool = False


class CandidateJoinRequestCreateSchema(BaseModel):
    """提交备选库加入申请"""

    person_id: int = Field(..., description="Person ID")
    scope: str = Field(default="store", description="申请范围: store/brand")
    matchmaker_id: int | None = Field(default=None, description="归属服务红娘ID")
    private_tags: list[str] = Field(default_factory=list, description="私有标签")
    private_remark: str | None = Field(default=None, max_length=2000, description="私有备注")
    request_reason: str | None = Field(default=None, max_length=2000, description="申请理由")


class CandidateJoinRequestReviewSchema(BaseModel):
    """审核备选库加入申请"""

    review_status: str = Field(..., description="审核结果: approved/rejected")
    review_remark: str | None = Field(default=None, max_length=2000, description="审核备注")


class CandidateRuleSchema(BaseModel):
    """备选库规则"""

    store_join_requires_review: bool = Field(default=True, description="本门店加入备选库是否需要管理员审批")
    brand_join_requires_review: bool = Field(default=True, description="品牌范围加入备选库是否需要管理员审批，固定为true")


class CandidateRuleUpdateSchema(BaseModel):
    """备选库规则更新"""

    store_join_requires_review: bool = Field(..., description="本门店加入备选库是否需要管理员审批")


class CandidateJoinRequestOutSchema(BaseModel):
    """备选库加入申请响应"""

    id: int
    person_id: int
    person_name: str | None = None
    person_display_no: str | None = None
    person_gender: str | None = None
    person_mobile: str | None = None
    person_wechat: str | None = None
    person_store_id: int | None = None
    person_store_name: str | None = None
    request_scope: str
    request_matchmaker_id: int
    request_matchmaker_name: str | None = None
    request_store_id: int | None = None
    request_store_name: str | None = None
    private_tags_snapshot: list[str] = Field(default_factory=list)
    private_remark_snapshot: str | None = None
    request_reason: str | None = None
    review_status: str
    reviewer_id: int | None = None
    reviewer_name: str | None = None
    reviewed_at: DateTimeStr | None = None
    review_remark: str | None = None
    approved_backup_item_id: int | None = None
    created_time: DateTimeStr


class CandidateJoinRequestQueryParam:  # noqa: B903
    """备选库加入申请查询参数"""

    def __init__(
        self,
        review_status: str | None = Query(None, description="审核状态"),
        scope: str | None = Query(None, description="申请范围"),
        mine: bool | None = Query(None, description="是否我的申请"),
    ) -> None:
        self.review_status = review_status
        self.scope = scope
        self.mine = mine


class CandidateQueryParam:
    """备选库查询参数"""

    def __init__(
        self,
        keyword: str | None = Query(None, description="姓名/手机号/编号"),
        source_type: str | None = Query(None, description="来源类型"),
        mine: bool | None = Query(None, description="是否我的备选"),
    ) -> None:
        self.keyword = keyword.strip() if keyword else None
        self.source_type = source_type
        self.mine = mine


class PersonSearchOutSchema(BaseModel):
    """Person搜索响应"""

    id: int
    display_no: str | None = None
    name: str
    gender: str
    mobile: str | None = None
    store_id: int | None = None
    age: int | None = None
