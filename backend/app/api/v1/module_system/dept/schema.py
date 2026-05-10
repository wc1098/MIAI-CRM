import re

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.common.enums import QueueEnum
from app.core.base_schema import BaseSchema
from app.core.validator import DateTimeStr


class DeptCreateSchema(BaseModel):
    """门店创建模型"""

    name: str = Field(..., max_length=64, description="门店名称")
    order: int = Field(default=1, ge=0, description="显示顺序")
    code: str = Field(..., max_length=32, description="门店编码")
    leader: str | None = Field(default=None, max_length=32, description="门店负责人")
    phone: str | None = Field(default=None, max_length=11, description="手机")
    email: str | None = Field(default=None, max_length=64, description="邮箱")
    parent_id: int | None = Field(default=None, ge=0, description="上级门店ID")
    status: str = Field(default="0", description="是否启用(0:启用 1:禁用)")
    description: str | None = Field(default=None, max_length=255, description="备注说明")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str):
        """
        校验并规范化门店名称（去空格、非空）。

        参数:
        - value (str): 门店名称。

        返回:
        - str: 规范化后的门店名称。

        异常:
        - ValueError: 门店名称为空时抛出。
        """
        if not value or len(value.strip()) == 0:
            raise ValueError("门店名称不能为空")
        value = value.replace(" ", "")
        return value

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str):
        """
        校验门店编码，允许纯数字编码以兼容后续支付通道门店号。

        参数:
        - value (str): 门店编码。

        返回:
        - str: 规范化后的门店编码。

        异常:
        - ValueError: 编码不满足格式要求时抛出。
        """
        if value is None or not str(value).strip():
            raise ValueError("门店编码不能为空")
        v = value.strip()
        if not re.match(r"^[A-Za-z0-9_]{1,32}$", v):
            raise ValueError("门店编码允许字母/数字/下划线，长度1-32，支持纯数字")
        return v


class DeptUpdateSchema(DeptCreateSchema):
    """门店更新模型"""


class DeptOutSchema(DeptCreateSchema, BaseSchema):
    """门店响应模型"""

    model_config = ConfigDict(from_attributes=True)

    parent_name: str | None = Field(default=None, max_length=64, description="上级门店名称")


class DeptQueryParam:
    """门店管理查询参数"""

    def __init__(
        self,
        name: str | None = Query(None, description="门店名称"),
        status: str | None = Query(None, description="门店状态(True正常 False停用)"),
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

        # 模糊查询字段
        self.name = (QueueEnum.like.value, name)

        # 精确查询字段
        self.status = (QueueEnum.eq.value, status)

        # 时间范围查询
        if created_time and len(created_time) == 2:
            self.created_time = (QueueEnum.between.value, (created_time[0], created_time[1]))
        if updated_time and len(updated_time) == 2:
            self.updated_time = (QueueEnum.between.value, (updated_time[0], updated_time[1]))
