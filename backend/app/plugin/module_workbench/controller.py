from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import ResponseSchema, SuccessResponse
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .schema import (
    NodesQueryParam,
    SummaryQueryParam,
    TasksQueryParam,
    WorkbenchNodesSchema,
    WorkbenchSummarySchema,
    WorkbenchTaskGroupSchema,
)
from .service import WorkbenchService

WorkbenchRouter = APIRouter(route_class=OperationLogRoute, tags=["角色工作台"])


@WorkbenchRouter.get("/summary", summary="查询工作台汇总", response_model=ResponseSchema[WorkbenchSummarySchema])
async def summary_controller(
    search: Annotated[SummaryQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["workbench:overview:query", "dashboard:workplace:query"]))],
) -> JSONResponse:
    result = await WorkbenchService.summary_service(auth=auth, search=search)
    return SuccessResponse(data=result, msg="查询工作台汇总成功")


@WorkbenchRouter.get("/tasks", summary="查询工作台任务", response_model=ResponseSchema[WorkbenchTaskGroupSchema])
async def tasks_controller(
    search: Annotated[TasksQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["workbench:overview:query", "dashboard:workplace:query"]))],
) -> JSONResponse:
    result = await WorkbenchService.tasks_service(auth=auth, search=search)
    return SuccessResponse(data=result, msg="查询工作台任务成功")


@WorkbenchRouter.get("/nodes", summary="查询工作台节点状态", response_model=ResponseSchema[WorkbenchNodesSchema])
async def nodes_controller(
    search: Annotated[NodesQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["workbench:overview:query", "dashboard:workplace:query"]))],
) -> JSONResponse:
    result = await WorkbenchService.nodes_service(auth=auth, search=search)
    return SuccessResponse(data=result, msg="查询工作台节点状态成功")
