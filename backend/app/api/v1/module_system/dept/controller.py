from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path
from fastapi.responses import JSONResponse

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import BatchSetAvailable
from app.core.dependencies import AuthPermission
from app.core.logger import log
from app.core.router_class import OperationLogRoute

from .schema import DeptCreateSchema, DeptOutSchema, DeptQueryParam, DeptUpdateSchema
from .service import DeptService

DeptRouter = APIRouter(route_class=OperationLogRoute, prefix="/dept", tags=["门店管理"])


@DeptRouter.get(
    "/tree",
    summary="查询门店树",
    description="查询门店树",
    response_model=ResponseSchema[list[DeptOutSchema]],
)
async def get_dept_tree_controller(
    search: Annotated[DeptQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_system:dept:query"]))],
) -> JSONResponse:
    """
    查询门店树

    参数:
    - search (DeptQueryParam): 查询参数模型
    - auth (AuthSchema): 认证信息模型

    返回:
    - JSONResponse: 包含门店树的响应模型

    异常:
    - CustomException: 查询门店树失败时抛出异常。
    """
    order_by = [{"order": "asc"}]
    result_dict_list = await DeptService.get_dept_tree_service(
        search=search, auth=auth, order_by=order_by
    )
    log.info("查询门店树成功")
    return SuccessResponse(data=result_dict_list, msg="查询门店树成功")


@DeptRouter.get(
    "/detail/{id}",
    summary="查询门店详情",
    description="查询门店详情",
    response_model=ResponseSchema[DeptOutSchema],
)
async def get_obj_detail_controller(
    id: Annotated[int, Path(description="门店ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_system:dept:detail"]))],
) -> JSONResponse:
    """
    查询门店详情

    参数:
    - id (int): 门店ID
    - auth (AuthSchema): 认证信息模型

    返回:
    - JSONResponse: 包含门店详情的响应模型

    异常:
    - CustomException: 查询门店详情失败时抛出异常。
    """
    result_dict = await DeptService.get_dept_detail_service(id=id, auth=auth)
    log.info(f"查询门店详情成功 {id}")
    return SuccessResponse(data=result_dict, msg="查询门店详情成功")


@DeptRouter.post(
    "/create",
    summary="创建门店",
    description="创建门店",
    response_model=ResponseSchema[DeptOutSchema],
)
async def create_obj_controller(
    data: DeptCreateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_system:dept:create"]))],
) -> JSONResponse:
    """
    创建门店

    参数:
    - data (DeptCreateSchema): 创建门店负载模型
    - auth (AuthSchema): 认证信息模型

    返回:
    - JSONResponse: 包含创建门店结果的响应模型

    异常:
    - CustomException: 创建门店失败时抛出异常。
    """
    result_dict = await DeptService.create_dept_service(data=data, auth=auth)
    log.info(f"创建门店成功: {result_dict}")
    return SuccessResponse(data=result_dict, msg="创建门店成功")


@DeptRouter.put(
    "/update/{id}",
    summary="修改门店",
    description="修改门店",
    response_model=ResponseSchema[DeptOutSchema],
)
async def update_obj_controller(
    data: DeptUpdateSchema,
    id: Annotated[int, Path(description="门店ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_system:dept:update"]))],
) -> JSONResponse:
    """
    修改门店

    参数:
    - data (DeptUpdateSchema): 修改门店负载模型
    - id (int): 门店ID
    - auth (AuthSchema): 认证信息模型

    返回:
    - JSONResponse: 包含修改门店结果的响应模型

    异常:
    - CustomException: 修改门店失败时抛出异常。
    """
    result_dict = await DeptService.update_dept_service(auth=auth, id=id, data=data)
    log.info(f"修改门店成功: {result_dict}")
    return SuccessResponse(data=result_dict, msg="修改门店成功")


@DeptRouter.delete(
    "/delete",
    summary="删除门店",
    description="删除门店",
    response_model=ResponseSchema[None],
)
async def delete_obj_controller(
    ids: Annotated[list[int], Body(description="ID列表")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_system:dept:delete"]))],
) -> JSONResponse:
    """
    删除门店

    参数:
    - ids (list[int]): 门店ID列表
    - auth (AuthSchema): 认证信息模型

    返回:
    - JSONResponse: 包含删除门店结果的响应模型

    异常:
    - CustomException: 删除门店失败时抛出异常。
    """
    await DeptService.delete_dept_service(ids=ids, auth=auth)
    log.info(f"删除门店成功: {ids}")
    return SuccessResponse(msg="删除门店成功")


@DeptRouter.patch(
    "/available/setting",
    summary="批量修改门店状态",
    description="批量修改门店状态",
    response_model=ResponseSchema[None],
)
async def batch_set_available_obj_controller(
    data: BatchSetAvailable,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_system:dept:patch"]))],
) -> JSONResponse:
    """
    批量修改门店状态

    参数:
    - data (BatchSetAvailable): 批量修改门店状态负载模型
    - auth (AuthSchema): 认证信息模型

    返回:
    - JSONResponse: 包含批量修改门店状态结果的响应模型

    异常:
    - CustomException: 批量修改门店状态失败时抛出异常。
    """
    await DeptService.batch_set_available_service(data=data, auth=auth)
    log.info(f"批量修改门店状态成功: {data.ids}")
    return SuccessResponse(msg="批量修改门店状态成功")
