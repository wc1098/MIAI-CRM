from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import ModelMixin


class MiniProgramUserModel(ModelMixin):
    """微信小程序用户身份。"""

    __tablename__ = "mini_program_user"
    __table_args__: dict[str, str] = {"comment": "微信小程序用户表"}
    __loader_options__: list[str] = ["person"]

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    person_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("crm_person.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="关联人员ID",
    )
    openid: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True, comment="微信openid")
    unionid: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True, comment="微信unionid")
    session_key: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="微信session_key")
    mobile: Mapped[str | None] = mapped_column(String(20), nullable=True, unique=True, index=True, comment="微信手机号")
    nickname: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="微信昵称")
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="系统头像/主展示照")
    is_invisible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否隐身")
    allow_user_wall: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否允许上墙")
    registered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="注册时间")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="最近登录时间")

    person: Mapped[Any] = relationship("CrmPersonModel", lazy="selectin")


class UserAgreementAcceptanceModel(ModelMixin):
    """小程序用户协议同意记录。"""

    __tablename__ = "user_agreement_acceptance"
    __table_args__: dict[str, str] = {"comment": "小程序协议同意记录表"}

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mini_program_user.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="小程序用户ID",
    )
    agreement_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="协议类型")
    agreement_version: Mapped[str] = mapped_column(String(32), nullable=False, comment="协议版本")
    agreement_title: Mapped[str] = mapped_column(String(128), nullable=False, comment="协议标题快照")
    accepted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="同意时间")
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="IP")
    device_info: Mapped[str | None] = mapped_column(Text, nullable=True, comment="设备信息")


class SourceEventModel(ModelMixin):
    """来源事件/行为事件。"""

    __tablename__ = "source_event"
    __table_args__: dict[str, str] = {"comment": "来源事件表"}

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    person_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crm_person.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="人员ID",
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("mini_program_user.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="小程序用户ID",
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="事件类型")
    source_channel: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="来源渠道")
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True, comment="来源对象ID")
    source_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="分享来源用户ID")
    store_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sys_dept.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="门店ID",
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原始来源参数")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="发生时间")
