from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.dependencies import AuthPermission
from app.core.logger import log
from app.core.router_class import OperationLogRoute

from .schema import (
    ProductPackageChangeStatusSchema,
    ProductPackageCreateSchema,
    ProductPackageOutSchema,
    ProductPackageQueryParam,
    ProductPackageUpdateSchema,
)
from .service import ProductPackageService

ProductRouter = APIRouter(route_class=OperationLogRoute, prefix="/product", tags=["CRM产品管理"])


@ProductRouter.get(
    "/list",
    summary="查询产品套餐列表",
    description="查询产品套餐列表",
    response_model=ResponseSchema[list[ProductPackageOutSchema]],
)
async def get_product_list_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[ProductPackageQueryParam, Depends()],
    auth: Annotated[
        AuthSchema,
        Depends(
            AuthPermission(
                [
                    "crm:product:query",
                    "crm:contract:create",
                    "crm:contract:update",
                    "crm:contract:query",
                ]
            )
        ),
    ],
) -> JSONResponse:
    result_dict = await ProductPackageService.page_service(
        auth=auth,
        page_no=page.page_no,
        page_size=page.page_size,
        search=search,
    )
    log.info("查询产品套餐列表成功")
    return SuccessResponse(data=result_dict, msg="查询产品套餐列表成功")


@ProductRouter.get(
    "/detail/{id}",
    summary="查询产品套餐详情",
    description="查询产品套餐详情",
    response_model=ResponseSchema[ProductPackageOutSchema],
)
async def get_product_detail_controller(
    id: Annotated[int, Path(description="产品套餐ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:product:detail"]))],
) -> JSONResponse:
    result_dict = await ProductPackageService.detail_service(auth=auth, id=id)
    log.info(f"查询产品套餐详情成功 {id}")
    return SuccessResponse(data=result_dict, msg="查询产品套餐详情成功")


@ProductRouter.post(
    "/create",
    summary="创建产品套餐",
    description="创建产品套餐",
    response_model=ResponseSchema[ProductPackageOutSchema],
)
async def create_product_controller(
    data: ProductPackageCreateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:product:create"]))],
) -> JSONResponse:
    result_dict = await ProductPackageService.create_service(auth=auth, data=data)
    log.info(f"创建产品套餐成功: {result_dict.get('package_name')}")
    return SuccessResponse(data=result_dict, msg="创建产品套餐成功")


@ProductRouter.put(
    "/update/{id}",
    summary="修改产品套餐",
    description="修改产品套餐",
    response_model=ResponseSchema[ProductPackageOutSchema],
)
async def update_product_controller(
    data: ProductPackageUpdateSchema,
    id: Annotated[int, Path(description="产品套餐ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:product:update"]))],
) -> JSONResponse:
    result_dict = await ProductPackageService.update_service(auth=auth, id=id, data=data)
    log.info(f"修改产品套餐成功: {result_dict.get('package_name')}")
    return SuccessResponse(data=result_dict, msg="修改产品套餐成功")


@ProductRouter.put(
    "/change-status/{id}",
    summary="启用/禁用产品套餐",
    description="启用/禁用产品套餐",
    response_model=ResponseSchema[None],
)
async def change_product_status_controller(
    data: ProductPackageChangeStatusSchema,
    id: Annotated[int, Path(description="产品套餐ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:product:change_status"]))],
) -> JSONResponse:
    await ProductPackageService.change_status_service(auth=auth, id=id, data=data)
    log.info(f"产品套餐状态修改成功: {id}")
    return SuccessResponse(msg="产品套餐状态修改成功")


@ProductRouter.delete(
    "/delete/{id}",
    summary="删除产品套餐",
    description="删除产品套餐",
    response_model=ResponseSchema[None],
)
async def delete_product_controller(
    id: Annotated[int, Path(description="产品套餐ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["crm:product:delete"]))],
) -> JSONResponse:
    await ProductPackageService.delete_service(auth=auth, id=id)
    log.info(f"删除产品套餐成功: {id}")
    return SuccessResponse(msg="删除产品套餐成功")
