from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select

from app.api.v1.module_system.auth.schema import AuthSchema
from app.api.v1.module_system.user.model import UserModel
from app.plugin.module_crm.contract.model import CrmContractModel
from app.plugin.module_crm.customer.model import (
    CrmCustomerProcessRecordModel,
    CrmCustomerProfileModel,
)
from app.plugin.module_crm.lead.model import (
    CrmLeadProcessRecordModel,
    CrmLeadProfileModel,
    CrmLeadStoreRuleModel,
    CrmPersonModel,
)
from app.plugin.module_service.vip.model import (
    BackupPoolItemModel,
    CandidateJoinRequestModel,
    DeepInterviewModel,
    EntitlementUsageLogModel,
    ServiceCaseModel,
    ServiceEntitlementModel,
    ServiceMeetingModel,
    ServicePlanItemModel,
    ServicePlanModel,
    ServiceRecommendationModel,
)

from .schema import NodesQueryParam, SummaryQueryParam, TasksQueryParam


class WorkbenchService:
    """角色工作台聚合服务。"""

    DONE_PLAN_STATUSES = {"completed", "cancelled", "skipped"}
    ACTIVE_CASE_STATUSES = {"serving", "reopened", "pending_close_review"}

    @classmethod
    def _role_codes(cls, auth: AuthSchema) -> set[str]:
        return {role.code for role in auth.user.roles or [] if role.status == "0"} if auth.user else set()

    @classmethod
    def _role_type(cls, auth: AuthSchema) -> tuple[str, str]:
        codes = cls._role_codes(auth)
        if auth.user and auth.user.is_superuser or codes & {"ADMIN", "HQ_OPS"}:
            return "manager", "管理工作台"
        if "STORE_MGR" in codes:
            return "manager", "店长工作台"
        if "MATCHMAKER" in codes:
            return "matchmaker", "服务工作台"
        if "SALES" in codes:
            return "sales", "销售工作台"
        return "personal", "个人工作台"

    @classmethod
    def _is_manager(cls, auth: AuthSchema) -> bool:
        return cls._role_type(auth)[0] == "manager"

    @classmethod
    def _is_brand_admin(cls, auth: AuthSchema) -> bool:
        codes = cls._role_codes(auth)
        return bool(auth.user and auth.user.is_superuser) or bool(codes & {"ADMIN", "HQ_OPS"})

    @staticmethod
    def _day_bounds(target: date | None = None) -> tuple[datetime, datetime]:
        target = target or date.today()
        start = datetime.combine(target, time.min)
        return start, start + timedelta(days=1)

    @classmethod
    def _range_bounds(cls, range_key: str) -> tuple[datetime, datetime]:
        now = datetime.now()
        if range_key == "week":
            start_date = date.today() - timedelta(days=date.today().weekday())
            return datetime.combine(start_date, time.min), now
        if range_key == "month":
            return datetime.combine(date.today().replace(day=1), time.min), now
        start, _ = cls._day_bounds()
        return start, now

    @classmethod
    def _scope_store_id(cls, auth: AuthSchema, requested_store_id: int | None = None) -> int | None:
        if cls._is_brand_admin(auth):
            return requested_store_id
        return auth.user.dept_id if auth.user else requested_store_id

    @classmethod
    def _lead_scope(cls, auth: AuthSchema, requested_store_id: int | None = None, force_mine: bool = False) -> list[Any]:
        conditions: list[Any] = [CrmLeadProfileModel.is_deleted == False]
        role_type, _ = cls._role_type(auth)
        store_id = cls._scope_store_id(auth, requested_store_id)
        if force_mine or role_type == "sales":
            conditions.append(CrmLeadProfileModel.owner_sales_id == (auth.user.id if auth.user else -1))
        elif store_id:
            conditions.append(CrmLeadProfileModel.store_id == store_id)
        elif not cls._is_brand_admin(auth):
            conditions.append(CrmLeadProfileModel.id == -1)
        return conditions

    @classmethod
    def _customer_scope(cls, auth: AuthSchema, requested_store_id: int | None = None, force_mine: bool = False) -> list[Any]:
        conditions: list[Any] = [CrmCustomerProfileModel.is_deleted == False, CrmCustomerProfileModel.ended_at.is_(None)]
        role_type, _ = cls._role_type(auth)
        store_id = cls._scope_store_id(auth, requested_store_id)
        if force_mine or role_type == "sales":
            conditions.append(CrmCustomerProfileModel.owner_user_id == (auth.user.id if auth.user else -1))
        elif store_id:
            conditions.append(CrmCustomerProfileModel.store_id == store_id)
        elif not cls._is_brand_admin(auth):
            conditions.append(CrmCustomerProfileModel.id == -1)
        return conditions

    @classmethod
    def _contract_scope(cls, auth: AuthSchema, requested_store_id: int | None = None, force_mine: bool = False) -> list[Any]:
        conditions: list[Any] = [CrmContractModel.is_deleted == False]
        role_type, _ = cls._role_type(auth)
        store_id = cls._scope_store_id(auth, requested_store_id)
        if force_mine or role_type == "sales":
            conditions.append(CrmContractModel.owner_user_id == (auth.user.id if auth.user else -1))
        elif store_id:
            conditions.append(CrmContractModel.store_id == store_id)
        elif not cls._is_brand_admin(auth):
            conditions.append(CrmContractModel.id == -1)
        return conditions

    @classmethod
    def _case_scope(cls, auth: AuthSchema, requested_store_id: int | None = None, force_mine: bool = False) -> list[Any]:
        conditions: list[Any] = [ServiceCaseModel.is_deleted == False]
        role_type, _ = cls._role_type(auth)
        store_id = cls._scope_store_id(auth, requested_store_id)
        if force_mine or role_type == "matchmaker":
            conditions.append(ServiceCaseModel.owner_matchmaker_id == (auth.user.id if auth.user else -1))
        elif store_id:
            conditions.append(ServiceCaseModel.store_id == store_id)
        elif not cls._is_brand_admin(auth):
            conditions.append(ServiceCaseModel.id == -1)
        return conditions

    @staticmethod
    def _money(value: Decimal | int | float | None) -> float:
        return float(value or 0)

    @classmethod
    async def _count(cls, auth: AuthSchema, model: Any, conditions: list[Any]) -> int:
        result = await auth.db.execute(select(func.count(model.id)).where(*conditions))
        return result.scalar() or 0

    @classmethod
    async def _contract_amount(cls, auth: AuthSchema, conditions: list[Any]) -> float:
        result = await auth.db.execute(select(func.coalesce(func.sum(CrmContractModel.contract_amount), 0)).where(*conditions))
        return cls._money(result.scalar())

    @classmethod
    async def _count_plan_items(cls, auth: AuthSchema, case_scope: list[Any], extra: list[Any]) -> int:
        result = await auth.db.execute(
            select(func.count(ServicePlanItemModel.id))
            .join(ServiceCaseModel, ServicePlanItemModel.service_case_id == ServiceCaseModel.id)
            .where(*case_scope, ServicePlanItemModel.is_deleted == False, *extra)
        )
        return result.scalar() or 0

    @classmethod
    async def _count_plans(cls, auth: AuthSchema, case_scope: list[Any], extra: list[Any]) -> int:
        result = await auth.db.execute(
            select(func.count(ServicePlanModel.id))
            .join(ServiceCaseModel, ServicePlanModel.service_case_id == ServiceCaseModel.id)
            .where(*case_scope, ServicePlanModel.is_deleted == False, *extra)
        )
        return result.scalar() or 0

    @classmethod
    async def _count_recommendations(cls, auth: AuthSchema, case_scope: list[Any], extra: list[Any]) -> int:
        result = await auth.db.execute(
            select(func.count(ServiceRecommendationModel.id))
            .join(ServiceCaseModel, ServiceRecommendationModel.service_case_id == ServiceCaseModel.id)
            .where(*case_scope, ServiceRecommendationModel.is_deleted == False, *extra)
        )
        return result.scalar() or 0

    @classmethod
    async def _count_meetings(cls, auth: AuthSchema, case_scope: list[Any], extra: list[Any]) -> int:
        scoped_case_ids = select(ServiceCaseModel.id).where(*case_scope)
        result = await auth.db.execute(
            select(func.count(ServiceMeetingModel.id)).where(
                ServiceMeetingModel.is_deleted == False,
                or_(
                    ServiceMeetingModel.initiator_service_case_id.in_(scoped_case_ids),
                    ServiceMeetingModel.target_service_case_id.in_(scoped_case_ids),
                ),
                *extra,
            )
        )
        return result.scalar() or 0

    @classmethod
    async def _count_overuse(cls, auth: AuthSchema, case_scope: list[Any]) -> int:
        result = await auth.db.execute(
            select(func.count(EntitlementUsageLogModel.id))
            .join(ServiceCaseModel, EntitlementUsageLogModel.service_case_id == ServiceCaseModel.id)
            .where(*case_scope, EntitlementUsageLogModel.is_deleted == False, EntitlementUsageLogModel.is_overuse == True)
        )
        return result.scalar() or 0

    @classmethod
    async def _reclaim_days_by_store(cls, auth: AuthSchema) -> dict[int, int]:
        result = await auth.db.execute(select(CrmLeadStoreRuleModel).where(CrmLeadStoreRuleModel.is_deleted == False))
        return {row.store_id: row.no_follow_reclaim_days for row in result.scalars().all()}

    @classmethod
    async def _soon_reclaim_count(cls, auth: AuthSchema, conditions: list[Any], days: int = 1) -> int:
        rules = await cls._reclaim_days_by_store(auth)
        result = await auth.db.execute(
            select(CrmLeadProfileModel).where(
                *conditions,
                CrmLeadProfileModel.pool_type == "sales_private",
                CrmLeadProfileModel.owner_sales_id.is_not(None),
                CrmLeadProfileModel.assigned_at.is_not(None),
                CrmLeadProfileModel.lead_type.in_(["new", "second_hand"]),
            )
        )
        now = datetime.now()
        count = 0
        for lead in result.scalars().all():
            reclaim_days = rules.get(lead.store_id or 0, 7)
            due_at = lead.assigned_at + timedelta(days=reclaim_days)
            has_follow = bool(lead.latest_follow_at and lead.latest_follow_at >= lead.assigned_at)
            if not has_follow and now <= due_at <= now + timedelta(days=days):
                count += 1
        return count

    @classmethod
    async def summary_service(cls, auth: AuthSchema, search: SummaryQueryParam) -> dict:
        role_type, role_name = cls._role_type(auth)
        start_at, end_at = cls._range_bounds(search.range)
        day_start, day_end = cls._day_bounds()
        metrics: list[dict[str, Any]] = []

        def add(key: str, title: str, value: int | float, unit: str | None = None, priority: str = "primary", route_path: str | None = None, query: dict[str, Any] | None = None) -> None:
            metrics.append({"key": key, "title": title, "value": value, "unit": unit, "priority": priority, "route_path": route_path, "query": query or {}})

        if role_type == "matchmaker":
            case_scope = cls._case_scope(auth, search.store_id, force_mine=True)
            active_case_scope = [*case_scope, ServiceCaseModel.case_status.in_(cls.ACTIVE_CASE_STATUSES)]
            add("serving_vip", "我的服务中VIP", await cls._count(auth, ServiceCaseModel, active_case_scope), route_path="/miailove/service/vip")
            add("today_plan_items", "今日服务节点", await cls._count_plan_items(auth, case_scope, [ServicePlanItemModel.due_at >= day_start, ServicePlanItemModel.due_at < day_end, ServicePlanItemModel.item_status.notin_(cls.DONE_PLAN_STATUSES)]), route_path="/miailove/service/vip")
            add("today_meetings", "今日约见", await cls._count(auth, ServiceMeetingModel, [ServiceMeetingModel.is_deleted == False, or_(ServiceMeetingModel.initiator_matchmaker_id == auth.user.id, ServiceMeetingModel.target_matchmaker_id == auth.user.id), ServiceMeetingModel.scheduled_at >= day_start, ServiceMeetingModel.scheduled_at < day_end, ServiceMeetingModel.meeting_status.in_(["confirmed", "pending_feedback"])]), route_path="/miailove/service/vip")
            add("pending_feedback", "今日待反馈", await cls._count(auth, ServiceMeetingModel, [ServiceMeetingModel.is_deleted == False, or_(ServiceMeetingModel.initiator_matchmaker_id == auth.user.id, ServiceMeetingModel.target_matchmaker_id == auth.user.id), ServiceMeetingModel.meeting_status == "pending_feedback"]), priority="warning", route_path="/miailove/service/vip")
            add("pending_interview", "待首次深访", await cls._pending_interview_count(auth, case_scope), priority="warning", route_path="/miailove/service/vip")
            add("pending_recommend", "待推荐节点", await cls._count_plan_items(auth, case_scope, [ServicePlanItemModel.item_type == "recommendation", ServicePlanItemModel.item_status.in_(["pending", "in_progress"])]), route_path="/miailove/service/vip")
            add("pending_meeting", "待约见节点", await cls._count_plan_items(auth, case_scope, [ServicePlanItemModel.item_type == "meeting", ServicePlanItemModel.item_status.in_(["pending", "in_progress", "pending_meeting"])]), route_path="/miailove/service/vip")
            add("overdue_plan_items", "逾期服务节点", await cls._count_plan_items(auth, case_scope, [ServicePlanItemModel.due_at < datetime.now(), ServicePlanItemModel.item_status.notin_(cls.DONE_PLAN_STATUSES)]), priority="danger", route_path="/miailove/service/vip")
            add("expiring_vip", "即将到期VIP", await cls._expiring_case_count(auth, case_scope), priority="warning", route_path="/miailove/service/vip")
            add("remaining_entitlements", "剩余权益未完成", await cls._remaining_entitlement_count(auth, case_scope), priority="warning", route_path="/miailove/service/vip")
        else:
            force_mine = role_type == "sales"
            lead_scope = cls._lead_scope(auth, search.store_id, force_mine=force_mine)
            customer_scope = cls._customer_scope(auth, search.store_id, force_mine=force_mine)
            contract_scope = cls._contract_scope(auth, search.store_id, force_mine=force_mine)
            entered_at = func.coalesce(CrmLeadProfileModel.store_entered_at, CrmLeadProfileModel.assigned_at, CrmLeadProfileModel.created_time)
            lead_route_path = "/miailove/lead/sales-private" if role_type == "sales" else "/miailove/lead/all"
            add("today_store_leads", "今日进入门店线索", await cls._count(auth, CrmLeadProfileModel, [*lead_scope, entered_at >= day_start, entered_at < day_end]), route_path=lead_route_path)
            add("today_valid_leads", "今日有效线索", await cls._valid_lead_count(auth, lead_scope, day_start, day_end), route_path=lead_route_path)
            add("today_appointments", "今日预约成功", await cls._count(auth, CrmCustomerProcessRecordModel, [CrmCustomerProcessRecordModel.is_deleted == False, CrmCustomerProcessRecordModel.record_type == "appointment", CrmCustomerProcessRecordModel.scheduled_at >= day_start, CrmCustomerProcessRecordModel.scheduled_at < day_end, CrmCustomerProcessRecordModel.customer_id.in_(select(CrmCustomerProfileModel.id).where(*customer_scope))]), route_path="/miailove/customer/visit")
            add("range_contracts", "合同创建数", await cls._count(auth, CrmContractModel, [*contract_scope, CrmContractModel.contract_status != "voided", CrmContractModel.created_time >= start_at, CrmContractModel.created_time <= end_at]), route_path="/miailove/crm/contract")
            add("range_contract_amount", "合同金额", await cls._contract_amount(auth, [*contract_scope, CrmContractModel.contract_status != "voided", CrmContractModel.created_time >= start_at, CrmContractModel.created_time <= end_at]), "元", route_path="/miailove/crm/contract")
            if role_type == "manager":
                case_scope = cls._case_scope(auth, search.store_id)
                add("store_pool_leads", "当前门店公海", await cls._count(auth, CrmLeadProfileModel, [*lead_scope, CrmLeadProfileModel.pool_type == "store_pool"]), route_path="/miailove/lead/store-pool")
                add("sales_private_leads", "当前销售私海", await cls._count(auth, CrmLeadProfileModel, [*lead_scope, CrmLeadProfileModel.pool_type == "sales_private"]), route_path="/miailove/lead/sales-private")
                add("serving_vip", "服务中VIP", await cls._count(auth, ServiceCaseModel, [*case_scope, ServiceCaseModel.case_status.in_(cls.ACTIVE_CASE_STATUSES)]), route_path="/miailove/service/vip")
                add("overdue_plan_items", "逾期服务节点", await cls._count_plan_items(auth, case_scope, [ServicePlanItemModel.due_at < datetime.now(), ServicePlanItemModel.item_status.notin_(cls.DONE_PLAN_STATUSES)]), priority="danger", route_path="/miailove/service/vip")
            else:
                add("my_private_leads", "我的私海线索", await cls._count(auth, CrmLeadProfileModel, [*lead_scope, CrmLeadProfileModel.pool_type == "sales_private"]), route_path="/miailove/lead/sales-private")
                add("soon_reclaim_leads", "即将回公海线索", await cls._soon_reclaim_count(auth, lead_scope), priority="warning", route_path="/miailove/lead/sales-private")
        return {"role_type": role_type, "role_name": role_name, "range": search.range, "scope": "store" if role_type == "manager" else "mine", "metrics": metrics}

    @classmethod
    async def _valid_lead_count(cls, auth: AuthSchema, lead_scope: list[Any], start_at: datetime, end_at: datetime) -> int:
        result = await auth.db.execute(
            select(func.count(func.distinct(CrmLeadProcessRecordModel.lead_id)))
            .join(CrmLeadProfileModel, CrmLeadProcessRecordModel.lead_id == CrmLeadProfileModel.id)
            .where(
                *lead_scope,
                CrmLeadProcessRecordModel.is_deleted == False,
                CrmLeadProcessRecordModel.action_type == "follow",
                CrmLeadProcessRecordModel.created_time >= start_at,
                CrmLeadProcessRecordModel.created_time < end_at,
            )
        )
        return result.scalar() or 0

    @classmethod
    async def _pending_interview_count(cls, auth: AuthSchema, case_scope: list[Any]) -> int:
        result = await auth.db.execute(
            select(func.count(ServiceCaseModel.id)).where(
                *case_scope,
                ServiceCaseModel.case_status.in_(cls.ACTIVE_CASE_STATUSES),
                ~ServiceCaseModel.id.in_(
                    select(DeepInterviewModel.service_case_id).where(
                        DeepInterviewModel.is_deleted == False,
                        DeepInterviewModel.interview_status == "active",
                        DeepInterviewModel.service_case_id.is_not(None),
                    )
                ),
            )
        )
        return result.scalar() or 0

    @classmethod
    async def _expiring_case_count(cls, auth: AuthSchema, case_scope: list[Any]) -> int:
        today = date.today()
        result = await auth.db.execute(
            select(func.count(ServiceCaseModel.id))
            .join(CrmContractModel, ServiceCaseModel.contract_id == CrmContractModel.id)
            .where(*case_scope, ServiceCaseModel.case_status.in_(cls.ACTIVE_CASE_STATUSES), CrmContractModel.end_date >= today, CrmContractModel.end_date <= today + timedelta(days=30))
        )
        return result.scalar() or 0

    @classmethod
    async def _remaining_entitlement_count(cls, auth: AuthSchema, case_scope: list[Any]) -> int:
        result = await auth.db.execute(
            select(func.count(ServiceEntitlementModel.id))
            .join(ServiceCaseModel, ServiceEntitlementModel.service_case_id == ServiceCaseModel.id)
            .where(*case_scope, ServiceEntitlementModel.is_deleted == False, ServiceEntitlementModel.remaining_quota > 0, ServiceEntitlementModel.entitlement_status == "active")
        )
        return result.scalar() or 0

    @classmethod
    def _bucket_condition(cls, column: Any, bucket: str, days: int) -> list[Any]:
        now = datetime.now()
        day_start, day_end = cls._day_bounds()
        if bucket == "overdue":
            return [column < now]
        if bucket == "upcoming":
            return [column >= day_end, column < day_end + timedelta(days=days)]
        return [column >= day_start, column < day_end]

    @staticmethod
    def _dt(value: datetime | None) -> str | None:
        return value.strftime("%Y-%m-%d %H:%M:%S") if value else None

    @classmethod
    def _task(cls, task_type: str, title: str, object_type: str, object_id: int, object_name: str | None, status: str, due_at: datetime | None, owner_user_id: int | None, owner_user_name: str | None, priority: str, action_text: str, route_path: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "id": f"{task_type}:{object_id}",
            "task_type": task_type,
            "title": title,
            "object_type": object_type,
            "object_id": object_id,
            "object_name": object_name,
            "status": status,
            "due_at": cls._dt(due_at),
            "owner_user_id": owner_user_id,
            "owner_user_name": owner_user_name,
            "priority": priority,
            "action_text": action_text,
            "route_path": route_path,
            "query": query or {"id": object_id},
        }

    @classmethod
    async def tasks_service(cls, auth: AuthSchema, search: TasksQueryParam) -> dict:
        role_type, _ = cls._role_type(auth)
        items: list[dict[str, Any]] = []
        if role_type == "matchmaker":
            await cls._append_service_tasks(auth, search, items)
        else:
            await cls._append_sales_manager_tasks(auth, search, items)
        priority_rank = {"danger": 0, "warning": 1, "primary": 2, "success": 3, "info": 4}
        items.sort(key=lambda item: (priority_rank.get(item["priority"], 9), item["due_at"] or "9999-12-31 23:59:59"))
        total = len(items)
        items = items[: search.limit]
        return {"role_type": role_type, "bucket": search.bucket, "total": total, "items": items}

    @classmethod
    async def _append_sales_manager_tasks(cls, auth: AuthSchema, search: TasksQueryParam, items: list[dict[str, Any]]) -> None:
        role_type, _ = cls._role_type(auth)
        force_mine = role_type == "sales"
        lead_scope = cls._lead_scope(auth, force_mine=force_mine)
        customer_scope = cls._customer_scope(auth, force_mine=force_mine)
        contract_scope = cls._contract_scope(auth, force_mine=force_mine)
        due_conditions = cls._bucket_condition(CrmLeadProfileModel.next_follow_at, search.bucket, search.days)
        lead_rows = (
            await auth.db.execute(
                select(CrmLeadProfileModel, CrmPersonModel, UserModel)
                .join(CrmPersonModel, CrmLeadProfileModel.person_id == CrmPersonModel.id)
                .outerjoin(UserModel, CrmLeadProfileModel.owner_sales_id == UserModel.id)
                .where(*lead_scope, CrmLeadProfileModel.next_follow_at.is_not(None), *due_conditions)
                .order_by(CrmLeadProfileModel.next_follow_at.asc())
                .limit(30)
            )
        ).all()
        for lead, person, owner in lead_rows:
            items.append(cls._task("lead_follow", "线索待跟进", "lead", lead.id, person.name, lead.lead_type, lead.next_follow_at, lead.owner_sales_id, owner.name if owner else None, "danger" if search.bucket == "overdue" else "warning", "立即跟进", "/miailove/lead/sales-private" if lead.pool_type == "sales_private" else "/miailove/lead/store-pool"))

        appointment_rows = (
            await auth.db.execute(
                select(CrmCustomerProcessRecordModel, CrmCustomerProfileModel, CrmPersonModel, UserModel)
                .join(CrmCustomerProfileModel, CrmCustomerProcessRecordModel.customer_id == CrmCustomerProfileModel.id)
                .join(CrmPersonModel, CrmCustomerProfileModel.person_id == CrmPersonModel.id)
                .outerjoin(UserModel, CrmCustomerProfileModel.owner_user_id == UserModel.id)
                .where(
                    *customer_scope,
                    CrmCustomerProcessRecordModel.is_deleted == False,
                    CrmCustomerProcessRecordModel.record_type == "appointment",
                    CrmCustomerProcessRecordModel.appointment_status == "pending",
                    CrmCustomerProcessRecordModel.scheduled_at.is_not(None),
                    *cls._bucket_condition(CrmCustomerProcessRecordModel.scheduled_at, search.bucket, search.days),
                )
                .order_by(CrmCustomerProcessRecordModel.scheduled_at.asc())
                .limit(30)
            )
        ).all()
        for record, customer, person, owner in appointment_rows:
            items.append(cls._task("customer_appointment", "客户预约到店", "customer", customer.id, person.name, record.appointment_status or "pending", record.scheduled_at, customer.owner_user_id, owner.name if owner else None, "danger" if search.bucket == "overdue" else "primary", "查看预约", "/miailove/customer/visit", {"process_id": record.id, "customer_id": customer.id}))

        if search.bucket in {"today", "overdue"}:
            status_filter = ["draft", "rejected"]
            contract_rows = (
                await auth.db.execute(
                    select(CrmContractModel, CrmPersonModel, UserModel)
                    .join(CrmPersonModel, CrmContractModel.person_id == CrmPersonModel.id)
                    .outerjoin(UserModel, CrmContractModel.owner_user_id == UserModel.id)
                    .where(*contract_scope, CrmContractModel.contract_status.in_(status_filter))
                    .order_by(CrmContractModel.created_time.asc())
                    .limit(20)
                )
            ).all()
            for contract, person, owner in contract_rows:
                items.append(cls._task("contract_pending", "合同待处理", "contract", contract.id, f"{person.name} · {contract.contract_no}", contract.contract_status, contract.created_time, contract.owner_user_id, owner.name if owner else None, "warning", "处理合同", "/miailove/crm/contract"))

        if role_type == "manager" and search.bucket in {"today", "overdue"}:
            await cls._append_manager_review_tasks(auth, items)

    @classmethod
    async def _append_manager_review_tasks(cls, auth: AuthSchema, items: list[dict[str, Any]]) -> None:
        store_id = cls._scope_store_id(auth)
        contract_conditions = [CrmContractModel.is_deleted == False, CrmContractModel.contract_status == "pending_review"]
        case_conditions = [ServiceCaseModel.is_deleted == False, ServiceCaseModel.case_status == "pending_assign"]
        close_conditions = [ServiceCaseModel.is_deleted == False, ServiceCaseModel.close_review_status == "pending"]
        request_conditions = [CandidateJoinRequestModel.is_deleted == False, CandidateJoinRequestModel.review_status == "pending"]
        if store_id:
            contract_conditions.append(CrmContractModel.store_id == store_id)
            case_conditions.append(ServiceCaseModel.store_id == store_id)
            close_conditions.append(ServiceCaseModel.store_id == store_id)
            request_conditions.append(CandidateJoinRequestModel.request_store_id == store_id)
        for contract in (await auth.db.execute(select(CrmContractModel).where(*contract_conditions).limit(20))).scalars().all():
            items.append(cls._task("contract_review", "合同待审核", "contract", contract.id, contract.contract_no, contract.contract_status, contract.review_submitted_at or contract.created_time, contract.owner_user_id, None, "warning", "审核合同", "/miailove/crm/contract"))
        for case in (await auth.db.execute(select(ServiceCaseModel).where(*case_conditions).limit(20))).scalars().all():
            items.append(cls._task("vip_assign", "VIP待分配", "service_case", case.id, f"服务工单 {case.id}", case.case_status, case.created_time, case.owner_matchmaker_id, None, "warning", "分配红娘", "/miailove/service/vip"))
        for case in (await auth.db.execute(select(ServiceCaseModel).where(*close_conditions).limit(20))).scalars().all():
            items.append(cls._task("close_review", "关单待审核", "service_case", case.id, f"服务工单 {case.id}", case.close_review_status, case.close_requested_at, case.owner_matchmaker_id, None, "danger", "审核关单", "/miailove/service/vip"))
        for request in (await auth.db.execute(select(CandidateJoinRequestModel).where(*request_conditions).limit(20))).scalars().all():
            items.append(cls._task("candidate_join_review", "备选库申请待审核", "candidate_join_request", request.id, f"申请 {request.id}", request.review_status, request.created_time, request.request_matchmaker_id, None, "warning", "审核申请", "/miailove/service/candidate"))

    @classmethod
    async def _append_service_tasks(cls, auth: AuthSchema, search: TasksQueryParam, items: list[dict[str, Any]]) -> None:
        case_scope = cls._case_scope(auth, force_mine=True)
        plan_rows = (
            await auth.db.execute(
                select(ServicePlanItemModel, ServiceCaseModel, CrmPersonModel)
                .join(ServiceCaseModel, ServicePlanItemModel.service_case_id == ServiceCaseModel.id)
                .join(CrmPersonModel, ServiceCaseModel.person_id == CrmPersonModel.id)
                .where(*case_scope, ServicePlanItemModel.is_deleted == False, ServicePlanItemModel.item_status.notin_(cls.DONE_PLAN_STATUSES), ServicePlanItemModel.due_at.is_not(None), *cls._bucket_condition(ServicePlanItemModel.due_at, search.bucket, search.days))
                .order_by(ServicePlanItemModel.due_at.asc())
                .limit(50)
            )
        ).all()
        for item, case, person in plan_rows:
            items.append(cls._task("service_plan_item", item.title, "service_case", case.id, person.name, item.item_status, item.due_at, case.owner_matchmaker_id, auth.user.name if auth.user else None, "danger" if search.bucket == "overdue" else "primary", "处理服务", "/miailove/service/vip", {"case_id": case.id, "item_id": item.id}))
        meeting_rows = (
            await auth.db.execute(
                select(ServiceMeetingModel)
                .where(
                    ServiceMeetingModel.is_deleted == False,
                    or_(ServiceMeetingModel.initiator_matchmaker_id == auth.user.id, ServiceMeetingModel.target_matchmaker_id == auth.user.id),
                    ServiceMeetingModel.meeting_status.in_(["confirmed", "pending_feedback"]),
                    ServiceMeetingModel.scheduled_at.is_not(None),
                    *cls._bucket_condition(ServiceMeetingModel.scheduled_at, search.bucket, search.days),
                )
                .order_by(ServiceMeetingModel.scheduled_at.asc())
                .limit(30)
            )
        ).scalars().all()
        for meeting in meeting_rows:
            items.append(cls._task("service_meeting", "相亲约见", "meeting", meeting.id, f"约见 {meeting.id}", meeting.meeting_status, meeting.scheduled_at, meeting.initiator_matchmaker_id or meeting.target_matchmaker_id, auth.user.name if auth.user else None, "warning" if meeting.meeting_status == "pending_feedback" else "primary", "处理约见", "/miailove/service/vip"))

    @classmethod
    async def nodes_service(cls, auth: AuthSchema, search: NodesQueryParam) -> dict:
        role_type, _ = cls._role_type(auth)
        force_mine = search.scope == "mine" and role_type != "manager"
        groups: list[dict[str, Any]] = []
        if role_type in {"manager", "sales", "personal"}:
            groups.extend(await cls._crm_node_groups(auth, search, force_mine))
        if role_type in {"manager", "matchmaker"}:
            groups.extend(await cls._service_node_groups(auth, search, force_mine or role_type == "matchmaker"))
        return {"role_type": role_type, "scope": search.scope, "groups": groups}

    @classmethod
    async def _crm_node_groups(cls, auth: AuthSchema, search: NodesQueryParam, force_mine: bool) -> list[dict[str, Any]]:
        lead_scope = cls._lead_scope(auth, search.store_id, force_mine=force_mine)
        customer_scope = cls._customer_scope(auth, search.store_id, force_mine=force_mine)
        contract_scope = cls._contract_scope(auth, search.store_id, force_mine=force_mine)

        async def lead_count(extra: list[Any]) -> int:
            return await cls._count(auth, CrmLeadProfileModel, [*lead_scope, *extra])

        async def customer_count(extra: list[Any]) -> int:
            return await cls._count(auth, CrmCustomerProfileModel, [*customer_scope, *extra])

        async def contract_count(status: str) -> int:
            return await cls._count(auth, CrmContractModel, [*contract_scope, CrmContractModel.contract_status == status])

        lead_all_route_path = "/miailove/lead/sales-private" if force_mine else "/miailove/lead/all"

        return [
            {
                "key": "lead",
                "title": "线索节点",
                "nodes": [
                    {"key": "pending", "title": "待分配", "count": await lead_count([CrmLeadProfileModel.lead_type == "pending"]), "route_path": lead_all_route_path, "query": {"lead_type": "pending"}},
                    {"key": "store_pool", "title": "门店公海", "count": await lead_count([CrmLeadProfileModel.pool_type == "store_pool"]), "route_path": "/miailove/lead/store-pool", "query": {}},
                    {"key": "sales_private", "title": "销售私海", "count": await lead_count([CrmLeadProfileModel.pool_type == "sales_private"]), "route_path": "/miailove/lead/sales-private", "query": {}},
                    {"key": "new", "title": "新线索", "count": await lead_count([CrmLeadProfileModel.lead_type == "new"]), "route_path": "/miailove/lead/sales-private", "query": {"lead_type": "new"}},
                    {"key": "second_hand", "title": "二手线索", "count": await lead_count([CrmLeadProfileModel.lead_type == "second_hand"]), "route_path": "/miailove/lead/sales-private", "query": {"lead_type": "second_hand"}},
                    {"key": "converted_customer", "title": "已转建档", "count": await lead_count([CrmLeadProfileModel.lead_type == "converted_customer"]), "route_path": lead_all_route_path, "query": {"lead_type": "converted_customer"}},
                    {"key": "invalid", "title": "无效", "count": await lead_count([CrmLeadProfileModel.lead_type == "invalid"]), "route_path": lead_all_route_path, "query": {"lead_type": "invalid"}},
                ],
            },
            {
                "key": "customer",
                "title": "客户节点",
                "nodes": [
                    {"key": "profiling", "title": "待完善资料", "count": await customer_count([CrmCustomerProfileModel.current_stage == "profiling"]), "route_path": "/miailove/customer/list", "query": {"current_stage": "profiling"}},
                    {"key": "appointed", "title": "已预约", "count": await customer_count([CrmCustomerProfileModel.current_stage == "appointed"]), "route_path": "/miailove/customer/list", "query": {"current_stage": "appointed"}},
                    {"key": "visited", "title": "已到店", "count": await customer_count([CrmCustomerProfileModel.current_stage == "visited"]), "route_path": "/miailove/customer/list", "query": {"current_stage": "visited"}},
                    {"key": "consulted", "title": "面谈中", "count": await customer_count([CrmCustomerProfileModel.current_stage == "consulted"]), "route_path": "/miailove/customer/list", "query": {"current_stage": "consulted"}},
                    {"key": "signing", "title": "签约推进中", "count": await customer_count([CrmCustomerProfileModel.current_stage == "signing"]), "route_path": "/miailove/customer/list", "query": {"current_stage": "signing"}},
                    {"key": "converted_vip", "title": "已转VIP", "count": await customer_count([CrmCustomerProfileModel.current_stage == "converted_vip"]), "route_path": "/miailove/customer/list", "query": {"current_stage": "converted_vip"}},
                ],
            },
            {
                "key": "contract",
                "title": "合同节点",
                "nodes": [
                    {"key": "draft", "title": "草稿", "count": await contract_count("draft"), "route_path": "/miailove/crm/contract", "query": {"contract_status": "draft"}},
                    {"key": "pending_review", "title": "待审核", "count": await contract_count("pending_review"), "route_path": "/miailove/crm/contract", "query": {"contract_status": "pending_review"}},
                    {"key": "rejected", "title": "已驳回", "count": await contract_count("rejected"), "priority": "warning", "route_path": "/miailove/crm/contract", "query": {"contract_status": "rejected"}},
                    {"key": "approved", "title": "已通过", "count": await contract_count("approved"), "route_path": "/miailove/crm/contract", "query": {"contract_status": "approved"}},
                    {"key": "effective", "title": "已生效", "count": await contract_count("effective"), "route_path": "/miailove/crm/contract", "query": {"contract_status": "effective"}},
                    {"key": "voided", "title": "已作废", "count": await contract_count("voided"), "route_path": "/miailove/crm/contract", "query": {"contract_status": "voided"}},
                ],
            },
        ]

    @classmethod
    async def _service_node_groups(cls, auth: AuthSchema, search: NodesQueryParam, force_mine: bool) -> list[dict[str, Any]]:
        case_scope = cls._case_scope(auth, search.store_id, force_mine=force_mine)

        async def case_count(extra: list[Any]) -> int:
            return await cls._count(auth, ServiceCaseModel, [*case_scope, *extra])

        async def item_count(extra: list[Any]) -> int:
            return await cls._count_plan_items(auth, case_scope, extra)

        return [
            {
                "key": "service_case",
                "title": "VIP服务",
                "nodes": [
                    {"key": "pending_assign", "title": "待分配", "count": await case_count([ServiceCaseModel.case_status == "pending_assign"]), "priority": "warning", "route_path": "/miailove/service/vip", "query": {"case_status": "pending_assign"}},
                    {"key": "serving", "title": "服务中", "count": await case_count([ServiceCaseModel.case_status.in_(cls.ACTIVE_CASE_STATUSES)]), "route_path": "/miailove/service/vip", "query": {"case_status": "serving"}},
                    {"key": "pending_interview", "title": "待深访", "count": await cls._pending_interview_count(auth, case_scope), "priority": "warning", "route_path": "/miailove/service/vip", "query": {"pending_interview": True}},
                    {"key": "plan_unpublished", "title": "计划未发布", "count": await cls._count_plans(auth, case_scope, [ServicePlanModel.plan_status != "published"]), "priority": "warning", "route_path": "/miailove/service/vip", "query": {}},
                    {"key": "expiring", "title": "即将到期", "count": await cls._expiring_case_count(auth, case_scope), "priority": "warning", "route_path": "/miailove/service/vip", "query": {"expiring": True}},
                    {"key": "close_review", "title": "待关单", "count": await case_count([ServiceCaseModel.close_review_status == "pending"]), "priority": "danger", "route_path": "/miailove/service/vip", "query": {"close_review_status": "pending"}},
                ],
            },
            {
                "key": "service_plan",
                "title": "服务计划",
                "nodes": [
                    {"key": "pending", "title": "待处理", "count": await item_count([ServicePlanItemModel.item_status == "pending"]), "route_path": "/miailove/service/vip", "query": {"item_status": "pending"}},
                    {"key": "in_progress", "title": "进行中", "count": await item_count([ServicePlanItemModel.item_status == "in_progress"]), "route_path": "/miailove/service/vip", "query": {"item_status": "in_progress"}},
                    {"key": "recommended", "title": "已推荐", "count": await item_count([ServicePlanItemModel.item_status == "recommended"]), "route_path": "/miailove/service/vip", "query": {"item_status": "recommended"}},
                    {"key": "pending_meeting", "title": "待约见", "count": await item_count([ServicePlanItemModel.item_status == "pending_meeting"]), "route_path": "/miailove/service/vip", "query": {"item_status": "pending_meeting"}},
                    {"key": "pending_feedback", "title": "待反馈", "count": await item_count([ServicePlanItemModel.item_status == "pending_feedback"]), "priority": "warning", "route_path": "/miailove/service/vip", "query": {"item_status": "pending_feedback"}},
                    {"key": "completed", "title": "已完成", "count": await item_count([ServicePlanItemModel.item_status == "completed"]), "route_path": "/miailove/service/vip", "query": {"item_status": "completed"}},
                    {"key": "cancelled", "title": "已取消", "count": await item_count([ServicePlanItemModel.item_status.in_(["cancelled", "skipped"])]), "route_path": "/miailove/service/vip", "query": {"item_status": "cancelled"}},
                ],
            },
            {
                "key": "service_rights",
                "title": "推荐约见与权益",
                "nodes": [
                    {"key": "recommended", "title": "已推荐", "count": await cls._count_recommendations(auth, case_scope, [ServiceRecommendationModel.recommendation_status == "recommended"]), "route_path": "/miailove/service/vip", "query": {}},
                    {"key": "meeting_created", "title": "已转约见", "count": await cls._count_recommendations(auth, case_scope, [ServiceRecommendationModel.recommendation_status == "meeting_created"]), "route_path": "/miailove/service/vip", "query": {}},
                    {"key": "meeting_confirmed", "title": "约见确认", "count": await cls._count_meetings(auth, case_scope, [ServiceMeetingModel.meeting_status == "confirmed"]), "route_path": "/miailove/service/vip", "query": {}},
                    {"key": "feedback", "title": "待反馈", "count": await cls._count_meetings(auth, case_scope, [ServiceMeetingModel.meeting_status == "pending_feedback"]), "priority": "warning", "route_path": "/miailove/service/vip", "query": {}},
                    {"key": "overuse", "title": "已超额使用", "count": await cls._count_overuse(auth, case_scope), "priority": "danger", "route_path": "/miailove/service/vip", "query": {}},
                    {"key": "backup", "title": "我的备选", "count": await cls._count(auth, BackupPoolItemModel, [BackupPoolItemModel.is_deleted == False, BackupPoolItemModel.matchmaker_id == (auth.user.id if auth.user else -1)]), "route_path": "/miailove/service/candidate", "query": {}},
                ],
            },
        ]
