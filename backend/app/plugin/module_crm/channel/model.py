from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import PermissionFilterStrategy
from app.core.base_model import ModelMixin, UserMixin


class CrmChannelModel(ModelMixin, UserMixin):
    """CRM渠道模型"""

    __tablename__: str = "crm_channel"
    __table_args__: dict[str, str] = {"comment": "CRM渠道表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    channel_code: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True, comment="渠道编码"
    )
    channel_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="渠道名称")
    channel_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True, comment="渠道类型"
    )
    source_system: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, comment="来源系统"
    )
    external_code: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True, comment="外部渠道编码"
    )
    landing_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="落地页/投放页链接"
    )
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="排序")
