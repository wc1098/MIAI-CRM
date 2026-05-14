from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import SuccessResponse
from app.core.dependencies import AuthPermission

from .service import PersonAiProfileService

ProfileAiRouter = APIRouter(prefix="/person-ai-profile", tags=["人员AI画像"])


@ProfileAiRouter.get("/person/{person_id}", summary="查询人员觅AI印象")
async def person_profile_controller(
    person_id: Annotated[int, Path(description="人员ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:lead:all:detail", "operation:miniprogram:detail"], check_data_scope=False))],
) -> JSONResponse:
    result = await PersonAiProfileService.admin_info_map(auth.db, {person_id})
    return SuccessResponse(data=result.get(person_id, {"profile": None, "latest_task": None}), msg="查询觅AI印象成功")
