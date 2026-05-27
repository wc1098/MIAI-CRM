from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select

from app.api.v1.module_system.auth.schema import AuthSchema
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.user.model import UserModel
from app.core.exceptions import CustomException
from app.plugin.module_certification.model import (
    CertificationApplicationModel,
    CertificationRecordModel,
    CertificationSensitiveAccessLogModel,
)
from app.plugin.module_crm.contract.model import CrmVipProfileModel
from app.plugin.module_crm.customer.model import (
    CrmCustomerLifecycleModel,
    CrmCustomerProfileModel,
)
from app.plugin.module_crm.lead.model import (
    CrmLeadLifecycleModel,
    CrmLeadProfileModel,
    CrmPersonModel,
)
from app.plugin.module_crm.preference.model import PersonPartnerPreferenceModel
from app.plugin.module_mp.auth.model import MiniProgramUserModel, SourceEventModel
from app.plugin.module_profile_ai.model import PersonAiProfileModel
from app.plugin.module_crm.person.model import PersonProfileInsightModel
from app.plugin.module_service.vip.model import (
    BackupPoolItemModel,
    CandidateJoinRequestModel,
    CandidateProfileModel,
    DeepInterviewModel,
    ServiceCaseModel,
    VipServiceLogModel,
)
from app.plugin.module_subscription.model import UserSubscriptionModel

from .schema import PersonQueryParam, SensitiveViewSchema


