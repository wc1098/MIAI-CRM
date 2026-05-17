from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.core.router_class import OperationLogRoute

from .schema import (
    OssPolicyRequestSchema,
    OssPolicyResponseSchema,
    UploadConfirmRequestSchema,
    UploadConfirmResponseSchema,
)
from .service import CommonUploadService

UploadRouter = APIRouter(route_class=OperationLogRoute, prefix="/upload", tags=["统一上传"])


@UploadRouter.post(
    "/oss-policy",
    summary="获取 OSS 直传凭证",
    response_model=ResponseSchema[OssPolicyResponseSchema],
)
async def oss_policy_controller(data: OssPolicyRequestSchema) -> JSONResponse:
    result = await CommonUploadService.create_oss_policy(data)
    return SuccessResponse(data=result, msg="获取上传凭证成功")


@UploadRouter.post(
    "/confirm",
    summary="确认 OSS 直传文件",
    response_model=ResponseSchema[UploadConfirmResponseSchema],
)
async def upload_confirm_controller(data: UploadConfirmRequestSchema) -> JSONResponse:
    result = await CommonUploadService.confirm_uploaded_object(data)
    return SuccessResponse(data=result, msg="确认上传成功")
