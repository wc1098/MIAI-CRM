import re

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.common.enums import QueueEnum
from app.core.base_schema import BaseSchema, UserBySchema
from app.core.validator import DateTimeStr

CHANNEL_CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class ChannelCreateSchema(BaseModel):
    """渠道创建模型"""

    channel_code: str = Field(..., max_length=64, description="渠道编码")
    channel_name: str = Field(..., max_length=64, description="渠道名称")
    channel_type: str = Field(..., max_length=32, description="渠道类型")
    source_system: str | None = Field(default=None, max_length=64, description="来源系统")
    external_code: str | None = Field(default=None, max_length=128, description="外部渠道编码")
    landing_url: str | None = Field(default=None, max_length=500, description="落地页/投放页链接")
    sort: int = Field(default=1, ge=1, le=999, description="排序")
    status: str = Field(default="0", description="状态(0:启用 1:停用)")
    description: str | None = Field(default=None, max_length=255, description="描述")

    @field_validator("channel_code")
    @classmethod
    def validate_channel_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not CHANNEL_CODE_PATTERN.match(value):
            raise ValueError("渠道编码只能包含字母、数字、下划线、中划线，长度1-64")
        return value

    @field_validator("channel_name")
    @classmethod
    def validate_channel_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("渠道名称不能为空")
        return value

    @field_validator("channel_type")
    @classmethod
    def validate_channel_type(cls, value: str) -> str:
        value = value.strip().lower()
        if not value:
            raise ValueError("渠道类型不能为空")
        return value

    @field_validator("source_system", "external_code", "landing_url", "description")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"0", "1"}:
            raise ValueError("状态必须为0或1")
        return value


class ChannelUpdateSchema(ChannelCreateSchema):
    """渠道更新模型"""


class ChannelOutSchema(ChannelCreateSchema, BaseSchema, UserBySchema):
    """渠道响应模型"""

    model_config = ConfigDict(from_attributes=True)


class ChannelQueryParam:
    """渠道查询参数"""

    def __init__(
        self,
        channel_code: str | None = Query(None, description="渠道编码"),
        channel_name: str | None = Query(None, description="渠道名称"),
        channel_type: str | None = Query(None, description="渠道类型"),
        source_system: str | None = Query(None, description="来源系统"),
        status: str | None = Query(None, description="状态"),
        created_time: list[DateTimeStr] | None = Query(
            None,
            description="创建时间范围",
            examples=["2025-01-01 00:00:00", "2025-12-31 23:59:59"],
        ),
        updated_time: list[DateTimeStr] | None = Query(
            None,
            description="更新时间范围",
            examples=["2025-01-01 00:00:00", "2025-12-31 23:59:59"],
        ),
    ) -> None:
        self.channel_code = (QueueEnum.like.value, channel_code)
        self.channel_name = (QueueEnum.like.value, channel_name)
        if channel_type:
            self.channel_type = (QueueEnum.eq.value, channel_type)
        if source_system:
            self.source_system = (QueueEnum.like.value, source_system)
        if status:
            self.status = (QueueEnum.eq.value, status)
        if created_time and len(created_time) == 2:
            self.created_time = (QueueEnum.between.value, (created_time[0], created_time[1]))
        if updated_time and len(updated_time) == 2:
            self.updated_time = (QueueEnum.between.value, (updated_time[0], updated_time[1]))
