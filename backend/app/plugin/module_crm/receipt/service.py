from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.module_system.auth.schema import AuthSchema
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.user.model import UserModel
from app.core.exceptions import CustomException
from app.plugin.module_crm.contract.model import (
    CrmContractModel,
    CrmContractReceiptModel,
    CrmVipProfileModel,
)
from app.plugin.module_crm.customer.model import CrmCustomerLifecycleModel, CrmCustomerProfileModel
from app.plugin.module_crm.lead.model import CrmPersonModel
from app.plugin.module_payment.core.model import PaymentOrderModel, PaymentRecordModel
from app.plugin.module_payment.core.service import PaymentService
from app.plugin.module_service.vip.model import ServiceCaseModel
from app.plugin.module_service.vip.service import VipService

from .schema import (
    BarcodePaySchema,
    BarcodeReceiptCreateSchema,
    OnlineReceiptCreateSchema,
    QrcodePaySchema,
    ReceiptContractSearchOutSchema,
    ReceiptCreateSchema,
    ReceiptOfflineConfirmSchema,
    ReceiptOutSchema,
    ReceiptPendingCreateSchema,
    ReceiptQueryParam,
    ReceiptRefundRegisterSchema,
    ReceiptReverseSchema,
    ReceiptReviewSchema,
    ReceiptSummaryOutSchema,
    ReceiptVoidSchema,
)


