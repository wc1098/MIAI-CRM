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
    CourseRecordCreateSchema,
    CourseRecordOutSchema,
    CourseRecordRevokeSchema,
    DeepInterviewCreateSchema,
    DeepInterviewOutSchema,
    EntitlementOutSchema,
    MatchCandidateSchema,
    MatchmakerOptionSchema,
    MeetingActionSchema,
    MeetingCreateSchema,
    MeetingFeedbackOutSchema,
    MeetingFeedbackSaveSchema,
    MeetingOutSchema,
    PersonSearchOutSchema,
    RecommendationCreateSchema,
    RecommendationOutSchema,
    RecommendationUpdateSchema,
    ReopenSchema,
    ServiceCertificationOutSchema,
    ServiceContractOutSchema,
    ServiceCustomerProcessCreateSchema,
    ServiceCustomerProfileOutSchema,
    ServiceLifecycleOutSchema,
    ServicePlanItemActionSchema,
    ServicePlanItemOutSchema,
    ServicePlanItemUpdateSchema,
    ServicePlanOutSchema,
    ServicePlanUpdateSchema,
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
    "/{id}/plan",
    summary="查询服务计划",
    response_model=ResponseSchema[ServicePlanOutSchema],
)
async def get_service_plan_controller(
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:plan:view"]))],
) -> JSONResponse:
    result_dict = await VipService.plan_service(auth=auth, case_id=id)
    return SuccessResponse(data=result_dict, msg="查询服务计划成功")


@VipRouter.put(
    "/{id}/plan",
    summary="更新服务计划",
    response_model=ResponseSchema[ServicePlanOutSchema],
)
async def update_service_plan_controller(
    data: ServicePlanUpdateSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:plan:update"]))],
) -> JSONResponse:
    result_dict = await VipService.update_plan_service(auth=auth, case_id=id, data=data)
    return SuccessResponse(data=result_dict, msg="更新服务计划成功")


@VipRouter.post(
    "/{id}/plan/publish",
    summary="发布服务计划",
    response_model=ResponseSchema[ServicePlanOutSchema],
)
async def publish_service_plan_controller(
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:plan:publish"]))],
) -> JSONResponse:
    result_dict = await VipService.publish_plan_service(auth=auth, case_id=id)
    return SuccessResponse(data=result_dict, msg="发布服务计划成功")


@VipRouter.post(
    "/{id}/plan/rebuild-from-entitlements",
    summary="按权益重建服务计划",
    response_model=ResponseSchema[ServicePlanOutSchema],
)
async def rebuild_service_plan_controller(
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:plan:update"]))],
) -> JSONResponse:
    result_dict = await VipService.rebuild_plan_service(auth=auth, case_id=id)
    return SuccessResponse(data=result_dict, msg="服务计划已重建")


@VipRouter.post(
    "/{id}/plan/auto-schedule",
    summary="自动排期未排节点",
    response_model=ResponseSchema[ServicePlanOutSchema],
)
async def auto_schedule_service_plan_controller(
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:plan:update"]))],
) -> JSONResponse:
    result_dict = await VipService.auto_schedule_plan_items_service(auth=auth, case_id=id)
    return SuccessResponse(data=result_dict, msg="服务计划已自动排期")


@VipRouter.get(
    "/{id}/plan/items",
    summary="查询服务计划节点",
    response_model=ResponseSchema[list[ServicePlanItemOutSchema]],
)
async def get_service_plan_items_controller(
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:plan:view"]))],
) -> JSONResponse:
    result_dict = await VipService.plan_items_service(auth=auth, case_id=id)
    return SuccessResponse(data=result_dict, msg="查询服务计划节点成功")


@VipRouter.put(
    "/{id}/plan/items/{item_id}",
    summary="更新服务计划节点",
    response_model=ResponseSchema[ServicePlanItemOutSchema],
)
async def update_service_plan_item_controller(
    data: ServicePlanItemUpdateSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    item_id: Annotated[int, Path(description="计划节点ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:plan:item:update"]))],
) -> JSONResponse:
    result_dict = await VipService.update_plan_item_service(auth=auth, case_id=id, item_id=item_id, data=data)
    return SuccessResponse(data=result_dict, msg="更新服务计划节点成功")


