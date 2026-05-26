from typing import Any, Literal

from pydantic import BaseModel, Field

MatchScene = Literal["subscription", "debug", "matchmaker_service"]


class MatchDebugQuery(BaseModel):
    person_id: int | None = Field(default=None, description="人员ID")
    display_no: str | None = Field(default=None, max_length=32, description="展示编号")
    scene: MatchScene = Field(default="debug", description="匹配场景")
    page_no: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class MatchCandidateOut(BaseModel):
    person_id: int
    display_no: str | None = None
    nickname: str | None = None
    gender: str | None = None
    age: int | None = None
    height_cm: int | None = None
    residence: str | None = None
    education: str | None = None
    annual_income: str | None = None
    marital_status: str | None = None
    match_score: int
    rank_score: int
    confidence_score: int
    structured_score: int
    vector_score: int | None = None
    vector_status: str
    matched_points: list[str] = Field(default_factory=list)
    risk_points: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    user_reason: str
    admin_reason: str


class MatchDebugOut(BaseModel):
    query_person_id: int
    query_display_no: str | None = None
    scene: MatchScene
    page_no: int
    page_size: int
    total: int
    has_next: bool
    model_info: dict[str, Any]
    vector_status: dict[str, Any]
    items: list[MatchCandidateOut]
