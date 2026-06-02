from pydantic import BaseModel, Field


class MpEventRegisterSchema(BaseModel):
    source_id: str | None = None
    source_user_id: int | None = None
    payload: dict | None = None


class MpEventCheckinSchema(BaseModel):
    registration_id: int | None = Field(default=None, ge=1)
    payload: dict | None = None


class MpEventBarrageSchema(BaseModel):
    content: str = Field(..., min_length=1, max_length=50)
