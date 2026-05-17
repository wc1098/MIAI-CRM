from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.base_schema import BaseSchema, UserBySchema
from app.core.validator import DateTimeStr

PreferenceSource = Literal["miniapp", "admin", "matchmaker", "deep_interview", "import"]
StrictnessLevel = Literal["loose", "normal", "strict"]


class PartnerPreferencePayload(BaseModel):
    """择偶要求保存模型。"""

    age_min: int | None = Field(default=None, ge=18, le=100, description="期望最小年龄")
    age_max: int | None = Field(default=None, ge=18, le=100, description="期望最大年龄")
    height_min_cm: int | None = Field(default=None, ge=80, le=260, description="期望最小身高cm")
    height_max_cm: int | None = Field(default=None, ge=80, le=260, description="期望最大身高cm")
    weight_min_kg: int | None = Field(default=None, ge=30, le=250, description="期望最小体重kg")
    weight_max_kg: int | None = Field(default=None, ge=30, le=250, description="期望最大体重kg")
    preferred_residence_region_codes: list[str] = Field(default_factory=list, description="期望常驻地范围")
    preferred_hometown_region_codes: list[str] = Field(default_factory=list, description="期望籍贯范围")
    preferred_education_codes: list[str] = Field(default_factory=list, description="期望学历")
    preferred_marital_status_codes: list[str] = Field(default_factory=list, description="期望婚况")
    preferred_annual_income_codes: list[str] = Field(default_factory=list, description="期望年收入")
    preferred_house_status_codes: list[str] = Field(default_factory=list, description="期望房产")
    preferred_car_status_codes: list[str] = Field(default_factory=list, description="期望车辆")
    accept_long_distance: bool | None = Field(default=None, description="是否接受异地")
    accept_divorced: bool | None = Field(default=None, description="是否接受离异")
    accept_children: bool | None = Field(default=None, description="是否接受有子女")
    children_requirement: str | None = Field(default=None, max_length=255, description="子女要求说明")
    preferred_personality_tags: list[str] = Field(default_factory=list, description="性格偏好")
    preferred_lifestyle_tags: list[str] = Field(default_factory=list, description="生活方式偏好")
    preferred_relationship_tags: list[str] = Field(default_factory=list, description="关系期待偏好")
    hard_reject_items: list[str] = Field(default_factory=list, description="硬性拒绝项")
    soft_preference_items: list[str] = Field(default_factory=list, description="软性偏好")
    preferred_occupation_text: str | None = Field(default=None, max_length=255, description="职业偏好文本")
    preference_text: str | None = Field(default=None, max_length=2000, description="自由择偶说明")
    strictness_level: StrictnessLevel = Field(default="normal", description="严格程度")
    must_match_fields: list[str] = Field(default_factory=list, description="必须匹配字段")
    preferred_match_fields: list[str] = Field(default_factory=list, description="优先匹配字段")
    profile_summary: str | None = Field(default=None, max_length=2000, description="系统摘要")

    @field_validator(
        "preferred_residence_region_codes",
        "preferred_hometown_region_codes",
        "preferred_education_codes",
        "preferred_marital_status_codes",
        "preferred_annual_income_codes",
        "preferred_house_status_codes",
        "preferred_car_status_codes",
        "preferred_personality_tags",
        "preferred_lifestyle_tags",
        "preferred_relationship_tags",
        "hard_reject_items",
        "soft_preference_items",
        "must_match_fields",
        "preferred_match_fields",
        mode="before",
    )
    @classmethod
    def normalize_list(cls, value: Any) -> list[str]:
        if value in (None, "", "不限"):
            return []
        if not isinstance(value, list):
            return []
        data: list[str] = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text and text not in data and text != "不限":
                data.append(text)
        return data

    @field_validator("children_requirement", "preferred_occupation_text", "preference_text", "profile_summary")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def validate_ranges(self) -> "PartnerPreferencePayload":
        ranges = [
            ("age_min", "age_max", "年龄"),
            ("height_min_cm", "height_max_cm", "身高"),
            ("weight_min_kg", "weight_max_kg", "体重"),
        ]
        for min_field, max_field, label in ranges:
            min_value = getattr(self, min_field)
            max_value = getattr(self, max_field)
            if min_value is not None and max_value is not None and min_value > max_value:
                raise ValueError(f"{label}范围不正确")
        return self


class PartnerPreferenceSaveSchema(PartnerPreferencePayload):
    """择偶要求完整保存模型。"""

    source_type: PreferenceSource = Field(default="admin", description="来源类型")
    source_id: str | None = Field(default=None, max_length=128, description="来源ID")
    force_final: bool = Field(default=False, description="是否按服务最终版保存")


class PartnerPreferenceOutSchema(BaseSchema, UserBySchema, PartnerPreferencePayload):
    """择偶要求响应模型。"""

    model_config = ConfigDict(from_attributes=True)

    brand_id: int = Field(default=1, description="品牌ID")
    person_id: int = Field(description="人员ID")
    source_type: str = Field(default="admin", description="来源类型")
    source_id: str | None = Field(default=None, description="来源ID")
    priority: int = Field(default=20, description="优先级")
    is_effective: bool = Field(default=True, description="是否当前有效")
    is_final: bool = Field(default=False, description="是否最终版")
    vector_dirty: bool = Field(default=True, description="向量是否待更新")
    last_vectorized_at: DateTimeStr | None = Field(default=None, description="最近向量化时间")
    version_no: int = Field(default=1, description="版本号")


class PartnerPreferenceVersionOutSchema(BaseSchema, UserBySchema):
    """择偶要求历史版本响应。"""

    model_config = ConfigDict(from_attributes=True)

    brand_id: int = Field(default=1, description="品牌ID")
    person_id: int = Field(description="人员ID")
    preference_id: int | None = Field(default=None, description="当前择偶要求ID")
    version_no: int = Field(description="版本号")
    source_type: str = Field(description="来源类型")
    source_id: str | None = Field(default=None, description="来源ID")
    priority: int = Field(default=20, description="优先级")
    is_effective: bool = Field(default=False, description="是否成为当前有效")
    is_final: bool = Field(default=False, description="是否最终版")
    snapshot: dict[str, Any] = Field(default_factory=dict, description="择偶要求快照")


class PartnerPreferenceAdminUpdateSchema(BaseModel):
    """后台按人员保存择偶要求。"""

    preference: PartnerPreferencePayload = Field(default_factory=PartnerPreferencePayload, description="择偶要求")
    source_type: PreferenceSource = Field(default="admin", description="来源类型")
    source_id: str | None = Field(default=None, max_length=128, description="来源ID")
    force_final: bool = Field(default=False, description="是否按服务最终版保存")


class PartnerPreferenceMpUpdateSchema(PartnerPreferencePayload):
    """小程序保存我的择偶要求。"""

    pass


class PartnerPreferenceBundleSchema(BaseModel):
    """择偶要求详情包。"""

    current: PartnerPreferenceOutSchema | None = None
    versions: list[PartnerPreferenceVersionOutSchema] = Field(default_factory=list)
