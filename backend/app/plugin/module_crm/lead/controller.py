from typing import Annotated

from fastapi import APIRouter, Depends, Path, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import ResponseSchema, StreamResponse, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.dependencies import AuthPermission
from app.core.logger import log
from app.core.router_class import OperationLogRoute
from app.utils.common_util import bytes2file_response

from .schema import (
    LeadAssignSchema,
    LeadClaimSchema,
    LeadCreateSchema,
    LeadDetailOutSchema,
    LeadImportResultSchema,
    LeadMobileCheckSchema,
    LeadOutSchema,
    LeadProcessCreateSchema,
    LeadProcessOutSchema,
    LeadQueryParam,
    LeadStoreRuleSchema,
    LeadUpdateSchema,
)
from .service import LeadService

LeadRouter = APIRouter(route_class=OperationLogRoute, prefix="/lead", tags=["CRM线索管理"])


@LeadRouter.get(
    "/all/list",
    summary="查询全量线索",
    response_model=ResponseSchema[list[LeadOutSchema]],
)
async def list_all_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[LeadQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:lead:all:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await LeadService.page_service(auth=auth, view="all", page_no=page.page_no, page_size=page.page_size, search=search)
    return SuccessResponse(data=result, msg="查询全量线索成功")


@LeadRouter.get(
    "/store-pool/list",
    summary="查询门店公海",
    response_model=ResponseSchema[list[LeadOutSchema]],
)
async def list_store_pool_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[LeadQueryParam, Depends()],
    auth: Annotated[
        AuthSchema,
        Depends(AuthPermission(["crm:lead:store:query", "crm:lead:sales:store_pool"], check_data_scope=False)),
    ],
) -> JSONResponse:
    result = await LeadService.page_service(auth=auth, view="store_pool", page_no=page.page_no, page_size=page.page_size, search=search)
    return SuccessResponse(data=result, msg="查询门店公海成功")


