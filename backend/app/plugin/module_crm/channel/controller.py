from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import ResponseSchema, StreamResponse, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.base_schema import BatchSetAvailable
from app.core.dependencies import AuthPermission
from app.core.logger import log
from app.core.router_class import OperationLogRoute
from app.utils.common_util import bytes2file_response

from .schema import ChannelCreateSchema, ChannelOutSchema, ChannelQueryParam, ChannelUpdateSchema
from .service import ChannelService

ChannelRouter = APIRouter(route_class=OperationLogRoute, prefix="/channel", tags=["CRM渠道管理"])


@ChannelRouter.get(
    "/list",
    summary="查询渠道列表",
    description="查询渠道列表",
    response_model=ResponseSchema[list[ChannelOutSchema]],
)
async def get_obj_list_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[ChannelQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:channel:query"]))],
) -> JSONResponse:
    result_dict = await ChannelService.page_service(
        auth=auth,
        page_no=page.page_no,
        page_size=page.page_size,
        search=search,
        order_by=page.order_by,
    )
    log.info("查询渠道列表成功")
    return SuccessResponse(data=result_dict, msg="查询渠道列表成功")


@ChannelRouter.get(
    "/detail/{id}",
    summary="查询渠道详情",
    description="查询渠道详情",
    response_model=ResponseSchema[ChannelOutSchema],
)
async def get_obj_detail_controller(
    id: Annotated[int, Path(description="渠道ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:channel:detail"]))],
) -> JSONResponse:
    result_dict = await ChannelService.detail_service(auth=auth, id=id)
    log.info(f"查询渠道详情成功 {id}")
    return SuccessResponse(data=result_dict, msg="查询渠道详情成功")


@ChannelRouter.post(
    "/create",
    summary="创建渠道",
    description="创建渠道",
    response_model=ResponseSchema[ChannelOutSchema],
)
async def create_obj_controller(
    data: ChannelCreateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:channel:create"]))],
) -> JSONResponse:
    result_dict = await ChannelService.create_service(auth=auth, data=data)
    log.info(f"创建渠道成功: {result_dict.get('channel_code')}")
    return SuccessResponse(data=result_dict, msg="创建渠道成功")


@ChannelRouter.put(
    "/update/{id}",
    summary="修改渠道",
    description="修改渠道",
    response_model=ResponseSchema[ChannelOutSchema],
)
async def update_obj_controller(
    data: ChannelUpdateSchema,
    id: Annotated[int, Path(description="渠道ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:channel:update"]))],
) -> JSONResponse:
    result_dict = await ChannelService.update_service(auth=auth, id=id, data=data)
    log.info(f"修改渠道成功: {result_dict.get('channel_code')}")
    return SuccessResponse(data=result_dict, msg="修改渠道成功")


@ChannelRouter.delete(
    "/delete",
    summary="删除渠道",
    description="删除渠道",
    response_model=ResponseSchema[None],
)
async def delete_obj_controller(
    ids: Annotated[list[int], Body(description="ID列表")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:channel:delete"]))],
) -> JSONResponse:
    await ChannelService.delete_service(auth=auth, ids=ids)
    log.info(f"删除渠道成功: {ids}")
    return SuccessResponse(msg="删除渠道成功")


@ChannelRouter.patch(
    "/available/setting",
    summary="批量修改渠道状态",
    description="批量修改渠道状态",
    response_model=ResponseSchema[None],
)
async def batch_set_available_obj_controller(
    data: BatchSetAvailable,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:channel:patch"]))],
) -> JSONResponse:
    await ChannelService.set_available_service(auth=auth, data=data)
    log.info(f"批量修改渠道状态成功: {data.ids}")
    return SuccessResponse(msg="批量修改渠道状态成功")


@ChannelRouter.post(
    "/export",
    summary="导出渠道",
    description="导出渠道",
)
async def export_obj_list_controller(
    search: Annotated[ChannelQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:channel:export"]))],
) -> StreamingResponse:
    result_dict_list = await ChannelService.list_service(auth=auth, search=search)
    export_result = await ChannelService.export_service(obj_list=result_dict_list)
    log.info("导出渠道成功")
    return StreamResponse(
        data=bytes2file_response(export_result),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=crm_channel.xlsx"},
    )
