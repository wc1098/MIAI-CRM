from datetime import datetime
from typing import Any

from fastapi import Query
from pydantic import BaseModel, Field, field_validator

from app.core.validator import DateTimeStr


class ScreenDeviceQueryParam:
    def __init__(
        self,
        keyword: str | None = Query(None, description="设备码/设备名称"),
        bind_status: str | None = Query(None, description="绑定状态"),
        online_status: str | None = Query(None, description="在线状态"),
    ) -> None:
        self.keyword = keyword.strip() if keyword else None
        self.bind_status = bind_status
        self.online_status = online_status


class ScreenDeviceBootstrapSchema(BaseModel):
    device_type: str = Field(default="web", max_length=32, description="设备类型")
    app_version: str | None = Field(default=None, max_length=64, description="应用版本")
    system_info: dict[str, Any] = Field(default_factory=dict, description="系统信息")


class ScreenDeviceBindSchema(BaseModel):
    device_code: str = Field(..., min_length=4, max_length=32, description="设备码")
    device_name: str | None = Field(default=None, max_length=128, description="设备名称")
    store_id: int | None = Field(default=None, description="门店ID，仅用于资产管理")

    @field_validator("device_code")
    @classmethod
    def clean_device_code(cls, value: str) -> str:
        return value.strip().upper()


class ScreenDeviceHeartbeatSchema(BaseModel):
    app_version: str | None = Field(default=None, max_length=64, description="应用版本")
    system_info: dict[str, Any] = Field(default_factory=dict, description="系统信息")


class ScreenUserWallConfigSchema(BaseModel):
    title: str = Field(default="觅爱用户墙", min_length=1, max_length=128, description="标题")
    user_switch_seconds: int = Field(default=12, ge=5, le=120, description="用户轮播秒数")
    photo_switch_seconds: int = Field(default=4, ge=2, le=60, description="用户多图切换秒数")
    sort_strategy: str = Field(default="latest", description="排序策略")
    filter_config: dict[str, Any] = Field(default_factory=dict, description="筛选配置")
    qr_action: str = Field(default="mini_profile", description="二维码动作")
    status: str = Field(default="0", description="状态")


class ScreenUserWallRecordSchema(BaseModel):
    person_id: int
    user_id: int | None = None
    display_no: str | None = None
    display_snapshot: dict[str, Any] = Field(default_factory=dict)
    duration_seconds: int | None = Field(default=None, ge=0, le=3600)
    play_result: str = Field(default="success", max_length=32)
    error_message: str | None = Field(default=None, max_length=1000)


class ScreenPromoConfigSchema(BaseModel):
    enabled: bool = Field(default=True, description="是否启用")
    image_duration_seconds: int = Field(default=8, ge=3, le=3600, description="默认图片轮播秒数")
    staff_duration_seconds: int = Field(default=12, ge=3, le=3600, description="默认员工轮播秒数")
    sync_interval_seconds: int = Field(default=60, ge=10, le=86400, description="安卓同步间隔秒数")
    cache_limit_gb: int = Field(default=20, ge=1, le=200, description="缓存上限GB")
    status: str = Field(default="0", description="状态")


class ScreenPromoStaffSchema(BaseModel):
    avatar_url: str | None = Field(default=None, max_length=1000, description="头像/形象照URL")
    display_name: str = Field(..., min_length=1, max_length=64, description="展示姓名/花名")
    role_title: str | None = Field(default=None, max_length=128, description="岗位")
    years_experience: int | None = Field(default=None, ge=0, le=80, description="从业年限")
    specialties: list[str] = Field(default_factory=list, description="擅长方向标签")
    service_slogan: str | None = Field(default=None, max_length=2000, description="服务宣言")
    public_tags: list[str] = Field(default_factory=list, description="公开成绩/标签")
    sort: int = Field(default=0, ge=0, description="排序")
    status: str = Field(default="0", description="状态")


class ScreenPromoItemSchema(BaseModel):
    item_type: str = Field(..., description="类型:image/video/staff")
    title: str = Field(default="", max_length=128, description="标题")
    file_url: str | None = Field(default=None, max_length=1000, description="素材URL")
    cover_url: str | None = Field(default=None, max_length=1000, description="封面URL")
    file_hash: str | None = Field(default=None, max_length=128, description="文件Hash")
    file_size: int | None = Field(default=None, ge=0, description="文件大小")
    version: int = Field(default=1, ge=1, description="版本")
    duration_seconds: int | None = Field(default=None, ge=1, le=86400, description="展示秒数")
    sort: int = Field(default=0, ge=0, description="排序")
    staff_id: int | None = Field(default=None, description="员工资料ID")
    status: str = Field(default="0", description="状态")

    @field_validator("item_type")
    @classmethod
    def validate_item_type(cls, value: str) -> str:
        clean = value.strip().lower()
        if clean not in {"image", "video", "staff"}:
            raise ValueError("播放项类型只支持 image、video、staff")
        return clean


class ScreenPromoSortSchema(BaseModel):
    ids: list[int] = Field(..., min_length=1, description="排序后的ID列表")


class ScreenPromoCacheReportSchema(BaseModel):
    item_id: int | None = None
    version: int = Field(default=1, ge=1)
    cache_status: str = Field(..., max_length=32)
    local_path: str | None = Field(default=None, max_length=1000)
    downloaded_bytes: int | None = Field(default=None, ge=0)
    error_message: str | None = Field(default=None, max_length=2000)


class ScreenPromoRecordSchema(BaseModel):
    item_id: int | None = None
    item_type: str = Field(..., max_length=16)
    play_result: str = Field(default="success", max_length=32)
    duration_seconds: int | None = Field(default=None, ge=0, le=86400)
    error_message: str | None = Field(default=None, max_length=2000)


class ScreenDeviceOutSchema(BaseModel):
    id: int
    brand_id: int
    store_id: int | None = None
    device_code: str
    device_name: str | None = None
    device_type: str
    bind_status: str
    online_status: str
    bound_by: int | None = None
    bound_at: DateTimeStr | None = None
    last_online_at: DateTimeStr | None = None
    last_sync_at: DateTimeStr | None = None
    app_version: str | None = None
    system_info: dict[str, Any] | None = None
    created_time: DateTimeStr | None = None


class ScreenDeviceBootstrapOutSchema(BaseModel):
    device_id: int | None = None
    device_code: str
    bind_status: str
    expires_at: datetime | None = None


class ScreenBindStatusOutSchema(BaseModel):
    device_id: int | None = None
    device_code: str
    bind_status: str
    device_token: str | None = None
    device_name: str | None = None
