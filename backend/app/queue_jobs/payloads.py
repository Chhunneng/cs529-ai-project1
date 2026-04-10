"""Redis queue job payloads (API enqueue, worker dequeue)."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class ResumePdfGenerationJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["resume_pdf_generation"] = "resume_pdf_generation"
    session_id: str
    user_message_id: str
    input_hash: str
    resume_template_id: str | None = None
    resume_id: str | None = None
    job_description_id: str | None = None


class RenderResumeJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["render_resume"] = "render_resume"
    output_id: str
    session_id: str
    template_id: str


class ParseResumeJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["parse_resume"] = "parse_resume"
    resume_id: str


_DiscriminatedAgentJob = Annotated[
    Union[ResumePdfGenerationJob, RenderResumeJob, ParseResumeJob], Field(discriminator="type")
]

_job_adapter = TypeAdapter(_DiscriminatedAgentJob)

type AgentJob = ResumePdfGenerationJob | RenderResumeJob | ParseResumeJob


def parse_agent_job(data: object) -> ResumePdfGenerationJob | RenderResumeJob | ParseResumeJob:
    """Factory: validate dict / parsed JSON into a concrete job model."""
    return _job_adapter.validate_python(data)


def serialize_job(job: ResumePdfGenerationJob | RenderResumeJob | ParseResumeJob) -> str:
    """Adapter: domain model → Redis wire string."""
    return job.model_dump_json()


def deserialize_job(raw: str) -> ResumePdfGenerationJob | RenderResumeJob | ParseResumeJob:
    """Adapter: Redis wire string → domain model (validates)."""
    return _job_adapter.validate_json(raw)
