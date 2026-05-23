from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.dependencies import AuthPermission
from app.core.logger import log
from app.core.router_class import OperationLogRoute
from app.plugin.module_crm.customer.schema import (
    CustomerCertificationMaterialSaveSchema,
    CustomerUpdateSchema,
)

from .schema import (
    CandidateAddExistingSchema,
    CandidateCreateSchema,
    CandidateDiscoverOutSchema,
    CandidateDiscoverSchema,
    CandidateJoinRequestCreateSchema,
    CandidateJoinRequestOutSchema,
    CandidateJoinRequestQueryParam,
    CandidateJoinRequestReviewSchema,
    CandidateOutSchema,
    CandidateQueryParam,
    CandidateRuleSchema,
    CandidateRuleUpdateSchema,
    CloseApplySchema,
    CloseReviewSchema,
    DeepInterviewCreateSchema,
    DeepInterviewOutSchema,
    EntitlementOutSchema,
    MatchmakerOptionSchema,
    PersonSearchOutSchema,
    ReopenSchema,
    ServiceCertificationOutSchema,
    ServiceContractOutSchema,
    ServiceCustomerProcessCreateSchema,
    ServiceCustomerProfileOutSchema,
    ServiceLifecycleOutSchema,
    ServiceTimelineOutSchema,
    ServiceWorkSummaryOutSchema,
    UsageCreateSchema,
    UsageOutSchema,
    UsageVoidSchema,
    VipAssignSchema,
    VipDetailOutSchema,
    VipOutSchema,
    VipQueryParam,
)
from .service import CandidateService, VipService

VipRouter = APIRouter(route_class=OperationLogRoute, prefix="/vip", tags=["VIP服务"])
CandidateRouter = APIRouter(route_class=OperationLogRoute, prefix="/candidate", tags=["候选备选库"])


@VipRouter.get(
    "/pending-assign",
    summary="查询VIP待分配服务池",
    description="查询VIP待分配服务池",
    response_model=ResponseSchema[list[VipOutSchema]],
)
async def get_pending_assign_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[VipQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:query"]))],
) -> JSONResponse:
    result_dict = await VipService.page_service(
        auth=auth,
        page_no=page.page_no,
        page_size=page.page_size,
        search=search,
        pending_only=True,
    )
    log.info("查询VIP待分配服务池成功")
    return SuccessResponse(data=result_dict, msg="查询VIP待分配服务池成功")


@VipRouter.get(
    "/list",
    summary="查询VIP列表",
    description="查询VIP列表",
    response_model=ResponseSchema[list[VipOutSchema]],
)
async def get_vip_list_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[VipQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:query"]))],
) -> JSONResponse:
    result_dict = await VipService.page_service(
        auth=auth,
        page_no=page.page_no,
        page_size=page.page_size,
        search=search,
        pending_only=False,
    )
    log.info("查询VIP列表成功")
    return SuccessResponse(data=result_dict, msg="查询VIP列表成功")


@VipRouter.get(
    "/detail/{id}",
    summary="查询VIP详情",
    description="查询VIP详情",
    response_model=ResponseSchema[VipDetailOutSchema],
)
async def get_vip_detail_controller(
    id: Annotated[int, Path(description="VIP服务ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:detail"]))],
) -> JSONResponse:
    result_dict = await VipService.detail_service(auth=auth, vip_id=id)
    log.info(f"查询VIP详情成功: {id}")
    return SuccessResponse(data=result_dict, msg="查询VIP详情成功")


@VipRouter.get(
    "/entitlements/{id}",
    summary="查询服务权益账本",
    response_model=ResponseSchema[list[EntitlementOutSchema]],
)
async def get_entitlements_controller(
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:detail"]))],
) -> JSONResponse:
    result_dict = await VipService.entitlements_service(auth=auth, case_id=id)
    return SuccessResponse(data=result_dict, msg="查询服务权益账本成功")


@VipRouter.post(
    "/usage/{id}",
    summary="新增服务权益核销",
    response_model=ResponseSchema[UsageOutSchema],
)
async def create_usage_controller(
    data: UsageCreateSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:update"]))],
) -> JSONResponse:
    result_dict = await VipService.create_usage_service(auth=auth, case_id=id, data=data)
    return SuccessResponse(data=result_dict, msg="新增服务权益核销成功")


@VipRouter.delete(
    "/usage/{id}/{usage_id}",
    summary="作废服务权益核销",
    response_model=ResponseSchema[UsageOutSchema],
)
async def void_usage_controller(
    data: UsageVoidSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    usage_id: Annotated[int, Path(description="核销记录ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:meeting:rollback"]))],
) -> JSONResponse:
    result_dict = await VipService.void_usage_service(auth=auth, case_id=id, usage_id=usage_id, data=data)
    return SuccessResponse(data=result_dict, msg="作废服务权益核销成功")


