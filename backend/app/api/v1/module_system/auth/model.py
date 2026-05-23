from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import ModelMixin


class UserQuickLoginDeviceModel(ModelMixin):
    """本机快速登录凭证。"""

    __tablename__: str = "sys_user_quick_login_device"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sys_user.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID",
    )
    token_hash: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True, comment="快速登录凭证哈希"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True, comment="过期时间"
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True, comment="最近使用时间"
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True, comment="撤销时间"
    )

    user = relationship("UserModel", lazy="selectin", uselist=False)
