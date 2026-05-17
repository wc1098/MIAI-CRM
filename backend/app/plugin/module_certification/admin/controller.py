from typing import Annotated

from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import JSONResponse

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.dependencies import AuthPermission

from ..schema import (
    CertificationApplicationQueryParam,
    CertificationItemUpsertSchema,
    CertificationLogQueryParam,
    CertificationPackageUpsertSchema,
    CertificationRecordQueryParam,
    ReviewSchema,
    SensitiveViewSchema,
)
from ..service import CertificationService, detect_and_upload_photo

CertificationAdminRouter = APIRouter(prefix="/admin", tags=["认证后台管理"])


@CertificationAdminRouter.get("/items/list", summary="认证项配置列表")
async def admin_certification_items_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:certification:settings"]))],
) -> JSONResponse:
    result = await CertificationService.list_items(auth.db)
    return SuccessResponse(data=result, msg="获取认证项成功")


@CertificationAdminRouter.put("/items/{item_code}", summary="修改认证项配置")
async def admin_certification_item_update_controller(
    item_code: str,
    data: CertificationItemUpsertSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:certification:settings"]))],
) -> JSONResponse:
    result = await CertificationService.save_item(auth.db, item_code, data)
    return SuccessResponse(data=result, msg="保存认证项成功")


@CertificationAdminRouter.get("/packages/list", summary="认证套餐列表")
async def admin_certification_packages_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:certification:query"]))],
) -> JSONResponse:
    result = await CertificationService.list_packages(auth.db)
    return SuccessResponse(data=result, msg="获取认证套餐成功")


@CertificationAdminRouter.put("/packages/{level_code}", summary="修改认证套餐")
async def admin_certification_package_update_controller(
    level_code: str,
    data: CertificationPackageUpsertSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:certification:settings"]))],
) -> JSONResponse:
    result = await CertificationService.save_package(auth.db, level_code, data)
    return SuccessResponse(data=result, msg="保存认证套餐成功")


@CertificationAdminRouter.get("/applications/list", summary="认证申请列表")
async def admin_certification_applications_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:certification:query"]))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[CertificationApplicationQueryParam, Depends()],
) -> JSONResponse:
    result = await CertificationService.page_applications(auth.db, page.page_no, page.page_size, search)
    return SuccessResponse(data=result, msg="获取认证申请成功")


@CertificationAdminRouter.get("/applications/{application_id}", summary="认证申请详情")
async def admin_certification_application_detail_controller(
    application_id: int,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:certification:query"]))],
) -> JSONResponse:
    result = await CertificationService.admin_application_detail(auth.db, application_id)
    return SuccessResponse(data=result, msg="获取认证申请详情成功")


@CertificationAdminRouter.get("/person/{person_id}/summary", summary="人员认证概览")
async def admin_certification_person_summary_controller(
    person_id: int,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:certification:query"]))],
) -> JSONResponse:
    result = await CertificationService.admin_person_summary(auth.db, person_id)
    return SuccessResponse(data=result, msg="获取人员认证概览成功")


@CertificationAdminRouter.get("/records/list", summary="认证单项记录列表")
async def admin_certification_records_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["review:task:query"]))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[CertificationRecordQueryParam, Depends()],
) -> JSONResponse:
    result = await CertificationService.page_records(auth.db, page.page_no, page.page_size, search)
    return SuccessResponse(data=result, msg="获取认证记录成功")


@CertificationAdminRouter.get("/verification-logs/list", summary="实名核验日志列表")
async def admin_certification_verification_logs_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:certification:query"]))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[CertificationLogQueryParam, Depends()],
) -> JSONResponse:
    result = await CertificationService.page_verification_logs(auth.db, page.page_no, page.page_size, search)
    return SuccessResponse(data=result, msg="获取实名核验日志成功")


@CertificationAdminRouter.get("/face-logs/list", summary="人脸检测日志列表")
async def admin_certification_face_logs_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:certification:query"]))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[CertificationLogQueryParam, Depends()],
) -> JSONResponse:
    result = await CertificationService.page_face_logs(auth.db, page.page_no, page.page_size, search)
    return SuccessResponse(data=result, msg="获取人脸检测日志成功")


@CertificationAdminRouter.post("/records/{record_id}/review", summary="审核认证项")
async def admin_certification_review_controller(
    record_id: int,
    data: ReviewSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["review:task:cert_review"]))],
) -> JSONResponse:
    result = await CertificationService.review_record(auth.db, record_id, auth.user.id if auth.user else None, data.action, data.reject_reason)
    return SuccessResponse(data=result, msg="审核认证项成功")


@CertificationAdminRouter.post("/person/{person_id}/id-card/view", summary="查看完整身份证号")
async def admin_certification_id_card_view_controller(
    person_id: int,
    data: SensitiveViewSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:person:view_id_card"]))],
) -> JSONResponse:
    result = await CertificationService.view_id_card(auth.db, person_id, auth.user.id if auth.user else None, data.reason)
    return SuccessResponse(data=result, msg="查看身份证号成功")


@CertificationAdminRouter.post("/photo/upload", summary="后台上传用户照片并检测人脸")
async def admin_certification_photo_upload_controller(
    file: UploadFile,
    request: Request,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:certification:settings"]))],
) -> JSONResponse:
    result = await detect_and_upload_photo(auth.db, str(request.base_url), file, business_type="admin_photo_upload")
    return SuccessResponse(data=result, msg="上传照片成功")