@VipRouter.post(
    "/{id}/plan/items/{item_id}/cancel",
    summary="取消服务计划节点",
    response_model=ResponseSchema[ServicePlanItemOutSchema],
)
async def cancel_service_plan_item_controller(
    data: ServicePlanItemActionSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    item_id: Annotated[int, Path(description="计划节点ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:plan:item:update"]))],
) -> JSONResponse:
    result_dict = await VipService.cancel_plan_item_service(auth=auth, case_id=id, item_id=item_id, data=data)
    return SuccessResponse(data=result_dict, msg="服务计划节点已取消")


@VipRouter.post(
    "/{id}/plan/items/{item_id}/skip",
    summary="跳过服务计划节点",
    response_model=ResponseSchema[ServicePlanItemOutSchema],
)
async def skip_service_plan_item_controller(
    data: ServicePlanItemActionSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    item_id: Annotated[int, Path(description="计划节点ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:plan:item:update"]))],
) -> JSONResponse:
    result_dict = await VipService.skip_plan_item_service(auth=auth, case_id=id, item_id=item_id, data=data)
    return SuccessResponse(data=result_dict, msg="服务计划节点已跳过")


@VipRouter.post(
    "/{id}/plan/items/{item_id}/restore",
    summary="撤销服务计划节点放弃",
    response_model=ResponseSchema[ServicePlanItemOutSchema],
)
async def restore_service_plan_item_controller(
    data: ServicePlanItemActionSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    item_id: Annotated[int, Path(description="计划节点ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:plan:item:update"]))],
) -> JSONResponse:
    result_dict = await VipService.restore_plan_item_service(auth=auth, case_id=id, item_id=item_id, data=data)
    return SuccessResponse(data=result_dict, msg="服务计划节点已恢复")


@VipRouter.post(
    "/{id}/plan/items/{item_id}/match-candidates",
    summary="匹配候选人",
    response_model=ResponseSchema[dict],
)
async def match_candidates_controller(
    data: MatchCandidateSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    item_id: Annotated[int, Path(description="计划节点ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:match:candidate"]))],
) -> JSONResponse:
    result_dict = await VipService.match_candidates_service(auth=auth, case_id=id, item_id=item_id, data=data)
    return SuccessResponse(data=result_dict, msg="匹配候选人成功")


@VipRouter.get(
    "/{id}/candidates/{person_id}",
    summary="查询服务计划候选详情",
    response_model=ResponseSchema[dict],
)
async def get_service_candidate_detail_controller(
    id: Annotated[int, Path(description="服务工单ID")],
    person_id: Annotated[int, Path(description="候选Person ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:match:candidate"]))],
) -> JSONResponse:
    result_dict = await VipService.service_candidate_detail_service(auth=auth, case_id=id, person_id=person_id)
    return SuccessResponse(data=result_dict, msg="查询候选详情成功")


@VipRouter.post(
    "/{id}/recommendations",
    summary="创建服务推荐记录",
    response_model=ResponseSchema[RecommendationOutSchema],
)
async def create_recommendation_controller(
    data: RecommendationCreateSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:recommendation:create"]))],
) -> JSONResponse:
    result_dict = await VipService.create_recommendation_service(auth=auth, case_id=id, data=data)
    return SuccessResponse(data=result_dict, msg="创建服务推荐记录成功")


@VipRouter.get(
    "/{id}/recommendations",
    summary="查询服务推荐记录",
    response_model=ResponseSchema[list[RecommendationOutSchema]],
)
async def get_recommendations_controller(
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:plan:view"]))],
) -> JSONResponse:
    result_dict = await VipService.recommendations_service(auth=auth, case_id=id)
    return SuccessResponse(data=result_dict, msg="查询服务推荐记录成功")


@VipRouter.put(
    "/{id}/recommendations/{recommendation_id}",
    summary="更新服务推荐记录",
    response_model=ResponseSchema[RecommendationOutSchema],
)
async def update_recommendation_controller(
    data: RecommendationUpdateSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    recommendation_id: Annotated[int, Path(description="推荐记录ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:recommendation:update"]))],
) -> JSONResponse:
    result_dict = await VipService.update_recommendation_service(auth=auth, case_id=id, recommendation_id=recommendation_id, data=data)
    return SuccessResponse(data=result_dict, msg="更新服务推荐记录成功")