@VipRouter.post(
    "/interview/{id}",
    summary="新增服务深访",
    response_model=ResponseSchema[DeepInterviewOutSchema],
)
async def create_interview_controller(
    data: DeepInterviewCreateSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:deep_interview"]))],
) -> JSONResponse:
    result_dict = await VipService.create_interview_service(auth=auth, case_id=id, data=data)
    return SuccessResponse(data=result_dict, msg="新增服务深访成功")


@VipRouter.post(
    "/close/apply/{id}",
    summary="申请关单",
    response_model=ResponseSchema[VipOutSchema],
)
async def apply_close_controller(
    data: CloseApplySchema,
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:close"]))],
) -> JSONResponse:
    result_dict = await VipService.apply_close_service(auth=auth, case_id=id, data=data)
    return SuccessResponse(data=result_dict, msg="关单申请已提交")


@VipRouter.post(
    "/close/review/{id}",
    summary="审核关单",
    response_model=ResponseSchema[VipOutSchema],
)
async def review_close_controller(
    data: CloseReviewSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:close"]))],
) -> JSONResponse:
    result_dict = await VipService.review_close_service(auth=auth, case_id=id, data=data)
    return SuccessResponse(data=result_dict, msg="关单审核完成")


@VipRouter.post(
    "/reopen/{id}",
    summary="重开服务工单",
    response_model=ResponseSchema[VipOutSchema],
)
async def reopen_controller(
    data: ReopenSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:reopen"]))],
) -> JSONResponse:
    result_dict = await VipService.reopen_service(auth=auth, case_id=id, data=data)
    return SuccessResponse(data=result_dict, msg="服务工单已重开")


@VipRouter.get(
    "/{id}/customer-profile",
    summary="查询服务客户资料",
    response_model=ResponseSchema[ServiceCustomerProfileOutSchema],
)
async def get_service_customer_profile_controller(
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:detail"]))],
) -> JSONResponse:
    result_dict = await VipService.customer_profile_service(auth=auth, case_id=id)
    return SuccessResponse(data=result_dict, msg="查询服务客户资料成功")


@VipRouter.put(
    "/{id}/customer-profile",
    summary="编辑服务客户资料",
    response_model=ResponseSchema[ServiceCustomerProfileOutSchema],
)
async def update_service_customer_profile_controller(
    data: CustomerUpdateSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:update"]))],
) -> JSONResponse:
    result_dict = await VipService.update_customer_profile_service(auth=auth, case_id=id, data=data)
    return SuccessResponse(data=result_dict, msg="编辑服务客户资料成功")


@VipRouter.get(
    "/{id}/certification",
    summary="查询服务客户认证资料",
    response_model=ResponseSchema[list[ServiceCertificationOutSchema]],
)
async def get_service_certification_controller(
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:detail"]))],
) -> JSONResponse:
    result_dict = await VipService.certification_service(auth=auth, case_id=id)
    return SuccessResponse(data=result_dict, msg="查询服务客户认证资料成功")


@VipRouter.get(
    "/{id}/certification-archive-items",
    summary="查询服务客户认证资料存档项",
)
async def get_service_certification_archive_items_controller(
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:detail"]))],
) -> JSONResponse:
    result_dict = await VipService.certification_archive_items_service(auth=auth, case_id=id)
    return SuccessResponse(data=result_dict, msg="查询服务客户认证资料存档项成功")


@VipRouter.post(
    "/{id}/certification-material",
    summary="新增服务客户认证资料存档",
    response_model=ResponseSchema[ServiceCertificationOutSchema],
)
async def save_service_certification_material_controller(
    data: CustomerCertificationMaterialSaveSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:update"]))],
) -> JSONResponse:
    result_dict = await VipService.save_certification_material_service(auth=auth, case_id=id, data=data)
    return SuccessResponse(data=result_dict, msg="认证资料已存档")


@VipRouter.delete(
    "/{id}/certification-material/{material_id}",
    summary="删除服务客户认证资料存档",
)
async def delete_service_certification_material_controller(
    id: Annotated[int, Path(description="服务工单ID")],
    material_id: Annotated[int, Path(description="资料ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:update"]))],
) -> JSONResponse:
    await VipService.delete_certification_material_service(auth=auth, case_id=id, material_id=material_id)
    return SuccessResponse(msg="认证资料已删除")


