from datetime import date

from pydantic import BaseModel, Field, field_validator

GENDER_VALUES = {"0", "1", "2"}


class MpMineProfileUpdateSchema(BaseModel):
    """小程序个人资料更新。"""

    name: str = Field(..., min_length=1, max_length=64)
    gender: str = Field(..., description="性别")
    wechat: str | None = Field(default=None, max_length=64)
    birth_date: date | None = Field(default=None)
    height_cm: int | None = Field(default=None, ge=80, le=260)
    ethnicity: str | None = Field(default=None, max_length=32)
    occupation: str | None = Field(default=None, max_length=64)
    annual_income: str | None = Field(default=None, max_length=32)
    marital_status: str | None = Field(default=None, max_length=32)
    education: str | None = Field(default=None, max_length=32)
    hometown: str | None = Field(default=None, max_length=128)
    residence: str | None = Field(default=None, max_length=128)
    house_status: str | None = Field(default=None, max_length=32)
    car_status: str | None = Field(default=None, max_length=32)
    photo_urls: list[str] = Field(default_factory=list, max_length=12)
    profile_intro: str | None = Field(default=None, max_length=800)

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value: str) -> str:
        if value not in GENDER_VALUES:
            raise ValueError("性别必须为0、1或2")
        return value

    @field_validator(
        "name",
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
        "profile_intro",
        mode="before",
    )
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    @field_validator("photo_urls")
    @classmethod
    def clean_photo_urls(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and item.strip()]

    @field_validator("birth_date", mode="before")
    @classmethod
    def normalize_birth_date(cls, value: date | str | None) -> date | str | None:
        if value == "":
            return None
        return value

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value: date | None) -> date | None:
        if value and value > date.today():
            raise ValueError("出生日期不能晚于今天")
        return value


class MpMinePrivacyUpdateSchema(BaseModel):
    """小程序隐私设置更新。"""

    is_invisible: bool = Field(default=False, description="是否隐身")
