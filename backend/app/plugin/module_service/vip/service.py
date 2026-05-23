from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.module_system.auth.schema import AuthSchema
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.params.model import ParamsModel
from app.api.v1.module_system.position.model import PositionModel
from app.api.v1.module_system.role.model import RoleModel
from app.api.v1.module_system.user.model import UserModel
from app.core.exceptions import CustomException
from app.plugin.module_certification.model import CertificationItemModel
from app.plugin.module_crm.contract.model import (
    CrmContractItemModel,
    CrmContractModel,
    CrmContractReceiptModel,
    CrmVipProfileModel,
)
from app.plugin.module_crm.customer.model import (
    CrmCustomerCertificationMaterialModel,
    CrmCustomerLifecycleModel,
    CrmCustomerProcessRecordModel,
    CrmCustomerProfileModel,
)
from app.plugin.module_crm.customer.schema import (
    CustomerCertificationMaterialSaveSchema,
    CustomerUpdateSchema,
)
from app.plugin.module_crm.customer.service import CustomerService
from app.plugin.module_crm.lead.model import (
    CrmLeadLifecycleModel,
    CrmLeadProcessRecordModel,
    CrmLeadProfileModel,
    CrmPersonModel,
)
from app.plugin.module_crm.preference.model import PersonPartnerPreferenceModel
from app.plugin.module_crm.preference.schema import PartnerPreferenceSaveSchema
from app.plugin.module_crm.preference.service import PartnerPreferenceService

from .model import (
    BackupPoolItemModel,
    CandidateJoinRequestModel,
    CandidateProfileModel,
    DeepInterviewModel,
    EntitlementUsageLogModel,
    ServiceCaseModel,
    ServiceEntitlementModel,
    VipServiceLogModel,
)
from .schema import (
    CandidateAddExistingSchema,
    CandidateCreateSchema,
    CandidateDiscoverSchema,
    CandidateJoinRequestCreateSchema,
    CandidateJoinRequestQueryParam,
    CandidateJoinRequestReviewSchema,
    CandidateQueryParam,
    CandidateRuleUpdateSchema,
    CloseApplySchema,
    CloseReviewSchema,
    DeepInterviewCreateSchema,
    MatchmakerOptionSchema,
    ReopenSchema,
    ServiceCustomerProcessCreateSchema,
    UsageCreateSchema,
    UsageVoidSchema,
    VipAssignSchema,
    VipQueryParam,
)


