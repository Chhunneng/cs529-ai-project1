"""Paginated list envelopes for list endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schemas.job_description import JobDescriptionResponse
from app.schemas.resume import ResumeListItem
from app.schemas.resume_template import ResumeTemplateListItem
from app.schemas.session import SessionResponse


class PaginatedResumesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ResumeListItem]
    total: int


class PaginatedResumeTemplatesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ResumeTemplateListItem]
    total: int


class PaginatedSessionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SessionResponse]
    total: int


class PaginatedJobDescriptionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[JobDescriptionResponse]
    total: int
