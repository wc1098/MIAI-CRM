from typing import Any

from sqlalchemy import select

from app.api.v1.module_system.auth.schema import AuthSchema
from app.api.v1.module_system.dept.model import DeptModel
from app.core.exceptions import CustomException

from .client import CloudPayClient
from .schema import (
    CloudPayCreateSchema,
    CloudPayPaySchema,
    CloudPayPrecreateSchema,
    CloudPayQuerySchema,
    CloudPayRefundQuerySchema,
    CloudPayRefundSchema,
)


class CloudPayService:
    """
    云支付交易服务。
    """

    @staticmethod
    async def _get_top_store_merchant_id(auth: AuthSchema) -> str:
        result = await auth.db.execute(
            select(DeptModel).where(
                DeptModel.parent_id.is_(None),
                DeptModel.status == "0",
                DeptModel.is_deleted == False,
            )
        )
        stores = result.scalars().all()
        if not stores:
            raise CustomException(msg="云支付商户ID获取失败：请先配置一个启用的最顶级门店")
        if len(stores) > 1:
            raise CustomException(msg="云支付商户ID获取失败：存在多个启用的最顶级门店，请先整理门店树")
        if not stores[0].code:
            raise CustomException(msg="云支付商户ID获取失败：最顶级门店编码为空")
        return stores[0].code

    @staticmethod
    async def _get_store_id(auth: AuthSchema, dept_id: int) -> str:
        dept = await auth.db.get(DeptModel, dept_id)
        if not dept or dept.is_deleted:
            raise CustomException(msg="云支付门店ID获取失败：门店不存在")
        if dept.status != "0":
            raise CustomException(msg="云支付门店ID获取失败：门店已停用")
        return str(dept.id)

    @classmethod
    async def _with_store_mapping(
        cls,
        auth: AuthSchema,
        dept_id: int,
        biz_content: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            **biz_content,
            "cp_mid": await cls._get_top_store_merchant_id(auth),
            "cp_store_id": await cls._get_store_id(auth, dept_id),
        }

    @staticmethod
    def _drop_none(data: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in data.items() if value is not None and value != ""}

    @classmethod
    async def pay_service(cls, auth: AuthSchema, data: CloudPayPaySchema) -> dict[str, Any]:
        biz_content = await cls._with_store_mapping(
            auth,
            data.dept_id,
            {
                "out_order_no": data.out_order_no,
                "scene": data.scene,
                "total_amount": data.total_amount,
                "auth_code": data.auth_code,
                "subject": data.subject,
                "body": data.body,
                "operator_id": data.operator_id,
                "pay_channel": data.pay_channel,
                "notify_url": data.notify_url,
            },
        )
        return await CloudPayClient.execute(
            "ant.antfin.eco.cloudpay.trade.pay",
            cls._drop_none(biz_content),
        )

    @classmethod
    async def precreate_service(
        cls, auth: AuthSchema, data: CloudPayPrecreateSchema
    ) -> dict[str, Any]:
        biz_content = await cls._with_store_mapping(
            auth,
            data.dept_id,
            {
                "out_order_no": data.out_order_no,
                "total_amount": data.total_amount,
                "subject": data.subject,
                "body": data.body,
                "operator_id": data.operator_id,
                "pay_channel": data.pay_channel,
                "notify_url": data.notify_url,
            },
        )
        return await CloudPayClient.execute(
            "ant.antfin.eco.cloudpay.trade.precreate",
            cls._drop_none(biz_content),
        )

    @classmethod
    async def create_service(cls, auth: AuthSchema, data: CloudPayCreateSchema) -> dict[str, Any]:
        biz_content = await cls._with_store_mapping(
            auth,
            data.dept_id,
            {
                "out_order_no": data.out_order_no,
                "total_amount": data.total_amount,
                "buyer_id": data.buyer_id,
                "subject": data.subject,
                "body": data.body,
                "operator_id": data.operator_id,
                "pay_channel": data.pay_channel,
                "notify_url": data.notify_url,
                "sub_app_id": data.sub_app_id,
            },
        )
        return await CloudPayClient.execute(
            "ant.antfin.eco.cloudpay.trade.create",
            cls._drop_none(biz_content),
        )

    @classmethod
    async def query_service(cls, auth: AuthSchema, data: CloudPayQuerySchema) -> dict[str, Any]:
        biz_content = await cls._with_store_mapping(
            auth,
            data.dept_id,
            {
                "out_order_no": data.out_order_no,
                "trans_no": data.trans_no,
            },
        )
        return await CloudPayClient.execute(
            "ant.antfin.eco.cloudpay.trade.query",
            cls._drop_none(biz_content),
        )

    @classmethod
    async def refund_service(cls, auth: AuthSchema, data: CloudPayRefundSchema) -> dict[str, Any]:
        biz_content = await cls._with_store_mapping(
            auth,
            data.dept_id,
            {
                "out_order_no": data.out_order_no,
                "trans_no": data.trans_no,
                "refund_amount": data.refund_amount,
                "out_request_no": data.out_request_no,
                "refund_reason": data.refund_reason,
                "operator_id": data.operator_id,
                "pay_channel": data.pay_channel,
            },
        )
        return await CloudPayClient.execute(
            "ant.antfin.eco.cloudpay.trade.refund",
            cls._drop_none(biz_content),
        )

    @classmethod
    async def refund_query_service(
        cls, auth: AuthSchema, data: CloudPayRefundQuerySchema
    ) -> dict[str, Any]:
        biz_content = await cls._with_store_mapping(
            auth,
            data.dept_id,
            {
                "out_order_no": data.out_order_no,
                "out_request_no": data.out_request_no,
            },
        )
        return await CloudPayClient.execute(
            "ant.antfin.eco.cloudpay.trade.refund.query",
            cls._drop_none(biz_content),
        )
