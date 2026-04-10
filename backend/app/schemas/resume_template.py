import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResumeTemplateListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    valid: bool
    created_at: datetime


class ResumeTemplateDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    latex_source: str
    valid: bool
    created_at: datetime
    updated_at: datetime | None = None


class ResumeTemplateCreateBody(BaseModel):
    name: str = Field(..., min_length=1)
    latex_source: str = Field(..., min_length=1)


class ResumeTemplatePatchBody(BaseModel):
    name: str | None = None
    latex_source: str | None = Field(default=None, min_length=1)


class ResumeTemplateGenerateBody(BaseModel):
    requirements: str = Field(..., min_length=10, max_length=5000, strip_whitespace=True)


class ResumeTemplateGenerateResponse(BaseModel):
    latex_resume_content: str


class ResumeTemplateFixBody(BaseModel):
    latex_source: str = Field(..., min_length=100, max_length=5000, strip_whitespace=True)
    error_message: str = Field(..., min_length=10, max_length=5000, strip_whitespace=True)


class ResumeTemplateValidateBody(BaseModel):
    latex_source: str = Field(..., min_length=1, max_length=5000, strip_whitespace=True)


class ResumeTemplateValidateResponse(BaseModel):
    """Whether the given source compiles with pdflatex (same path as PDF preview)."""

    ok: bool
    message: str | None = None
    latex_error: str | None = None
    line_number: int | None = None
    line_context: str | None = None
    hint: str | None = None
