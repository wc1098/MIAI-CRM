from datetime import date, datetime, time, timedelta
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
from app.plugin.module_certification.model import (
    CertificationApplicationModel,
    CertificationItemModel,
    CertificationRecordModel,
    CertificationSensitiveAccessLogModel,
)
from app.plugin.module_certification.service import CertificationService
from app.plugin.module_crm.channel.model import CrmChannelModel
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
from app.plugin.module_crm.person.service import PersonCenterService
from app.plugin.module_crm.preference.model import PersonPartnerPreferenceModel
from app.plugin.module_crm.preference.schema import PartnerPreferenceSaveSchema
from app.plugin.module_crm.preference.service import PartnerPreferenceService
from app.plugin.module_match.service import MatchProfileService
from app.plugin.module_mp.auth.model import SourceEventModel

from .model import (
    BackupPoolItemModel,
    CandidateJoinRequestModel,
    CandidateProfileModel,
    DeepInterviewModel,
    EntitlementUsageLogModel,
    ServiceCaseModel,
    ServiceCourseRecordModel,
    ServiceEntitlementModel,
    ServiceMeetingFeedbackModel,
    ServiceMeetingModel,
    ServicePlanItemModel,
    ServicePlanModel,
    ServiceRecommendationModel,
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
    CourseRecordCreateSchema,
    CourseRecordRevokeSchema,
    DeepInterviewCreateSchema,
    MatchCandidateSchema,
    MatchmakerOptionSchema,
    MeetingActionSchema,
    MeetingCreateSchema,
    MeetingFeedbackSaveSchema,
    RecommendationCreateSchema,
    RecommendationUpdateSchema,
    ReopenSchema,
    ServiceCustomerProcessCreateSchema,
    ServicePlanItemActionSchema,
    ServicePlanItemUpdateSchema,
    ServicePlanUpdateSchema,
    UsageCreateSchema,
    UsageVoidSchema,
    VipAssignSchema,
    VipQueryParam,
)