@VipRouter.post(
    "/{id}/recommendations/{recommendation_id}/revoke",
    summary="撤销服务推荐记录",
    response_model=ResponseSchema[RecommendationOutSchema],
)
async def revoke_recommendation_controller(
    data: ServicePlanItemActionSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    recommendation_id: Annotated[int, Path(description="推荐记录ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:recommendation:update"]))],
) -> JSONResponse:
    result_dict = await VipService.revoke_recommendation_service(auth=auth, case_id=id, recommendation_id=recommendation_id, data=data)
    return SuccessResponse(data=result_dict, msg="推荐记录已撤销")


@VipRouter.post(
    "/{id}/recommendations/{recommendation_id}/consume",
    summary="核销服务推荐权益",
    response_model=ResponseSchema[RecommendationOutSchema],
)
async def consume_recommendation_controller(
    data: ServicePlanItemActionSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    recommendation_id: Annotated[int, Path(description="推荐记录ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:recommendation:update"]))],
) -> JSONResponse:
    result_dict = await VipService.consume_recommendation_service(auth=auth, case_id=id, recommendation_id=recommendation_id, data=data)
    return SuccessResponse(data=result_dict, msg="推荐权益已核销")


@VipRouter.post(
    "/{id}/meetings",
    summary="创建相亲约见",
    response_model=ResponseSchema[MeetingOutSchema],
)
async def create_meeting_controller(
    data: MeetingCreateSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:meeting:create"]))],
) -> JSONResponse:
    result_dict = await VipService.create_meeting_service(auth=auth, case_id=id, data=data)
    return SuccessResponse(data=result_dict, msg="创建相亲约见成功")


@VipRouter.get(
    "/{id}/meetings",
    summary="查询相亲约见",
    response_model=ResponseSchema[list[MeetingOutSchema]],
)
async def get_meetings_controller(
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:plan:view"]))],
) -> JSONResponse:
    result_dict = await VipService.meetings_service(auth=auth, case_id=id)
    return SuccessResponse(data=result_dict, msg="查询相亲约见成功")


@VipRouter.post("/{id}/meetings/{meeting_id}/confirm", summary="确认相亲约见", response_model=ResponseSchema[MeetingOutSchema])
async def confirm_meeting_controller(
    id: Annotated[int, Path(description="服务工单ID")],
    meeting_id: Annotated[int, Path(description="约见ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:meeting:confirm"]))],
) -> JSONResponse:
    result_dict = await VipService.confirm_meeting_service(auth=auth, case_id=id, meeting_id=meeting_id)
    return SuccessResponse(data=result_dict, msg="相亲约见已确认")


@VipRouter.post("/{id}/meetings/{meeting_id}/complete", summary="登记相亲约见完成", response_model=ResponseSchema[MeetingOutSchema])
async def complete_meeting_controller(
    data: MeetingActionSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    meeting_id: Annotated[int, Path(description="约见ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:meeting:complete"]))],
) -> JSONResponse:
    result_dict = await VipService.complete_meeting_service(auth=auth, case_id=id, meeting_id=meeting_id, data=data)
    return SuccessResponse(data=result_dict, msg="相亲约见已登记")


@VipRouter.post("/{id}/meetings/{meeting_id}/cancel", summary="取消相亲约见", response_model=ResponseSchema[MeetingOutSchema])
async def cancel_meeting_controller(
    data: MeetingActionSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    meeting_id: Annotated[int, Path(description="约见ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:meeting:cancel"]))],
) -> JSONResponse:
    result_dict = await VipService.cancel_meeting_service(auth=auth, case_id=id, meeting_id=meeting_id, data=data)
    return SuccessResponse(data=result_dict, msg="相亲约见已取消")


@VipRouter.post("/{id}/meetings/{meeting_id}/no-show", summary="标记相亲约见爽约", response_model=ResponseSchema[MeetingOutSchema])
async def no_show_meeting_controller(
    data: MeetingActionSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    meeting_id: Annotated[int, Path(description="约见ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:meeting:no_show"]))],
) -> JSONResponse:
    result_dict = await VipService.no_show_meeting_service(auth=auth, case_id=id, meeting_id=meeting_id, data=data)
    return SuccessResponse(data=result_dict, msg="相亲约见已标记爽约")


