from datetime import date, timedelta
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.plugin.module_crm.lead.model import CrmPersonModel
from app.plugin.module_mp.auth.model import MiniProgramUserModel


class MpPlazaService:
    """小程序广场用户列表服务。"""

    @classmethod
    def _age(cls, birth_date: date | None) -> int | None:
        if not birth_date:
            return None
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    @classmethod
    def _age_cutoff(cls, age: int) -> date:
        today = date.today()
        try:
            return today.replace(year=today.year - age)
        except ValueError:
            return today.replace(year=today.year - age, day=28)

    @classmethod
    def _masked_name(cls, name: str | None, gender: str | None) -> str:
        prefix = (name or "觅")[:1]
        suffix = {"0": "先生", "1": "女士"}.get(gender or "", "")
        return f"{prefix}{suffix}" if suffix else f"{prefix}**"

    @classmethod
    def _split_values(cls, value: str | None) -> list[str]:
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    @classmethod
    def _item_out(cls, user: MiniProgramUserModel, person: CrmPersonModel) -> dict[str, Any]:
        photo_urls = person.photo_urls or []
        return {
            "user_id": user.id,
            "person_id": person.id,
            "display_no": person.display_no,
            "nickname": user.nickname or cls._masked_name(person.name, person.gender),
            "avatar_url": user.avatar_url or (photo_urls[0] if photo_urls else None),
            "age": cls._age(person.birth_date),
            "gender": person.gender,
            "residence": person.residence,
            "height_cm": person.height_cm,
            "occupation": person.occupation,
            "annual_income": person.annual_income,
            "education": person.education,
            "marital_status": person.marital_status,
            "house_status": person.house_status,
            "car_status": person.car_status,
            "certification_status": "未认证",
            "registered_at": user.registered_at,
        }

    @classmethod
    async def _current_user(cls, db: AsyncSession, user_id: int | None) -> MiniProgramUserModel | None:
        if not user_id:
            return None
        result = await db.execute(
            select(MiniProgramUserModel)
            .where(MiniProgramUserModel.id == user_id, MiniProgramUserModel.is_deleted == False)
            .options(selectinload(MiniProgramUserModel.person))
        )
        return result.scalars().first()

    @classmethod
    async def list_service(
        cls,
        db: AsyncSession,
        user_id: int | None = None,
        page_no: int = 1,
        page_size: int = 20,
        display_no: str | None = None,
        gender: str | None = None,
        age_min: int | None = None,
        age_max: int | None = None,
        height_min: int | None = None,
        height_max: int | None = None,
        residence: str | None = None,
        education: str | None = None,
        marital_status: str | None = None,
        annual_income: str | None = None,
        house_status: str | None = None,
        car_status: str | None = None,
    ) -> dict[str, Any]:
        current_user = await cls._current_user(db, user_id)
        current_person = current_user.person if current_user and current_user.person_id else None
        effective_gender = gender
        if not effective_gender and current_person and current_person.gender in {"0", "1"}:
            effective_gender = "1" if current_person.gender == "0" else "0"

        conditions: list[Any] = [
            MiniProgramUserModel.person_id.is_not(None),
            MiniProgramUserModel.registered_at.is_not(None),
            MiniProgramUserModel.is_invisible == False,
            MiniProgramUserModel.is_deleted == False,
            CrmPersonModel.is_deleted == False,
            CrmPersonModel.display_no.is_not(None),
        ]
        if current_person:
            conditions.append(CrmPersonModel.id != current_person.id)
        if display_no:
            conditions.append(CrmPersonModel.display_no == display_no.strip())
        if effective_gender in {"0", "1"}:
            conditions.append(CrmPersonModel.gender == effective_gender)
        if age_min is not None:
            conditions.append(CrmPersonModel.birth_date <= cls._age_cutoff(age_min))
        if age_max is not None:
            conditions.append(CrmPersonModel.birth_date >= cls._age_cutoff(age_max + 1) + timedelta(days=1))
        if height_min is not None:
            conditions.append(CrmPersonModel.height_cm >= height_min)
        if height_max is not None:
            conditions.append(CrmPersonModel.height_cm <= height_max)
        if residence:
            conditions.append(CrmPersonModel.residence.like(f"%{residence.strip()}%"))
        education_values = cls._split_values(education)
        marital_status_values = cls._split_values(marital_status)
        annual_income_values = cls._split_values(annual_income)
        house_status_values = cls._split_values(house_status)
        car_status_values = cls._split_values(car_status)
        if education_values:
            conditions.append(CrmPersonModel.education.in_(education_values))
        if marital_status_values:
            conditions.append(CrmPersonModel.marital_status.in_(marital_status_values))
        if annual_income_values:
            conditions.append(CrmPersonModel.annual_income.in_(annual_income_values))
        if house_status_values:
            conditions.append(CrmPersonModel.house_status.in_(house_status_values))
        if car_status_values:
            conditions.append(CrmPersonModel.car_status.in_(car_status_values))

        total = (
            await db.execute(
                select(func.count(MiniProgramUserModel.id))
                .join(CrmPersonModel, MiniProgramUserModel.person_id == CrmPersonModel.id)
                .where(and_(*conditions))
            )
        ).scalar() or 0
        rows = (
            await db.execute(
                select(MiniProgramUserModel, CrmPersonModel)
                .join(CrmPersonModel, MiniProgramUserModel.person_id == CrmPersonModel.id)
                .where(and_(*conditions))
                .order_by(MiniProgramUserModel.registered_at.desc(), MiniProgramUserModel.id.desc())
                .offset((page_no - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": [cls._item_out(user, person) for user, person in rows],
        }
