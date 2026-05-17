from typing import Annotated

from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_common.upload.schema import UploadConfirmRequestSchema
from app.common.response import SuccessResponse
from app.core.dependencies import db_getter
from app.plugin.module_mp.auth.dependencies import get_current_mp_user_id

from ..schema import CertificationOrderCreateSchema, ManualSubmitSchema, RealNameSubmitSchema
from ..service import CertificationService

CertificationMpRouter = APIRouter(prefix="/mp", tags=["小程序认证中心"])


@CertificationMpRouter.get("/center", summary="小程序认证中心")
async def mp_certification_center_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await CertificationService.mp_center(db, user_id)
    return SuccessResponse(data=result, msg="获取认证中心成功")


@CertificationMpRouter.post("/orders", summary="创建认证订单")
async def mp_certification_order_create_controller(
    data: CertificationOrderCreateSchema,
    request: Request,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await CertificationService.create_order(db, request, user_id, data.package_id)
    return SuccessResponse(data=result, msg="创建认证订单成功")


@CertificationMpRouter.post("/orders/{order_id}/continue-pay", summary="继续支付认证订单")
async def mp_certification_continue_pay_controller(
    order_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await CertificationService.continue_pay(db, request, user_id, order_id)
    return SuccessResponse(data=result, msg="继续支付认证订单成功")


@CertificationMpRouter.get("/orders/{order_id}", summary="认证订单状态")
async def mp_certification_order_detail_controller(
    order_id: int,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await CertificationService.mp_order_detail(db, user_id, order_id)
    return SuccessResponse(data=result, msg="获取认证订单成功")


@CertificationMpRouter.get("/applications/{application_id}", summary="认证申请详情")
async def mp_certification_application_detail_controller(
    application_id: int,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await CertificationService.mp_application_detail(db, user_id, application_id)
    return SuccessResponse(data=result, msg="获取认证申请成功")


@CertificationMpRouter.post("/real-name", summary="提交实名认证")
async def mp_certification_real_name_controller(
    data: RealNameSubmitSchema,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await CertificationService.submit_real_name(db, user_id, data.name, data.id_card_no)
    return SuccessResponse(data=result, msg="实名认证提交成功")


@CertificationMpRouter.post("/materials/{item_code}/upload", summary="上传认证材料")
async def mp_certification_material_upload_controller(
    item_code: str,
    file: UploadFile,
    request: Request,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await CertificationService.upload_material(db, user_id, item_code, file, str(request.base_url))
    return SuccessResponse(data=result, msg="上传认证材料成功")


@CertificationMpRouter.post("/materials/{item_code}/confirm", summary="确认认证材料")
async def mp_certification_material_confirm_controller(
    item_code: str,
    data: UploadConfirmRequestSchema,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await CertificationService.confirm_material(db, user_id, item_code, data)
    return SuccessResponse(data=result, msg="上传认证材料成功")


@CertificationMpRouter.post("/manual", summary="提交人工认证项")
async def mp_certification_manual_submit_controller(
    data: ManualSubmitSchema,
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await CertificationService.submit_manual(db, user_id, data.item_code, data.payload)
    return SuccessResponse(data=result, msg="提交认证材料成功")
