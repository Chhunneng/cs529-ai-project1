"""Redis queue job payloads (API enqueue, worker dequeue)."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class ChatMessageJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["chat_message"] = "chat_message"
    session_id: str
    message_id: str
    input_hash: str


class RenderResumeJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["render_resume"] = "render_resume"
    output_id: str
    session_id: str
    template_id: str


_DiscriminatedAgentJob = Annotated[
    Union[ChatMessageJob, RenderResumeJob], Field(discriminator="type")
]

_job_adapter = TypeAdapter(_DiscriminatedAgentJob)

type AgentJob = ChatMessageJob | RenderResumeJob


def parse_agent_job(data: object) -> ChatMessageJob | RenderResumeJob:
    """Factory: validate dict / parsed JSON into a concrete job model."""
    return _job_adapter.validate_python(data)


def serialize_job(job: ChatMessageJob | RenderResumeJob) -> str:
    """Adapter: domain model → Redis wire string."""
    return job.model_dump_json()


def deserialize_job(raw: str) -> ChatMessageJob | RenderResumeJob:
    """Adapter: Redis wire string → domain model (validates)."""
    return _job_adapter.validate_json(raw)
