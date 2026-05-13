from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseSchema
from app.core.validator import DateTimeStr


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


class MpUserQueryParam:
    """小程序注册用户查询参数。"""

    def __init__(
        self,
        keyword: str | None = Query(None, description="昵称/手机号/姓名/微信号"),
        is_registered: bool | None = Query(None, description="是否已完成注册"),
    ) -> None:
        self.keyword = keyword.strip() if keyword else None
        self.is_registered = is_registered
