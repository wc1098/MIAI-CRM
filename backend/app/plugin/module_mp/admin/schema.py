from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseSchema
from app.core.validator import DateTimeStr
from app.plugin.module_crm.preference.schema import PartnerPreferenceOutSchema


class MpPersonBriefSchema(BaseModel):
    """小程序注册关联的CRM人员摘要。"""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = Field(default=None, description="人员ID")
    name: str | None = Field(default=None, description="姓名")
    gender: str | None = Field(default=None, description="性别")
    primary_mobile: str | None = Field(default=None, description="手机号")
    wechat: str | None = Field(default=None, description="微信号")
    birth_date: str | None = Field(default=None, description="出生日期")
    height_cm: int | None = Field(default=None, description="身高cm")
    ethnicity: str | None = Field(default=None, description="民族")
    occupation: str | None = Field(default=None, description="职业")
    annual_income: str | None = Field(default=None, description="年收入")
    marital_status: str | None = Field(default=None, description="婚况")
    education: str | None = Field(default=None, description="学历")
    hometown: str | None = Field(default=None, description="籍贯")
    residence: str | None = Field(default=None, description="常驻地")
    house_status: str | None = Field(default=None, description="房产信息")
    car_status: str | None = Field(default=None, description="购车信息")
    photo_urls: list[str] = Field(default_factory=list, description="照片相册")


class MpUserOutSchema(BaseSchema):
    """小程序用户后台响应模型。"""

    model_config = ConfigDict(from_attributes=True)

    brand_id: int = Field(default=1, description="品牌ID")
    person_id: int | None = Field(default=None, description="关联人员ID")
    openid: str | None = Field(default=None, description="openid")
    unionid: str | None = Field(default=None, description="unionid")
    mobile: str | None = Field(default=None, description="微信手机号")
    nickname: str | None = Field(default=None, description="微信昵称")
    avatar_url: str | None = Field(default=None, description="头像")
    is_invisible: bool = Field(default=False, description="是否隐身")
    allow_user_wall: bool = Field(default=True, description="是否允许上墙")
    registered_at: DateTimeStr | None = Field(default=None, description="注册时间")
    last_login_at: DateTimeStr | None = Field(default=None, description="最近登录时间")
    is_registered: bool = Field(default=False, description="是否已完成注册")
    lead_id: int | None = Field(default=None, description="当前有效线索ID")
    source_event_count: int = Field(default=0, description="来源事件数")
    person: MpPersonBriefSchema | None = Field(default=None, description="人员摘要")
    ai_profile: dict | None = Field(default=None, description="觅AI印象摘要")
    partner_preference: PartnerPreferenceOutSchema | None = Field(default=None, description="择偶要求")
    interaction_stats: dict | None = Field(default=None, description="互动统计")
    recent_actions: list[dict] = Field(default_factory=list, description="最近行为")
    coupon_summary: dict | None = Field(default=None, description="免费券摘要")


class MpUserQueryParam:
    """小程序注册用户查询参数。"""

    def __init__(
        self,
        keyword: str | None = Query(None, description="昵称/手机号/姓名/微信号"),
        is_registered: bool | None = Query(None, description="是否已完成注册"),
    ) -> None:
        self.keyword = keyword.strip() if keyword else None
        self.is_registered = is_registered


