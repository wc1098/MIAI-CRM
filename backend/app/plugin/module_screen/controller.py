from typing import Annotated

from fastapi import APIRouter, Body, Depends, Header, Query, Request
from fastapi.responses import JSONResponse
from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter, redis_getter
from app.core.router_class import OperationLogRoute

from .dependencies import get_screen_device
from .model import ScreenDeviceModel
from .schema import (
    ScreenActivityBarrageSettingsSchema,
    ScreenActivityCheckinWallSettingsSchema,
    ScreenActivityCommandSchema,
    ScreenActivityConfigSchema,
    ScreenActivityDominateSettingsSchema,
    ScreenActivityMusicSettingsSchema,
    ScreenActivityQrcodeSettingsSchema,
    ScreenActivityQueryParam,
    ScreenDeviceBindSchema,
    ScreenDeviceBootstrapSchema,
    ScreenDeviceHeartbeatSchema,
    ScreenDeviceQueryParam,
    ScreenPromoCacheReportSchema,
    ScreenPromoConfigSchema,
    ScreenPromoItemSchema,
    ScreenPromoRecordSchema,
    ScreenPromoSortSchema,
    ScreenPromoStaffSchema,
    ScreenUserWallConfigSchema,
    ScreenUserWallRecordSchema,
)
from .service import ScreenService

ScreenDeviceRouter = APIRouter(route_class=OperationLogRoute, prefix="/device", tags=["大屏设备端"])
ScreenPlayerRouter = APIRouter(route_class=OperationLogRoute, prefix="/player", tags=["大屏播放端"])
ScreenAdminRouter = APIRouter(route_class=OperationLogRoute, prefix="/admin", tags=["大屏后台管理"])
ScreenControlRouter = APIRouter(route_class=OperationLogRoute, prefix="/control", tags=["活动大屏手机控制台"])


def _control_token(authorization: str | None, x_screen_control_token: str | None = None) -> str:
    token = x_screen_control_token or ""
    if authorization:
        parts = authorization.strip().split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "screencontrol":
            token = parts[1].strip()
    return token


@ScreenDeviceRouter.post("/bootstrap", summary="大屏设备初始化")
async def bootstrap_controller(
    data: ScreenDeviceBootstrapSchema,
    db: Annotated[AsyncSession, Depends(db_getter)],
    redis: Annotated[Redis, Depends(redis_getter)],
) -> JSONResponse:
    result = await ScreenService.bootstrap(db, redis, data)
    return SuccessResponse(data=result, msg="大屏设备初始化成功")


@ScreenDeviceRouter.get("/bind-status", summary="查询设备绑定状态")
async def bind_status_controller(
    device_code: Annotated[str, Query(description="设备码")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    redis: Annotated[Redis, Depends(redis_getter)],
) -> JSONResponse:
    result = await ScreenService.bind_status(db, redis, device_code)
    return SuccessResponse(data=result, msg="查询设备绑定状态成功")


@ScreenDeviceRouter.post("/heartbeat", summary="大屏设备心跳")
async def heartbeat_controller(
    data: ScreenDeviceHeartbeatSchema,
    db: Annotated[AsyncSession, Depends(db_getter)],
    device: Annotated[ScreenDeviceModel, Depends(get_screen_device)],
) -> JSONResponse:
    result = await ScreenService.heartbeat(db, device, data)
    return SuccessResponse(data=result, msg="大屏设备心跳成功")


@ScreenPlayerRouter.get("/config", summary="查询大屏播放配置")
async def player_config_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
    device: Annotated[ScreenDeviceModel, Depends(get_screen_device)],
) -> JSONResponse:
    result = await ScreenService.player_config(db, device)
    return SuccessResponse(data=result, msg="查询大屏播放配置成功")


@ScreenPlayerRouter.get("/user-wall", summary="查询用户墙数据")
async def player_user_wall_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
    device: Annotated[ScreenDeviceModel, Depends(get_screen_device)],
) -> JSONResponse:
    result = await ScreenService.player_user_wall(db, device)
    return SuccessResponse(data=result, msg="查询用户墙数据成功")


