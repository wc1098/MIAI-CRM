from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.dependencies import AuthPermission

from .schema import MpUserQueryParam
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
