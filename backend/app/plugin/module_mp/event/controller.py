from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.dependencies import db_getter
from app.plugin.module_mp.auth.dependencies import get_current_mp_user_id, get_optional_mp_user_id

from .schema import MpEventBarrageSchema, MpEventCheckinSchema, MpEventRegisterSchema
from .service import MpEventService

MpEventRouter = APIRouter(prefix="/event", tags=["小程序活动"])


@MpEventRouter.get("/list", summary="小程序活动列表", response_model=ResponseSchema[dict])
async def event_list_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int | None, Depends(get_optional_mp_user_id)],
    page_no: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 10,
) -> JSONResponse:
    result = await MpEventService.list_service(db=db, page_no=page_no, page_size=page_size, user_id=user_id)
    return SuccessResponse(data=result, msg="查询活动列表成功")


@MpEventRouter.get("/detail/{event_id}", summary="小程序活动详情", response_model=ResponseSchema[dict])
async def event_detail_controller(
    event_id: Annotated[int, Path(description="活动ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await MpEventService.detail_service(db=db, event_id=event_id)
    return SuccessResponse(data=result, msg="获取活动详情成功")


@MpEventRouter.get("/my-registration/{event_id}", summary="我的活动报名", response_model=ResponseSchema[dict])
async def event_my_registration_controller(
    event_id: Annotated[int, Path(description="活动ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpEventService.detail_service(db=db, event_id=event_id, user_id=user_id)
    return SuccessResponse(data=result.get("my_registration"), msg="获取我的报名成功")


@MpEventRouter.post("/register/{event_id}", summary="小程序活动报名", response_model=ResponseSchema[dict])
async def event_register_controller(
    event_id: Annotated[int, Path(description="活动ID")],
    data: MpEventRegisterSchema,
    request: Request,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpEventService.register_service(db=db, request=request, event_id=event_id, user_id=user_id, data=data)
    return SuccessResponse(data=result, msg="活动报名已提交")


@MpEventRouter.post("/pay/{registration_id}", summary="继续支付活动报名", response_model=ResponseSchema[dict])
async def event_continue_pay_controller(
    registration_id: Annotated[int, Path(description="报名ID")],
    request: Request,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpEventService.continue_pay_service(db=db, request=request, registration_id=registration_id, user_id=user_id)
    return SuccessResponse(data=result, msg="创建支付成功")


@MpEventRouter.post("/checkin/{event_id}", summary="小程序活动签到", response_model=ResponseSchema[dict])
async def event_checkin_controller(
    event_id: Annotated[int, Path(description="活动ID")],
    data: MpEventCheckinSchema,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpEventService.checkin_service(db=db, event_id=event_id, user_id=user_id, data=data)
    return SuccessResponse(data=result, msg="签到成功")


@MpEventRouter.get("/checkin-scene/{scene}", summary="扫码签到上下文", response_model=ResponseSchema[dict])
async def event_checkin_scene_controller(
    scene: Annotated[str, Path(description="活动大屏签到场景值")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int | None, Depends(get_optional_mp_user_id)],
) -> JSONResponse:
    result = await MpEventService.checkin_scene_context_service(db=db, scene=scene, user_id=user_id)
    return SuccessResponse(data=result, msg="获取扫码签到信息成功")


@MpEventRouter.post("/checkin-scan/{scene}", summary="扫码确认签到", response_model=ResponseSchema[dict])
async def event_checkin_scan_controller(
    scene: Annotated[str, Path(description="活动大屏签到场景值")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpEventService.checkin_scan_service(db=db, scene=scene, user_id=user_id)
    return SuccessResponse(data=result, msg="签到成功")


@MpEventRouter.post("/barrage/{event_id}", summary="发送活动弹幕", response_model=ResponseSchema[dict])
async def event_barrage_controller(
    event_id: Annotated[int, Path(description="活动ID")],
    data: MpEventBarrageSchema,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpEventService.barrage_service(db=db, event_id=event_id, user_id=user_id, data=data)
    return SuccessResponse(data=result, msg="发送成功")