@ScreenPlayerRouter.post("/user-wall/record", summary="上报用户墙播放记录")
async def player_user_wall_record_controller(
    data: ScreenUserWallRecordSchema,
    db: Annotated[AsyncSession, Depends(db_getter)],
    device: Annotated[ScreenDeviceModel, Depends(get_screen_device)],
) -> JSONResponse:
    result = await ScreenService.record_user_wall(db, device, data)
    return SuccessResponse(data=result, msg="上报用户墙播放记录成功")


@ScreenPlayerRouter.get("/promo", summary="查询宣传大屏播放列表")
async def player_promo_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
    device: Annotated[ScreenDeviceModel, Depends(get_screen_device)],
) -> JSONResponse:
    result = await ScreenService.player_promo(db, device)
    return SuccessResponse(data=result, msg="查询宣传大屏播放列表成功")


@ScreenPlayerRouter.post("/promo/cache-report", summary="上报宣传大屏缓存状态")
async def player_promo_cache_report_controller(
    data: ScreenPromoCacheReportSchema,
    db: Annotated[AsyncSession, Depends(db_getter)],
    device: Annotated[ScreenDeviceModel, Depends(get_screen_device)],
) -> JSONResponse:
    result = await ScreenService.report_promo_cache(db, device, data)
    return SuccessResponse(data=result, msg="上报宣传大屏缓存状态成功")


@ScreenPlayerRouter.post("/promo/record", summary="上报宣传大屏播放记录")
async def player_promo_record_controller(
    data: ScreenPromoRecordSchema,
    db: Annotated[AsyncSession, Depends(db_getter)],
    device: Annotated[ScreenDeviceModel, Depends(get_screen_device)],
) -> JSONResponse:
    result = await ScreenService.record_promo(db, device, data)
    return SuccessResponse(data=result, msg="上报宣传大屏播放记录成功")


@ScreenPlayerRouter.get("/activity/list", summary="查询活动大屏列表")
async def player_activity_list_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
    device: Annotated[ScreenDeviceModel, Depends(get_screen_device)],
) -> JSONResponse:
    result = await ScreenService.player_activity_list(db, device)
    return SuccessResponse(data=result, msg="查询活动大屏列表成功")


@ScreenPlayerRouter.get("/activity/detail/{activity_id}", summary="查询活动大屏详情")
async def player_activity_detail_controller(
    activity_id: int,
    db: Annotated[AsyncSession, Depends(db_getter)],
    device: Annotated[ScreenDeviceModel, Depends(get_screen_device)],
) -> JSONResponse:
    result = await ScreenService.player_activity_detail(db, device, activity_id)
    return SuccessResponse(data=result, msg="查询活动大屏详情成功")


@ScreenPlayerRouter.get("/activity/{activity_id}/participants", summary="查询活动大屏签到数据")
async def player_activity_participants_controller(
    activity_id: int,
    db: Annotated[AsyncSession, Depends(db_getter)],
    device: Annotated[ScreenDeviceModel, Depends(get_screen_device)],
) -> JSONResponse:
    result = await ScreenService.activity_participants(db, activity_id)
    return SuccessResponse(data=result, msg="查询活动签到数据成功")


@ScreenAdminRouter.get("/device/list", summary="查询大屏设备列表")
async def admin_device_list_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:device:query"], check_data_scope=False))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[ScreenDeviceQueryParam, Depends()],
) -> JSONResponse:
    result = await ScreenService.page_devices(auth, page.page_no, page.page_size, search)
    return SuccessResponse(data=result, msg="查询大屏设备列表成功")


@ScreenAdminRouter.get("/activity/list", summary="查询活动大屏列表")
async def admin_activity_list_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:activity:query"], check_data_scope=False))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[ScreenActivityQueryParam, Depends()],
) -> JSONResponse:
    result = await ScreenService.page_activities(auth, page.page_no, page.page_size, search)
    return SuccessResponse(data=result, msg="查询活动大屏列表成功")


