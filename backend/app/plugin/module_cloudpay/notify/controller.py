from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import db_getter
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
async def cloudpay_notify_controller(
    request: Request,
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> PlainTextResponse:
    result = await CloudPayNotifyService.handle_trade_notify(db=db, request=request)
    return PlainTextResponse(result)
