import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.params.model import ParamsModel
from app.core.exceptions import CustomException
from app.core.logger import log
from app.plugin.module_cloudpay.trade.client import CloudPayClient

from .model import PaymentCallbackLogModel, PaymentOrderModel, PaymentRecordModel


class PaymentService:
    """统一支付订单服务。"""

    SUCCESS_TRADE_STATUSES = {"TRADE_SUCCESS", "SUCCESS", "PAY_SUCCESS", "ORDER_SUCCESS", "2"}

    @staticmethod
    def _order_no(prefix: str = "P") -> str:
        return f"{prefix}{datetime.now():%y%m%d%H%M%S}{uuid4().hex[:8].upper()}"

    @classmethod
    async def _param(cls, db: AsyncSession, key: str, default: str | None = None) -> str | None:
        result = await db.execute(
            select(ParamsModel.config_value).where(
                ParamsModel.config_key == key,
                ParamsModel.status == "0",
                ParamsModel.is_deleted == False,
            )
        )
        value = result.scalar()
        return value if value not in (None, "") else default

    @classmethod
    async def _top_dept_code(cls, db: AsyncSession, store_id: int) -> str:
        current_id: int | None = store_id
        top: DeptModel | None = None
        while current_id:
            result = await db.execute(select(DeptModel).where(DeptModel.id == current_id, DeptModel.is_deleted == False))
            dept = result.scalars().first()
            if not dept:
                break
            top = dept
            current_id = dept.parent_id
        if not top or not top.code:
            raise CustomException(msg="无法解析云支付商户门店编码")
        return top.code

    @classmethod
    async def _store_code(cls, db: AsyncSession, store_id: int) -> str:
        dept = await db.get(DeptModel, store_id)
        if not dept or dept.is_deleted:
            raise CustomException(msg="云支付门店ID获取失败：门店不存在")
        if dept.status != "0":
            raise CustomException(msg="云支付门店ID获取失败：门店已停用")
        if not dept.code:
            raise CustomException(msg="云支付门店ID获取失败：门店编码为空")
        return dept.code

    @classmethod
    async def create_order(
        cls,
        db: AsyncSession,
        *,
        biz_type: str,
        biz_id: int,
        subject: str,
        amount: Decimal,
        store_id: int | None = None,
        person_id: int | None = None,
        mp_user_id: int | None = None,
        expire_minutes: int = 24 * 60,
        extra: dict[str, Any] | None = None,
    ) -> PaymentOrderModel:
        order = PaymentOrderModel(
            brand_id=1,
            store_id=store_id,
            order_no=cls._order_no("P"),
            biz_type=biz_type,
            biz_id=biz_id,
            person_id=person_id,
            mp_user_id=mp_user_id,
            subject=subject[:255],
            amount=amount,
            payable_amount=amount,
            paid_amount=Decimal("0.00"),
            order_status="pending",
            pay_status="pending",
            channel="cloudpay",
            expire_at=datetime.now() + timedelta(minutes=expire_minutes),
            extra=extra,
        )
        db.add(order)
        await db.flush()
        return order

    @classmethod
    def _response_data(cls, response: dict[str, Any]) -> dict[str, Any] | list[Any] | str | None:
        data = response.get("data")
        if isinstance(data, str):
            try:
                return json.loads(data)
            except ValueError:
                return data
        if data is not None:
            return data
        for key, value in response.items():
            if key.endswith("_response") and isinstance(value, dict):
                return value
        return response

    @classmethod
    def _wechat_pay_payload(cls, response: dict[str, Any]) -> dict[str, str] | None:
        data = cls._response_data(response)
        if not isinstance(data, dict):
            return None
        time_stamp = data.get("timeStamp") or data.get("time_stamp")
        nonce_str = data.get("nonceStr") or data.get("nonce_str")
        package_info = data.get("package") or data.get("package_info")
        sign_type = data.get("signType") or data.get("sign_type")
        pay_sign = data.get("paySign") or data.get("pay_sign")
        if not all([time_stamp, nonce_str, package_info, sign_type, pay_sign]):
            return None
        return {
            "timeStamp": str(time_stamp),
            "nonceStr": str(nonce_str),
            "package": str(package_info),
            "signType": str(sign_type),
            "paySign": str(pay_sign),
        }

    @classmethod
    async def create_cloudpay_mp_payment(
        cls,
        db: AsyncSession,
        *,
        order: PaymentOrderModel,
        buyer_id: str,
        notify_url: str,
        sub_app_id: str | None = None,
    ) -> dict[str, Any]:
        if order.pay_status == "paid":
            raise CustomException(msg="订单已支付")
        if order.expire_at and datetime.now() >= order.expire_at:
            await cls.close_order(db, order)
            raise CustomException(msg="订单已超时，请重新报名")
        if not order.store_id:
            raise CustomException(msg="订单缺少归属门店，无法发起支付")

        payment = PaymentRecordModel(
            order_id=order.id,
            payment_no=cls._order_no("T"),
            channel="cloudpay",
            pay_method="wechat",
            amount=order.payable_amount,
            payment_status="pending",
            merchant_trade_no=order.order_no,
        )
        biz_content = {
            "cp_mid": await cls._top_dept_code(db, order.store_id),
            "cp_store_id": await cls._store_code(db, order.store_id),
            "out_order_no": order.order_no,
            "total_amount": f"{order.payable_amount:.2f}",
            "buyer_id": buyer_id,
            "subject": order.subject,
            "pay_channel": "wechat",
            "body": order.subject[:128],
            "notify_url": notify_url,
            "sub_app_id": sub_app_id or await cls._param(db, "miniprogram.wechat.app_id"),
        }
        log.info(
            f"云支付小程序下单参数: order_no={order.order_no}, "
            f"cp_mid={biz_content['cp_mid']}, cp_store_id={biz_content['cp_store_id']}"
        )
        payment.raw_request = biz_content
        db.add(payment)
        await db.flush()

        try:
            response = await CloudPayClient.execute("ant.antfin.eco.cloudpay.trade.create", biz_content)
        except CustomException as exc:
            payload = exc.data if isinstance(exc.data, dict) else {}
            if payload.get("code") == "40014" or "订单已支付" in exc.msg:
                payment.raw_response = payload or {"msg": exc.msg}
                payment.payment_status = "paid"
                await cls.mark_order_paid(
                    db,
                    order,
                    {
                        "out_order_no": order.order_no,
                        "total_amount": f"{order.payable_amount:.2f}",
                        "trade_status": "TRADE_SUCCESS",
                        "cloudpay_compensated": True,
                        "cloudpay_response": payload,
                    },
                    trade_no=None,
                )
                return {
                    "order_id": order.id,
                    "order_no": order.order_no,
                    "payment_id": payment.id,
                    "payment_no": payment.payment_no,
                    "expire_at": order.expire_at,
                    "pay_payload": None,
                    "wechat_pay": None,
                    "paid": True,
                    "message": "订单已支付，已同步业务状态",
                }
            raise
        payment.raw_response = response
        payment.payment_status = "created"
        order.pay_status = "processing"
        await db.flush()
        return {
            "order_id": order.id,
            "order_no": order.order_no,
            "payment_id": payment.id,
            "payment_no": payment.payment_no,
            "expire_at": order.expire_at,
            "pay_payload": cls._response_data(response),
            "wechat_pay": cls._wechat_pay_payload(response),
        }

    @classmethod
    async def close_order(cls, db: AsyncSession, order: PaymentOrderModel) -> None:
        if order.pay_status == "paid":
            return
        order.order_status = "closed"
        order.pay_status = "timeout"
        order.closed_at = datetime.now()
        await db.flush()

    @classmethod
    def _payload_order_no(cls, payload: dict[str, Any]) -> str | None:
        for key in ("out_order_no", "out_trade_no", "merchant_trade_no"):
            value = payload.get(key)
            if value:
                return str(value)
        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("out_order_no", "out_trade_no", "merchant_trade_no"):
                value = data.get(key)
                if value:
                    return str(value)
        return None

    @classmethod
    def _payload_trade_no(cls, payload: dict[str, Any]) -> str | None:
        for key in ("trans_no", "trade_no", "channel_trade_no"):
            value = payload.get(key)
            if value:
                return str(value)
        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("trans_no", "trade_no", "channel_trade_no"):
                value = data.get(key)
                if value:
                    return str(value)
        return None

    @classmethod
    def _payload_amount(cls, payload: dict[str, Any], default: Decimal) -> Decimal:
        for key in ("total_amount", "receipt_amount", "buyer_pay_amount"):
            value = payload.get(key)
            if value not in (None, ""):
                return Decimal(str(value))
        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("total_amount", "receipt_amount", "buyer_pay_amount"):
                value = data.get(key)
                if value not in (None, ""):
                    return Decimal(str(value))
        return default

    @classmethod
    def _payload_success(cls, payload: dict[str, Any]) -> bool:
        values = {
            str(payload.get(key) or "").upper()
            for key in ("trade_status", "order_status", "pay_status", "status")
        }
        data = payload.get("data")
        if isinstance(data, dict):
            values |= {
                str(data.get(key) or "").upper()
                for key in ("trade_status", "order_status", "pay_status", "status")
            }
        return bool(values & cls.SUCCESS_TRADE_STATUSES)

    @classmethod
    async def handle_cloudpay_callback(
        cls,
        db: AsyncSession,
        payload: dict[str, Any],
        verify_result: bool,
        verify_error: str | None = None,
    ) -> None:
        order_no = cls._payload_order_no(payload)
        trade_no = cls._payload_trade_no(payload)
        log = PaymentCallbackLogModel(
            channel="cloudpay",
            merchant_trade_no=order_no,
            channel_trade_no=trade_no,
            payload=payload,
            signature=payload.get("sign"),
            verify_result=verify_result,
            process_status="pending",
            received_at=datetime.now(),
        )
        db.add(log)
        await db.flush()
        try:
            if not verify_result:
                raise CustomException(msg=verify_error or "云支付通知验签失败")
            if not order_no:
                raise CustomException(msg="云支付通知缺少商户订单号")
            result = await db.execute(
                select(PaymentOrderModel).where(
                    PaymentOrderModel.order_no == order_no,
                    PaymentOrderModel.is_deleted == False,
                )
            )
            order = result.scalars().first()
            if not order:
                raise CustomException(msg="本地支付订单不存在")
            if cls._payload_success(payload):
                await cls.mark_order_paid(db, order, payload, trade_no)
            log.process_status = "success"
            log.processed_at = datetime.now()
        except Exception as exc:
            log.process_status = "failed"
            log.error_message = str(exc)
            log.processed_at = datetime.now()
            return

    @classmethod
    async def mark_order_paid(
        cls,
        db: AsyncSession,
        order: PaymentOrderModel,
        payload: dict[str, Any],
        trade_no: str | None,
    ) -> None:
        if order.pay_status == "paid":
            return
        paid_amount = cls._payload_amount(payload, order.payable_amount)
        now = datetime.now()
        order.order_status = "paid"
        order.pay_status = "paid"
        order.paid_amount = paid_amount
        order.paid_at = now
        result = await db.execute(
            select(PaymentRecordModel)
            .where(PaymentRecordModel.order_id == order.id, PaymentRecordModel.is_deleted == False)
            .order_by(PaymentRecordModel.id.desc())
        )
        record = result.scalars().first()
        if record:
            record.payment_status = "paid"
            record.channel_trade_no = trade_no or record.channel_trade_no
            record.raw_response = payload
            record.paid_at = now
        await db.flush()
        if order.biz_type == "event_registration":
            from app.plugin.module_mp.event.service import MpEventService

            await MpEventService.on_payment_success(db, order)
        elif order.biz_type == "contact_unlock":
            from app.plugin.module_mp.plaza.service import MpPlazaService

            await MpPlazaService.on_payment_success(db, order)
        elif order.biz_type == "subscription":
            from app.plugin.module_subscription.service import SubscriptionService

            await SubscriptionService.on_payment_success(db, order)
