from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import JSONResponse
from starlette.routing import NoMatchFound

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .schema import (
    BarcodePaySchema,
    BarcodeReceiptCreateSchema,
    OnlineReceiptCreateSchema,
    QrcodePaySchema,
    ReceiptContractSearchOutSchema,
    ReceiptCreateSchema,
    ReceiptOfflineConfirmSchema,
    ReceiptOutSchema,
    ReceiptPaymentOutSchema,
    ReceiptPendingCreateSchema,
    ReceiptQueryParam,
    ReceiptRefundRegisterSchema,
    ReceiptReverseSchema,
    ReceiptReviewSchema,
    ReceiptSummaryOutSchema,
    ReceiptVoidSchema,
)
from .service import ReceiptService

ReceiptRouter = APIRouter(route_class=OperationLogRoute, prefix="/receipt", tags=["CRM收款管理"])


def _get_notify_url(request: Request) -> str:
    try:
        return str(request.url_for("cloudpay_notify_controller"))
    except NoMatchFound:
        root_path = request.scope.get("root_path", "").rstrip("/")
        return f"{str(request.base_url).rstrip('/')}{root_path}/cloudpay/notify/trade"


@ReceiptRouter.get("/list", summary="查询收款列表", response_model=ResponseSchema[list[ReceiptOutSchema]])
async def list_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[ReceiptQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:receipt:query"], check_data_scope=False))],
) -> JSONResponse:
    result = await ReceiptService.page_service(auth=auth, page_no=page.page_no, page_size=page.page_size, search=search)
    return SuccessResponse(data=result, msg="查询收款列表成功")


@ReceiptRouter.get("/detail/{id}", summary="查询收款详情", response_model=ResponseSchema[ReceiptOutSchema])
async def detail_controller(
    id: Annotated[int, Path(description="收款单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:receipt:detail"], check_data_scope=False))],
) -> JSONResponse:
    result = await ReceiptService.detail_service(auth=auth, receipt_id=id)
    return SuccessResponse(data=result, msg="查询收款详情成功")


@ReceiptRouter.get("/contract/search", summary="收款合同快速搜索", response_model=ResponseSchema[list[ReceiptContractSearchOutSchema]])
async def contract_search_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:receipt:query"], check_data_scope=False))],
    keyword: Annotated[str | None, Query(description="合同编号/客户姓名/手机号")] = None,
    limit: Annotated[int, Query(ge=1, le=50, description="返回条数")] = 20,
) -> JSONResponse:
    result = await ReceiptService.contract_search_service(auth=auth, keyword=keyword, limit=limit)
    return SuccessResponse(data=result, msg="查询可收款合同成功")


@ReceiptRouter.post("/offline/{contract_id}", summary="提交线下收款", response_model=ResponseSchema[ReceiptOutSchema])
async def offline_controller(
    data: ReceiptCreateSchema,
    contract_id: Annotated[int, Path(description="合同ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:receipt:submit_offline"], check_data_scope=False))],
) -> JSONResponse:
    result = await ReceiptService.create_offline_service(auth=auth, contract_id=contract_id, data=data)
    return SuccessResponse(data=result, msg="线下收款已提交")


@ReceiptRouter.post("/pending/{contract_id}", summary="创建待收款单", response_model=ResponseSchema[ReceiptOutSchema])
async def pending_controller(
    data: ReceiptPendingCreateSchema,
    contract_id: Annotated[int, Path(description="合同ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:receipt:submit_offline"], check_data_scope=False))],
) -> JSONResponse:
    result = await ReceiptService.create_pending_service(auth=auth, contract_id=contract_id, data=data)
    return SuccessResponse(data=result, msg="待收款单已创建")


@ReceiptRouter.post("/online/{contract_id}", summary="创建在线扫码收款", response_model=ResponseSchema[ReceiptPaymentOutSchema])
async def online_controller(
    data: OnlineReceiptCreateSchema,
    request: Request,
    contract_id: Annotated[int, Path(description="合同ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:receipt:create_online"], check_data_scope=False))],
) -> JSONResponse:
    result = await ReceiptService.create_online_service(auth=auth, contract_id=contract_id, data=data, notify_url=_get_notify_url(request))
    return SuccessResponse(data=result, msg="在线收款已创建")