class MpOperationSettingsSchema(BaseModel):
    """小程序运营设置。"""

    plaza_show_pending_users: bool = Field(default=False, description="广场是否展示待绑定小程序用户")
    contact_price: str = Field(default="19.90", description="联系方式解锁价格")
    allow_coupon: bool = Field(default=True, description="是否允许免费券解锁")
    allow_paid_boost: bool = Field(default=True, description="是否允许付费补足")
    allow_task_free: bool = Field(default=True, description="是否允许任务免费解锁")
    daily_unlock_limit: int = Field(default=5, ge=0, description="每日解锁上限")
    default_store_id: int | None = Field(default=None, description="默认收款门店ID")
    heartbeat_initial_min: int = Field(default=35, description="初始心动值下限")
    heartbeat_initial_max: int = Field(default=55, description="初始心动值上限")
    heartbeat_view_score: int = Field(default=1, description="有效浏览加分")
    heartbeat_like_score: int = Field(default=8, description="喜欢加分")
    heartbeat_favorite_score: int = Field(default=5, description="收藏加分")
    heartbeat_profile_score: int = Field(default=0, description="资料完整加分")
    heartbeat_unlock_score: int = Field(default=100, description="心动值解锁阈值")
    coupon_enabled: bool = Field(default=True, description="是否启用免费券")
    coupon_name: str = Field(default="联系方式解锁券", description="免费券名称")
    coupon_valid_days: int = Field(default=7, description="免费券有效天数")
    coupon_cycle_days: int = Field(default=2, ge=1, description="免费券连续任务周期")
    coupon_hold_limit: int = Field(default=1, ge=1, description="免费券持有上限")
    coupon_description: str = Field(default="可免费解锁一次心仪用户手机号", description="免费券说明")
    copy_progress: str = Field(default="完成互动任务提升心动值，达到目标后即可查看手机号。", description="进度页文案")
    copy_final: str = Field(default="解锁后可查看对方手机号，本次解锁后可重复查看，不重复收费。", description="最后一步文案")
    copy_pay: str = Field(default="付费补足会直接加满当前心动值并解锁手机号。", description="支付说明文案")
    copy_contact: str = Field(default="请真诚沟通，尊重对方意愿；若对方明确拒绝，请停止打扰。", description="手机号展示提示")
    copy_risk: str = Field(default="今日解锁次数已用完，请明天再试。", description="风控提示")


class MpActionQueryParam:
    """小程序用户行为查询参数。"""

    def __init__(
        self,
        keyword: str | None = Query(None, description="编号/昵称/手机号/姓名"),
        action_type: str | None = Query(None, description="行为类型"),
    ) -> None:
        self.keyword = keyword.strip() if keyword else None
        self.action_type = action_type.strip() if action_type else None


class MpCouponQueryParam:
    """小程序免费券查询参数。"""

    def __init__(
        self,
        keyword: str | None = Query(None, description="编号/昵称/手机号/姓名"),
        coupon_status: str | None = Query(None, description="券状态"),
    ) -> None:
        self.keyword = keyword.strip() if keyword else None
        self.coupon_status = coupon_status.strip() if coupon_status else None


class MpCouponGrantSchema(BaseModel):
    """发放小程序免费券。"""

    user_id: int = Field(..., description="小程序用户ID")
    quantity: int = Field(default=1, ge=1, le=100, description="发放数量")
    coupon_name: str | None = Field(default=None, max_length=64, description="券名称")
    valid_days: int | None = Field(default=None, ge=1, le=3650, description="有效天数")
    grant_reason: str | None = Field(default=None, max_length=500, description="发放原因")


class MpTaskUpsertSchema(BaseModel):
    task_code: str = Field(..., max_length=64, description="任务编码")
    task_name: str = Field(..., max_length=100, description="任务名称")
    task_type: str = Field(..., max_length=32, description="任务类型")
    task_group: str = Field(default="quick", max_length=32, description="任务分组")
    score: int = Field(default=0, ge=0, le=999, description="加分值")
    is_global: bool = Field(default=False, description="是否全局任务")
    is_target: bool = Field(default=True, description="是否目标任务")
    daily_limit: int = Field(default=1, ge=0, le=999, description="每日限制")
    sort: int = Field(default=0, ge=0, le=9999, description="排序")
    status: str = Field(default="0", description="状态")


class MpQuestionUpsertSchema(BaseModel):
    question: str = Field(..., max_length=255, description="题目")
    options: list[dict] = Field(..., min_length=2, description="选项")
    recommended_answer: str | None = Field(default=None, max_length=64, description="推荐答案")
    match_tags: list[str] | None = Field(default=None, description="匹配标签")
    correct_score: int = Field(default=10, ge=0, le=999, description="答对加分")
    wrong_score: int = Field(default=3, ge=0, le=999, description="答错加分")
    category: str = Field(default="default", max_length=32, description="题目分类")
    sort: int = Field(default=0, ge=0, le=9999, description="排序")
    status: str = Field(default="0", description="状态")


class MpUnlockRecordQueryParam:
    def __init__(
        self,
        keyword: str | None = Query(None, description="编号/昵称/手机号/姓名"),
        unlock_status: str | None = Query(None, description="解锁状态"),
    ) -> None:
        self.keyword = keyword.strip() if keyword else None
        self.unlock_status = unlock_status.strip() if unlock_status else None


class MpUnlockRevokeSchema(BaseModel):
    status: str = Field(..., pattern="^(revoked|blocked)$", description="处理状态")
    reason: str | None = Field(default=None, max_length=500, description="原因")

