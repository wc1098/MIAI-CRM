from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import PermissionFilterStrategy
from app.core.base_model import ModelMixin, UserMixin


class PersonPartnerPreferenceModel(ModelMixin, UserMixin):
    """人员当前有效择偶要求。"""

    __tablename__ = "person_partner_preference"
    __table_args__: dict[str, str] = {"comment": "人员当前有效择偶要求表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    person_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crm_person.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="人员ID",
    )
    age_min: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="期望最小年龄")
    age_max: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="期望最大年龄")
    height_min_cm: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="期望最小身高cm")
    height_max_cm: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="期望最大身高cm")
    weight_min_kg: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="期望最小体重kg")
    weight_max_kg: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="期望最大体重kg")
    preferred_residence_region_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, comment="期望常驻地范围")
    preferred_hometown_region_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, comment="期望籍贯范围")
    preferred_education_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, comment="期望学历")
    preferred_marital_status_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, comment="期望婚况")
    preferred_annual_income_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, comment="期望年收入")
    preferred_house_status_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, comment="期望房产")
    preferred_car_status_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, comment="期望车辆")
    accept_long_distance: Mapped[bool | None] = mapped_column(Boolean, nullable=True, comment="是否接受异地")
    accept_divorced: Mapped[bool | None] = mapped_column(Boolean, nullable=True, comment="是否接受离异")
    accept_children: Mapped[bool | None] = mapped_column(Boolean, nullable=True, comment="是否接受有子女")
    children_requirement: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="子女要求说明")
    preferred_personality_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, comment="性格偏好")
    preferred_lifestyle_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, comment="生活方式偏好")
    preferred_relationship_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, comment="关系期待偏好")
    hard_reject_items: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, comment="硬性拒绝项")
    soft_preference_items: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, comment="软性偏好")
    preferred_occupation_text: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="职业偏好文本")
    preference_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="择偶要求自由描述")
    strictness_level: Mapped[str] = mapped_column(String(16), nullable=False, default="normal", index=True, comment="严格程度")
    must_match_fields: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, comment="必须匹配字段")
    preferred_match_fields: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, comment="优先匹配字段")
    profile_summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="系统摘要")
    vector_dirty: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True, comment="向量是否待更新")
    last_vectorized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最近向量化时间")
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="admin", index=True, comment="来源类型")
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True, comment="来源ID")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=20, index=True, comment="优先级")
    is_effective: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True, comment="是否当前有效")
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True, comment="是否最终版")
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="版本号")


class PersonPartnerPreferenceVersionModel(ModelMixin, UserMixin):
    """人员择偶要求历史版本。"""

    __tablename__ = "person_partner_preference_version"
    __table_args__: dict[str, str] = {"comment": "人员择偶要求历史版本表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    person_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crm_person.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="人员ID",
    )
    preference_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("person_partner_preference.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="当前择偶要求ID",
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="版本号")
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="来源类型")
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True, comment="来源ID")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=20, index=True, comment="优先级")
    is_effective: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True, comment="是否成为当前有效")
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True, comment="是否最终版")
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, comment="择偶要求快照")
