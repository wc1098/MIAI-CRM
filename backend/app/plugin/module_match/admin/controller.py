from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import SuccessResponse
from app.core.dependencies import AuthPermission

from ..schema import MatchDebugQuery
from ..service import MatchProfileService

MatchAdminRouter = APIRouter(prefix="/admin", tags=["匹配推荐后台调试"])


@MatchAdminRouter.get("/debug/candidates", summary="匹配推荐调试")
async def debug_candidates_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:match:debug"]))],
    query: Annotated[MatchDebugQuery, Depends()],
) -> JSONResponse:
    result = await MatchProfileService.candidate_debug(
        db=auth.db,
        person_id=query.person_id,
        display_no=query.display_no,
        scene=query.scene,
        page_no=query.page_no,
        page_size=query.page_size,
    )
    return SuccessResponse(data=result, msg="获取匹配推荐调试结果成功")


@MatchAdminRouter.post("/debug/person/{person_id}/dirty", summary="重建人员匹配向量")
async def rebuild_person_vector_controller(
    person_id: int,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["operation:miniprogram:match:debug"]))],
) -> JSONResponse:
    await MatchProfileService.mark_dirty(
        db=auth.db,
        person_id=person_id,
        dirty_parts=["self_profile", "preference"],
        source_type="admin_debug_rebuild",
        source_id=auth.user.id if auth.user else None,
    )
    return SuccessResponse(data={"person_id": person_id}, msg="已投递匹配向量重建任务")
