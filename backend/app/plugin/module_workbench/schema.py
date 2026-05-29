from typing import Any

from fastapi import Query
from pydantic import BaseModel, Field


class WorkbenchMetricSchema(BaseModel):
    key: str
    title: str
    value: int | float | str
    unit: str | None = None
    hint: str | None = None
    priority: str = "primary"
    route_path: str | None = None
    query: dict[str, Any] = Field(default_factory=dict)


class WorkbenchSummarySchema(BaseModel):
    role_type: str
    role_name: str
    range: str
    scope: str
    metrics: list[WorkbenchMetricSchema] = Field(default_factory=list)


class WorkbenchTaskSchema(BaseModel):
    id: str
    task_type: str
    title: str
    object_type: str
    object_id: int
    object_name: str | None = None
    status: str
    due_at: str | None = None
    owner_user_id: int | None = None
    owner_user_name: str | None = None
    priority: str = "primary"
    action_text: str
    route_path: str
    query: dict[str, Any] = Field(default_factory=dict)


class WorkbenchTaskGroupSchema(BaseModel):
    role_type: str
    bucket: str
    total: int
    items: list[WorkbenchTaskSchema] = Field(default_factory=list)


class WorkbenchNodeSchema(BaseModel):
    key: str
    title: str
    count: int
    priority: str = "primary"
    route_path: str
    query: dict[str, Any] = Field(default_factory=dict)


class WorkbenchNodeGroupSchema(BaseModel):
    key: str
    title: str
    nodes: list[WorkbenchNodeSchema] = Field(default_factory=list)


class WorkbenchNodesSchema(BaseModel):
    role_type: str
    scope: str
    groups: list[WorkbenchNodeGroupSchema] = Field(default_factory=list)


class SummaryQueryParam:  # noqa: B903
    def __init__(
        self,
        range: str = Query("today", pattern="^(today|week|month)$", description="统计范围"),
        store_id: int | None = Query(None, description="门店ID"),
    ) -> None:
        self.range = range
        self.store_id = store_id


class TasksQueryParam:  # noqa: B903
    def __init__(
        self,
        bucket: str = Query("today", pattern="^(today|overdue|upcoming)$", description="任务分组"),
        days: int = Query(7, ge=1, le=30, description="未来日程天数"),
        limit: int = Query(50, ge=1, le=200, description="返回上限"),
    ) -> None:
        self.bucket = bucket
        self.days = days
        self.limit = limit


class NodesQueryParam:  # noqa: B903
    def __init__(
        self,
        scope: str = Query("mine", pattern="^(mine|store)$", description="统计范围"),
        store_id: int | None = Query(None, description="门店ID"),
    ) -> None:
        self.scope = scope
        self.store_id = store_id