class PersonCenterService:
    """用户资源中心只读聚合服务"""

    BASIC_FIELDS = {
        "name": "姓名",
        "gender": "性别",
        "primary_mobile": "手机号",
        "birth_date": "出生日期",
        "height_cm": "身高",
        "education": "学历",
        "occupation_code": "职业",
        "annual_income": "年收入",
        "marital_status": "婚况",
        "residence": "常驻地",
    }
    DISPLAY_FIELDS = {
        "photo_urls": "照片",
        "profile_intro": "个人介绍",
        "certification_level": "认证等级",
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
    def _is_sales(cls, auth: AuthSchema) -> bool:
        return "SALES" in cls._role_codes(auth)

    @classmethod
    def _is_matchmaker(cls, auth: AuthSchema) -> bool:
        return "MATCHMAKER" in cls._role_codes(auth)

    @classmethod
    def _mask_mobile(cls, mobile: str | None) -> str | None:
        if not mobile or len(mobile) < 7:
            return mobile
        return f"{mobile[:3]}****{mobile[-4:]}"

    @classmethod
    def _mask_wechat(cls, wechat: str | None) -> str | None:
        if not wechat:
            return None
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
    async def _user_names(cls, auth: AuthSchema, ids: set[int | None]) -> dict[int, str]:
        user_ids = {user_id for user_id in ids if user_id}
        if not user_ids:
            return {}
        result = await auth.db.execute(select(UserModel.id, UserModel.name).where(UserModel.id.in_(user_ids)))
        return {row[0]: row[1] for row in result.all()}

    @classmethod
    async def _profile_insight_out(cls, auth: AuthSchema, person_id: int) -> dict[str, Any] | None:
        insight = (
            await auth.db.execute(
                select(PersonProfileInsightModel).where(
                    PersonProfileInsightModel.person_id == person_id,
                    PersonProfileInsightModel.is_deleted == False,
                )
            )
        ).scalars().first()
        if not insight:
            return None
        users = await cls._user_names(auth, {insight.updated_by_user_id})
        source_voided = False
        if insight.source_interview_id:
            source = await auth.db.get(DeepInterviewModel, insight.source_interview_id)
            source_voided = bool(source and source.interview_status == "voided")
        return {
            "id": insight.id,
            "person_id": insight.person_id,
            "source_interview_id": insight.source_interview_id,
            "source_scope": insight.source_scope,
            "personality_tags": insight.personality_tags or [],
            "family_background": insight.family_background,
            "relationship_history": insight.relationship_history,
            "marriage_view": insight.marriage_view,
            "communication_style": insight.communication_style,
            "emotional_needs": insight.emotional_needs,
            "hard_reject_items": insight.hard_reject_items or [],
            "soft_preference_items": insight.soft_preference_items or [],
            "compromise_items": insight.compromise_items or [],
            "risk_level": insight.risk_level,
            "risk_notes": insight.risk_notes,
            "communication_taboo": insight.communication_taboo,
            "recommendation_strategy": insight.recommendation_strategy,
            "matchmaker_comment": insight.matchmaker_comment,
            "public_matchmaker_impression": insight.public_matchmaker_impression,
            "keywords": insight.keywords or [],
            "profile_status": insight.profile_status,
            "updated_by_user_id": insight.updated_by_user_id,
            "updated_by_user_name": users.get(insight.updated_by_user_id),
            "insight_updated_at": insight.insight_updated_at,
            "source_interview_voided": source_voided,
        }

    @classmethod
    async def _dept_names(cls, auth: AuthSchema, ids: set[int | None]) -> dict[int, str]:
        dept_ids = {dept_id for dept_id in ids if dept_id}
        if not dept_ids:
            return {}
        result = await auth.db.execute(select(DeptModel.id, DeptModel.name).where(DeptModel.id.in_(dept_ids)))
        return {row[0]: row[1] for row in result.all()}

    @classmethod
    async def user_options_service(cls, auth: AuthSchema) -> list[dict[str, Any]]:
        conditions: list[Any] = [UserModel.status == "0", UserModel.is_deleted == False]
        if not cls._is_brand_admin(auth):
            if not auth.user or not auth.user.dept_id:
                return []
            conditions.append(UserModel.dept_id == auth.user.dept_id)
        result = await auth.db.execute(
            select(UserModel)
            .where(*conditions)
            .order_by(UserModel.dept_id.asc(), UserModel.id.asc())
            .limit(500)
        )
        return [
            {
                "id": row.id,
                "name": row.name,
                "username": row.username,
                "dept_id": row.dept_id,
            }
            for row in result.scalars().all()
            if row.id
        ]

    @classmethod
    def _scope_condition(cls, auth: AuthSchema) -> Any | None:
        if cls._is_brand_admin(auth):
            return None
        if not auth.user:
            return CrmPersonModel.id == -1
        related_conditions = []
        if cls._is_store_mgr(auth) and auth.user.dept_id:
            store_id = auth.user.dept_id
            related_conditions.extend(
                [
                    CrmPersonModel.id.in_(select(CrmLeadProfileModel.person_id).where(CrmLeadProfileModel.store_id == store_id, CrmLeadProfileModel.is_deleted == False)),
                    CrmPersonModel.id.in_(select(CrmCustomerProfileModel.person_id).where(CrmCustomerProfileModel.store_id == store_id, CrmCustomerProfileModel.is_deleted == False)),
                    CrmPersonModel.id.in_(select(ServiceCaseModel.person_id).where(ServiceCaseModel.store_id == store_id, ServiceCaseModel.is_deleted == False)),
                    CrmPersonModel.id.in_(select(BackupPoolItemModel.person_id).where(BackupPoolItemModel.store_id == store_id, BackupPoolItemModel.is_deleted == False)),
                ]
            )
        if cls._is_sales(auth):
            related_conditions.extend(
                [
                    CrmPersonModel.id.in_(select(CrmLeadProfileModel.person_id).where(CrmLeadProfileModel.owner_sales_id == auth.user.id, CrmLeadProfileModel.is_deleted == False)),
                    CrmPersonModel.id.in_(select(CrmCustomerProfileModel.person_id).where(CrmCustomerProfileModel.owner_user_id == auth.user.id, CrmCustomerProfileModel.is_deleted == False)),
                ]
            )
        if cls._is_matchmaker(auth):
            related_conditions.extend(
                [
                    CrmPersonModel.id.in_(select(ServiceCaseModel.person_id).where(ServiceCaseModel.owner_matchmaker_id == auth.user.id, ServiceCaseModel.is_deleted == False)),
                    CrmPersonModel.id.in_(select(BackupPoolItemModel.person_id).where(BackupPoolItemModel.matchmaker_id == auth.user.id, BackupPoolItemModel.is_deleted == False)),
                ]
            )
        return or_(*related_conditions) if related_conditions else CrmPersonModel.id == -1

    @classmethod
    def _identity_condition(cls, tag: str) -> Any | None:
        mapping = {
            "lead": select(CrmLeadProfileModel.person_id).where(CrmLeadProfileModel.is_deleted == False),
            "customer": select(CrmCustomerProfileModel.person_id).where(CrmCustomerProfileModel.is_deleted == False),
            "vip": select(CrmVipProfileModel.person_id).where(CrmVipProfileModel.is_deleted == False),
            "service": select(ServiceCaseModel.person_id).where(ServiceCaseModel.is_deleted == False),
            "candidate": select(CandidateProfileModel.person_id).where(CandidateProfileModel.is_deleted == False),
            "backup": select(BackupPoolItemModel.person_id).where(BackupPoolItemModel.is_deleted == False),
            "mp_user": select(MiniProgramUserModel.person_id).where(MiniProgramUserModel.person_id.is_not(None), MiniProgramUserModel.is_deleted == False),
            "subscription": select(UserSubscriptionModel.person_id).where(UserSubscriptionModel.is_deleted == False),
        }
        stmt = mapping.get(tag)
        return CrmPersonModel.id.in_(stmt) if stmt is not None else None

    @classmethod
    def _store_condition(cls, store_id: int) -> Any:
        return or_(
            CrmPersonModel.id.in_(select(CrmLeadProfileModel.person_id).where(CrmLeadProfileModel.store_id == store_id, CrmLeadProfileModel.is_deleted == False)),
            CrmPersonModel.id.in_(select(CrmCustomerProfileModel.person_id).where(CrmCustomerProfileModel.store_id == store_id, CrmCustomerProfileModel.is_deleted == False)),
            CrmPersonModel.id.in_(select(ServiceCaseModel.person_id).where(ServiceCaseModel.store_id == store_id, ServiceCaseModel.is_deleted == False)),
            CrmPersonModel.id.in_(select(BackupPoolItemModel.person_id).where(BackupPoolItemModel.store_id == store_id, BackupPoolItemModel.is_deleted == False)),
        )

    @classmethod
    def _sales_condition(cls, user_id: int) -> Any:
        return or_(
            CrmPersonModel.id.in_(select(CrmLeadProfileModel.person_id).where(CrmLeadProfileModel.owner_sales_id == user_id, CrmLeadProfileModel.is_deleted == False)),
            CrmPersonModel.id.in_(select(CrmCustomerProfileModel.person_id).where(CrmCustomerProfileModel.owner_user_id == user_id, CrmCustomerProfileModel.is_deleted == False)),
        )

    @classmethod
    def _matchmaker_condition(cls, user_id: int) -> Any:
        return or_(
            CrmPersonModel.id.in_(select(ServiceCaseModel.person_id).where(ServiceCaseModel.owner_matchmaker_id == user_id, ServiceCaseModel.is_deleted == False)),
            CrmPersonModel.id.in_(select(BackupPoolItemModel.person_id).where(BackupPoolItemModel.matchmaker_id == user_id, BackupPoolItemModel.is_deleted == False)),
        )

    @classmethod
    def _base_conditions(cls, auth: AuthSchema, search: PersonQueryParam | None = None) -> list[Any]:
        conditions: list[Any] = [CrmPersonModel.is_deleted == False]
        scope_condition = cls._scope_condition(auth)
        if scope_condition is not None:
            conditions.append(scope_condition)
        if not search:
            return conditions
        if search.keyword:
            like = f"%{search.keyword}%"
            conditions.append(or_(CrmPersonModel.display_no.like(like), CrmPersonModel.name.like(like), CrmPersonModel.primary_mobile.like(like)))
        if search.certification_level:
            conditions.append(CrmPersonModel.certification_level == search.certification_level)
        if search.store_id:
            conditions.append(cls._store_condition(search.store_id))
        if search.owner_sales_id:
            conditions.append(cls._sales_condition(search.owner_sales_id))
        if search.service_owner_user_id:
            conditions.append(cls._matchmaker_condition(search.service_owner_user_id))
        if search.identity_tag:
            identity_condition = cls._identity_condition(search.identity_tag)
            if identity_condition is not None:
                conditions.append(identity_condition)
        return conditions

    @classmethod
    async def _active_maps(cls, auth: AuthSchema, person_ids: list[int]) -> dict[str, Any]:
        if not person_ids:
            return {}
        lead_rows = (
            await auth.db.execute(select(CrmLeadProfileModel).where(CrmLeadProfileModel.person_id.in_(person_ids), CrmLeadProfileModel.is_deleted == False).order_by(CrmLeadProfileModel.id.desc()))
        ).scalars().all()
        customer_rows = (
            await auth.db.execute(select(CrmCustomerProfileModel).where(CrmCustomerProfileModel.person_id.in_(person_ids), CrmCustomerProfileModel.is_deleted == False).order_by(CrmCustomerProfileModel.id.desc()))
        ).scalars().all()
        vip_rows = (
            await auth.db.execute(select(CrmVipProfileModel).where(CrmVipProfileModel.person_id.in_(person_ids), CrmVipProfileModel.is_deleted == False).order_by(CrmVipProfileModel.id.desc()))
        ).scalars().all()
        service_rows = (
            await auth.db.execute(select(ServiceCaseModel).where(ServiceCaseModel.person_id.in_(person_ids), ServiceCaseModel.is_deleted == False).order_by(ServiceCaseModel.id.desc()))
        ).scalars().all()
        candidate_rows = (
            await auth.db.execute(select(CandidateProfileModel).where(CandidateProfileModel.person_id.in_(person_ids), CandidateProfileModel.is_deleted == False).order_by(CandidateProfileModel.id.desc()))
        ).scalars().all()
        backup_rows = (
            await auth.db.execute(select(BackupPoolItemModel).where(BackupPoolItemModel.person_id.in_(person_ids), BackupPoolItemModel.is_deleted == False).order_by(BackupPoolItemModel.id.desc()))
        ).scalars().all()
        request_rows = (
            await auth.db.execute(select(CandidateJoinRequestModel).where(CandidateJoinRequestModel.person_id.in_(person_ids), CandidateJoinRequestModel.is_deleted == False).order_by(CandidateJoinRequestModel.id.desc()))
        ).scalars().all()
        mp_rows = (
            await auth.db.execute(select(MiniProgramUserModel).where(MiniProgramUserModel.person_id.in_(person_ids), MiniProgramUserModel.is_deleted == False).order_by(MiniProgramUserModel.id.desc()))
        ).scalars().all()
        sub_rows = (
            await auth.db.execute(select(UserSubscriptionModel).where(UserSubscriptionModel.person_id.in_(person_ids), UserSubscriptionModel.is_deleted == False).order_by(UserSubscriptionModel.id.desc()))
        ).scalars().all()
        preference_rows = (
            await auth.db.execute(select(PersonPartnerPreferenceModel).where(PersonPartnerPreferenceModel.person_id.in_(person_ids), PersonPartnerPreferenceModel.is_deleted == False, PersonPartnerPreferenceModel.is_effective == True))
        ).scalars().all()
        ai_rows = (
            await auth.db.execute(select(PersonAiProfileModel).where(PersonAiProfileModel.person_id.in_(person_ids), PersonAiProfileModel.is_deleted == False, PersonAiProfileModel.is_effective == True).order_by(PersonAiProfileModel.priority.asc(), PersonAiProfileModel.id.desc()))
        ).scalars().all()
        deep_counts = {
            row[0]: row[1]
            for row in (
                await auth.db.execute(
                    select(DeepInterviewModel.person_id, func.count(DeepInterviewModel.id)).where(
                        DeepInterviewModel.person_id.in_(person_ids),
                        DeepInterviewModel.is_deleted == False,
                        DeepInterviewModel.interview_status == "active",
                    ).group_by(DeepInterviewModel.person_id)
                )
            ).all()
        }
        cert_counts = {
            row[0]: row[1]
            for row in (
                await auth.db.execute(
                    select(CertificationRecordModel.person_id, func.count(CertificationRecordModel.id)).where(
                        CertificationRecordModel.person_id.in_(person_ids),
                        CertificationRecordModel.is_deleted == False,
                    ).group_by(CertificationRecordModel.person_id)
                )
            ).all()
        }

        def first_by_person(rows: list[Any]) -> dict[int, Any]:
            result: dict[int, Any] = {}
            for row in rows:
                result.setdefault(row.person_id, row)
            return result

        def list_by_person(rows: list[Any]) -> dict[int, list[Any]]:
            result: dict[int, list[Any]] = {}
            for row in rows:
                result.setdefault(row.person_id, []).append(row)
            return result

        return {
            "lead": first_by_person(lead_rows),
            "customer": first_by_person(customer_rows),
            "vip": first_by_person(vip_rows),
            "service": first_by_person(service_rows),
            "candidate": first_by_person(candidate_rows),
            "backup": list_by_person(backup_rows),
            "join_request": list_by_person(request_rows),
            "mp_user": first_by_person(mp_rows),
            "subscription": first_by_person(sub_rows),
            "preference": first_by_person(preference_rows),
            "ai_profile": first_by_person(ai_rows),
            "deep_count": deep_counts,
            "cert_count": cert_counts,
        }

    @classmethod
    def _identity_tags(cls, person_id: int, maps: dict[str, Any]) -> list[str]:
        tags = []
        for key, label in [
            ("mp_user", "mp_user"),
            ("lead", "lead"),
            ("customer", "customer"),
            ("vip", "vip"),
            ("service", "service"),
            ("candidate", "candidate"),
            ("subscription", "subscription"),
        ]:
            if maps.get(key, {}).get(person_id):
                tags.append(label)
        if maps.get("backup", {}).get(person_id):
            tags.append("backup")
        return tags

    @classmethod
    def _latest_activity(cls, person: CrmPersonModel, person_id: int, maps: dict[str, Any]) -> datetime | None:
        dates = [person.updated_time, person.created_time]
        lead = maps.get("lead", {}).get(person_id)
        customer = maps.get("customer", {}).get(person_id)
        service = maps.get("service", {}).get(person_id)
        vip = maps.get("vip", {}).get(person_id)
        mp_user = maps.get("mp_user", {}).get(person_id)
        subscription = maps.get("subscription", {}).get(person_id)
        if lead:
            dates.extend([lead.latest_follow_at, lead.next_follow_at, lead.assigned_at, lead.converted_customer_at, lead.updated_time])
        if customer:
            dates.extend([customer.latest_follow_at, customer.next_follow_at, customer.converted_vip_at, customer.updated_time])
        if service:
            dates.extend([service.assigned_at, service.close_requested_at, service.close_reviewed_at, service.reopened_at, service.updated_time])
        if vip:
            dates.extend([vip.assigned_at, vip.started_at, vip.ended_at, vip.updated_time])
        if mp_user:
            dates.extend([mp_user.registered_at, mp_user.last_login_at, mp_user.updated_time])
        if subscription:
            dates.extend([subscription.started_at, subscription.last_unlock_at, subscription.updated_time])
        for item in maps.get("backup", {}).get(person_id, []):
            dates.extend([item.last_used_at, item.approved_at, item.updated_time])
        for item in maps.get("join_request", {}).get(person_id, []):
            dates.extend([item.reviewed_at, item.updated_time])
        active_dates = [item for item in dates if item is not None]
        return max(active_dates) if active_dates else None

    @classmethod
    def _quality(cls, person: CrmPersonModel, person_id: int, maps: dict[str, Any]) -> dict:
        missing_basic = [label for field, label in cls.BASIC_FIELDS.items() if not getattr(person, field, None)]
        missing_display = [label for field, label in cls.DISPLAY_FIELDS.items() if not getattr(person, field, None) or getattr(person, field, None) == "none"]
        if not maps.get("preference", {}).get(person_id):
            missing_display.append("择偶要求")
        missing_service = []
        if not maps.get("deep_count", {}).get(person_id):
            missing_service.append("深访")
        if not maps.get("ai_profile", {}).get(person_id):
            missing_service.append("AI画像")
        basic_score = round((len(cls.BASIC_FIELDS) - len(missing_basic)) / len(cls.BASIC_FIELDS) * 100)
        display_total = len(cls.DISPLAY_FIELDS) + 1
        display_score = round((display_total - len(missing_display)) / display_total * 100)
        service_total = 2
        service_score = round((service_total - len(missing_service)) / service_total * 100)
        score = round(basic_score * 0.5 + display_score * 0.3 + service_score * 0.2)
        if score >= 80:
            quality_level = "good"
        elif score >= 50:
            quality_level = "medium"
        else:
            quality_level = "poor"
        risk_flags = []
        lead = maps.get("lead", {}).get(person_id)
        customer = maps.get("customer", {}).get(person_id)
        service = maps.get("service", {}).get(person_id)
        vip = maps.get("vip", {}).get(person_id)
        candidate = maps.get("candidate", {}).get(person_id)
        latest = cls._latest_activity(person, person_id, maps)
        if not person.primary_mobile:
            risk_flags.append({"type": "no_mobile", "level": "danger", "title": "无手机号"})
        if not any([lead and lead.store_id, customer and customer.store_id, service and service.store_id]):
            risk_flags.append({"type": "no_store", "level": "warning", "title": "无归属门店"})
        if latest and latest < datetime.now() - timedelta(days=30):
            risk_flags.append({"type": "inactive_30d", "level": "warning", "title": "30天无动作"})
        if vip and not service:
            risk_flags.append({"type": "vip_without_case", "level": "danger", "title": "VIP无服务工单"})
        if service and not service.owner_matchmaker_id:
            risk_flags.append({"type": "service_without_owner", "level": "danger", "title": "服务未分配红娘"})
        if candidate and not maps.get("backup", {}).get(person_id):
            risk_flags.append({"type": "candidate_without_backup", "level": "warning", "title": "候选无备选归属"})
        return {
            "score": score,
            "quality_level": quality_level,
            "basic_score": basic_score,
            "display_score": display_score,
            "service_score": service_score,
            "missing_basic": missing_basic,
            "missing_display": missing_display,
            "missing_service": missing_service,
            "risk_flags": risk_flags,
        }

    @classmethod
    def _person_brief(cls, person: CrmPersonModel) -> dict:
        return {
            "id": person.id,
            "display_no": person.display_no,
            "name": person.name,
            "gender": person.gender,
            "primary_mobile": cls._mask_mobile(person.primary_mobile),
            "mobile_masked": cls._mask_mobile(person.primary_mobile),
            "wechat": cls._mask_wechat(person.wechat),
            "birth_date": person.birth_date,
            "age": cls._age(person.birth_date),
            "height_cm": person.height_cm,
            "education": person.education,
            "annual_income": person.annual_income,
            "marital_status": person.marital_status,
            "occupation": person.occupation,
            "occupation_code": person.occupation_code,
            "residence": person.residence,
            "photo_urls": person.photo_urls or [],
            "certification_level": person.certification_level,
            "id_card_no_masked": cls._mask_id_card(person.id_card_no),
        }

    @classmethod
    async def _decorate_people(cls, auth: AuthSchema, people: list[CrmPersonModel]) -> list[dict]:
        person_ids = [person.id for person in people]
        maps = await cls._active_maps(auth, person_ids)
        user_ids: set[int | None] = set()
        dept_ids: set[int | None] = set()
        for person_id in person_ids:
            lead = maps["lead"].get(person_id)
            customer = maps["customer"].get(person_id)
            service = maps["service"].get(person_id)
            if lead:
                user_ids.add(lead.owner_sales_id)
                dept_ids.add(lead.store_id)
            if customer:
                user_ids.add(customer.owner_user_id)
                dept_ids.add(customer.store_id)
            if service:
                user_ids.add(service.owner_matchmaker_id)
                dept_ids.add(service.store_id)
            for item in maps["backup"].get(person_id, []):
                user_ids.add(item.matchmaker_id)
                dept_ids.add(item.store_id)
        user_names = await cls._user_names(auth, user_ids)
        dept_names = await cls._dept_names(auth, dept_ids)
        result = []
        for person in people:
            lead = maps["lead"].get(person.id)
            customer = maps["customer"].get(person.id)
            service = maps["service"].get(person.id)
            store_id = (service.store_id if service else None) or (customer.store_id if customer else None) or (lead.store_id if lead else None)
            owner_sales_id = (customer.owner_user_id if customer else None) or (lead.owner_sales_id if lead else None)
            service_owner_id = service.owner_matchmaker_id if service else None
            quality = cls._quality(person, person.id, maps)
            result.append(
                {
                    "person": cls._person_brief(person),
                    "store": {"id": store_id, "name": dept_names.get(store_id)} if store_id else None,
                    "owner_sales": {"id": owner_sales_id, "name": user_names.get(owner_sales_id)} if owner_sales_id else None,
                    "service_owner": {"id": service_owner_id, "name": user_names.get(service_owner_id)} if service_owner_id else None,
                    "identity_tags": cls._identity_tags(person.id, maps),
                    "identity_summary": {
                        "backup_count": len(maps["backup"].get(person.id, [])),
                        "join_request_count": len(maps["join_request"].get(person.id, [])),
                        "certification_count": maps["cert_count"].get(person.id, 0),
                    },
                    "quality": quality,
                    "latest_activity_at": cls._latest_activity(person, person.id, maps),
                    "created_time": person.created_time,
                }
            )
        return result

    @classmethod
    async def page_service(cls, auth: AuthSchema, page_no: int, page_size: int, search: PersonQueryParam) -> dict:
        conditions = cls._base_conditions(auth, search)
        needs_post_filter = bool(search.quality_level or search.latest_activity_start or search.latest_activity_end)
        if needs_post_filter:
            result = await auth.db.execute(select(CrmPersonModel).where(*conditions).order_by(CrmPersonModel.updated_time.desc(), CrmPersonModel.id.desc()))
            decorated = await cls._decorate_people(auth, result.scalars().all())
            if search.quality_level:
                decorated = [item for item in decorated if item["quality"]["quality_level"] == search.quality_level]
            if search.latest_activity_start:
                decorated = [item for item in decorated if item["latest_activity_at"] and item["latest_activity_at"] >= search.latest_activity_start]
            if search.latest_activity_end:
                decorated = [item for item in decorated if item["latest_activity_at"] and item["latest_activity_at"] <= search.latest_activity_end]
            total = len(decorated)
            offset = (page_no - 1) * page_size
            return {
                "page_no": page_no,
                "page_size": page_size,
                "total": total,
                "has_next": offset + page_size < total,
                "items": decorated[offset : offset + page_size],
            }
        total = (await auth.db.execute(select(func.count(CrmPersonModel.id)).where(*conditions))).scalar() or 0
        offset = (page_no - 1) * page_size
        result = await auth.db.execute(
            select(CrmPersonModel).where(*conditions).order_by(CrmPersonModel.updated_time.desc(), CrmPersonModel.id.desc()).offset(offset).limit(page_size)
        )
        people = result.scalars().all()
        items = await cls._decorate_people(auth, people)
        return {"page_no": page_no, "page_size": page_size, "total": total, "has_next": offset + page_size < total, "items": items}

    @classmethod
    async def _get_person(cls, auth: AuthSchema, person_id: int) -> CrmPersonModel:
        result = await auth.db.execute(select(CrmPersonModel).where(CrmPersonModel.id == person_id, CrmPersonModel.is_deleted == False))
        person = result.scalars().first()
        if not person:
            raise CustomException(msg="人员不存在")
        conditions = cls._base_conditions(auth)
        access = await auth.db.scalar(select(func.count(CrmPersonModel.id)).where(CrmPersonModel.id == person_id, *conditions))
        if not access:
            raise CustomException(msg="无权访问该资源", code=10403, status_code=403)
        return person

    @classmethod
    def _model_out(cls, row: Any, fields: list[str]) -> dict[str, Any] | None:
        if not row:
            return None
        data = {field: getattr(row, field, None) for field in fields}
        data["id"] = row.id
        data["created_time"] = getattr(row, "created_time", None)
        data["updated_time"] = getattr(row, "updated_time", None)
        return data

    @classmethod
    async def detail_service(cls, auth: AuthSchema, person_id: int) -> dict:
        person = await cls._get_person(auth, person_id)
        maps = await cls._active_maps(auth, [person_id])
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
        user_names = await cls._user_names(auth, user_ids)
        dept_names = await cls._dept_names(auth, dept_ids)
        application = await auth.db.scalar(
            select(CertificationApplicationModel).where(
                CertificationApplicationModel.person_id == person_id,
                CertificationApplicationModel.is_deleted == False,
            ).order_by(CertificationApplicationModel.id.desc())
        )
        sensitive_count = await auth.db.scalar(select(func.count(CertificationSensitiveAccessLogModel.id)).where(CertificationSensitiveAccessLogModel.person_id == person_id, CertificationSensitiveAccessLogModel.is_deleted == False)) or 0
        preference = maps["preference"].get(person_id)
        ai_profile = maps["ai_profile"].get(person_id)
        return {
            "person": cls._person_brief(person),
            "relations": {
                "lead": cls._model_out(maps["lead"].get(person_id), ["store_id", "owner_sales_id", "pool_type", "lead_type", "source_channel_code", "latest_follow_at", "next_follow_at", "assigned_at", "converted_customer_at"]),
                "customer": cls._model_out(maps["customer"].get(person_id), ["lead_id", "store_id", "owner_user_id", "current_stage", "max_stage", "latest_follow_at", "next_follow_at", "converted_vip_at", "ended_at", "end_reason"]),
                "vip": cls._model_out(maps["vip"].get(person_id), ["customer_id", "contract_id", "store_id", "service_owner_user_id", "vip_level", "vip_status", "started_at", "ended_at", "assigned_at"]),
                "service_case": cls._model_out(maps["service"].get(person_id), ["vip_id", "customer_id", "contract_id", "store_id", "owner_matchmaker_id", "pool_type", "case_status", "close_review_status"]),
                "candidate": cls._model_out(maps["candidate"].get(person_id), ["candidate_status"]),
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
                "miniprogram_user": cls._model_out(maps["mp_user"].get(person_id), ["mobile", "nickname", "registered_at", "last_login_at", "is_invisible", "allow_user_wall"]),
                "subscription": cls._model_out(maps["subscription"].get(person_id), ["plan_id", "started_at", "expired_at", "total_quota", "used_quota", "subscription_status", "last_unlock_at"]),
                "certification": cls._model_out(application, ["level_code", "level_name", "application_status", "paid_at", "approved_at"]) if application else {"certification_level": person.certification_level, "certification_summary": person.certification_summary},
                "partner_preference": cls._model_out(preference, ["profile_summary", "strictness_level", "is_final", "version_no", "source_type"]) if preference else None,
                "ai_profile": cls._model_out(ai_profile, ["profile_type", "source_type", "content", "generation_status", "model_name", "generated_at"]) if ai_profile else None,
            },
            "quality": cls._quality(person, person_id, maps),
            "profile_insight": await cls._profile_insight_out(auth, person_id),
            "sensitive_log_count": sensitive_count,
        }

    @classmethod
    async def quality_service(cls, auth: AuthSchema, person_id: int) -> dict:
        person = await cls._get_person(auth, person_id)
        maps = await cls._active_maps(auth, [person_id])
        return cls._quality(person, person_id, maps)

    @classmethod
    async def timeline_service(cls, auth: AuthSchema, person_id: int) -> list[dict]:
        await cls._get_person(auth, person_id)
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
        user_names = await cls._user_names(auth, {row.get("operator_user_id") for row in rows})
        for row in rows:
            row["operator_user_name"] = user_names.get(row.get("operator_user_id"))
        rows.sort(key=lambda row: row["occurred_at"] or datetime.min, reverse=True)
        return rows[:100]

    @classmethod
    async def sensitive_log_service(cls, auth: AuthSchema, person_id: int) -> list[dict]:
        await cls._get_person(auth, person_id)
        rows = (
            await auth.db.execute(
                select(CertificationSensitiveAccessLogModel)
                .where(CertificationSensitiveAccessLogModel.person_id == person_id, CertificationSensitiveAccessLogModel.is_deleted == False)
                .order_by(CertificationSensitiveAccessLogModel.accessed_at.desc(), CertificationSensitiveAccessLogModel.id.desc())
                .limit(100)
            )
        ).scalars().all()
        user_names = await cls._user_names(auth, {row.operator_id for row in rows})
        return [
            {
                "id": row.id,
                "access_type": row.access_type,
                "permission_result": row.permission_result,
                "reason": row.reason,
                "operator_id": row.operator_id,
                "operator_name": user_names.get(row.operator_id),
                "accessed_at": row.accessed_at,
            }
            for row in rows
        ]

    @classmethod
    async def _write_sensitive_log(cls, auth: AuthSchema, person_id: int, access_type: str, reason: str) -> None:
        log = CertificationSensitiveAccessLogModel(
            brand_id=1,
            operator_id=auth.user.id if auth.user else None,
            person_id=person_id,
            access_type=access_type,
            permission_result="allowed",
            reason=reason.strip(),
            accessed_at=datetime.now(),
        )
        auth.db.add(log)
        await auth.db.flush()

    @classmethod
    async def view_phone_service(cls, auth: AuthSchema, person_id: int, data: SensitiveViewSchema) -> dict:
        person = await cls._get_person(auth, person_id)
        if not data.reason.strip():
            raise CustomException(msg="查看完整手机号必须填写原因")
        await cls._write_sensitive_log(auth, person_id, "view_phone", data.reason)
        return {"person_id": person_id, "primary_mobile": person.primary_mobile, "mobile_masked": cls._mask_mobile(person.primary_mobile)}

    @classmethod
    async def view_id_card_service(cls, auth: AuthSchema, person_id: int, data: SensitiveViewSchema) -> dict:
        person = await cls._get_person(auth, person_id)
        if not data.reason.strip():
            raise CustomException(msg="查看完整身份证号必须填写原因")
        await cls._write_sensitive_log(auth, person_id, "view_id_card", data.reason)
        return {"person_id": person_id, "id_card_no": person.id_card_no, "id_card_no_masked": cls._mask_id_card(person.id_card_no)}
