"""Redis payloads for the CrewAI worker queue (backend producer, CrewAI consumer)."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class CrewAiGenerateRequestMessage(BaseModel):
    """Work item: generate interview questions via CrewAI (no HTTP from backend)."""

    model_config = ConfigDict(extra="forbid")

    message_type: Literal["crewai_generate_request"] = "crewai_generate_request"
    interview_job_request_id: str
    practice_session_id: str
    source: Literal["jd", "resume", "both"]
    count: int
    job_description_text: str | None = None
    resume_text: str | None = None
    question_style: Literal["random", "technical", "behavioral", "domain", "language", "other"] = "random"
    level: Literal["random", "easy", "medium", "hard"] = "random"
    focus_detail: str | None = None
    attempt_count: int = 0


class CrewAiRefineRequestMessage(BaseModel):
    """Work item: refine an answer via CrewAI."""

    # Ignore unknown keys from older queue payloads (e.g. removed job_description_text).
    model_config = ConfigDict(extra="ignore")

    message_type: Literal["crewai_refine_request"] = "crewai_refine_request"
    interview_job_request_id: str
    practice_session_id: str
    answer_attempt_id: str
    question: str
    ideal_answer: str
    user_answer: str
    attempt_count: int = 0


_CrewAiBridgeMessage = Annotated[
    Union[CrewAiGenerateRequestMessage, CrewAiRefineRequestMessage],
    Field(discriminator="message_type"),
]

_crewai_bridge_adapter = TypeAdapter(_CrewAiBridgeMessage)

type CrewAiBridgeMessage = CrewAiGenerateRequestMessage | CrewAiRefineRequestMessage


def serialize_crewai_bridge_message(message: CrewAiBridgeMessage) -> str:
    """Serialize a CrewAI queue message for RPUSH."""
    return message.model_dump_json()


def deserialize_crewai_bridge_message(raw: str) -> CrewAiBridgeMessage:
    """Parse a CrewAI queue message from BLPOP / BRPOPLPUSH."""
    return _crewai_bridge_adapter.validate_json(raw)
