from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import PermissionFilterStrategy
from app.core.base_model import ModelMixin, UserMixin


class ScreenDeviceModel(ModelMixin, UserMixin):
    """大屏设备"""

    __tablename__: str = "screen_device"
    __table_args__ = (
        UniqueConstraint("device_code", name="uq_screen_device_code"),
        {"comment": "大屏设备表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    store_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_dept.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="绑定门店ID")
    device_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="设备码")
    device_name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="设备名称")
    device_type: Mapped[str] = mapped_column(String(32), nullable=False, default="web", index=True, comment="设备类型")
    device_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True, comment="设备Token哈希")
    bind_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unbound", index=True, comment="绑定状态")
    online_status: Mapped[str] = mapped_column(String(32), nullable=False, default="offline", index=True, comment="在线状态")
    bound_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="绑定人ID")
    bound_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="绑定时间")
    last_online_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="最近在线时间")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="最近同步时间")
    app_version: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="应用版本")
    system_info: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="设备系统信息")


class ScreenUserWallConfigModel(ModelMixin, UserMixin):
    """品牌用户墙配置"""

    __tablename__: str = "screen_user_wall_config"
    __table_args__ = (
        UniqueConstraint("brand_id", name="uq_screen_user_wall_config_brand"),
        {"comment": "大屏用户墙配置表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    title: Mapped[str] = mapped_column(String(128), nullable=False, default="觅爱用户墙", comment="标题")
    user_switch_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=12, comment="用户轮播秒数")
    photo_switch_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=4, comment="多图切换秒数")
    sort_strategy: Mapped[str] = mapped_column(String(32), nullable=False, default="latest", index=True, comment="排序策略")
    filter_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="筛选配置")
    qr_action: Mapped[str] = mapped_column(String(32), nullable=False, default="mini_profile", comment="二维码动作")


class ScreenUserWallQrcodeModel(ModelMixin):
    """用户墙小程序码缓存"""

    __tablename__: str = "screen_user_wall_qrcode"
    __table_args__ = (
        UniqueConstraint("person_id", "display_no", "page_path", name="uq_screen_user_wall_qrcode_target"),
        {"comment": "大屏用户墙小程序码缓存表"},
    )

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="人员ID")
    display_no: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="展示编号")
    page_path: Mapped[str] = mapped_column(String(255), nullable=False, comment="小程序页面路径")
    scene: Mapped[str] = mapped_column(String(128), nullable=False, comment="小程序码场景值")
    file_url: Mapped[str] = mapped_column(String(1000), nullable=False, comment="文件URL")
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="文件路径")
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="生成时间")


class ScreenUserWallRecordModel(ModelMixin):
    """用户墙播放记录"""

    __tablename__: str = "screen_user_wall_record"
    __table_args__: dict[str, str] = {"comment": "大屏用户墙播放记录表"}

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("screen_device.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="设备ID")
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="展示人员ID")
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("mini_program_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="小程序用户ID")
    display_no: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="展示编号")
    display_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="展示快照")
    displayed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="展示时间")
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="展示秒数")
    play_result: Mapped[str] = mapped_column(String(32), nullable=False, default="success", index=True, comment="播放结果")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")


class ScreenPromoConfigModel(ModelMixin, UserMixin):
    """品牌宣传大屏配置"""

    __tablename__: str = "screen_promo_config"
    __table_args__ = (
        UniqueConstraint("brand_id", name="uq_screen_promo_config_brand"),
        {"comment": "宣传大屏配置表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False, comment="是否启用")
    image_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=8, comment="默认图片轮播秒数")
    staff_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=12, comment="默认员工轮播秒数")
    sync_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60, comment="安卓同步间隔秒数")
    cache_limit_gb: Mapped[int] = mapped_column(Integer, nullable=False, default=20, comment="安卓缓存上限GB")


class ScreenPromoStaffModel(ModelMixin, UserMixin):
    """宣传大屏员工公开资料"""

    __tablename__: str = "screen_promo_staff"
    __table_args__: dict[str, str] = {"comment": "宣传大屏员工展示资料表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    avatar_url: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="头像/形象照URL")
    display_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="展示姓名/花名")
    role_title: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="岗位")
    years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="从业年限")
    specialties: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="擅长方向")
    service_slogan: Mapped[str | None] = mapped_column(Text, nullable=True, comment="服务宣言")
    public_tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, comment="公开成绩/标签")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True, comment="排序")


