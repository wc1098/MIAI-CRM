from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.auth.schema import AuthSchema
from app.plugin.module_match.service import MatchProfileService

from .model import PersonPartnerPreferenceModel, PersonPartnerPreferenceVersionModel
from .schema import (
    PartnerPreferenceOutSchema,
    PartnerPreferencePayload,
    PartnerPreferenceSaveSchema,
    PartnerPreferenceVersionOutSchema,
)


class PartnerPreferenceService:
    """择偶要求服务。"""

    PRIORITY = {
        "miniapp": 10,
        "admin": 20,
        "matchmaker": 30,
        "deep_interview": 100,
        "import": 5,
    }

    COPY_FIELDS = [
        "age_min",
        "age_max",
        "height_min_cm",
        "height_max_cm",
        "weight_min_kg",
        "weight_max_kg",
        "preferred_residence_region_codes",
        "preferred_hometown_region_codes",
        "preferred_education_codes",
        "preferred_marital_status_codes",
        "preferred_annual_income_codes",
        "preferred_house_status_codes",
        "preferred_car_status_codes",
        "accept_long_distance",
        "accept_divorced",
        "accept_children",
        "children_requirement",
        "preferred_personality_tags",
        "preferred_lifestyle_tags",
        "preferred_relationship_tags",
        "hard_reject_items",
        "soft_preference_items",
        "preferred_occupation_text",
        "preference_text",
        "strictness_level",
        "must_match_fields",
        "preferred_match_fields",
        "profile_summary",
    ]

    @classmethod
    def _stamp_create(cls, auth: AuthSchema | None, obj: Any, admin_user_id: int | None = None) -> None:
        user_id = admin_user_id or (auth.user.id if auth and auth.user else None)
        if user_id:
            if hasattr(obj, "created_id"):
                obj.created_id = user_id
            if hasattr(obj, "updated_id"):
                obj.updated_id = user_id

    @classmethod
    def _stamp_update(cls, auth: AuthSchema | None, obj: Any, admin_user_id: int | None = None) -> None:
        user_id = admin_user_id or (auth.user.id if auth and auth.user else None)
        if user_id and hasattr(obj, "updated_id"):
            obj.updated_id = user_id

    @classmethod
    def _priority(cls, source_type: str, force_final: bool = False) -> int:
        if force_final:
            return cls.PRIORITY["deep_interview"]
        return cls.PRIORITY.get(source_type, 20)

    @classmethod
    async def current(cls, db: AsyncSession, person_id: int) -> PersonPartnerPreferenceModel | None:
        result = await db.execute(
            select(PersonPartnerPreferenceModel).where(
                PersonPartnerPreferenceModel.person_id == person_id,
                PersonPartnerPreferenceModel.is_deleted == False,
            )
        )
        return result.scalars().first()

    @classmethod
    async def current_out(cls, db: AsyncSession, person_id: int) -> dict | None:
        current = await cls.current(db, person_id)
        return PartnerPreferenceOutSchema.model_validate(current).model_dump() if current else None

    @classmethod
    async def versions_out(cls, db: AsyncSession, person_id: int, limit: int = 10) -> list[dict]:
        rows = (
            await db.execute(
                select(PersonPartnerPreferenceVersionModel)
                .where(
                    PersonPartnerPreferenceVersionModel.person_id == person_id,
                    PersonPartnerPreferenceVersionModel.is_deleted == False,
                )
                .order_by(PersonPartnerPreferenceVersionModel.version_no.desc(), PersonPartnerPreferenceVersionModel.id.desc())
                .limit(limit)
            )
        ).scalars().all()
        return [PartnerPreferenceVersionOutSchema.model_validate(row).model_dump() for row in rows]

    @classmethod
    async def bundle_out(cls, db: AsyncSession, person_id: int, limit: int = 10) -> dict:
        return {"current": await cls.current_out(db, person_id), "versions": await cls.versions_out(db, person_id, limit)}

    @classmethod
    async def map_current(cls, db: AsyncSession, person_ids: set[int]) -> dict[int, dict]:
        if not person_ids:
            return {}
        rows = (
            await db.execute(
                select(PersonPartnerPreferenceModel).where(
                    PersonPartnerPreferenceModel.person_id.in_(person_ids),
                    PersonPartnerPreferenceModel.is_deleted == False,
                )
            )
        ).scalars().all()
        return {row.person_id: PartnerPreferenceOutSchema.model_validate(row).model_dump() for row in rows}

    @classmethod
    def _snapshot(cls, preference: PersonPartnerPreferenceModel) -> dict[str, Any]:
        return {field: getattr(preference, field) for field in cls.COPY_FIELDS}

    @classmethod
    async def save(
        cls,
        db: AsyncSession,
        person_id: int,
        data: PartnerPreferenceSaveSchema | PartnerPreferencePayload,
        *,
        auth: AuthSchema | None = None,
        source_type: str | None = None,
        source_id: str | int | None = None,
        force_final: bool | None = None,
        admin_user_id: int | None = None,
    ) -> PersonPartnerPreferenceModel:
        save_data = data if isinstance(data, PartnerPreferenceSaveSchema) else PartnerPreferenceSaveSchema(
            **data.model_dump(),
            source_type=source_type or "admin",
            source_id=str(source_id) if source_id is not None else None,
            force_final=bool(force_final),
        )
        if source_type:
            save_data.source_type = source_type  # type: ignore[misc]
        if source_id is not None:
            save_data.source_id = str(source_id)
        if force_final is not None:
            save_data.force_final = force_final

        current = await cls.current(db, person_id)
        latest_version = (
            await db.execute(
                select(func.max(PersonPartnerPreferenceVersionModel.version_no)).where(
                    PersonPartnerPreferenceVersionModel.person_id == person_id,
                    PersonPartnerPreferenceVersionModel.is_deleted == False,
                )
            )
        ).scalar() or 0
        version_no = int(latest_version) + 1
        source = save_data.source_type
        is_final_candidate = bool(save_data.force_final or source == "deep_interview")
        priority = cls._priority(source, is_final_candidate)
        should_replace_current = current is None or is_final_candidate or not current.is_final

        if should_replace_current:
            if current is None:
                current = PersonPartnerPreferenceModel(brand_id=1, person_id=person_id)
                cls._stamp_create(auth, current, admin_user_id)
                db.add(current)
            else:
                cls._stamp_update(auth, current, admin_user_id)
            for field in cls.COPY_FIELDS:
                setattr(current, field, getattr(save_data, field))
            current.source_type = source
            current.source_id = save_data.source_id
            current.priority = priority
            current.is_effective = True
            current.is_final = is_final_candidate
            current.version_no = version_no
            current.vector_dirty = True
            await db.flush()

        snapshot = save_data.model_dump(exclude={"source_type", "source_id", "force_final"})
        version = PersonPartnerPreferenceVersionModel(
            brand_id=1,
            person_id=person_id,
            preference_id=current.id if current else None,
            version_no=version_no,
            source_type=source,
            source_id=save_data.source_id,
            priority=priority,
            is_effective=should_replace_current,
            is_final=is_final_candidate,
            snapshot=snapshot,
        )
        cls._stamp_create(auth, version, admin_user_id)
        db.add(version)
        await MatchProfileService.mark_dirty(
            db=db,
            person_id=person_id,
            dirty_parts=["preference"],
            source_type=source,
            source_id=save_data.source_id or version_no,
        )
        await db.flush()
        return current