@VipRouter.get(
    "/{id}/timeline",
    summary="查询服务客户统一过程时间轴",
    response_model=ResponseSchema[list[ServiceTimelineOutSchema]],
)
async def get_service_timeline_controller(
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:detail"]))],
) -> JSONResponse:
    result_dict = await VipService.timeline_service(auth=auth, case_id=id)
    return SuccessResponse(data=result_dict, msg="查询服务客户统一过程时间轴成功")


@VipRouter.post(
    "/{id}/customer-process-record",
    summary="新增服务客户过程记录",
    response_model=ResponseSchema[ServiceTimelineOutSchema],
)
async def create_service_customer_process_record_controller(
    data: ServiceCustomerProcessCreateSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:process_record"]))],
) -> JSONResponse:
    result_dict = await VipService.create_customer_process_record_service(auth=auth, case_id=id, data=data)
    return SuccessResponse(data=result_dict, msg="客户过程记录已保存")


@VipRouter.post(
    "/{id}/appointment",
    summary="新增服务邀约到店",
    response_model=ResponseSchema[ServiceTimelineOutSchema],
)
async def create_service_appointment_controller(
    data: ServiceCustomerProcessCreateSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:appointment"]))],
) -> JSONResponse:
    result_dict = await VipService.create_appointment_service(auth=auth, case_id=id, data=data)
    return SuccessResponse(data=result_dict, msg="服务邀约已保存")


@VipRouter.get(
    "/{id}/lifecycle",
    summary="查询服务客户生命周期",
    response_model=ResponseSchema[list[ServiceLifecycleOutSchema]],
)
async def get_service_lifecycle_controller(
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:detail"]))],
) -> JSONResponse:
    result_dict = await VipService.lifecycle_service(auth=auth, case_id=id)
    return SuccessResponse(data=result_dict, msg="查询服务客户生命周期成功")


@VipRouter.get(
    "/{id}/contracts",
    summary="查询服务客户合同收款",
    response_model=ResponseSchema[list[ServiceContractOutSchema]],
)
async def get_service_contracts_controller(
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:detail"]))],
) -> JSONResponse:
    result_dict = await VipService.contracts_service(auth=auth, case_id=id)
    return SuccessResponse(data=result_dict, msg="查询服务客户合同收款成功")


@VipRouter.get(
    "/{id}/work-summary",
    summary="查询服务工作小计",
    response_model=ResponseSchema[ServiceWorkSummaryOutSchema],
)
async def get_service_work_summary_controller(
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:detail"]))],
) -> JSONResponse:
    result_dict = await VipService.work_summary_service(auth=auth, case_id=id)
    return SuccessResponse(data=result_dict, msg="查询服务工作小计成功")


@VipRouter.get(
    "/matchmakers",
    summary="查询服务红娘候选",
    description="查询同门店服务红娘候选",
    response_model=ResponseSchema[list[MatchmakerOptionSchema]],
)
async def get_matchmaker_options_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:assign"]))],
    store_id: Annotated[int | None, Query(description="门店ID")] = None,
) -> JSONResponse:
    result_dict = await VipService.matchmaker_options_service(auth=auth, store_id=store_id)
    log.info(f"查询服务红娘候选成功: {store_id}")
    return SuccessResponse(data=result_dict, msg="查询服务红娘候选成功")


@VipRouter.post(
    "/assign/{id}",
    summary="分配VIP服务红娘",
    description="分配VIP服务红娘",
    response_model=ResponseSchema[VipOutSchema],
)
async def assign_vip_controller(
    data: VipAssignSchema,
    id: Annotated[int, Path(description="VIP服务ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:assign"]))],
) -> JSONResponse:
    result_dict = await VipService.assign_service(auth=auth, vip_id=id, data=data)
    log.info(f"分配VIP服务红娘成功: {id}")
    return SuccessResponse(data=result_dict, msg="分配VIP服务红娘成功")


@VipRouter.post(
    "/transfer/{id}",
    summary="改派VIP服务红娘",
    description="改派VIP服务红娘",
    response_model=ResponseSchema[VipOutSchema],
)
async def transfer_vip_controller(
    data: VipAssignSchema,
    id: Annotated[int, Path(description="VIP服务ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:vip:assign"]))],
) -> JSONResponse:
    result_dict = await VipService.transfer_service(auth=auth, vip_id=id, data=data)
    log.info(f"改派VIP服务红娘成功: {id}")
    return SuccessResponse(data=result_dict, msg="改派VIP服务红娘成功")


@CandidateRouter.get(
    "/list",
    summary="查询我的备选库",
    response_model=ResponseSchema[list[CandidateOutSchema]],
)
async def candidate_list_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[CandidateQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:candidate:query"]))],
) -> JSONResponse:
    result_dict = await CandidateService.page_service(auth=auth, page_no=page.page_no, page_size=page.page_size, search=search)
    return SuccessResponse(data=result_dict, msg="查询备选库成功")


