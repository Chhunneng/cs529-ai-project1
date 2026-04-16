"""Wire contracts matching backend ``app.queue_jobs`` (duplicate for standalone CrewAI image)."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class CrewAiGenerateRequestMessage(BaseModel):
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
    model_config = ConfigDict(extra="ignore")

    message_type: Literal["crewai_refine_request"] = "crewai_refine_request"
    interview_job_request_id: str
    practice_session_id: str
    answer_attempt_id: str
    question: str
    ideal_answer: str
    user_answer: str
    attempt_count: int = 0


_CrewAiBridge = Annotated[
    Union[CrewAiGenerateRequestMessage, CrewAiRefineRequestMessage],
    Field(discriminator="message_type"),
]

_crewai_bridge_adapter = TypeAdapter(_CrewAiBridge)


def parse_crewai_bridge_message(raw: str) -> CrewAiGenerateRequestMessage | CrewAiRefineRequestMessage:
    return _crewai_bridge_adapter.validate_json(raw)


class InterviewQuestionWire(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str
    sample_answer: str
    metadata: dict = Field(default_factory=dict)


class InterviewGeneratePersistJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["interview_generate_persist"] = "interview_generate_persist"
    interview_job_request_id: str
    practice_session_id: str
    source: Literal["jd", "resume", "both"]
    success: bool
    questions: list[InterviewQuestionWire] | None = None
    error_text: str | None = None


class InterviewRefinePersistJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["interview_refine_persist"] = "interview_refine_persist"
    interview_job_request_id: str
    practice_session_id: str
    answer_attempt_id: str
    success: bool
    feedback: str | None = None
    refined_answer: str | None = None
    scores: dict | None = None
    error_text: str | None = None


def serialize_persist_job(job: InterviewGeneratePersistJob | InterviewRefinePersistJob) -> str:
    return job.model_dump_json()
