from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.core.router_class import OperationLogRoute

from .service import CloudPayNotifyService


CloudPayNotifyRouter = APIRouter(
    route_class=OperationLogRoute,
    prefix="/notify",
    tags=["云支付通知"],
)


@CloudPayNotifyRouter.post(
    "/trade",
    summary="云支付交易异步通知",
    response_class=PlainTextResponse,
)
async def cloudpay_notify_controller(request: Request) -> PlainTextResponse:
    result = await CloudPayNotifyService.handle_trade_notify(request)
    return PlainTextResponse(result)
