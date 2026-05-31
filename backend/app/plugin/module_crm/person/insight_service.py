from datetime import datetime
from typing import Any

from sqlalchemy import select, update

from app.api.v1.module_system.auth.schema import AuthSchema
from app.api.v1.module_system.user.model import UserModel
from app.core.exceptions import CustomException
from app.plugin.module_crm.customer.model import CrmCustomerProfileModel
from app.plugin.module_crm.lead.model import CrmLeadProfileModel, CrmPersonModel
from app.plugin.module_match.service import MatchProfileService
from app.plugin.module_service.vip.model import (
    BackupPoolItemModel,
    DeepInterviewModel,
    ServiceCaseModel,
)

from .model import PersonProfileInsightModel
from .schema import (
    PersonInterviewSaveSchema,
    PersonInterviewVoidSchema,
    PersonProfileInsightSaveSchema,
)


class PersonInsightService:
    """人员深访与当前画像公共服务"""

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
    def _is_sales(cls, auth: AuthSchema) -> bool:
        return "SALES" in cls._role_codes(auth)

    @staticmethod
    def _stamp_create(auth: AuthSchema, obj: Any) -> None:
        if auth.user:
            if hasattr(obj, "created_id"):
                obj.created_id = auth.user.id
            if hasattr(obj, "updated_id"):
                obj.updated_id = auth.user.id

    @staticmethod
    def _stamp_update(auth: AuthSchema, obj: Any) -> None:
        if auth.user and hasattr(obj, "updated_id"):
            obj.updated_id = auth.user.id

    @classmethod
    async def _person_exists(cls, auth: AuthSchema, person_id: int) -> CrmPersonModel:
        person = await auth.db.get(CrmPersonModel, person_id)
        if not person or person.is_deleted:
            raise CustomException(msg="人员不存在")
        return person

    @classmethod
    async def _person_in_store(cls, auth: AuthSchema, person_id: int, store_id: int | None) -> bool:
        if not store_id:
            return False
        exists = await auth.db.scalar(
            select(CrmLeadProfileModel.id).where(
                CrmLeadProfileModel.person_id == person_id,
                CrmLeadProfileModel.store_id == store_id,
                CrmLeadProfileModel.is_deleted == False,
            )
        )
        if exists:
            return True
        exists = await auth.db.scalar(
            select(CrmCustomerProfileModel.id).where(
                CrmCustomerProfileModel.person_id == person_id,
                CrmCustomerProfileModel.store_id == store_id,
                CrmCustomerProfileModel.is_deleted == False,
            )
        )
        if exists:
            return True
        exists = await auth.db.scalar(
            select(ServiceCaseModel.id).where(
                ServiceCaseModel.person_id == person_id,
                ServiceCaseModel.store_id == store_id,
                ServiceCaseModel.is_deleted == False,
            )
        )
        if exists:
            return True
        exists = await auth.db.scalar(
            select(BackupPoolItemModel.id).where(
                BackupPoolItemModel.person_id == person_id,
                BackupPoolItemModel.store_id == store_id,
                BackupPoolItemModel.is_deleted == False,
            )
        )
        return bool(exists)

    @classmethod
    async def _matchmaker_related(cls, auth: AuthSchema, person_id: int) -> bool:
        if not auth.user:
            return False
        exists = await auth.db.scalar(
            select(ServiceCaseModel.id).where(
                ServiceCaseModel.person_id == person_id,
                ServiceCaseModel.owner_matchmaker_id == auth.user.id,
                ServiceCaseModel.is_deleted == False,
            )
        )
        if exists:
            return True
        exists = await auth.db.scalar(
            select(BackupPoolItemModel.id).where(
                BackupPoolItemModel.person_id == person_id,
                BackupPoolItemModel.matchmaker_id == auth.user.id,
                BackupPoolItemModel.is_deleted == False,
            )
        )
        return bool(exists)

    @classmethod
    async def _ensure_read_access(cls, auth: AuthSchema, person_id: int) -> None:
        if cls._is_brand_admin(auth):
            return
        if not auth.user:
            raise CustomException(msg="无权访问深访画像")
        if cls._is_store_mgr(auth) and await cls._person_in_store(auth, person_id, auth.user.dept_id):
            return
        if cls._is_matchmaker(auth) and await cls._matchmaker_related(auth, person_id):
            return
        raise CustomException(msg="无权访问深访画像")

    @classmethod
    async def _ensure_write_access(cls, auth: AuthSchema, person_id: int) -> None:
        if cls._is_sales(auth) and not (cls._is_brand_admin(auth) or cls._is_store_mgr(auth) or cls._is_matchmaker(auth)):
            raise CustomException(msg="销售无权维护深访画像")
        await cls._ensure_read_access(auth, person_id)

    @classmethod
    async def _user_names(cls, auth: AuthSchema, ids: set[int | None]) -> dict[int, str]:
        user_ids = {user_id for user_id in ids if user_id}
        if not user_ids:
            return {}
        result = await auth.db.execute(select(UserModel.id, UserModel.name).where(UserModel.id.in_(user_ids)))
        return {row[0]: row[1] for row in result.all()}

    @staticmethod
    def _list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    @staticmethod
    def _get(payload: dict[str, Any], *path: str) -> Any:
        current: Any = payload
        for part in path:
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current

    @classmethod
    def _insight_from_interview(cls, data: PersonInterviewSaveSchema) -> PersonProfileInsightSaveSchema:
        payload = data.structured_payload or {}
        summary_keywords = cls._get(payload, "summary", "keywords")
        suggested_hard_reject_items = cls._list(cls._get(payload, "preference_review", "suggested_hard_reject_items")) or cls._list(cls._get(payload, "preference_insight", "hard_reject_items"))
        suggested_priority_items = cls._list(cls._get(payload, "preference_review", "suggested_priority_items")) or cls._list(cls._get(payload, "preference_insight", "soft_preference_items"))
        suggested_relax_items = cls._list(cls._get(payload, "preference_review", "suggested_relax_items")) or cls._list(cls._get(payload, "preference_insight", "compromise_items"))
        review_reason = cls._get(payload, "preference_review", "review_reason")
        return PersonProfileInsightSaveSchema(
            personality_tags=cls._list(cls._get(payload, "personality", "tags")),
            family_background=cls._get(payload, "family", "family_notes") or cls._get(payload, "family", "family_structure"),
            relationship_history=cls._get(payload, "relationship", "history_summary"),
            marriage_view=cls._get(payload, "relationship", "marriage_view"),
            communication_style=cls._get(payload, "personality", "communication_style"),
            emotional_needs=cls._get(payload, "relationship", "emotional_needs"),
            hard_reject_items=suggested_hard_reject_items,
            soft_preference_items=suggested_priority_items,
            compromise_items=suggested_relax_items,
            risk_level=cls._get(payload, "risk", "risk_level"),
            risk_notes=cls._get(payload, "risk", "internal_notes") or cls._get(payload, "risk", "risk_notes") or review_reason,
            communication_taboo=cls._get(payload, "risk", "communication_taboo"),
            recommendation_strategy=cls._get(payload, "service_strategy", "candidate_strategy"),
            matchmaker_comment=data.manual_notes or cls._get(payload, "personality", "matchmaker_observation"),
            public_matchmaker_impression=cls._get(payload, "summary", "public_matchmaker_impression"),
            keywords=data.keywords or cls._list(summary_keywords),
        )

    @classmethod
    async def _upsert_insight(
        cls,
        auth: AuthSchema,
        *,
        person_id: int,
        source_interview: DeepInterviewModel | None,
        data: PersonProfileInsightSaveSchema,
        profile_payload: dict[str, Any] | None = None,
        status: str = "active",
        brand_id: int = 1,
    ) -> PersonProfileInsightModel:
        insight = (
            await auth.db.execute(
                select(PersonProfileInsightModel).where(
                    PersonProfileInsightModel.person_id == person_id,
                    PersonProfileInsightModel.is_deleted == False,
                )
            )
        ).scalars().first()
        if insight is None:
            insight = PersonProfileInsightModel(brand_id=brand_id, person_id=person_id)
            cls._stamp_create(auth, insight)
            auth.db.add(insight)
        insight.source_interview_id = source_interview.id if source_interview else insight.source_interview_id
        insight.source_scope = source_interview.interview_scope if source_interview else insight.source_scope
        insight.personality_tags = data.personality_tags
        insight.family_background = data.family_background
        insight.relationship_history = data.relationship_history
        insight.marriage_view = data.marriage_view
        insight.communication_style = data.communication_style
        insight.emotional_needs = data.emotional_needs
        insight.hard_reject_items = data.hard_reject_items
        insight.soft_preference_items = data.soft_preference_items
        insight.compromise_items = data.compromise_items
        insight.risk_level = data.risk_level
        insight.risk_notes = data.risk_notes
        insight.communication_taboo = data.communication_taboo
        insight.recommendation_strategy = data.recommendation_strategy
        insight.matchmaker_comment = data.matchmaker_comment
        insight.public_matchmaker_impression = data.public_matchmaker_impression
        insight.keywords = data.keywords
        insight.profile_status = status
        insight.profile_payload = profile_payload
        insight.updated_by_user_id = auth.user.id if auth.user else None
        insight.insight_updated_at = datetime.now()
        cls._stamp_update(auth, insight)
        await auth.db.flush()
        await MatchProfileService.mark_dirty(auth.db, person_id, ["self_profile", "preference"], "deep_interview" if source_interview else "profile_insight", source_interview.id if source_interview else insight.id)
        return insight

    @classmethod
    async def create_interview_service(
        cls,
        auth: AuthSchema,
        person_id: int,
        data: PersonInterviewSaveSchema,
        *,
        service_case: ServiceCaseModel | None = None,
        force_matchmaker_id: int | None = None,
    ) -> dict:
        person = await cls._person_exists(auth, person_id)
        await cls._ensure_write_access(auth, person_id)
        matchmaker_id = force_matchmaker_id if force_matchmaker_id is not None else (auth.user.id if auth.user and cls._is_matchmaker(auth) else None)
        interview = DeepInterviewModel(
            brand_id=person.brand_id,
            service_case_id=service_case.id if service_case else None,
            vip_id=service_case.vip_id if service_case else None,
            person_id=person.id,
            customer_id=service_case.customer_id if service_case else data.customer_id,
            contract_id=service_case.contract_id if service_case else None,
            backup_item_id=data.backup_item_id,
            matchmaker_id=matchmaker_id,
            interview_scope=data.interview_scope,
            interview_type=data.interview_type,
            interview_method=data.interview_method,
            interviewed_at=data.interviewed_at or datetime.now(),
            content=data.content,
            structured_payload=data.structured_payload,
            keywords=data.keywords,
            summary=data.summary,
            manual_notes=data.manual_notes,
            interview_status="active",
            is_current_source=True,
        )
        cls._stamp_create(auth, interview)
        auth.db.add(interview)
        await auth.db.flush()
        await auth.db.execute(
            update(DeepInterviewModel)
            .where(
                DeepInterviewModel.person_id == person.id,
                DeepInterviewModel.id != interview.id,
                DeepInterviewModel.is_current_source == True,
                DeepInterviewModel.is_deleted == False,
            )
            .values(is_current_source=False)
        )
        insight_data = cls._insight_from_interview(data)
        await cls._upsert_insight(
            auth,
            person_id=person.id,
            source_interview=interview,
            data=insight_data,
            profile_payload=data.structured_payload,
            brand_id=person.brand_id,
        )
        await auth.db.flush()
        return await cls.interview_out(auth, interview)

    @classmethod
    async def update_interview_service(cls, auth: AuthSchema, person_id: int, interview_id: int, data: PersonInterviewSaveSchema) -> dict:
        person = await cls._person_exists(auth, person_id)
        await cls._ensure_write_access(auth, person_id)
        interview = await auth.db.get(DeepInterviewModel, interview_id)
        if not interview or interview.is_deleted or interview.person_id != person_id:
            raise CustomException(msg="深访记录不存在")
        if interview.interview_status == "voided":
            raise CustomException(msg="已作废深访不能编辑")
        interview.interview_scope = data.interview_scope
        interview.interview_type = data.interview_type
        interview.interview_method = data.interview_method
        interview.interviewed_at = data.interviewed_at or interview.interviewed_at
        interview.content = data.content
        interview.structured_payload = data.structured_payload
        interview.keywords = data.keywords
        interview.summary = data.summary
        interview.manual_notes = data.manual_notes
        cls._stamp_update(auth, interview)
        if interview.is_current_source:
            await cls._upsert_insight(
                auth,
                person_id=person_id,
                source_interview=interview,
                data=cls._insight_from_interview(data),
                profile_payload=data.structured_payload,
                brand_id=person.brand_id,
            )
        else:
            await MatchProfileService.mark_dirty(auth.db, person_id, ["self_profile", "preference"], "deep_interview", interview.id)
        await auth.db.flush()
        return await cls.interview_out(auth, interview)

    @classmethod
    async def void_interview_service(cls, auth: AuthSchema, person_id: int, interview_id: int, data: PersonInterviewVoidSchema) -> dict:
        await cls._person_exists(auth, person_id)
        await cls._ensure_write_access(auth, person_id)
        interview = await auth.db.get(DeepInterviewModel, interview_id)
        if not interview or interview.is_deleted or interview.person_id != person_id:
            raise CustomException(msg="深访记录不存在")
        interview.interview_status = "voided"
        interview.void_reason = data.reason
        interview.voided_by = auth.user.id if auth.user else None
        interview.voided_at = datetime.now()
        was_current = interview.is_current_source
        interview.is_current_source = False
        cls._stamp_update(auth, interview)
        if was_current:
            insight = (
                await auth.db.execute(
                    select(PersonProfileInsightModel).where(
                        PersonProfileInsightModel.person_id == person_id,
                        PersonProfileInsightModel.is_deleted == False,
                    )
                )
            ).scalars().first()
            if insight:
                insight.profile_status = "stale"
                cls._stamp_update(auth, insight)
        await MatchProfileService.mark_dirty(auth.db, person_id, ["self_profile", "preference"], "deep_interview_void", interview.id)
        await auth.db.flush()
        return await cls.interview_out(auth, interview)

    @classmethod
    async def profile_insight_service(cls, auth: AuthSchema, person_id: int) -> dict | None:
        await cls._person_exists(auth, person_id)
        await cls._ensure_read_access(auth, person_id)
        insight = (
            await auth.db.execute(
                select(PersonProfileInsightModel).where(
                    PersonProfileInsightModel.person_id == person_id,
                    PersonProfileInsightModel.is_deleted == False,
                )
            )
        ).scalars().first()
        return await cls.insight_out(auth, insight, person_id) if insight else None

    @classmethod
    async def update_profile_insight_service(cls, auth: AuthSchema, person_id: int, data: PersonProfileInsightSaveSchema) -> dict:
        person = await cls._person_exists(auth, person_id)
        await cls._ensure_write_access(auth, person_id)
        insight = await cls._upsert_insight(auth, person_id=person_id, source_interview=None, data=data, profile_payload=None, brand_id=person.brand_id)
        await auth.db.flush()
        return await cls.insight_out(auth, insight, person_id)

    @classmethod
    async def list_interviews_service(cls, auth: AuthSchema, person_id: int) -> list[dict]:
        await cls._person_exists(auth, person_id)
        await cls._ensure_read_access(auth, person_id)
        result = await auth.db.execute(
            select(DeepInterviewModel)
            .where(DeepInterviewModel.person_id == person_id, DeepInterviewModel.is_deleted == False)
            .order_by(DeepInterviewModel.interviewed_at.desc(), DeepInterviewModel.id.desc())
        )
        return [await cls.interview_out(auth, item) for item in result.scalars().all()]

    @classmethod
    async def get_interview_service(cls, auth: AuthSchema, person_id: int, interview_id: int) -> dict:
        await cls._person_exists(auth, person_id)
        await cls._ensure_read_access(auth, person_id)
        interview = await auth.db.get(DeepInterviewModel, interview_id)
        if not interview or interview.is_deleted or interview.person_id != person_id:
            raise CustomException(msg="深访记录不存在")
        return await cls.interview_out(auth, interview)

    @classmethod
    async def insight_out(cls, auth: AuthSchema, insight: PersonProfileInsightModel | None, person_id: int) -> dict:
        if not insight:
            return {"person_id": person_id, "profile_status": "none"}
        user_names = await cls._user_names(auth, {insight.updated_by_user_id})
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
            "updated_by_user_name": user_names.get(insight.updated_by_user_id),
            "insight_updated_at": insight.insight_updated_at,
            "source_interview_voided": source_voided,
        }

    @classmethod
    async def interview_out(cls, auth: AuthSchema, row: DeepInterviewModel) -> dict:
        user_names = await cls._user_names(auth, {row.matchmaker_id, row.created_id, row.voided_by})
        return {
            "id": row.id,
            "person_id": row.person_id,
            "interview_scope": row.interview_scope,
            "interview_type": row.interview_type,
            "interview_method": row.interview_method,
            "interviewed_at": row.interviewed_at,
            "content": row.content,
            "structured_payload": row.structured_payload or {},
            "keywords": row.keywords or [],
            "summary": row.summary,
            "manual_notes": row.manual_notes,
            "interview_status": row.interview_status,
            "is_current_source": row.is_current_source,
            "matchmaker_id": row.matchmaker_id,
            "matchmaker_name": user_names.get(row.matchmaker_id),
            "service_case_id": row.service_case_id,
            "vip_id": row.vip_id,
            "contract_id": row.contract_id,
            "customer_id": row.customer_id,
            "backup_item_id": row.backup_item_id,
            "void_reason": row.void_reason,
            "voided_by": row.voided_by,
            "voided_by_name": user_names.get(row.voided_by),
            "voided_at": row.voided_at,
            "created_by_name": user_names.get(row.created_id),
            "created_time": row.created_time,
        }
