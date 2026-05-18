import re
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MOBILE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
GENDER_VALUES = {"0", "1", "2"}


class MpLoginSchema(BaseModel):
    """小程序登录参数。"""

    code: str = Field(..., min_length=1, max_length=256, description="微信登录code")


class MpRegisterSchema(BaseModel):
    """小程序注册参数。"""

    login_code: str = Field(..., min_length=1, max_length=256, description="微信登录code")
    phone_code: str = Field(..., min_length=1, max_length=256, description="微信手机号授权code")
    nickname: str = Field(..., min_length=1, max_length=64, description="微信昵称")
    avatar_url: str | None = Field(default=None, max_length=500, description="系统头像/主展示照")
    agreement_accepted: bool = Field(..., description="是否同意注册协议")
    agreement_version: str = Field(default="1.0", min_length=1, max_length=32, description="协议版本")
    agreement_title: str = Field(default="觅AI用户注册协议", min_length=1, max_length=128, description="协议标题")
    name: str = Field(..., min_length=1, max_length=64, description="姓名")
    gender: str = Field(..., description="性别")
    wechat: str = Field(..., min_length=1, max_length=64, description="微信号")
    birth_date: date = Field(..., description="出生日期")
    height_cm: int = Field(..., ge=80, le=260, description="身高cm")
    ethnicity: str = Field(..., min_length=1, max_length=32, description="民族")
    occupation: str = Field(..., min_length=1, max_length=64, description="职业")
    annual_income: str = Field(..., min_length=1, max_length=32, description="年收入")
    marital_status: str = Field(..., min_length=1, max_length=32, description="婚况")
    education: str = Field(..., min_length=1, max_length=32, description="学历")
    hometown: str = Field(..., min_length=1, max_length=128, description="籍贯")
    residence: str = Field(..., min_length=1, max_length=128, description="常驻地")
    house_status: str = Field(..., min_length=1, max_length=32, description="房产信息")
    car_status: str = Field(..., min_length=1, max_length=32, description="购车信息")
    photo_urls: list[str] = Field(..., min_length=1, description="照片相册")
    source_id: str | None = Field(default=None, max_length=128, description="来源对象ID")
    source_user_id: int | None = Field(default=None, description="分享来源用户ID")
    payload: dict | None = Field(default=None, description="来源扩展参数")

    @field_validator("name", "nickname", "wechat", "ethnicity", "occupation", "annual_income", "marital_status", "education", "hometown", "residence", "house_status", "car_status")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("必填文本不能为空")
        return value

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value: str) -> str:
        if value not in GENDER_VALUES:
            raise ValueError("性别必须为0、1或2")
        return value

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("出生日期不能晚于今天")
        return value

    @field_validator("photo_urls")
    @classmethod
    def validate_photo_urls(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if not cleaned:
            raise ValueError("照片相册至少需要1张")
        return cleaned

    @model_validator(mode="after")
    def validate_register_payload(self):
        if not self.agreement_accepted:
            raise ValueError("必须同意注册协议")
        if not self.avatar_url and self.photo_urls:
            self.avatar_url = self.photo_urls[0]
        return self


class MpPersonOutSchema(BaseModel):
    """小程序人员摘要。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    display_no: str | None = None
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
    profile_intro: str | None = None
    certification_level: str = "none"
    certification_summary: dict | None = None


class MpUserOutSchema(BaseModel):
    """小程序用户摘要。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    person_id: int | None = None
    mobile: str | None = None
    nickname: str | None = None
    avatar_url: str | None = None
    is_invisible: bool = False
    allow_user_wall: bool = True


class MpAuthOutSchema(BaseModel):
    """小程序登录/注册响应。"""

    token: str
    token_type: str = "Bearer"
    expires_in: int
    is_registered: bool
    user: MpUserOutSchema
    person: MpPersonOutSchema | None = None
    lead_id: int | None = None
