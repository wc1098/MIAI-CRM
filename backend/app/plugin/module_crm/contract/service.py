from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import selectinload

from app.api.v1.module_system.auth.schema import AuthSchema
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.user.model import UserModel
from app.core.exceptions import CustomException
from app.plugin.module_crm.customer.model import CrmCustomerLifecycleModel, CrmCustomerProfileModel
from app.plugin.module_crm.lead.model import CrmPersonModel
from app.plugin.module_crm.product.model import CrmProductPackageModel
from app.plugin.module_service.vip.model import ServiceCaseModel

from .model import (
    CrmContractAttachmentModel,
    CrmContractItemModel,
    CrmContractModel,
    CrmContractReceiptModel,
    CrmContractStoreRuleModel,
)
from .schema import (
    ContractAttachmentOutSchema,
    ContractAttachmentSaveSchema,
    ContractCreateSchema,
    ContractItemOutSchema,
    ContractQueryParam,
    ContractReceiptOutSchema,
    ContractReviewSchema,
    ContractSignSchema,
    ContractStoreRuleSchema,
    ContractUpdateSchema,
    ContractVoidSchema,
    CustomerSearchOutSchema,
)


class ContractService:
    """CRM合同服务层"""

    @classmethod
    async def _expire_overdue_contracts(cls, auth: AuthSchema) -> None:
        await auth.db.execute(
            update(CrmContractModel)
            .where(
                CrmContractModel.contract_status == "effective",
                CrmContractModel.end_date < date.today(),
                CrmContractModel.is_deleted == False,
            )
            .values(contract_status="expired", updated_time=datetime.now())
        )
        await auth.db.flush()

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
    def _can_review_contract(cls, auth: AuthSchema) -> bool:
        return cls._is_brand_admin(auth) or bool(cls._role_codes(auth) & {"STORE_MGR", "FINANCE", "RECEPTION"})

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
    def _money(cls, value: Decimal | int | str) -> Decimal:
        return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def _active_receipt_amount(cls, receipt: CrmContractReceiptModel) -> Decimal:
        if receipt.is_deleted:
            return Decimal("0.00")
        if receipt.receipt_status in {"approved", "refund_registered"}:
            return cls._money(receipt.amount)
        return Decimal("0.00")

    @classmethod
    def _payment_summary(cls, contract: CrmContractModel) -> tuple[Decimal, Decimal, Decimal, str]:
        received_amount = sum((cls._active_receipt_amount(receipt) for receipt in contract.receipts or []), Decimal("0.00"))
        received_amount = max(cls._money(received_amount), Decimal("0.00"))
        contract_amount = cls._money(contract.contract_amount)
        if contract_amount <= 0:
            progress = Decimal("100.00") if received_amount > 0 else Decimal("0.00")
        else:
            progress = min((received_amount / contract_amount * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), Decimal("100.00"))
        pending_amount = max(contract_amount - received_amount, Decimal("0.00"))
        if received_amount <= 0:
            payment_status = "unpaid"
        elif contract_amount > 0 and received_amount >= contract_amount:
            payment_status = "settled"
        else:
            payment_status = "partial"
        return received_amount, pending_amount, progress, payment_status

    @classmethod
    def _scope_conditions(cls, auth: AuthSchema) -> list[Any]:
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
    async def _ensure_customer_access(cls, auth: AuthSchema, customer: CrmCustomerProfileModel) -> None:
        if cls._is_brand_admin(auth):
            return
        if not auth.user:
            raise CustomException(msg="无权访问客户")
        if cls._is_store_mgr(auth) and customer.store_id == auth.user.dept_id:
            return
        if customer.owner_user_id == auth.user.id:
            return
        if await cls._is_serving_customer(auth, customer.id):
            return
        raise CustomException(msg="无权访问客户")

    @classmethod
    async def _ensure_actual_store(cls, auth: AuthSchema, store_id: int) -> None:
        store = await auth.db.get(DeptModel, store_id)
        if not store or store.is_deleted or store.status != "0":
            raise CustomException(msg="门店不存在或已停用")
        if store.parent_id is None:
            raise CustomException(msg="合同规则只能配置实际门店，不能配置品牌/总部节点")

    @classmethod
    async def _ensure_store_rule_access(cls, auth: AuthSchema, store_id: int, action: str) -> None:
        if cls._is_brand_admin(auth):
            return
        if cls._is_store_mgr(auth) and auth.user and auth.user.dept_id == store_id:
            return
        raise CustomException(msg=f"无权限{action}门店合同规则", code=10403, status_code=403)

    @classmethod
    async def _store_rule_by_db(cls, auth: AuthSchema, store_id: int) -> CrmContractStoreRuleModel:
        result = await auth.db.execute(
            select(CrmContractStoreRuleModel).where(
                CrmContractStoreRuleModel.store_id == store_id,
                CrmContractStoreRuleModel.is_deleted == False,
            )
        )
        rule = result.scalars().first()
        if rule:
            return rule
        rule = CrmContractStoreRuleModel(store_id=store_id, require_contract_review=True)
        cls._stamp_create(auth, rule)
        auth.db.add(rule)
        await auth.db.flush()
        return rule

    @classmethod
    async def _requires_contract_review(cls, auth: AuthSchema, store_id: int) -> bool:
        rule = await cls._store_rule_by_db(auth, store_id)
        return bool(rule.require_contract_review)

    @classmethod
    async def _get_contract(cls, auth: AuthSchema, id: int) -> CrmContractModel:
        result = await auth.db.execute(
            select(CrmContractModel)
            .where(CrmContractModel.id == id, CrmContractModel.is_deleted == False)
            .options(
                selectinload(CrmContractModel.customer),
                selectinload(CrmContractModel.person),
                selectinload(CrmContractModel.items),
                selectinload(CrmContractModel.attachments),
                selectinload(CrmContractModel.receipts),
            )
        )
        contract = result.scalars().first()
        if not contract:
            raise CustomException(msg="合同不存在")
        await cls._ensure_contract_access(auth, contract)
        return contract

    @classmethod
    async def _get_customer(cls, auth: AuthSchema, id: int) -> CrmCustomerProfileModel:
        result = await auth.db.execute(
            select(CrmCustomerProfileModel)
            .where(
                CrmCustomerProfileModel.id == id,
                CrmCustomerProfileModel.is_deleted == False,
            )
            .options(selectinload(CrmCustomerProfileModel.person))
        )
        customer = result.scalars().first()
        if not customer:
            raise CustomException(msg="客户不存在")
        await cls._ensure_customer_access(auth, customer)
        return customer

    @classmethod
    async def _products(cls, auth: AuthSchema, product_ids: list[int]) -> list[CrmProductPackageModel]:
        result = await auth.db.execute(
            select(CrmProductPackageModel)
            .where(
                CrmProductPackageModel.id.in_(product_ids),
                CrmProductPackageModel.is_deleted == False,
                CrmProductPackageModel.status == "0",
            )
            .order_by(CrmProductPackageModel.sort.asc(), CrmProductPackageModel.id.asc())
        )
        products = result.scalars().all()
        if len(products) != len(set(product_ids)):
            raise CustomException(msg="存在不可用或不存在的产品套餐")
        product_map = {product.id: product for product in products}
        return [product_map[product_id] for product_id in product_ids]

    @classmethod
    async def _generate_contract_no(cls, auth: AuthSchema, store_id: int) -> str:
        today = datetime.now().strftime("%y%m%d")
        prefix = f"HT{today}"
        result = await auth.db.execute(
            select(func.count(CrmContractModel.id)).where(CrmContractModel.contract_no.like(f"{prefix}%"))
        )
        seq = (result.scalar() or 0) + 1
        return f"{prefix}{seq:04d}"

    @classmethod
    def _amounts(cls, original_amount: Decimal, contract_amount: Decimal, discount_reason: str | None) -> tuple[Decimal, Decimal]:
        original_amount = cls._money(original_amount)
        contract_amount = cls._money(contract_amount)
        if contract_amount < original_amount and not discount_reason:
            raise CustomException(msg="合同总金额低于产品原价合计时必须填写折扣原因")
        discount_amount = cls._money(max(original_amount - contract_amount, Decimal("0.00")))
        discount_rate = Decimal("0.0000")
        if original_amount > 0:
            discount_rate = (discount_amount / original_amount).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        return discount_amount, discount_rate

    @classmethod
    async def _write_customer_lifecycle(
        cls,
        auth: AuthSchema,
        customer: CrmCustomerProfileModel,
        operation_type: str,
        change_detail: dict[str, Any] | None = None,
        remark: str | None = None,
    ) -> None:
        record = CrmCustomerLifecycleModel(
            brand_id=customer.brand_id,
            customer_id=customer.id,
            person_id=customer.person_id,
            operation_type=operation_type,
            operator_user_id=auth.user.id if auth.user else None,
            change_detail=change_detail,
            remark=remark,
        )
        cls._stamp_create(auth, record)
        auth.db.add(record)

    @classmethod
    async def _contract_out(cls, auth: AuthSchema, contract: CrmContractModel) -> dict:
        received_amount, pending_amount, payment_progress, payment_status = cls._payment_summary(contract)
        user_ids = {contract.owner_user_id}
        if contract.receipts:
            user_ids.update(receipt.reviewed_by for receipt in contract.receipts if receipt.reviewed_by)
        users = {}
        if user_ids:
            result = await auth.db.execute(select(UserModel.id, UserModel.name).where(UserModel.id.in_(user_ids)))
            users = {row[0]: row[1] for row in result.all()}
        store = await auth.db.get(DeptModel, contract.store_id)
        data = {
            "id": contract.id,
            "uuid": contract.uuid,
            "status": contract.status,
            "description": contract.description,
            "created_time": contract.created_time,
            "updated_time": contract.updated_time,
            "is_deleted": contract.is_deleted,
            "deleted_time": contract.deleted_time,
            "created_id": contract.created_id,
            "created_by": None,
            "updated_id": contract.updated_id,
            "updated_by": None,
            "deleted_id": contract.deleted_id,
            "deleted_by": None,
            "brand_id": contract.brand_id,
            "contract_no": contract.contract_no,
            "contract_name": contract.contract_name,
            "customer_id": contract.customer_id,
            "person_id": contract.person_id,
            "store_id": contract.store_id,
            "owner_user_id": contract.owner_user_id,
            "vip_level": contract.vip_level,
            "contract_status": contract.contract_status,
            "original_amount": contract.original_amount,
            "contract_amount": contract.contract_amount,
            "received_amount": received_amount,
            "pending_amount": pending_amount,
            "payment_progress": payment_progress,
            "payment_status": payment_status,
            "validity_period": f"{contract.start_date} 至 {contract.end_date}",
            "discount_amount": contract.discount_amount,
            "discount_rate": contract.discount_rate,
            "discount_reason": contract.discount_reason,
            "start_date": contract.start_date,
            "end_date": contract.end_date,
            "expire_remind_days": contract.expire_remind_days,
            "signer_name": contract.signer_name,
            "signed_at": contract.signed_at,
            "review_submitted_at": contract.review_submitted_at,
            "reviewed_at": contract.reviewed_at,
            "reviewed_by": contract.reviewed_by,
            "review_remark": contract.review_remark,
            "effective_at": contract.effective_at,
            "first_paid_at": contract.first_paid_at,
            "voided_at": contract.voided_at,
            "void_reason": contract.void_reason,
            "remark": contract.remark,
        }
        data["customer"] = {"id": contract.customer_id, "name": contract.person.name if contract.person else ""}
        data["person"] = {"id": contract.person_id, "name": contract.person.name if contract.person else ""}
        data["person_display_no"] = contract.person.display_no if contract.person else None
        data["person_mobile"] = contract.person.primary_mobile if contract.person else None
        data["owner_user_name"] = users.get(contract.owner_user_id)
        data["store_name"] = store.name if store else None
        data["items"] = [
            ContractItemOutSchema.model_validate(item).model_dump()
            for item in sorted(contract.items or [], key=lambda item: item.id or 0)
            if not item.is_deleted
        ]
        data["attachments"] = [
            ContractAttachmentOutSchema.model_validate(item).model_dump()
            for item in sorted(contract.attachments or [], key=lambda item: item.id or 0)
            if not item.is_deleted
        ]
        data["receipts"] = [
            ContractReceiptOutSchema.model_validate(item).model_dump()
            for item in sorted(contract.receipts or [], key=lambda item: item.id or 0, reverse=True)
            if not item.is_deleted
        ]
        return data

    @classmethod
    async def page_service(cls, auth: AuthSchema, page_no: int, page_size: int, search: ContractQueryParam | None = None) -> dict:
        await cls._expire_overdue_contracts(auth)
        conditions = cls._scope_conditions(auth)
        receipt_amount_sq = (
            select(
                CrmContractReceiptModel.contract_id.label("contract_id"),
                func.coalesce(func.sum(CrmContractReceiptModel.amount), Decimal("0.00")).label("received_amount"),
            )
            .where(
                CrmContractReceiptModel.is_deleted == False,
                CrmContractReceiptModel.receipt_status.in_({"approved", "refund_registered"}),
            )
            .group_by(CrmContractReceiptModel.contract_id)
            .subquery()
        )
        received_amount = func.coalesce(receipt_amount_sq.c.received_amount, Decimal("0.00"))
        if search:
            if search.contract_status:
                conditions.append(CrmContractModel.contract_status == search.contract_status)
            if search.payment_status == "unpaid":
                conditions.append(received_amount <= 0)
            elif search.payment_status == "settled":
                conditions.append(CrmContractModel.contract_amount > 0)
                conditions.append(received_amount >= CrmContractModel.contract_amount)
            elif search.payment_status == "partial":
                conditions.append(received_amount > 0)
                conditions.append(or_(CrmContractModel.contract_amount <= 0, received_amount < CrmContractModel.contract_amount))
            if search.vip_level:
                conditions.append(CrmContractModel.vip_level == search.vip_level)
            if search.store_id:
                conditions.append(CrmContractModel.store_id == search.store_id)
            if search.owner_user_id:
                conditions.append(CrmContractModel.owner_user_id == search.owner_user_id)
            if search.customer_id:
                conditions.append(CrmContractModel.customer_id == search.customer_id)
            if search.keyword:
                like = f"%{search.keyword}%"
                conditions.append(
                    or_(
                        CrmContractModel.contract_no.like(like),
                        CrmContractModel.contract_name.like(like),
                        CrmPersonModel.name.like(like),
                        CrmPersonModel.primary_mobile.like(like),
                    )
                )
        count_sql = select(func.count(CrmContractModel.id)).join(CrmPersonModel, CrmContractModel.person_id == CrmPersonModel.id).outerjoin(receipt_amount_sq, receipt_amount_sq.c.contract_id == CrmContractModel.id).where(*conditions)
        total = (await auth.db.execute(count_sql)).scalar() or 0
        offset = (page_no - 1) * page_size
        result = await auth.db.execute(
            select(CrmContractModel)
            .join(CrmPersonModel, CrmContractModel.person_id == CrmPersonModel.id)
            .outerjoin(receipt_amount_sq, receipt_amount_sq.c.contract_id == CrmContractModel.id)
            .where(*conditions)
            .options(selectinload(CrmContractModel.customer), selectinload(CrmContractModel.person), selectinload(CrmContractModel.items), selectinload(CrmContractModel.attachments), selectinload(CrmContractModel.receipts))
            .order_by(CrmContractModel.updated_time.desc(), CrmContractModel.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        contracts = result.scalars().unique().all()
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": offset + page_size < total,
            "items": [await cls._contract_out(auth, contract) for contract in contracts],
        }

    @classmethod
    async def detail_service(cls, auth: AuthSchema, id: int) -> dict:
        await cls._expire_overdue_contracts(auth)
        return await cls._contract_out(auth, await cls._get_contract(auth, id))

    @classmethod
    async def get_store_rule_service(cls, auth: AuthSchema, store_id: int) -> dict:
        await cls._ensure_store_rule_access(auth, store_id, "查看")
        await cls._ensure_actual_store(auth, store_id)
        rule = await cls._store_rule_by_db(auth, store_id)
        return ContractStoreRuleSchema.model_validate(rule).model_dump()

    @classmethod
    async def set_store_rule_service(cls, auth: AuthSchema, store_id: int, data: ContractStoreRuleSchema) -> None:
        await cls._ensure_store_rule_access(auth, store_id, "设置")
        await cls._ensure_actual_store(auth, store_id)
        rule = await cls._store_rule_by_db(auth, store_id)
        rule.require_contract_review = data.require_contract_review
        cls._stamp_update(auth, rule)
        await auth.db.flush()

    @classmethod
    async def create_service(cls, auth: AuthSchema, data: ContractCreateSchema) -> dict:
        customer = await cls._get_customer(auth, data.customer_id)
        products = await cls._products(auth, data.product_ids)
        original_amount = sum((cls._money(product.standard_price) for product in products), Decimal("0.00"))
        discount_amount, discount_rate = cls._amounts(original_amount, data.contract_amount, data.discount_reason)
        contract = CrmContractModel(
            brand_id=customer.brand_id,
            contract_no=await cls._generate_contract_no(auth, customer.store_id),
            contract_name=data.contract_name,
            customer_id=customer.id,
            person_id=customer.person_id,
            store_id=customer.store_id,
            owner_user_id=auth.user.id if auth.user and await cls._is_serving_customer(auth, customer.id) else customer.owner_user_id,
            vip_level=data.vip_level,
            original_amount=original_amount,
            contract_amount=cls._money(data.contract_amount),
            discount_amount=discount_amount,
            discount_rate=discount_rate,
            discount_reason=data.discount_reason,
            start_date=data.start_date,
            end_date=data.end_date,
            expire_remind_days=data.expire_remind_days,
            signer_name=data.signer_name,
            remark=data.remark,
        )
        cls._stamp_create(auth, contract)
        auth.db.add(contract)
        await auth.db.flush()
        for product in products:
            item = CrmContractItemModel(
                brand_id=customer.brand_id,
                contract_id=contract.id,
                product_id=product.id,
                product_name_snapshot=product.package_name,
                price_snapshot=cls._money(product.standard_price),
                service_days_snapshot=product.service_days,
                recommendation_quota_snapshot=product.recommendation_quota,
                meeting_quota_snapshot=product.meeting_quota,
                course_quota_snapshot=product.course_quota,
                supports_online_meeting_snapshot=product.supports_online_meeting,
            )
            cls._stamp_create(auth, item)
            auth.db.add(item)
        await cls._write_customer_lifecycle(auth, customer, "contract_create", {"contract_no": contract.contract_no}, "创建合同草稿")
        await auth.db.flush()
        return await cls.detail_service(auth, contract.id)

    @classmethod
    async def update_service(cls, auth: AuthSchema, id: int, data: ContractUpdateSchema) -> dict:
        contract = await cls._get_contract(auth, id)
        if contract.contract_status != "draft":
            raise CustomException(msg="只有草稿合同可以编辑")
        customer = await cls._get_customer(auth, data.customer_id)
        if customer.id != contract.customer_id:
            raise CustomException(msg="合同客户不可修改，请作废后重签")
        products = await cls._products(auth, data.product_ids)
        original_amount = sum((cls._money(product.standard_price) for product in products), Decimal("0.00"))
        discount_amount, discount_rate = cls._amounts(original_amount, data.contract_amount, data.discount_reason)
        for field, value in {
            "contract_name": data.contract_name,
            "vip_level": data.vip_level,
            "original_amount": original_amount,
            "contract_amount": cls._money(data.contract_amount),
            "discount_amount": discount_amount,
            "discount_rate": discount_rate,
            "discount_reason": data.discount_reason,
            "start_date": data.start_date,
            "end_date": data.end_date,
            "expire_remind_days": data.expire_remind_days,
            "signer_name": data.signer_name,
            "remark": data.remark,
        }.items():
            setattr(contract, field, value)
        cls._stamp_update(auth, contract)
        for item in contract.items or []:
            item.is_deleted = True
            item.deleted_time = datetime.now()
            item.deleted_id = auth.user.id if auth.user else None
        await auth.db.flush()
        for product in products:
            item = CrmContractItemModel(
                brand_id=contract.brand_id,
                contract_id=contract.id,
                product_id=product.id,
                product_name_snapshot=product.package_name,
                price_snapshot=cls._money(product.standard_price),
                service_days_snapshot=product.service_days,
                recommendation_quota_snapshot=product.recommendation_quota,
                meeting_quota_snapshot=product.meeting_quota,
                course_quota_snapshot=product.course_quota,
                supports_online_meeting_snapshot=product.supports_online_meeting,
            )
            cls._stamp_create(auth, item)
            auth.db.add(item)
        await cls._write_customer_lifecycle(auth, customer, "contract_update", {"contract_no": contract.contract_no}, "编辑合同草稿")
        await auth.db.flush()
        return await cls.detail_service(auth, contract.id)

    @classmethod
    async def save_attachment_service(cls, auth: AuthSchema, id: int, data: ContractAttachmentSaveSchema) -> dict:
        contract = await cls._get_contract(auth, id)
        if contract.contract_status in {"effective", "voided"}:
            raise CustomException(msg="已生效或已作废合同不能上传影像")
        attachment = CrmContractAttachmentModel(
            brand_id=contract.brand_id,
            contract_id=contract.id,
            file_name=data.file_name,
            file_path=data.file_path,
            file_url=data.file_url,
            file_type=data.file_type,
            page_count=data.page_count,
            payload=data.payload,
        )
        cls._stamp_create(auth, attachment)
        auth.db.add(attachment)
        await cls._write_customer_lifecycle(auth, contract.customer, "contract_attachment", {"contract_no": contract.contract_no, "file_name": data.file_name}, "上传合同影像")
        await auth.db.flush()
        return ContractAttachmentOutSchema.model_validate(attachment).model_dump()

    @classmethod
    async def delete_attachment_service(cls, auth: AuthSchema, attachment_id: int) -> None:
        result = await auth.db.execute(
            select(CrmContractAttachmentModel, CrmContractModel)
            .join(CrmContractModel, CrmContractAttachmentModel.contract_id == CrmContractModel.id)
            .where(
                CrmContractAttachmentModel.id == attachment_id,
                CrmContractAttachmentModel.is_deleted == False,
                CrmContractModel.is_deleted == False,
            )
            .options(selectinload(CrmContractModel.customer))
        )
        row = result.first()
        if not row:
            raise CustomException(msg="合同影像不存在")
        attachment, contract = row
        await cls._ensure_contract_access(auth, contract)
        can_delete_submitted = cls._is_brand_admin(auth) or (cls._is_store_mgr(auth) and auth.user and auth.user.dept_id == contract.store_id)
        if contract.contract_status in {"effective", "voided"}:
            raise CustomException(msg="已生效或已作废合同不能删除影像")
        if contract.contract_status != "draft" and not can_delete_submitted:
            raise CustomException(msg="合同提交后只有店长可以删除影像")
        attachment.is_deleted = True
        attachment.deleted_time = datetime.now()
        attachment.attachment_status = "deleted"
        if auth.user:
            attachment.deleted_id = auth.user.id
            attachment.updated_id = auth.user.id
        await cls._write_customer_lifecycle(
            auth,
            contract.customer,
            "contract_attachment_delete",
            {"contract_no": contract.contract_no, "file_name": attachment.file_name},
            "删除合同影像",
        )
        await auth.db.flush()

    @classmethod
    async def sign_service(cls, auth: AuthSchema, id: int, data: ContractSignSchema) -> dict:
        contract = await cls._get_contract(auth, id)
        if contract.contract_status != "draft":
            raise CustomException(msg="只有草稿合同可以标记已签")
        active_attachments = [item for item in contract.attachments or [] if not item.is_deleted and item.attachment_status == "active"]
        if not active_attachments:
            raise CustomException(msg="请先上传至少一份合同影像")
        require_review = await cls._requires_contract_review(auth, contract.store_id)
        contract.contract_status = "signed" if require_review else "pending_payment"
        contract.signed_at = datetime.now()
        contract.review_submitted_at = None
        contract.reviewed_at = None
        contract.reviewed_by = None
        contract.review_remark = None
        cls._stamp_update(auth, contract)
        contract.customer.current_stage = "contracted"
        contract.customer.max_stage = "contracted"
        await cls._write_customer_lifecycle(auth, contract.customer, "contract_sign", {"contract_no": contract.contract_no}, data.remark or "合同已签")
        if not require_review:
            await cls._write_customer_lifecycle(
                auth,
                contract.customer,
                "contract_review_skipped",
                {"contract_no": contract.contract_no, "store_id": contract.store_id, "require_contract_review": False},
                "门店规则免审核，合同进入待收款",
            )
        await auth.db.flush()
        return await cls.detail_service(auth, id)

    @classmethod
    async def submit_review_service(cls, auth: AuthSchema, id: int) -> dict:
        contract = await cls._get_contract(auth, id)
        if contract.contract_status != "signed":
            raise CustomException(msg="只有已签合同可以提交审核")
        if not await cls._requires_contract_review(auth, contract.store_id):
            contract.contract_status = "pending_payment"
            contract.review_submitted_at = None
            contract.reviewed_at = None
            contract.reviewed_by = None
            contract.review_remark = None
            cls._stamp_update(auth, contract)
            await cls._write_customer_lifecycle(
                auth,
                contract.customer,
                "contract_review_skipped",
                {"contract_no": contract.contract_no, "store_id": contract.store_id, "require_contract_review": False},
                "门店规则免审核，合同进入待收款",
            )
            await auth.db.flush()
            return await cls.detail_service(auth, id)
        contract.contract_status = "pending_review"
        contract.review_submitted_at = datetime.now()
        contract.reviewed_at = None
        contract.reviewed_by = None
        contract.review_remark = None
        cls._stamp_update(auth, contract)
        await cls._write_customer_lifecycle(
            auth,
            contract.customer,
            "contract_submit_review",
            {"contract_no": contract.contract_no},
            "合同提交审核",
        )
        await auth.db.flush()
        return await cls.detail_service(auth, id)

    @classmethod
    async def review_service(cls, auth: AuthSchema, id: int, data: ContractReviewSchema) -> dict:
        if not cls._can_review_contract(auth):
            raise CustomException(msg="无权审核合同")
        contract = await cls._get_contract(auth, id)
        if contract.contract_status != "pending_review":
            raise CustomException(msg="只有待审核合同可以审核")
        now = datetime.now()
        contract.reviewed_at = now
        contract.reviewed_by = auth.user.id if auth.user else None
        contract.review_remark = data.review_remark
        contract.contract_status = "pending_payment" if data.approved else "signed"
        cls._stamp_update(auth, contract)
        await cls._write_customer_lifecycle(
            auth,
            contract.customer,
            "contract_review",
            {"contract_no": contract.contract_no, "approved": data.approved},
            data.review_remark or ("合同审核通过" if data.approved else "合同审核驳回"),
        )
        await auth.db.flush()
        return await cls.detail_service(auth, id)

    @classmethod
    async def void_service(cls, auth: AuthSchema, id: int, data: ContractVoidSchema) -> dict:
        contract = await cls._get_contract(auth, id)
        if contract.contract_status not in {"draft", "signed"}:
            raise CustomException(msg="只有草稿或已签合同可以作废")
        if contract.contract_status == "draft":
            if not auth.user or (contract.created_id != auth.user.id and contract.owner_user_id != auth.user.id and not cls._is_brand_admin(auth) and not (cls._is_store_mgr(auth) and auth.user.dept_id == contract.store_id)):
                raise CustomException(msg="只有合同创建人可以作废草稿合同")
        elif not (cls._is_brand_admin(auth) or cls._can_review_contract(auth)):
            raise CustomException(msg="只有店长或审核人员可以作废已签合同")
        contract.contract_status = "voided"
        contract.voided_at = datetime.now()
        contract.void_reason = data.reason
        cls._stamp_update(auth, contract)
        await cls._write_customer_lifecycle(auth, contract.customer, "contract_void", {"contract_no": contract.contract_no}, data.reason)
        await auth.db.flush()
        return await cls.detail_service(auth, id)

    @classmethod
    async def customer_search_service(cls, auth: AuthSchema, keyword: str | None = None, limit: int = 20) -> list[dict]:
        conditions = [
            CrmCustomerProfileModel.is_deleted == False,
            or_(
                CrmCustomerProfileModel.ended_at.is_(None),
                CrmCustomerProfileModel.converted_vip_at.is_not(None),
            ),
        ]
        if cls._is_brand_admin(auth):
            pass
        elif auth.user and cls._is_store_mgr(auth):
            conditions.append(CrmCustomerProfileModel.store_id == (auth.user.dept_id or -1))
        elif auth.user:
            if cls._is_matchmaker(auth):
                conditions.append(or_(CrmCustomerProfileModel.owner_user_id == auth.user.id, CrmCustomerProfileModel.id.in_(cls._served_customer_ids(auth))))
            else:
                conditions.append(CrmCustomerProfileModel.owner_user_id == auth.user.id)
        else:
            conditions.append(CrmCustomerProfileModel.id == -1)
        if keyword:
            like = f"%{keyword.strip()}%"
            conditions.append(or_(CrmPersonModel.name.like(like), CrmPersonModel.primary_mobile.like(like), CrmPersonModel.display_no.like(like)))
        result = await auth.db.execute(
            select(CrmCustomerProfileModel, CrmPersonModel)
            .join(CrmPersonModel, CrmCustomerProfileModel.person_id == CrmPersonModel.id)
            .where(*conditions)
            .order_by(CrmCustomerProfileModel.updated_time.desc(), CrmCustomerProfileModel.id.desc())
            .limit(min(limit, 50))
        )
        return [
            CustomerSearchOutSchema(
                id=customer.id,
                person_id=customer.person_id,
                display_no=person.display_no,
                name=person.name,
                mobile=person.primary_mobile,
                gender=person.gender,
                store_id=customer.store_id,
                owner_user_id=customer.owner_user_id,
            ).model_dump()
            for customer, person in result.all()
        ]
