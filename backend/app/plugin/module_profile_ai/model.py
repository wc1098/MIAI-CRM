from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin


class PersonAiProfileModel(ModelMixin):
    """人员 AI 画像结果。"""

    __tablename__ = "person_ai_profile"
    __table_args__: dict[str, str] = {"comment": "人员AI画像结果表"}

    person_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crm_person.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="人员ID",
    )
    profile_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="画像类型")
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="来源类型")
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True, comment="来源对象ID")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=10, index=True, comment="优先级")
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="画像内容")
    input_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="脱敏输入快照")
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="模型名称")
    generation_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True, comment="生成状态")
    is_effective: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True, comment="是否当前生效")
    generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="生成时间")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="最近错误")


class PersonAiProfileTaskModel(ModelMixin):
    """人员 AI 画像异步任务。"""

    __tablename__ = "person_ai_profile_task"
    __table_args__: dict[str, str] = {"comment": "人员AI画像生成任务表"}

    person_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crm_person.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="人员ID",
    )
    profile_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="画像类型")
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="来源类型")
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True, comment="来源对象ID")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=10, index=True, comment="优先级")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True, comment="任务状态")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="重试次数")
    next_retry_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="下次重试时间")
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="锁定时间")
    locked_by: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="锁定者")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="最近错误")
    payload_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="脱敏载荷快照")
