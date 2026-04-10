import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SessionCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    resume_id: uuid.UUID | None
    job_description_id: uuid.UUID | None
    resume_template_id: uuid.UUID | None
    state_json: dict = Field(default_factory=dict)
