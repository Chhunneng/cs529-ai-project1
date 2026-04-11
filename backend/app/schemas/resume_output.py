import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeOutputCreateBody(BaseModel):
    template_id: uuid.UUID
    source_resume_id: uuid.UUID | None = None
    job_description_id: uuid.UUID | None = None


class ResumeOutputResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    template_id: uuid.UUID | None
    status: str
    input_json: dict | None
    tex_path: str | None
    pdf_path: str | None
    error_text: str | None
    created_at: datetime
    updated_at: datetime
