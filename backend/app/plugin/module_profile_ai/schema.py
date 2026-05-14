from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.validator import DateTimeStr


class PersonAiProfileBriefSchema(BaseModel):
    """AI 画像摘要。"""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    profile_type: str = Field(default="miai_impression", description="画像类型")
    source_type: str | None = Field(default=None, description="来源类型")
    source_id: str | None = Field(default=None, description="来源对象ID")
    priority: int | None = Field(default=None, description="优先级")
    content: str | None = Field(default=None, description="画像内容")
    generation_status: str | None = Field(default=None, description="生成状态")
    is_effective: bool = Field(default=False, description="是否当前生效")
    model_name: str | None = Field(default=None, description="模型名称")
    generated_at: DateTimeStr | None = Field(default=None, description="生成时间")
    updated_time: DateTimeStr | None = Field(default=None, description="更新时间")
    last_error: str | None = Field(default=None, description="最近错误")


class PersonAiProfileTaskBriefSchema(BaseModel):
    """AI 画像任务摘要。"""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    profile_type: str = Field(default="miai_impression", description="画像类型")
    status: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    priority: int | None = None
    retry_count: int = 0
    next_retry_at: DateTimeStr | None = None
    updated_time: DateTimeStr | None = None
    last_error: str | None = None


class PersonAiProfileAdminSchema(BaseModel):
    """admin 端 AI 画像展示信息。"""

    profile: PersonAiProfileBriefSchema | None = None
    latest_task: PersonAiProfileTaskBriefSchema | None = None


class EnqueueProfileTaskSchema(BaseModel):
    """画像任务投递响应。"""

    task_id: int
    person_id: int
    profile_type: str
    source_type: str
    payload_snapshot: dict[str, Any] | None = None
