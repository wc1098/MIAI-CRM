from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .schema import (
    PersonDetailOutSchema,
    PersonListOutSchema,
    PersonQualitySchema,
    PersonQueryParam,
    PersonTimelineOutSchema,
    PersonUserOptionSchema,
    SensitiveLogOutSchema,
    SensitiveViewSchema,
)
from .service import PersonCenterService

PersonRouter = APIRouter(route_class=OperationLogRoute, prefix="/person", tags=["用户资源中心"])


@PersonRouter.get("/list", summary="查询资源总库", response_model=ResponseSchema[list[PersonListOutSchema]])
async def list_person_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[PersonQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:person:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await PersonCenterService.page_service(auth=auth, page_no=page.page_no, page_size=page.page_size, search=search)
    return SuccessResponse(data=result, msg="查询资源总库成功")


@PersonRouter.get("/user-options", summary="查询资源中心人员筛选项", response_model=ResponseSchema[list[PersonUserOptionSchema]])
async def user_options_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:person:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await PersonCenterService.user_options_service(auth=auth)
    return SuccessResponse(data=result, msg="查询资源中心人员筛选项成功")


@PersonRouter.get("/detail/{person_id}", summary="查询资源详情", response_model=ResponseSchema[PersonDetailOutSchema])
async def detail_person_controller(
    person_id: Annotated[int, Path(description="Person ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:person:detail"], check_data_scope=False))],
) -> JSONResponse:
    result = await PersonCenterService.detail_service(auth=auth, person_id=person_id)
    return SuccessResponse(data=result, msg="查询资源详情成功")


@PersonRouter.get("/timeline/{person_id}", summary="查询资源生命周期", response_model=ResponseSchema[list[PersonTimelineOutSchema]])
async def timeline_person_controller(
    person_id: Annotated[int, Path(description="Person ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:person:detail"], check_data_scope=False))],
) -> JSONResponse:
    result = await PersonCenterService.timeline_service(auth=auth, person_id=person_id)
    return SuccessResponse(data=result, msg="查询资源生命周期成功")


@PersonRouter.get("/quality/{person_id}", summary="查询资料质量", response_model=ResponseSchema[PersonQualitySchema])
async def quality_person_controller(
    person_id: Annotated[int, Path(description="Person ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:person:profile_review"], check_data_scope=False))],
) -> JSONResponse:
    result = await PersonCenterService.quality_service(auth=auth, person_id=person_id)
    return SuccessResponse(data=result, msg="查询资料质量成功")


@PersonRouter.post("/phone/view/{person_id}", summary="查看完整手机号")
async def view_phone_controller(
    data: SensitiveViewSchema,
    person_id: Annotated[int, Path(description="Person ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:person:view_phone"], check_data_scope=False))],
) -> JSONResponse:
    result = await PersonCenterService.view_phone_service(auth=auth, person_id=person_id, data=data)
    return SuccessResponse(data=result, msg="查看完整手机号成功")


@PersonRouter.post("/id-card/view/{person_id}", summary="查看完整身份证")
async def view_id_card_controller(
    data: SensitiveViewSchema,
    person_id: Annotated[int, Path(description="Person ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:person:view_id_card"], check_data_scope=False))],
) -> JSONResponse:
    result = await PersonCenterService.view_id_card_service(auth=auth, person_id=person_id, data=data)
    return SuccessResponse(data=result, msg="查看完整身份证成功")


@PersonRouter.get("/sensitive-log/{person_id}", summary="查询敏感访问记录", response_model=ResponseSchema[list[SensitiveLogOutSchema]])
async def sensitive_log_controller(
    person_id: Annotated[int, Path(description="Person ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:person:profile_review"], check_data_scope=False))],
) -> JSONResponse:
    result = await PersonCenterService.sensitive_log_service(auth=auth, person_id=person_id)
    return SuccessResponse(data=result, msg="查询敏感访问记录成功")
