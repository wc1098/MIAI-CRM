from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.dependencies import db_getter
from app.plugin.module_mp.auth.dependencies import get_optional_mp_user_id

from .service import MpPlazaService

MpPlazaRouter = APIRouter(prefix="/plaza", tags=["小程序广场"])


@MpPlazaRouter.get("/list", summary="小程序广场用户列表", response_model=ResponseSchema[dict])
async def plaza_list_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int | None, Depends(get_optional_mp_user_id)],
    page_no: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
    display_no: Annotated[str | None, Query(min_length=7, max_length=7, pattern=r"^[1-9]\d{6}$")] = None,
    gender: Annotated[str | None, Query(pattern=r"^[01]$")] = None,
    age_min: Annotated[int | None, Query(ge=18, le=100)] = None,
    age_max: Annotated[int | None, Query(ge=18, le=100)] = None,
    height_min: Annotated[int | None, Query(ge=80, le=260)] = None,
    height_max: Annotated[int | None, Query(ge=80, le=260)] = None,
    residence: Annotated[str | None, Query(max_length=128)] = None,
    education: Annotated[str | None, Query(max_length=160)] = None,
    marital_status: Annotated[str | None, Query(max_length=160)] = None,
    annual_income: Annotated[str | None, Query(max_length=160)] = None,
    house_status: Annotated[str | None, Query(max_length=160)] = None,
    car_status: Annotated[str | None, Query(max_length=160)] = None,
) -> JSONResponse:
    result = await MpPlazaService.list_service(
        db=db,
        user_id=user_id,
        page_no=page_no,
        page_size=page_size,
        display_no=display_no,
        gender=gender,
        age_min=age_min,
        age_max=age_max,
        height_min=height_min,
        height_max=height_max,
        residence=residence,
        education=education,
        marital_status=marital_status,
        annual_income=annual_income,
        house_status=house_status,
        car_status=car_status,
    )
    return SuccessResponse(data=result, msg="查询广场用户成功")
