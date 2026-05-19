from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .schema import (
    CustomerCertificationMaterialOutSchema,
    CustomerCertificationMaterialSaveSchema,
    CustomerDetailOutSchema,
    CustomerOutSchema,
    CustomerPrintCardSchema,
    CustomerProcessCreateSchema,
    CustomerProcessOutSchema,
    CustomerQueryParam,
    CustomerReturnLeadSchema,
    CustomerTransferOwnerSchema,
    CustomerTransferStoreSchema,
    CustomerUpdateSchema,
    CustomerVisitConsultationSchema,
    CustomerVisitQueryParam,
)
from .service import CustomerService

CustomerRouter = APIRouter(route_class=OperationLogRoute, prefix="/customer", tags=["CRM客户管理"])


@CustomerRouter.get(
    "/list",
    summary="查询客户列表",
    response_model=ResponseSchema[list[CustomerOutSchema]],
)
async def list_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[CustomerQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:customer:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await CustomerService.page_service(auth=auth, page_no=page.page_no, page_size=page.page_size, search=search)
    return SuccessResponse(data=result, msg="查询客户列表成功")


@CustomerRouter.get(
    "/detail/{id}",
    summary="查询客户总档案",
    response_model=ResponseSchema[CustomerDetailOutSchema],
)
async def detail_controller(
    id: Annotated[int, Path(description="客户ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:customer:detail"], check_data_scope=False))],
) -> JSONResponse:
    result = await CustomerService.detail_service(auth=auth, id=id)
    return SuccessResponse(data=result, msg="查询客户总档案成功")


@CustomerRouter.put(
    "/update/{id}",
    summary="编辑客户主档案",
    response_model=ResponseSchema[CustomerOutSchema],
)
async def update_controller(
    data: CustomerUpdateSchema,
    id: Annotated[int, Path(description="客户ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:customer:update"], check_data_scope=False))],
) -> JSONResponse:
    result = await CustomerService.update_service(auth=auth, id=id, data=data)
    return SuccessResponse(data=result, msg="编辑客户主档案成功")


@CustomerRouter.post(
    "/certification-material/{id}",
    summary="新增客户认证资料存档",
    response_model=ResponseSchema[CustomerCertificationMaterialOutSchema],
)
async def save_certification_material_controller(
    data: CustomerCertificationMaterialSaveSchema,
    id: Annotated[int, Path(description="客户ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:customer:update"], check_data_scope=False))],
) -> JSONResponse:
    result = await CustomerService.save_certification_material_service(auth=auth, customer_id=id, data=data)
    return SuccessResponse(data=result, msg="新增客户认证资料成功")


@CustomerRouter.delete(
    "/certification-material/{material_id}",
    summary="删除客户认证资料存档",
    response_model=ResponseSchema,
)
async def delete_certification_material_controller(
    material_id: Annotated[int, Path(description="资料ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:customer:update"], check_data_scope=False))],
) -> JSONResponse:
    await CustomerService.delete_certification_material_service(auth=auth, material_id=material_id)
    return SuccessResponse(msg="删除客户认证资料成功")


@CustomerRouter.post(
    "/from-lead/{lead_id}",
    summary="线索转建档客户",
    response_model=ResponseSchema[CustomerOutSchema],
)
async def from_lead_controller(
    lead_id: Annotated[int, Path(description="线索ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:customer:create"], check_data_scope=False))],
) -> JSONResponse:
    result = await CustomerService.create_from_lead_service(auth=auth, lead_id=lead_id)
    return SuccessResponse(data=result, msg="线索转建档客户成功")


@CustomerRouter.post(
    "/process/{id}",
    summary="新增客户统一跟进记录",
    response_model=ResponseSchema[CustomerProcessOutSchema],
)
async def process_controller(
    data: CustomerProcessCreateSchema,
    id: Annotated[int, Path(description="客户ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:customer:follow"], check_data_scope=False))],
) -> JSONResponse:
    result = await CustomerService.process_service(auth=auth, customer_id=id, record_type="follow", data=data)
    return SuccessResponse(data=result, msg="新增客户过程记录成功")


@CustomerRouter.post(
    "/process/follow/{id}",
    summary="新增客户跟进记录",
    response_model=ResponseSchema[CustomerProcessOutSchema],
)
async def follow_process_controller(
    data: CustomerProcessCreateSchema,
    id: Annotated[int, Path(description="客户ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:customer:follow"], check_data_scope=False))],
) -> JSONResponse:
    result = await CustomerService.process_service(auth=auth, customer_id=id, record_type="follow", data=data)
    return SuccessResponse(data=result, msg="新增客户跟进记录成功")


@CustomerRouter.post(
    "/process/appointment/{id}",
    summary="新增客户邀约记录",
    response_model=ResponseSchema[CustomerProcessOutSchema],
)
async def appointment_process_controller(
    data: CustomerProcessCreateSchema,
    id: Annotated[int, Path(description="客户ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:customer:appointment"], check_data_scope=False))],
) -> JSONResponse:
    result = await CustomerService.process_service(auth=auth, customer_id=id, record_type="appointment", data=data)
    return SuccessResponse(data=result, msg="新增客户邀约记录成功")


