from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from app.core.exceptions import CustomException
from app.plugin.module_crm.lead.model import CrmLeadProfileModel, CrmPersonModel
from app.plugin.module_mp.auth.model import MiniProgramUserModel, SourceEventModel

from .schema import MpPersonBriefSchema, MpUserOutSchema, MpUserQueryParam


class MpAdminService:
    """小程序后台管理服务。"""

    @classmethod
    async def page_users(
        cls,
        db,
        page_no: int,
        page_size: int,
        search: MpUserQueryParam | None = None,
    ) -> dict:
        conditions = [MiniProgramUserModel.is_deleted == False]
        join_person = False
        if search:
            if search.is_registered is True:
                conditions.append(MiniProgramUserModel.registered_at.is_not(None))
            elif search.is_registered is False:
                conditions.append(MiniProgramUserModel.registered_at.is_(None))
            if search.keyword:
                join_person = True
                keyword = f"%{search.keyword}%"
                conditions.append(
                    or_(
                        MiniProgramUserModel.nickname.like(keyword),
                        MiniProgramUserModel.mobile.like(keyword),
                        CrmPersonModel.name.like(keyword),
                        CrmPersonModel.primary_mobile.like(keyword),
                        CrmPersonModel.wechat.like(keyword),
                    )
                )

        count_stmt = select(func.count(MiniProgramUserModel.id)).where(and_(*conditions))
        rows_stmt = (
            select(MiniProgramUserModel)
            .where(and_(*conditions))
            .options(selectinload(MiniProgramUserModel.person))
            .order_by(MiniProgramUserModel.registered_at.desc(), MiniProgramUserModel.id.desc())
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        if join_person:
            count_stmt = count_stmt.outerjoin(CrmPersonModel, MiniProgramUserModel.person_id == CrmPersonModel.id)
            rows_stmt = rows_stmt.outerjoin(CrmPersonModel, MiniProgramUserModel.person_id == CrmPersonModel.id)

        total = (await db.execute(count_stmt)).scalar() or 0
        users = list((await db.execute(rows_stmt)).scalars().all())
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": await cls._decorate_users(db, users),
        }

    @classmethod
    async def detail_user(cls, db, user_id: int) -> dict:
        result = await db.execute(
            select(MiniProgramUserModel)
            .where(MiniProgramUserModel.id == user_id, MiniProgramUserModel.is_deleted == False)
            .options(selectinload(MiniProgramUserModel.person))
        )
        user = result.scalars().first()
        if not user:
            raise CustomException(msg="小程序用户不存在")
        return (await cls._decorate_users(db, [user]))[0]

    @classmethod
    async def _decorate_users(cls, db, users: list[MiniProgramUserModel]) -> list[dict]:
        if not users:
            return []
        user_ids = [user.id for user in users]
        person_ids = [user.person_id for user in users if user.person_id]

        lead_map: dict[int, int] = {}
        if person_ids:
            lead_rows = await db.execute(
                select(CrmLeadProfileModel.person_id, CrmLeadProfileModel.id)
                .where(CrmLeadProfileModel.person_id.in_(person_ids), CrmLeadProfileModel.is_deleted == False)
                .order_by(CrmLeadProfileModel.updated_time.desc(), CrmLeadProfileModel.id.desc())
            )
            for person_id, lead_id in lead_rows.all():
                lead_map.setdefault(person_id, lead_id)

        event_count_map: dict[int, int] = {}
        event_rows = await db.execute(
            select(SourceEventModel.user_id, func.count(SourceEventModel.id))
            .where(SourceEventModel.user_id.in_(user_ids), SourceEventModel.is_deleted == False)
            .group_by(SourceEventModel.user_id)
        )
        for user_id, count in event_rows.all():
            event_count_map[user_id] = int(count or 0)

        items: list[dict] = []
        for user in users:
            person = user.person
            person_data = None
            if person:
                person_data = MpPersonBriefSchema(
                    id=person.id,
                    name=person.name,
                    gender=person.gender,
                    primary_mobile=person.primary_mobile,
                    wechat=person.wechat,
                    birth_date=person.birth_date.isoformat() if person.birth_date else None,
                    height_cm=person.height_cm,
                    ethnicity=person.ethnicity,
                    occupation=person.occupation,
                    annual_income=person.annual_income,
                    marital_status=person.marital_status,
                    education=person.education,
                    hometown=person.hometown,
                    residence=person.residence,
                    house_status=person.house_status,
                    car_status=person.car_status,
                    photo_urls=person.photo_urls or [],
                )
            items.append(
                MpUserOutSchema(
                    id=user.id,
                    uuid=user.uuid,
                    status=user.status,
                    description=user.description,
                    created_time=user.created_time,
                    updated_time=user.updated_time,
                    is_deleted=user.is_deleted,
                    deleted_time=user.deleted_time,
                    brand_id=user.brand_id,
                    person_id=user.person_id,
                    openid=user.openid,
                    unionid=user.unionid,
                    mobile=user.mobile,
                    nickname=user.nickname,
                    avatar_url=user.avatar_url,
                    is_invisible=user.is_invisible,
                    allow_user_wall=user.allow_user_wall,
                    registered_at=user.registered_at,
                    last_login_at=user.last_login_at,
                    is_registered=bool(user.registered_at),
                    lead_id=lead_map.get(user.person_id or 0),
                    source_event_count=event_count_map.get(user.id, 0),
                    person=person_data,
                ).model_dump()
            )
        return items
