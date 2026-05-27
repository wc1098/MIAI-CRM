from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import PermissionFilterStrategy
from app.core.base_model import ModelMixin, UserMixin


class PersonProfileInsightModel(ModelMixin, UserMixin):
    """人员当前深访画像"""

    __tablename__: str = "person_profile_insight"
    __table_args__ = (
        UniqueConstraint("person_id", name="uq_person_profile_insight_person"),
        {"comment": "人员当前深访画像表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="人员ID")
    source_interview_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("deep_interview.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="来源深访ID")
    source_scope: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="来源深访场景")
    personality_tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, comment="性格标签")
    family_background: Mapped[str | None] = mapped_column(Text, nullable=True, comment="家庭背景")
    relationship_history: Mapped[str | None] = mapped_column(Text, nullable=True, comment="情感经历")
    marriage_view: Mapped[str | None] = mapped_column(Text, nullable=True, comment="婚恋观")
    communication_style: Mapped[str | None] = mapped_column(Text, nullable=True, comment="沟通方式")
    emotional_needs: Mapped[str | None] = mapped_column(Text, nullable=True, comment="情感需求")
    hard_reject_items: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, comment="硬性拒绝项")
    soft_preference_items: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, comment="软性偏好")
    compromise_items: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, comment="可妥协项")
    risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="风险等级")
    risk_notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="风险提示")
    communication_taboo: Mapped[str | None] = mapped_column(Text, nullable=True, comment="沟通禁忌")
    recommendation_strategy: Mapped[str | None] = mapped_column(Text, nullable=True, comment="推荐策略")
    matchmaker_comment: Mapped[str | None] = mapped_column(Text, nullable=True, comment="红娘评价")
    public_matchmaker_impression: Mapped[str | None] = mapped_column(Text, nullable=True, comment="脱敏红娘印象")
    keywords: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, comment="关键词")
    profile_status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True, comment="画像状态")
    profile_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="画像来源结构化快照")
    updated_by_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="画像维护人ID")
    insight_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="画像更新时间")
