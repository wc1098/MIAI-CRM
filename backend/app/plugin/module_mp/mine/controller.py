from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.dependencies import db_getter
from app.plugin.module_mp.auth.dependencies import get_current_mp_user_id

from .schema import MpMinePrivacyUpdateSchema, MpMineProfileUpdateSchema
from .service import MpMineService

MpMineRouter = APIRouter(prefix="/mine", tags=["小程序我的"])


@MpMineRouter.get("/center", summary="我的首页聚合", response_model=ResponseSchema[dict])
async def mine_center_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpMineService.center(db, user_id)
    return SuccessResponse(data=result, msg="获取我的首页成功")


@MpMineRouter.get("/profile", summary="我的个人资料", response_model=ResponseSchema[dict])
async def mine_profile_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpMineService.profile(db, user_id)
    return SuccessResponse(data=result, msg="获取个人资料成功")


@MpMineRouter.put("/profile", summary="保存我的个人资料", response_model=ResponseSchema[dict])
async def mine_profile_update_controller(
    data: MpMineProfileUpdateSchema,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpMineService.update_profile(db, user_id, data)
    return SuccessResponse(data=result, msg="保存个人资料成功")


@MpMineRouter.put("/privacy", summary="保存我的隐私设置", response_model=ResponseSchema[dict])
async def mine_privacy_update_controller(
    data: MpMinePrivacyUpdateSchema,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpMineService.update_privacy(db, user_id, data)
    return SuccessResponse(data=result, msg="保存隐私设置成功")


@MpMineRouter.get("/likes", summary="我的喜欢列表", response_model=ResponseSchema[dict])
async def mine_likes_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
    type: Annotated[str, Query(pattern="^(received|sent)$")] = "received",
    page_no: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> JSONResponse:
    result = await MpMineService.likes(db, user_id, type, page_no, page_size)
    return SuccessResponse(data=result, msg="获取喜欢列表成功")


@MpMineRouter.get("/favorites", summary="我的收藏列表", response_model=ResponseSchema[dict])
async def mine_favorites_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
    page_no: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> JSONResponse:
    result = await MpMineService.favorites(db, user_id, page_no, page_size)
    return SuccessResponse(data=result, msg="获取收藏列表成功")


@MpMineRouter.get("/unlocks", summary="我的联系方式解锁记录", response_model=ResponseSchema[dict])
async def mine_unlocks_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
    page_no: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> JSONResponse:
    result = await MpMineService.unlocks(db, user_id, page_no, page_size)
    return SuccessResponse(data=result, msg="获取解锁记录成功")


@MpMineRouter.get("/events", summary="我的活动报名", response_model=ResponseSchema[dict])
async def mine_events_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
    page_no: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> JSONResponse:
    result = await MpMineService.events(db, user_id, page_no, page_size)
    return SuccessResponse(data=result, msg="获取我的活动成功")
