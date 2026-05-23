from decimal import Decimal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.common.enums import QueueEnum
from app.core.base_schema import BaseSchema, UserBySchema


class ProductPackageBaseSchema(BaseModel):
    """产品套餐基础模型"""

    package_name: str = Field(..., max_length=128, description="套餐名称")
    standard_price: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2, description="标准价")
    service_days: int = Field(default=0, ge=0, description="服务时长天数")
    recommendation_quota: int = Field(default=0, ge=0, description="推荐次数")
    meeting_quota: int = Field(default=0, ge=0, description="约见次数")
    course_quota: int = Field(default=0, ge=0, description="课程次数")
    supports_online_meeting: bool = Field(default=False, description="是否支持线上约见")
    description: str | None = Field(default=None, description="套餐说明")
    internal_remark: str | None = Field(default=None, description="内部备注")
    sort: int = Field(default=0, ge=0, le=9999, description="排序")
    status: str = Field(default="0", description="状态(0:启用 1:停用)")

    @field_validator("package_name")
    @classmethod
    def validate_package_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("套餐名称不能为空")
        return value

    @field_validator("description", "internal_remark")
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


class ProductPackageCreateSchema(ProductPackageBaseSchema):
    """产品套餐创建模型"""


class ProductPackageUpdateSchema(ProductPackageBaseSchema):
    """产品套餐更新模型"""


class ProductPackageChangeStatusSchema(BaseModel):
    """产品套餐状态修改模型"""

    status: str = Field(..., description="状态(0:启用 1:停用)")

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"0", "1"}:
            raise ValueError("状态必须为0或1")
        return value


class ProductPackageOutSchema(ProductPackageBaseSchema, BaseSchema, UserBySchema):
    """产品套餐响应模型"""

    model_config = ConfigDict(from_attributes=True)

    brand_id: int = Field(default=1, description="品牌ID")


class ProductPackageQueryParam:
    """产品套餐查询参数"""

    def __init__(
        self,
        keyword: str | None = Query(None, description="关键词"),
        status: str | None = Query(None, description="状态"),
    ) -> None:
        self.keyword = keyword.strip() if keyword else None
        if status:
            self.status = (QueueEnum.eq.value, status)
