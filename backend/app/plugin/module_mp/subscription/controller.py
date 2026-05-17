from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.dependencies import db_getter
from app.plugin.module_mp.auth.dependencies import get_current_mp_user_id, get_optional_mp_user_id
from app.plugin.module_subscription.schema import SubscriptionOrderCreateSchema
from app.plugin.module_subscription.service import SubscriptionService

MpSubscriptionRouter = APIRouter(prefix="/subscription", tags=["小程序订阅"])


@MpSubscriptionRouter.get("/plans", summary="小程序订阅方案", response_model=ResponseSchema[dict])
async def mp_subscription_plans_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int | None, Depends(get_optional_mp_user_id)],
) -> JSONResponse:
    result = await SubscriptionService.mp_plans(db, user_id)
    return SuccessResponse(data=result, msg="获取订阅方案成功")


@MpSubscriptionRouter.post("/orders", summary="创建订阅订单", response_model=ResponseSchema[dict])
async def mp_subscription_order_controller(
    data: SubscriptionOrderCreateSchema,
    request: Request,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await SubscriptionService.create_order(db, request, user_id, data.plan_id)
    return SuccessResponse(data=result, msg="订阅订单创建成功")


@MpSubscriptionRouter.post("/orders/{order_id}/pay", summary="继续支付订阅订单", response_model=ResponseSchema[dict])
async def mp_subscription_pay_controller(
    order_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await SubscriptionService.continue_pay(db, request, user_id, order_id)
    return SuccessResponse(data=result, msg="继续支付请求成功")


@MpSubscriptionRouter.get("/me", summary="我的订阅", response_model=ResponseSchema[dict])
async def mp_subscription_me_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int | None, Depends(get_optional_mp_user_id)],
) -> JSONResponse:
    result = await SubscriptionService.mp_me(db, user_id)
    return SuccessResponse(data=result, msg="获取订阅状态成功")


@MpSubscriptionRouter.get("/recommendations", summary="订阅推荐槽位", response_model=ResponseSchema[dict])
async def mp_subscription_recommendations_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await SubscriptionService.mp_recommendations(db, user_id)
    return SuccessResponse(data=result, msg="获取订阅推荐成功")


@MpSubscriptionRouter.get("/recommendations/{recommendation_id}/contact", summary="查看订阅推荐手机号", response_model=ResponseSchema[dict])
async def mp_subscription_contact_controller(
    recommendation_id: int,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await SubscriptionService.contact(db, user_id, recommendation_id)
    return SuccessResponse(data=result, msg="获取手机号成功")