class VipService:
    """服务工作台服务层"""

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
    def _is_matchmaker(cls, auth: AuthSchema) -> bool:
        return "MATCHMAKER" in cls._role_codes(auth)

    @classmethod
    def _can_assign(cls, auth: AuthSchema) -> bool:
        return cls._is_brand_admin(auth) or cls._is_store_mgr(auth)

    @classmethod
    def _can_review_close(cls, auth: AuthSchema) -> bool:
        return cls._is_brand_admin(auth) or cls._is_store_mgr(auth)

    @classmethod
    def _has_permission(cls, auth: AuthSchema, permission: str) -> bool:
        if auth.user and auth.user.is_superuser:
            return True
        return any(
            menu.permission == permission
            for role in auth.user.roles or []
            if role.status == "0"
            for menu in role.menus or []
            if menu.status == "0"
        ) if auth.user else False

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
    def _mask_mobile(cls, mobile: str | None) -> str | None:
        if not mobile or len(mobile) < 7:
            return mobile
        return f"{mobile[:3]}****{mobile[-4:]}"

    @classmethod
    def _mask_id_card(cls, id_card_no: str | None) -> str | None:
        if not id_card_no or len(id_card_no) < 8:
            return id_card_no
        return f"{id_card_no[:4]}**********{id_card_no[-4:]}"

    @classmethod
    def _money(cls, value: Decimal | int | str) -> Decimal:
        return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def _age(cls, birth_date: date | None) -> int | None:
        if not birth_date:
            return None
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    @classmethod
    def _active_receipt_amount(cls, receipt: CrmContractReceiptModel) -> Decimal:
        if receipt.is_deleted:
            return Decimal("0.00")
        if receipt.receipt_status in {"approved", "refund_registered"}:
            return cls._money(receipt.amount)
        return Decimal("0.00")

    @classmethod
    def _payment_summary(cls, contract: CrmContractModel) -> tuple[Decimal, Decimal, str]:
        received_amount = sum((cls._active_receipt_amount(receipt) for receipt in contract.receipts or []), Decimal("0.00"))
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
    def _case_scope_conditions(cls, auth: AuthSchema) -> list[Any]:
        conditions: list[Any] = [ServiceCaseModel.is_deleted == False]
        if cls._is_brand_admin(auth):
            return conditions
        if not auth.user:
            conditions.append(ServiceCaseModel.id == -1)
            return conditions
        if cls._is_store_mgr(auth):
            conditions.append(ServiceCaseModel.store_id == (auth.user.dept_id or -1))
            return conditions
        if cls._is_matchmaker(auth):
            conditions.append(ServiceCaseModel.owner_matchmaker_id == auth.user.id)
            return conditions
        conditions.append(ServiceCaseModel.id == -1)
        return conditions

    @classmethod
    async def _ensure_case_access(cls, auth: AuthSchema, case: ServiceCaseModel) -> None:
        if cls._is_brand_admin(auth):
            return
        if not auth.user:
            raise CustomException(msg="无权访问服务工单")
        if cls._is_store_mgr(auth) and case.store_id == auth.user.dept_id:
            return
        if cls._is_matchmaker(auth) and case.owner_matchmaker_id == auth.user.id:
            return
        raise CustomException(msg="无权访问服务工单")

    @classmethod
    async def _ensure_assign_access(cls, auth: AuthSchema, case: ServiceCaseModel) -> None:
        if not cls._can_assign(auth):
            raise CustomException(msg="无权分配VIP服务")
        if cls._is_brand_admin(auth):
            return
        if cls._is_store_mgr(auth) and auth.user and case.store_id == auth.user.dept_id:
            return
        raise CustomException(msg="无权分配该门店VIP服务")

    @classmethod
    async def _ensure_close_review_access(cls, auth: AuthSchema, case: ServiceCaseModel) -> None:
        if not cls._can_review_close(auth):
            raise CustomException(msg="无权审核关单")
        if cls._is_brand_admin(auth):
            return
        if cls._is_store_mgr(auth) and auth.user and case.store_id == auth.user.dept_id:
            return
        raise CustomException(msg="无权审核该门店关单")

    @classmethod
    async def _get_case(cls, auth: AuthSchema, case_id: int) -> ServiceCaseModel:
        result = await auth.db.execute(
            select(ServiceCaseModel).where(ServiceCaseModel.id == case_id, ServiceCaseModel.is_deleted == False)
        )
        case = result.scalars().first()
        if not case:
            raise CustomException(msg="服务工单不存在")
        await cls._ensure_case_access(auth, case)
        return case

    @classmethod
    async def _validate_matchmaker(cls, db: AsyncSession, store_id: int, user_id: int) -> UserModel:
        result = await db.execute(
            select(UserModel)
            .where(
                UserModel.id == user_id,
                UserModel.is_deleted == False,
                UserModel.status == "0",
                UserModel.dept_id == store_id,
                or_(UserModel.roles.any(RoleModel.code == "MATCHMAKER"), UserModel.positions.any(PositionModel.name == "服务红娘")),
            )
            .options(selectinload(UserModel.roles), selectinload(UserModel.positions))
        )
        user = result.scalars().first()
        if not user:
            raise CustomException(msg="请选择同门店启用的服务红娘")
        return user

    @classmethod
    async def _user_names(cls, db: AsyncSession, ids: set[int | None]) -> dict[int, str]:
        user_ids = {user_id for user_id in ids if user_id}
        if not user_ids:
            return {}
        result = await db.execute(select(UserModel.id, UserModel.name).where(UserModel.id.in_(user_ids)))
        return {row[0]: row[1] for row in result.all()}

    @classmethod
    async def _entitlement_summary(cls, db: AsyncSession, case_id: int) -> dict[str, dict[str, int]]:
        result = await db.execute(
            select(ServiceEntitlementModel).where(ServiceEntitlementModel.service_case_id == case_id, ServiceEntitlementModel.is_deleted == False)
        )
        summary: dict[str, dict[str, int]] = {}
        for item in result.scalars().all():
            bucket = summary.setdefault(item.entitlement_type, {"total": 0, "used": 0, "remaining": 0})
            bucket["total"] += item.total_quota
            bucket["used"] += item.used_quota
            bucket["remaining"] += item.remaining_quota
        return summary

    @classmethod
    async def _case_out(cls, auth: AuthSchema, case: ServiceCaseModel) -> dict:
        vip = await auth.db.get(CrmVipProfileModel, case.vip_id)
        person = await auth.db.get(CrmPersonModel, case.person_id)
        contract = await auth.db.get(
            CrmContractModel,
            case.contract_id,
            options=[selectinload(CrmContractModel.receipts), selectinload(CrmContractModel.items)],
        )
        store = await auth.db.get(DeptModel, case.store_id)
        received_amount, pending_amount, payment_status = cls._payment_summary(contract) if contract else (Decimal("0.00"), Decimal("0.00"), "unpaid")
        users = await cls._user_names(
            auth.db,
            {
                contract.owner_user_id if contract else None,
                case.owner_matchmaker_id,
                case.assigned_by,
                case.close_requested_by,
                case.close_reviewed_by,
            },
        )
        mobile = person.primary_mobile if person else None
        if not cls._has_permission(auth, "service:vip:view_phone"):
            mobile = cls._mask_mobile(mobile)
        now = datetime.now()
        waiting_base = contract.effective_at if contract and contract.effective_at else case.created_time
        waiting_hours = max(int((now - waiting_base).total_seconds() // 3600), 0) if case.case_status == "pending_assign" and waiting_base else None
        remaining_days = None
        if vip and vip.ended_at:
            remaining_days = (vip.ended_at.date() - date.today()).days
        elif contract and contract.end_date:
            remaining_days = (contract.end_date - date.today()).days
        deep_count = (await auth.db.execute(select(func.count(DeepInterviewModel.id)).where(DeepInterviewModel.service_case_id == case.id, DeepInterviewModel.is_deleted == False))).scalar() or 0
        usage_count = (await auth.db.execute(select(func.count(EntitlementUsageLogModel.id)).where(EntitlementUsageLogModel.service_case_id == case.id, EntitlementUsageLogModel.is_deleted == False))).scalar() or 0
        vip_status = vip.vip_status if vip else case.case_status
        return {
            "id": case.id,
            "case_id": case.id,
            "brand_id": case.brand_id,
            "vip_id": case.vip_id,
            "person_id": case.person_id,
            "customer_id": case.customer_id,
            "contract_id": case.contract_id,
            "store_id": case.store_id,
            "service_owner_user_id": case.owner_matchmaker_id,
            "owner_matchmaker_id": case.owner_matchmaker_id,
            "case_status": case.case_status,
            "pool_type": case.pool_type,
            "close_review_status": case.close_review_status,
            "close_requested_at": case.close_requested_at,
            "close_requested_by": case.close_requested_by,
            "close_requested_by_name": users.get(case.close_requested_by),
            "close_reason": case.close_reason,
            "close_reviewed_at": case.close_reviewed_at,
            "close_reviewed_by": case.close_reviewed_by,
            "close_reviewed_by_name": users.get(case.close_reviewed_by),
            "close_review_remark": case.close_review_remark,
            "vip_level": vip.vip_level if vip else contract.vip_level if contract else "",
            "vip_status": vip_status,
            "started_at": vip.started_at if vip else case.created_time,
            "ended_at": vip.ended_at if vip else None,
            "assigned_at": case.assigned_at,
            "assigned_by": case.assigned_by,
            "source_receipt_id": vip.source_receipt_id if vip else None,
            "person_display_no": person.display_no if person else None,
            "person_name": person.name if person else None,
            "person_gender": person.gender if person else None,
            "person_age": cls._age(person.birth_date if person else None),
            "person_mobile": mobile,
            "contract_no": contract.contract_no if contract else None,
            "contract_name": contract.contract_name if contract else None,
            "contract_status": contract.contract_status if contract else None,
            "original_amount": contract.original_amount if contract else Decimal("0.00"),
            "contract_amount": contract.contract_amount if contract else Decimal("0.00"),
            "discount_amount": contract.discount_amount if contract else Decimal("0.00"),
            "discount_rate": contract.discount_rate if contract else Decimal("0.0000"),
            "discount_reason": contract.discount_reason if contract else None,
            "signer_name": contract.signer_name if contract else None,
            "signed_at": contract.signed_at if contract else None,
            "effective_at": contract.effective_at if contract else None,
            "start_date": contract.start_date if contract else None,
            "end_date": contract.end_date if contract else None,
            "received_amount": received_amount,
            "pending_amount": pending_amount,
            "payment_status": payment_status,
            "contract_effective_at": contract.effective_at if contract else None,
            "contract_items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "product_name_snapshot": item.product_name_snapshot,
                    "price_snapshot": item.price_snapshot,
                    "service_days_snapshot": item.service_days_snapshot,
                    "recommendation_quota_snapshot": item.recommendation_quota_snapshot,
                    "meeting_quota_snapshot": item.meeting_quota_snapshot,
                    "course_quota_snapshot": item.course_quota_snapshot,
                    "supports_online_meeting_snapshot": item.supports_online_meeting_snapshot,
                }
                for item in (contract.items or [])
                if not item.is_deleted
            ]
            if contract
            else [],
            "owner_user_id": contract.owner_user_id if contract else None,
            "owner_user_name": users.get(contract.owner_user_id) if contract else None,
            "service_owner_user_name": users.get(case.owner_matchmaker_id),
            "assigned_by_name": users.get(case.assigned_by),
            "store_name": store.name if store else None,
            "waiting_hours": waiting_hours,
            "remaining_days": remaining_days,
            "entitlement_summary": await cls._entitlement_summary(auth.db, case.id),
            "deep_interview_count": deep_count,
            "usage_count": usage_count,
        }

    @classmethod
    async def page_service(cls, auth: AuthSchema, page_no: int, page_size: int, search: VipQueryParam | None = None, pending_only: bool = False) -> dict:
        conditions = cls._case_scope_conditions(auth)
        if pending_only:
            conditions.append(ServiceCaseModel.case_status == "pending_assign")
        if search:
            if search.mine and auth.user:
                conditions.append(ServiceCaseModel.owner_matchmaker_id == auth.user.id)
            if search.vip_status:
                conditions.append(ServiceCaseModel.case_status == search.vip_status)
            if search.close_review_status:
                conditions.append(ServiceCaseModel.close_review_status == search.close_review_status)
            if search.vip_level:
                conditions.append(CrmVipProfileModel.vip_level == search.vip_level)
            if search.store_id:
                conditions.append(ServiceCaseModel.store_id == search.store_id)
            if search.service_owner_user_id:
                conditions.append(ServiceCaseModel.owner_matchmaker_id == search.service_owner_user_id)
            if search.owner_user_id:
                conditions.append(CrmContractModel.owner_user_id == search.owner_user_id)
            if search.effective_start:
                conditions.append(CrmContractModel.effective_at >= datetime.combine(search.effective_start, time.min))
            if search.effective_end:
                conditions.append(CrmContractModel.effective_at <= datetime.combine(search.effective_end, time.max))
            if search.ended_start:
                conditions.append(CrmVipProfileModel.ended_at >= datetime.combine(search.ended_start, time.min))
            if search.ended_end:
                conditions.append(CrmVipProfileModel.ended_at <= datetime.combine(search.ended_end, time.max))
            if search.keyword:
                like = f"%{search.keyword}%"
                conditions.append(or_(CrmPersonModel.name.like(like), CrmPersonModel.primary_mobile.like(like), CrmPersonModel.display_no.like(like), CrmContractModel.contract_no.like(like), CrmContractModel.contract_name.like(like)))
        base = (
            select(ServiceCaseModel)
            .join(CrmPersonModel, ServiceCaseModel.person_id == CrmPersonModel.id)
            .join(CrmContractModel, ServiceCaseModel.contract_id == CrmContractModel.id)
            .join(CrmVipProfileModel, ServiceCaseModel.vip_id == CrmVipProfileModel.id)
            .where(*conditions)
        )
        total = (
            await auth.db.execute(
                select(func.count(ServiceCaseModel.id))
                .join(CrmPersonModel, ServiceCaseModel.person_id == CrmPersonModel.id)
                .join(CrmContractModel, ServiceCaseModel.contract_id == CrmContractModel.id)
                .join(CrmVipProfileModel, ServiceCaseModel.vip_id == CrmVipProfileModel.id)
                .where(*conditions)
            )
        ).scalar() or 0
        offset = (page_no - 1) * page_size
        result = await auth.db.execute(base.order_by(ServiceCaseModel.created_time.desc(), ServiceCaseModel.id.desc()).offset(offset).limit(page_size))
        cases = result.scalars().all()
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": offset + page_size < total,
            "items": [await cls._case_out(auth, case) for case in cases],
        }

    @classmethod
    async def detail_service(cls, auth: AuthSchema, vip_id: int) -> dict:
        case = await cls._get_case(auth, vip_id)
        data = await cls._case_out(auth, case)
        result = await auth.db.execute(
            select(VipServiceLogModel)
            .where(VipServiceLogModel.vip_id == case.vip_id, VipServiceLogModel.is_deleted == False)
            .order_by(VipServiceLogModel.created_time.desc(), VipServiceLogModel.id.desc())
        )
        logs = result.scalars().all()
        user_ids = {log.operator_user_id for log in logs} | {log.before_owner_user_id for log in logs} | {log.after_owner_user_id for log in logs}
        users = await cls._user_names(auth.db, user_ids)
        data["logs"] = [
            {
                "id": log.id,
                "operation_type": log.operation_type,
                "operator_user_id": log.operator_user_id,
                "operator_user_name": users.get(log.operator_user_id),
                "before_owner_user_id": log.before_owner_user_id,
                "before_owner_user_name": users.get(log.before_owner_user_id),
                "after_owner_user_id": log.after_owner_user_id,
                "after_owner_user_name": users.get(log.after_owner_user_id),
                "before_status": log.before_status,
                "after_status": log.after_status,
                "remark": log.remark,
                "created_time": log.created_time,
            }
            for log in logs
        ]
        data["entitlements"] = await cls.entitlements_service(auth, case.id)
        data["usages"] = await cls.usage_list_service(auth, case.id)
        data["deep_interviews"] = await cls.interview_list_service(auth, case.id)
        return data

    @classmethod
    async def customer_profile_service(cls, auth: AuthSchema, case_id: int) -> dict:
        case = await cls._get_case(auth, case_id)
        person = await auth.db.get(CrmPersonModel, case.person_id)
        customer = await auth.db.get(CrmCustomerProfileModel, case.customer_id)
        store = await auth.db.get(DeptModel, case.store_id)
        users = await cls._user_names(auth.db, {customer.owner_user_id if customer else None, case.owner_matchmaker_id})
        mobile = person.primary_mobile if person else None
        wechat = person.wechat if person else None
        if not cls._has_permission(auth, "service:vip:view_phone"):
            mobile = cls._mask_mobile(mobile)
            wechat = cls._mask_mobile(wechat)
        id_card_no = person.id_card_no if person else None
        if not (cls._has_permission(auth, "crm:person:view_id_card") or cls._has_permission(auth, "crm:customer:view_id_card")):
            id_card_no = cls._mask_id_card(id_card_no)
        return {
            "person_id": case.person_id,
            "person_brand_id": person.brand_id if person else None,
            "customer_id": case.customer_id,
            "customer_brand_id": customer.brand_id if customer else None,
            "lead_id": customer.lead_id if customer else None,
            "store_id": case.store_id,
            "store_name": store.name if store else None,
            "owner_user_id": customer.owner_user_id if customer else None,
            "owner_user_name": users.get(customer.owner_user_id) if customer else None,
            "service_owner_user_id": case.owner_matchmaker_id,
            "service_owner_user_name": users.get(case.owner_matchmaker_id),
            "display_no": person.display_no if person else None,
            "name": person.name if person else None,
            "gender": person.gender if person else None,
            "mobile": mobile,
            "wechat": wechat,
            "id_card_no": id_card_no,
            "birth_date": person.birth_date if person else None,
            "age": cls._age(person.birth_date if person else None),
            "constellation": CustomerService._constellation(person.birth_date if person else None),
            "zodiac": CustomerService._zodiac(person.birth_date if person else None),
            "height_cm": person.height_cm if person else None,
            "weight_kg": person.weight_kg if person else None,
            "education": person.education if person else None,
            "annual_income": person.annual_income if person else None,
            "marital_status": person.marital_status if person else None,
            "ethnicity": person.ethnicity if person else None,
            "occupation": person.occupation if person else None,
            "occupation_code": person.occupation_code if person else None,
            "unit_type": person.unit_type if person else None,
            "graduated_school": person.graduated_school if person else None,
            "major": person.major if person else None,
            "job_title": person.job_title if person else None,
            "work_company": person.work_company if person else None,
            "hometown": person.hometown if person else None,
            "residence": person.residence if person else None,
            "house_status": person.house_status if person else None,
            "car_status": person.car_status if person else None,
            "accept_long_distance_self": person.accept_long_distance_self if person else None,
            "accept_flash_marriage": person.accept_flash_marriage if person else None,
            "willing_relocate": person.willing_relocate if person else None,
            "marriage_plan": person.marriage_plan if person else None,
            "family_background": person.family_background if person else None,
            "profile_remark": person.profile_remark if person else None,
            "photo_urls": person.photo_urls if person and person.photo_urls else [],
            "profile_intro": person.profile_intro if person else None,
            "certification_level": person.certification_level if person else None,
            "certification_summary": person.certification_summary if person else None,
            "partner_preference": await PartnerPreferenceService.current_out(auth.db, case.person_id),
            "current_stage": customer.current_stage if customer else None,
            "max_stage": customer.max_stage if customer else None,
            "latest_follow_at": customer.latest_follow_at if customer else None,
            "next_follow_at": customer.next_follow_at if customer else None,
            "ended_at": customer.ended_at if customer else None,
            "end_reason": customer.end_reason if customer else None,
            "returned_lead_id": customer.returned_lead_id if customer else None,
            "converted_vip_at": customer.converted_vip_at if customer else None,
            "created_time": customer.created_time if customer else None,
            "updated_time": customer.updated_time if customer else None,
        }

    @classmethod
    async def update_customer_profile_service(cls, auth: AuthSchema, case_id: int, data: CustomerUpdateSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        if case.case_status not in {"serving", "reopened", "pending_close_review"}:
            raise CustomException(msg="当前服务状态不能编辑客户资料")
        person = await auth.db.get(CrmPersonModel, case.person_id)
        if not person:
            raise CustomException(msg="客户Person不存在")
        customer = await auth.db.get(CrmCustomerProfileModel, case.customer_id)
        old = {
            "mobile": person.primary_mobile,
            "name": person.name,
            "gender": person.gender,
            "wechat": person.wechat,
            "birth_date": person.birth_date,
            "height_cm": person.height_cm,
            "weight_kg": person.weight_kg,
            "ethnicity": person.ethnicity,
            "occupation": person.occupation,
            "occupation_code": person.occupation_code,
            "annual_income": person.annual_income,
            "marital_status": person.marital_status,
            "education": person.education,
            "graduated_school": person.graduated_school,
            "major": person.major,
            "unit_type": person.unit_type,
            "job_title": person.job_title,
            "work_company": person.work_company,
            "hometown": person.hometown,
            "residence": person.residence,
            "house_status": person.house_status,
            "car_status": person.car_status,
            "accept_long_distance_self": person.accept_long_distance_self,
            "accept_flash_marriage": person.accept_flash_marriage,
            "willing_relocate": person.willing_relocate,
            "marriage_plan": person.marriage_plan,
            "family_background": person.family_background,
            "profile_remark": person.profile_remark,
            "photo_urls": person.photo_urls or [],
            "profile_intro": person.profile_intro,
            "id_card_no": person.id_card_no,
        }
        payload = data.model_dump(exclude={"partner_preference", "current_stage", "next_follow_at", "description"})
        payload["mobile"] = person.primary_mobile
        if not payload.get("id_card_no") or "*" in str(payload.get("id_card_no")):
            payload["id_card_no"] = person.id_card_no
        if payload.get("photo_urls") is None:
            payload["photo_urls"] = person.photo_urls or []
        changes: dict[str, Any] = {}
        for field, value in payload.items():
            target = "primary_mobile" if field == "mobile" else field
            if old.get(field) != value:
                changes[field] = {"from": old.get(field), "to": value}
            setattr(person, target, value)
        if data.partner_preference is not None:
            await PartnerPreferenceService.save(
                auth.db,
                case.person_id,
                PartnerPreferenceSaveSchema(
                    **data.partner_preference.model_dump(),
                    source_type="matchmaker",
                    source_id=str(case.id),
                    force_final=True,
                ),
                auth=auth,
            )
            changes["partner_preference"] = "已更新"
        cls._stamp_update(auth, person)
        if customer and changes:
            await CustomerService._write_lifecycle(auth, customer, "service_profile_update", changes, data.description or "服务阶段编辑VIP资料")
        await auth.db.flush()
        return await cls.customer_profile_service(auth, case.id)

    @classmethod
    async def certification_service(cls, auth: AuthSchema, case_id: int) -> list[dict]:
        case = await cls._get_case(auth, case_id)
        result = await auth.db.execute(
            select(CrmCustomerCertificationMaterialModel)
            .where(
                CrmCustomerCertificationMaterialModel.customer_id == case.customer_id,
                CrmCustomerCertificationMaterialModel.person_id == case.person_id,
                CrmCustomerCertificationMaterialModel.is_deleted == False,
            )
            .order_by(CrmCustomerCertificationMaterialModel.created_time.desc(), CrmCustomerCertificationMaterialModel.id.desc())
        )
        rows = result.scalars().all()
        users = await cls._user_names(auth.db, {row.collected_by for row in rows} | {row.created_id for row in rows})
        return [
            {
                "id": row.id,
                "item_code": row.item_code,
                "item_name": row.item_name,
                "material_type": row.material_type,
                "file_name": row.file_name,
                "file_path": row.file_path,
                "file_url": row.file_url,
                "payload": row.payload,
                "collected_by": row.collected_by,
                "collected_by_name": users.get(row.collected_by) or users.get(row.created_id),
                "created_time": row.created_time,
            }
            for row in rows
        ]

    @classmethod
    async def certification_archive_items_service(cls, auth: AuthSchema, case_id: int) -> list[dict[str, Any]]:
        await cls._get_case(auth, case_id)
        rows = (
            await auth.db.execute(
                select(CertificationItemModel)
                .where(
                    CertificationItemModel.is_deleted == False,
                    CertificationItemModel.status == "0",
                    CertificationItemModel.material_required == True,
                    CertificationItemModel.item_code != "real_photo",
                )
                .order_by(CertificationItemModel.sort.asc(), CertificationItemModel.id.asc())
            )
        ).scalars().all()
        result = [{"item_code": "id_card_photo", "item_name": "身份证照片", "sort": 0, "material_required": True, "material_desc": None}]
        result.extend(
            [
                {
                    "item_code": row.item_code,
                    "item_name": row.item_name,
                    "sort": row.sort,
                    "material_required": row.material_required,
                    "material_desc": row.material_desc,
                }
                for row in rows
            ]
        )
        return result

    @classmethod
    async def save_certification_material_service(cls, auth: AuthSchema, case_id: int, data: CustomerCertificationMaterialSaveSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        if case.case_status not in {"serving", "reopened", "pending_close_review"}:
            raise CustomException(msg="当前服务状态不能维护认证资料")
        archive_items = await cls.certification_archive_items_service(auth, case.id)
        item_name_map = {row["item_code"]: row["item_name"] for row in archive_items}
        material = CrmCustomerCertificationMaterialModel(
            brand_id=case.brand_id,
            customer_id=case.customer_id,
            person_id=case.person_id,
            item_code=data.item_code,
            item_name=data.item_name or item_name_map.get(data.item_code) or data.item_code,
            material_type=data.material_type,
            file_name=data.file_name,
            file_path=data.file_path,
            file_url=data.file_url,
            payload=data.payload,
            collected_by=auth.user.id if auth.user else None,
        )
        cls._stamp_create(auth, material)
        auth.db.add(material)
        await auth.db.flush()
        await auth.db.refresh(material)
        return {
            "id": material.id,
            "item_code": material.item_code,
            "item_name": material.item_name,
            "material_type": material.material_type,
            "file_name": material.file_name,
            "file_path": material.file_path,
            "file_url": material.file_url,
            "payload": material.payload,
            "collected_by": material.collected_by,
            "collected_by_name": auth.user.name if auth.user else None,
            "created_time": material.created_time,
        }

    @classmethod
    async def delete_certification_material_service(cls, auth: AuthSchema, case_id: int, material_id: int) -> None:
        case = await cls._get_case(auth, case_id)
        result = await auth.db.execute(
            select(CrmCustomerCertificationMaterialModel).where(
                CrmCustomerCertificationMaterialModel.id == material_id,
                CrmCustomerCertificationMaterialModel.customer_id == case.customer_id,
                CrmCustomerCertificationMaterialModel.person_id == case.person_id,
                CrmCustomerCertificationMaterialModel.is_deleted == False,
            )
        )
        material = result.scalars().first()
        if not material:
            raise CustomException(msg="认证资料不存在")
        material.is_deleted = True
        material.deleted_time = datetime.now()
        if auth.user and hasattr(material, "deleted_id"):
            material.deleted_id = auth.user.id
        cls._stamp_update(auth, material)

    @classmethod
    def _timeline_item(
        cls,
        *,
        source_type: str,
        record_type: str,
        related_id: int,
        occurred_at: datetime | None,
        title: str,
        content: str | None = None,
        operator_user_id: int | None = None,
        operator_user_name: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict:
        return {
            "id": f"{source_type}:{related_id}:{record_type}",
            "source_type": source_type,
            "record_type": record_type,
            "occurred_at": occurred_at or datetime.now(),
            "title": title,
            "content": content,
            "operator_user_id": operator_user_id,
            "operator_user_name": operator_user_name,
            "related_id": related_id,
            "payload": payload or {},
        }

    @classmethod
    async def timeline_service(cls, auth: AuthSchema, case_id: int) -> list[dict]:
        case = await cls._get_case(auth, case_id)
        customer = await auth.db.get(CrmCustomerProfileModel, case.customer_id)
        items: list[dict] = []
        operator_ids: set[int | None] = set()

        if customer and customer.lead_id:
            lead_records = (
                await auth.db.execute(
                    select(CrmLeadProcessRecordModel)
                    .where(
                        CrmLeadProcessRecordModel.lead_id == customer.lead_id,
                        CrmLeadProcessRecordModel.is_deleted == False,
                    )
                    .order_by(CrmLeadProcessRecordModel.created_time.desc(), CrmLeadProcessRecordModel.id.desc())
                )
            ).scalars().all()
            for row in lead_records:
                operator_ids.add(row.operator_user_id)
                items.append(
                    cls._timeline_item(
                        source_type="lead",
                        record_type=row.action_type,
                        related_id=row.id,
                        occurred_at=row.created_time,
                        title="线索过程",
                        content=row.content,
                        operator_user_id=row.operator_user_id,
                        payload={"lead_id": row.lead_id, "follow_method": row.follow_method, "next_follow_at": row.next_follow_at},
                    )
                )

        customer_records = (
            await auth.db.execute(
                select(CrmCustomerProcessRecordModel)
                .where(
                    CrmCustomerProcessRecordModel.customer_id == case.customer_id,
                    CrmCustomerProcessRecordModel.person_id == case.person_id,
                    CrmCustomerProcessRecordModel.is_deleted == False,
                )
                .order_by(CrmCustomerProcessRecordModel.occurred_at.desc(), CrmCustomerProcessRecordModel.id.desc())
            )
        ).scalars().all()
        for row in customer_records:
            operator_ids.add(row.operator_user_id)
            source_type = "visit" if row.record_type in {"appointment", "visit", "consultation"} else "sales"
            if row.record_type.startswith("service_"):
                source_type = "service"
            items.append(
                cls._timeline_item(
                    source_type=source_type,
                    record_type=row.record_type,
                    related_id=row.id,
                    occurred_at=row.occurred_at,
                    title="客户过程记录",
                    content=row.content,
                    operator_user_id=row.operator_user_id,
                    payload={
                        "method": row.method,
                        "result": row.result,
                        "next_follow_at": row.next_follow_at,
                        "scheduled_at": row.scheduled_at,
                        "appointment_slot": row.appointment_slot,
                        "visit_purpose": row.visit_purpose,
                        "need_summary": row.need_summary,
                        "intention_level": row.intention_level,
                        "next_action": row.next_action,
                    },
                )
            )

        interviews = (
            await auth.db.execute(
                select(DeepInterviewModel)
                .where(DeepInterviewModel.service_case_id == case.id, DeepInterviewModel.is_deleted == False)
                .order_by(DeepInterviewModel.interviewed_at.desc(), DeepInterviewModel.id.desc())
            )
        ).scalars().all()
        for row in interviews:
            operator_ids.add(row.matchmaker_id)
            items.append(
                cls._timeline_item(
                    source_type="service",
                    record_type=f"deep_interview_{row.interview_type}",
                    related_id=row.id,
                    occurred_at=row.interviewed_at,
                    title="深访记录",
                    content=row.summary or row.content,
                    operator_user_id=row.matchmaker_id,
                    payload={"keywords": row.keywords or [], "interview_status": row.interview_status},
                )
            )

        usages = (
            await auth.db.execute(
                select(EntitlementUsageLogModel)
                .where(EntitlementUsageLogModel.service_case_id == case.id, EntitlementUsageLogModel.is_deleted == False)
                .order_by(EntitlementUsageLogModel.occurred_at.desc(), EntitlementUsageLogModel.id.desc())
            )
        ).scalars().all()
        for row in usages:
            operator_ids.add(row.created_id)
            items.append(
                cls._timeline_item(
                    source_type="service",
                    record_type=f"usage_{row.usage_type}",
                    related_id=row.id,
                    occurred_at=row.occurred_at,
                    title="权益核销",
                    content=row.content or row.title,
                    operator_user_id=row.created_id,
                    payload={
                        "quantity": row.quantity,
                        "usage_status": row.usage_status,
                        "candidate_person_id": row.candidate_person_id,
                        "is_overuse": row.is_overuse,
                        "overuse_reason": row.overuse_reason,
                    },
                )
            )

        contracts = await cls._contracts_for_case(auth, case)
        contract_ids = {contract.id for contract in contracts}
        for contract in contracts:
            operator_ids.add(contract.owner_user_id)
            items.append(
                cls._timeline_item(
                    source_type="contract",
                    record_type=f"contract_{contract.contract_status}",
                    related_id=contract.id,
                    occurred_at=contract.effective_at or contract.signed_at or contract.created_time,
                    title="合同记录",
                    content=contract.contract_name,
                    operator_user_id=contract.owner_user_id,
                    payload={"contract_no": contract.contract_no, "contract_amount": contract.contract_amount, "vip_level": contract.vip_level},
                )
            )
        if contract_ids:
            receipts = (
                await auth.db.execute(
                    select(CrmContractReceiptModel)
                    .where(CrmContractReceiptModel.contract_id.in_(contract_ids), CrmContractReceiptModel.is_deleted == False)
                    .order_by(CrmContractReceiptModel.submitted_at.desc(), CrmContractReceiptModel.id.desc())
                )
            ).scalars().all()
            for row in receipts:
                operator_ids.add(row.created_id)
                items.append(
                    cls._timeline_item(
                        source_type="receipt",
                        record_type=f"receipt_{row.receipt_status}",
                        related_id=row.id,
                        occurred_at=row.confirmed_at or row.paid_at or row.submitted_at,
                        title="收款记录",
                        content=row.remark,
                        operator_user_id=row.created_id,
                        payload={
                            "receipt_no": row.receipt_no,
                            "contract_id": row.contract_id,
                            "receipt_type": row.receipt_type,
                            "pay_method": row.pay_method,
                            "amount": row.amount,
                        },
                    )
                )

        service_logs = (
            await auth.db.execute(
                select(VipServiceLogModel)
                .where(
                    VipServiceLogModel.vip_id == case.vip_id,
                    VipServiceLogModel.customer_id == case.customer_id,
                    VipServiceLogModel.is_deleted == False,
                )
                .order_by(VipServiceLogModel.created_time.desc(), VipServiceLogModel.id.desc())
            )
        ).scalars().all()
        for row in service_logs:
            operator_ids.add(row.operator_user_id)
            items.append(
                cls._timeline_item(
                    source_type="service",
                    record_type=f"service_{row.operation_type}",
                    related_id=row.id,
                    occurred_at=row.created_time,
                    title="服务流转",
                    content=row.remark,
                    operator_user_id=row.operator_user_id,
                    payload=row.change_detail or {},
                )
            )

        users = await cls._user_names(auth.db, operator_ids)
        for item in items:
            item["operator_user_name"] = users.get(item["operator_user_id"])
        return sorted(items, key=lambda item: (item["occurred_at"], item["id"]), reverse=True)

    @classmethod
    async def create_customer_process_record_service(cls, auth: AuthSchema, case_id: int, data: ServiceCustomerProcessCreateSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        if not auth.user:
            raise CustomException(msg="无权新增客户过程记录")
        if cls._is_matchmaker(auth) and case.owner_matchmaker_id != auth.user.id:
            raise CustomException(msg="只有当前服务红娘可以新增该客户过程记录")
        if case.case_status not in {"serving", "reopened", "pending_close_review"}:
            raise CustomException(msg="当前服务工单不可新增客户过程记录")
        record = CrmCustomerProcessRecordModel(
            brand_id=case.brand_id,
            customer_id=case.customer_id,
            person_id=case.person_id,
            record_type=data.record_type,
            occurred_at=data.occurred_at or datetime.now(),
            method=data.method,
            result=data.result,
            content=data.content,
            next_follow_at=data.next_follow_at,
            scheduled_at=data.scheduled_at,
            appointment_slot=data.appointment_slot,
            visit_purpose=data.visit_purpose,
            promised_gift=data.promised_gift,
            need_summary=data.need_summary,
            intention_level=data.intention_level,
            next_action=data.next_action,
            enter_signing=data.enter_signing,
            operator_user_id=auth.user.id,
        )
        cls._stamp_create(auth, record)
        auth.db.add(record)
        customer = await auth.db.get(CrmCustomerProfileModel, case.customer_id)
        if customer:
            customer.latest_follow_at = record.occurred_at
            if data.next_follow_at:
                customer.next_follow_at = data.next_follow_at
            cls._stamp_update(auth, customer)
        await auth.db.flush()
        users = await cls._user_names(auth.db, {record.operator_user_id})
        return cls._timeline_item(
            source_type="service" if record.record_type.startswith("service_") else "sales",
            record_type=record.record_type,
            related_id=record.id,
            occurred_at=record.occurred_at,
            title="客户过程记录",
            content=record.content,
            operator_user_id=record.operator_user_id,
            operator_user_name=users.get(record.operator_user_id),
            payload={
                "method": record.method,
                "result": record.result,
                "next_follow_at": record.next_follow_at,
                "scheduled_at": record.scheduled_at,
                "appointment_slot": record.appointment_slot,
                "visit_purpose": record.visit_purpose,
                "promised_gift": record.promised_gift,
                "need_summary": record.need_summary,
                "intention_level": record.intention_level,
                "next_action": record.next_action,
            },
        )

    @classmethod
    async def create_appointment_service(cls, auth: AuthSchema, case_id: int, data: ServiceCustomerProcessCreateSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        if not auth.user or not cls._is_matchmaker(auth) or case.owner_matchmaker_id != auth.user.id:
            raise CustomException(msg="只有当前服务红娘可以发起服务邀约")
        if case.case_status not in {"serving", "reopened"}:
            raise CustomException(msg="当前服务工单不可发起邀约")
        if not data.scheduled_at:
            raise CustomException(msg="邀约必须填写预约日期")
        record = CrmCustomerProcessRecordModel(
            brand_id=case.brand_id,
            customer_id=case.customer_id,
            person_id=case.person_id,
            record_type="appointment",
            occurred_at=datetime.now(),
            method="appointment",
            result="pending",
            content=data.content,
            next_follow_at=data.next_follow_at,
            scheduled_at=data.scheduled_at,
            appointment_slot=data.appointment_slot,
            visit_purpose=data.visit_purpose,
            promised_gift=data.promised_gift,
            appointment_status="pending",
            need_summary=data.need_summary,
            next_action=data.next_action,
            operator_user_id=auth.user.id,
        )
        cls._stamp_create(auth, record)
        auth.db.add(record)
        customer = await auth.db.get(CrmCustomerProfileModel, case.customer_id)
        if customer:
            customer.current_stage = "appointed"
            customer.max_stage = "appointed" if customer.max_stage in {"profiling", "following"} else customer.max_stage
            customer.latest_follow_at = record.occurred_at
            customer.next_follow_at = data.next_follow_at
            cls._stamp_update(auth, customer)
        await auth.db.flush()
        users = await cls._user_names(auth.db, {record.operator_user_id})
        return cls._timeline_item(
            source_type="visit",
            record_type="appointment",
            related_id=record.id,
            occurred_at=record.occurred_at,
            title="服务邀约到店",
            content=record.content,
            operator_user_id=record.operator_user_id,
            operator_user_name=users.get(record.operator_user_id),
            payload={
                "method": record.method,
                "result": record.result,
                "next_follow_at": record.next_follow_at,
                "scheduled_at": record.scheduled_at,
                "appointment_slot": record.appointment_slot,
                "visit_purpose": record.visit_purpose,
                "promised_gift": record.promised_gift,
                "appointment_status": record.appointment_status,
                "need_summary": record.need_summary,
                "next_action": record.next_action,
            },
        )

    @classmethod
    async def lifecycle_service(cls, auth: AuthSchema, case_id: int) -> list[dict]:
        case = await cls._get_case(auth, case_id)
        customer = await auth.db.get(CrmCustomerProfileModel, case.customer_id)
        items: list[dict] = []
        operator_ids: set[int | None] = set()
        if customer and customer.lead_id:
            lead_lifecycles = (
                await auth.db.execute(
                    select(CrmLeadLifecycleModel).where(
                        CrmLeadLifecycleModel.lead_id == customer.lead_id,
                        CrmLeadLifecycleModel.is_deleted == False,
                    )
                )
            ).scalars().all()
            for row in lead_lifecycles:
                operator_ids.add(row.operator_user_id)
                items.append(
                    {
                        "id": f"lead:{row.id}",
                        "stage_group": "lead",
                        "operation_type": row.operation_type,
                        "occurred_at": row.created_time,
                        "title": "线索生命周期",
                        "remark": row.remark,
                        "operator_user_id": row.operator_user_id,
                        "related_id": row.id,
                        "change_detail": row.change_detail,
                    }
                )
        customer_lifecycles = (
            await auth.db.execute(
                select(CrmCustomerLifecycleModel).where(
                    CrmCustomerLifecycleModel.customer_id == case.customer_id,
                    CrmCustomerLifecycleModel.person_id == case.person_id,
                    CrmCustomerLifecycleModel.is_deleted == False,
                )
            )
        ).scalars().all()
        for row in customer_lifecycles:
            operator_ids.add(row.operator_user_id)
            items.append(
                {
                    "id": f"customer:{row.id}",
                    "stage_group": "customer",
                    "operation_type": row.operation_type,
                    "occurred_at": row.created_time,
                    "title": "客户生命周期",
                    "remark": row.remark,
                    "operator_user_id": row.operator_user_id,
                    "related_id": row.id,
                    "change_detail": row.change_detail,
                }
            )
        for contract in await cls._contracts_for_case(auth, case):
            operator_ids.add(contract.owner_user_id)
            items.append(
                {
                    "id": f"contract:{contract.id}",
                    "stage_group": "contract",
                    "operation_type": contract.contract_status,
                    "occurred_at": contract.effective_at or contract.signed_at or contract.created_time,
                    "title": "合同状态",
                    "remark": contract.contract_name,
                    "operator_user_id": contract.owner_user_id,
                    "related_id": contract.id,
                    "change_detail": {"contract_no": contract.contract_no, "amount": contract.contract_amount},
                }
            )
        users = await cls._user_names(auth.db, operator_ids)
        for item in items:
            item["operator_user_name"] = users.get(item["operator_user_id"])
        return sorted(items, key=lambda item: (item["occurred_at"], item["id"]), reverse=True)

    @classmethod
    async def _contracts_for_case(cls, auth: AuthSchema, case: ServiceCaseModel) -> list[CrmContractModel]:
        result = await auth.db.execute(
            select(CrmContractModel)
            .where(
                CrmContractModel.customer_id == case.customer_id,
                CrmContractModel.person_id == case.person_id,
                CrmContractModel.is_deleted == False,
            )
            .options(selectinload(CrmContractModel.items), selectinload(CrmContractModel.attachments), selectinload(CrmContractModel.receipts))
            .order_by(CrmContractModel.created_time.desc(), CrmContractModel.id.desc())
        )
        return list(result.scalars().all())

    @classmethod
    async def contracts_service(cls, auth: AuthSchema, case_id: int) -> list[dict]:
        case = await cls._get_case(auth, case_id)
        contracts = await cls._contracts_for_case(auth, case)
        users = await cls._user_names(auth.db, {contract.owner_user_id for contract in contracts})
        rows: list[dict] = []
        for contract in contracts:
            received_amount, pending_amount, payment_status = cls._payment_summary(contract)
            rows.append(
                {
                    "id": contract.id,
                    "contract_no": contract.contract_no,
                    "contract_name": contract.contract_name,
                    "contract_status": contract.contract_status,
                    "vip_level": contract.vip_level,
                    "store_id": contract.store_id,
                    "owner_user_id": contract.owner_user_id,
                    "owner_user_name": users.get(contract.owner_user_id),
                    "original_amount": contract.original_amount,
                    "contract_amount": contract.contract_amount,
                    "discount_amount": contract.discount_amount,
                    "discount_rate": contract.discount_rate,
                    "discount_reason": contract.discount_reason,
                    "signer_name": contract.signer_name,
                    "signed_at": contract.signed_at,
                    "review_submitted_at": contract.review_submitted_at,
                    "reviewed_at": contract.reviewed_at,
                    "review_remark": contract.review_remark,
                    "effective_at": contract.effective_at,
                    "start_date": contract.start_date,
                    "end_date": contract.end_date,
                    "validity_period": f"{contract.start_date} 至 {contract.end_date}" if contract.start_date and contract.end_date else None,
                    "expire_remind_days": contract.expire_remind_days,
                    "remark": contract.remark,
                    "received_amount": received_amount,
                    "pending_amount": pending_amount,
                    "payment_status": payment_status,
                    "items": [
                        {
                            "id": item.id,
                            "product_id": item.product_id,
                            "product_name_snapshot": item.product_name_snapshot,
                            "price_snapshot": item.price_snapshot,
                            "service_days_snapshot": item.service_days_snapshot,
                            "recommendation_quota_snapshot": item.recommendation_quota_snapshot,
                            "meeting_quota_snapshot": item.meeting_quota_snapshot,
                            "course_quota_snapshot": item.course_quota_snapshot,
                            "supports_online_meeting_snapshot": item.supports_online_meeting_snapshot,
                        }
                        for item in (contract.items or [])
                        if not item.is_deleted
                    ],
                    "attachments": [
                        {
                            "id": attachment.id,
                            "file_name": attachment.file_name,
                            "file_url": attachment.file_url,
                            "file_type": attachment.file_type,
                            "attachment_status": attachment.attachment_status,
                            "created_time": attachment.created_time,
                        }
                        for attachment in (contract.attachments or [])
                        if not attachment.is_deleted
                    ],
                    "receipts": [
                        {
                            "id": receipt.id,
                            "receipt_no": receipt.receipt_no,
                            "receipt_type": receipt.receipt_type,
                            "pay_method": receipt.pay_method,
                            "amount": receipt.amount,
                            "receipt_status": receipt.receipt_status,
                            "submitted_at": receipt.submitted_at,
                            "confirmed_at": receipt.confirmed_at,
                            "remark": receipt.remark,
                        }
                        for receipt in (contract.receipts or [])
                        if not receipt.is_deleted
                    ],
                }
            )
        return rows

    @classmethod
    async def work_summary_service(cls, auth: AuthSchema, case_id: int) -> dict:
        case = await cls._get_case(auth, case_id)
        contracts = await cls._contracts_for_case(auth, case)
        contract_amount = sum((cls._money(contract.contract_amount) for contract in contracts), Decimal("0.00"))
        received_amount = Decimal("0.00")
        pending_amount = Decimal("0.00")
        for contract in contracts:
            received, pending, _ = cls._payment_summary(contract)
            received_amount += received
            pending_amount += pending
        process_count = (
            await auth.db.execute(
                select(func.count(CrmCustomerProcessRecordModel.id)).where(
                    CrmCustomerProcessRecordModel.customer_id == case.customer_id,
                    CrmCustomerProcessRecordModel.person_id == case.person_id,
                    CrmCustomerProcessRecordModel.is_deleted == False,
                    CrmCustomerProcessRecordModel.occurred_at >= case.created_time,
                )
            )
        ).scalar() or 0
        deep_count = (
            await auth.db.execute(
                select(func.count(DeepInterviewModel.id)).where(
                    DeepInterviewModel.service_case_id == case.id,
                    DeepInterviewModel.is_deleted == False,
                )
            )
        ).scalar() or 0
        active_usage_count = (
            await auth.db.execute(
                select(func.count(EntitlementUsageLogModel.id)).where(
                    EntitlementUsageLogModel.service_case_id == case.id,
                    EntitlementUsageLogModel.is_deleted == False,
                    EntitlementUsageLogModel.usage_status == "active",
                )
            )
        ).scalar() or 0
        base = await cls._case_out(auth, case)
        return {
            "entitlement_summary": await cls._entitlement_summary(auth.db, case.id),
            "deep_interview_count": deep_count,
            "active_usage_count": active_usage_count,
            "process_record_count": process_count,
            "contract_count": len(contracts),
            "contract_amount": cls._money(contract_amount),
            "received_amount": cls._money(received_amount),
            "pending_amount": cls._money(pending_amount),
            "remaining_days": base.get("remaining_days"),
        }

    @classmethod
    async def _write_flow_log(
        cls,
        auth: AuthSchema,
        case: ServiceCaseModel,
        operation_type: str,
        before_owner_user_id: int | None,
        after_owner_user_id: int | None,
        before_status: str | None,
        after_status: str | None,
        remark: str | None = None,
    ) -> None:
        log = VipServiceLogModel(
            brand_id=case.brand_id,
            vip_id=case.vip_id,
            person_id=case.person_id,
            customer_id=case.customer_id,
            contract_id=case.contract_id,
            operation_type=operation_type,
            operator_user_id=auth.user.id if auth.user else None,
            before_owner_user_id=before_owner_user_id,
            after_owner_user_id=after_owner_user_id,
            before_status=before_status,
            after_status=after_status,
            change_detail={"case_id": case.id, "vip_id": case.vip_id, "contract_id": case.contract_id},
            remark=remark,
        )
        cls._stamp_create(auth, log)
        auth.db.add(log)
        lifecycle = CrmCustomerLifecycleModel(
            brand_id=case.brand_id,
            customer_id=case.customer_id,
            person_id=case.person_id,
            operation_type=f"service_{operation_type}",
            operator_user_id=auth.user.id if auth.user else None,
            change_detail={
                "case_id": case.id,
                "vip_id": case.vip_id,
                "contract_id": case.contract_id,
                "before_owner_user_id": before_owner_user_id,
                "after_owner_user_id": after_owner_user_id,
                "before_status": before_status,
                "after_status": after_status,
            },
            remark=remark,
        )
        cls._stamp_create(auth, lifecycle)
        auth.db.add(lifecycle)

    @classmethod
    async def assign_service(cls, auth: AuthSchema, vip_id: int, data: VipAssignSchema) -> dict:
        case = await cls._get_case(auth, vip_id)
        await cls._ensure_assign_access(auth, case)
        if case.case_status != "pending_assign":
            raise CustomException(msg="只有待分配服务工单可以分配")
        await cls._validate_matchmaker(auth.db, case.store_id, data.service_owner_user_id)
        before_owner = case.owner_matchmaker_id
        before_status = case.case_status
        now = datetime.now()
        case.owner_matchmaker_id = data.service_owner_user_id
        case.assigned_at = now
        case.assigned_by = auth.user.id if auth.user else None
        case.case_status = "serving"
        case.pool_type = "matchmaker_private"
        case.close_review_status = "none"
        vip = await auth.db.get(CrmVipProfileModel, case.vip_id)
        if vip:
            vip.service_owner_user_id = data.service_owner_user_id
            vip.assigned_at = now
            vip.assigned_by = auth.user.id if auth.user else None
            vip.vip_status = "serving"
            cls._stamp_update(auth, vip)
        cls._stamp_update(auth, case)
        await cls._write_flow_log(auth, case, "assign", before_owner, data.service_owner_user_id, before_status, case.case_status, data.remark)
        await auth.db.flush()
        return await cls._case_out(auth, case)

    @classmethod
    async def transfer_service(cls, auth: AuthSchema, vip_id: int, data: VipAssignSchema) -> dict:
        case = await cls._get_case(auth, vip_id)
        await cls._ensure_assign_access(auth, case)
        if case.case_status not in {"serving", "reopened"}:
            raise CustomException(msg="只有服务中的工单可以改派")
        if case.owner_matchmaker_id == data.service_owner_user_id:
            raise CustomException(msg="新服务红娘不能与当前服务红娘相同")
        await cls._validate_matchmaker(auth.db, case.store_id, data.service_owner_user_id)
        before_owner = case.owner_matchmaker_id
        before_status = case.case_status
        now = datetime.now()
        case.owner_matchmaker_id = data.service_owner_user_id
        case.assigned_at = now
        case.assigned_by = auth.user.id if auth.user else None
        case.case_status = "serving"
        case.pool_type = "matchmaker_private"
        vip = await auth.db.get(CrmVipProfileModel, case.vip_id)
        if vip:
            vip.service_owner_user_id = data.service_owner_user_id
            vip.assigned_at = now
            vip.assigned_by = auth.user.id if auth.user else None
            vip.vip_status = "serving"
            cls._stamp_update(auth, vip)
        cls._stamp_update(auth, case)
        await cls._write_flow_log(auth, case, "transfer", before_owner, data.service_owner_user_id, before_status, case.case_status, data.remark)
        await auth.db.flush()
        return await cls._case_out(auth, case)

    @classmethod
    async def matchmaker_options_service(cls, auth: AuthSchema, store_id: int | None = None) -> list[dict]:
        if not cls._is_brand_admin(auth):
            if not auth.user or not cls._is_store_mgr(auth):
                raise CustomException(msg="无权查询服务红娘")
            if store_id and auth.user.dept_id != store_id:
                raise CustomException(msg="无权查询该门店服务红娘")
            store_id = auth.user.dept_id
        conditions = [
            UserModel.is_deleted == False,
            UserModel.status == "0",
            or_(UserModel.roles.any(RoleModel.code == "MATCHMAKER"), UserModel.positions.any(PositionModel.name == "服务红娘")),
        ]
        if store_id:
            conditions.append(UserModel.dept_id == store_id)
        result = await auth.db.execute(select(UserModel).where(*conditions).order_by(UserModel.dept_id.asc(), UserModel.id.asc()))
        return [MatchmakerOptionSchema(id=user.id, name=user.name, mobile=cls._mask_mobile(user.mobile), dept_id=user.dept_id).model_dump() for user in result.scalars().all()]

    @classmethod
    async def entitlements_service(cls, auth: AuthSchema, case_id: int) -> list[dict]:
        case = await cls._get_case(auth, case_id)
        result = await auth.db.execute(
            select(ServiceEntitlementModel).where(ServiceEntitlementModel.service_case_id == case.id, ServiceEntitlementModel.is_deleted == False).order_by(ServiceEntitlementModel.entitlement_type.asc(), ServiceEntitlementModel.id.asc())
        )
        return [
            {
                "id": item.id,
                "entitlement_type": item.entitlement_type,
                "total_quota": item.total_quota,
                "used_quota": item.used_quota,
                "remaining_quota": item.remaining_quota,
                "unit": item.unit,
                "allow_overuse": item.allow_overuse,
                "entitlement_status": item.entitlement_status,
                "source_contract_item_id": item.source_contract_item_id,
            }
            for item in result.scalars().all()
        ]

    @classmethod
    async def create_usage_service(cls, auth: AuthSchema, case_id: int, data: UsageCreateSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        if not auth.user or not cls._is_matchmaker(auth) or case.owner_matchmaker_id != auth.user.id:
            raise CustomException(msg="只有当前服务红娘可以核销权益")
        if case.case_status not in {"serving", "reopened"}:
            raise CustomException(msg="当前服务工单不可核销")
        entitlement = await auth.db.get(ServiceEntitlementModel, data.entitlement_id)
        if not entitlement or entitlement.is_deleted or entitlement.service_case_id != case.id:
            raise CustomException(msg="请选择当前服务工单下的权益")
        projected_remaining = entitlement.remaining_quota - data.quantity
        is_overuse = projected_remaining < 0
        if is_overuse and not entitlement.allow_overuse:
            raise CustomException(msg="该权益不允许超额核销")
        if is_overuse and not data.overuse_reason:
            raise CustomException(msg="超额核销必须填写超额原因")
        usage = EntitlementUsageLogModel(
            brand_id=case.brand_id,
            entitlement_id=entitlement.id,
            service_case_id=case.id,
            vip_id=case.vip_id,
            contract_id=case.contract_id,
            usage_type=entitlement.entitlement_type,
            quantity=data.quantity,
            usage_status="active",
            occurred_at=data.occurred_at or datetime.now(),
            title=data.title,
            content=data.content,
            candidate_person_id=data.candidate_person_id,
            is_overuse=is_overuse,
            overuse_reason=data.overuse_reason,
            customer_confirm_status=data.customer_confirm_status,
            customer_signature_url=data.customer_signature_url,
            customer_signed_at=data.customer_signed_at,
        )
        cls._stamp_create(auth, usage)
        entitlement.used_quota += data.quantity
        entitlement.remaining_quota = projected_remaining
        entitlement.entitlement_status = "exhausted" if entitlement.remaining_quota <= 0 else "active"
        cls._stamp_update(auth, entitlement)
        auth.db.add(usage)
        await auth.db.flush()
        return (await cls.usage_list_service(auth, case.id, usage_id=usage.id))[0]

    @classmethod
    async def usage_list_service(cls, auth: AuthSchema, case_id: int, usage_id: int | None = None) -> list[dict]:
        case = await cls._get_case(auth, case_id)
        stmt = select(EntitlementUsageLogModel).where(EntitlementUsageLogModel.service_case_id == case.id, EntitlementUsageLogModel.is_deleted == False)
        if usage_id:
            stmt = stmt.where(EntitlementUsageLogModel.id == usage_id)
        result = await auth.db.execute(stmt.order_by(EntitlementUsageLogModel.occurred_at.desc(), EntitlementUsageLogModel.id.desc()))
        rows = result.scalars().all()
        user_names = await cls._user_names(auth.db, {row.created_id for row in rows})
        person_ids = {row.candidate_person_id for row in rows if row.candidate_person_id}
        person_names: dict[int, str] = {}
        if person_ids:
            person_result = await auth.db.execute(select(CrmPersonModel.id, CrmPersonModel.name).where(CrmPersonModel.id.in_(person_ids)))
            person_names = {row[0]: row[1] for row in person_result.all()}
        return [
            {
                "id": row.id,
                "entitlement_id": row.entitlement_id,
                "usage_type": row.usage_type,
                "quantity": row.quantity,
                "usage_status": row.usage_status,
                "occurred_at": row.occurred_at,
                "title": row.title,
                "content": row.content,
                "candidate_person_id": row.candidate_person_id,
                "candidate_name": person_names.get(row.candidate_person_id),
                "is_overuse": row.is_overuse,
                "overuse_reason": row.overuse_reason,
                "void_reason": row.void_reason,
                "customer_confirm_status": row.customer_confirm_status,
                "customer_signature_url": row.customer_signature_url,
                "customer_signed_at": row.customer_signed_at,
                "created_by_name": user_names.get(row.created_id),
            }
            for row in rows
        ]

    @classmethod
    async def void_usage_service(cls, auth: AuthSchema, case_id: int, usage_id: int, data: UsageVoidSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        if not auth.user or not (cls._is_brand_admin(auth) or cls._is_store_mgr(auth) or case.owner_matchmaker_id == auth.user.id):
            raise CustomException(msg="无权作废核销记录")
        usage = await auth.db.get(EntitlementUsageLogModel, usage_id)
        if not usage or usage.is_deleted or usage.service_case_id != case.id:
            raise CustomException(msg="核销记录不存在")
        if usage.usage_status != "active":
            raise CustomException(msg="只有有效核销记录可以作废")
        entitlement = await auth.db.get(ServiceEntitlementModel, usage.entitlement_id)
        if not entitlement:
            raise CustomException(msg="权益账本不存在")
        usage.usage_status = "void"
        usage.void_reason = data.reason
        usage.voided_by = auth.user.id if auth.user else None
        usage.voided_at = datetime.now()
        entitlement.used_quota = max(entitlement.used_quota - usage.quantity, 0)
        entitlement.remaining_quota += usage.quantity
        entitlement.entitlement_status = "active"
        cls._stamp_update(auth, usage)
        cls._stamp_update(auth, entitlement)
        await auth.db.flush()
        return (await cls.usage_list_service(auth, case.id, usage_id=usage.id))[0]

    @classmethod
    async def create_interview_service(cls, auth: AuthSchema, case_id: int, data: DeepInterviewCreateSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        if not auth.user or not cls._is_matchmaker(auth) or case.owner_matchmaker_id != auth.user.id:
            raise CustomException(msg="只有当前服务红娘可以新增深访")
        if case.case_status not in {"serving", "reopened"}:
            raise CustomException(msg="当前服务工单不可新增深访")
        interview = DeepInterviewModel(
            brand_id=case.brand_id,
            service_case_id=case.id,
            vip_id=case.vip_id,
            person_id=case.person_id,
            contract_id=case.contract_id,
            matchmaker_id=case.owner_matchmaker_id,
            interview_type=data.interview_type,
            interviewed_at=data.interviewed_at or datetime.now(),
            content=data.content,
            keywords=data.keywords,
            summary=data.summary,
            interview_status="active",
        )
        cls._stamp_create(auth, interview)
        auth.db.add(interview)
        await auth.db.flush()
        return (await cls.interview_list_service(auth, case.id, interview_id=interview.id))[0]

    @classmethod
    async def interview_list_service(cls, auth: AuthSchema, case_id: int, interview_id: int | None = None) -> list[dict]:
        case = await cls._get_case(auth, case_id)
        stmt = select(DeepInterviewModel).where(DeepInterviewModel.service_case_id == case.id, DeepInterviewModel.is_deleted == False)
        if interview_id:
            stmt = stmt.where(DeepInterviewModel.id == interview_id)
        result = await auth.db.execute(stmt.order_by(DeepInterviewModel.interviewed_at.desc(), DeepInterviewModel.id.desc()))
        rows = result.scalars().all()
        user_names = await cls._user_names(auth.db, {row.matchmaker_id for row in rows} | {row.created_id for row in rows})
        return [
            {
                "id": row.id,
                "interview_type": row.interview_type,
                "interviewed_at": row.interviewed_at,
                "content": row.content,
                "keywords": row.keywords or [],
                "summary": row.summary,
                "interview_status": row.interview_status,
                "matchmaker_id": row.matchmaker_id,
                "matchmaker_name": user_names.get(row.matchmaker_id),
                "created_by_name": user_names.get(row.created_id),
            }
            for row in rows
        ]

    @classmethod
    async def apply_close_service(cls, auth: AuthSchema, case_id: int, data: CloseApplySchema) -> dict:
        case = await cls._get_case(auth, case_id)
        if not auth.user or not cls._is_matchmaker(auth) or case.owner_matchmaker_id != auth.user.id:
            raise CustomException(msg="只有当前服务红娘可以申请关单")
        if case.case_status not in {"serving", "reopened"}:
            raise CustomException(msg="当前服务工单不可申请关单")
        before_status = case.case_status
        case.case_status = "pending_close_review"
        case.close_review_status = "pending"
        case.close_requested_by = auth.user.id
        case.close_requested_at = datetime.now()
        case.close_reason = data.reason
        cls._stamp_update(auth, case)
        await cls._write_flow_log(auth, case, "close_apply", case.owner_matchmaker_id, case.owner_matchmaker_id, before_status, case.case_status, data.reason)
        await auth.db.flush()
        return await cls._case_out(auth, case)

    @classmethod
    async def review_close_service(cls, auth: AuthSchema, case_id: int, data: CloseReviewSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_close_review_access(auth, case)
        if case.close_review_status != "pending":
            raise CustomException(msg="只有待审核关单可以审核")
        before_status = case.case_status
        case.close_reviewed_by = auth.user.id if auth.user else None
        case.close_reviewed_at = datetime.now()
        case.close_review_remark = data.review_remark
        if data.approved:
            case.close_review_status = "approved"
            case.case_status = "closed"
            case.pool_type = "closed"
            vip = await auth.db.get(CrmVipProfileModel, case.vip_id)
            if vip:
                vip.vip_status = "closed"
                vip.ended_at = vip.ended_at or datetime.now()
                cls._stamp_update(auth, vip)
        else:
            case.close_review_status = "rejected"
            case.case_status = "serving"
        cls._stamp_update(auth, case)
        await cls._write_flow_log(auth, case, "close_review", case.owner_matchmaker_id, case.owner_matchmaker_id, before_status, case.case_status, data.review_remark)
        await auth.db.flush()
        return await cls._case_out(auth, case)

    @classmethod
    async def reopen_service(cls, auth: AuthSchema, case_id: int, data: ReopenSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_close_review_access(auth, case)
        if case.case_status != "closed":
            raise CustomException(msg="只有已关单服务可以重开")
        before_status = case.case_status
        case.case_status = "reopened"
        case.pool_type = "matchmaker_private" if case.owner_matchmaker_id else "pending_assign"
        case.close_review_status = "none"
        case.reopened_by = auth.user.id if auth.user else None
        case.reopened_at = datetime.now()
        case.reopen_reason = data.reason
        vip = await auth.db.get(CrmVipProfileModel, case.vip_id)
        if vip:
            vip.vip_status = "serving" if case.owner_matchmaker_id else "pending_assign"
            cls._stamp_update(auth, vip)
        cls._stamp_update(auth, case)
        await cls._write_flow_log(auth, case, "reopen", case.owner_matchmaker_id, case.owner_matchmaker_id, before_status, case.case_status, data.reason)
        await auth.db.flush()
        return await cls._case_out(auth, case)

    @classmethod
    async def ensure_service_case_for_contract(
        cls,
        db: AsyncSession,
        contract: CrmContractModel,
        vip: CrmVipProfileModel,
        operator_user_id: int | None = None,
    ) -> ServiceCaseModel:
        result = await db.execute(select(ServiceCaseModel).where(ServiceCaseModel.contract_id == contract.id, ServiceCaseModel.is_deleted == False))
        case = result.scalars().first()
        if not case:
            case = ServiceCaseModel(
                brand_id=contract.brand_id,
                vip_id=vip.id,
                person_id=contract.person_id,
                customer_id=contract.customer_id,
                contract_id=contract.id,
                store_id=contract.store_id,
                owner_matchmaker_id=vip.service_owner_user_id,
                pool_type="matchmaker_private" if vip.service_owner_user_id else "pending_assign",
                case_status="serving" if vip.service_owner_user_id else "pending_assign",
                close_review_status="none",
            )
            if operator_user_id:
                case.created_id = operator_user_id
                case.updated_id = operator_user_id
            db.add(case)
            await db.flush()

        entitlement_result = await db.execute(
            select(
                ServiceEntitlementModel.source_contract_item_id,
                ServiceEntitlementModel.entitlement_type,
            ).where(
                ServiceEntitlementModel.service_case_id == case.id,
                ServiceEntitlementModel.is_deleted == False,
            )
        )
        existing_entitlements = {tuple(row) for row in entitlement_result.all()}
        result = await db.execute(select(CrmContractItemModel).where(CrmContractItemModel.contract_id == contract.id, CrmContractItemModel.is_deleted == False))
        for item in result.scalars().all():
            rows = [
                ("recommendation", item.recommendation_quota_snapshot, "人"),
                ("meeting", item.meeting_quota_snapshot, "人"),
                ("course", item.course_quota_snapshot, "课时"),
            ]
            for entitlement_type, quota, unit in rows:
                if quota <= 0:
                    continue
                key = (item.id, entitlement_type)
                if key in existing_entitlements:
                    continue
                entitlement = ServiceEntitlementModel(
                    brand_id=contract.brand_id,
                    service_case_id=case.id,
                    vip_id=vip.id,
                    contract_id=contract.id,
                    source_contract_item_id=item.id,
                    entitlement_type=entitlement_type,
                    total_quota=quota,
                    used_quota=0,
                    remaining_quota=quota,
                    unit=unit,
                    allow_overuse=True,
                    entitlement_status="active",
                )
                if operator_user_id:
                    entitlement.created_id = operator_user_id
                    entitlement.updated_id = operator_user_id
                db.add(entitlement)
                existing_entitlements.add(key)
        await db.flush()
        return case

    @classmethod
    async def backfill_effective_contract_service_cases(cls, db: AsyncSession, operator_user_id: int | None = None) -> dict[str, int]:
        stats = {
            "contracts_scanned": 0,
            "vip_created": 0,
            "service_cases_created": 0,
            "entitlements_created": 0,
        }
        result = await db.execute(
            select(CrmContractModel).where(
                CrmContractModel.contract_status == "effective",
                CrmContractModel.is_deleted == False,
            )
        )
        for contract in result.scalars().all():
            stats["contracts_scanned"] += 1
            vip_result = await db.execute(
                select(CrmVipProfileModel).where(
                    CrmVipProfileModel.contract_id == contract.id,
                    CrmVipProfileModel.is_deleted == False,
                )
            )
            vip = vip_result.scalars().first()
            if not vip:
                vip = CrmVipProfileModel(
                    brand_id=contract.brand_id,
                    person_id=contract.person_id,
                    customer_id=contract.customer_id,
                    contract_id=contract.id,
                    store_id=contract.store_id,
                    vip_level=contract.vip_level,
                    started_at=contract.effective_at or datetime.now(),
                    ended_at=datetime.combine(contract.end_date, time.min) if contract.end_date else None,
                )
                if operator_user_id:
                    vip.created_id = operator_user_id
                    vip.updated_id = operator_user_id
                db.add(vip)
                await db.flush()
                stats["vip_created"] += 1

            case_exists = await db.scalar(
                select(func.count(ServiceCaseModel.id)).where(
                    ServiceCaseModel.contract_id == contract.id,
                    ServiceCaseModel.is_deleted == False,
                )
            )
            entitlement_before = await db.scalar(
                select(func.count(ServiceEntitlementModel.id)).where(
                    ServiceEntitlementModel.contract_id == contract.id,
                    ServiceEntitlementModel.is_deleted == False,
                )
            )
            await cls.ensure_service_case_for_contract(db=db, contract=contract, vip=vip, operator_user_id=operator_user_id)
            entitlement_after = await db.scalar(
                select(func.count(ServiceEntitlementModel.id)).where(
                    ServiceEntitlementModel.contract_id == contract.id,
                    ServiceEntitlementModel.is_deleted == False,
                )
            )
            if not case_exists:
                stats["service_cases_created"] += 1
            stats["entitlements_created"] += int((entitlement_after or 0) - (entitlement_before or 0))
        await db.flush()
        return stats


class CandidateService:
    """红娘私有备选库服务层"""

    STORE_JOIN_REQUIRES_REVIEW_KEY = "service.candidate.store_join_requires_review"

    @classmethod
    async def _resolve_matchmaker_id(cls, auth: AuthSchema, matchmaker_id: int | None = None) -> int:
        if not auth.user:
            raise CustomException(msg="未登录")
        if VipService._is_matchmaker(auth):
            if matchmaker_id and matchmaker_id != auth.user.id and not (VipService._is_brand_admin(auth) or VipService._is_store_mgr(auth)):
                raise CustomException(msg="只能维护自己的备选库")
            return matchmaker_id or auth.user.id
        if not (VipService._is_brand_admin(auth) or VipService._is_store_mgr(auth)):
            raise CustomException(msg="无权维护备选库")
        if not matchmaker_id:
            raise CustomException(msg="请选择归属服务红娘")
        result = await auth.db.execute(
            select(UserModel)
            .options(selectinload(UserModel.roles), selectinload(UserModel.positions))
            .where(UserModel.id == matchmaker_id)
        )
        matchmaker = result.scalars().first()
        if not matchmaker or matchmaker.is_deleted or matchmaker.status != "0":
            raise CustomException(msg="归属服务红娘不存在或已停用")
        if not VipService._is_brand_admin(auth) and matchmaker.dept_id != auth.user.dept_id:
            raise CustomException(msg="只能维护本门店红娘的备选库")
        has_matchmaker_role = any(role.code == "MATCHMAKER" and role.status == "0" for role in matchmaker.roles or [])
        has_matchmaker_position = any(position.name == "服务红娘" and position.status == "0" for position in matchmaker.positions or [])
        if not has_matchmaker_role and not has_matchmaker_position:
            raise CustomException(msg="归属用户不是服务红娘")
        return matchmaker.id

    @classmethod
    async def _candidate_out(cls, auth: AuthSchema, item: BackupPoolItemModel) -> dict:
        person = await auth.db.get(CrmPersonModel, item.person_id)
        store = await auth.db.get(DeptModel, item.store_id) if item.store_id else None
        users = await VipService._user_names(auth.db, {item.matchmaker_id})
        can_view_phone = bool(
            auth.user
            and (
                (auth.user.id == item.matchmaker_id and item.contact_unmasked_after_approval)
                or VipService._has_permission(auth, "service:candidate:view_phone")
                or VipService._is_brand_admin(auth)
            )
        )
        mobile = person.primary_mobile if person else None
        if not can_view_phone:
            mobile = VipService._mask_mobile(mobile)
        return {
            "id": item.id,
            "candidate_id": item.candidate_id,
            "person_id": item.person_id,
            "matchmaker_id": item.matchmaker_id,
            "matchmaker_name": users.get(item.matchmaker_id),
            "store_id": item.store_id,
            "store_name": store.name if store else None,
            "source_type": item.source_type,
            "name": person.name if person else "",
            "gender": person.gender if person else "",
            "mobile": mobile,
            "wechat": person.wechat if person and can_view_phone else None,
            "birth_date": person.birth_date if person else None,
            "age": VipService._age(person.birth_date if person else None),
            "height_cm": person.height_cm if person else None,
            "residence": person.residence if person else None,
            "education": person.education if person else None,
            "annual_income": person.annual_income if person else None,
            "marital_status": person.marital_status if person else None,
            "private_tags": item.private_tags or [],
            "private_remark": item.private_remark,
            "join_request_id": item.join_request_id,
            "approved_by": item.approved_by,
            "approved_at": item.approved_at,
            "contact_unmasked_after_approval": item.contact_unmasked_after_approval,
            "created_time": item.created_time,
        }

    @classmethod
    async def _ensure_candidate_profile(cls, auth: AuthSchema, person_id: int) -> CandidateProfileModel:
        result = await auth.db.execute(select(CandidateProfileModel).where(CandidateProfileModel.person_id == person_id, CandidateProfileModel.is_deleted == False))
        candidate = result.scalars().first()
        if candidate:
            return candidate
        candidate = CandidateProfileModel(brand_id=1, person_id=person_id, candidate_status="active")
        VipService._stamp_create(auth, candidate)
        auth.db.add(candidate)
        await auth.db.flush()
        return candidate

    @classmethod
    async def _person_store_map(cls, auth: AuthSchema, person_ids: list[int]) -> dict[int, int]:
        store_map: dict[int, int] = {}
        if not person_ids:
            return store_map
        customer_store_result = await auth.db.execute(
            select(CrmCustomerProfileModel.person_id, CrmCustomerProfileModel.store_id).where(
                CrmCustomerProfileModel.person_id.in_(person_ids),
                CrmCustomerProfileModel.is_deleted == False,
            )
        )
        store_map.update({person_id: store_id for person_id, store_id in customer_store_result.all() if store_id})
        missing_store_person_ids = [person_id for person_id in person_ids if person_id not in store_map]
        if missing_store_person_ids:
            lead_store_result = await auth.db.execute(
                select(CrmLeadProfileModel.person_id, CrmLeadProfileModel.store_id).where(
                    CrmLeadProfileModel.person_id.in_(missing_store_person_ids),
                    CrmLeadProfileModel.is_deleted == False,
                )
            )
            store_map.update({person_id: store_id for person_id, store_id in lead_store_result.all() if store_id})
        return store_map

    @classmethod
    async def _person_in_store(cls, auth: AuthSchema, person_id: int, store_id: int | None) -> bool:
        if not store_id:
            return False
        customer_exists = await auth.db.scalar(
            select(func.count(CrmCustomerProfileModel.id)).where(
                CrmCustomerProfileModel.person_id == person_id,
                CrmCustomerProfileModel.store_id == store_id,
                CrmCustomerProfileModel.is_deleted == False,
            )
        )
        if customer_exists:
            return True
        lead_exists = await auth.db.scalar(
            select(func.count(CrmLeadProfileModel.id)).where(
                CrmLeadProfileModel.person_id == person_id,
                CrmLeadProfileModel.store_id == store_id,
                CrmLeadProfileModel.is_deleted == False,
            )
        )
        return bool(lead_exists)

    @classmethod
    async def _dept_names(cls, auth: AuthSchema, dept_ids: set[int]) -> dict[int, str]:
        if not dept_ids:
            return {}
        result = await auth.db.execute(select(DeptModel.id, DeptModel.name).where(DeptModel.id.in_(dept_ids)))
        return {row.id: row.name for row in result.all()}

    @classmethod
    def _mask_wechat(cls, wechat: str | None) -> str | None:
        if not wechat:
            return None
        if len(wechat) <= 4:
            return f"{wechat[:1]}***"
        return f"{wechat[:2]}***{wechat[-2:]}"

    @classmethod
    def _birth_date_for_age(cls, age: int) -> date:
        today = date.today()
        try:
            return today.replace(year=today.year - age)
        except ValueError:
            return today.replace(year=today.year - age, day=28)

    @classmethod
    def _json_any_contains(cls, column: Any, values: list[str]) -> Any | None:
        values = [value for value in values if value]
        if not values:
            return None
        text_column = cast(column, String)
        return or_(*[text_column.like(f"%{value}%") for value in values])

    @classmethod
    def _review_allowed(cls, auth: AuthSchema, request_scope: str, request_store_id: int | None) -> bool:
        if VipService._is_brand_admin(auth):
            return True
        if request_scope == "store" and VipService._is_store_mgr(auth) and auth.user and auth.user.dept_id == request_store_id:
            return True
        return False

    @classmethod
    async def _get_param_value(cls, auth: AuthSchema, key: str, default: str) -> str:
        value = await auth.db.scalar(
            select(ParamsModel.config_value).where(
                ParamsModel.config_key == key,
                ParamsModel.status == "0",
                ParamsModel.is_deleted == False,
            )
        )
        return value if value not in (None, "") else default

    @classmethod
    async def _set_param_value(cls, auth: AuthSchema, key: str, value: str, name: str, description: str) -> None:
        result = await auth.db.execute(select(ParamsModel).where(ParamsModel.config_key == key, ParamsModel.is_deleted == False))
        param = result.scalars().first()
        if param:
            param.config_value = value
            param.config_name = name
            param.description = description
            if auth.user and hasattr(param, "updated_id"):
                param.updated_id = auth.user.id
        else:
            param = ParamsModel(config_name=name, config_key=key, config_value=value, config_type=True, status="0", description=description)
            VipService._stamp_create(auth, param)
            auth.db.add(param)
        await auth.db.flush()

    @classmethod
    async def _store_join_requires_review(cls, auth: AuthSchema) -> bool:
        value = await cls._get_param_value(auth, cls.STORE_JOIN_REQUIRES_REVIEW_KEY, "true")
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @classmethod
    async def get_rule_service(cls, auth: AuthSchema) -> dict:
        if not (VipService._is_store_mgr(auth) or VipService._is_brand_admin(auth)):
            raise CustomException(msg="无权查看备选规则", code=10403, status_code=403)
        return {
            "store_join_requires_review": await cls._store_join_requires_review(auth),
            "brand_join_requires_review": True,
        }

    @classmethod
    async def update_rule_service(cls, auth: AuthSchema, data: CandidateRuleUpdateSchema) -> dict:
        if not (VipService._is_store_mgr(auth) or VipService._is_brand_admin(auth)):
            raise CustomException(msg="无权设置备选规则", code=10403, status_code=403)
        await cls._set_param_value(
            auth,
            cls.STORE_JOIN_REQUIRES_REVIEW_KEY,
            "true" if data.store_join_requires_review else "false",
            "本门店备选加入需要审核",
            "本门店范围候选加入备选库是否需要门店管理员审批；品牌范围始终需要审核",
        )
        return await cls.get_rule_service(auth)

    @classmethod
    async def _create_backup_from_request(cls, auth: AuthSchema, request: CandidateJoinRequestModel) -> BackupPoolItemModel:
        candidate = await cls._ensure_candidate_profile(auth, request.person_id)
        exists = await auth.db.execute(
            select(BackupPoolItemModel).where(
                BackupPoolItemModel.matchmaker_id == request.request_matchmaker_id,
                BackupPoolItemModel.person_id == request.person_id,
                BackupPoolItemModel.is_deleted == False,
            )
        )
        item = exists.scalars().first()
        if item:
            return item
        item = BackupPoolItemModel(
            brand_id=request.brand_id,
            candidate_id=candidate.id,
            person_id=request.person_id,
            store_id=request.person_store_id,
            matchmaker_id=request.request_matchmaker_id,
            source_type="brand_review_join" if request.request_scope == "brand" else "store_review_join",
            private_tags=request.private_tags_snapshot or [],
            private_remark=request.private_remark_snapshot,
            join_request_id=request.id,
            approved_by=auth.user.id if auth.user else None,
            approved_at=datetime.now(),
            contact_unmasked_after_approval=True,
        )
        VipService._stamp_create(auth, item)
        auth.db.add(item)
        await auth.db.flush()
        return item

    @classmethod
    async def _join_request_out(cls, auth: AuthSchema, item: CandidateJoinRequestModel) -> dict:
        person = await auth.db.get(CrmPersonModel, item.person_id)
        dept_ids = {dept_id for dept_id in [item.person_store_id, item.request_store_id] if dept_id}
        dept_names = await cls._dept_names(auth, dept_ids)
        user_ids = {user_id for user_id in [item.request_matchmaker_id, item.reviewer_id] if user_id}
        user_names = await VipService._user_names(auth.db, user_ids)
        return {
            "id": item.id,
            "person_id": item.person_id,
            "person_name": person.name if person else None,
            "person_display_no": person.display_no if person else None,
            "person_gender": person.gender if person else None,
            "person_mobile": VipService._mask_mobile(person.primary_mobile if person else None),
            "person_wechat": cls._mask_wechat(person.wechat if person else None),
            "person_store_id": item.person_store_id,
            "person_store_name": dept_names.get(item.person_store_id or 0),
            "request_scope": item.request_scope,
            "request_matchmaker_id": item.request_matchmaker_id,
            "request_matchmaker_name": user_names.get(item.request_matchmaker_id),
            "request_store_id": item.request_store_id,
            "request_store_name": dept_names.get(item.request_store_id or 0),
            "private_tags_snapshot": item.private_tags_snapshot or [],
            "private_remark_snapshot": item.private_remark_snapshot,
            "request_reason": item.request_reason,
            "review_status": item.review_status,
            "reviewer_id": item.reviewer_id,
            "reviewer_name": user_names.get(item.reviewer_id) if item.reviewer_id else None,
            "reviewed_at": item.reviewed_at,
            "review_remark": item.review_remark,
            "approved_backup_item_id": item.approved_backup_item_id,
            "created_time": item.created_time,
        }

    @classmethod
    def _preference_filters(cls, data: CandidateDiscoverSchema) -> list[Any]:
        filters: list[Any] = [
            PersonPartnerPreferenceModel.is_deleted == False,
            PersonPartnerPreferenceModel.is_effective == True,
        ]
        interval_map = [
            (data.pref_age_min, data.pref_age_max, PersonPartnerPreferenceModel.age_min, PersonPartnerPreferenceModel.age_max),
            (data.pref_height_min, data.pref_height_max, PersonPartnerPreferenceModel.height_min_cm, PersonPartnerPreferenceModel.height_max_cm),
            (data.pref_weight_min, data.pref_weight_max, PersonPartnerPreferenceModel.weight_min_kg, PersonPartnerPreferenceModel.weight_max_kg),
        ]
        for min_value, max_value, col_min, col_max in interval_map:
            if min_value is not None:
                filters.append(or_(col_max.is_(None), col_max >= min_value))
            if max_value is not None:
                filters.append(or_(col_min.is_(None), col_min <= max_value))
        json_fields = [
            (PersonPartnerPreferenceModel.preferred_residence_region_codes, data.preferred_residence_region_codes),
            (PersonPartnerPreferenceModel.preferred_hometown_region_codes, data.preferred_hometown_region_codes),
            (PersonPartnerPreferenceModel.preferred_education_codes, data.preferred_education_codes),
            (PersonPartnerPreferenceModel.preferred_marital_status_codes, data.preferred_marital_status_codes),
            (PersonPartnerPreferenceModel.preferred_annual_income_codes, data.preferred_annual_income_codes),
            (PersonPartnerPreferenceModel.preferred_house_status_codes, data.preferred_house_status_codes),
            (PersonPartnerPreferenceModel.preferred_car_status_codes, data.preferred_car_status_codes),
            (PersonPartnerPreferenceModel.hard_reject_items, data.hard_reject_items),
            (PersonPartnerPreferenceModel.soft_preference_items, data.soft_preference_items),
            (PersonPartnerPreferenceModel.preferred_personality_tags, data.preferred_personality_tags),
            (PersonPartnerPreferenceModel.preferred_lifestyle_tags, data.preferred_lifestyle_tags),
            (PersonPartnerPreferenceModel.preferred_relationship_tags, data.preferred_relationship_tags),
            (PersonPartnerPreferenceModel.must_match_fields, data.must_match_fields),
            (PersonPartnerPreferenceModel.preferred_match_fields, data.preferred_match_fields),
        ]
        for column, values in json_fields:
            condition = cls._json_any_contains(column, values)
            if condition is not None:
                filters.append(condition)
        bool_fields = [
            (PersonPartnerPreferenceModel.accept_long_distance, data.pref_accept_long_distance),
            (PersonPartnerPreferenceModel.accept_divorced, data.pref_accept_divorced),
            (PersonPartnerPreferenceModel.accept_children, data.pref_accept_children),
        ]
        for column, value in bool_fields:
            if value is not None:
                filters.append(column == value)
        text_fields = [
            (PersonPartnerPreferenceModel.children_requirement, data.children_requirement),
            (PersonPartnerPreferenceModel.preferred_occupation_text, data.preferred_occupation_text),
            (PersonPartnerPreferenceModel.preference_text, data.preference_text),
        ]
        for column, value in text_fields:
            if value:
                filters.append(column.like(f"%{value.strip()}%"))
        if data.strictness_level:
            filters.append(PersonPartnerPreferenceModel.strictness_level == data.strictness_level)
        return filters

    @classmethod
    def _has_preference_filter(cls, data: CandidateDiscoverSchema) -> bool:
        return len(cls._preference_filters(data)) > 2

    @classmethod
    async def discover_service(cls, auth: AuthSchema, data: CandidateDiscoverSchema) -> dict:
        if not auth.user or not (VipService._is_matchmaker(auth) or VipService._is_store_mgr(auth) or VipService._is_brand_admin(auth)):
            raise CustomException(msg="无权进行候选发现")
        if data.scope not in {"store", "brand"}:
            raise CustomException(msg="搜索范围不正确")
        matchmaker_id: int | None = None
        matchmaker: UserModel | None = None
        if data.matchmaker_id or VipService._is_matchmaker(auth):
            matchmaker_id = await cls._resolve_matchmaker_id(auth, data.matchmaker_id)
            matchmaker = await auth.db.get(UserModel, matchmaker_id)
        conditions: list[Any] = [CrmPersonModel.is_deleted == False]
        if data.scope == "store":
            store_id = matchmaker.dept_id if matchmaker else auth.user.dept_id
            if not store_id:
                raise CustomException(msg="请选择归属红娘后搜索本门店范围，或切换到品牌范围")
            conditions.append(
                or_(
                    CrmPersonModel.id.in_(
                        select(CrmCustomerProfileModel.person_id).where(
                            CrmCustomerProfileModel.store_id == store_id,
                            CrmCustomerProfileModel.is_deleted == False,
                        )
                    ),
                    CrmPersonModel.id.in_(
                        select(CrmLeadProfileModel.person_id).where(
                            CrmLeadProfileModel.store_id == store_id,
                            CrmLeadProfileModel.is_deleted == False,
                        )
                    ),
                )
            )
        if data.keyword:
            like = f"%{data.keyword.strip()}%"
            conditions.append(or_(CrmPersonModel.name.like(like), CrmPersonModel.primary_mobile.like(like), CrmPersonModel.display_no.like(like), cast(CrmPersonModel.id, String).like(like)))
        exact_fields = [
            (CrmPersonModel.id, data.person_id),
            (CrmPersonModel.display_no, data.display_no),
            (CrmPersonModel.primary_mobile, data.mobile),
            (CrmPersonModel.name, data.name),
            (CrmPersonModel.gender, data.gender),
            (CrmPersonModel.education, data.education),
            (CrmPersonModel.annual_income, data.annual_income),
            (CrmPersonModel.marital_status, data.marital_status),
            (CrmPersonModel.ethnicity, data.ethnicity),
            (CrmPersonModel.occupation_code, data.occupation_code),
            (CrmPersonModel.unit_type, data.unit_type),
            (CrmPersonModel.house_status, data.house_status),
            (CrmPersonModel.car_status, data.car_status),
            (CrmPersonModel.marriage_plan, data.marriage_plan),
            (CrmPersonModel.certification_level, data.certification_level),
        ]
        for column, value in exact_fields:
            if value is not None and value != "":
                conditions.append(column == value)
        for column, value in [(CrmPersonModel.residence, data.residence), (CrmPersonModel.hometown, data.hometown)]:
            if value:
                conditions.append(column.like(f"%{value.strip()}%"))
        if data.age_min is not None:
            conditions.append(CrmPersonModel.birth_date <= cls._birth_date_for_age(data.age_min))
        if data.age_max is not None:
            conditions.append(CrmPersonModel.birth_date >= cls._birth_date_for_age(data.age_max + 1))
        if data.height_min is not None:
            conditions.append(CrmPersonModel.height_cm >= data.height_min)
        if data.height_max is not None:
            conditions.append(CrmPersonModel.height_cm <= data.height_max)
        if data.weight_min is not None:
            conditions.append(CrmPersonModel.weight_kg >= data.weight_min)
        if data.weight_max is not None:
            conditions.append(CrmPersonModel.weight_kg <= data.weight_max)
        bool_fields = [
            (CrmPersonModel.accept_long_distance_self, data.accept_long_distance_self),
            (CrmPersonModel.accept_flash_marriage, data.accept_flash_marriage),
            (CrmPersonModel.willing_relocate, data.willing_relocate),
        ]
        for column, value in bool_fields:
            if value is not None:
                conditions.append(column == value)
        if data.has_photo is True:
            conditions.append(cast(CrmPersonModel.photo_urls, String).notin_(["null", "[]"]))
        elif data.has_photo is False:
            conditions.append(or_(CrmPersonModel.photo_urls.is_(None), cast(CrmPersonModel.photo_urls, String).in_(["null", "[]"])))

        base = select(CrmPersonModel)
        count_stmt = select(func.count(CrmPersonModel.id))
        if cls._has_preference_filter(data):
            pref_filters = cls._preference_filters(data)
            base = base.join(PersonPartnerPreferenceModel, PersonPartnerPreferenceModel.person_id == CrmPersonModel.id)
            count_stmt = count_stmt.join(PersonPartnerPreferenceModel, PersonPartnerPreferenceModel.person_id == CrmPersonModel.id)
            conditions.extend(pref_filters)
        total = await auth.db.scalar(count_stmt.where(*conditions)) or 0
        offset = (data.page_no - 1) * data.page_size
        result = await auth.db.execute(base.where(*conditions).order_by(CrmPersonModel.id.desc()).offset(offset).limit(data.page_size))
        people = result.scalars().all()
        person_ids = [person.id for person in people]
        store_map = await cls._person_store_map(auth, person_ids)
        backup_ids: set[int] = set()
        pending_ids: set[int] = set()
        if matchmaker_id:
            backup_result = await auth.db.execute(
                select(BackupPoolItemModel.person_id).where(
                    BackupPoolItemModel.matchmaker_id == matchmaker_id,
                    BackupPoolItemModel.person_id.in_(person_ids or [-1]),
                    BackupPoolItemModel.is_deleted == False,
                )
            )
            backup_ids = set(backup_result.scalars().all())
            pending_result = await auth.db.execute(
                select(CandidateJoinRequestModel.person_id).where(
                    CandidateJoinRequestModel.request_matchmaker_id == matchmaker_id,
                    CandidateJoinRequestModel.person_id.in_(person_ids or [-1]),
                    CandidateJoinRequestModel.review_status == "pending",
                    CandidateJoinRequestModel.is_deleted == False,
                )
            )
            pending_ids = set(pending_result.scalars().all())
        dept_names = await cls._dept_names(auth, {store_id for store_id in store_map.values() if store_id})
        items = [
            {
                "id": person.id,
                "display_no": person.display_no,
                "name": person.name,
                "gender": person.gender,
                "mobile": VipService._mask_mobile(person.primary_mobile),
                "wechat": cls._mask_wechat(person.wechat),
                "store_id": store_map.get(person.id),
                "store_name": dept_names.get(store_map.get(person.id) or 0),
                "age": VipService._age(person.birth_date),
                "height_cm": person.height_cm,
                "weight_kg": person.weight_kg,
                "residence": person.residence,
                "hometown": person.hometown,
                "education": person.education,
                "annual_income": person.annual_income,
                "marital_status": person.marital_status,
                "has_photo": bool(person.photo_urls),
                "certification_level": person.certification_level,
                "already_in_backup": person.id in backup_ids,
                "pending_request": person.id in pending_ids,
            }
            for person in people
        ]
        return {"page_no": data.page_no, "page_size": data.page_size, "total": total, "has_next": offset + data.page_size < total, "items": items}

    @classmethod
    async def create_join_request_service(cls, auth: AuthSchema, data: CandidateJoinRequestCreateSchema) -> dict:
        if not auth.user:
            raise CustomException(msg="未登录")
        if data.scope not in {"store", "brand"}:
            raise CustomException(msg="申请范围不正确")
        matchmaker_id = await cls._resolve_matchmaker_id(auth, data.matchmaker_id)
        matchmaker = await auth.db.get(UserModel, matchmaker_id)
        person = await auth.db.get(CrmPersonModel, data.person_id)
        if not person or person.is_deleted:
            raise CustomException(msg="人员不存在")
        if data.scope == "store" and not await cls._person_in_store(auth, person.id, matchmaker.dept_id if matchmaker else None):
            raise CustomException(msg="本门店范围只能申请本门店人员")
        exists = await auth.db.execute(
            select(BackupPoolItemModel).where(
                BackupPoolItemModel.matchmaker_id == matchmaker_id,
                BackupPoolItemModel.person_id == person.id,
                BackupPoolItemModel.is_deleted == False,
            )
        )
        if exists.scalars().first():
            raise CustomException(msg="该人员已在备选库中")
        pending = await auth.db.execute(
            select(CandidateJoinRequestModel).where(
                CandidateJoinRequestModel.request_matchmaker_id == matchmaker_id,
                CandidateJoinRequestModel.person_id == person.id,
                CandidateJoinRequestModel.review_status == "pending",
                CandidateJoinRequestModel.is_deleted == False,
            )
        )
        if pending.scalars().first():
            raise CustomException(msg="该人员已有待审核加入申请")
        person_store_map = await cls._person_store_map(auth, [person.id])
        request = CandidateJoinRequestModel(
            brand_id=person.brand_id,
            person_id=person.id,
            person_store_id=person_store_map.get(person.id),
            request_scope=data.scope,
            request_matchmaker_id=matchmaker_id,
            request_store_id=matchmaker.dept_id if matchmaker else auth.user.dept_id,
            private_tags_snapshot=data.private_tags,
            private_remark_snapshot=data.private_remark,
            request_reason=data.request_reason,
            review_status="pending",
        )
        VipService._stamp_create(auth, request)
        auth.db.add(request)
        await auth.db.flush()
        store_auto_approve = request.request_scope == "store" and not await cls._store_join_requires_review(auth)
        if store_auto_approve or cls._review_allowed(auth, request.request_scope, request.request_store_id):
            request.review_status = "approved"
            request.reviewer_id = auth.user.id if auth.user else None
            request.reviewed_at = datetime.now()
            request.review_remark = "本门店备选规则配置为免审核，自动通过" if store_auto_approve else "发起人具备审核权限，自动通过"
            item = await cls._create_backup_from_request(auth, request)
            request.approved_backup_item_id = item.id
            VipService._stamp_update(auth, request)
            await auth.db.flush()
        return await cls._join_request_out(auth, request)

    @classmethod
    async def join_request_page_service(cls, auth: AuthSchema, page_no: int, page_size: int, search: CandidateJoinRequestQueryParam) -> dict:
        if not auth.user:
            raise CustomException(msg="未登录")
        conditions: list[Any] = [CandidateJoinRequestModel.is_deleted == False]
        if search.review_status:
            conditions.append(CandidateJoinRequestModel.review_status == search.review_status)
        if search.scope:
            conditions.append(CandidateJoinRequestModel.request_scope == search.scope)
        if search.mine is True or (VipService._is_matchmaker(auth) and not (VipService._is_store_mgr(auth) or VipService._is_brand_admin(auth))):
            conditions.append(CandidateJoinRequestModel.request_matchmaker_id == auth.user.id)
        elif VipService._is_store_mgr(auth) and not VipService._is_brand_admin(auth):
            conditions.append(CandidateJoinRequestModel.request_store_id == auth.user.dept_id)
            conditions.append(CandidateJoinRequestModel.request_scope == "store")
        elif not VipService._is_brand_admin(auth):
            conditions.append(CandidateJoinRequestModel.id == -1)
        total = await auth.db.scalar(select(func.count(CandidateJoinRequestModel.id)).where(*conditions)) or 0
        offset = (page_no - 1) * page_size
        result = await auth.db.execute(
            select(CandidateJoinRequestModel)
            .where(*conditions)
            .order_by(CandidateJoinRequestModel.created_time.desc(), CandidateJoinRequestModel.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = [await cls._join_request_out(auth, item) for item in result.scalars().all()]
        return {"page_no": page_no, "page_size": page_size, "total": total, "has_next": offset + page_size < total, "items": items}

    @classmethod
    async def review_join_request_service(cls, auth: AuthSchema, request_id: int, data: CandidateJoinRequestReviewSchema) -> dict:
        if data.review_status not in {"approved", "rejected"}:
            raise CustomException(msg="审核结果不正确")
        request = await auth.db.get(CandidateJoinRequestModel, request_id)
        if not request or request.is_deleted:
            raise CustomException(msg="加入申请不存在")
        if request.review_status != "pending":
            raise CustomException(msg="该申请已审核，不能重复处理")
        if not cls._review_allowed(auth, request.request_scope, request.request_store_id):
            raise CustomException(msg="无权审核该加入申请")
        request.review_status = data.review_status
        request.reviewer_id = auth.user.id if auth.user else None
        request.reviewed_at = datetime.now()
        request.review_remark = data.review_remark
        if data.review_status == "approved":
            item = await cls._create_backup_from_request(auth, request)
            request.approved_backup_item_id = item.id
        VipService._stamp_update(auth, request)
        await auth.db.flush()
        return await cls._join_request_out(auth, request)

    @classmethod
    async def page_service(cls, auth: AuthSchema, page_no: int, page_size: int, search: CandidateQueryParam | None = None) -> dict:
        conditions = [BackupPoolItemModel.is_deleted == False]
        if VipService._is_matchmaker(auth) and auth.user and (not search or search.mine is not False):
            conditions.append(BackupPoolItemModel.matchmaker_id == auth.user.id)
        elif VipService._is_store_mgr(auth) and auth.user:
            store_matchmaker_ids = select(UserModel.id).where(UserModel.dept_id == auth.user.dept_id, UserModel.is_deleted == False)
            conditions.append(BackupPoolItemModel.matchmaker_id.in_(store_matchmaker_ids))
        elif not VipService._is_brand_admin(auth):
            conditions.append(BackupPoolItemModel.id == -1)
        if search and search.source_type:
            conditions.append(BackupPoolItemModel.source_type == search.source_type)
        if search and search.keyword:
            like = f"%{search.keyword}%"
            conditions.append(or_(CrmPersonModel.name.like(like), CrmPersonModel.primary_mobile.like(like), CrmPersonModel.display_no.like(like)))
        base = select(BackupPoolItemModel).join(CrmPersonModel, BackupPoolItemModel.person_id == CrmPersonModel.id).where(*conditions)
        total = (await auth.db.execute(select(func.count(BackupPoolItemModel.id)).join(CrmPersonModel, BackupPoolItemModel.person_id == CrmPersonModel.id).where(*conditions))).scalar() or 0
        offset = (page_no - 1) * page_size
        result = await auth.db.execute(base.order_by(BackupPoolItemModel.created_time.desc(), BackupPoolItemModel.id.desc()).offset(offset).limit(page_size))
        items = [await cls._candidate_out(auth, item) for item in result.scalars().all()]
        return {"page_no": page_no, "page_size": page_size, "total": total, "has_next": offset + page_size < total, "items": items}

    @classmethod
    async def search_person_service(cls, auth: AuthSchema, keyword: str | None = None, limit: int = 20) -> list[dict]:
        if not auth.user or not (VipService._is_matchmaker(auth) or VipService._is_store_mgr(auth) or VipService._is_brand_admin(auth)):
            raise CustomException(msg="无权查询备选资源")
        conditions = [CrmPersonModel.is_deleted == False]
        store_id = auth.user.dept_id if auth.user and not VipService._is_brand_admin(auth) else None
        if store_id:
            conditions.append(
                or_(
                    CrmPersonModel.id.in_(
                        select(CrmCustomerProfileModel.person_id).where(
                            CrmCustomerProfileModel.store_id == store_id,
                            CrmCustomerProfileModel.is_deleted == False,
                        )
                    ),
                    CrmPersonModel.id.in_(
                        select(CrmLeadProfileModel.person_id).where(
                            CrmLeadProfileModel.store_id == store_id,
                            CrmLeadProfileModel.is_deleted == False,
                        )
                    ),
                )
            )
        if VipService._is_store_mgr(auth) and not VipService._is_brand_admin(auth):
            pass
        elif VipService._is_matchmaker(auth) and not (VipService._is_brand_admin(auth) or VipService._is_store_mgr(auth)):
            pass
        if keyword:
            like = f"%{keyword.strip()}%"
            conditions.append(or_(CrmPersonModel.name.like(like), CrmPersonModel.primary_mobile.like(like), CrmPersonModel.display_no.like(like)))
        result = await auth.db.execute(select(CrmPersonModel).where(*conditions).order_by(CrmPersonModel.id.desc()).limit(limit))
        people = result.scalars().all()
        store_map = await cls._person_store_map(auth, [person.id for person in people])
        return [
            {
                "id": person.id,
                "display_no": person.display_no,
                "name": person.name,
                "gender": person.gender,
                "mobile": VipService._mask_mobile(person.primary_mobile),
                "store_id": store_map.get(person.id),
                "age": VipService._age(person.birth_date),
            }
            for person in people
        ]

    @classmethod
    async def add_existing_service(cls, auth: AuthSchema, data: CandidateAddExistingSchema) -> dict:
        matchmaker_id = await cls._resolve_matchmaker_id(auth, data.matchmaker_id)
        person = await auth.db.get(CrmPersonModel, data.person_id)
        if not person or person.is_deleted:
            raise CustomException(msg="人员不存在")
        matchmaker = await auth.db.get(UserModel, matchmaker_id)
        if not cls._review_allowed(auth, "store", matchmaker.dept_id if matchmaker else None):
            raise CustomException(msg="请通过候选发现提交加入申请，审核通过后自动入库")
        if not VipService._is_brand_admin(auth) and not await cls._person_in_store(auth, person.id, matchmaker.dept_id if matchmaker else None):
            raise CustomException(msg="只能加入本门店人员")
        candidate = await cls._ensure_candidate_profile(auth, person.id)
        exists = await auth.db.execute(select(BackupPoolItemModel).where(BackupPoolItemModel.matchmaker_id == matchmaker_id, BackupPoolItemModel.person_id == person.id, BackupPoolItemModel.is_deleted == False))
        if exists.scalars().first():
            raise CustomException(msg="该人员已在你的备选库中")
        item = BackupPoolItemModel(
            brand_id=person.brand_id,
            candidate_id=candidate.id,
            person_id=person.id,
            store_id=matchmaker.dept_id if matchmaker else None,
            matchmaker_id=matchmaker_id,
            source_type="store_search",
            private_tags=data.private_tags,
            private_remark=data.private_remark,
            approved_by=auth.user.id if auth.user else None,
            approved_at=datetime.now(),
            contact_unmasked_after_approval=True,
        )
        VipService._stamp_create(auth, item)
        auth.db.add(item)
        await auth.db.flush()
        if data.partner_preference is not None:
            await PartnerPreferenceService.save(
                auth.db,
                person.id,
                PartnerPreferenceSaveSchema(**data.partner_preference.model_dump(), source_type="matchmaker", source_id=str(item.id)),
                auth=auth,
            )
        return await cls._candidate_out(auth, item)

    @classmethod
    async def create_manual_service(cls, auth: AuthSchema, data: CandidateCreateSchema) -> dict:
        matchmaker_id = await cls._resolve_matchmaker_id(auth, data.matchmaker_id)
        matchmaker = await auth.db.get(UserModel, matchmaker_id)
        person_fields = {
            "name": data.name,
            "gender": data.gender,
            "primary_mobile": data.primary_mobile,
            "wechat": data.wechat,
            "birth_date": data.birth_date,
            "height_cm": data.height_cm,
            "weight_kg": data.weight_kg,
            "ethnicity": data.ethnicity,
            "occupation": data.occupation,
            "occupation_code": data.occupation_code,
            "annual_income": data.annual_income,
            "marital_status": data.marital_status,
            "education": data.education,
            "graduated_school": data.graduated_school,
            "major": data.major,
            "unit_type": data.unit_type,
            "job_title": data.job_title,
            "work_company": data.work_company,
            "hometown": data.hometown,
            "residence": data.residence,
            "house_status": data.house_status,
            "car_status": data.car_status,
            "accept_long_distance_self": data.accept_long_distance_self,
            "accept_flash_marriage": data.accept_flash_marriage,
            "willing_relocate": data.willing_relocate,
            "marriage_plan": data.marriage_plan,
            "family_background": data.family_background,
            "profile_remark": data.profile_remark,
            "photo_urls": data.photo_urls,
            "profile_intro": data.profile_intro,
            "id_card_no": data.id_card_no,
        }
        result = await auth.db.execute(select(CrmPersonModel).where(CrmPersonModel.primary_mobile == data.primary_mobile, CrmPersonModel.is_deleted == False))
        person = result.scalars().first()
        if person is None:
            person = CrmPersonModel(
                brand_id=1,
                **person_fields,
            )
            VipService._stamp_create(auth, person)
            auth.db.add(person)
            await auth.db.flush()
        elif not VipService._is_brand_admin(auth) and not await cls._person_in_store(auth, person.id, matchmaker.dept_id if matchmaker else None):
            raise CustomException(msg="该手机号已存在于其他门店，不能加入本门店备选库")
        else:
            for field, value in person_fields.items():
                if field == "primary_mobile":
                    continue
                if value is None or value == []:
                    continue
                setattr(person, field, value)
            VipService._stamp_update(auth, person)
        candidate = await cls._ensure_candidate_profile(auth, person.id)
        exists = await auth.db.execute(select(BackupPoolItemModel).where(BackupPoolItemModel.matchmaker_id == matchmaker_id, BackupPoolItemModel.person_id == person.id, BackupPoolItemModel.is_deleted == False))
        if exists.scalars().first():
            raise CustomException(msg="该人员已在你的备选库中")
        item = BackupPoolItemModel(
            brand_id=person.brand_id,
            candidate_id=candidate.id,
            person_id=person.id,
            store_id=matchmaker.dept_id if matchmaker else None,
            matchmaker_id=matchmaker_id,
            source_type="manual_create",
            private_tags=data.private_tags,
            private_remark=data.private_remark,
            approved_by=auth.user.id if auth.user else None,
            approved_at=datetime.now(),
            contact_unmasked_after_approval=True,
        )
        VipService._stamp_create(auth, item)
        auth.db.add(item)
        await auth.db.flush()
        if data.partner_preference is not None:
            await PartnerPreferenceService.save(
                auth.db,
                person.id,
                PartnerPreferenceSaveSchema(**data.partner_preference.model_dump(), source_type="matchmaker", source_id=str(item.id)),
                auth=auth,
            )
        if data.certification_materials:
            archive_items = await cls.certification_archive_items_service(auth)
            item_name_map = {row["item_code"]: row["item_name"] for row in archive_items}
            for material_data in data.certification_materials:
                material = CrmCustomerCertificationMaterialModel(
                    brand_id=person.brand_id,
                    customer_id=None,
                    person_id=person.id,
                    item_code=material_data.item_code,
                    item_name=material_data.item_name or item_name_map.get(material_data.item_code) or material_data.item_code,
                    material_type=material_data.material_type,
                    file_name=material_data.file_name,
                    file_path=material_data.file_path,
                    file_url=material_data.file_url,
                    payload=material_data.payload,
                    collected_by=auth.user.id if auth.user else None,
                )
                VipService._stamp_create(auth, material)
                auth.db.add(material)
            await auth.db.flush()
        return await cls._candidate_out(auth, item)

    @classmethod
    async def certification_archive_items_service(cls, auth: AuthSchema) -> list[dict[str, Any]]:
        rows = (
            await auth.db.execute(
                select(CertificationItemModel)
                .where(
                    CertificationItemModel.is_deleted == False,
                    CertificationItemModel.status == "0",
                    CertificationItemModel.material_required == True,
                    CertificationItemModel.item_code != "real_photo",
                )
                .order_by(CertificationItemModel.sort.asc(), CertificationItemModel.id.asc())
            )
        ).scalars().all()
        result = [{"item_code": "id_card_photo", "item_name": "身份证照片", "sort": 0, "material_required": True, "material_desc": None}]
        result.extend([
            {
                "item_code": row.item_code,
                "item_name": row.item_name,
                "sort": row.sort,
                "material_required": row.material_required,
                "material_desc": row.material_desc,
            }
            for row in rows
        ])
        return result
