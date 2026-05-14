from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path
from fastapi.responses import JSONResponse

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import ResponseSchema, SuccessResponse
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .schema import EventEffectSchema, EventQueryParam, EventUpsertSchema
from .service import EventAdminService

EventAdminRouter = APIRouter(route_class=OperationLogRoute, prefix="/admin", tags=["活动后台管理"])


@EventAdminRouter.get("/list", summary="活动列表", response_model=ResponseSchema[dict])
async def event_list_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:event:query"]))],
    search: Annotated[EventQueryParam, Depends()],
) -> JSONResponse:
    result = await EventAdminService.list_service(auth=auth, search=search)
    return SuccessResponse(data=result, msg="查询活动列表成功")


@EventAdminRouter.get("/detail/{event_id}", summary="活动详情", response_model=ResponseSchema[dict])
async def event_detail_controller(
    event_id: Annotated[int, Path(description="活动ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:event:detail"]))],
) -> JSONResponse:
    result = await EventAdminService.detail_service(auth=auth, event_id=event_id)
    return SuccessResponse(data=result, msg="获取活动详情成功")


@EventAdminRouter.post("/create", summary="创建活动", response_model=ResponseSchema[dict])
async def event_create_controller(
    data: EventUpsertSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:event:create"]))],
) -> JSONResponse:
    result = await EventAdminService.create_service(auth=auth, data=data)
    return SuccessResponse(data=result, msg="创建活动成功")


@EventAdminRouter.put("/update/{event_id}", summary="编辑活动", response_model=ResponseSchema[dict])
async def event_update_controller(
    event_id: Annotated[int, Path(description="活动ID")],
    data: EventUpsertSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:event:update"]))],
) -> JSONResponse:
    result = await EventAdminService.update_service(auth=auth, event_id=event_id, data=data)
    return SuccessResponse(data=result, msg="编辑活动成功")


@EventAdminRouter.patch("/publish/{event_id}", summary="发布活动", response_model=ResponseSchema[dict])
async def event_publish_controller(
    event_id: Annotated[int, Path(description="活动ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:event:publish"]))],
) -> JSONResponse:
    result = await EventAdminService.publish_service(auth=auth, event_id=event_id)
    return SuccessResponse(data=result, msg="发布活动成功")


@EventAdminRouter.patch("/cancel/{event_id}", summary="取消活动", response_model=ResponseSchema[dict])
async def event_cancel_controller(
    event_id: Annotated[int, Path(description="活动ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:event:publish"]))],
) -> JSONResponse:
    result = await EventAdminService.cancel_service(auth=auth, event_id=event_id)
    return SuccessResponse(data=result, msg="取消活动成功")


@EventAdminRouter.patch("/finish/{event_id}", summary="结束活动", response_model=ResponseSchema[dict])
async def event_finish_controller(
    event_id: Annotated[int, Path(description="活动ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:event:publish"]))],
) -> JSONResponse:
    result = await EventAdminService.finish_service(auth=auth, event_id=event_id)
    return SuccessResponse(data=result, msg="结束活动成功")


@EventAdminRouter.patch("/effect/{event_id}", summary="编辑活动效果", response_model=ResponseSchema[dict])
async def event_effect_controller(
    event_id: Annotated[int, Path(description="活动ID")],
    data: EventEffectSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:event:update"]))],
) -> JSONResponse:
    result = await EventAdminService.effect_service(auth=auth, event_id=event_id, data=data)
    return SuccessResponse(data=result, msg="保存活动效果成功")


@EventAdminRouter.get("/registrations/{event_id}", summary="报名管理", response_model=ResponseSchema[list[dict]])
async def event_registration_list_controller(
    event_id: Annotated[int, Path(description="活动ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:event:detail"]))],
) -> JSONResponse:
    result = await EventAdminService.registration_list_service(auth=auth, event_id=event_id)
    return SuccessResponse(data=result, msg="查询报名列表成功")


@EventAdminRouter.get("/participants/{event_id}", summary="签到管理", response_model=ResponseSchema[list[dict]])
async def event_participant_list_controller(
    event_id: Annotated[int, Path(description="活动ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:event:checkin"]))],
) -> JSONResponse:
    result = await EventAdminService.participant_list_service(auth=auth, event_id=event_id)
    return SuccessResponse(data=result, msg="查询签到列表成功")


@EventAdminRouter.post("/checkin/{registration_id}", summary="后台辅助签到", response_model=ResponseSchema[dict])
async def event_admin_checkin_controller(
    registration_id: Annotated[int, Path(description="报名ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:event:checkin"]))],
) -> JSONResponse:
    result = await EventAdminService.admin_checkin_service(auth=auth, registration_id=registration_id)
    return SuccessResponse(data=result, msg="签到成功")


@EventAdminRouter.delete("/delete", summary="删除活动", response_model=ResponseSchema[None])
async def event_delete_controller(
    ids: Annotated[list[int], Body(description="活动ID列表")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:event:delete"]))],
) -> JSONResponse:
    await EventAdminService.delete_service(auth=auth, ids=ids)
    return SuccessResponse(msg="删除活动成功")
