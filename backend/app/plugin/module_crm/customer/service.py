from datetime import date, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from app.api.v1.module_system.auth.schema import AuthSchema
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.user.model import UserModel
from app.core.exceptions import CustomException
from app.plugin.module_certification.model import CertificationItemModel
from app.plugin.module_crm.lead.model import (
    CrmLeadLifecycleModel,
    CrmLeadProcessRecordModel,
    CrmLeadProfileModel,
    CrmPersonModel,
)
from app.plugin.module_crm.preference.schema import PartnerPreferenceSaveSchema
from app.plugin.module_crm.preference.service import PartnerPreferenceService
from app.plugin.module_match.service import MatchProfileService
from app.plugin.module_profile_ai.service import PersonAiProfileService
from app.plugin.module_service.vip.model import ServiceCaseModel

from .model import (
    CrmCustomerCertificationMaterialModel,
    CrmCustomerLifecycleModel,
    CrmCustomerProcessRecordModel,
    CrmCustomerProfileModel,
)
from .schema import (
    PROCESS_TYPES,
    CustomerCertificationMaterialOutSchema,
    CustomerCertificationMaterialSaveSchema,
    CustomerDetailOutSchema,
    CustomerLifecycleOutSchema,
    CustomerOutSchema,
    CustomerPrintCardSchema,
    CustomerProcessCreateSchema,
    CustomerProcessOutSchema,
    CustomerQueryParam,
    CustomerReturnLeadSchema,
    CustomerTransferOwnerSchema,
    CustomerTransferStoreSchema,
    CustomerUpdateSchema,
    CustomerVisitConsultationSchema,
    CustomerVisitQueryParam,
)