@CustomerRouter.post(
    "/process/visit/{id}",
    summary="新增客户到店记录",
    response_model=ResponseSchema[CustomerProcessOutSchema],
)
async def visit_process_controller(
    data: CustomerProcessCreateSchema,
    id: Annotated[int, Path(description="客户ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:customer:visit"], check_data_scope=False))],
) -> JSONResponse:
    result = await CustomerService.process_service(auth=auth, customer_id=id, record_type="visit_checkin", data=data)
    return SuccessResponse(data=result, msg="新增客户到店记录成功")


@CustomerRouter.post(
    "/process/consultation/{id}",
    summary="新增客户面谈记录",
    response_model=ResponseSchema[CustomerProcessOutSchema],
)
async def consultation_process_controller(
    data: CustomerProcessCreateSchema,
    id: Annotated[int, Path(description="客户ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:customer:consultation"], check_data_scope=False))],
) -> JSONResponse:
    result = await CustomerService.process_service(auth=auth, customer_id=id, record_type="consultation", data=data)
    return SuccessResponse(data=result, msg="新增客户面谈记录成功")


@CustomerRouter.get(
    "/visit/list",
    summary="查询到店管理列表",
    response_model=ResponseSchema[list[CustomerProcessOutSchema]],
)
async def visit_list_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[CustomerVisitQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:customer:visit:list"], check_data_scope=False))],
) -> JSONResponse:
    result = await CustomerService.visit_page_service(
        auth=auth,
        page_no=page.page_no,
        page_size=page.page_size,
        search=search,
    )
    return SuccessResponse(data=result, msg="查询到店管理列表成功")


@CustomerRouter.post(
    "/visit/checkin/{process_id}",
    summary="登记到店",
    response_model=ResponseSchema[CustomerProcessOutSchema],
)
async def visit_checkin_controller(
    process_id: Annotated[int, Path(description="邀约过程记录ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:customer:visit:checkin"], check_data_scope=False))],
) -> JSONResponse:
    result = await CustomerService.visit_status_service(auth=auth, process_id=process_id, action="visit_checkin")
    return SuccessResponse(data=result, msg="登记到店成功")


@CustomerRouter.post(
    "/visit/no-show/{process_id}",
    summary="标记爽约",
    response_model=ResponseSchema[CustomerProcessOutSchema],
)
async def visit_no_show_controller(
    process_id: Annotated[int, Path(description="邀约过程记录ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:customer:visit:no_show"], check_data_scope=False))],
) -> JSONResponse:
    result = await CustomerService.visit_status_service(auth=auth, process_id=process_id, action="no_show")
    return SuccessResponse(data=result, msg="标记爽约成功")


@CustomerRouter.post(
    "/visit/cancel/{process_id}",
    summary="取消预约",
    response_model=ResponseSchema[CustomerProcessOutSchema],
)
async def visit_cancel_controller(
    process_id: Annotated[int, Path(description="邀约过程记录ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:customer:visit:cancel"], check_data_scope=False))],
) -> JSONResponse:
    result = await CustomerService.visit_status_service(auth=auth, process_id=process_id, action="appointment_cancel")
    return SuccessResponse(data=result, msg="取消预约成功")


@CustomerRouter.post(
    "/visit/consultation/{process_id}",
    summary="到店管理记录面谈",
    response_model=ResponseSchema[CustomerProcessOutSchema],
)
async def visit_consultation_controller(
    data: CustomerVisitConsultationSchema,
    process_id: Annotated[int, Path(description="邀约过程记录ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:customer:visit:consultation"], check_data_scope=False))],
) -> JSONResponse:
    result = await CustomerService.visit_status_service(
        auth=auth,
        process_id=process_id,
        action="consultation",
        data=data,
    )
    return SuccessResponse(data=result, msg="记录面谈成功")


@CustomerRouter.post(
    "/transfer-owner",
    summary="客户同店转派",
    response_model=ResponseSchema[None],
)
async def transfer_owner_controller(
    data: CustomerTransferOwnerSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:customer:transfer"], check_data_scope=False))],
) -> JSONResponse:
    await CustomerService.transfer_owner_service(auth=auth, data=data)
    return SuccessResponse(msg="客户转派成功")


@CustomerRouter.post(
    "/transfer-store",
    summary="客户跨店转交",
    response_model=ResponseSchema[None],
)
async def transfer_store_controller(
    data: CustomerTransferStoreSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:customer:transfer"], check_data_scope=False))],
) -> JSONResponse:
    await CustomerService.transfer_store_service(auth=auth, data=data)
    return SuccessResponse(msg="客户转交成功")


@CustomerRouter.post(
    "/return-lead/{id}",
    summary="客户退回线索",
    response_model=ResponseSchema[None],
)
async def return_lead_controller(
    data: CustomerReturnLeadSchema,
    id: Annotated[int, Path(description="客户ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:customer:follow"], check_data_scope=False))],
) -> JSONResponse:
    await CustomerService.return_lead_service(auth=auth, id=id, data=data)
    return SuccessResponse(msg="客户退回线索成功")


@CustomerRouter.get(
    "/print-card/{id}",
    summary="查询A4对外资料卡",
    response_model=ResponseSchema[CustomerPrintCardSchema],
)
async def print_card_controller(
    id: Annotated[int, Path(description="客户ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:customer:print"], check_data_scope=False))],
) -> JSONResponse:
    result = await CustomerService.print_card_service(auth=auth, id=id)
    return SuccessResponse(data=result, msg="查询A4对外资料卡成功")