@LeadRouter.get(
    "/sales-private/list",
    summary="查询销售私海",
    response_model=ResponseSchema[list[LeadOutSchema]],
)
async def list_sales_private_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[LeadQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:lead:sales:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await LeadService.page_service(auth=auth, view="sales_private", page_no=page.page_no, page_size=page.page_size, search=search)
    return SuccessResponse(data=result, msg="查询销售私海成功")


@LeadRouter.get(
    "/sales-options",
    summary="查询CRM销售选择器",
)
async def sales_options_controller(
    auth: Annotated[
        AuthSchema,
        Depends(
            AuthPermission(
                [
                    "crm:lead:store:query",
                    "crm:lead:sales:query",
                    "crm:customer:query",
                    "crm:customer:visit:list",
                ],
                check_data_scope=False,
            )
        ),
    ],
    store_id: int | None = None,
) -> JSONResponse:
    result = await LeadService.sales_options_service(auth=auth, store_id=store_id)
    return SuccessResponse(data=result, msg="查询销售选择器成功")


@LeadRouter.get(
    "/store-options",
    summary="查询CRM门店选择器",
)
async def store_options_controller(
    auth: Annotated[
        AuthSchema,
        Depends(
            AuthPermission(
                [
                    "crm:lead:store:query",
                    "crm:lead:sales:query",
                    "crm:customer:query",
                    "crm:customer:visit:list",
                ],
                check_data_scope=False,
            )
        ),
    ],
) -> JSONResponse:
    result = await LeadService.store_options_service(auth=auth)
    return SuccessResponse(data=result, msg="查询门店选择器成功")


@LeadRouter.get(
    "/source-options",
    summary="查询CRM来源渠道选择器",
)
async def source_options_controller(
    auth: Annotated[
        AuthSchema,
        Depends(
            AuthPermission(
                [
                    "crm:lead:store:query",
                    "crm:lead:sales:query",
                    "crm:customer:query",
                ],
                check_data_scope=False,
            )
        ),
    ],
) -> JSONResponse:
    result = await LeadService.source_options_service(auth=auth)
    return SuccessResponse(data=result, msg="查询来源渠道选择器成功")


@LeadRouter.get(
    "/detail/{id}",
    summary="查询线索详情",
    response_model=ResponseSchema[LeadDetailOutSchema],
)
async def detail_controller(
    id: Annotated[int, Path(description="线索ID")],
    auth: Annotated[
        AuthSchema,
        Depends(
            AuthPermission(
                ["crm:lead:all:detail", "crm:lead:store:detail", "crm:lead:sales:detail"],
                check_data_scope=False,
            )
        ),
    ],
) -> JSONResponse:
    result = await LeadService.detail_service(auth=auth, id=id)
    return SuccessResponse(data=result, msg="查询线索详情成功")


@LeadRouter.get(
    "/mobile/check/{mobile}",
    summary="手机号查重",
    response_model=ResponseSchema[LeadMobileCheckSchema],
)
async def check_mobile_controller(
    mobile: Annotated[str, Path(description="手机号")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:lead:create"], check_data_scope=False))],
) -> JSONResponse:
    result = await LeadService.check_mobile_service(auth=auth, mobile=mobile)
    return SuccessResponse(data=result, msg="手机号查重成功")


@LeadRouter.post(
    "/create",
    summary="新增线索",
    response_model=ResponseSchema[LeadOutSchema],
)
async def create_controller(
    data: LeadCreateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:lead:create"], check_data_scope=False))],
) -> JSONResponse:
    result = await LeadService.create_service(auth=auth, data=data)
    log.info(f"新增线索成功: {result.get('id')}")
    return SuccessResponse(data=result, msg="新增线索成功")


@LeadRouter.put(
    "/update/{id}",
    summary="编辑线索",
    response_model=ResponseSchema[LeadOutSchema],
)
async def update_controller(
    data: LeadUpdateSchema,
    id: Annotated[int, Path(description="线索ID")],
    auth: Annotated[
        AuthSchema,
        Depends(
            AuthPermission(
                ["crm:lead:update", "crm:lead:sales:detail"],
                check_data_scope=False,
            )
        ),
    ],
) -> JSONResponse:
    result = await LeadService.update_service(auth=auth, id=id, data=data)
    return SuccessResponse(data=result, msg="编辑线索成功")


@LeadRouter.post(
    "/assign",
    summary="分配线索",
    response_model=ResponseSchema[None],
)
async def assign_controller(
    data: LeadAssignSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:lead:assign"], check_data_scope=False))],
) -> JSONResponse:
    await LeadService.assign_service(auth=auth, data=data)
    return SuccessResponse(msg="分配线索成功")


@LeadRouter.post(
    "/claim",
    summary="领取线索",
    response_model=ResponseSchema[None],
)
async def claim_controller(
    data: LeadClaimSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:lead:sales:claim"], check_data_scope=False))],
) -> JSONResponse:
    await LeadService.claim_service(auth=auth, data=data)
    return SuccessResponse(msg="领取线索成功")


@LeadRouter.post(
    "/process/{id}",
    summary="新增线索过程记录",
    response_model=ResponseSchema[LeadProcessOutSchema],
)
async def process_controller(
    data: LeadProcessCreateSchema,
    id: Annotated[int, Path(description="线索ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:lead:process"], check_data_scope=False))],
) -> JSONResponse:
    result = await LeadService.process_service(auth=auth, id=id, data=data)
    return SuccessResponse(data=result, msg="保存过程记录成功")


@LeadRouter.get(
    "/store-rule/{store_id}",
    summary="查询门店线索规则",
    response_model=ResponseSchema[LeadStoreRuleSchema],
)
async def get_store_rule_controller(
    store_id: Annotated[int, Path(description="门店ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:lead:rule:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await LeadService.get_store_rule_service(auth=auth, store_id=store_id)
    return SuccessResponse(data=result, msg="查询门店线索规则成功")


@LeadRouter.put(
    "/store-rule/{store_id}",
    summary="设置门店线索规则",
    response_model=ResponseSchema[None],
)
async def set_store_rule_controller(
    data: LeadStoreRuleSchema,
    store_id: Annotated[int, Path(description="门店ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:lead:rule:update"], check_data_scope=False))],
) -> JSONResponse:
    await LeadService.set_store_rule_service(auth=auth, store_id=store_id, data=data)
    return SuccessResponse(msg="设置门店线索规则成功")


@LeadRouter.post(
    "/import/template",
    summary="下载线索导入模板",
)
async def download_template_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:lead:import"], check_data_scope=False))],
) -> StreamingResponse:
    result = await LeadService.download_template_service()
    return StreamResponse(
        data=bytes2file_response(result),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=crm_lead_import_template.xlsx"},
    )


@LeadRouter.post(
    "/import/data",
    summary="导入线索",
    response_model=ResponseSchema[LeadImportResultSchema],
)
async def import_controller(
    file: UploadFile,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:lead:import"], check_data_scope=False))],
) -> JSONResponse:
    result = await LeadService.import_service(auth=auth, file=file)
    return SuccessResponse(data=result, msg="导入线索完成")
