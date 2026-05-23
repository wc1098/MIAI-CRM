from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .schema import (
    ContractAttachmentOutSchema,
    ContractAttachmentSaveSchema,
    ContractCreateSchema,
    ContractOutSchema,
    ContractQueryParam,
    ContractReviewSchema,
    ContractSignSchema,
    ContractStoreRuleSchema,
    ContractUpdateSchema,
    ContractVoidSchema,
    CustomerSearchOutSchema,
)
from .service import ContractService

ContractRouter = APIRouter(route_class=OperationLogRoute, prefix="/contract", tags=["CRM合同管理"])


@ContractRouter.get("/list", summary="查询合同列表", response_model=ResponseSchema[list[ContractOutSchema]])
async def list_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[ContractQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:contract:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await ContractService.page_service(auth=auth, page_no=page.page_no, page_size=page.page_size, search=search)
    return SuccessResponse(data=result, msg="查询合同列表成功")


@ContractRouter.get("/detail/{id}", summary="查询合同详情", response_model=ResponseSchema[ContractOutSchema])
async def detail_controller(
    id: Annotated[int, Path(description="合同ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:contract:detail"], check_data_scope=False))],
) -> JSONResponse:
    result = await ContractService.detail_service(auth=auth, id=id)
    return SuccessResponse(data=result, msg="查询合同详情成功")


@ContractRouter.post("/create", summary="创建合同草稿", response_model=ResponseSchema[ContractOutSchema])
async def create_controller(
    data: ContractCreateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:contract:create"], check_data_scope=False))],
) -> JSONResponse:
    result = await ContractService.create_service(auth=auth, data=data)
    return SuccessResponse(data=result, msg="创建合同成功")


@ContractRouter.put("/update/{id}", summary="编辑合同草稿", response_model=ResponseSchema[ContractOutSchema])
async def update_controller(
    data: ContractUpdateSchema,
    id: Annotated[int, Path(description="合同ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:contract:update"], check_data_scope=False))],
) -> JSONResponse:
    result = await ContractService.update_service(auth=auth, id=id, data=data)
    return SuccessResponse(data=result, msg="编辑合同成功")


@ContractRouter.post("/sign/{id}", summary="标记合同已签", response_model=ResponseSchema[ContractOutSchema])
async def sign_controller(
    data: ContractSignSchema,
    id: Annotated[int, Path(description="合同ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:contract:sign"], check_data_scope=False))],
) -> JSONResponse:
    result = await ContractService.sign_service(auth=auth, id=id, data=data)
    return SuccessResponse(data=result, msg="合同已签")


@ContractRouter.post("/submit-review/{id}", summary="提交合同审核", response_model=ResponseSchema[ContractOutSchema])
async def submit_review_controller(
    id: Annotated[int, Path(description="合同ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:contract:submit_review"], check_data_scope=False))],
) -> JSONResponse:
    result = await ContractService.submit_review_service(auth=auth, id=id)
    return SuccessResponse(data=result, msg="合同已提交审核")


@ContractRouter.post("/review/{id}", summary="审核合同", response_model=ResponseSchema[ContractOutSchema])
async def review_controller(
    data: ContractReviewSchema,
    id: Annotated[int, Path(description="合同ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:contract:review"], check_data_scope=False))],
) -> JSONResponse:
    result = await ContractService.review_service(auth=auth, id=id, data=data)
    return SuccessResponse(data=result, msg="合同审核完成")


@ContractRouter.get("/store-rule/{store_id}", summary="查询门店合同规则", response_model=ResponseSchema[ContractStoreRuleSchema])
async def get_store_rule_controller(
    store_id: Annotated[int, Path(description="门店ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:contract:rule:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await ContractService.get_store_rule_service(auth=auth, store_id=store_id)
    return SuccessResponse(data=result, msg="查询门店合同规则成功")


@ContractRouter.put("/store-rule/{store_id}", summary="设置门店合同规则", response_model=ResponseSchema)
async def set_store_rule_controller(
    data: ContractStoreRuleSchema,
    store_id: Annotated[int, Path(description="门店ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:contract:rule:update"], check_data_scope=False))],
) -> JSONResponse:
    await ContractService.set_store_rule_service(auth=auth, store_id=store_id, data=data)
    return SuccessResponse(msg="门店合同规则已保存")


@ContractRouter.post("/void/{id}", summary="作废合同", response_model=ResponseSchema[ContractOutSchema])
async def void_controller(
    data: ContractVoidSchema,
    id: Annotated[int, Path(description="合同ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:contract:void"], check_data_scope=False))],
) -> JSONResponse:
    result = await ContractService.void_service(auth=auth, id=id, data=data)
    return SuccessResponse(data=result, msg="合同已作废")


@ContractRouter.post("/attachment/{id}", summary="保存合同影像", response_model=ResponseSchema[ContractAttachmentOutSchema])
async def attachment_controller(
    data: ContractAttachmentSaveSchema,
    id: Annotated[int, Path(description="合同ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:contract:view_file"], check_data_scope=False))],
) -> JSONResponse:
    result = await ContractService.save_attachment_service(auth=auth, id=id, data=data)
    return SuccessResponse(data=result, msg="合同影像已保存")


@ContractRouter.delete("/attachment/{attachment_id}", summary="删除合同影像", response_model=ResponseSchema)
async def attachment_delete_controller(
    attachment_id: Annotated[int, Path(description="合同影像ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:contract:view_file"], check_data_scope=False))],
) -> JSONResponse:
    await ContractService.delete_attachment_service(auth=auth, attachment_id=attachment_id)
    return SuccessResponse(msg="合同影像已删除")


@ContractRouter.get("/customer/search", summary="合同客户快速搜索", response_model=ResponseSchema[list[CustomerSearchOutSchema]])
async def customer_search_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:contract:create"], check_data_scope=False))],
    keyword: Annotated[str | None, Query(description="客户姓名/手机号/编号")] = None,
    limit: Annotated[int, Query(ge=1, le=50, description="返回条数")] = 20,
) -> JSONResponse:
    result = await ContractService.customer_search_service(auth=auth, keyword=keyword, limit=limit)
    return SuccessResponse(data=result, msg="查询客户成功")
