import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SessionPatchRequest(BaseModel):
    selected_resume_id: uuid.UUID | None = None
    active_jd_id: uuid.UUID | None = None
    state_json: dict | None = None


class MessageCreateBody(BaseModel):
    content: str = Field(..., min_length=1)
