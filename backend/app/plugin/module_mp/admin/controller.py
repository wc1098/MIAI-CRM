from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.dependencies import AuthPermission

from .schema import (
    MpActionQueryParam,
    MpCouponGrantSchema,
    MpCouponQueryParam,
    MpOperationSettingsSchema,
    MpQuestionUpsertSchema,
    MpTaskUpsertSchema,
    MpUnlockRecordQueryParam,
    MpUnlockRevokeSchema,
    MpUserProfileUpdateSchema,
    MpUserQueryParam,
)
from .service import MpAdminService

MpAdminRouter = APIRouter(prefix="/admin/user", tags=["小程序后台用户管理"])


@MpAdminRouter.get("/list", summary="小程序注册用户列表")
async def list_user_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:query"]))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[MpUserQueryParam, Depends()],
) -> JSONResponse:
    result = await MpAdminService.page_users(
        db=auth.db,
        page_no=page.page_no,
        page_size=page.page_size,
        search=search,
    )
    return SuccessResponse(data=result, msg="获取小程序注册用户成功")


@MpAdminRouter.get("/detail/{user_id}", summary="小程序注册用户详情")
async def detail_user_controller(
    user_id: int,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:detail"]))],
) -> JSONResponse:
    result = await MpAdminService.detail_user(db=auth.db, user_id=user_id)
    return SuccessResponse(data=result, msg="获取小程序注册用户详情成功")


@MpAdminRouter.put("/{user_id}/profile", summary="更新小程序用户资料")
async def update_user_profile_controller(
    user_id: int,
    data: MpUserProfileUpdateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:update"]))],
) -> JSONResponse:
    result = await MpAdminService.update_user_profile(auth=auth, user_id=user_id, data=data)
    return SuccessResponse(data=result, msg="保存小程序用户资料成功")


@MpAdminRouter.get("/settings", summary="小程序运营设置")
async def settings_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:settings"]))],
) -> JSONResponse:
    result = await MpAdminService.get_settings(db=auth.db)
    return SuccessResponse(data=result, msg="获取小程序运营设置成功")


@MpAdminRouter.put("/settings", summary="保存小程序运营设置")
async def update_settings_controller(
    data: MpOperationSettingsSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:settings"]))],
) -> JSONResponse:
    result = await MpAdminService.update_settings(db=auth.db, data=data)
    return SuccessResponse(data=result, msg="保存小程序运营设置成功")


@MpAdminRouter.get("/actions/list", summary="小程序用户行为记录")
async def action_list_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:action:query"]))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[MpActionQueryParam, Depends()],
) -> JSONResponse:
    result = await MpAdminService.page_actions(auth.db, page.page_no, page.page_size, search)
    return SuccessResponse(data=result, msg="获取小程序行为记录成功")


@MpAdminRouter.get("/coupons/list", summary="小程序免费券列表")
async def coupon_list_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:coupon:query"]))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[MpCouponQueryParam, Depends()],
) -> JSONResponse:
    result = await MpAdminService.page_coupons(auth.db, page.page_no, page.page_size, search)
    return SuccessResponse(data=result, msg="获取小程序免费券成功")


@MpAdminRouter.post("/coupons/grant", summary="发放小程序免费券")
async def coupon_grant_controller(
    data: MpCouponGrantSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:coupon:grant"]))],
) -> JSONResponse:
    result = await MpAdminService.grant_coupon(auth.db, data)
    return SuccessResponse(data=result, msg="发放免费券成功")


@MpAdminRouter.get("/tasks/list", summary="小程序解锁任务配置")
async def task_list_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:settings"]))],
) -> JSONResponse:
    result = await MpAdminService.list_tasks(auth.db)
    return SuccessResponse(data=result, msg="获取解锁任务成功")


@MpAdminRouter.post("/tasks", summary="新增小程序解锁任务")
async def task_create_controller(
    data: MpTaskUpsertSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:settings"]))],
) -> JSONResponse:
    result = await MpAdminService.save_task(auth.db, data)
    return SuccessResponse(data=result, msg="保存解锁任务成功")


@MpAdminRouter.put("/tasks/{task_id}", summary="修改小程序解锁任务")
async def task_update_controller(
    task_id: int,
    data: MpTaskUpsertSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:settings"]))],
) -> JSONResponse:
    result = await MpAdminService.save_task(auth.db, data, task_id)
    return SuccessResponse(data=result, msg="保存解锁任务成功")


@MpAdminRouter.get("/questions/list", summary="小程序默契题配置")
async def question_list_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:settings"]))],
) -> JSONResponse:
    result = await MpAdminService.list_questions(auth.db)
    return SuccessResponse(data=result, msg="获取默契题成功")


@MpAdminRouter.post("/questions", summary="新增小程序默契题")
async def question_create_controller(
    data: MpQuestionUpsertSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:settings"]))],
) -> JSONResponse:
    result = await MpAdminService.save_question(auth.db, data)
    return SuccessResponse(data=result, msg="保存默契题成功")


@MpAdminRouter.put("/questions/{question_id}", summary="修改小程序默契题")
async def question_update_controller(
    question_id: int,
    data: MpQuestionUpsertSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:settings"]))],
) -> JSONResponse:
    result = await MpAdminService.save_question(auth.db, data, question_id)
    return SuccessResponse(data=result, msg="保存默契题成功")


@MpAdminRouter.get("/unlock-records/list", summary="小程序联系方式解锁记录")
async def unlock_record_list_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:action:query"]))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[MpUnlockRecordQueryParam, Depends()],
) -> JSONResponse:
    result = await MpAdminService.page_unlock_records(auth.db, page.page_no, page.page_size, search)
    return SuccessResponse(data=result, msg="获取解锁记录成功")


@MpAdminRouter.put("/unlock-records/{unlock_id}/status", summary="撤销或屏蔽小程序联系方式解锁记录")
async def unlock_record_revoke_controller(
    unlock_id: int,
    data: MpUnlockRevokeSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:settings"]))],
) -> JSONResponse:
    result = await MpAdminService.revoke_unlock_record(auth.db, unlock_id, data, auth.user.id if auth.user else None)
    return SuccessResponse(data=result, msg="处理解锁记录成功")


@MpAdminRouter.get("/contact-views/list", summary="小程序手机号查看日志")
async def contact_view_list_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:action:query"]))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[MpUnlockRecordQueryParam, Depends()],
) -> JSONResponse:
    result = await MpAdminService.page_contact_views(auth.db, page.page_no, page.page_size, search)
    return SuccessResponse(data=result, msg="获取手机号查看日志成功")
