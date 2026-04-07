import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ResumeTemplateListItem(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime


class ResumeTemplateDetail(BaseModel):
    id: uuid.UUID
    name: str
    latex_source: str
    schema_json: dict
    created_at: datetime
    updated_at: datetime | None = None


class ResumeTemplateCreateBody(BaseModel):
    name: str = Field(..., min_length=1)
    latex_source: str = Field(..., min_length=1)
    schema_json: dict = Field(default_factory=dict)


class ResumeTemplatePatchBody(BaseModel):
    name: str | None = None
    latex_source: str | None = Field(default=None, min_length=1)
    schema_json: dict | None = None