@VipRouter.get("/{id}/meetings/{meeting_id}/feedback", summary="查询相亲约见反馈", response_model=ResponseSchema[list[MeetingFeedbackOutSchema]])
async def get_meeting_feedback_controller(
    id: Annotated[int, Path(description="服务工单ID")],
    meeting_id: Annotated[int, Path(description="约见ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:plan:view"]))],
) -> JSONResponse:
    result_dict = await VipService.feedback_list_service(auth=auth, case_id=id, meeting_id=meeting_id)
    return SuccessResponse(data=result_dict, msg="查询相亲约见反馈成功")


@VipRouter.post("/{id}/meetings/{meeting_id}/feedback", summary="新增相亲约见反馈", response_model=ResponseSchema[MeetingFeedbackOutSchema])
async def create_meeting_feedback_controller(
    data: MeetingFeedbackSaveSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    meeting_id: Annotated[int, Path(description="约见ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:meeting:feedback"]))],
) -> JSONResponse:
    result_dict = await VipService.save_feedback_service(auth=auth, case_id=id, meeting_id=meeting_id, data=data)
    return SuccessResponse(data=result_dict, msg="相亲约见反馈已保存")


@VipRouter.put("/{id}/meetings/{meeting_id}/feedback/{feedback_id}", summary="更新相亲约见反馈", response_model=ResponseSchema[MeetingFeedbackOutSchema])
async def update_meeting_feedback_controller(
    data: MeetingFeedbackSaveSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    meeting_id: Annotated[int, Path(description="约见ID")],
    feedback_id: Annotated[int, Path(description="反馈ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:meeting:feedback"]))],
) -> JSONResponse:
    result_dict = await VipService.save_feedback_service(auth=auth, case_id=id, meeting_id=meeting_id, data=data, feedback_id=feedback_id)
    return SuccessResponse(data=result_dict, msg="相亲约见反馈已更新")


@VipRouter.post(
    "/{id}/plan/items/{item_id}/course-record",
    summary="登记课程服务并核销",
    response_model=ResponseSchema[CourseRecordOutSchema],
)
async def create_course_record_controller(
    data: CourseRecordCreateSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    item_id: Annotated[int, Path(description="课程计划节点ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:plan:item:update"]))],
) -> JSONResponse:
    result_dict = await VipService.create_course_record_service(auth=auth, case_id=id, item_id=item_id, data=data)
    return SuccessResponse(data=result_dict, msg="课程服务已登记并核销")


@VipRouter.get(
    "/{id}/course-records",
    summary="查询课程服务记录",
    response_model=ResponseSchema[list[CourseRecordOutSchema]],
)
async def get_course_records_controller(
    id: Annotated[int, Path(description="服务工单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:plan:view"]))],
) -> JSONResponse:
    result_dict = await VipService.course_records_service(auth=auth, case_id=id)
    return SuccessResponse(data=result_dict, msg="查询课程服务记录成功")


@VipRouter.post(
    "/{id}/course-records/{record_id}/revoke",
    summary="撤销课程服务记录",
    response_model=ResponseSchema[CourseRecordOutSchema],
)
async def revoke_course_record_controller(
    data: CourseRecordRevokeSchema,
    id: Annotated[int, Path(description="服务工单ID")],
    record_id: Annotated[int, Path(description="课程记录ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:plan:item:update"]))],
) -> JSONResponse:
    result_dict = await VipService.revoke_course_record_service(auth=auth, case_id=id, record_id=record_id, data=data)
    return SuccessResponse(data=result_dict, msg="课程服务记录已撤销")


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
    "/detail/{id}",
    summary="查询备选人详情",
    response_model=ResponseSchema[dict],
)
async def candidate_detail_controller(
    id: Annotated[int, Path(description="备选库条目ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["service:candidate:detail", "service:candidate:discover"]))],
    by_person: Annotated[bool, Query(description="是否按Person ID查询")] = False,
    scope: Annotated[str | None, Query(description="候选发现范围")] = None,
    matchmaker_id: Annotated[int | None, Query(description="目标红娘ID")] = None,
) -> JSONResponse:
    result_dict = await CandidateService.detail_service(auth=auth, item_id=id, by_person=by_person, scope=scope, matchmaker_id=matchmaker_id)
    return SuccessResponse(data=result_dict, msg="查询备选人详情成功")


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
