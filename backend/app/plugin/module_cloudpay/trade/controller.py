from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from starlette.routing import NoMatchFound

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import ResponseSchema, SuccessResponse
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .schema import (
    CloudPayCreateSchema,
    CloudPayPaySchema,
    CloudPayPrecreateSchema,
    CloudPayQuerySchema,
    CloudPayRefundQuerySchema,
    CloudPayRefundSchema,
    CloudPayResponseSchema,
)
from .service import CloudPayService


CloudPayTradeRouter = APIRouter(
    route_class=OperationLogRoute,
    prefix="/trade",
    tags=["云支付交易"],
)


def _get_notify_url(request: Request) -> str:
    try:
        return str(request.url_for("cloudpay_notify_controller"))
    except NoMatchFound:
        root_path = request.scope.get("root_path", "").rstrip("/")
        return f"{str(request.base_url).rstrip('/')}{root_path}/cloudpay/notify/trade"


@CloudPayTradeRouter.post(
    "/pay",
    summary="云支付条码支付",
    response_model=ResponseSchema[CloudPayResponseSchema],
)
async def pay_controller(
    data: CloudPayPaySchema,
    request: Request,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["finance:payment:pay"]))],
) -> JSONResponse:
    data.notify_url = data.notify_url or _get_notify_url(request)
    result = await CloudPayService.pay_service(auth=auth, data=data)
    return SuccessResponse(data=result, msg="云支付条码支付请求成功")


@CloudPayTradeRouter.post(
    "/precreate",
    summary="云支付交易预创建",
    response_model=ResponseSchema[CloudPayResponseSchema],
)
async def precreate_controller(
    data: CloudPayPrecreateSchema,
    request: Request,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["finance:payment:pay"]))],
) -> JSONResponse:
    data.notify_url = data.notify_url or _get_notify_url(request)
    result = await CloudPayService.precreate_service(auth=auth, data=data)
    return SuccessResponse(data=result, msg="云支付交易预创建请求成功")


@CloudPayTradeRouter.post(
    "/create",
    summary="云支付小程序支付创建",
    response_model=ResponseSchema[CloudPayResponseSchema],
)
async def create_controller(
    data: CloudPayCreateSchema,
    request: Request,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["finance:payment:pay"]))],
) -> JSONResponse:
    data.notify_url = data.notify_url or _get_notify_url(request)
    result = await CloudPayService.create_service(auth=auth, data=data)
    return SuccessResponse(data=result, msg="云支付小程序支付创建请求成功")


@CloudPayTradeRouter.post(
    "/query",
    summary="云支付交易查询",
    response_model=ResponseSchema[CloudPayResponseSchema],
)
async def query_controller(
    data: CloudPayQuerySchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["finance:payment:query"]))],
) -> JSONResponse:
    result = await CloudPayService.query_service(auth=auth, data=data)
    return SuccessResponse(data=result, msg="云支付交易查询请求成功")


@CloudPayTradeRouter.post(
    "/refund",
    summary="云支付退款",
    response_model=ResponseSchema[CloudPayResponseSchema],
)
async def refund_controller(
    data: CloudPayRefundSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["finance:payment:refund"]))],
) -> JSONResponse:
    result = await CloudPayService.refund_service(auth=auth, data=data)
    return SuccessResponse(data=result, msg="云支付退款请求成功")


@CloudPayTradeRouter.post(
    "/refund-query",
    summary="云支付退款详情查询",
    response_model=ResponseSchema[CloudPayResponseSchema],
)
async def refund_query_controller(
    data: CloudPayRefundQuerySchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["finance:payment:refund"]))],
) -> JSONResponse:
    result = await CloudPayService.refund_query_service(auth=auth, data=data)
    return SuccessResponse(data=result, msg="云支付退款详情查询请求成功")