class ReceiptService:
    """CRM合同收款服务。"""

    CONFIRMED_STATUSES = {"approved", "refund_registered"}

    @classmethod
    async def _expire_overdue_contracts(cls, db: AsyncSession) -> None:
        await db.execute(
            update(CrmContractModel)
            .where(
                CrmContractModel.contract_status == "effective",
                CrmContractModel.end_date < date.today(),
                CrmContractModel.is_deleted == False,
            )
            .values(contract_status="expired", updated_time=datetime.now())
        )
        await db.flush()

    @classmethod
    def _role_codes(cls, auth: AuthSchema) -> set[str]:
        if not auth.user:
            return set()
        return {role.code for role in auth.user.roles or [] if role.status == "0"}

    @classmethod
    def _is_brand_admin(cls, auth: AuthSchema) -> bool:
        if auth.user and auth.user.is_superuser:
            return True
        return bool(cls._role_codes(auth) & {"ADMIN", "HQ_OPS"})

    @classmethod
    def _is_store_mgr(cls, auth: AuthSchema) -> bool:
        return "STORE_MGR" in cls._role_codes(auth)

    @classmethod
    def _is_finance(cls, auth: AuthSchema) -> bool:
        return "FINANCE" in cls._role_codes(auth)

    @classmethod
    def _is_matchmaker(cls, auth: AuthSchema) -> bool:
        return "MATCHMAKER" in cls._role_codes(auth)

    @classmethod
    def _can_review(cls, auth: AuthSchema) -> bool:
        return cls._is_brand_admin(auth) or cls._is_store_mgr(auth) or cls._is_finance(auth)

    @classmethod
    def _money(cls, value: Decimal | int | str) -> Decimal:
        return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def _stamp_create(cls, auth: AuthSchema, obj: Any) -> None:
        if auth.user:
            if hasattr(obj, "created_id"):
                obj.created_id = auth.user.id
            if hasattr(obj, "updated_id"):
                obj.updated_id = auth.user.id

    @classmethod
    def _stamp_update(cls, auth: AuthSchema, obj: Any) -> None:
        if auth.user and hasattr(obj, "updated_id"):
            obj.updated_id = auth.user.id

    @classmethod
    def _scope_conditions(cls, auth: AuthSchema) -> list[Any]:
        conditions: list[Any] = [CrmContractReceiptModel.is_deleted == False, CrmContractModel.is_deleted == False]
        if cls._is_brand_admin(auth) or cls._is_finance(auth):
            return conditions
        if not auth.user:
            conditions.append(CrmContractReceiptModel.id == -1)
            return conditions
        if cls._is_store_mgr(auth):
            conditions.append(CrmContractReceiptModel.store_id == (auth.user.dept_id or -1))
            return conditions
        if cls._is_matchmaker(auth):
            conditions.append(or_(CrmContractModel.owner_user_id == auth.user.id, CrmContractModel.customer_id.in_(cls._served_customer_ids(auth))))
        else:
            conditions.append(CrmContractModel.owner_user_id == auth.user.id)
        return conditions

    @classmethod
    def _contract_scope_conditions(cls, auth: AuthSchema) -> list[Any]:
        conditions: list[Any] = [CrmContractModel.is_deleted == False]
        if cls._is_brand_admin(auth) or cls._is_finance(auth):
            return conditions
        if not auth.user:
            conditions.append(CrmContractModel.id == -1)
            return conditions
        if cls._is_store_mgr(auth):
            conditions.append(CrmContractModel.store_id == (auth.user.dept_id or -1))
            return conditions
        if cls._is_matchmaker(auth):
            conditions.append(or_(CrmContractModel.owner_user_id == auth.user.id, CrmContractModel.customer_id.in_(cls._served_customer_ids(auth))))
        else:
            conditions.append(CrmContractModel.owner_user_id == auth.user.id)
        return conditions

    @classmethod
    def _served_customer_ids(cls, auth: AuthSchema):
        return select(ServiceCaseModel.customer_id).where(
            ServiceCaseModel.owner_matchmaker_id == auth.user.id,
            ServiceCaseModel.is_deleted == False,
            ServiceCaseModel.case_status.in_({"serving", "reopened", "pending_close_review"}),
        )

    @classmethod
    async def _is_serving_customer(cls, auth: AuthSchema, customer_id: int) -> bool:
        if not auth.user or not cls._is_matchmaker(auth):
            return False
        result = await auth.db.execute(cls._served_customer_ids(auth).where(ServiceCaseModel.customer_id == customer_id))
        return result.scalars().first() is not None

    @classmethod
    async def _ensure_contract_access(cls, auth: AuthSchema, contract: CrmContractModel) -> None:
        if cls._is_brand_admin(auth) or cls._is_finance(auth):
            return
        if not auth.user:
            raise CustomException(msg="无权访问合同")
        if cls._is_store_mgr(auth) and contract.store_id == auth.user.dept_id:
            return
        if contract.owner_user_id == auth.user.id:
            return
        if await cls._is_serving_customer(auth, contract.customer_id):
            return
        raise CustomException(msg="无权访问合同")

    @classmethod
    async def _get_contract(cls, auth: AuthSchema, contract_id: int) -> CrmContractModel:
        result = await auth.db.execute(
            select(CrmContractModel)
            .where(CrmContractModel.id == contract_id, CrmContractModel.is_deleted == False)
            .options(selectinload(CrmContractModel.customer), selectinload(CrmContractModel.person))
        )
        contract = result.scalars().first()
        if not contract:
            raise CustomException(msg="合同不存在")
        if contract.contract_status == "effective" and contract.end_date < date.today():
            contract.contract_status = "expired"
            contract.updated_time = datetime.now()
            await auth.db.flush()
        await cls._ensure_contract_access(auth, contract)
        return contract

    @classmethod
    async def _get_receipt(cls, auth: AuthSchema, receipt_id: int) -> tuple[CrmContractReceiptModel, CrmContractModel]:
        result = await auth.db.execute(
            select(CrmContractReceiptModel, CrmContractModel)
            .join(CrmContractModel, CrmContractReceiptModel.contract_id == CrmContractModel.id)
            .where(
                CrmContractReceiptModel.id == receipt_id,
                CrmContractReceiptModel.is_deleted == False,
                CrmContractModel.is_deleted == False,
            )
            .options(selectinload(CrmContractModel.customer), selectinload(CrmContractModel.person))
        )
        row = result.first()
        if not row:
            raise CustomException(msg="收款单不存在")
        receipt, contract = row
        await cls._ensure_contract_access(auth, contract)
        return receipt, contract

    @classmethod
    async def _generate_receipt_no(cls, db: AsyncSession, store_id: int) -> str:
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"RC-{store_id}-{today}-"
        result = await db.execute(
            select(func.count(CrmContractReceiptModel.id)).where(CrmContractReceiptModel.receipt_no.like(f"{prefix}%"))
        )
        seq = (result.scalar() or 0) + 1
        return f"{prefix}{seq:04d}"

    @classmethod
    async def _write_lifecycle(
        cls,
        db: AsyncSession,
        customer: CrmCustomerProfileModel,
        operation_type: str,
        change_detail: dict[str, Any] | None = None,
        remark: str | None = None,
        operator_user_id: int | None = None,
    ) -> None:
        record = CrmCustomerLifecycleModel(
            brand_id=customer.brand_id,
            customer_id=customer.id,
            person_id=customer.person_id,
            operation_type=operation_type,
            operator_user_id=operator_user_id,
            change_detail=change_detail,
            remark=remark,
        )
        if operator_user_id:
            record.created_id = operator_user_id
            record.updated_id = operator_user_id
        db.add(record)

    @classmethod
    def _active_amount(cls, receipt: CrmContractReceiptModel) -> Decimal:
        if receipt.receipt_status == "approved":
            return cls._money(receipt.amount)
        if receipt.receipt_status == "refund_registered":
            return cls._money(receipt.amount)
        return Decimal("0.00")

    @classmethod
    async def _contract_payment_summary(cls, db: AsyncSession, contract: CrmContractModel) -> tuple[Decimal, Decimal, str]:
        result = await db.execute(
            select(CrmContractReceiptModel).where(
                CrmContractReceiptModel.contract_id == contract.id,
                CrmContractReceiptModel.is_deleted == False,
            )
        )
        received_amount = sum((cls._active_amount(receipt) for receipt in result.scalars().all()), Decimal("0.00"))
        received_amount = max(cls._money(received_amount), Decimal("0.00"))
        contract_amount = cls._money(contract.contract_amount)
        pending_amount = max(contract_amount - received_amount, Decimal("0.00"))
        if received_amount <= 0:
            payment_status = "unpaid"
        elif contract_amount > 0 and received_amount >= contract_amount:
            payment_status = "settled"
        else:
            payment_status = "partial"
        return received_amount, pending_amount, payment_status

    @classmethod
    async def _ensure_receipt_amount(cls, db: AsyncSession, contract: CrmContractModel, amount: Decimal) -> Decimal:
        amount = cls._money(amount)
        _, pending_amount, _ = await cls._contract_payment_summary(db, contract)
        if amount <= 0:
            raise CustomException(msg="收款金额必须大于0")
        if amount > pending_amount:
            raise CustomException(msg="收款金额不能大于待收金额")
        return amount

    @classmethod
    async def _ensure_first_payment_receipt_type(
        cls,
        db: AsyncSession,
        contract: CrmContractModel,
        receipt_type: str,
    ) -> None:
        if receipt_type not in {"deposit", "full"}:
            return
        result = await db.execute(
            select(CrmContractReceiptModel.id).where(
                CrmContractReceiptModel.contract_id == contract.id,
                CrmContractReceiptModel.receipt_type.in_({"deposit", "full"}),
                CrmContractReceiptModel.receipt_status.in_({"pending", "pending_payment", "approved", "refund_registered"}),
                CrmContractReceiptModel.is_deleted == False,
            )
        )
        if result.scalars().first():
            raise CustomException(msg="该合同已有首款或全款收款记录，不能重复创建首付款")

    @classmethod
    async def _receipt_out(cls, db: AsyncSession, receipt: CrmContractReceiptModel) -> dict:
        result = await db.execute(
            select(CrmContractModel, CrmPersonModel)
            .join(CrmPersonModel, CrmContractModel.person_id == CrmPersonModel.id)
            .where(CrmContractModel.id == receipt.contract_id)
        )
        row = result.first()
        contract, person = row if row else (None, None)
        store = await db.get(DeptModel, receipt.store_id)
        user_ids = {
            value
            for value in [
                contract.owner_user_id if contract else None,
                receipt.reviewed_by,
                receipt.confirmed_by,
                receipt.voided_by,
            ]
            if value
        }
        users = {}
        if user_ids:
            user_result = await db.execute(select(UserModel.id, UserModel.name).where(UserModel.id.in_(user_ids)))
            users = {item[0]: item[1] for item in user_result.all()}
        order = await db.get(PaymentOrderModel, receipt.order_id) if receipt.order_id else None
        payment = await db.get(PaymentRecordModel, receipt.payment_id) if receipt.payment_id else None
        return ReceiptOutSchema(
            id=receipt.id,
            brand_id=receipt.brand_id,
            receipt_no=receipt.receipt_no,
            contract_id=receipt.contract_id,
            contract_no=contract.contract_no if contract else None,
            contract_name=contract.contract_name if contract else None,
            customer_id=receipt.customer_id,
            person_id=receipt.person_id,
            person_name=person.name if person else None,
            person_display_no=person.display_no if person else None,
            person_mobile=person.primary_mobile if person else None,
            store_id=receipt.store_id,
            store_name=store.name if store else None,
            owner_user_id=contract.owner_user_id if contract else None,
            owner_user_name=users.get(contract.owner_user_id) if contract else None,
            receipt_type=receipt.receipt_type,
            pay_method=receipt.pay_method,
            amount=receipt.amount,
            receipt_status=receipt.receipt_status,
            payment_scene=receipt.payment_scene,
            order_id=receipt.order_id,
            order_no=order.order_no if order else None,
            order_pay_status=order.pay_status if order else None,
            payment_id=receipt.payment_id,
            channel_trade_no=receipt.channel_trade_no or (payment.channel_trade_no if payment else None),
            submitted_at=receipt.submitted_at,
            reviewed_at=receipt.reviewed_at,
            reviewed_by=receipt.reviewed_by,
            reviewed_by_name=users.get(receipt.reviewed_by),
            review_remark=receipt.review_remark,
            paid_at=receipt.paid_at,
            confirmed_at=receipt.confirmed_at,
            confirmed_by=receipt.confirmed_by,
            confirmed_by_name=users.get(receipt.confirmed_by),
            voided_at=receipt.voided_at,
            voided_by=receipt.voided_by,
            voided_by_name=users.get(receipt.voided_by),
            void_reason=receipt.void_reason,
            reverse_receipt_id=receipt.reverse_receipt_id,
            reverse_reason=receipt.reverse_reason,
            payment_payload=receipt.payment_payload,
            remark=receipt.remark,
            created_time=receipt.created_time,
            updated_time=receipt.updated_time,
        ).model_dump()

    @classmethod
    async def page_service(cls, auth: AuthSchema, page_no: int, page_size: int, search: ReceiptQueryParam) -> dict:
        conditions = cls._scope_conditions(auth)
        if search.contract_id:
            conditions.append(CrmContractReceiptModel.contract_id == search.contract_id)
        if search.receipt_type:
            conditions.append(CrmContractReceiptModel.receipt_type == search.receipt_type)
        if search.payment_scene:
            conditions.append(CrmContractReceiptModel.payment_scene == search.payment_scene)
        if search.pay_method:
            conditions.append(CrmContractReceiptModel.pay_method == search.pay_method)
        if search.receipt_status:
            conditions.append(CrmContractReceiptModel.receipt_status == search.receipt_status)
        if search.store_id:
            conditions.append(CrmContractReceiptModel.store_id == search.store_id)
        if search.owner_user_id:
            conditions.append(CrmContractModel.owner_user_id == search.owner_user_id)
        if search.submitted_start:
            conditions.append(CrmContractReceiptModel.submitted_at >= search.submitted_start)
        if search.submitted_end:
            conditions.append(CrmContractReceiptModel.submitted_at <= search.submitted_end)
        if search.confirmed_start:
            conditions.append(CrmContractReceiptModel.confirmed_at >= search.confirmed_start)
        if search.confirmed_end:
            conditions.append(CrmContractReceiptModel.confirmed_at <= search.confirmed_end)
        if search.keyword:
            keyword = search.keyword.strip()
            like = f"%{keyword}%"
            conditions.append(
                or_(
                    CrmContractReceiptModel.receipt_no == keyword,
                    CrmContractReceiptModel.receipt_no.like(f"{keyword}%"),
                    CrmContractReceiptModel.receipt_no.like(like),
                    CrmContractModel.contract_no == keyword,
                    CrmContractModel.contract_no.like(f"{keyword}%"),
                    CrmContractModel.contract_no.like(like),
                    CrmContractModel.contract_name.like(like),
                    CrmPersonModel.name.like(like),
                    CrmPersonModel.primary_mobile == keyword,
                    CrmPersonModel.primary_mobile.like(f"{keyword}%"),
                    CrmPersonModel.primary_mobile.like(like),
                    CrmPersonModel.display_no == keyword,
                    CrmPersonModel.display_no.like(f"{keyword}%"),
                    CrmPersonModel.display_no.like(like),
                )
            )
        base = (
            select(CrmContractReceiptModel)
            .join(CrmContractModel, CrmContractReceiptModel.contract_id == CrmContractModel.id)
            .join(CrmPersonModel, CrmContractReceiptModel.person_id == CrmPersonModel.id)
            .where(*conditions)
        )
        total = (
            await auth.db.execute(
                select(func.count(CrmContractReceiptModel.id))
                .join(CrmContractModel, CrmContractReceiptModel.contract_id == CrmContractModel.id)
                .join(CrmPersonModel, CrmContractReceiptModel.person_id == CrmPersonModel.id)
                .where(*conditions)
            )
        ).scalar() or 0
        offset = (page_no - 1) * page_size
        result = await auth.db.execute(
            base.order_by(
                func.coalesce(CrmContractReceiptModel.submitted_at, CrmContractReceiptModel.created_time).desc(),
                CrmContractReceiptModel.id.desc(),
            )
            .offset(offset)
            .limit(page_size)
        )
        receipts = result.scalars().all()
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": offset + page_size < total,
            "items": [await cls._receipt_out(auth.db, receipt) for receipt in receipts],
        }

    @classmethod
    async def detail_service(cls, auth: AuthSchema, receipt_id: int) -> dict:
        receipt, _ = await cls._get_receipt(auth, receipt_id)
        return await cls._receipt_out(auth.db, receipt)

    @classmethod
    async def contract_search_service(cls, auth: AuthSchema, keyword: str | None = None, limit: int = 20) -> list[dict]:
        await cls._expire_overdue_contracts(auth.db)
        conditions = cls._contract_scope_conditions(auth)
        conditions.append(CrmContractModel.contract_status.in_(["pending_payment", "effective"]))
        if keyword:
            keyword_value = keyword.strip()
            like = f"%{keyword_value}%"
            conditions.append(
                or_(
                    CrmContractModel.contract_no == keyword_value,
                    CrmContractModel.contract_no.like(f"{keyword_value}%"),
                    CrmContractModel.contract_no.like(like),
                    CrmContractModel.contract_name.like(like),
                    CrmPersonModel.name.like(like),
                    CrmPersonModel.primary_mobile == keyword_value,
                    CrmPersonModel.primary_mobile.like(f"{keyword_value}%"),
                    CrmPersonModel.primary_mobile.like(like),
                    CrmPersonModel.display_no == keyword_value,
                    CrmPersonModel.display_no.like(f"{keyword_value}%"),
                    CrmPersonModel.display_no.like(like),
                )
            )
        result = await auth.db.execute(
            select(CrmContractModel, CrmPersonModel)
            .join(CrmPersonModel, CrmContractModel.person_id == CrmPersonModel.id)
            .where(*conditions)
            .order_by(CrmContractModel.updated_time.desc(), CrmContractModel.id.desc())
            .limit(min(limit, 50))
        )
        rows = result.unique().all()
        store_ids = {contract.store_id for contract, _ in rows if contract.store_id}
        owner_user_ids = {contract.owner_user_id for contract, _ in rows if contract.owner_user_id}
        stores = {}
        if store_ids:
            store_result = await auth.db.execute(select(DeptModel.id, DeptModel.name).where(DeptModel.id.in_(store_ids)))
            stores = {item[0]: item[1] for item in store_result.all()}
        users = {}
        if owner_user_ids:
            user_result = await auth.db.execute(select(UserModel.id, UserModel.name).where(UserModel.id.in_(owner_user_ids)))
            users = {item[0]: item[1] for item in user_result.all()}
        items = []
        for contract, person in rows:
            received_amount, pending_amount, payment_status = await cls._contract_payment_summary(auth.db, contract)
            if pending_amount <= 0:
                continue
            items.append(
                ReceiptContractSearchOutSchema(
                    id=contract.id,
                    contract_no=contract.contract_no,
                    contract_name=contract.contract_name,
                    contract_status=contract.contract_status,
                    contract_amount=contract.contract_amount,
                    received_amount=received_amount,
                    pending_amount=pending_amount,
                    payment_status=payment_status,
                    customer_id=contract.customer_id,
                    person_id=contract.person_id,
                    person_name=person.name,
                    person_display_no=person.display_no,
                    person_mobile=person.primary_mobile,
                    store_id=contract.store_id,
                    store_name=stores.get(contract.store_id),
                    owner_user_id=contract.owner_user_id,
                    owner_user_name=users.get(contract.owner_user_id),
                ).model_dump()
            )
        return items

    @classmethod
    def _ensure_receivable_contract(cls, contract: CrmContractModel) -> None:
        if contract.contract_status not in {"pending_payment", "effective"}:
            raise CustomException(msg="只有待收款或已生效合同可以收款")

    @classmethod
    async def _create_payment_order(
        cls,
        auth: AuthSchema,
        contract: CrmContractModel,
        receipt: CrmContractReceiptModel,
    ) -> PaymentOrderModel:
        order = await PaymentService.create_order(
            auth.db,
            biz_type="contract_receipt",
            biz_id=receipt.id,
            subject=f"{contract.contract_no} 合同收款",
            amount=receipt.amount,
            store_id=contract.store_id,
            person_id=contract.person_id,
            expire_minutes=30,
            extra={"contract_id": contract.id, "receipt_no": receipt.receipt_no, "receipt_type": receipt.receipt_type},
        )
        receipt.order_id = order.id
        return order

    @classmethod
    async def create_offline_service(cls, auth: AuthSchema, contract_id: int, data: ReceiptCreateSchema) -> dict:
        contract = await cls._get_contract(auth, contract_id)
        cls._ensure_receivable_contract(contract)
        await cls._ensure_first_payment_receipt_type(auth.db, contract, data.receipt_type)
        amount = await cls._ensure_receipt_amount(auth.db, contract, data.amount)
        receipt = CrmContractReceiptModel(
            brand_id=contract.brand_id,
            receipt_no=await cls._generate_receipt_no(auth.db, contract.store_id),
            contract_id=contract.id,
            customer_id=contract.customer_id,
            person_id=contract.person_id,
            store_id=contract.store_id,
            receipt_type=data.receipt_type,
            pay_method=data.pay_method,
            amount=amount,
            receipt_status="pending",
            payment_scene="offline",
            remark=data.remark,
        )
        cls._stamp_create(auth, receipt)
        auth.db.add(receipt)
        await cls._write_lifecycle(
            auth.db,
            contract.customer,
            "contract_receipt_submit",
            {"contract_no": contract.contract_no, "receipt_type": receipt.receipt_type, "amount": str(receipt.amount)},
            "提交线下收款",
            auth.user.id if auth.user else None,
        )
        await auth.db.flush()
        return await cls._receipt_out(auth.db, receipt)

    @classmethod
    async def create_pending_service(cls, auth: AuthSchema, contract_id: int, data: ReceiptPendingCreateSchema) -> dict:
        contract = await cls._get_contract(auth, contract_id)
        cls._ensure_receivable_contract(contract)
        await cls._ensure_first_payment_receipt_type(auth.db, contract, data.receipt_type)
        amount = await cls._ensure_receipt_amount(auth.db, contract, data.amount)
        receipt = CrmContractReceiptModel(
            brand_id=contract.brand_id,
            receipt_no=await cls._generate_receipt_no(auth.db, contract.store_id),
            contract_id=contract.id,
            customer_id=contract.customer_id,
            person_id=contract.person_id,
            store_id=contract.store_id,
            receipt_type=data.receipt_type,
            pay_method="pending",
            amount=amount,
            receipt_status="pending_payment",
            payment_scene="pending",
            remark=data.remark,
        )
        cls._stamp_create(auth, receipt)
        auth.db.add(receipt)
        await cls._write_lifecycle(
            auth.db,
            contract.customer,
            "contract_receipt_submit",
            {"contract_no": contract.contract_no, "receipt_type": receipt.receipt_type, "amount": str(receipt.amount)},
            "创建待收款单",
            auth.user.id if auth.user else None,
        )
        await auth.db.flush()
        return await cls._receipt_out(auth.db, receipt)

    @classmethod
    async def create_online_service(cls, auth: AuthSchema, contract_id: int, data: OnlineReceiptCreateSchema, notify_url: str) -> dict:
        contract = await cls._get_contract(auth, contract_id)
        cls._ensure_receivable_contract(contract)
        await cls._ensure_first_payment_receipt_type(auth.db, contract, data.receipt_type)
        amount = await cls._ensure_receipt_amount(auth.db, contract, data.amount)
        receipt = CrmContractReceiptModel(
            brand_id=contract.brand_id,
            receipt_no=await cls._generate_receipt_no(auth.db, contract.store_id),
            contract_id=contract.id,
            customer_id=contract.customer_id,
            person_id=contract.person_id,
            store_id=contract.store_id,
            receipt_type=data.receipt_type,
            pay_method=data.pay_channel,
            amount=amount,
            receipt_status="pending_payment",
            payment_scene="qrcode",
            remark=data.remark,
        )
        cls._stamp_create(auth, receipt)
        auth.db.add(receipt)
        await auth.db.flush()
        order = await PaymentService.create_order(
            auth.db,
            biz_type="contract_receipt",
            biz_id=receipt.id,
            subject=f"{contract.contract_no} 合同收款",
            amount=amount,
            store_id=contract.store_id,
            person_id=contract.person_id,
            expire_minutes=30,
            extra={"contract_id": contract.id, "receipt_no": receipt.receipt_no, "receipt_type": receipt.receipt_type},
        )
        receipt.order_id = order.id
        payment = await PaymentService.create_cloudpay_precreate_payment(
            auth.db,
            order=order,
            pay_channel=data.pay_channel,
            notify_url=notify_url,
            operator_id=data.operator_id,
        )
        receipt.payment_id = payment.get("payment_id")
        receipt.payment_payload = {"create_response": payment}
        cls._stamp_update(auth, receipt)
        await auth.db.flush()
        return {"receipt": await cls._receipt_out(auth.db, receipt), "payment": payment}

    @classmethod
    async def qrcode_pay_service(cls, auth: AuthSchema, receipt_id: int, data: QrcodePaySchema, notify_url: str) -> dict:
        receipt, contract = await cls._get_receipt(auth, receipt_id)
        if receipt.receipt_status != "pending_payment":
            raise CustomException(msg="只有待支付收款单可以发起扫码支付")
        order = await cls._create_payment_order(auth, contract, receipt)
        payment = await PaymentService.create_cloudpay_precreate_payment(
            auth.db,
            order=order,
            pay_channel=data.pay_channel,
            notify_url=notify_url,
            operator_id=data.operator_id,
        )
        receipt.pay_method = data.pay_channel
        receipt.payment_scene = "qrcode"
        receipt.payment_id = payment.get("payment_id")
        payload = receipt.payment_payload if isinstance(receipt.payment_payload, dict) else {}
        receipt.payment_payload = {**payload, "create_response": payment}
        cls._stamp_update(auth, receipt)
        await auth.db.flush()
        return {"receipt": await cls._receipt_out(auth.db, receipt), "payment": payment}

    @classmethod
    async def offline_confirm_service(cls, auth: AuthSchema, receipt_id: int, data: ReceiptOfflineConfirmSchema) -> dict:
        receipt, contract = await cls._get_receipt(auth, receipt_id)
        if receipt.receipt_status != "pending_payment":
            raise CustomException(msg="只有待支付收款单可以转线下确认")
        receipt.pay_method = data.pay_method
        receipt.payment_scene = "offline"
        receipt.receipt_status = "pending"
        receipt.remark = data.remark or receipt.remark
        cls._stamp_update(auth, receipt)
        await cls._write_lifecycle(
            auth.db,
            contract.customer,
            "contract_receipt_submit",
            {"contract_no": contract.contract_no, "receipt_type": receipt.receipt_type, "amount": str(receipt.amount)},
            "提交线下收款",
            auth.user.id if auth.user else None,
        )
        await auth.db.flush()
        return await cls._receipt_out(auth.db, receipt)

    @classmethod
    async def create_barcode_service(cls, auth: AuthSchema, contract_id: int, data: BarcodeReceiptCreateSchema, notify_url: str) -> dict:
        contract = await cls._get_contract(auth, contract_id)
        cls._ensure_receivable_contract(contract)
        await cls._ensure_first_payment_receipt_type(auth.db, contract, data.receipt_type)
        amount = await cls._ensure_receipt_amount(auth.db, contract, data.amount)
        receipt = CrmContractReceiptModel(
            brand_id=contract.brand_id,
            receipt_no=await cls._generate_receipt_no(auth.db, contract.store_id),
            contract_id=contract.id,
            customer_id=contract.customer_id,
            person_id=contract.person_id,
            store_id=contract.store_id,
            receipt_type=data.receipt_type,
            pay_method=data.pay_channel,
            amount=amount,
            receipt_status="pending_payment",
            payment_scene="barcode",
            remark=data.remark,
        )
        cls._stamp_create(auth, receipt)
        auth.db.add(receipt)
        await auth.db.flush()
        order = await PaymentService.create_order(
            auth.db,
            biz_type="contract_receipt",
            biz_id=receipt.id,
            subject=f"{contract.contract_no} 合同收款",
            amount=amount,
            store_id=contract.store_id,
            person_id=contract.person_id,
            expire_minutes=30,
            extra={"contract_id": contract.id, "receipt_no": receipt.receipt_no, "receipt_type": receipt.receipt_type},
        )
        receipt.order_id = order.id
        payment = await PaymentService.create_cloudpay_barcode_payment(
            auth.db,
            order=order,
            auth_code=data.auth_code,
            pay_channel=data.pay_channel,
            notify_url=notify_url,
            operator_id=data.operator_id,
        )
        receipt.payment_id = payment.get("payment_id")
        receipt.payment_payload = {"barcode_response": payment}
        cls._stamp_update(auth, receipt)
        await auth.db.flush()
        return {"receipt": await cls._receipt_out(auth.db, receipt), "payment": payment}

    @classmethod
    async def barcode_pay_service(cls, auth: AuthSchema, receipt_id: int, data: BarcodePaySchema, notify_url: str) -> dict:
        receipt, _ = await cls._get_receipt(auth, receipt_id)
        contract = _
        if receipt.receipt_status not in {"pending_payment"}:
            raise CustomException(msg="只有待支付收款单可以发起条码支付")
        if not receipt.order_id:
            order = await cls._create_payment_order(auth, contract, receipt)
        else:
            order = await auth.db.get(PaymentOrderModel, receipt.order_id)
            if not order or order.is_deleted:
                raise CustomException(msg="支付订单不存在")
        payment = await PaymentService.create_cloudpay_barcode_payment(
            auth.db,
            order=order,
            auth_code=data.auth_code,
            pay_channel=data.pay_channel,
            notify_url=notify_url,
            operator_id=data.operator_id,
        )
        receipt.pay_method = data.pay_channel or receipt.pay_method
        receipt.payment_scene = "barcode"
        receipt.payment_id = payment.get("payment_id")
        payload = receipt.payment_payload if isinstance(receipt.payment_payload, dict) else {}
        receipt.payment_payload = {**payload, "barcode_response": payment}
        cls._stamp_update(auth, receipt)
        await auth.db.flush()
        return {"receipt": await cls._receipt_out(auth.db, receipt), "payment": payment}

    @classmethod
    async def review_service(cls, auth: AuthSchema, receipt_id: int, data: ReceiptReviewSchema) -> dict:
        if not cls._can_review(auth):
            raise CustomException(msg="无权复核收款")
        receipt, contract = await cls._get_receipt(auth, receipt_id)
        if receipt.payment_scene != "offline":
            raise CustomException(msg="在线收款不需要人工复核")
        if receipt.receipt_status != "pending":
            raise CustomException(msg="该收款记录已复核")
        if data.approved:
            await cls._confirm_receipt(
                auth.db,
                contract,
                receipt,
                operator_user_id=auth.user.id if auth.user else None,
                payload={"review_remark": data.review_remark},
            )
        else:
            receipt.receipt_status = "rejected"
            receipt.reviewed_at = datetime.now()
            receipt.reviewed_by = auth.user.id if auth.user else None
            receipt.review_remark = data.review_remark
            cls._stamp_update(auth, receipt)
            await cls._write_lifecycle(
                auth.db,
                contract.customer,
                "contract_receipt_review",
                {"contract_no": contract.contract_no, "receipt_no": receipt.receipt_no, "approved": False},
                data.review_remark,
                auth.user.id if auth.user else None,
            )
        await auth.db.flush()
        return await cls._receipt_out(auth.db, receipt)

    @classmethod
    async def void_service(cls, auth: AuthSchema, receipt_id: int, data: ReceiptVoidSchema) -> dict:
        receipt, contract = await cls._get_receipt(auth, receipt_id)
        if receipt.receipt_status in {"approved", "reversed", "refund_registered"}:
            raise CustomException(msg="已确认收款不能作废，请使用冲正或退款登记")
        if receipt.receipt_status == "voided":
            raise CustomException(msg="收款单已作废")
        receipt.receipt_status = "voided"
        receipt.voided_at = datetime.now()
        receipt.voided_by = auth.user.id if auth.user else None
        receipt.void_reason = data.reason
        cls._stamp_update(auth, receipt)
        await cls._write_lifecycle(
            auth.db,
            contract.customer,
            "contract_receipt_void",
            {"contract_no": contract.contract_no, "receipt_no": receipt.receipt_no},
            data.reason,
            auth.user.id if auth.user else None,
        )
        await auth.db.flush()
        return await cls._receipt_out(auth.db, receipt)

    @classmethod
    async def reverse_service(cls, auth: AuthSchema, receipt_id: int, data: ReceiptReverseSchema) -> dict:
        if not cls._can_review(auth):
            raise CustomException(msg="无权冲正收款")
        receipt, contract = await cls._get_receipt(auth, receipt_id)
        if receipt.receipt_status != "approved":
            raise CustomException(msg="只有已确认收款可以冲正")
        receipt.receipt_status = "reversed"
        receipt.reverse_reason = data.reason
        cls._stamp_update(auth, receipt)
        reverse = CrmContractReceiptModel(
            brand_id=receipt.brand_id,
            receipt_no=await cls._generate_receipt_no(auth.db, receipt.store_id),
            contract_id=receipt.contract_id,
            customer_id=receipt.customer_id,
            person_id=receipt.person_id,
            store_id=receipt.store_id,
            receipt_type=receipt.receipt_type,
            pay_method=receipt.pay_method,
            amount=-cls._money(receipt.amount),
            receipt_status="approved",
            payment_scene="reverse",
            paid_at=datetime.now(),
            confirmed_at=datetime.now(),
            confirmed_by=auth.user.id if auth.user else None,
            reverse_receipt_id=receipt.id,
            reverse_reason=data.reason,
            remark="收款冲正",
        )
        cls._stamp_create(auth, reverse)
        auth.db.add(reverse)
        await cls._write_lifecycle(
            auth.db,
            contract.customer,
            "contract_receipt_reverse",
            {"contract_no": contract.contract_no, "receipt_no": receipt.receipt_no, "reverse_receipt_no": reverse.receipt_no},
            data.reason,
            auth.user.id if auth.user else None,
        )
        await auth.db.flush()
        return await cls._receipt_out(auth.db, reverse)

    @classmethod
    async def refund_register_service(cls, auth: AuthSchema, receipt_id: int, data: ReceiptRefundRegisterSchema) -> dict:
        if not cls._can_review(auth):
            raise CustomException(msg="无权登记退款")
        receipt, contract = await cls._get_receipt(auth, receipt_id)
        if receipt.receipt_status not in {"approved", "reversed"}:
            raise CustomException(msg="只有已确认收款可以登记退款")
        refund = CrmContractReceiptModel(
            brand_id=receipt.brand_id,
            receipt_no=await cls._generate_receipt_no(auth.db, receipt.store_id),
            contract_id=receipt.contract_id,
            customer_id=receipt.customer_id,
            person_id=receipt.person_id,
            store_id=receipt.store_id,
            receipt_type="refund",
            pay_method=receipt.pay_method,
            amount=-cls._money(data.amount),
            receipt_status="refund_registered",
            payment_scene="refund_register",
            paid_at=datetime.now(),
            confirmed_at=datetime.now(),
            confirmed_by=auth.user.id if auth.user else None,
            reverse_receipt_id=receipt.id,
            reverse_reason=data.reason,
            remark="退款登记",
        )
        cls._stamp_create(auth, refund)
        auth.db.add(refund)
        await cls._write_lifecycle(
            auth.db,
            contract.customer,
            "contract_receipt_refund_register",
            {"contract_no": contract.contract_no, "receipt_no": receipt.receipt_no, "refund_receipt_no": refund.receipt_no, "amount": str(refund.amount)},
            data.reason,
            auth.user.id if auth.user else None,
        )
        await auth.db.flush()
        return await cls._receipt_out(auth.db, refund)

    @classmethod
    async def summary_service(cls, auth: AuthSchema, contract_id: int | None = None) -> dict:
        conditions = cls._scope_conditions(auth)
        if contract_id:
            conditions.append(CrmContractReceiptModel.contract_id == contract_id)
        result = await auth.db.execute(
            select(CrmContractReceiptModel, CrmContractModel)
            .join(CrmContractModel, CrmContractReceiptModel.contract_id == CrmContractModel.id)
            .where(*conditions)
        )
        rows = result.all()
        contract_amount = Decimal("0.00")
        if contract_id:
            contract = await cls._get_contract(auth, contract_id)
            contract_amount = cls._money(contract.contract_amount)
        else:
            contracts = {contract.id: contract for _, contract in rows}
            contract_amount = sum((cls._money(contract.contract_amount) for contract in contracts.values()), Decimal("0.00"))
        received_amount = sum((cls._active_amount(receipt) for receipt, _ in rows), Decimal("0.00"))
        first_payment_received = any(receipt.receipt_status == "approved" and receipt.receipt_type in {"deposit", "full"} for receipt, _ in rows)
        pending_amount = max(contract_amount - received_amount, Decimal("0.00"))
        return ReceiptSummaryOutSchema(
            contract_id=contract_id,
            contract_amount=contract_amount,
            received_amount=cls._money(received_amount),
            pending_amount=cls._money(pending_amount),
            first_payment_received=first_payment_received,
            balance_paid=contract_amount > 0 and received_amount >= contract_amount,
        ).model_dump()

    @classmethod
    async def _confirm_receipt(
        cls,
        db: AsyncSession,
        contract: CrmContractModel,
        receipt: CrmContractReceiptModel,
        operator_user_id: int | None = None,
        payload: dict[str, Any] | None = None,
        channel_trade_no: str | None = None,
    ) -> None:
        if receipt.receipt_status == "approved":
            return
        if receipt.receipt_status in {"voided", "reversed", "refund_registered"}:
            raise CustomException(msg="收款单状态不可确认")
        now = datetime.now()
        receipt.receipt_status = "approved"
        receipt.reviewed_at = receipt.reviewed_at or now
        receipt.reviewed_by = receipt.reviewed_by or operator_user_id
        receipt.paid_at = receipt.paid_at or now
        receipt.confirmed_at = now
        receipt.confirmed_by = operator_user_id
        receipt.channel_trade_no = channel_trade_no or receipt.channel_trade_no
        receipt.payment_payload = payload or receipt.payment_payload
        if operator_user_id:
            receipt.updated_id = operator_user_id
        if receipt.receipt_type in {"deposit", "full"} and contract.contract_status in {"signed", "pending_payment"}:
            await cls._activate_contract(db, contract, receipt, operator_user_id)
        else:
            await cls._write_lifecycle(
                db,
                contract.customer,
                "contract_receipt_confirm",
                {"contract_no": contract.contract_no, "receipt_no": receipt.receipt_no, "receipt_type": receipt.receipt_type, "amount": str(receipt.amount)},
                "收款已确认",
                operator_user_id,
            )

    @classmethod
    async def _activate_contract(
        cls,
        db: AsyncSession,
        contract: CrmContractModel,
        receipt: CrmContractReceiptModel,
        operator_user_id: int | None = None,
    ) -> None:
        now = datetime.now()
        contract.contract_status = "effective"
        contract.effective_at = contract.effective_at or now
        contract.first_paid_at = contract.first_paid_at or now
        if operator_user_id:
            contract.updated_id = operator_user_id
        exists = await db.execute(
            select(CrmVipProfileModel.id).where(CrmVipProfileModel.contract_id == contract.id, CrmVipProfileModel.is_deleted == False)
        )
        vip_id = exists.scalars().first()
        if not vip_id:
            vip = CrmVipProfileModel(
                brand_id=contract.brand_id,
                person_id=contract.person_id,
                customer_id=contract.customer_id,
                contract_id=contract.id,
                store_id=contract.store_id,
                vip_level=contract.vip_level,
                started_at=now,
                source_receipt_id=receipt.id,
            )
            if operator_user_id:
                vip.created_id = operator_user_id
                vip.updated_id = operator_user_id
            db.add(vip)
            await db.flush()
        else:
            vip = await db.get(CrmVipProfileModel, vip_id)
        await VipService.ensure_service_case_for_contract(db=db, contract=contract, vip=vip, operator_user_id=operator_user_id)
        contract.customer.current_stage = "converted_vip"
        contract.customer.max_stage = "converted_vip"
        contract.customer.ended_at = contract.customer.ended_at or now
        contract.customer.end_reason = contract.customer.end_reason or "converted_vip"
        contract.customer.converted_vip_at = contract.customer.converted_vip_at or now
        await cls._write_lifecycle(
            db,
            contract.customer,
            "contract_first_payment_effective",
            {"contract_no": contract.contract_no, "receipt_no": receipt.receipt_no, "vip_level": contract.vip_level},
            "首付款确认，合同生效并转VIP",
            operator_user_id,
        )

    @classmethod
    async def on_payment_success(
        cls,
        db: AsyncSession,
        order: PaymentOrderModel,
        payload: dict[str, Any],
        trade_no: str | None,
    ) -> None:
        result = await db.execute(
            select(CrmContractReceiptModel, CrmContractModel)
            .join(CrmContractModel, CrmContractReceiptModel.contract_id == CrmContractModel.id)
            .where(
                CrmContractReceiptModel.id == order.biz_id,
                CrmContractReceiptModel.order_id == order.id,
                CrmContractReceiptModel.is_deleted == False,
                CrmContractModel.is_deleted == False,
            )
            .options(selectinload(CrmContractModel.customer), selectinload(CrmContractModel.person))
        )
        row = result.first()
        if not row:
            raise CustomException(msg="合同收款单不存在")
        receipt, contract = row
        if cls._money(order.paid_amount) != cls._money(receipt.amount):
            raise CustomException(msg="支付金额与收款单金额不一致")
        await cls._confirm_receipt(db, contract, receipt, payload=payload, channel_trade_no=trade_no)
        await db.flush()