@CandidateRouter.get(
    "/person/search",
    summary="搜索本门店备选Person",
    response_model=ResponseSchema[list[PersonSearchOutSchema]],
)
async def person_search_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:candidate:query"]))],
    keyword: Annotated[str | None, Query(description="姓名/手机号/编号")] = None,
    limit: Annotated[int, Query(ge=1, le=50, description="返回条数")] = 20,
) -> JSONResponse:
    result_dict = await CandidateService.search_person_service(auth=auth, keyword=keyword, limit=limit)
    return SuccessResponse(data=result_dict, msg="搜索人员成功")


@CandidateRouter.get(
    "/rule",
    summary="查询备选库规则",
    response_model=ResponseSchema[CandidateRuleSchema],
)
async def candidate_rule_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:candidate:rule:query"]))],
) -> JSONResponse:
    result_dict = await CandidateService.get_rule_service(auth=auth)
    return SuccessResponse(data=result_dict, msg="查询备选库规则成功")


@CandidateRouter.put(
    "/rule",
    summary="设置备选库规则",
    response_model=ResponseSchema[CandidateRuleSchema],
)
async def update_candidate_rule_controller(
    data: CandidateRuleUpdateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:candidate:rule:update"]))],
) -> JSONResponse:
    result_dict = await CandidateService.update_rule_service(auth=auth, data=data)
    return SuccessResponse(data=result_dict, msg="备选库规则已保存")


@CandidateRouter.post(
    "/discover",
    summary="候选发现联合搜索",
    response_model=ResponseSchema[list[CandidateDiscoverOutSchema]],
)
async def candidate_discover_controller(
    data: CandidateDiscoverSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:candidate:discover"]))],
) -> JSONResponse:
    result_dict = await CandidateService.discover_service(auth=auth, data=data)
    return SuccessResponse(data=result_dict, msg="候选发现查询成功")


@CandidateRouter.post(
    "/join-request",
    summary="提交备选库加入申请",
    response_model=ResponseSchema[CandidateJoinRequestOutSchema],
)
async def create_join_request_controller(
    data: CandidateJoinRequestCreateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:candidate:join_request"]))],
) -> JSONResponse:
    result_dict = await CandidateService.create_join_request_service(auth=auth, data=data)
    return SuccessResponse(data=result_dict, msg="加入申请已提交")


@CandidateRouter.get(
    "/join-request/list",
    summary="查询备选库加入申请",
    response_model=ResponseSchema[list[CandidateJoinRequestOutSchema]],
)
async def join_request_list_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[CandidateJoinRequestQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:candidate:join_request:query"]))],
) -> JSONResponse:
    result_dict = await CandidateService.join_request_page_service(auth=auth, page_no=page.page_no, page_size=page.page_size, search=search)
    return SuccessResponse(data=result_dict, msg="查询加入申请成功")


@CandidateRouter.post(
    "/join-request/{id}/review",
    summary="审核备选库加入申请",
    response_model=ResponseSchema[CandidateJoinRequestOutSchema],
)
async def review_join_request_controller(
    data: CandidateJoinRequestReviewSchema,
    id: Annotated[int, Path(description="加入申请ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:candidate:join_request:review"]))],
) -> JSONResponse:
    result_dict = await CandidateService.review_join_request_service(auth=auth, request_id=id, data=data)
    return SuccessResponse(data=result_dict, msg="审核加入申请成功")


@CandidateRouter.post(
    "/add-existing",
    summary="加入已有Person到备选库",
    response_model=ResponseSchema[CandidateOutSchema],
)
async def add_existing_candidate_controller(
    data: CandidateAddExistingSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:candidate:add_backup"]))],
) -> JSONResponse:
    result_dict = await CandidateService.add_existing_service(auth=auth, data=data)
    return SuccessResponse(data=result_dict, msg="加入备选库成功")


@CandidateRouter.post(
    "/manual-create",
    summary="手动新增备选资源",
    response_model=ResponseSchema[CandidateOutSchema],
)
async def manual_create_candidate_controller(
    data: CandidateCreateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:candidate:create"]))],
) -> JSONResponse:
    result_dict = await CandidateService.create_manual_service(auth=auth, data=data)
    return SuccessResponse(data=result_dict, msg="新增备选资源成功")


@CandidateRouter.get(
    "/certification-archive-items",
    summary="查询备选认证资料存档项",
    response_model=ResponseSchema[list[dict]],
)
async def candidate_certification_archive_items_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:candidate:create"]))],
) -> JSONResponse:
    result_list = await CandidateService.certification_archive_items_service(auth=auth)
    return SuccessResponse(data=result_list, msg="查询备选认证资料存档项成功")
