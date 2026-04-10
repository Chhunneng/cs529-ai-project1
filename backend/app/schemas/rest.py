import uuid

from pydantic import BaseModel, ConfigDict, Field


class SessionPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resume_id: uuid.UUID | None = None
    job_description_id: uuid.UUID | None = None
    resume_template_id: uuid.UUID | None = None
    state_json: dict | None = None


class SessionMessageCreateBody(BaseModel):

    model_config = ConfigDict(extra="forbid")

    content: str = Field(..., min_length=1)
    resume_template_id: uuid.UUID
    resume_id: uuid.UUID
    job_description_id: uuid.UUID
