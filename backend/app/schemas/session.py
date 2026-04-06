import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreateResponse(BaseModel):
    id: uuid.UUID


class SessionResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    selected_resume_id: uuid.UUID | None
    active_jd_id: uuid.UUID | None
    state_json: dict = Field(default_factory=dict)