class VipService:
    """服务工作台服务层"""

    DIVORCED_STATUS_CODES = {"divorced", "离异", "离婚", "divorce"}

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

    @staticmethod
    def _address_parts(value: str | None) -> list[str]:
        return [part.strip() for part in (value or "").replace("，", "/").replace(",", "/").split("/") if part.strip()]

    @classmethod
    def _same_region_condition(cls, column: Any, source_value: str | None) -> Any | None:
        parts = cls._address_parts(source_value)
        if not parts:
            return None
        if len(parts) >= 2:
            province, city = parts[0], parts[1]
            return or_(
                column == f"{province}/{city}",
                column.like(f"{province}/{city}/%"),
                column.like(f"%{city}%"),
            )
        province = parts[0]
        return or_(column == province, column.like(f"{province}/%"))

    @classmethod
    def _vip_preference_person_filters(cls, vip_person: CrmPersonModel | None, vip_pref: PersonPartnerPreferenceModel | None) -> list[Any]:
        filters: list[Any] = []
        if vip_pref and vip_pref.accept_long_distance is False:
            same_region = cls._same_region_condition(CrmPersonModel.residence, vip_person.residence if vip_person else None)
            if same_region is not None:
                filters.append(same_region)
        if vip_pref and vip_pref.accept_divorced is False:
            filters.append(or_(CrmPersonModel.marital_status.is_(None), CrmPersonModel.marital_status.notin_(cls.DIVORCED_STATUS_CODES)))
        return filters

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
        record_map = await CustomerService._certification_record_map(auth, CustomerService._certification_record_ids(rows))
        items = []
        for row in rows:
            material_out = CustomerService._certification_material_out(row, record_map)
            items.append(
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
                    "certification_record_id": material_out.get("certification_record_id"),
                    "certification_record_status": material_out.get("certification_record_status"),
                    "certification_reject_reason": material_out.get("certification_reject_reason"),
                    "certification_reviewed_at": material_out.get("certification_reviewed_at"),
                }
            )
        return items

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
        ocr_result = None
        certification_sync = None
        if data.item_code == "id_card_photo" and data.file_url:
            ocr_result = await CertificationService.recognize_id_card_for_url(
                auth.db,
                file_url=data.file_url,
                business_type="vip_certification_material",
                business_id=material.id,
                operator_id=auth.user.id if auth.user else None,
                person_id=case.person_id,
            )
        if data.file_url:
            certification_sync = await CertificationService.sync_staff_material_to_record(
                auth.db,
                person_id=case.person_id,
                archive_material_id=material.id,
                archive_item_code=data.item_code,
                archive_item_name=material.item_name,
                material_type=material.material_type,
                file_name=material.file_name,
                file_path=material.file_path,
                file_url=material.file_url,
                operator_id=auth.user.id if auth.user else None,
                source_business_type="vip_certification_material",
                source_business_id=case.id,
                ocr_result=ocr_result,
            )
            material.payload = {**(material.payload or {}), "ocr_result": ocr_result, "certification_sync": certification_sync}
            await CustomerService._replace_rejected_archive_materials(auth, material, certification_sync)
            await auth.db.flush()
        await auth.db.refresh(material)
        record_map = {}
        record_id = certification_sync.get("record_id") if isinstance(certification_sync, dict) else None
        if record_id:
            record = await auth.db.get(CertificationRecordModel, int(record_id))
            if record:
                record_map[record.id] = record
        result = {
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
            **{
                key: value
                for key, value in CustomerService._certification_material_out(material, record_map).items()
                if key.startswith("certification_")
            },
        }
        if ocr_result:
            result["ocr_result"] = ocr_result
        if certification_sync:
            result["certification_sync"] = certification_sync
        return result

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
        await CertificationService.revoke_staff_material_review(auth.db, material.id)
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
        await cls._ensure_plan(auth, case)
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
        plan_result = await auth.db.execute(select(ServicePlanModel).where(ServicePlanModel.service_case_id == case.id, ServicePlanModel.is_deleted == False))
        plan = plan_result.scalars().first()
        if plan:
            plan.matchmaker_id = data.service_owner_user_id
            cls._stamp_update(auth, plan)
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
    async def _ensure_plan_write_access(cls, auth: AuthSchema, case: ServiceCaseModel) -> None:
        await cls._ensure_case_access(auth, case)
        if cls._is_brand_admin(auth):
            return
        if cls._is_store_mgr(auth) and auth.user and case.store_id == auth.user.dept_id:
            return
        if cls._is_matchmaker(auth) and auth.user and case.owner_matchmaker_id == auth.user.id:
            return
        raise CustomException(msg="无权维护该服务计划")

    @classmethod
    def _item_type_for_entitlement(cls, entitlement_type: str) -> str:
        return {"recommendation": "recommendation", "meeting": "meeting", "course": "course"}.get(entitlement_type, entitlement_type)

    @classmethod
    def _item_title(cls, item_type: str, index: int) -> str:
        labels = {"recommendation": "推荐服务", "meeting": "相亲约见", "course": "课程服务"}
        return f"第 {index} 次{labels.get(item_type, '服务节点')}"

    @classmethod
    def _contract_start_at(cls, contract: CrmContractModel) -> datetime:
        return datetime.combine(contract.start_date, time.min)

    @classmethod
    def _contract_end_at(cls, contract: CrmContractModel) -> datetime:
        return datetime.combine(contract.end_date, time.max)

    @classmethod
    def _item_start_at(cls, item: ServicePlanItemModel) -> datetime | None:
        return item.planned_start_at or item.planned_at

    @classmethod
    def _item_end_at(cls, item: ServicePlanItemModel) -> datetime | None:
        return item.planned_end_at or item.due_at

    @classmethod
    def _item_executed(cls, item: ServicePlanItemModel) -> bool:
        return bool(
            item.related_recommendation_id
            or item.related_meeting_id
            or item.related_usage_id
            or item.item_status in {"recommended", "pending_meeting", "pending_feedback", "completed", "cancelled", "skipped"}
        )

    @classmethod
    async def _entitlement_contract_map(cls, db: AsyncSession, entitlement_ids: set[int]) -> tuple[dict[int, ServiceEntitlementModel], dict[int, CrmContractModel]]:
        if not entitlement_ids:
            return {}, {}
        entitlement_result = await db.execute(
            select(ServiceEntitlementModel).where(ServiceEntitlementModel.id.in_(entitlement_ids), ServiceEntitlementModel.is_deleted == False)
        )
        entitlements = {row.id: row for row in entitlement_result.scalars().all()}
        contract_ids = {row.contract_id for row in entitlements.values()}
        contracts: dict[int, CrmContractModel] = {}
        if contract_ids:
            contract_result = await db.execute(select(CrmContractModel).where(CrmContractModel.id.in_(contract_ids), CrmContractModel.is_deleted == False))
            contracts = {row.id: row for row in contract_result.scalars().all()}
        return entitlements, contracts

    @classmethod
    def _validate_item_range(cls, item: ServicePlanItemModel, entitlement: ServiceEntitlementModel | None, contract: CrmContractModel | None) -> None:
        start_at = cls._item_start_at(item)
        end_at = cls._item_end_at(item)
        if item.item_status in {"cancelled", "skipped"}:
            return
        if not start_at or not end_at:
            raise CustomException(msg=f"{item.title}缺少计划区间")
        if start_at > end_at:
            raise CustomException(msg=f"{item.title}计划区间开始时间不能晚于结束时间")
        if not entitlement or not contract:
            raise CustomException(msg=f"{item.title}缺少来源合同，不能发布")
        if start_at < cls._contract_start_at(contract) or end_at > cls._contract_end_at(contract):
            raise CustomException(msg=f"{item.title}计划区间不能超出来源合同服务期")

    @classmethod
    def _apply_default_schedule(cls, items: list[ServicePlanItemModel], contract: CrmContractModel) -> None:
        if not items:
            return
        start_date = contract.start_date
        total_days = max((contract.end_date - contract.start_date).days + 1, 1)
        total = len(items)
        for index, item in enumerate(sorted(items, key=lambda row: (row.sequence_no, row.id or 0))):
            start_offset = int(index * total_days / total)
            end_offset = int((index + 1) * total_days / total) - 1
            if end_offset < start_offset:
                end_offset = start_offset
            planned_start = datetime.combine(start_date + timedelta(days=start_offset), time.min)
            planned_end = datetime.combine(start_date + timedelta(days=min(end_offset, total_days - 1)), time.max)
            item.planned_start_at = item.planned_start_at or item.planned_at or planned_start
            item.planned_end_at = item.planned_end_at or item.due_at or planned_end
            item.planned_at = item.planned_at or item.planned_start_at
            item.due_at = item.due_at or item.planned_end_at

    @classmethod
    async def _ensure_plan_published(cls, auth: AuthSchema, case: ServiceCaseModel) -> ServicePlanModel:
        plan = await cls._ensure_plan(auth, case)
        if plan.plan_status != "published":
            raise CustomException(msg="请先发布服务计划")
        return plan

    @classmethod
    async def _ensure_plan(cls, auth: AuthSchema, case: ServiceCaseModel) -> ServicePlanModel:
        result = await auth.db.execute(
            select(ServicePlanModel).where(ServicePlanModel.service_case_id == case.id, ServicePlanModel.is_deleted == False)
        )
        plan = result.scalars().first()
        if not plan:
            plan = ServicePlanModel(
                brand_id=case.brand_id,
                service_case_id=case.id,
                vip_id=case.vip_id,
                contract_id=case.contract_id,
                person_id=case.person_id,
                matchmaker_id=case.owner_matchmaker_id,
                plan_status="draft",
            )
            cls._stamp_create(auth, plan)
            auth.db.add(plan)
            await auth.db.flush()
        elif plan.matchmaker_id != case.owner_matchmaker_id:
            plan.matchmaker_id = case.owner_matchmaker_id
            cls._stamp_update(auth, plan)

        await cls._build_missing_plan_items(auth, case, plan)
        return plan

    @classmethod
    async def _build_missing_plan_items(cls, auth: AuthSchema, case: ServiceCaseModel, plan: ServicePlanModel) -> list[ServicePlanItemModel]:
        result = await auth.db.execute(
            select(ServiceEntitlementModel)
            .where(ServiceEntitlementModel.service_case_id == case.id, ServiceEntitlementModel.is_deleted == False)
            .order_by(ServiceEntitlementModel.entitlement_type.asc(), ServiceEntitlementModel.id.asc())
        )
        entitlements = result.scalars().all()
        existing_result = await auth.db.execute(
            select(ServicePlanItemModel).where(ServicePlanItemModel.plan_id == plan.id, ServicePlanItemModel.is_deleted == False)
        )
        existing_items = list(existing_result.scalars().all())
        sequence_no = max((item.sequence_no for item in existing_items), default=0) + 1
        type_counts: dict[str, int] = {}
        for item in existing_items:
            type_counts[item.item_type] = max(type_counts.get(item.item_type, 0), sum(1 for row in existing_items if row.item_type == item.item_type and row.sequence_no <= item.sequence_no))
        existing_by_entitlement: dict[int, int] = {}
        for item in existing_items:
            if item.entitlement_id:
                existing_by_entitlement[item.entitlement_id] = existing_by_entitlement.get(item.entitlement_id, 0) + 1
        new_items: list[ServicePlanItemModel] = []
        for entitlement in entitlements:
            item_type = cls._item_type_for_entitlement(entitlement.entitlement_type)
            quota = max(entitlement.total_quota or 0, 0)
            missing_quota = max(quota - existing_by_entitlement.get(entitlement.id, 0), 0)
            for _ in range(missing_quota):
                type_counts[item_type] = type_counts.get(item_type, 0) + 1
                item = ServicePlanItemModel(
                    brand_id=case.brand_id,
                    plan_id=plan.id,
                    service_case_id=case.id,
                    entitlement_id=entitlement.id,
                    entitlement_type=entitlement.entitlement_type,
                    item_type=item_type,
                    item_status="pending",
                    sequence_no=sequence_no,
                    title=cls._item_title(item_type, type_counts[item_type]),
                )
                cls._stamp_create(auth, item)
                auth.db.add(item)
                new_items.append(item)
                sequence_no += 1
        await auth.db.flush()
        if new_items:
            entitlement_map, contract_map = await cls._entitlement_contract_map(auth.db, {item.entitlement_id for item in new_items if item.entitlement_id})
            items_by_contract: dict[int, list[ServicePlanItemModel]] = {}
            for item in new_items:
                entitlement = entitlement_map.get(item.entitlement_id or 0)
                if entitlement:
                    items_by_contract.setdefault(entitlement.contract_id, []).append(item)
            for contract_id, rows in items_by_contract.items():
                contract = contract_map.get(contract_id)
                if contract:
                    cls._apply_default_schedule(rows, contract)
                    for row in rows:
                        cls._stamp_update(auth, row)
            await auth.db.flush()
        return new_items

    @classmethod
    async def _build_plan_items(cls, auth: AuthSchema, case: ServiceCaseModel, plan: ServicePlanModel) -> None:
        await cls._build_missing_plan_items(auth, case, plan)

    @classmethod
    async def _plan_items_out(cls, auth: AuthSchema, plan_id: int) -> list[dict]:
        result = await auth.db.execute(
            select(ServicePlanItemModel)
            .where(ServicePlanItemModel.plan_id == plan_id, ServicePlanItemModel.is_deleted == False)
            .order_by(ServicePlanItemModel.sequence_no.asc(), ServicePlanItemModel.id.asc())
        )
        rows = result.scalars().all()
        person_ids = {row.candidate_person_id for row in rows if row.candidate_person_id}
        person_names: dict[int, str] = {}
        if person_ids:
            person_result = await auth.db.execute(select(CrmPersonModel.id, CrmPersonModel.name).where(CrmPersonModel.id.in_(person_ids)))
            person_names = {row[0]: row[1] for row in person_result.all()}
        recommendation_summary: dict[int, dict[str, Any]] = {}
        item_ids = [row.id for row in rows]
        if item_ids:
            recommendation_result = await auth.db.execute(
                select(ServiceRecommendationModel.plan_item_id, ServiceRecommendationModel.candidate_person_id)
                .where(
                    ServiceRecommendationModel.plan_item_id.in_(item_ids),
                    ServiceRecommendationModel.recommendation_status != "abandoned",
                    ServiceRecommendationModel.is_deleted == False,
                )
                .order_by(ServiceRecommendationModel.id.asc())
            )
            recommendation_person_ids: set[int] = set()
            recommendation_rows = recommendation_result.all()
            for row in recommendation_rows:
                recommendation_person_ids.add(row[1])
            recommendation_person_names: dict[int, str] = {}
            if recommendation_person_ids:
                recommendation_person_result = await auth.db.execute(select(CrmPersonModel.id, CrmPersonModel.name).where(CrmPersonModel.id.in_(recommendation_person_ids)))
                recommendation_person_names = {row[0]: row[1] for row in recommendation_person_result.all()}
            for plan_item_id, candidate_person_id in recommendation_rows:
                summary = recommendation_summary.setdefault(plan_item_id, {"count": 0, "names": []})
                summary["count"] += 1
                if recommendation_person_names.get(candidate_person_id):
                    summary["names"].append(recommendation_person_names[candidate_person_id])
        entitlement_map, contract_map = await cls._entitlement_contract_map(auth.db, {row.entitlement_id for row in rows if row.entitlement_id})
        return [
            {
                "id": row.id,
                "plan_id": row.plan_id,
                "service_case_id": row.service_case_id,
                "entitlement_id": row.entitlement_id,
                "entitlement_type": row.entitlement_type,
                "item_type": row.item_type,
                "item_status": row.item_status,
                "sequence_no": row.sequence_no,
                "title": row.title,
                "planned_at": row.planned_at,
                "due_at": row.due_at,
                "planned_start_at": row.planned_start_at or row.planned_at,
                "planned_end_at": row.planned_end_at or row.due_at,
                "source_contract_id": entitlement_map[row.entitlement_id].contract_id if row.entitlement_id in entitlement_map else None,
                "source_contract_no": contract_map[entitlement_map[row.entitlement_id].contract_id].contract_no if row.entitlement_id in entitlement_map and entitlement_map[row.entitlement_id].contract_id in contract_map else None,
                "source_contract_item_id": entitlement_map[row.entitlement_id].source_contract_item_id if row.entitlement_id in entitlement_map else None,
                "candidate_person_id": row.candidate_person_id,
                "candidate_name": f"已推荐{recommendation_summary.get(row.id, {}).get('count', 0)}人" if row.item_type == "recommendation" and recommendation_summary.get(row.id, {}).get("count", 0) else person_names.get(row.candidate_person_id),
                "recommendation_count": recommendation_summary.get(row.id, {}).get("count", 0),
                "related_recommendation_id": row.related_recommendation_id,
                "related_meeting_id": row.related_meeting_id,
                "related_usage_id": row.related_usage_id,
                "remark": row.remark,
            }
            for row in rows
        ]

    @classmethod
    async def _plan_out(cls, auth: AuthSchema, plan: ServicePlanModel) -> dict:
        names = await cls._user_names(auth.db, {plan.matchmaker_id})
        return {
            "id": plan.id,
            "brand_id": plan.brand_id,
            "service_case_id": plan.service_case_id,
            "vip_id": plan.vip_id,
            "contract_id": plan.contract_id,
            "person_id": plan.person_id,
            "matchmaker_id": plan.matchmaker_id,
            "matchmaker_name": names.get(plan.matchmaker_id),
            "plan_status": plan.plan_status,
            "service_start_at": plan.service_start_at,
            "service_end_at": plan.service_end_at,
            "plan_summary": plan.plan_summary,
            "remark": plan.remark,
            "items": await cls._plan_items_out(auth, plan.id),
        }

    @classmethod
    async def plan_service(cls, auth: AuthSchema, case_id: int) -> dict:
        case = await cls._get_case(auth, case_id)
        plan = await cls._ensure_plan(auth, case)
        await auth.db.flush()
        return await cls._plan_out(auth, plan)

    @classmethod
    async def update_plan_service(cls, auth: AuthSchema, case_id: int, data: ServicePlanUpdateSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_plan_write_access(auth, case)
        plan = await cls._ensure_plan(auth, case)
        for field in ["service_start_at", "service_end_at", "plan_summary", "remark"]:
            setattr(plan, field, getattr(data, field))
        cls._stamp_update(auth, plan)
        await auth.db.flush()
        return await cls._plan_out(auth, plan)

    @classmethod
    async def publish_plan_service(cls, auth: AuthSchema, case_id: int) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_plan_write_access(auth, case)
        if case.case_status not in {"serving", "reopened"}:
            raise CustomException(msg="只有服务中的工单可以发布服务计划")
        plan = await cls._ensure_plan(auth, case)
        result = await auth.db.execute(
            select(ServicePlanItemModel).where(ServicePlanItemModel.plan_id == plan.id, ServicePlanItemModel.is_deleted == False)
        )
        rows = list(result.scalars().all())
        entitlement_map, contract_map = await cls._entitlement_contract_map(auth.db, {row.entitlement_id for row in rows if row.entitlement_id})
        for row in rows:
            entitlement = entitlement_map.get(row.entitlement_id or 0)
            contract = contract_map.get(entitlement.contract_id) if entitlement else None
            cls._validate_item_range(row, entitlement, contract)
        plan.plan_status = "published"
        cls._stamp_update(auth, plan)
        await auth.db.flush()
        return await cls._plan_out(auth, plan)

    @classmethod
    async def auto_schedule_plan_items_service(cls, auth: AuthSchema, case_id: int) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_plan_write_access(auth, case)
        plan = await cls._ensure_plan(auth, case)
        result = await auth.db.execute(
            select(ServicePlanItemModel).where(ServicePlanItemModel.plan_id == plan.id, ServicePlanItemModel.is_deleted == False)
        )
        rows = [
            row
            for row in result.scalars().all()
            if row.item_status not in {"cancelled", "skipped"}
            and not cls._item_executed(row)
            and not cls._item_start_at(row)
            and not cls._item_end_at(row)
        ]
        entitlement_map, contract_map = await cls._entitlement_contract_map(auth.db, {row.entitlement_id for row in rows if row.entitlement_id})
        rows_by_contract: dict[int, list[ServicePlanItemModel]] = {}
        for row in rows:
            entitlement = entitlement_map.get(row.entitlement_id or 0)
            if entitlement:
                rows_by_contract.setdefault(entitlement.contract_id, []).append(row)
        for contract_id, items in rows_by_contract.items():
            contract = contract_map.get(contract_id)
            if not contract:
                continue
            cls._apply_default_schedule(items, contract)
            for item in items:
                cls._stamp_update(auth, item)
        await auth.db.flush()
        return await cls._plan_out(auth, plan)

    @classmethod
    async def rebuild_plan_service(cls, auth: AuthSchema, case_id: int) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_plan_write_access(auth, case)
        if not cls._is_brand_admin(auth):
            raise CustomException(msg="只有品牌管理员可以按权益重建服务计划")
        plan = await cls._ensure_plan(auth, case)
        result = await auth.db.execute(
            select(ServicePlanItemModel).where(ServicePlanItemModel.plan_id == plan.id, ServicePlanItemModel.is_deleted == False)
        )
        rows = result.scalars().all()
        if any(row.related_recommendation_id or row.related_meeting_id or row.related_usage_id or row.item_status in {"completed", "recommended", "pending_meeting", "pending_feedback"} for row in rows):
            raise CustomException(msg="服务计划已有执行记录，不能重建")
        for row in rows:
            row.is_deleted = True
            cls._stamp_update(auth, row)
        await auth.db.flush()
        await cls._build_plan_items(auth, case, plan)
        plan.plan_status = "draft"
        cls._stamp_update(auth, plan)
        await auth.db.flush()
        return await cls._plan_out(auth, plan)

    @classmethod
    async def plan_items_service(cls, auth: AuthSchema, case_id: int) -> list[dict]:
        case = await cls._get_case(auth, case_id)
        plan = await cls._ensure_plan(auth, case)
        return await cls._plan_items_out(auth, plan.id)

    @classmethod
    async def update_plan_item_service(cls, auth: AuthSchema, case_id: int, item_id: int, data: ServicePlanItemUpdateSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_plan_write_access(auth, case)
        item = await auth.db.get(ServicePlanItemModel, item_id)
        if not item or item.is_deleted or item.service_case_id != case.id:
            raise CustomException(msg="服务计划节点不存在")
        plan = await auth.db.get(ServicePlanModel, item.plan_id)
        update_data = data.model_dump(exclude_unset=True)
        if plan and plan.plan_status == "published":
            if any(field in update_data for field in ["title", "sequence_no"]):
                raise CustomException(msg="服务计划发布后不能修改节点标题和顺序")
            if cls._item_executed(item) and any(field in update_data for field in ["planned_at", "due_at", "planned_start_at", "planned_end_at"]):
                raise CustomException(msg="已执行节点不能修改计划区间")
        for field in ["planned_at", "due_at", "planned_start_at", "planned_end_at", "title", "remark", "sequence_no"]:
            value = getattr(data, field)
            if value is not None:
                setattr(item, field, value)
        if data.planned_start_at is None and data.planned_at is not None:
            item.planned_start_at = data.planned_at
        if data.planned_end_at is None and data.due_at is not None:
            item.planned_end_at = data.due_at
        entitlement_map, contract_map = await cls._entitlement_contract_map(auth.db, {item.entitlement_id} if item.entitlement_id else set())
        entitlement = entitlement_map.get(item.entitlement_id or 0)
        contract = contract_map.get(entitlement.contract_id) if entitlement else None
        if cls._item_start_at(item) or cls._item_end_at(item):
            cls._validate_item_range(item, entitlement, contract)
        cls._stamp_update(auth, item)
        await auth.db.flush()
        return next(row for row in await cls._plan_items_out(auth, item.plan_id) if row["id"] == item.id)

    @classmethod
    async def cancel_plan_item_service(cls, auth: AuthSchema, case_id: int, item_id: int, data: ServicePlanItemActionSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_plan_write_access(auth, case)
        item = await auth.db.get(ServicePlanItemModel, item_id)
        if not item or item.is_deleted or item.service_case_id != case.id:
            raise CustomException(msg="服务计划节点不存在")
        if item.related_usage_id:
            raise CustomException(msg="已核销节点不能取消")
        item.item_status = "cancelled"
        item.remark = data.reason or item.remark
        cls._stamp_update(auth, item)
        await auth.db.flush()
        return next(row for row in await cls._plan_items_out(auth, item.plan_id) if row["id"] == item.id)

    @classmethod
    async def skip_plan_item_service(cls, auth: AuthSchema, case_id: int, item_id: int, data: ServicePlanItemActionSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_plan_write_access(auth, case)
        item = await auth.db.get(ServicePlanItemModel, item_id)
        if not item or item.is_deleted or item.service_case_id != case.id:
            raise CustomException(msg="服务计划节点不存在")
        if item.related_usage_id:
            raise CustomException(msg="已核销节点不能跳过")
        item.item_status = "skipped"
        item.remark = data.reason or item.remark
        cls._stamp_update(auth, item)
        await auth.db.flush()
        return next(row for row in await cls._plan_items_out(auth, item.plan_id) if row["id"] == item.id)

    @classmethod
    async def restore_plan_item_service(cls, auth: AuthSchema, case_id: int, item_id: int, data: ServicePlanItemActionSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_plan_write_access(auth, case)
        item = await auth.db.get(ServicePlanItemModel, item_id)
        if not item or item.is_deleted or item.service_case_id != case.id:
            raise CustomException(msg="服务计划节点不存在")
        if item.item_status != "skipped":
            raise CustomException(msg="只有已放弃的节点可以撤销")
        if item.related_recommendation_id or item.related_meeting_id or item.related_usage_id:
            raise CustomException(msg="已有关联业务记录的节点不能撤销")
        item.item_status = "pending"
        item.remark = data.reason or item.remark
        cls._stamp_update(auth, item)
        await auth.db.flush()
        return next(row for row in await cls._plan_items_out(auth, item.plan_id) if row["id"] == item.id)

    @classmethod
    async def match_candidates_service(cls, auth: AuthSchema, case_id: int, item_id: int, data: MatchCandidateSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_plan_write_access(auth, case)
        await cls._ensure_plan_published(auth, case)
        item = await auth.db.get(ServicePlanItemModel, item_id)
        if not item or item.is_deleted or item.service_case_id != case.id or item.item_type != "recommendation":
            raise CustomException(msg="请选择推荐服务项")
        active_recommendation_count = await auth.db.scalar(
            select(func.count(ServiceRecommendationModel.id)).where(
                ServiceRecommendationModel.plan_item_id == item.id,
                ServiceRecommendationModel.service_case_id == case.id,
                ServiceRecommendationModel.recommendation_status != "abandoned",
                ServiceRecommendationModel.is_deleted == False,
            )
        )
        if active_recommendation_count:
            raise CustomException(msg="该推荐服务项已有推荐记录，请先撤销后再重新匹配")
        if data.search_mode not in {"score", "filter"}:
            raise CustomException(msg="搜索模式不正确")
        if data.scope not in {"backup", "store", "brand"}:
            raise CustomException(msg="候选范围不正确")
        vip_person = await auth.db.get(CrmPersonModel, case.person_id)
        vip_pref = (
            await auth.db.execute(
                select(PersonPartnerPreferenceModel).where(
                    PersonPartnerPreferenceModel.person_id == case.person_id,
                    PersonPartnerPreferenceModel.is_deleted == False,
                )
            )
        ).scalars().first()
        conditions: list[Any] = [CrmPersonModel.is_deleted == False, CrmPersonModel.id != case.person_id]
        opposite_gender = {"0": "1", "1": "0"}.get(vip_person.gender if vip_person else None)
        if not opposite_gender:
            raise CustomException(msg="VIP客户性别缺失，无法匹配异性候选")
        conditions.append(CrmPersonModel.gender == opposite_gender)
        conditions.extend(cls._vip_preference_person_filters(vip_person, vip_pref))
        join_backup = False
        if data.scope == "backup":
            join_backup = True
            conditions.extend(
                [
                    BackupPoolItemModel.matchmaker_id == case.owner_matchmaker_id,
                    BackupPoolItemModel.is_deleted == False,
                    BackupPoolItemModel.person_id == CrmPersonModel.id,
                ]
            )
        elif data.scope == "store":
            conditions.append(
                or_(
                    CrmPersonModel.id.in_(
                        select(CrmCustomerProfileModel.person_id).where(
                            CrmCustomerProfileModel.store_id == case.store_id,
                            CrmCustomerProfileModel.is_deleted == False,
                        )
                    ),
                    CrmPersonModel.id.in_(
                        select(CrmLeadProfileModel.person_id).where(
                            CrmLeadProfileModel.store_id == case.store_id,
                            CrmLeadProfileModel.is_deleted == False,
                        )
                    ),
                )
            )
        else:
            conditions.append(CrmPersonModel.brand_id == case.brand_id)
        if data.keyword:
            like = f"%{data.keyword.strip()}%"
            conditions.append(or_(CrmPersonModel.name.like(like), CrmPersonModel.primary_mobile.like(like), CrmPersonModel.display_no.like(like), cast(CrmPersonModel.id, String).like(like)))
        exact_fields = [
            (CrmPersonModel.id, data.person_id),
            (CrmPersonModel.display_no, data.display_no),
            (CrmPersonModel.primary_mobile, data.mobile),
            (CrmPersonModel.name, data.name),
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
            conditions.append(CrmPersonModel.birth_date <= CandidateService._birth_date_for_age(data.age_min))
        if data.age_max is not None:
            conditions.append(CrmPersonModel.birth_date >= CandidateService._birth_date_for_age(data.age_max + 1))
        if data.height_min is not None:
            conditions.append(CrmPersonModel.height_cm >= data.height_min)
        if data.height_max is not None:
            conditions.append(CrmPersonModel.height_cm <= data.height_max)
        if data.weight_min is not None:
            conditions.append(CrmPersonModel.weight_kg >= data.weight_min)
        if data.weight_max is not None:
            conditions.append(CrmPersonModel.weight_kg <= data.weight_max)
        for column, value in [
            (CrmPersonModel.accept_long_distance_self, data.accept_long_distance_self),
            (CrmPersonModel.accept_flash_marriage, data.accept_flash_marriage),
            (CrmPersonModel.willing_relocate, data.willing_relocate),
        ]:
            if value is not None:
                conditions.append(column == value)
        if data.has_photo is True:
            conditions.append(cast(CrmPersonModel.photo_urls, String).notin_(["null", "[]"]))
        elif data.has_photo is False:
            conditions.append(or_(CrmPersonModel.photo_urls.is_(None), cast(CrmPersonModel.photo_urls, String).in_(["null", "[]"])))

        stmt = select(CrmPersonModel)
        if join_backup:
            stmt = stmt.select_from(CrmPersonModel, BackupPoolItemModel)
        if CandidateService._has_preference_filter(data):
            stmt = stmt.join(PersonPartnerPreferenceModel, PersonPartnerPreferenceModel.person_id == CrmPersonModel.id)
            conditions.extend(CandidateService._preference_filters(data))
        offset = (data.page_no - 1) * data.page_size
        result = await auth.db.execute(stmt.where(*conditions).order_by(CrmPersonModel.id.desc()))
        people = result.scalars().all()
        person_ids = [person.id for person in people]
        store_map = await CandidateService._person_store_map(auth, person_ids)
        dept_names = await CandidateService._dept_names(auth, {store_id for store_id in store_map.values() if store_id})
        backup_result = await auth.db.execute(
            select(BackupPoolItemModel).where(
                BackupPoolItemModel.matchmaker_id == case.owner_matchmaker_id,
                BackupPoolItemModel.person_id.in_(person_ids or [-1]),
                BackupPoolItemModel.is_deleted == False,
            )
        )
        backup_map = {row.person_id: row for row in backup_result.scalars().all()}
        vip_case_result = await auth.db.execute(
            select(ServiceCaseModel.person_id, ServiceCaseModel.owner_matchmaker_id).where(
                ServiceCaseModel.person_id.in_(person_ids or [-1]),
                ServiceCaseModel.case_status.in_(["serving", "reopened", "pending_close_review"]),
                ServiceCaseModel.is_deleted == False,
            )
        )
        vip_case_rows = vip_case_result.all()
        vip_person_ids = {row[0] for row in vip_case_rows}
        own_service_person_ids = {row[0] for row in vip_case_rows if row[1] == case.owner_matchmaker_id}
        score_rows = await MatchProfileService.score_people(auth.db, vip_person, people, scene="matchmaker_service", source_pref=vip_pref)
        score_map = {row["person_id"]: row for row in score_rows}
        ranked_items = []
        for person in people:
            score_info = score_map.get(person.id)
            if not score_info:
                continue
            backup = backup_map.get(person.id)
            contact_unmasked = bool((backup and backup.contact_unmasked_after_approval) or person.id in own_service_person_ids)
            if data.only_backup_unmasked and not contact_unmasked:
                continue
            ranked_items.append(
                {
                    "id": person.id,
                    "display_no": person.display_no,
                    "name": person.name,
                    "gender": person.gender,
                    "mobile": person.primary_mobile if contact_unmasked else cls._mask_mobile(person.primary_mobile),
                    "wechat": person.wechat if contact_unmasked else CandidateService._mask_wechat(person.wechat),
                    "age": cls._age(person.birth_date),
                    "height_cm": person.height_cm,
                    "weight_kg": person.weight_kg,
                    "residence": person.residence,
                    "hometown": person.hometown,
                    "education": person.education,
                    "annual_income": person.annual_income,
                    "marital_status": person.marital_status,
                    "store_id": store_map.get(person.id),
                    "store_name": dept_names.get(store_map.get(person.id) or 0),
                    "in_backup": bool(backup),
                    "contact_unmasked": contact_unmasked,
                    "is_vip": person.id in vip_person_ids,
                    "match_score": score_info.get("match_score"),
                    "matched_points": score_info.get("matched_points") or [],
                    "unmatched_points": score_info.get("risk_points") or [],
                    "rank_score": score_info.get("rank_score"),
                    "confidence_score": score_info.get("confidence_score"),
                    "structured_score": score_info.get("structured_score"),
                    "vector_score": score_info.get("vector_score"),
                    "vector_status": score_info.get("vector_status"),
                }
            )
        if data.search_mode == "score":
            ranked_items.sort(key=lambda item: (item.get("rank_score") or 0, item.get("match_score") or 0, item.get("id") or 0), reverse=True)
        else:
            ranked_items.sort(key=lambda item: item.get("id") or 0, reverse=True)
        total = len(ranked_items)
        items = ranked_items[offset : offset + data.page_size]
        return {"page_no": data.page_no, "page_size": data.page_size, "total": total, "has_next": offset + data.page_size < total, "items": items}

    @classmethod
    async def _ensure_case_candidate(cls, auth: AuthSchema, case: ServiceCaseModel, person_id: int) -> None:
        plan_item_exists = await auth.db.scalar(
            select(func.count(ServicePlanItemModel.id)).where(
                ServicePlanItemModel.service_case_id == case.id,
                ServicePlanItemModel.candidate_person_id == person_id,
                ServicePlanItemModel.is_deleted == False,
            )
        )
        if plan_item_exists:
            return
        recommendation_exists = await auth.db.scalar(
            select(func.count(ServiceRecommendationModel.id)).where(
                ServiceRecommendationModel.service_case_id == case.id,
                ServiceRecommendationModel.candidate_person_id == person_id,
                ServiceRecommendationModel.is_deleted == False,
            )
        )
        if recommendation_exists:
            return
        meeting_exists = await auth.db.scalar(
            select(func.count(ServiceMeetingModel.id)).where(
                ServiceMeetingModel.is_deleted == False,
                or_(
                    (ServiceMeetingModel.initiator_service_case_id == case.id) & (ServiceMeetingModel.target_person_id == person_id),
                    (ServiceMeetingModel.target_service_case_id == case.id) & (ServiceMeetingModel.initiator_person_id == person_id),
                ),
            )
        )
        if meeting_exists:
            return
        raise CustomException(msg="该候选不属于当前服务计划")

    @classmethod
    async def service_candidate_detail_service(cls, auth: AuthSchema, case_id: int, person_id: int) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_plan_write_access(auth, case)
        person = await auth.db.get(CrmPersonModel, person_id)
        if not person or person.is_deleted:
            raise CustomException(msg="候选人员不存在")
        if person.id == case.person_id or person.brand_id != case.brand_id:
            raise CustomException(msg="候选人员不属于当前服务范围")
        backup_result = await auth.db.execute(
            select(BackupPoolItemModel).where(
                BackupPoolItemModel.matchmaker_id == case.owner_matchmaker_id,
                BackupPoolItemModel.person_id == person.id,
                BackupPoolItemModel.is_deleted == False,
            )
        )
        backup = backup_result.scalars().first()
        pending_result = await auth.db.execute(
            select(CandidateJoinRequestModel).where(
                CandidateJoinRequestModel.request_matchmaker_id == case.owner_matchmaker_id,
                CandidateJoinRequestModel.person_id == person.id,
                CandidateJoinRequestModel.review_status == "pending",
                CandidateJoinRequestModel.is_deleted == False,
            )
        )
        pending_request = pending_result.scalars().first()
        store_map = await CandidateService._person_store_map(auth, [person.id])
        store_id = store_map.get(person.id)
        dept_names = await CandidateService._dept_names(auth, {store_id} if store_id else set())
        pref_result = await auth.db.execute(
            select(PersonPartnerPreferenceModel).where(
                PersonPartnerPreferenceModel.person_id == person.id,
                PersonPartnerPreferenceModel.is_deleted == False,
            )
        )
        preference = pref_result.scalars().first()
        own_service_count = await auth.db.scalar(
            select(func.count(ServiceCaseModel.id)).where(
                ServiceCaseModel.person_id == person.id,
                ServiceCaseModel.owner_matchmaker_id == case.owner_matchmaker_id,
                ServiceCaseModel.case_status.in_(["serving", "reopened", "pending_close_review"]),
                ServiceCaseModel.is_deleted == False,
            )
        )
        contact_unmasked = bool(
            (backup and backup.contact_unmasked_after_approval)
            or own_service_count
            or cls._is_brand_admin(auth)
        )
        request_scope = "store" if store_id and store_id == case.store_id else "brand"
        preference_payload = None
        if preference:
            preference_payload = {
                "age_min": preference.age_min,
                "age_max": preference.age_max,
                "height_min_cm": preference.height_min_cm,
                "height_max_cm": preference.height_max_cm,
                "weight_min_kg": preference.weight_min_kg,
                "weight_max_kg": preference.weight_max_kg,
                "preferred_residence_region_codes": preference.preferred_residence_region_codes or [],
                "preferred_hometown_region_codes": preference.preferred_hometown_region_codes or [],
                "preferred_education_codes": preference.preferred_education_codes or [],
                "preferred_marital_status_codes": preference.preferred_marital_status_codes or [],
                "preferred_annual_income_codes": preference.preferred_annual_income_codes or [],
                "preferred_house_status_codes": preference.preferred_house_status_codes or [],
                "preferred_car_status_codes": preference.preferred_car_status_codes or [],
                "accept_long_distance": preference.accept_long_distance,
                "accept_divorced": preference.accept_divorced,
                "accept_children": preference.accept_children,
                "children_requirement": preference.children_requirement,
                "preferred_occupation_text": preference.preferred_occupation_text,
                "preference_text": preference.preference_text,
                "preferred_personality_tags": preference.preferred_personality_tags or [],
                "preferred_lifestyle_tags": preference.preferred_lifestyle_tags or [],
                "preferred_relationship_tags": preference.preferred_relationship_tags or [],
                "hard_reject_items": preference.hard_reject_items or [],
                "soft_preference_items": preference.soft_preference_items or [],
                "strictness_level": preference.strictness_level,
                "must_match_fields": preference.must_match_fields or [],
                "preferred_match_fields": preference.preferred_match_fields or [],
            }
        person_center = await cls._service_candidate_person_center(auth, person, contact_unmasked)
        timeline = await cls._service_candidate_timeline(auth, person.id)
        return {
            "person": {
                "id": person.id,
                "display_no": person.display_no,
                "name": person.name,
                "gender": person.gender,
                "mobile": person.primary_mobile if contact_unmasked else cls._mask_mobile(person.primary_mobile),
                "wechat": person.wechat if contact_unmasked else CandidateService._mask_wechat(person.wechat),
                "birth_date": person.birth_date,
                "age": cls._age(person.birth_date),
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
                "profile_intro": person.profile_intro,
                "profile_remark": person.profile_remark,
                "photo_urls": person.photo_urls or [],
                "certification_level": person.certification_level,
                "store_id": store_id,
                "store_name": dept_names.get(store_id or 0),
            },
            "partner_preference": preference_payload,
            "person_center": person_center,
            "timeline": timeline,
            "backup": {
                "in_backup": bool(backup),
                "backup_item_id": backup.id if backup else None,
                "contact_unmasked": contact_unmasked,
                "pending_request": bool(pending_request),
                "pending_request_id": pending_request.id if pending_request else None,
                "request_scope": request_scope,
                "unlock_method": "backup_approved" if contact_unmasked else ("pending_review" if pending_request else "join_request"),
            },
        }

    @classmethod
    async def _service_candidate_person_center(cls, auth: AuthSchema, person: CrmPersonModel, contact_unmasked: bool) -> dict:
        person_id = person.id
        maps = await PersonCenterService._active_maps(auth, [person_id])
        user_ids = set()
        dept_ids = set()
        backup_items = maps["backup"].get(person_id, [])
        join_requests = maps["join_request"].get(person_id, [])
        for item in backup_items:
            user_ids.add(item.matchmaker_id)
            user_ids.add(item.approved_by)
            dept_ids.add(item.store_id)
        for item in join_requests:
            user_ids.add(item.request_matchmaker_id)
            user_ids.add(item.reviewer_id)
            dept_ids.add(item.request_store_id)
            dept_ids.add(item.person_store_id)
        lead = maps["lead"].get(person_id)
        customer = maps["customer"].get(person_id)
        vip = maps["vip"].get(person_id)
        service = maps["service"].get(person_id)
        if lead:
            user_ids.add(lead.owner_sales_id)
            dept_ids.add(lead.store_id)
        if customer:
            user_ids.add(customer.owner_user_id)
            dept_ids.add(customer.store_id)
        if vip:
            user_ids.add(vip.service_owner_user_id)
            dept_ids.add(vip.store_id)
        if service:
            user_ids.add(service.owner_matchmaker_id)
            dept_ids.add(service.store_id)
        user_names = await PersonCenterService._user_names(auth, user_ids)
        dept_names = await PersonCenterService._dept_names(auth, dept_ids)
        channel_names = {
            row.channel_code: row.channel_name
            for row in (
                await auth.db.execute(select(CrmChannelModel).where(CrmChannelModel.is_deleted == False))
            ).scalars().all()
        }
        application = await auth.db.scalar(
            select(CertificationApplicationModel)
            .where(CertificationApplicationModel.person_id == person_id, CertificationApplicationModel.is_deleted == False)
            .order_by(CertificationApplicationModel.id.desc())
        )
        sensitive_count = await auth.db.scalar(
            select(func.count(CertificationSensitiveAccessLogModel.id)).where(
                CertificationSensitiveAccessLogModel.person_id == person_id,
                CertificationSensitiveAccessLogModel.is_deleted == False,
            )
        ) or 0
        preference = maps["preference"].get(person_id)
        ai_profile = maps["ai_profile"].get(person_id)
        brief = PersonCenterService._person_brief(person)
        if contact_unmasked:
            brief["primary_mobile"] = person.primary_mobile
            brief["mobile_masked"] = person.primary_mobile
            brief["wechat"] = person.wechat
        return {
            "person": brief,
            "relations": {
                "lead": cls._relation_names_out(
                    PersonCenterService._model_out(lead, ["store_id", "owner_sales_id", "pool_type", "lead_type", "source_channel_code", "latest_follow_at", "next_follow_at", "assigned_at", "converted_customer_at"]),
                    user_names,
                    dept_names,
                    channel_names,
                ),
                "customer": cls._relation_names_out(
                    PersonCenterService._model_out(customer, ["lead_id", "store_id", "owner_user_id", "current_stage", "max_stage", "latest_follow_at", "next_follow_at", "converted_vip_at", "ended_at", "end_reason"]),
                    user_names,
                    dept_names,
                    channel_names,
                ),
                "vip": cls._relation_names_out(
                    PersonCenterService._model_out(vip, ["customer_id", "contract_id", "store_id", "service_owner_user_id", "vip_level", "vip_status", "started_at", "ended_at", "assigned_at"]),
                    user_names,
                    dept_names,
                    channel_names,
                ),
                "service_case": cls._relation_names_out(
                    PersonCenterService._model_out(service, ["vip_id", "customer_id", "contract_id", "store_id", "owner_matchmaker_id", "pool_type", "case_status", "close_review_status"]),
                    user_names,
                    dept_names,
                    channel_names,
                ),
                "candidate": PersonCenterService._model_out(maps["candidate"].get(person_id), ["candidate_status"]),
                "backup_items": [
                    {
                        "id": item.id,
                        "matchmaker_id": item.matchmaker_id,
                        "matchmaker_name": user_names.get(item.matchmaker_id),
                        "store_id": item.store_id,
                        "store_name": dept_names.get(item.store_id),
                        "source_type": item.source_type,
                        "approved_at": item.approved_at,
                        "created_time": item.created_time,
                    }
                    for item in backup_items
                ],
                "join_requests": [
                    {
                        "id": item.id,
                        "request_scope": item.request_scope,
                        "request_matchmaker_id": item.request_matchmaker_id,
                        "request_matchmaker_name": user_names.get(item.request_matchmaker_id),
                        "request_store_id": item.request_store_id,
                        "request_store_name": dept_names.get(item.request_store_id),
                        "review_status": item.review_status,
                        "reviewed_at": item.reviewed_at,
                        "created_time": item.created_time,
                    }
                    for item in join_requests
                ],
                "miniprogram_user": PersonCenterService._model_out(maps["mp_user"].get(person_id), ["mobile", "nickname", "registered_at", "last_login_at", "is_invisible", "allow_user_wall"]),
                "subscription": PersonCenterService._model_out(maps["subscription"].get(person_id), ["plan_id", "started_at", "expired_at", "total_quota", "used_quota", "subscription_status", "last_unlock_at"]),
                "certification": PersonCenterService._model_out(application, ["level_code", "level_name", "application_status", "paid_at", "approved_at"]) if application else {"certification_level": person.certification_level, "certification_summary": person.certification_summary},
                "partner_preference": PersonCenterService._model_out(preference, ["profile_summary", "strictness_level", "is_final", "version_no", "source_type"]) if preference else None,
                "ai_profile": PersonCenterService._model_out(ai_profile, ["profile_type", "source_type", "content", "generation_status", "model_name", "generated_at"]) if ai_profile else None,
            },
            "quality": PersonCenterService._quality(person, person_id, maps),
            "sensitive_log_count": sensitive_count,
        }

    @classmethod
    def _relation_names_out(
        cls,
        data: dict[str, Any] | None,
        user_names: dict[int, str],
        dept_names: dict[int, str],
        channel_names: dict[str, str],
    ) -> dict[str, Any] | None:
        if not data:
            return None
        store_id = data.get("store_id")
        if store_id:
            data["store_name"] = dept_names.get(store_id)
        for key in ["owner_sales_id", "owner_user_id", "service_owner_user_id", "owner_matchmaker_id"]:
            user_id = data.get(key)
            if user_id:
                data[f"{key}_name"] = user_names.get(user_id)
        channel_code = data.get("source_channel_code")
        if channel_code:
            data["source_channel_name"] = channel_names.get(channel_code)
        return data

    @classmethod
    async def _service_candidate_timeline(cls, auth: AuthSchema, person_id: int) -> list[dict]:
        rows: list[dict[str, Any]] = []
        source_events = (
            await auth.db.execute(select(SourceEventModel).where(SourceEventModel.person_id == person_id, SourceEventModel.is_deleted == False).order_by(SourceEventModel.occurred_at.desc()).limit(50))
        ).scalars().all()
        rows.extend(
            {
                "id": f"source-{item.id}",
                "source_type": "source_event",
                "title": item.event_type,
                "occurred_at": item.occurred_at,
                "content": item.source_channel,
                "related_id": item.id,
                "payload": item.payload,
            }
            for item in source_events
        )
        lead_lifecycle = (
            await auth.db.execute(select(CrmLeadLifecycleModel).where(CrmLeadLifecycleModel.person_id == person_id, CrmLeadLifecycleModel.is_deleted == False).order_by(CrmLeadLifecycleModel.created_time.desc()).limit(50))
        ).scalars().all()
        rows.extend(
            {
                "id": f"lead-{item.id}",
                "source_type": "lead_lifecycle",
                "title": item.operation_type,
                "occurred_at": item.created_time,
                "content": item.remark,
                "operator_user_id": item.operator_user_id,
                "related_id": item.lead_id,
                "payload": item.change_detail,
            }
            for item in lead_lifecycle
        )
        customer_lifecycle = (
            await auth.db.execute(select(CrmCustomerLifecycleModel).where(CrmCustomerLifecycleModel.person_id == person_id, CrmCustomerLifecycleModel.is_deleted == False).order_by(CrmCustomerLifecycleModel.created_time.desc()).limit(50))
        ).scalars().all()
        rows.extend(
            {
                "id": f"customer-{item.id}",
                "source_type": "customer_lifecycle",
                "title": item.operation_type,
                "occurred_at": item.created_time,
                "content": item.remark,
                "operator_user_id": item.operator_user_id,
                "related_id": item.customer_id,
                "payload": item.change_detail,
            }
            for item in customer_lifecycle
        )
        service_logs = (
            await auth.db.execute(select(VipServiceLogModel).where(VipServiceLogModel.person_id == person_id, VipServiceLogModel.is_deleted == False).order_by(VipServiceLogModel.created_time.desc()).limit(50))
        ).scalars().all()
        rows.extend(
            {
                "id": f"service-{item.id}",
                "source_type": "service_log",
                "title": item.operation_type,
                "occurred_at": item.created_time,
                "content": item.remark,
                "operator_user_id": item.operator_user_id,
                "related_id": item.vip_id,
                "payload": item.change_detail,
            }
            for item in service_logs
        )
        join_requests = (
            await auth.db.execute(select(CandidateJoinRequestModel).where(CandidateJoinRequestModel.person_id == person_id, CandidateJoinRequestModel.is_deleted == False).order_by(CandidateJoinRequestModel.created_time.desc()).limit(50))
        ).scalars().all()
        rows.extend(
            {
                "id": f"candidate-request-{item.id}",
                "source_type": "candidate_join_request",
                "title": f"备选加入申请-{item.review_status}",
                "occurred_at": item.reviewed_at or item.created_time,
                "content": item.request_reason or item.review_remark,
                "operator_user_id": item.request_matchmaker_id,
                "related_id": item.id,
                "payload": {"request_scope": item.request_scope, "review_status": item.review_status},
            }
            for item in join_requests
        )
        cert_records = (
            await auth.db.execute(select(CertificationRecordModel).where(CertificationRecordModel.person_id == person_id, CertificationRecordModel.is_deleted == False).order_by(CertificationRecordModel.updated_time.desc()).limit(50))
        ).scalars().all()
        rows.extend(
            {
                "id": f"cert-{item.id}",
                "source_type": "certification",
                "title": f"{item.item_name}-{item.record_status}",
                "occurred_at": item.reviewed_at or item.verified_at or item.submitted_at or item.updated_time or item.created_time,
                "content": item.reject_reason,
                "operator_user_id": item.reviewer_id,
                "related_id": item.id,
                "payload": {"item_code": item.item_code, "record_status": item.record_status},
            }
            for item in cert_records
        )
        user_names = await PersonCenterService._user_names(auth, {row.get("operator_user_id") for row in rows})
        for row in rows:
            row["operator_user_name"] = user_names.get(row.get("operator_user_id"))
        rows.sort(key=lambda row: row["occurred_at"] or datetime.min, reverse=True)
        return rows[:100]

    @classmethod
    def _candidate_match_score(
        cls,
        vip_person: CrmPersonModel | None,
        vip_pref: PersonPartnerPreferenceModel | None,
        candidate: CrmPersonModel,
    ) -> tuple[int, list[str], list[str]]:
        score = 50
        matched: list[str] = []
        unmatched: list[str] = []
        if vip_person and candidate.gender and vip_person.gender and candidate.gender != vip_person.gender:
            score += 10
            matched.append("性别互补")
        age = cls._age(candidate.birth_date)
        if vip_pref and age:
            if vip_pref.age_min and age < vip_pref.age_min:
                score -= 8
                unmatched.append("年龄低于期望")
            elif vip_pref.age_max and age > vip_pref.age_max:
                score -= 8
                unmatched.append("年龄高于期望")
            else:
                score += 8
                matched.append("年龄符合期望")
        if vip_pref and candidate.height_cm:
            if vip_pref.height_min_cm and candidate.height_cm < vip_pref.height_min_cm:
                score -= 6
                unmatched.append("身高低于期望")
            elif vip_pref.height_max_cm and candidate.height_cm > vip_pref.height_max_cm:
                score -= 4
                unmatched.append("身高高于期望")
            else:
                score += 6
                matched.append("身高符合期望")
        for label, value, expected in [
            ("学历", candidate.education, getattr(vip_pref, "preferred_education_codes", None) if vip_pref else None),
            ("婚况", candidate.marital_status, getattr(vip_pref, "preferred_marital_status_codes", None) if vip_pref else None),
            ("年收入", candidate.annual_income, getattr(vip_pref, "preferred_annual_income_codes", None) if vip_pref else None),
        ]:
            if expected and value:
                if value in expected:
                    score += 5
                    matched.append(f"{label}符合期望")
                else:
                    score -= 3
                    unmatched.append(f"{label}不在期望范围")
        return max(0, min(score, 100)), matched, unmatched

    @classmethod
    async def create_recommendation_service(cls, auth: AuthSchema, case_id: int, data: RecommendationCreateSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_plan_write_access(auth, case)
        await cls._ensure_plan_published(auth, case)
        item = await auth.db.get(ServicePlanItemModel, data.plan_item_id)
        if not item or item.is_deleted or item.service_case_id != case.id or item.item_type != "recommendation":
            raise CustomException(msg="请选择当前服务工单下的推荐服务项")
        active_recommendation_count = await auth.db.scalar(
            select(func.count(ServiceRecommendationModel.id)).where(
                ServiceRecommendationModel.plan_item_id == item.id,
                ServiceRecommendationModel.service_case_id == case.id,
                ServiceRecommendationModel.recommendation_status != "abandoned",
                ServiceRecommendationModel.is_deleted == False,
            )
        )
        if active_recommendation_count:
            raise CustomException(msg="该推荐服务项已有推荐记录，请先撤销后再重新推荐")
        if data.candidate_person_id == case.person_id:
            raise CustomException(msg="候选对象不能是当前VIP本人")
        candidate = await auth.db.get(CrmPersonModel, data.candidate_person_id)
        if not candidate or candidate.is_deleted:
            raise CustomException(msg="候选人员不存在")
        duplicate_result = await auth.db.execute(
            select(ServiceRecommendationModel).where(
                ServiceRecommendationModel.plan_item_id == item.id,
                ServiceRecommendationModel.service_case_id == case.id,
                ServiceRecommendationModel.candidate_person_id == candidate.id,
                ServiceRecommendationModel.recommendation_status != "abandoned",
                ServiceRecommendationModel.is_deleted == False,
            )
        )
        if duplicate_result.scalars().first():
            raise CustomException(msg="该候选已在当前推荐节点中")
        recommendation = ServiceRecommendationModel(
            brand_id=case.brand_id,
            service_case_id=case.id,
            plan_item_id=item.id,
            vip_person_id=case.person_id,
            candidate_person_id=candidate.id,
            recommendation_status="recommended",
            recommend_reason=data.recommend_reason,
            match_score=data.match_score,
            matched_points=data.matched_points,
            unmatched_points=data.unmatched_points,
            risk_notes=data.risk_notes,
            matchmaker_remark=data.matchmaker_remark,
        )
        cls._stamp_create(auth, recommendation)
        auth.db.add(recommendation)
        await auth.db.flush()
        item.item_status = "recommended"
        cls._stamp_update(auth, item)
        await auth.db.flush()
        return (await cls.recommendations_service(auth, case.id, recommendation.id))[0]

    @classmethod
    async def revoke_recommendation_service(cls, auth: AuthSchema, case_id: int, recommendation_id: int, data: ServicePlanItemActionSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_plan_write_access(auth, case)
        recommendation = await auth.db.get(ServiceRecommendationModel, recommendation_id)
        if not recommendation or recommendation.is_deleted or recommendation.service_case_id != case.id:
            raise CustomException(msg="推荐记录不存在")
        if recommendation.recommendation_status != "recommended":
            raise CustomException(msg="只有待转约见的推荐记录可以撤销")
        active_meeting_count = await auth.db.scalar(
            select(func.count(ServiceMeetingModel.id)).where(
                ServiceMeetingModel.recommendation_id == recommendation.id,
                ServiceMeetingModel.is_deleted == False,
                ServiceMeetingModel.meeting_status.notin_(["cancelled", "no_show"]),
            )
        )
        if active_meeting_count:
            raise CustomException(msg="推荐已生成有效约见，不能直接撤销")
        recommendation.recommendation_status = "abandoned"
        if data.reason:
            recommendation.matchmaker_remark = data.reason
        cls._stamp_update(auth, recommendation)
        item = await auth.db.get(ServicePlanItemModel, recommendation.plan_item_id)
        if item and not item.is_deleted:
            active_recommendation_count = await auth.db.scalar(
                select(func.count(ServiceRecommendationModel.id)).where(
                    ServiceRecommendationModel.plan_item_id == item.id,
                    ServiceRecommendationModel.service_case_id == case.id,
                    ServiceRecommendationModel.recommendation_status != "abandoned",
                    ServiceRecommendationModel.is_deleted == False,
                    ServiceRecommendationModel.id != recommendation.id,
                )
            )
            if not active_recommendation_count and not item.related_usage_id:
                item.item_status = "pending"
                item.candidate_person_id = None
                item.related_recommendation_id = None
                cls._stamp_update(auth, item)
        await auth.db.flush()
        return (await cls.recommendations_service(auth, case.id, recommendation.id))[0]

    @classmethod
    async def consume_recommendation_service(cls, auth: AuthSchema, case_id: int, recommendation_id: int, data: ServicePlanItemActionSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_plan_write_access(auth, case)
        await cls._ensure_plan_published(auth, case)
        recommendation = await auth.db.get(ServiceRecommendationModel, recommendation_id)
        if not recommendation or recommendation.is_deleted or recommendation.service_case_id != case.id:
            raise CustomException(msg="推荐记录不存在")
        if recommendation.recommendation_status not in {"recommended", "meeting_created", "completed"}:
            raise CustomException(msg="当前推荐记录不能核销")
        item = await auth.db.get(ServicePlanItemModel, recommendation.plan_item_id)
        if not item or item.is_deleted or item.service_case_id != case.id or item.item_type != "recommendation":
            raise CustomException(msg="推荐记录缺少有效推荐服务项")
        if item.related_usage_id:
            raise CustomException(msg="该推荐记录已核销")
        usage = await cls._auto_usage_from_item(
            auth,
            case,
            item.id,
            "recommendation",
            recommendation.id,
            recommendation.id,
            recommendation.candidate_person_id,
            data.reason or "推荐服务核销",
        )
        if not usage:
            raise CustomException(msg="推荐权益核销失败")
        recommendation.recommendation_status = "completed"
        cls._stamp_update(auth, recommendation)
        await auth.db.flush()
        return (await cls.recommendations_service(auth, case.id, recommendation.id))[0]

    @classmethod
    async def recommendations_service(cls, auth: AuthSchema, case_id: int, recommendation_id: int | None = None) -> list[dict]:
        case = await cls._get_case(auth, case_id)
        stmt = select(ServiceRecommendationModel).where(ServiceRecommendationModel.service_case_id == case.id, ServiceRecommendationModel.is_deleted == False)
        if recommendation_id:
            stmt = stmt.where(ServiceRecommendationModel.id == recommendation_id)
        result = await auth.db.execute(stmt.order_by(ServiceRecommendationModel.id.desc()))
        rows = result.scalars().all()
        person_ids = {row.vip_person_id for row in rows} | {row.candidate_person_id for row in rows}
        plan_item_ids = {row.plan_item_id for row in rows}
        people: dict[int, CrmPersonModel] = {}
        if person_ids:
            person_result = await auth.db.execute(select(CrmPersonModel).where(CrmPersonModel.id.in_(person_ids)))
            people = {row.id: row for row in person_result.scalars().all()}
        usage_by_item: dict[int, int | None] = {}
        if plan_item_ids:
            item_result = await auth.db.execute(select(ServicePlanItemModel.id, ServicePlanItemModel.related_usage_id).where(ServicePlanItemModel.id.in_(plan_item_ids)))
            usage_by_item = {row[0]: row[1] for row in item_result.all()}
        return [
            {
                "id": row.id,
                "service_case_id": row.service_case_id,
                "plan_item_id": row.plan_item_id,
                "vip_person_id": row.vip_person_id,
                "vip_name": people.get(row.vip_person_id).name if people.get(row.vip_person_id) else None,
                "candidate_person_id": row.candidate_person_id,
                "candidate_name": people.get(row.candidate_person_id).name if people.get(row.candidate_person_id) else None,
                "candidate_mobile": cls._mask_mobile(people.get(row.candidate_person_id).primary_mobile) if people.get(row.candidate_person_id) else None,
                "recommendation_status": row.recommendation_status,
                "recommend_reason": row.recommend_reason,
                "match_score": row.match_score,
                "matched_points": row.matched_points or [],
                "unmatched_points": row.unmatched_points or [],
                "risk_notes": row.risk_notes,
                "matchmaker_remark": row.matchmaker_remark,
                "related_usage_id": usage_by_item.get(row.plan_item_id),
                "created_time": row.created_time,
            }
            for row in rows
        ]

    @classmethod
    async def update_recommendation_service(cls, auth: AuthSchema, case_id: int, recommendation_id: int, data: RecommendationUpdateSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_plan_write_access(auth, case)
        recommendation = await auth.db.get(ServiceRecommendationModel, recommendation_id)
        if not recommendation or recommendation.is_deleted or recommendation.service_case_id != case.id:
            raise CustomException(msg="推荐记录不存在")
        for field in ["recommendation_status", "recommend_reason", "match_score", "matched_points", "unmatched_points", "risk_notes", "matchmaker_remark"]:
            value = getattr(data, field)
            if value is not None:
                setattr(recommendation, field, value)
        cls._stamp_update(auth, recommendation)
        await auth.db.flush()
        return (await cls.recommendations_service(auth, case.id, recommendation.id))[0]

    @classmethod
    async def _next_meeting_item(cls, auth: AuthSchema, case: ServiceCaseModel, plan_item_id: int | None = None) -> ServicePlanItemModel:
        plan = await cls._ensure_plan(auth, case)
        if plan_item_id:
            item = await auth.db.get(ServicePlanItemModel, plan_item_id)
            if not item or item.is_deleted or item.service_case_id != case.id or item.item_type != "meeting":
                raise CustomException(msg="请选择当前服务工单下的相亲约见节点")
            if item.related_meeting_id or item.item_status in {"completed", "cancelled", "skipped"}:
                raise CustomException(msg="该相亲约见节点不可用")
            return item
        result = await auth.db.execute(
            select(ServicePlanItemModel)
            .where(
                ServicePlanItemModel.plan_id == plan.id,
                ServicePlanItemModel.item_type == "meeting",
                ServicePlanItemModel.related_meeting_id.is_(None),
                ServicePlanItemModel.item_status.in_(["pending", "in_progress"]),
                ServicePlanItemModel.is_deleted == False,
            )
            .order_by(ServicePlanItemModel.sequence_no.asc(), ServicePlanItemModel.id.asc())
        )
        item = result.scalars().first()
        if not item:
            raise CustomException(msg="没有可用的相亲约见计划节点")
        return item

    @classmethod
    async def _target_service_case(cls, auth: AuthSchema, person_id: int, exclude_case_id: int) -> ServiceCaseModel | None:
        result = await auth.db.execute(
            select(ServiceCaseModel)
            .where(
                ServiceCaseModel.person_id == person_id,
                ServiceCaseModel.id != exclude_case_id,
                ServiceCaseModel.case_status.in_(["serving", "reopened", "pending_close_review"]),
                ServiceCaseModel.is_deleted == False,
            )
            .order_by(ServiceCaseModel.id.desc())
        )
        return result.scalars().first()

    @classmethod
    async def create_meeting_service(cls, auth: AuthSchema, case_id: int, data: MeetingCreateSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_plan_write_access(auth, case)
        await cls._ensure_plan_published(auth, case)
        recommendation = await auth.db.get(ServiceRecommendationModel, data.recommendation_id)
        if not recommendation or recommendation.is_deleted or recommendation.service_case_id != case.id:
            raise CustomException(msg="推荐记录不存在")
        if recommendation.recommendation_status not in {"recommended", "completed"}:
            raise CustomException(msg="请选择可转约见的推荐记录")
        existing = await auth.db.execute(
            select(ServiceMeetingModel).where(
                ServiceMeetingModel.recommendation_id == recommendation.id,
                ServiceMeetingModel.is_deleted == False,
                ServiceMeetingModel.meeting_status.notin_(["cancelled", "no_show"]),
            )
        )
        if existing.scalars().first():
            raise CustomException(msg="该推荐记录已创建相亲约见")
        if not data.plan_item_id:
            raise CustomException(msg="请选择绑定的相亲约见计划节点")
        initiator_item = await cls._next_meeting_item(auth, case, data.plan_item_id)
        target_case = await cls._target_service_case(auth, recommendation.candidate_person_id, case.id)
        target_item: ServicePlanItemModel | None = None
        if target_case:
            target_item = await cls._next_meeting_item(auth, target_case)
        meeting = ServiceMeetingModel(
            brand_id=case.brand_id,
            recommendation_id=recommendation.id,
            initiator_service_case_id=case.id,
            initiator_plan_item_id=initiator_item.id,
            initiator_person_id=case.person_id,
            initiator_matchmaker_id=case.owner_matchmaker_id,
            target_service_case_id=target_case.id if target_case else None,
            target_plan_item_id=target_item.id if target_item else None,
            target_person_id=recommendation.candidate_person_id,
            target_matchmaker_id=target_case.owner_matchmaker_id if target_case else None,
            target_is_vip=bool(target_case),
            meeting_type=data.meeting_type,
            meeting_status="pending_confirm" if target_case and target_case.owner_matchmaker_id != case.owner_matchmaker_id else "confirmed",
            scheduled_at=data.scheduled_at,
            appointment_slot=data.appointment_slot,
            location=data.location,
        )
        cls._stamp_create(auth, meeting)
        auth.db.add(meeting)
        await auth.db.flush()
        initiator_item.related_meeting_id = meeting.id
        initiator_item.item_status = "pending_meeting"
        if target_item:
            target_item.related_meeting_id = meeting.id
            target_item.item_status = "pending_meeting"
            cls._stamp_update(auth, target_item)
        if recommendation.recommendation_status == "recommended":
            recommendation.recommendation_status = "meeting_created"
            cls._stamp_update(auth, recommendation)
        cls._stamp_update(auth, initiator_item)
        await auth.db.flush()
        return (await cls.meetings_service(auth, case.id, meeting.id))[0]

    @classmethod
    async def _meeting_access_case_ids(cls, case: ServiceCaseModel, meeting: ServiceMeetingModel) -> set[int]:
        ids = {meeting.initiator_service_case_id}
        if meeting.target_service_case_id:
            ids.add(meeting.target_service_case_id)
        ids.add(case.id)
        return ids

    @classmethod
    async def _ensure_meeting_access(cls, auth: AuthSchema, case: ServiceCaseModel, meeting: ServiceMeetingModel) -> None:
        if case.id not in await cls._meeting_access_case_ids(case, meeting):
            raise CustomException(msg="相亲约见不属于当前服务工单")
        await cls._ensure_case_access(auth, case)

    @classmethod
    async def meetings_service(cls, auth: AuthSchema, case_id: int, meeting_id: int | None = None) -> list[dict]:
        case = await cls._get_case(auth, case_id)
        stmt = select(ServiceMeetingModel).where(
            ServiceMeetingModel.is_deleted == False,
            or_(ServiceMeetingModel.initiator_service_case_id == case.id, ServiceMeetingModel.target_service_case_id == case.id),
        )
        if meeting_id:
            stmt = stmt.where(ServiceMeetingModel.id == meeting_id)
        result = await auth.db.execute(stmt.order_by(ServiceMeetingModel.id.desc()))
        rows = result.scalars().all()
        person_ids = {row.initiator_person_id for row in rows} | {row.target_person_id for row in rows}
        user_ids = {row.initiator_matchmaker_id for row in rows if row.initiator_matchmaker_id} | {row.target_matchmaker_id for row in rows if row.target_matchmaker_id}
        people: dict[int, CrmPersonModel] = {}
        if person_ids:
            person_result = await auth.db.execute(select(CrmPersonModel).where(CrmPersonModel.id.in_(person_ids)))
            people = {row.id: row for row in person_result.scalars().all()}
        users = await cls._user_names(auth.db, user_ids)
        return [
            {
                "id": row.id,
                "recommendation_id": row.recommendation_id,
                "initiator_service_case_id": row.initiator_service_case_id,
                "initiator_plan_item_id": row.initiator_plan_item_id,
                "initiator_person_id": row.initiator_person_id,
                "initiator_name": people.get(row.initiator_person_id).name if people.get(row.initiator_person_id) else None,
                "initiator_gender": people.get(row.initiator_person_id).gender if people.get(row.initiator_person_id) else None,
                "initiator_matchmaker_id": row.initiator_matchmaker_id,
                "initiator_matchmaker_name": users.get(row.initiator_matchmaker_id),
                "target_service_case_id": row.target_service_case_id,
                "target_plan_item_id": row.target_plan_item_id,
                "target_person_id": row.target_person_id,
                "target_name": people.get(row.target_person_id).name if people.get(row.target_person_id) else None,
                "target_gender": people.get(row.target_person_id).gender if people.get(row.target_person_id) else None,
                "target_matchmaker_id": row.target_matchmaker_id,
                "target_matchmaker_name": users.get(row.target_matchmaker_id),
                "target_is_vip": row.target_is_vip,
                "meeting_type": row.meeting_type,
                "meeting_status": row.meeting_status,
                "scheduled_at": row.scheduled_at,
                "appointment_slot": row.appointment_slot,
                "location": row.location,
                "meeting_result": row.meeting_result,
                "next_action": row.next_action,
                "completed_at": row.completed_at,
                "cancelled_at": row.cancelled_at,
                "cancel_reason": row.cancel_reason,
                "matchmaker_opinion": row.matchmaker_opinion,
            }
            for row in rows
        ]

    @classmethod
    async def confirm_meeting_service(cls, auth: AuthSchema, case_id: int, meeting_id: int) -> dict:
        case = await cls._get_case(auth, case_id)
        meeting = await auth.db.get(ServiceMeetingModel, meeting_id)
        if not meeting or meeting.is_deleted or case.id not in {meeting.initiator_service_case_id, meeting.target_service_case_id}:
            raise CustomException(msg="相亲约见不存在")
        if meeting.target_service_case_id and case.id != meeting.target_service_case_id and not cls._is_brand_admin(auth) and not cls._is_store_mgr(auth):
            raise CustomException(msg="只有对方红娘或管理员可以确认")
        await cls._ensure_plan_write_access(auth, case)
        await cls._ensure_plan_published(auth, case)
        if meeting.meeting_status != "pending_confirm":
            raise CustomException(msg="当前约见不需要确认")
        meeting.meeting_status = "confirmed"
        cls._stamp_update(auth, meeting)
        await auth.db.flush()
        return (await cls.meetings_service(auth, case.id, meeting.id))[0]

    @classmethod
    async def complete_meeting_service(cls, auth: AuthSchema, case_id: int, meeting_id: int, data: MeetingActionSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_plan_write_access(auth, case)
        await cls._ensure_plan_published(auth, case)
        meeting = await auth.db.get(ServiceMeetingModel, meeting_id)
        if not meeting or meeting.is_deleted or case.id not in {meeting.initiator_service_case_id, meeting.target_service_case_id}:
            raise CustomException(msg="相亲约见不存在")
        if meeting.meeting_status not in {"confirmed", "pending_feedback"}:
            raise CustomException(msg="当前约见不能登记完成")
        meeting.meeting_status = "pending_feedback"
        meeting.meeting_result = data.meeting_result or meeting.meeting_result
        meeting.next_action = data.next_action or meeting.next_action
        meeting.completed_at = meeting.completed_at or datetime.now()
        cls._stamp_update(auth, meeting)
        await cls._try_finalize_meeting(auth, meeting)
        await auth.db.flush()
        return (await cls.meetings_service(auth, case.id, meeting.id))[0]

    @classmethod
    async def cancel_meeting_service(cls, auth: AuthSchema, case_id: int, meeting_id: int, data: MeetingActionSchema) -> dict:
        return await cls._close_meeting_without_usage(auth, case_id, meeting_id, "cancelled", data.reason)

    @classmethod
    async def no_show_meeting_service(cls, auth: AuthSchema, case_id: int, meeting_id: int, data: MeetingActionSchema) -> dict:
        return await cls._close_meeting_without_usage(auth, case_id, meeting_id, "no_show", data.reason)

    @classmethod
    async def _close_meeting_without_usage(cls, auth: AuthSchema, case_id: int, meeting_id: int, status: str, reason: str | None) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_plan_write_access(auth, case)
        await cls._ensure_plan_published(auth, case)
        meeting = await auth.db.get(ServiceMeetingModel, meeting_id)
        if not meeting or meeting.is_deleted or case.id not in {meeting.initiator_service_case_id, meeting.target_service_case_id}:
            raise CustomException(msg="相亲约见不存在")
        if meeting.meeting_status == "completed":
            raise CustomException(msg="已完成约见不能撤销")
        meeting.meeting_status = status
        meeting.cancelled_at = datetime.now()
        meeting.cancel_reason = reason
        meeting.completed_at = None
        cls._stamp_update(auth, meeting)
        recommendation = await auth.db.get(ServiceRecommendationModel, meeting.recommendation_id) if meeting.recommendation_id else None
        if recommendation and not recommendation.is_deleted and recommendation.recommendation_status == "meeting_created":
            recommendation.recommendation_status = "recommended"
            cls._stamp_update(auth, recommendation)
        for item_id in [meeting.initiator_plan_item_id, meeting.target_plan_item_id]:
            item = await auth.db.get(ServicePlanItemModel, item_id) if item_id else None
            if item:
                item.item_status = "pending"
                item.related_meeting_id = None
                cls._stamp_update(auth, item)
        await auth.db.flush()
        return (await cls.meetings_service(auth, case.id, meeting.id))[0]

    @classmethod
    async def feedback_list_service(cls, auth: AuthSchema, case_id: int, meeting_id: int) -> list[dict]:
        case = await cls._get_case(auth, case_id)
        meeting = await auth.db.get(ServiceMeetingModel, meeting_id)
        if not meeting or meeting.is_deleted or case.id not in {meeting.initiator_service_case_id, meeting.target_service_case_id}:
            raise CustomException(msg="相亲约见不存在")
        result = await auth.db.execute(
            select(ServiceMeetingFeedbackModel).where(
                ServiceMeetingFeedbackModel.meeting_id == meeting.id,
                ServiceMeetingFeedbackModel.is_deleted == False,
            )
        )
        rows = result.scalars().all()
        person_ids = {row.feedback_person_id for row in rows}
        people: dict[int, str] = {}
        if person_ids:
            person_result = await auth.db.execute(select(CrmPersonModel.id, CrmPersonModel.name).where(CrmPersonModel.id.in_(person_ids)))
            people = {row[0]: row[1] for row in person_result.all()}
        users = await cls._user_names(auth.db, {row.feedback_matchmaker_id for row in rows})
        return [
            {
                "id": row.id,
                "meeting_id": row.meeting_id,
                "feedback_person_id": row.feedback_person_id,
                "feedback_person_name": people.get(row.feedback_person_id),
                "feedback_service_case_id": row.feedback_service_case_id,
                "feedback_matchmaker_id": row.feedback_matchmaker_id,
                "feedback_matchmaker_name": users.get(row.feedback_matchmaker_id),
                "feedback_content": row.feedback_content,
                "interest_level": row.interest_level,
                "meeting_result": row.meeting_result,
                "next_action": row.next_action,
                "created_time": row.created_time,
            }
            for row in rows
        ]

    @classmethod
    async def save_feedback_service(cls, auth: AuthSchema, case_id: int, meeting_id: int, data: MeetingFeedbackSaveSchema, feedback_id: int | None = None) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_plan_write_access(auth, case)
        await cls._ensure_plan_published(auth, case)
        meeting = await auth.db.get(ServiceMeetingModel, meeting_id)
        if not meeting or meeting.is_deleted or case.id not in {meeting.initiator_service_case_id, meeting.target_service_case_id}:
            raise CustomException(msg="相亲约见不存在")
        if meeting.meeting_status in {"cancelled", "no_show"}:
            raise CustomException(msg="已撤销或爽约的约见不能填写反馈")
        if data.feedback_person_id not in {meeting.initiator_person_id, meeting.target_person_id}:
            raise CustomException(msg="反馈归属人员必须是约见双方")
        feedback_service_case_id = None
        if data.feedback_person_id == meeting.initiator_person_id:
            feedback_service_case_id = meeting.initiator_service_case_id
        elif data.feedback_person_id == meeting.target_person_id:
            feedback_service_case_id = meeting.target_service_case_id
        feedback = await auth.db.get(ServiceMeetingFeedbackModel, feedback_id) if feedback_id else None
        if feedback_id and (not feedback or feedback.is_deleted or feedback.meeting_id != meeting.id):
            raise CustomException(msg="反馈记录不存在")
        if not feedback:
            existing = await auth.db.execute(
                select(ServiceMeetingFeedbackModel).where(
                    ServiceMeetingFeedbackModel.meeting_id == meeting.id,
                    ServiceMeetingFeedbackModel.feedback_person_id == data.feedback_person_id,
                    ServiceMeetingFeedbackModel.is_deleted == False,
                )
            )
            if existing.scalars().first():
                raise CustomException(msg="该人员反馈已存在，请编辑原反馈")
            feedback = ServiceMeetingFeedbackModel(
                brand_id=meeting.brand_id,
                meeting_id=meeting.id,
                feedback_person_id=data.feedback_person_id,
                feedback_service_case_id=data.feedback_service_case_id or feedback_service_case_id,
                feedback_matchmaker_id=auth.user.id if auth.user else None,
                feedback_content=data.feedback_content,
                interest_level=data.interest_level,
                meeting_result=data.meeting_result,
                next_action=data.next_action,
            )
            cls._stamp_create(auth, feedback)
            auth.db.add(feedback)
        else:
            feedback.feedback_content = data.feedback_content
            feedback.interest_level = data.interest_level
            feedback.meeting_result = data.meeting_result
            feedback.next_action = data.next_action
            feedback.feedback_matchmaker_id = auth.user.id if auth.user else feedback.feedback_matchmaker_id
            cls._stamp_update(auth, feedback)
        if data.matchmaker_opinion is not None:
            meeting.matchmaker_opinion = data.matchmaker_opinion
            cls._stamp_update(auth, meeting)
        if meeting.meeting_status == "confirmed":
            meeting.meeting_status = "pending_feedback"
            meeting.completed_at = datetime.now()
            cls._stamp_update(auth, meeting)
        await auth.db.flush()
        await cls._try_finalize_meeting(auth, meeting)
        await auth.db.flush()
        return next(row for row in await cls.feedback_list_service(auth, case.id, meeting.id) if row["id"] == feedback.id)

    @classmethod
    async def create_course_record_service(cls, auth: AuthSchema, case_id: int, item_id: int, data: CourseRecordCreateSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_plan_write_access(auth, case)
        await cls._ensure_plan_published(auth, case)
        if case.case_status not in {"serving", "reopened"}:
            raise CustomException(msg="当前服务工单不可登记课程")
        item = await auth.db.get(ServicePlanItemModel, item_id)
        if not item or item.is_deleted or item.service_case_id != case.id or item.item_type != "course":
            raise CustomException(msg="请选择当前服务工单下的课程服务节点")
        if item.related_usage_id or item.item_status in {"completed", "cancelled", "skipped"}:
            raise CustomException(msg="该课程节点不可登记")
        entitlement = await auth.db.get(ServiceEntitlementModel, item.entitlement_id) if item.entitlement_id else None
        if not entitlement or entitlement.is_deleted or entitlement.service_case_id != case.id or entitlement.entitlement_type != "course":
            raise CustomException(msg="课程节点缺少有效课程权益")
        existing = await auth.db.execute(
            select(ServiceCourseRecordModel).where(
                ServiceCourseRecordModel.service_plan_item_id == item.id,
                ServiceCourseRecordModel.record_status == "active",
                ServiceCourseRecordModel.is_deleted == False,
            )
        )
        if existing.scalars().first():
            raise CustomException(msg="该课程节点已登记课程")
        record = ServiceCourseRecordModel(
            brand_id=case.brand_id,
            service_case_id=case.id,
            service_plan_item_id=item.id,
            entitlement_id=entitlement.id,
            vip_id=case.vip_id,
            contract_id=case.contract_id,
            person_id=case.person_id,
            matchmaker_id=case.owner_matchmaker_id,
            course_at=data.course_at or datetime.now(),
            course_title=data.course_title,
            course_mode=data.course_mode,
            content=data.content,
            customer_feedback=data.customer_feedback,
            matchmaker_remark=data.matchmaker_remark,
            quantity=1,
            customer_confirm_status=data.customer_confirm_status or "matchmaker_confirmed",
            customer_signature_url=data.customer_signature_url,
            customer_signed_at=data.customer_signed_at,
            record_status="active",
        )
        cls._stamp_create(auth, record)
        auth.db.add(record)
        await auth.db.flush()
        usage = await cls._auto_usage_from_item(auth, case, item.id, "course", record.id, None, None, f"课程服务核销：{record.course_title}")
        if not usage:
            raise CustomException(msg="课程核销失败")
        usage.occurred_at = record.course_at
        usage.title = record.course_title
        usage.content = record.content
        usage.customer_confirm_status = record.customer_confirm_status
        usage.customer_signature_url = record.customer_signature_url
        usage.customer_signed_at = record.customer_signed_at
        record.usage_id = usage.id
        cls._stamp_update(auth, usage)
        cls._stamp_update(auth, record)
        await auth.db.flush()
        return (await cls.course_records_service(auth, case.id, record.id))[0]

    @classmethod
    async def course_records_service(cls, auth: AuthSchema, case_id: int, record_id: int | None = None) -> list[dict]:
        case = await cls._get_case(auth, case_id)
        stmt = select(ServiceCourseRecordModel).where(ServiceCourseRecordModel.service_case_id == case.id, ServiceCourseRecordModel.is_deleted == False)
        if record_id:
            stmt = stmt.where(ServiceCourseRecordModel.id == record_id)
        result = await auth.db.execute(stmt.order_by(ServiceCourseRecordModel.course_at.desc(), ServiceCourseRecordModel.id.desc()))
        rows = result.scalars().all()
        users = await cls._user_names(auth.db, {row.matchmaker_id for row in rows if row.matchmaker_id})
        return [
            {
                "id": row.id,
                "service_case_id": row.service_case_id,
                "service_plan_item_id": row.service_plan_item_id,
                "entitlement_id": row.entitlement_id,
                "usage_id": row.usage_id,
                "course_at": row.course_at,
                "course_title": row.course_title,
                "course_mode": row.course_mode,
                "content": row.content,
                "customer_feedback": row.customer_feedback,
                "matchmaker_remark": row.matchmaker_remark,
                "quantity": row.quantity,
                "customer_confirm_status": row.customer_confirm_status,
                "customer_signature_url": row.customer_signature_url,
                "customer_signed_at": row.customer_signed_at,
                "record_status": row.record_status,
                "revoke_reason": row.revoke_reason,
                "revoked_at": row.revoked_at,
                "matchmaker_id": row.matchmaker_id,
                "matchmaker_name": users.get(row.matchmaker_id),
                "created_time": row.created_time,
            }
            for row in rows
        ]

    @classmethod
    async def revoke_course_record_service(cls, auth: AuthSchema, case_id: int, record_id: int, data: CourseRecordRevokeSchema) -> dict:
        case = await cls._get_case(auth, case_id)
        await cls._ensure_plan_write_access(auth, case)
        record = await auth.db.get(ServiceCourseRecordModel, record_id)
        if not record or record.is_deleted or record.service_case_id != case.id:
            raise CustomException(msg="课程记录不存在")
        if record.record_status != "active":
            raise CustomException(msg="只有有效课程记录可以撤销")
        usage = await auth.db.get(EntitlementUsageLogModel, record.usage_id) if record.usage_id else None
        entitlement = await auth.db.get(ServiceEntitlementModel, record.entitlement_id)
        if not usage or usage.is_deleted or usage.usage_status != "active":
            raise CustomException(msg="课程核销记录不存在或已作废")
        if not entitlement:
            raise CustomException(msg="课程权益账本不存在")
        record.record_status = "revoked"
        record.revoke_reason = data.reason
        record.revoked_by = auth.user.id if auth.user else None
        record.revoked_at = datetime.now()
        usage.usage_status = "void"
        usage.void_reason = data.reason
        usage.voided_by = auth.user.id if auth.user else None
        usage.voided_at = datetime.now()
        entitlement.used_quota = max(entitlement.used_quota - usage.quantity, 0)
        entitlement.remaining_quota += usage.quantity
        entitlement.entitlement_status = "active"
        item = await auth.db.get(ServicePlanItemModel, record.service_plan_item_id)
        if item and not item.is_deleted:
            item.related_usage_id = None
            item.item_status = "pending"
            cls._stamp_update(auth, item)
        cls._stamp_update(auth, record)
        cls._stamp_update(auth, usage)
        cls._stamp_update(auth, entitlement)
        await auth.db.flush()
        return (await cls.course_records_service(auth, case.id, record.id))[0]

    @classmethod
    async def _try_finalize_meeting(cls, auth: AuthSchema, meeting: ServiceMeetingModel) -> None:
        if meeting.meeting_status not in {"confirmed", "pending_feedback"}:
            return
        if not meeting.matchmaker_opinion:
            return
        result = await auth.db.execute(
            select(ServiceMeetingFeedbackModel.feedback_person_id).where(
                ServiceMeetingFeedbackModel.meeting_id == meeting.id,
                ServiceMeetingFeedbackModel.is_deleted == False,
            )
        )
        feedback_person_ids = set(result.scalars().all())
        required = {meeting.initiator_person_id, meeting.target_person_id}
        if not required.issubset(feedback_person_ids):
            return
        recommendation = await auth.db.get(ServiceRecommendationModel, meeting.recommendation_id)
        initiator_case = await auth.db.get(ServiceCaseModel, meeting.initiator_service_case_id)
        if not recommendation or not initiator_case:
            return
        if meeting.initiator_plan_item_id:
            await cls._auto_usage_from_item(auth, initiator_case, meeting.initiator_plan_item_id, "meeting", meeting.id, recommendation.id, meeting.target_person_id, "相亲约见完成自动核销")
        if meeting.target_is_vip and meeting.target_service_case_id and meeting.target_plan_item_id:
            target_case = await auth.db.get(ServiceCaseModel, meeting.target_service_case_id)
            if target_case:
                await cls._auto_usage_from_item(auth, target_case, meeting.target_plan_item_id, "meeting", meeting.id, recommendation.id, meeting.initiator_person_id, "双VIP相亲约见完成自动核销")
        meeting.meeting_status = "completed"
        meeting.completed_at = meeting.completed_at or datetime.now()
        cls._stamp_update(auth, meeting)

    @classmethod
    async def _auto_usage_from_item(
        cls,
        auth: AuthSchema,
        case: ServiceCaseModel,
        item_id: int,
        source_type: str,
        source_id: int,
        recommendation_id: int | None,
        candidate_person_id: int | None,
        title: str,
    ) -> EntitlementUsageLogModel | None:
        item = await auth.db.get(ServicePlanItemModel, item_id)
        if not item or item.is_deleted or item.related_usage_id:
            return None
        entitlement = await auth.db.get(ServiceEntitlementModel, item.entitlement_id) if item.entitlement_id else None
        if not entitlement or entitlement.is_deleted:
            return None
        existing = await auth.db.execute(
            select(EntitlementUsageLogModel).where(
                EntitlementUsageLogModel.service_plan_item_id == item.id,
                EntitlementUsageLogModel.usage_status == "active",
                EntitlementUsageLogModel.is_deleted == False,
            )
        )
        if existing.scalars().first():
            return None
        projected_remaining = entitlement.remaining_quota - 1
        is_overuse = projected_remaining < 0
        if is_overuse and not entitlement.allow_overuse:
            raise CustomException(msg=f"{item.title}对应权益不允许超额核销")
        usage = EntitlementUsageLogModel(
            brand_id=case.brand_id,
            entitlement_id=entitlement.id,
            service_case_id=case.id,
            vip_id=case.vip_id,
            contract_id=entitlement.contract_id,
            usage_type=entitlement.entitlement_type,
            quantity=1,
            usage_status="active",
            occurred_at=datetime.now(),
            title=title,
            content=title,
            candidate_person_id=candidate_person_id,
            is_overuse=is_overuse,
            overuse_reason="服务计划自动核销" if is_overuse else None,
            service_plan_item_id=item.id,
            source_type=source_type,
            source_id=source_id,
            recommendation_id=recommendation_id,
            meeting_id=source_id if source_type == "meeting" else None,
        )
        cls._stamp_create(auth, usage)
        auth.db.add(usage)
        await auth.db.flush()
        entitlement.used_quota += 1
        entitlement.remaining_quota = projected_remaining
        entitlement.entitlement_status = "exhausted" if entitlement.remaining_quota <= 0 else "active"
        item.related_usage_id = usage.id
        item.item_status = "completed"
        cls._stamp_update(auth, entitlement)
        cls._stamp_update(auth, item)
        return usage

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
        if entitlement.entitlement_type == "course":
            raise CustomException(msg="课程核销必须从服务计划课程节点登记")
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
            contract_id=entitlement.contract_id,
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
                "service_plan_item_id": row.service_plan_item_id,
                "source_type": row.source_type,
                "source_id": row.source_id,
                "recommendation_id": row.recommendation_id,
                "meeting_id": row.meeting_id,
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
        if usage.service_plan_item_id:
            item = await auth.db.get(ServicePlanItemModel, usage.service_plan_item_id)
            if item:
                item.related_usage_id = None
                if item.item_type == "recommendation":
                    item.item_status = "recommended"
                elif item.item_type == "meeting":
                    item.item_status = "pending_feedback"
                else:
                    item.item_status = "pending"
                cls._stamp_update(auth, item)
        if usage.usage_type == "recommendation" and usage.recommendation_id:
            recommendation = await auth.db.get(ServiceRecommendationModel, usage.recommendation_id)
            if recommendation and not recommendation.is_deleted and recommendation.recommendation_status == "completed":
                active_meeting_count = await auth.db.scalar(
                    select(func.count(ServiceMeetingModel.id)).where(
                        ServiceMeetingModel.recommendation_id == recommendation.id,
                        ServiceMeetingModel.is_deleted == False,
                        ServiceMeetingModel.meeting_status.notin_(["cancelled", "no_show"]),
                    )
                )
                recommendation.recommendation_status = "meeting_created" if active_meeting_count else "recommended"
                cls._stamp_update(auth, recommendation)
        if usage.meeting_id:
            meeting = await auth.db.get(ServiceMeetingModel, usage.meeting_id)
            if meeting and meeting.meeting_status == "completed":
                meeting.meeting_status = "pending_feedback"
                cls._stamp_update(auth, meeting)
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
            result = await db.execute(
                select(ServiceCaseModel)
                .where(
                    ServiceCaseModel.person_id == contract.person_id,
                    ServiceCaseModel.case_status.in_(["serving", "reopened", "pending_assign"]),
                    ServiceCaseModel.is_deleted == False,
                )
                .order_by(
                    ServiceCaseModel.case_status.in_(["serving", "reopened"]).desc(),
                    ServiceCaseModel.id.desc(),
                )
            )
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
        plan_auth = AuthSchema(db=db, user=None)
        plan = await cls._ensure_plan(plan_auth, case)
        await cls._build_missing_plan_items(plan_auth, case, plan)
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
