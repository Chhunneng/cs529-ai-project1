import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class JobDescriptionCreateBody(BaseModel):
    raw_text: str = Field(..., min_length=1)
    set_active: bool = True


class JobDescriptionResponse(BaseModel):
    id: uuid.UUID
    raw_text: str
    extracted_json: dict | None
    created_at: datetime
    updated_at: datetime

