from datetime import datetime

from pydantic import BaseModel, Field


class ResumeTemplateListItem(BaseModel):
    id: str
    name: str
    storage_path: str
    created_at: datetime


class ResumeTemplateDetail(BaseModel):
    id: str
    name: str
    storage_path: str
    latex_source: str | None = None
    schema_json: dict
    created_at: datetime
    updated_at: datetime | None = None


class ResumeTemplateCreateBody(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1)
    storage_path: str = Field(default="__inline__", min_length=1)
    latex_source: str | None = None
    schema_json: dict = Field(default_factory=dict)


class ResumeTemplatePatchBody(BaseModel):
    name: str | None = None
    storage_path: str | None = None
    latex_source: str | None = None
    schema_json: dict | None = None
