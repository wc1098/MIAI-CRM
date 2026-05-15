from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Request
from fastapi.responses import JSONResponse
from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.dependencies import db_getter, redis_getter
from app.plugin.module_mp.auth.dependencies import get_current_mp_user_id, get_optional_mp_user_id

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


@MpPlazaRouter.get("/detail/{display_no}", summary="小程序广场用户详情", response_model=ResponseSchema[dict])
async def plaza_detail_controller(
    display_no: Annotated[str, Path(min_length=7, max_length=7, pattern=r"^[1-9]\d{6}$")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int | None, Depends(get_optional_mp_user_id)],
) -> JSONResponse:
    result = await MpPlazaService.detail_service(db=db, display_no=display_no, user_id=user_id)
    return SuccessResponse(data=result, msg="获取广场用户详情成功")


@MpPlazaRouter.post("/{display_no}/like", summary="喜欢用户", response_model=ResponseSchema[dict])
async def plaza_like_controller(
    display_no: str,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpPlazaService.like_service(db=db, display_no=display_no, user_id=user_id)
    return SuccessResponse(data=result, msg="已喜欢")


@MpPlazaRouter.delete("/{display_no}/like", summary="取消喜欢用户", response_model=ResponseSchema[dict])
async def plaza_unlike_controller(
    display_no: str,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpPlazaService.unlike_service(db=db, display_no=display_no, user_id=user_id)
    return SuccessResponse(data=result, msg="已取消喜欢")


@MpPlazaRouter.post("/{display_no}/favorite", summary="收藏用户", response_model=ResponseSchema[dict])
async def plaza_favorite_controller(
    display_no: str,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpPlazaService.favorite_service(db=db, display_no=display_no, user_id=user_id)
    return SuccessResponse(data=result, msg="已收藏")


@MpPlazaRouter.delete("/{display_no}/favorite", summary="取消收藏用户", response_model=ResponseSchema[dict])
async def plaza_unfavorite_controller(
    display_no: str,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpPlazaService.unfavorite_service(db=db, display_no=display_no, user_id=user_id)
    return SuccessResponse(data=result, msg="已取消收藏")


@MpPlazaRouter.post("/{display_no}/unlock/heartbeat", summary="使用心动值解锁联系方式", response_model=ResponseSchema[dict])
async def plaza_unlock_heartbeat_controller(
    display_no: str,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpPlazaService.unlock_by_heartbeat_service(db=db, display_no=display_no, user_id=user_id)
    return SuccessResponse(data=result, msg="心动值解锁成功")


@MpPlazaRouter.get("/{display_no}/unlock/progress", summary="联系方式解锁进度", response_model=ResponseSchema[dict])
async def plaza_unlock_progress_controller(
    display_no: str,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpPlazaService.unlock_progress_service(db=db, display_no=display_no, user_id=user_id)
    return SuccessResponse(data=result, msg="获取解锁进度成功")


@MpPlazaRouter.post("/{display_no}/unlock/task/{task_code}", summary="完成联系方式解锁任务", response_model=ResponseSchema[dict])
async def plaza_unlock_task_controller(
    display_no: str,
    task_code: str,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpPlazaService.complete_task_service(db=db, display_no=display_no, task_code=task_code, user_id=user_id)
    return SuccessResponse(data=result, msg="任务完成")


@MpPlazaRouter.get("/{display_no}/unlock/questions", summary="联系方式解锁默契题", response_model=ResponseSchema[dict])
async def plaza_unlock_questions_controller(
    display_no: str,
    db: Annotated[AsyncSession, Depends(db_getter)],
    redis: Annotated[Redis, Depends(redis_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpPlazaService.unlock_questions_service(db=db, display_no=display_no, user_id=user_id, redis=redis)
    return SuccessResponse(data=result, msg="获取默契题成功")


@MpPlazaRouter.post("/{display_no}/unlock/questions/{question_id}/answer", summary="提交联系方式解锁默契题", response_model=ResponseSchema[dict])
async def plaza_unlock_answer_controller(
    display_no: str,
    question_id: int,
    answer: Annotated[dict, Body()],
    db: Annotated[AsyncSession, Depends(db_getter)],
    redis: Annotated[Redis, Depends(redis_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpPlazaService.answer_question_service(
        db=db,
        display_no=display_no,
        question_id=question_id,
        answer_value=str(answer.get("answer_value", "")),
        user_id=user_id,
        redis=redis,
    )
    return SuccessResponse(data=result, msg="提交默契题成功")


@MpPlazaRouter.post("/{display_no}/unlock/coupon", summary="使用免费券解锁联系方式", response_model=ResponseSchema[dict])
async def plaza_unlock_coupon_controller(
    display_no: str,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpPlazaService.unlock_by_coupon_service(db=db, display_no=display_no, user_id=user_id)
    return SuccessResponse(data=result, msg="免费券解锁成功")


@MpPlazaRouter.post("/{display_no}/unlock/final/task-free", summary="最后一步使用心动值解锁", response_model=ResponseSchema[dict])
async def plaza_unlock_final_task_controller(
    display_no: str,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpPlazaService.final_task_free_service(db=db, display_no=display_no, user_id=user_id)
    return SuccessResponse(data=result, msg="心动值解锁成功")


@MpPlazaRouter.post("/{display_no}/unlock/final/coupon", summary="最后一步使用免费券解锁", response_model=ResponseSchema[dict])
async def plaza_unlock_final_coupon_controller(
    display_no: str,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpPlazaService.final_coupon_service(db=db, display_no=display_no, user_id=user_id)
    return SuccessResponse(data=result, msg="免费券解锁成功")


@MpPlazaRouter.post("/{display_no}/unlock/pay", summary="付费解锁联系方式", response_model=ResponseSchema[dict])
async def plaza_unlock_pay_controller(
    display_no: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpPlazaService.unlock_by_pay_service(db=db, request=request, display_no=display_no, user_id=user_id)
    return SuccessResponse(data=result, msg="解锁订单创建成功")


@MpPlazaRouter.post("/{display_no}/unlock/final/pay", summary="最后一步付费补足解锁", response_model=ResponseSchema[dict])
async def plaza_unlock_final_pay_controller(
    display_no: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpPlazaService.final_pay_service(db=db, request=request, display_no=display_no, user_id=user_id)
    return SuccessResponse(data=result, msg="解锁订单创建成功")


@MpPlazaRouter.get("/{display_no}/unlock/contact", summary="查看已解锁手机号", response_model=ResponseSchema[dict])
async def plaza_unlock_contact_controller(
    display_no: str,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpPlazaService.contact_service(db=db, display_no=display_no, user_id=user_id)
    return SuccessResponse(data=result, msg="获取手机号成功")


@MpPlazaRouter.post("/unlock/pay/{order_id}/continue", summary="继续支付联系方式解锁订单", response_model=ResponseSchema[dict])
async def plaza_unlock_pay_continue_controller(
    order_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpPlazaService.continue_unlock_pay_service(db=db, request=request, order_id=order_id, user_id=user_id)
    return SuccessResponse(data=result, msg="继续支付请求成功")