class ScreenPromoItemModel(ModelMixin, UserMixin):
    """宣传大屏播放序列项"""

    __tablename__: str = "screen_promo_item"
    __table_args__: dict[str, str] = {"comment": "宣传大屏播放序列表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    item_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="类型:image/video/staff")
    title: Mapped[str] = mapped_column(String(128), nullable=False, comment="标题")
    file_url: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="素材URL")
    cover_url: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="封面URL")
    file_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="文件Hash")
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="文件大小")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="素材版本")
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="展示秒数")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True, comment="排序")
    staff_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("screen_promo_staff.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="员工资料ID")


class ScreenPromoRecordModel(ModelMixin):
    """宣传大屏播放记录"""

    __tablename__: str = "screen_promo_record"
    __table_args__: dict[str, str] = {"comment": "宣传大屏播放记录表"}

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("screen_device.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="设备ID")
    item_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("screen_promo_item.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="播放项ID")
    item_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="播放项类型")
    play_result: Mapped[str] = mapped_column(String(32), nullable=False, default="success", index=True, comment="播放结果")
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="播放秒数")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    played_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="播放时间")


class ScreenPromoCacheReportModel(ModelMixin):
    """宣传大屏安卓缓存状态上报"""

    __tablename__: str = "screen_promo_cache_report"
    __table_args__: dict[str, str] = {"comment": "宣传大屏缓存状态表"}

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("screen_device.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="设备ID")
    item_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("screen_promo_item.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="播放项ID")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="素材版本")
    cache_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="缓存状态")
    local_path: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="本地路径")
    downloaded_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="已下载字节")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    reported_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="上报时间")


class ScreenActivityConfigModel(ModelMixin, UserMixin):
    """活动大屏配置"""

    __tablename__: str = "screen_activity_config"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_screen_activity_config_event"),
        UniqueConstraint("checkin_scene", name="uq_screen_activity_config_scene"),
        {"comment": "活动大屏配置表"},
    )
    __loader_options__: list[str] = ["event", "created_by", "updated_by", "deleted_by"]
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    store_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_dept.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="门店ID")
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("event.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="活动ID")
    screen_name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="大屏名称")
    title: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="兼容字段:大屏标题")
    subtitle: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="兼容字段:大屏副标题")
    background_url: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="背景图URL")
    theme_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="画面配置")
    module_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="功能模块配置")
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False, index=True, comment="是否启用")
    current_scene: Mapped[str] = mapped_column(String(32), nullable=False, default="blank", index=True, comment="当前场景:blank/checkin")
    show_qrcode: Mapped[bool] = mapped_column(default=True, nullable=False, comment="是否显示二维码")
    qrcode_url: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="小程序码URL")
    qrcode_file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="小程序码文件路径")
    qrcode_page: Mapped[str] = mapped_column(String(255), nullable=False, default="pages/activity/checkin/index", comment="小程序码页面")
    checkin_scene: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="扫码签到场景值")
    qrcode_generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="二维码生成时间")
    last_command: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="最近遥控命令")
    last_command_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="最近遥控时间")

    event: Mapped[Any] = relationship("EventModel", lazy="selectin")


class ScreenActivityBarrageModel(ModelMixin):
    """活动大屏普通弹幕记录"""

    __tablename__: str = "screen_activity_barrage"
    __table_args__: dict[str, str] = {"comment": "活动大屏普通弹幕记录表"}

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    store_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_dept.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="门店ID")
    activity_id: Mapped[int] = mapped_column(Integer, ForeignKey("screen_activity_config.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="活动大屏ID")
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("event.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="活动ID")
    mp_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("mini_program_user.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="小程序用户ID")
    person_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="人员ID")
    nickname: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="展示昵称")
    avatar_url: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="头像URL")
    content: Mapped[str] = mapped_column(String(200), nullable=False, comment="弹幕内容")
    display_status: Mapped[str] = mapped_column(String(32), nullable=False, default="displayed", index=True, comment="展示状态")
    displayed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="展示时间")