class CustomerService:
    """客户管理服务层"""

    CERTIFICATION_ARCHIVE_EXTRA_ITEMS = [{"item_code": "id_card_photo", "item_name": "身份证照片", "sort": 0}]

    STAGE_ORDER = {
        "profiling": 1,
        "following": 2,
        "appointed": 3,
        "visited": 4,
        "consulted": 5,
        "signing": 6,
        "contracted": 7,
        "converted_vip": 8,
    }

    PROCESS_STAGE = {
        "follow": "following",
        "appointment": "appointed",
        "visit": "visited",
        "visit_checkin": "visited",
        "consultation": "consulted",
        "no_show": "appointed",
        "appointment_cancel": "appointed",
    }

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
    def _is_reception(cls, auth: AuthSchema) -> bool:
        return "RECEPTION" in cls._role_codes(auth)

    @classmethod
    def _is_matchmaker(cls, auth: AuthSchema) -> bool:
        return "MATCHMAKER" in cls._role_codes(auth)

    @classmethod
    def _is_owner_staff(cls, auth: AuthSchema) -> bool:
        return bool(cls._role_codes(auth) & {"SALES", "MATCHMAKER", "RECEPTION"})

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
    def _mask_wechat(cls, wechat: str | None) -> str | None:
        if not wechat:
            return wechat
        if len(wechat) <= 4:
            return "****"
        return f"{wechat[:2]}****{wechat[-2:]}"

    @classmethod
    def _mask_id_card(cls, id_card: str | None) -> str | None:
        if not id_card or len(id_card) < 8:
            return id_card
        return f"{id_card[:3]}***********{id_card[-4:]}"

    @classmethod
    def _age(cls, birth_date: date | None) -> int | None:
        if not birth_date:
            return None
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    @classmethod
    def _constellation(cls, birth_date: date | None) -> str | None:
        if not birth_date:
            return None
        boundaries = [
            ((1, 20), "水瓶座"),
            ((2, 19), "双鱼座"),
            ((3, 21), "白羊座"),
            ((4, 20), "金牛座"),
            ((5, 21), "双子座"),
            ((6, 22), "巨蟹座"),
            ((7, 23), "狮子座"),
            ((8, 23), "处女座"),
            ((9, 23), "天秤座"),
            ((10, 24), "天蝎座"),
            ((11, 23), "射手座"),
            ((12, 22), "摩羯座"),
        ]
        month_day = (birth_date.month, birth_date.day)
        for index, (boundary, _) in enumerate(boundaries):
            if month_day < boundary:
                return "摩羯座" if index == 0 else boundaries[index - 1][1]
        return "摩羯座"

    @classmethod
    def _zodiac(cls, birth_date: date | None) -> str | None:
        if not birth_date:
            return None
        animals = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
        return animals[(birth_date.year - 1900) % 12]

    @classmethod
    def _surname_name(cls, name: str | None, gender: str | None) -> str:
        if not name:
            return "嘉宾"
        suffix = {"0": "先生", "1": "女士"}.get(gender or "", "")
        return f"{name[0]}{suffix}" if suffix else name[0]

    @classmethod
    def _can_view_contact(cls, auth: AuthSchema, customer: CrmCustomerProfileModel) -> bool:
        if cls._is_brand_admin(auth):
            return True
        if cls._is_store_mgr(auth) and auth.user and customer.store_id == auth.user.dept_id:
            return True
        if cls._is_reception(auth) and auth.user and customer.store_id == auth.user.dept_id:
            return True
        return bool(auth.user and customer.owner_user_id == auth.user.id)

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
    def _can_view_id_card(cls, auth: AuthSchema, customer: CrmCustomerProfileModel) -> bool:
        if cls._is_brand_admin(auth):
            return True
        return bool(cls._is_store_mgr(auth) and auth.user and customer.store_id == auth.user.dept_id)

    @classmethod
    async def _user_names(cls, auth: AuthSchema, ids: set[int]) -> dict[int, str]:
        if not ids:
            return {}
        result = await auth.db.execute(select(UserModel.id, UserModel.name).where(UserModel.id.in_(ids)))
        return {row[0]: row[1] for row in result.all()}

    @classmethod
    async def _dept_names(cls, auth: AuthSchema, ids: set[int]) -> dict[int, str]:
        if not ids:
            return {}
        result = await auth.db.execute(select(DeptModel.id, DeptModel.name).where(DeptModel.id.in_(ids)))
        return {row[0]: row[1] for row in result.all()}

    @classmethod
    async def _write_lifecycle(
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
    async def _write_lead_lifecycle(
        cls,
        auth: AuthSchema,
        lead: CrmLeadProfileModel,
        operation_type: str,
        change_detail: dict[str, Any] | None = None,
        remark: str | None = None,
    ) -> None:
        record = CrmLeadLifecycleModel(
            brand_id=lead.brand_id,
            lead_id=lead.id,
            person_id=lead.person_id,
            operation_type=operation_type,
            operator_user_id=auth.user.id if auth.user else None,
            change_detail=change_detail,
            remark=remark,
        )
        cls._stamp_create(auth, record)
        auth.db.add(record)

    @classmethod
    def _scope_conditions(cls, auth: AuthSchema) -> list[Any]:
        conditions: list[Any] = [
            CrmCustomerProfileModel.is_deleted == False,
        ]
        if auth.user and cls._is_matchmaker(auth):
            conditions.append(or_(CrmCustomerProfileModel.ended_at.is_(None), CrmCustomerProfileModel.id.in_(cls._served_customer_ids(auth))))
        else:
            conditions.append(CrmCustomerProfileModel.ended_at.is_(None))
        if cls._is_brand_admin(auth):
            return conditions
        if not auth.user:
            conditions.append(CrmCustomerProfileModel.id == -1)
            return conditions
        if cls._is_store_mgr(auth) or cls._is_reception(auth):
            conditions.append(CrmCustomerProfileModel.store_id == (auth.user.dept_id or -1))
            return conditions
        if cls._is_matchmaker(auth):
            conditions.append(or_(CrmCustomerProfileModel.owner_user_id == auth.user.id, CrmCustomerProfileModel.id.in_(cls._served_customer_ids(auth))))
        else:
            conditions.append(CrmCustomerProfileModel.owner_user_id == auth.user.id)
        return conditions

    @classmethod
    def _deal_scope_conditions(cls, auth: AuthSchema) -> list[Any]:
        conditions: list[Any] = [
            CrmCustomerProfileModel.is_deleted == False,
            CrmCustomerProfileModel.converted_vip_at.is_not(None),
        ]
        if cls._is_brand_admin(auth):
            return conditions
        if not auth.user:
            conditions.append(CrmCustomerProfileModel.id == -1)
            return conditions
        if cls._is_store_mgr(auth) or cls._is_reception(auth):
            conditions.append(CrmCustomerProfileModel.store_id == (auth.user.dept_id or -1))
            return conditions
        if cls._is_matchmaker(auth):
            conditions.append(or_(CrmCustomerProfileModel.owner_user_id == auth.user.id, CrmCustomerProfileModel.id.in_(cls._served_customer_ids(auth))))
        else:
            conditions.append(CrmCustomerProfileModel.owner_user_id == auth.user.id)
        return conditions

    @classmethod
    async def _validate_owner_in_store(cls, auth: AuthSchema, store_id: int, owner_user_id: int) -> None:
        result = await auth.db.execute(
            select(UserModel).where(UserModel.id == owner_user_id, UserModel.is_deleted == False)
        )
        user = result.scalars().first()
        if not user:
            raise CustomException(msg="归属人不存在")
        if user.dept_id != store_id:
            raise CustomException(msg="归属人不属于目标门店")

    @classmethod
    async def _ensure_access(cls, auth: AuthSchema, customer: CrmCustomerProfileModel, action: str = "read") -> None:
        if cls._is_brand_admin(auth):
            return
        user = auth.user
        if not user:
            raise CustomException(msg="无权限访问该客户", code=10403, status_code=403)
        same_store = customer.store_id == user.dept_id
        is_owner = customer.owner_user_id == user.id
        is_serving_customer = await cls._is_serving_customer(auth, customer.id)
        if action == "read" and is_serving_customer:
            return
        if action in {"update", "follow", "appointment", "visit_checkin", "consultation", "no_show", "appointment_cancel"} and is_serving_customer:
            return
        if action == "read" and ((cls._is_store_mgr(auth) or cls._is_reception(auth)) and same_store or is_owner):
            return
        if action in {"update", "return_lead"} and (is_owner or (cls._is_store_mgr(auth) and same_store)):
            return
        if action in {"follow", "appointment", "visit_checkin", "consultation", "no_show", "appointment_cancel"}:
            if is_owner or (cls._is_store_mgr(auth) and same_store):
                return
            if cls._is_reception(auth) and same_store and action in {"visit_checkin", "consultation", "no_show", "appointment_cancel"}:
                return
        if action == "transfer_owner" and (is_owner or (cls._is_store_mgr(auth) and same_store)):
            return
        if action == "transfer_store" and cls._is_store_mgr(auth) and same_store:
            return
        raise CustomException(msg="无权限操作该客户", code=10403, status_code=403)

    @classmethod
    async def _get_customer(cls, auth: AuthSchema, id: int, action: str = "read") -> CrmCustomerProfileModel:
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
        await cls._ensure_access(auth, customer, action)
        return customer

    @classmethod
    def _advance_stage(cls, customer: CrmCustomerProfileModel, stage: str) -> None:
        customer.current_stage = stage
        if cls.STAGE_ORDER.get(stage, 0) > cls.STAGE_ORDER.get(customer.max_stage, 0):
            customer.max_stage = stage

    @classmethod
    async def _certification_archive_items(cls, auth: AuthSchema) -> list[dict[str, Any]]:
        rows = (
            await auth.db.execute(
                select(CertificationItemModel).where(
                    CertificationItemModel.is_deleted == False,
                    CertificationItemModel.status == "0",
                ).order_by(CertificationItemModel.sort.asc(), CertificationItemModel.id.asc())
            )
        ).scalars().all()
        result = [*cls.CERTIFICATION_ARCHIVE_EXTRA_ITEMS]
        result.extend(
            {
                "item_code": row.item_code,
                "item_name": row.item_name,
                "sort": row.sort,
                "material_required": row.material_required,
                "material_desc": row.material_desc,
            }
            for row in rows
            if row.material_required
        )
        return result

    @classmethod
    async def _certification_archive_materials(cls, auth: AuthSchema, customer_id: int) -> list[dict[str, Any]]:
        rows = (
            await auth.db.execute(
                select(CrmCustomerCertificationMaterialModel)
                .where(
                    CrmCustomerCertificationMaterialModel.customer_id == customer_id,
                    CrmCustomerCertificationMaterialModel.is_deleted == False,
                )
                .order_by(CrmCustomerCertificationMaterialModel.id.desc())
            )
        ).scalars().all()
        return [CustomerCertificationMaterialOutSchema.model_validate(row).model_dump() for row in rows]

    @classmethod
    async def _get_customer_process(
        cls,
        auth: AuthSchema,
        process_id: int,
        action: str,
    ) -> CrmCustomerProcessRecordModel:
        result = await auth.db.execute(
            select(CrmCustomerProcessRecordModel).where(
                CrmCustomerProcessRecordModel.id == process_id,
                CrmCustomerProcessRecordModel.is_deleted == False,
            )
        )
        record = result.scalars().first()
        if not record:
            raise CustomException(msg="预约记录不存在")
        await cls._get_customer(auth, record.customer_id, action)
        if cls._is_matchmaker(auth) and auth.user and record.operator_user_id != auth.user.id:
            raise CustomException(msg="服务红娘只能操作自己发起的邀约", code=10403, status_code=403)
        if record.record_type != "appointment":
            raise CustomException(msg="只能操作邀约记录")
        return record

    @classmethod
    async def _decorate_list(cls, auth: AuthSchema, customers: list[CrmCustomerProfileModel]) -> list[dict]:
        user_names = await cls._user_names(auth, {row.owner_user_id for row in customers if row.owner_user_id})
        dept_names = await cls._dept_names(auth, {row.store_id for row in customers if row.store_id})
        ai_profile_map = await PersonAiProfileService.admin_info_map(auth.db, {row.person_id for row in customers})
        preference_map = await PartnerPreferenceService.map_current(auth.db, {row.person_id for row in customers})
        served_ids: set[int] = set()
        if auth.user and cls._is_matchmaker(auth) and customers:
            served_result = await auth.db.execute(
                select(ServiceCaseModel.customer_id).where(
                    ServiceCaseModel.customer_id.in_({row.id for row in customers}),
                    ServiceCaseModel.owner_matchmaker_id == auth.user.id,
                    ServiceCaseModel.is_deleted == False,
                    ServiceCaseModel.case_status.in_({"serving", "reopened", "pending_close_review"}),
                )
            )
            served_ids = set(served_result.scalars().all())
        data = []
        for customer in customers:
            item = CustomerOutSchema.model_validate(customer).model_dump()
            can_view_contact = cls._can_view_contact(auth, customer) or customer.id in served_ids
            can_view_id_card = cls._can_view_id_card(auth, customer)
            item["can_view_contact"] = can_view_contact
            item["can_view_id_card"] = can_view_id_card
            item["mobile_masked"] = (
                customer.person.primary_mobile if can_view_contact else cls._mask_mobile(customer.person.primary_mobile)
            )
            item["wechat_masked"] = customer.person.wechat if can_view_contact else cls._mask_wechat(customer.person.wechat)
            item["id_card_no_masked"] = (
                customer.person.id_card_no if can_view_id_card else cls._mask_id_card(customer.person.id_card_no)
            )
            if not can_view_contact:
                item["person"]["primary_mobile"] = item["mobile_masked"]
                item["person"]["wechat"] = item["wechat_masked"]
            if not can_view_id_card:
                item["person"]["id_card_no"] = item["id_card_no_masked"]
            item["store"] = {"id": customer.store_id, "name": dept_names.get(customer.store_id)} if customer.store_id else None
            item["owner_user"] = (
                {"id": customer.owner_user_id, "name": user_names.get(customer.owner_user_id)}
                if customer.owner_user_id
                else None
            )
            item["age"] = cls._age(customer.person.birth_date)
            item["constellation"] = cls._constellation(customer.person.birth_date)
            item["zodiac"] = cls._zodiac(customer.person.birth_date)
            item["ai_profile"] = ai_profile_map.get(customer.person_id, {"profile": None, "latest_task": None})
            item["partner_preference"] = preference_map.get(customer.person_id)
            data.append(item)
        return data

    @classmethod
    async def page_service(
        cls,
        auth: AuthSchema,
        page_no: int,
        page_size: int,
        search: CustomerQueryParam | None = None,
    ) -> dict:
        conditions = cls._scope_conditions(auth)
        return await cls._page_with_conditions(auth=auth, page_no=page_no, page_size=page_size, search=search, conditions=conditions)

    @classmethod
    async def deal_page_service(
        cls,
        auth: AuthSchema,
        page_no: int,
        page_size: int,
        search: CustomerQueryParam | None = None,
    ) -> dict:
        conditions = cls._deal_scope_conditions(auth)
        return await cls._page_with_conditions(auth=auth, page_no=page_no, page_size=page_size, search=search, conditions=conditions)

    @classmethod
    async def _page_with_conditions(
        cls,
        auth: AuthSchema,
        page_no: int,
        page_size: int,
        search: CustomerQueryParam | None,
        conditions: list[Any],
    ) -> dict:
        if search:
            if search.keyword:
                conditions.append(
                    or_(
                        CrmPersonModel.display_no.like(f"%{search.keyword}%"),
                        CrmPersonModel.name.like(f"%{search.keyword}%"),
                        CrmPersonModel.primary_mobile.like(f"%{search.keyword}%"),
                    )
                )
            if search.current_stage:
                conditions.append(CrmCustomerProfileModel.current_stage == search.current_stage)
            if search.max_stage:
                conditions.append(CrmCustomerProfileModel.max_stage == search.max_stage)
            if search.gender:
                conditions.append(CrmPersonModel.gender == search.gender)
            if search.education:
                conditions.append(CrmPersonModel.education == search.education)
            if search.marital_status:
                conditions.append(CrmPersonModel.marital_status == search.marital_status)
            if search.store_id:
                conditions.append(CrmCustomerProfileModel.store_id == search.store_id)
            if search.owner_user_id:
                conditions.append(CrmCustomerProfileModel.owner_user_id == search.owner_user_id)
            if search.latest_follow_time and len(search.latest_follow_time) == 2:
                conditions.append(
                    CrmCustomerProfileModel.latest_follow_at.between(
                        search.latest_follow_time[0], search.latest_follow_time[1]
                    )
                )
            if search.next_follow_time and len(search.next_follow_time) == 2:
                conditions.append(
                    CrmCustomerProfileModel.next_follow_at.between(
                        search.next_follow_time[0], search.next_follow_time[1]
                    )
                )
            if search.created_time and len(search.created_time) == 2:
                conditions.append(
                    CrmCustomerProfileModel.created_time.between(search.created_time[0], search.created_time[1])
                )
            if search.age_min or search.age_max:
                year = date.today().year
                if search.age_min:
                    conditions.append(CrmPersonModel.birth_date <= date(year - search.age_min, date.today().month, date.today().day))
                if search.age_max:
                    conditions.append(CrmPersonModel.birth_date >= date(year - search.age_max - 1, date.today().month, date.today().day))
        total_result = await auth.db.execute(
            select(func.count(CrmCustomerProfileModel.id))
            .join(CrmPersonModel, CrmCustomerProfileModel.person_id == CrmPersonModel.id)
            .where(and_(*conditions))
        )
        rows_result = await auth.db.execute(
            select(CrmCustomerProfileModel)
            .join(CrmPersonModel, CrmCustomerProfileModel.person_id == CrmPersonModel.id)
            .where(and_(*conditions))
            .options(selectinload(CrmCustomerProfileModel.person))
            .order_by(CrmCustomerProfileModel.updated_time.desc(), CrmCustomerProfileModel.id.desc())
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        total = total_result.scalar() or 0
        items = await cls._decorate_list(auth, list(rows_result.scalars().all()))
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": items,
        }

    @classmethod
    async def detail_service(cls, auth: AuthSchema, id: int) -> dict:
        customer = await cls._get_customer(auth, id)
        data = (await cls._decorate_list(auth, [customer]))[0]
        process_result = await auth.db.execute(
            select(CrmCustomerProcessRecordModel)
            .where(
                CrmCustomerProcessRecordModel.customer_id == id,
                CrmCustomerProcessRecordModel.is_deleted == False,
            )
            .order_by(CrmCustomerProcessRecordModel.occurred_at.desc(), CrmCustomerProcessRecordModel.id.desc())
        )
        process_rows = list(process_result.scalars().all())
        lifecycle_result = await auth.db.execute(
            select(CrmCustomerLifecycleModel)
            .where(
                CrmCustomerLifecycleModel.customer_id == id,
                CrmCustomerLifecycleModel.is_deleted == False,
                CrmCustomerLifecycleModel.operation_type.notin_(PROCESS_TYPES),
            )
            .order_by(CrmCustomerLifecycleModel.created_time.desc(), CrmCustomerLifecycleModel.id.desc())
        )
        lifecycle_rows = list(lifecycle_result.scalars().all())
        lead_process_records: list[dict] = []
        lead_lifecycle_records: list[dict] = []
        if customer.lead_id:
            lead_process_result = await auth.db.execute(
                select(CrmLeadProcessRecordModel)
                .where(
                    CrmLeadProcessRecordModel.lead_id == customer.lead_id,
                    CrmLeadProcessRecordModel.is_deleted == False,
                )
                .order_by(CrmLeadProcessRecordModel.created_time.desc(), CrmLeadProcessRecordModel.id.desc())
            )
            lead_process_rows = list(lead_process_result.scalars().all())
            lead_lifecycle_result = await auth.db.execute(
                select(CrmLeadLifecycleModel)
                .where(
                    CrmLeadLifecycleModel.lead_id == customer.lead_id,
                    CrmLeadLifecycleModel.is_deleted == False,
                    CrmLeadLifecycleModel.operation_type != "follow",
                )
                .order_by(CrmLeadLifecycleModel.created_time.desc(), CrmLeadLifecycleModel.id.desc())
            )
            lead_lifecycle_rows = list(lead_lifecycle_result.scalars().all())
            operator_names = await cls._user_names(
                auth,
                {
                    user_id
                    for row in [*process_rows, *lifecycle_rows, *lead_process_rows, *lead_lifecycle_rows]
                    for user_id in [getattr(row, "operator_user_id", None), getattr(row, "checked_in_user_id", None)]
                    if user_id
                },
            )
            lead_process_records = [
                {
                    "id": row.id,
                    "record_type": row.action_type,
                    "occurred_at": row.created_time,
                    "method": row.follow_method,
                    "result": None,
                    "content": row.content,
                    "next_follow_at": row.next_follow_at,
                    "operator_user_id": row.operator_user_id,
                    "operator_user_name": operator_names.get(row.operator_user_id or 0),
                    "created_time": row.created_time,
                    "source": "lead",
                }
                for row in lead_process_rows
            ]
            lead_lifecycle_records = [
                {
                    "id": row.id,
                    "operation_type": row.operation_type,
                    "operator_user_id": row.operator_user_id,
                    "operator_user_name": operator_names.get(row.operator_user_id or 0),
                    "change_detail": row.change_detail,
                    "remark": row.remark,
                    "created_time": row.created_time,
                    "source": "lead",
                }
                for row in lead_lifecycle_rows
            ]
        else:
            operator_names = await cls._user_names(
                auth,
                {
                    user_id
                    for row in [*process_rows, *lifecycle_rows]
                    for user_id in [getattr(row, "operator_user_id", None), getattr(row, "checked_in_user_id", None)]
                    if user_id
                },
            )
        data["process_records"] = []
        for row in process_rows:
            item = CustomerProcessOutSchema.model_validate(row).model_dump()
            item["operator_user_name"] = operator_names.get(row.operator_user_id or 0)
            item["checked_in_user_name"] = operator_names.get(row.checked_in_user_id or 0)
            item["source"] = "customer"
            data["process_records"].append(item)
        data["lead_process_records"] = lead_process_records
        data["lifecycle_records"] = []
        for row in lifecycle_rows:
            item = CustomerLifecycleOutSchema.model_validate(row).model_dump()
            item["operator_user_name"] = operator_names.get(row.operator_user_id or 0)
            item["source"] = "customer"
            data["lifecycle_records"].append(item)
        data["lead_lifecycle_records"] = lead_lifecycle_records
        data["partner_preference_versions"] = await PartnerPreferenceService.versions_out(auth.db, customer.person_id, 10)
        data["certification"] = {
            "certification_level": customer.person.certification_level,
            "certification_summary": customer.person.certification_summary,
            "id_card_no_masked": data["id_card_no_masked"],
            "archive_items": await cls._certification_archive_items(auth),
            "archive_materials": await cls._certification_archive_materials(auth, customer.id),
        }
        return CustomerDetailOutSchema.model_validate(data).model_dump()

    @classmethod
    async def save_certification_material_service(
        cls,
        auth: AuthSchema,
        customer_id: int,
        data: CustomerCertificationMaterialSaveSchema,
    ) -> dict:
        customer = await cls._get_customer(auth, customer_id, "update")
        items = await cls._certification_archive_items(auth)
        item_name = data.item_name or next(
            (item["item_name"] for item in items if item["item_code"] == data.item_code),
            data.item_code,
        )
        material = CrmCustomerCertificationMaterialModel(
            brand_id=customer.brand_id,
            customer_id=customer.id,
            person_id=customer.person_id,
            item_code=data.item_code,
            item_name=item_name,
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
        return CustomerCertificationMaterialOutSchema.model_validate(material).model_dump()

    @classmethod
    async def delete_certification_material_service(cls, auth: AuthSchema, material_id: int) -> None:
        result = await auth.db.execute(
            select(CrmCustomerCertificationMaterialModel).where(
                CrmCustomerCertificationMaterialModel.id == material_id,
                CrmCustomerCertificationMaterialModel.is_deleted == False,
            )
        )
        material = result.scalars().first()
        if not material:
            raise CustomException(msg="认证资料不存在")
        await cls._get_customer(auth, material.customer_id, "update")
        material.is_deleted = True
        material.deleted_time = datetime.now()
        if auth.user and hasattr(material, "deleted_id"):
            material.deleted_id = auth.user.id
        cls._stamp_update(auth, material)
        await auth.db.flush()

    @classmethod
    async def create_from_lead_service(cls, auth: AuthSchema, lead_id: int, remark: str | None = None) -> dict:
        result = await auth.db.execute(
            select(CrmLeadProfileModel)
            .where(CrmLeadProfileModel.id == lead_id, CrmLeadProfileModel.is_deleted == False)
            .options(selectinload(CrmLeadProfileModel.person))
        )
        lead = result.scalars().first()
        if not lead:
            raise CustomException(msg="线索不存在")
        if lead.lead_type == "converted_customer":
            raise CustomException(msg="线索已转建档客户")
        if not auth.user:
            raise CustomException(msg="当前用户无效", code=10403, status_code=403)
        if not (cls._is_brand_admin(auth) or cls._is_store_mgr(auth) or lead.owner_sales_id == auth.user.id):
            raise CustomException(msg="无权限转建档客户", code=10403, status_code=403)
        store_id = lead.store_id or auth.user.dept_id
        if not store_id:
            raise CustomException(msg="线索未归属门店，无法转建档客户")
        owner_user_id = auth.user.id
        active_result = await auth.db.execute(
            select(CrmCustomerProfileModel.id).where(
                CrmCustomerProfileModel.person_id == lead.person_id,
                CrmCustomerProfileModel.ended_at.is_(None),
                CrmCustomerProfileModel.is_deleted == False,
            )
        )
        if active_result.scalar():
            raise CustomException(msg="该人员已有当前客户档案")
        customer = CrmCustomerProfileModel(
            brand_id=lead.brand_id,
            person_id=lead.person_id,
            lead_id=lead.id,
            store_id=store_id,
            owner_user_id=owner_user_id,
            current_stage="profiling",
            max_stage="profiling",
            description=remark or lead.description,
        )
        cls._stamp_create(auth, customer)
        auth.db.add(customer)
        await auth.db.flush()
        old = {"pool_type": lead.pool_type, "lead_type": lead.lead_type, "owner_sales_id": lead.owner_sales_id}
        lead.lead_type = "converted_customer"
        lead.converted_customer_at = datetime.now()
        lead.latest_follow_at = lead.converted_customer_at
        cls._stamp_update(auth, lead)
        await cls._write_lifecycle(
            auth,
            customer,
            "create_from_lead",
            {"lead_id": lead.id, "store_id": store_id, "owner_user_id": owner_user_id},
            remark or "线索转建档客户",
        )
        await cls._write_lead_lifecycle(
            auth,
            lead,
            "convert_customer",
            {"from": old, "to": {"lead_type": "converted_customer", "customer_id": customer.id}},
            remark or "线索转建档客户",
        )
        await auth.db.flush()
        await auth.db.refresh(customer)
        return (await cls._decorate_list(auth, [customer]))[0]

    @classmethod
    async def update_service(cls, auth: AuthSchema, id: int, data: CustomerUpdateSchema) -> dict:
        customer = await cls._get_customer(auth, id, "update")
        if customer.ended_at:
            raise CustomException(msg="客户已离开客户阶段，不能编辑")
        old = {
            "mobile": customer.person.primary_mobile,
            "name": customer.person.name,
            "gender": customer.person.gender,
            "wechat": customer.person.wechat,
            "birth_date": customer.person.birth_date,
            "height_cm": customer.person.height_cm,
            "weight_kg": customer.person.weight_kg,
            "ethnicity": customer.person.ethnicity,
            "occupation": customer.person.occupation,
            "occupation_code": customer.person.occupation_code,
            "annual_income": customer.person.annual_income,
            "marital_status": customer.person.marital_status,
            "education": customer.person.education,
            "graduated_school": customer.person.graduated_school,
            "major": customer.person.major,
            "unit_type": customer.person.unit_type,
            "job_title": customer.person.job_title,
            "work_company": customer.person.work_company,
            "hometown": customer.person.hometown,
            "residence": customer.person.residence,
            "house_status": customer.person.house_status,
            "car_status": customer.person.car_status,
            "accept_long_distance_self": customer.person.accept_long_distance_self,
            "accept_flash_marriage": customer.person.accept_flash_marriage,
            "willing_relocate": customer.person.willing_relocate,
            "marriage_plan": customer.person.marriage_plan,
            "family_background": customer.person.family_background,
            "profile_remark": customer.person.profile_remark,
            "photo_urls": customer.person.photo_urls or [],
            "profile_intro": customer.person.profile_intro,
            "id_card_no": customer.person.id_card_no,
            "current_stage": customer.current_stage,
            "next_follow_at": customer.next_follow_at,
            "description": customer.description,
        }
        if data.mobile != customer.person.primary_mobile:
            raise CustomException(msg="手机号不允许编辑")
        person_fields = data.model_dump(
            exclude={"partner_preference", "current_stage", "next_follow_at", "description"}
        )
        for field, value in person_fields.items():
            target = "primary_mobile" if field == "mobile" else field
            setattr(customer.person, target, value)
        if data.current_stage:
            cls._advance_stage(customer, data.current_stage)
        customer.next_follow_at = data.next_follow_at
        customer.description = data.description
        changes = {}
        new = data.model_dump(exclude={"partner_preference"})
        for field, value in new.items():
            if old.get(field) != value:
                changes[field] = {"from": old.get(field), "to": value}
        if data.partner_preference is not None:
            await PartnerPreferenceService.save(
                auth.db,
                customer.person_id,
                PartnerPreferenceSaveSchema(
                    **data.partner_preference.model_dump(), source_type="customer", source_id=str(customer.id)
                ),
                auth=auth,
            )
            changes["partner_preference"] = "已更新"
        cls._stamp_update(auth, customer.person)
        cls._stamp_update(auth, customer)
        if changes:
            await cls._write_lifecycle(auth, customer, "edit", changes, data.description)
            await PersonAiProfileService.enqueue_miai_impression(
                db=auth.db,
                person_id=customer.person_id,
                source_type="admin_update",
                source_id=customer.id,
            )
            await MatchProfileService.mark_dirty(
                db=auth.db,
                person_id=customer.person_id,
                dirty_parts=["self_profile", "preference"],
                source_type="admin_customer_update",
                source_id=customer.id,
            )
        await auth.db.flush()
        await auth.db.refresh(customer)
        return (await cls._decorate_list(auth, [customer]))[0]

    @classmethod
    async def process_service(
        cls,
        auth: AuthSchema,
        customer_id: int,
        record_type: str,
        data: CustomerProcessCreateSchema,
    ) -> dict:
        if record_type == "follow" and data.method in {"appointment", "consultation"}:
            record_type = data.method
        if record_type in {"appointment", "visit"}:
            record_type = "appointment" if record_type == "appointment" else "visit_checkin"
        if record_type not in PROCESS_TYPES:
            raise CustomException(msg="过程记录类型不正确")
        customer = await cls._get_customer(auth, customer_id, record_type)
        if customer.ended_at:
            raise CustomException(msg="客户已离开客户阶段，不能新增过程记录")
        if record_type == "appointment" and not data.scheduled_at:
            raise CustomException(msg="邀约必须填写预约时间")
        record = CrmCustomerProcessRecordModel(
            brand_id=customer.brand_id,
            customer_id=customer.id,
            person_id=customer.person_id,
            record_type=record_type,
            occurred_at=datetime.now(),
            method=data.method or record_type,
            result=data.result,
            content=data.content,
            next_follow_at=data.next_follow_at,
            scheduled_at=data.scheduled_at,
            appointment_slot=data.appointment_slot,
            visit_purpose=data.visit_purpose,
            promised_gift=data.promised_gift,
            appointment_status="pending" if record_type == "appointment" else None,
            need_summary=data.need_summary,
            budget_range=data.budget_range,
            main_objection=data.main_objection,
            intention_level=data.intention_level,
            next_action=data.next_action,
            enter_signing=data.enter_signing,
            operator_user_id=auth.user.id if auth.user else None,
        )
        cls._stamp_create(auth, record)
        auth.db.add(record)
        stage = "signing" if record_type == "consultation" and data.enter_signing else cls.PROCESS_STAGE[record_type]
        cls._advance_stage(customer, stage)
        customer.latest_follow_at = record.occurred_at
        customer.next_follow_at = data.next_follow_at
        cls._stamp_update(auth, customer)
        await auth.db.flush()
        await auth.db.refresh(record)
        return CustomerProcessOutSchema.model_validate(record).model_dump()

    @classmethod
    def _visit_scope_conditions(cls, auth: AuthSchema) -> list[Any]:
        conditions: list[Any] = [
            CrmCustomerProcessRecordModel.is_deleted == False,
            CrmCustomerProcessRecordModel.record_type == "appointment",
        ]
        if cls._is_brand_admin(auth):
            return conditions
        if not auth.user:
            conditions.append(CrmCustomerProcessRecordModel.id == -1)
            return conditions
        if cls._is_store_mgr(auth) or cls._is_reception(auth):
            conditions.append(CrmCustomerProfileModel.store_id == (auth.user.dept_id or -1))
            return conditions
        conditions.append(
            or_(
                CrmCustomerProfileModel.owner_user_id == auth.user.id,
                CrmCustomerProcessRecordModel.operator_user_id == auth.user.id,
            )
        )
        return conditions

    @classmethod
    async def visit_page_service(
        cls,
        auth: AuthSchema,
        page_no: int,
        page_size: int,
        search: CustomerVisitQueryParam | None = None,
    ) -> dict:
        conditions = cls._visit_scope_conditions(auth)
        if search:
            if search.keyword:
                conditions.append(
                    or_(
                        CrmPersonModel.display_no.like(f"%{search.keyword}%"),
                        CrmPersonModel.name.like(f"%{search.keyword}%"),
                        CrmPersonModel.primary_mobile.like(f"%{search.keyword}%"),
                    )
                )
            if search.scheduled_time and len(search.scheduled_time) == 2:
                conditions.append(
                    CrmCustomerProcessRecordModel.scheduled_at.between(
                        search.scheduled_time[0], search.scheduled_time[1]
                    )
                )
            if search.appointment_slot:
                conditions.append(CrmCustomerProcessRecordModel.appointment_slot == search.appointment_slot)
            if search.visit_purpose:
                conditions.append(CrmCustomerProcessRecordModel.visit_purpose == search.visit_purpose)
            if search.appointment_status:
                conditions.append(CrmCustomerProcessRecordModel.appointment_status == search.appointment_status)
            if search.operator_user_id:
                conditions.append(CrmCustomerProcessRecordModel.operator_user_id == search.operator_user_id)
            if search.store_id:
                conditions.append(CrmCustomerProfileModel.store_id == search.store_id)
        total_result = await auth.db.execute(
            select(func.count(CrmCustomerProcessRecordModel.id))
            .join(CrmCustomerProfileModel, CrmCustomerProcessRecordModel.customer_id == CrmCustomerProfileModel.id)
            .join(CrmPersonModel, CrmCustomerProcessRecordModel.person_id == CrmPersonModel.id)
            .where(and_(*conditions))
        )
        rows_result = await auth.db.execute(
            select(CrmCustomerProcessRecordModel, CrmCustomerProfileModel, CrmPersonModel)
            .join(CrmCustomerProfileModel, CrmCustomerProcessRecordModel.customer_id == CrmCustomerProfileModel.id)
            .join(CrmPersonModel, CrmCustomerProcessRecordModel.person_id == CrmPersonModel.id)
            .where(and_(*conditions))
            .order_by(
                CrmCustomerProcessRecordModel.scheduled_at.asc(),
                CrmCustomerProcessRecordModel.id.desc(),
            )
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        rows = rows_result.all()
        user_ids = {
            user_id
            for record, customer, _ in rows
            for user_id in [record.operator_user_id, record.checked_in_user_id, customer.owner_user_id]
            if user_id
        }
        user_names = await cls._user_names(auth, user_ids)
        service_cases = []
        if rows:
            service_cases = (
                await auth.db.execute(
                    select(ServiceCaseModel.customer_id, ServiceCaseModel.owner_matchmaker_id).where(
                        ServiceCaseModel.customer_id.in_({customer.id for _, customer, _ in rows}),
                        ServiceCaseModel.is_deleted == False,
                        ServiceCaseModel.case_status.in_({"serving", "reopened", "pending_close_review"}),
                    )
                )
            ).all()
        service_owner_by_customer = {customer_id: owner_id for customer_id, owner_id in service_cases if owner_id}
        items = []
        for record, customer, person in rows:
            appointment_source = "service" if service_owner_by_customer.get(customer.id) == record.operator_user_id else "sales"
            can_view = cls._can_view_contact(auth, customer) or (appointment_source == "service" and auth.user and record.operator_user_id == auth.user.id)
            items.append(
                {
                    **CustomerProcessOutSchema.model_validate(record).model_dump(),
                    "operator_user_name": user_names.get(record.operator_user_id or 0),
                    "checked_in_user_name": user_names.get(record.checked_in_user_id or 0),
                    "appointment_source": appointment_source,
                    "customer": {
                        "id": customer.id,
                        "current_stage": customer.current_stage,
                        "store_id": customer.store_id,
                        "owner_user_id": customer.owner_user_id,
                        "owner_user_name": user_names.get(customer.owner_user_id),
                    },
                    "person": {
                        "id": person.id,
                        "display_no": person.display_no,
                        "name": person.name,
                        "gender": person.gender,
                        "primary_mobile": person.primary_mobile if can_view else cls._mask_mobile(person.primary_mobile),
                    },
                }
            )
        total = total_result.scalar() or 0
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": items,
        }

    @classmethod
    async def visit_status_service(
        cls,
        auth: AuthSchema,
        process_id: int,
        action: str,
        data: CustomerVisitConsultationSchema | None = None,
    ) -> dict:
        status_map = {
            "visit_checkin": "checked_in",
            "no_show": "no_show",
            "appointment_cancel": "cancelled",
            "consultation": "consulted",
        }
        if action not in status_map:
            raise CustomException(msg="到店操作不正确")
        appointment = await cls._get_customer_process(auth, process_id, action)
        customer = await cls._get_customer(auth, appointment.customer_id, action)
        now = datetime.now()
        if action == "consultation" and data is None:
            raise CustomException(msg="面谈内容不能为空")
        current_status = appointment.appointment_status or "pending"
        if action in {"visit_checkin", "no_show", "appointment_cancel"} and current_status != "pending":
            raise CustomException(msg="当前预约状态不能执行该操作")
        if action == "consultation" and current_status not in {"pending", "checked_in"}:
            raise CustomException(msg="当前预约状态不能记录面谈")
        appointment.appointment_status = status_map[action]
        if action == "visit_checkin":
            appointment.checked_in_at = now
            appointment.checked_in_user_id = auth.user.id if auth.user else None
        if action == "consultation":
            cls._advance_stage(customer, "signing" if data and data.enter_signing else "consulted")
        elif action == "visit_checkin":
            cls._advance_stage(customer, "visited")
        content_map = {
            "visit_checkin": "登记到店",
            "no_show": "标记爽约",
            "appointment_cancel": "取消预约",
        }
        record = CrmCustomerProcessRecordModel(
            brand_id=appointment.brand_id,
            customer_id=appointment.customer_id,
            person_id=appointment.person_id,
            record_type=action,
            occurred_at=now,
            method=action,
            result=status_map[action],
            content=data.content if data else content_map[action],
            next_follow_at=data.next_follow_at if data else None,
            scheduled_at=appointment.scheduled_at,
            appointment_slot=appointment.appointment_slot,
            visit_purpose=appointment.visit_purpose,
            promised_gift=appointment.promised_gift,
            appointment_status=status_map[action],
            need_summary=data.need_summary if data else None,
            budget_range=data.budget_range if data else None,
            main_objection=data.main_objection if data else None,
            intention_level=data.intention_level if data else None,
            enter_signing=data.enter_signing if data else False,
            operator_user_id=auth.user.id if auth.user else None,
        )
        cls._stamp_create(auth, record)
        auth.db.add(record)
        customer.latest_follow_at = now
        customer.next_follow_at = data.next_follow_at if data else customer.next_follow_at
        cls._stamp_update(auth, appointment)
        cls._stamp_update(auth, customer)
        await auth.db.flush()
        await auth.db.refresh(record)
        return CustomerProcessOutSchema.model_validate(record).model_dump()

    @classmethod
    async def transfer_owner_service(cls, auth: AuthSchema, data: CustomerTransferOwnerSchema) -> None:
        customer = await cls._get_customer(auth, data.customer_id, "transfer_owner")
        if customer.ended_at:
            raise CustomException(msg="客户已离开客户阶段，不能转派")
        await cls._validate_owner_in_store(auth, customer.store_id, data.owner_user_id)
        old_owner = customer.owner_user_id
        customer.owner_user_id = data.owner_user_id
        cls._stamp_update(auth, customer)
        await cls._write_lifecycle(
            auth,
            customer,
            "transfer_owner",
            {"from_owner_user_id": old_owner, "to_owner_user_id": data.owner_user_id},
            data.remark,
        )
        await auth.db.flush()

    @classmethod
    async def transfer_store_service(cls, auth: AuthSchema, data: CustomerTransferStoreSchema) -> None:
        customer = await cls._get_customer(auth, data.customer_id, "transfer_store")
        if customer.ended_at:
            raise CustomException(msg="客户已离开客户阶段，不能转交")
        await cls._validate_owner_in_store(auth, data.store_id, data.owner_user_id)
        old = {"store_id": customer.store_id, "owner_user_id": customer.owner_user_id}
        customer.store_id = data.store_id
        customer.owner_user_id = data.owner_user_id
        cls._stamp_update(auth, customer)
        await cls._write_lifecycle(
            auth,
            customer,
            "transfer_store",
            {"from": old, "to": {"store_id": data.store_id, "owner_user_id": data.owner_user_id}},
            data.remark,
        )
        await auth.db.flush()

    @classmethod
    async def return_lead_service(cls, auth: AuthSchema, id: int, data: CustomerReturnLeadSchema) -> None:
        customer = await cls._get_customer(auth, id, "return_lead")
        if customer.ended_at:
            raise CustomException(msg="客户已离开客户阶段")
        now = datetime.now()
        lead: CrmLeadProfileModel | None = None
        if customer.lead_id:
            result = await auth.db.execute(
                select(CrmLeadProfileModel).where(
                    CrmLeadProfileModel.id == customer.lead_id,
                    CrmLeadProfileModel.is_deleted == False,
                )
            )
            lead = result.scalars().first()
        if not lead:
            lead = CrmLeadProfileModel(
                brand_id=customer.brand_id,
                person_id=customer.person_id,
                store_id=customer.store_id,
                owner_sales_id=None,
                pool_type="store_pool",
                lead_type="second_hand",
                assigned_at=None,
                latest_follow_at=now,
                description=data.reason,
            )
            cls._stamp_create(auth, lead)
            auth.db.add(lead)
            await auth.db.flush()
        else:
            lead.store_id = customer.store_id
            lead.owner_sales_id = None
            lead.pool_type = "store_pool"
            lead.lead_type = "second_hand"
            lead.latest_follow_at = now
            lead.next_follow_at = None
            lead.assigned_at = None
            cls._stamp_update(auth, lead)
        customer.ended_at = now
        customer.end_reason = "returned_lead"
        customer.returned_lead_id = lead.id
        cls._stamp_update(auth, customer)
        await cls._write_lifecycle(
            auth,
            customer,
            "return_lead",
            {"lead_id": lead.id, "reason_type": data.reason_type},
            data.reason,
        )
        await cls._write_lead_lifecycle(
            auth,
            lead,
            "customer_return",
            {
                "customer_id": customer.id,
                "to_pool": "store_pool",
                "lead_type": "second_hand",
                "reason_type": data.reason_type,
            },
            data.reason,
        )
        await auth.db.flush()

    @classmethod
    async def print_card_service(cls, auth: AuthSchema, id: int) -> dict:
        customer = await cls._get_customer(auth, id)
        ai_profile_map = await PersonAiProfileService.admin_info_map(auth.db, {customer.person_id})
        preference_map = await PartnerPreferenceService.map_current(auth.db, {customer.person_id})
        ai_profile = ai_profile_map.get(customer.person_id, {}).get("profile")
        first_photo = (customer.person.photo_urls or [None])[0]
        return CustomerPrintCardSchema(
            printed_at=datetime.now(),
            customer_no=customer.person.display_no,
            display_name=cls._surname_name(customer.person.name, customer.person.gender),
            gender=customer.person.gender,
            age=cls._age(customer.person.birth_date),
            constellation=cls._constellation(customer.person.birth_date),
            zodiac=cls._zodiac(customer.person.birth_date),
            height_cm=customer.person.height_cm,
            weight_kg=customer.person.weight_kg,
            education=customer.person.education,
            occupation=customer.person.occupation,
            occupation_code=customer.person.occupation_code,
            graduated_school=customer.person.graduated_school,
            major=customer.person.major,
            unit_type=customer.person.unit_type,
            job_title=customer.person.job_title,
            work_company=customer.person.work_company,
            annual_income=customer.person.annual_income,
            marital_status=customer.person.marital_status,
            hometown=customer.person.hometown,
            residence=customer.person.residence,
            house_status=customer.person.house_status,
            car_status=customer.person.car_status,
            profile_intro=customer.person.profile_intro,
            family_background=customer.person.family_background,
            first_photo_url=first_photo,
            partner_preference=preference_map.get(customer.person_id),
            miai_impression=getattr(ai_profile, "content", None) if ai_profile else None,
        ).model_dump()
