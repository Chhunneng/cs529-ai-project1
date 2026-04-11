import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeOutputCreateBody(BaseModel):
    template_id: uuid.UUID
    source_resume_id: uuid.UUID | None = None
    job_description_id: uuid.UUID | None = None


class StandaloneResumePdfCreateBody(BaseModel):
    """Create an ATS-oriented PDF export without linking a chat session."""

    template_id: uuid.UUID
    source_resume_id: uuid.UUID
    job_description_id: uuid.UUID


class ResumeOutputResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID | None
    template_id: uuid.UUID | None
    status: str
    input_json: dict | None
    tex_path: str | None
    pdf_path: str | None
    error_text: str | None
    created_at: datetime
    updated_at: datetime