@ReceiptRouter.post("/qrcode/{receipt_id}", summary="扫码支付", response_model=ResponseSchema[ReceiptPaymentOutSchema])
async def qrcode_controller(
    data: QrcodePaySchema,
    request: Request,
    receipt_id: Annotated[int, Path(description="收款单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:receipt:create_online"], check_data_scope=False))],
) -> JSONResponse:
    result = await ReceiptService.qrcode_pay_service(auth=auth, receipt_id=receipt_id, data=data, notify_url=_get_notify_url(request))
    return SuccessResponse(data=result, msg="扫码支付已创建")


@ReceiptRouter.post("/offline-confirm/{receipt_id}", summary="待收款单转线下确认", response_model=ResponseSchema[ReceiptOutSchema])
async def offline_confirm_controller(
    data: ReceiptOfflineConfirmSchema,
    receipt_id: Annotated[int, Path(description="收款单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:receipt:submit_offline"], check_data_scope=False))],
) -> JSONResponse:
    result = await ReceiptService.offline_confirm_service(auth=auth, receipt_id=receipt_id, data=data)
    return SuccessResponse(data=result, msg="线下收款已提交复核")


@ReceiptRouter.post("/barcode-create/{contract_id}", summary="发起条码收款", response_model=ResponseSchema[ReceiptPaymentOutSchema])
async def barcode_create_controller(
    data: BarcodeReceiptCreateSchema,
    request: Request,
    contract_id: Annotated[int, Path(description="合同ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:receipt:barcode_pay"], check_data_scope=False))],
) -> JSONResponse:
    result = await ReceiptService.create_barcode_service(auth=auth, contract_id=contract_id, data=data, notify_url=_get_notify_url(request))
    return SuccessResponse(data=result, msg="条码支付请求成功")


@ReceiptRouter.post("/barcode/{receipt_id}", summary="条码支付", response_model=ResponseSchema[ReceiptPaymentOutSchema])
async def barcode_controller(
    data: BarcodePaySchema,
    request: Request,
    receipt_id: Annotated[int, Path(description="收款单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:receipt:barcode_pay"], check_data_scope=False))],
) -> JSONResponse:
    result = await ReceiptService.barcode_pay_service(auth=auth, receipt_id=receipt_id, data=data, notify_url=_get_notify_url(request))
    return SuccessResponse(data=result, msg="条码支付请求成功")


@ReceiptRouter.post("/review/{id}", summary="复核线下收款", response_model=ResponseSchema[ReceiptOutSchema])
async def review_controller(
    data: ReceiptReviewSchema,
    id: Annotated[int, Path(description="收款单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:receipt:review"], check_data_scope=False))],
) -> JSONResponse:
    result = await ReceiptService.review_service(auth=auth, receipt_id=id, data=data)
    return SuccessResponse(data=result, msg="收款复核完成")


@ReceiptRouter.post("/void/{id}", summary="作废收款", response_model=ResponseSchema[ReceiptOutSchema])
async def void_controller(
    data: ReceiptVoidSchema,
    id: Annotated[int, Path(description="收款单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:receipt:void"], check_data_scope=False))],
) -> JSONResponse:
    result = await ReceiptService.void_service(auth=auth, receipt_id=id, data=data)
    return SuccessResponse(data=result, msg="收款已作废")


@ReceiptRouter.post("/reverse/{id}", summary="冲正收款", response_model=ResponseSchema[ReceiptOutSchema])
async def reverse_controller(
    data: ReceiptReverseSchema,
    id: Annotated[int, Path(description="收款单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:receipt:reverse"], check_data_scope=False))],
) -> JSONResponse:
    result = await ReceiptService.reverse_service(auth=auth, receipt_id=id, data=data)
    return SuccessResponse(data=result, msg="收款已冲正")


@ReceiptRouter.post("/refund-register/{id}", summary="退款登记", response_model=ResponseSchema[ReceiptOutSchema])
async def refund_register_controller(
    data: ReceiptRefundRegisterSchema,
    id: Annotated[int, Path(description="收款单ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:receipt:refund_register"], check_data_scope=False))],
) -> JSONResponse:
    result = await ReceiptService.refund_register_service(auth=auth, receipt_id=id, data=data)
    return SuccessResponse(data=result, msg="退款已登记")


@ReceiptRouter.get("/summary", summary="收款汇总", response_model=ResponseSchema[ReceiptSummaryOutSchema])
async def summary_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:receipt:query"], check_data_scope=False))],
    contract_id: Annotated[int | None, Query(description="合同ID")] = None,
) -> JSONResponse:
    result = await ReceiptService.summary_service(auth=auth, contract_id=contract_id)
    return SuccessResponse(data=result, msg="查询收款汇总成功")
