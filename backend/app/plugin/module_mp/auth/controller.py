from typing import Annotated

from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.dependencies import db_getter

from .dependencies import get_current_mp_user_id
from .schema import MpAuthOutSchema, MpLoginSchema, MpRegisterSchema
from .service import MpAuthService

MpAuthRouter = APIRouter(prefix="/auth", tags=["小程序认证"])


@MpAuthRouter.post("/login", summary="小程序微信登录", response_model=ResponseSchema[MpAuthOutSchema])
async def login_controller(
    data: MpLoginSchema,
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await MpAuthService.login(db=db, data=data)
    return SuccessResponse(data=result, msg="小程序登录成功")


@MpAuthRouter.post("/register", summary="小程序注册并接入CRM线索", response_model=ResponseSchema[MpAuthOutSchema])
async def register_controller(
    data: MpRegisterSchema,
    request: Request,
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await MpAuthService.register(
        db=db,
        data=data,
        ip=request.client.host if request.client else None,
        device_info=request.headers.get("user-agent"),
    )
    return SuccessResponse(data=result, msg="小程序注册成功")


@MpAuthRouter.get("/register-options", summary="获取小程序注册选项")
async def register_options_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await MpAuthService.register_options(db=db)
    return SuccessResponse(data=result, msg="获取小程序注册选项成功")


@MpAuthRouter.post("/register-photo/upload", summary="上传小程序注册照片")
async def register_photo_upload_controller(
    file: UploadFile,
    request: Request,
) -> JSONResponse:
    result = await MpAuthService.upload_register_photo(base_url=str(request.base_url), file=file)
    return SuccessResponse(data=result, msg="上传注册照片成功")


@MpAuthRouter.get("/me", summary="获取当前小程序用户", response_model=ResponseSchema[MpAuthOutSchema])
async def me_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Depends(get_current_mp_user_id)],
) -> JSONResponse:
    result = await MpAuthService.me(db=db, user_id=user_id)
    return SuccessResponse(data=result, msg="获取小程序用户成功")
