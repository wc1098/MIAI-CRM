from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import SuccessResponse
from app.core.dependencies import db_getter
from app.core.exceptions import CustomException
from app.plugin.module_crm.preference.schema import (
    PartnerPreferenceMpUpdateSchema,
    PartnerPreferenceSaveSchema,
)
from app.plugin.module_crm.preference.service import PartnerPreferenceService
from app.plugin.module_mp.auth.dependencies import get_current_mp_user_id
from app.plugin.module_mp.auth.model import MiniProgramUserModel

MpProfileRouter = APIRouter(prefix="/profile", tags=["小程序个人资料"])


async def _current_user(db: AsyncSession, user_id: int) -> MiniProgramUserModel:
    result = await db.execute(
        select(MiniProgramUserModel).where(MiniProgramUserModel.id == user_id, MiniProgramUserModel.is_deleted == False)
    )
    user = result.scalars().first()
    if not user:
        raise CustomException(msg="小程序用户不存在", code=10401, status_code=401)
    if not user.registered_at or not user.person_id:
        raise CustomException(msg="请先完成注册资料", code=10402, status_code=401)
    return user


@MpProfileRouter.get("/preference", summary="获取我的择偶要求")
async def preference_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    user = await _current_user(db, user_id)
    result = await PartnerPreferenceService.bundle_out(db, user.person_id, 5)
    return SuccessResponse(data=result, msg="获取择偶要求成功")


@MpProfileRouter.put("/preference", summary="保存我的择偶要求")
async def update_preference_controller(
    data: PartnerPreferenceMpUpdateSchema,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    user = await _current_user(db, user_id)
    await PartnerPreferenceService.save(
        db,
        user.person_id,
        PartnerPreferenceSaveSchema(**data.model_dump(), source_type="miniapp", source_id=str(user.id)),
    )
    result = await PartnerPreferenceService.bundle_out(db, user.person_id, 5)
    return SuccessResponse(data=result, msg="保存择偶要求成功")
