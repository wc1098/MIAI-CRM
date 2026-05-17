from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin


class PersonMatchProfileModel(ModelMixin):
    """人员匹配画像快照。"""

    __tablename__ = "person_match_profile"
    __table_args__ = (
        UniqueConstraint("person_id", name="uq_person_match_profile_person"),
        {"comment": "人员匹配画像快照表"},
    )

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    person_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crm_person.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="人员ID",
    )
    self_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="个人画像脱敏快照")
    preference_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="择偶要求脱敏快照")
    ai_profile_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="AI画像摘要快照")
    self_input_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="个人画像向量输入文本")
    preference_input_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="择偶要求向量输入文本")
    completeness_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="资料完整度")
    self_vector_dirty: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True, comment="个人画像向量待更新")
    preference_vector_dirty: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True, comment="择偶向量待更新")
    last_snapshot_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="最近快照时间")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="最近错误")


class PersonMatchVectorModel(ModelMixin):
    """人员匹配向量。"""

    __tablename__ = "person_match_vector"
    __table_args__ = (
        UniqueConstraint("person_id", "vector_type", name="uq_person_match_vector_person_type"),
        {"comment": "人员匹配向量表"},
    )

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    person_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crm_person.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="人员ID",
    )
    vector_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="向量类型")
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True, comment="向量")
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True, comment="向量模型")
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False, default=768, comment="向量维度")
    input_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="向量输入文本")
    input_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="向量输入快照")
    vector_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True, comment="向量状态")
    last_vectorized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="最近向量化时间")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="最近错误")


class PersonMatchVectorTaskModel(ModelMixin):
    """人员匹配向量异步任务。"""

    __tablename__ = "person_match_vector_task"
    __table_args__: dict[str, str] = {"comment": "人员匹配向量任务表"}

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    person_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crm_person.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="人员ID",
    )
    vector_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="向量类型")
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="来源类型")
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True, comment="来源对象ID")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True, comment="任务状态")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="重试次数")
    next_retry_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="下次执行时间")
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="锁定时间")
    locked_by: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="锁定者")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="最近错误")
    payload_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="载荷快照")
