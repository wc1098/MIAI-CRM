import json
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CustomException
from app.core.logger import log
from app.plugin.module_cloudpay.trade.client import CloudPayClient
from app.plugin.module_payment.core.service import PaymentService


class CloudPayNotifyService:
    """
    云支付异步通知服务。
    """

    @staticmethod
    async def parse_notify_payload(request: Request) -> dict[str, Any]:
        content_type = request.headers.get("content-type", "").lower()
        if "application/json" in content_type:
            payload = await request.json()
        elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            form = await request.form()
            payload = dict(form)
        else:
            body = await request.body()
            if not body:
                raise CustomException(msg="云支付通知内容为空")
            try:
                payload = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as e:
                raise CustomException(msg="云支付通知格式不支持") from e

        if not isinstance(payload, dict):
            raise CustomException(msg="云支付通知格式错误")
        return payload

    @classmethod
    async def handle_trade_notify(cls, db: AsyncSession, request: Request) -> str:
        payload = await cls.parse_notify_payload(request)
        signature = request.headers.get("x-ca-signature") or request.headers.get("x-signature") or request.headers.get("signature")
        verify_result = False
        verify_error = None
        notify_headers = {
            key: value
            for key, value in request.headers.items()
            if key.lower()
            in {
                "content-type",
                "user-agent",
                "x-forwarded-for",
                "x-real-ip",
                "x-ca-signature",
                "sign",
                "signature",
                "x-sign",
                "x-signature",
            }
        }
        try:
            verify_result = await CloudPayClient.verify_response_payload(payload, signature=signature)
        except Exception as exc:
            verify_error = str(exc)
            message = f"云支付交易通知验签失败: {exc}, headers={notify_headers}, payload_keys={list(payload.keys())}, payload={payload}"
            if "缺少签名" in verify_error:
                log.warning(message)
            else:
                log.error(message)
        if verify_result:
            log.info(f"云支付交易通知验签成功: {payload}")
        process_error = await PaymentService.handle_cloudpay_callback(
            db=db,
            payload=payload,
            signature=signature,
            verify_result=verify_result,
            verify_error=verify_error,
        )
        if process_error:
            return process_error
        return "success"
