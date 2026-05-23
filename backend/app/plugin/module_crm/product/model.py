from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import PermissionFilterStrategy
from app.core.base_model import ModelMixin, UserMixin


class CrmProductPackageModel(ModelMixin, UserMixin):
    """CRM产品套餐模型"""

    __tablename__: str = "crm_product_package"
    __table_args__: dict[str, str] = {"comment": "CRM产品套餐表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DEPT_BASED

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    package_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment="套餐名称")
    standard_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00"), comment="标准价"
    )
    service_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="服务时长天数")
    recommendation_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="推荐次数")
    meeting_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="约见次数")
    course_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="课程次数")
    supports_online_meeting: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否支持线上约见")
    internal_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="内部备注")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True, comment="排序")