@ScreenAdminRouter.get("/activity/detail/{activity_id}", summary="查询活动大屏详情")
async def admin_activity_detail_controller(
    activity_id: int,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:activity:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.detail_activity(auth.db, activity_id)
    return SuccessResponse(data=result, msg="查询活动大屏详情成功")


@ScreenAdminRouter.post("/activity/create", summary="创建活动大屏")
async def admin_activity_create_controller(
    data: ScreenActivityConfigSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:activity:create"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.create_activity(auth, data)
    return SuccessResponse(data=result, msg="创建活动大屏成功")


@ScreenAdminRouter.put("/activity/update/{activity_id}", summary="修改活动大屏")
async def admin_activity_update_controller(
    activity_id: int,
    data: ScreenActivityConfigSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:activity:update"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.update_activity(auth, activity_id, data)
    return SuccessResponse(data=result, msg="修改活动大屏成功")


@ScreenAdminRouter.delete("/activity/delete/{activity_id}", summary="删除活动大屏")
async def admin_activity_delete_controller(
    activity_id: int,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:activity:delete"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.delete_activity(auth, activity_id)
    return SuccessResponse(data=result, msg="删除活动大屏成功")


@ScreenAdminRouter.delete("/activity/delete", summary="批量删除活动大屏")
async def admin_activity_batch_delete_controller(
    ids: Annotated[list[int], Body(description="活动大屏ID列表")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:activity:delete"], check_data_scope=False))],
) -> JSONResponse:
    for activity_id in ids:
        await ScreenService.delete_activity(auth, activity_id)
    return SuccessResponse(data={"ids": ids}, msg="删除活动大屏成功")


@ScreenAdminRouter.post("/activity/{activity_id}/qrcode/regenerate", summary="重新生成活动大屏签到码")
async def admin_activity_qrcode_regenerate_controller(
    activity_id: int,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:activity:update"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.regenerate_activity_qrcode(auth, activity_id)
    return SuccessResponse(data=result, msg="生成活动签到码成功")


@ScreenAdminRouter.post("/activity/{activity_id}/control-token", summary="生成活动大屏手机控制台链接")
async def admin_activity_control_token_controller(
    activity_id: int,
    request: Request,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:activity:remote"], check_data_scope=False))],
    redis: Annotated[Redis, Depends(redis_getter)],
) -> JSONResponse:
    origin = request.headers.get("origin") or f"{request.url.scheme}://{request.url.netloc}"
    result = await ScreenService.create_activity_control_token(auth, redis, activity_id, origin)
    return SuccessResponse(data=result, msg="控制台链接已生成")


@ScreenAdminRouter.get("/activity/barrage/settings", summary="查询活动大屏普通弹幕配置")
async def admin_activity_barrage_settings_detail_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:activity:barrage:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.activity_barrage_settings(auth.db)
    return SuccessResponse(data=result, msg="查询普通弹幕配置成功")


@ScreenAdminRouter.put("/activity/barrage/settings", summary="修改活动大屏普通弹幕配置")
async def admin_activity_barrage_settings_update_controller(
    data: ScreenActivityBarrageSettingsSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:activity:barrage:update"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.update_activity_barrage_settings(auth, data)
    return SuccessResponse(data=result, msg="普通弹幕配置已保存")


@ScreenAdminRouter.get("/activity/qrcode/settings", summary="查询活动大屏签到二维码配置")
async def admin_activity_qrcode_settings_detail_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:activity:qrcode:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.activity_qrcode_settings(auth.db)
    return SuccessResponse(data=result, msg="查询签到二维码配置成功")


@ScreenAdminRouter.put("/activity/qrcode/settings", summary="修改活动大屏签到二维码配置")
async def admin_activity_qrcode_settings_update_controller(
    data: ScreenActivityQrcodeSettingsSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:activity:qrcode:update"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.update_activity_qrcode_settings(auth, data)
    return SuccessResponse(data=result, msg="签到二维码配置已保存")


@ScreenAdminRouter.get("/activity/checkin-wall/settings", summary="查询活动大屏签到墙配置")
async def admin_activity_checkin_wall_settings_detail_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:activity:checkin_wall:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.activity_checkin_wall_settings(auth.db)
    return SuccessResponse(data=result, msg="查询签到墙配置成功")


@ScreenAdminRouter.put("/activity/checkin-wall/settings", summary="修改活动大屏签到墙配置")
async def admin_activity_checkin_wall_settings_update_controller(
    data: ScreenActivityCheckinWallSettingsSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:activity:checkin_wall:update"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.update_activity_checkin_wall_settings(auth, data)
    return SuccessResponse(data=result, msg="签到墙配置已保存")


@ScreenAdminRouter.get("/activity/dominate/settings", summary="查询活动大屏头像霸屏配置")
async def admin_activity_dominate_settings_detail_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:activity:dominate:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.activity_dominate_settings(auth.db)
    return SuccessResponse(data=result, msg="查询头像霸屏配置成功")


@ScreenAdminRouter.put("/activity/dominate/settings", summary="修改活动大屏头像霸屏配置")
async def admin_activity_dominate_settings_update_controller(
    data: ScreenActivityDominateSettingsSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:activity:dominate:update"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.update_activity_dominate_settings(auth, data)
    return SuccessResponse(data=result, msg="头像霸屏配置已保存")


@ScreenAdminRouter.get("/activity/music/settings", summary="查询活动大屏背景音乐配置")
async def admin_activity_music_settings_detail_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:activity:music:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.activity_music_settings(auth.db)
    return SuccessResponse(data=result, msg="查询背景音乐配置成功")


@ScreenAdminRouter.put("/activity/music/settings", summary="修改活动大屏背景音乐配置")
async def admin_activity_music_settings_update_controller(
    data: ScreenActivityMusicSettingsSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:activity:music:update"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.update_activity_music_settings(auth, data)
    return SuccessResponse(data=result, msg="背景音乐配置已保存")


@ScreenAdminRouter.post("/activity/{activity_id}/command", summary="发送活动大屏遥控命令")
async def admin_activity_command_controller(
    activity_id: int,
    data: ScreenActivityCommandSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:activity:remote"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.activity_command(auth, activity_id, data)
    from .ws import activity_ws_manager

    await activity_ws_manager.broadcast(activity_id, {"type": data.command, "payload": result})
    return SuccessResponse(data=result, msg="活动大屏命令发送成功")


@ScreenAdminRouter.get("/activity/{activity_id}/participants", summary="查询活动大屏签到数据")
async def admin_activity_participants_controller(
    activity_id: int,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:activity:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.activity_participants(auth.db, activity_id)
    return SuccessResponse(data=result, msg="查询活动签到数据成功")


@ScreenControlRouter.get("/activity", summary="查询手机控制台活动状态")
async def control_activity_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
    redis: Annotated[Redis, Depends(redis_getter)],
    authorization: Annotated[str | None, Header()] = None,
    x_screen_control_token: Annotated[str | None, Header()] = None,
) -> JSONResponse:
    token = _control_token(authorization, x_screen_control_token)
    result = await ScreenService.control_activity_detail(db, redis, token)
    return SuccessResponse(data=result, msg="查询活动控制台成功")


@ScreenControlRouter.post("/activity/command", summary="手机控制台发送活动大屏命令")
async def control_activity_command_controller(
    data: ScreenActivityCommandSchema,
    db: Annotated[AsyncSession, Depends(db_getter)],
    redis: Annotated[Redis, Depends(redis_getter)],
    authorization: Annotated[str | None, Header()] = None,
    x_screen_control_token: Annotated[str | None, Header()] = None,
) -> JSONResponse:
    token = _control_token(authorization, x_screen_control_token)
    result = await ScreenService.control_activity_command(db, redis, token, data)
    from .ws import activity_ws_manager

    await activity_ws_manager.broadcast(result["id"], {"type": data.command, "payload": result})
    return SuccessResponse(data=result, msg="活动大屏命令发送成功")


@ScreenAdminRouter.post("/device/bind", summary="绑定大屏设备")
async def admin_device_bind_controller(
    data: ScreenDeviceBindSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:device:bind"], check_data_scope=False))],
    redis: Annotated[Redis, Depends(redis_getter)],
) -> JSONResponse:
    result = await ScreenService.bind_device(auth, redis, data)
    return SuccessResponse(data=result, msg="绑定大屏设备成功")


@ScreenAdminRouter.post("/device/{device_id}/unbind", summary="解绑大屏设备")
async def admin_device_unbind_controller(
    device_id: int,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:device:unbind"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.unbind_device(auth, device_id)
    return SuccessResponse(data=result, msg="解绑大屏设备成功")


@ScreenAdminRouter.delete("/device/{device_id}", summary="删除大屏设备")
async def admin_device_delete_controller(
    device_id: int,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:device:delete"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.delete_device(auth, device_id)
    return SuccessResponse(data=result, msg="删除大屏设备成功")


@ScreenAdminRouter.post("/device/{device_id}/reset-token", summary="重置大屏设备授权")
async def admin_device_reset_token_controller(
    device_id: int,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:device:update"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.reset_device_token(auth, device_id)
    return SuccessResponse(data=result, msg="重置大屏设备授权成功")


@ScreenAdminRouter.get("/user-wall/config", summary="查询用户墙配置")
async def admin_user_wall_config_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:user_wall:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.get_user_wall_config(auth.db)
    return SuccessResponse(data=result, msg="查询用户墙配置成功")


@ScreenAdminRouter.put("/user-wall/config", summary="保存用户墙配置")
async def admin_user_wall_config_update_controller(
    data: ScreenUserWallConfigSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:user_wall:update"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.save_user_wall_config(auth, data)
    return SuccessResponse(data=result, msg="保存用户墙配置成功")


@ScreenAdminRouter.get("/promo/config", summary="查询宣传大屏配置")
async def admin_promo_config_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:promo:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.get_promo_manage(auth.db)
    return SuccessResponse(data=result, msg="查询宣传大屏配置成功")


@ScreenAdminRouter.put("/promo/config", summary="保存宣传大屏配置")
async def admin_promo_config_update_controller(
    data: ScreenPromoConfigSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:promo:update"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.save_promo_config(auth, data)
    return SuccessResponse(data=result, msg="保存宣传大屏配置成功")


@ScreenAdminRouter.post("/promo/staff", summary="新增宣传大屏员工资料")
async def admin_promo_staff_create_controller(
    data: ScreenPromoStaffSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:promo:create"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.create_promo_staff(auth, data)
    return SuccessResponse(data=result, msg="新增宣传大屏员工资料成功")


@ScreenAdminRouter.put("/promo/staff/{staff_id}", summary="修改宣传大屏员工资料")
async def admin_promo_staff_update_controller(
    staff_id: int,
    data: ScreenPromoStaffSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:promo:update"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.update_promo_staff(auth, staff_id, data)
    return SuccessResponse(data=result, msg="修改宣传大屏员工资料成功")


@ScreenAdminRouter.delete("/promo/staff/{staff_id}", summary="删除宣传大屏员工资料")
async def admin_promo_staff_delete_controller(
    staff_id: int,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:promo:delete"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.delete_promo_staff(auth, staff_id)
    return SuccessResponse(data=result, msg="删除宣传大屏员工资料成功")


@ScreenAdminRouter.post("/promo/item", summary="新增宣传大屏播放项")
async def admin_promo_item_create_controller(
    data: ScreenPromoItemSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:promo:create"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.create_promo_item(auth, data)
    return SuccessResponse(data=result, msg="新增宣传大屏播放项成功")


@ScreenAdminRouter.put("/promo/item/{item_id}", summary="修改宣传大屏播放项")
async def admin_promo_item_update_controller(
    item_id: int,
    data: ScreenPromoItemSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:promo:update"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.update_promo_item(auth, item_id, data)
    return SuccessResponse(data=result, msg="修改宣传大屏播放项成功")


@ScreenAdminRouter.delete("/promo/item/{item_id}", summary="删除宣传大屏播放项")
async def admin_promo_item_delete_controller(
    item_id: int,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:promo:delete"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.delete_promo_item(auth, item_id)
    return SuccessResponse(data=result, msg="删除宣传大屏播放项成功")


@ScreenAdminRouter.post("/promo/item/sort", summary="调整宣传大屏播放顺序")
async def admin_promo_item_sort_controller(
    data: ScreenPromoSortSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["screen:promo:sort"], check_data_scope=False))],
) -> JSONResponse:
    result = await ScreenService.sort_promo_items(auth, data)
    return SuccessResponse(data=result, msg="调整宣传大屏播放顺序成功")
