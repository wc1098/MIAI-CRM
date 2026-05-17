from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.dependencies import AuthPermission

from ..schema import SubscriptionAdminQueryParam, SubscriptionPlanUpsertSchema
from ..service import SubscriptionAdminService, SubscriptionService

SubscriptionAdminRouter = APIRouter(prefix="/admin", tags=["订阅后台管理"])


@SubscriptionAdminRouter.get("/plans/list", summary="订阅方案列表")
async def admin_subscription_plans_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:subscription:query"]))],
) -> JSONResponse:
    result = await SubscriptionAdminService.list_plans(auth.db)
    return SuccessResponse(data=result, msg="获取订阅方案成功")


@SubscriptionAdminRouter.post("/plans", summary="新增订阅方案")
async def admin_subscription_plan_create_controller(
    data: SubscriptionPlanUpsertSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:subscription:settings"]))],
) -> JSONResponse:
    result = await SubscriptionAdminService.save_plan(auth.db, data)
    return SuccessResponse(data=result, msg="保存订阅方案成功")


@SubscriptionAdminRouter.put("/plans/{plan_id}", summary="修改订阅方案")
async def admin_subscription_plan_update_controller(
    plan_id: int,
    data: SubscriptionPlanUpsertSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:subscription:settings"]))],
) -> JSONResponse:
    result = await SubscriptionAdminService.save_plan(auth.db, data, plan_id)
    return SuccessResponse(data=result, msg="保存订阅方案成功")


@SubscriptionAdminRouter.get("/subscriptions/list", summary="用户订阅列表")
async def admin_subscription_users_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:subscription:query"]))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[SubscriptionAdminQueryParam, Depends()],
) -> JSONResponse:
    result = await SubscriptionAdminService.page_subscriptions(auth.db, page.page_no, page.page_size, search)
    return SuccessResponse(data=result, msg="获取用户订阅成功")


@SubscriptionAdminRouter.get("/recommendations/list", summary="订阅推荐记录")
async def admin_subscription_recommendations_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:subscription:query"]))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[SubscriptionAdminQueryParam, Depends()],
) -> JSONResponse:
    result = await SubscriptionAdminService.page_recommendations(auth.db, page.page_no, page.page_size, search)
    return SuccessResponse(data=result, msg="获取订阅推荐记录成功")


@SubscriptionAdminRouter.post("/recommendations/{recommendation_id}/rematch", summary="重新匹配订阅槽位")
async def admin_subscription_rematch_controller(
    recommendation_id: int,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:subscription:settings"]))],
) -> JSONResponse:
    result = await SubscriptionService.process_recommendation(auth.db, recommendation_id, force=True)
    return SuccessResponse(data=result, msg="已触发重新匹配")
