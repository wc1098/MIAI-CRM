from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .schema import (
    PersonInterviewOutSchema,
    PersonInterviewSaveSchema,
    PersonInterviewVoidSchema,
    PersonDetailOutSchema,
    PersonListOutSchema,
    PersonProfileInsightOutSchema,
    PersonProfileInsightSaveSchema,
    PersonQualitySchema,
    PersonQueryParam,
    PersonStoreOptionSchema,
    PersonTimelineOutSchema,
    PersonUserOptionSchema,
    SensitiveLogOutSchema,
    SensitiveViewSchema,
)
from .insight_service import PersonInsightService
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


@PersonRouter.get("/store-options", summary="查询资源中心门店筛选项", response_model=ResponseSchema[list[PersonStoreOptionSchema]])
async def store_options_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:person:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await PersonCenterService.store_options_service(auth=auth)
    return SuccessResponse(data=result, msg="查询资源中心门店筛选项成功")


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


@PersonRouter.get("/{person_id}/interviews", summary="查询人员深访记录", response_model=ResponseSchema[list[PersonInterviewOutSchema]])
async def list_person_interviews_controller(
    person_id: Annotated[int, Path(description="Person ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:person:interview:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await PersonInsightService.list_interviews_service(auth=auth, person_id=person_id)
    return SuccessResponse(data=result, msg="查询人员深访记录成功")


@PersonRouter.post("/{person_id}/interviews", summary="新增人员深访", response_model=ResponseSchema[PersonInterviewOutSchema])
async def create_person_interview_controller(
    data: PersonInterviewSaveSchema,
    person_id: Annotated[int, Path(description="Person ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:person:interview:create"], check_data_scope=False))],
) -> JSONResponse:
    result = await PersonInsightService.create_interview_service(auth=auth, person_id=person_id, data=data)
    return SuccessResponse(data=result, msg="人员深访已保存")


@PersonRouter.get("/{person_id}/interviews/{interview_id}", summary="查询人员深访详情", response_model=ResponseSchema[PersonInterviewOutSchema])
async def get_person_interview_controller(
    person_id: Annotated[int, Path(description="Person ID")],
    interview_id: Annotated[int, Path(description="深访ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:person:interview:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await PersonInsightService.get_interview_service(auth=auth, person_id=person_id, interview_id=interview_id)
    return SuccessResponse(data=result, msg="查询人员深访详情成功")


@PersonRouter.put("/{person_id}/interviews/{interview_id}", summary="编辑人员深访", response_model=ResponseSchema[PersonInterviewOutSchema])
async def update_person_interview_controller(
    data: PersonInterviewSaveSchema,
    person_id: Annotated[int, Path(description="Person ID")],
    interview_id: Annotated[int, Path(description="深访ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:person:interview:update"], check_data_scope=False))],
) -> JSONResponse:
    result = await PersonInsightService.update_interview_service(auth=auth, person_id=person_id, interview_id=interview_id, data=data)
    return SuccessResponse(data=result, msg="人员深访已更新")


@PersonRouter.post("/{person_id}/interviews/{interview_id}/void", summary="作废人员深访", response_model=ResponseSchema[PersonInterviewOutSchema])
async def void_person_interview_controller(
    data: PersonInterviewVoidSchema,
    person_id: Annotated[int, Path(description="Person ID")],
    interview_id: Annotated[int, Path(description="深访ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:person:interview:void"], check_data_scope=False))],
) -> JSONResponse:
    result = await PersonInsightService.void_interview_service(auth=auth, person_id=person_id, interview_id=interview_id, data=data)
    return SuccessResponse(data=result, msg="人员深访已作废")


@PersonRouter.get("/{person_id}/profile-insight", summary="查询人员当前深访画像", response_model=ResponseSchema[PersonProfileInsightOutSchema | None])
async def get_person_profile_insight_controller(
    person_id: Annotated[int, Path(description="Person ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:person:profile_insight:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await PersonInsightService.profile_insight_service(auth=auth, person_id=person_id)
    return SuccessResponse(data=result, msg="查询人员当前深访画像成功")


@PersonRouter.put("/{person_id}/profile-insight", summary="编辑人员当前深访画像", response_model=ResponseSchema[PersonProfileInsightOutSchema])
async def update_person_profile_insight_controller(
    data: PersonProfileInsightSaveSchema,
    person_id: Annotated[int, Path(description="Person ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:person:profile_insight:update"], check_data_scope=False))],
) -> JSONResponse:
    result = await PersonInsightService.update_profile_insight_service(auth=auth, person_id=person_id, data=data)
    return SuccessResponse(data=result, msg="人员当前深访画像已更新")
