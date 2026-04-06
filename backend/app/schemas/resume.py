import uuid
from datetime import datetime

from pydantic import BaseModel


class ResumeListItem(BaseModel):
    id: uuid.UUID
    created_at: datetime
    openai_file_id: str | None


class ResumeUploadRequest(BaseModel):
    filename: str


class ResumeUploadResponse(BaseModel):
    id: uuid.UUID

