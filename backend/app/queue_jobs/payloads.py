"""Redis queue job payloads (API enqueue, worker dequeue)."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class ResumePdfGenerationJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["resume_pdf_generation"] = "resume_pdf_generation"
    session_id: str
    user_message_id: str
    resume_template_id: str | None = None
    resume_id: str | None = None
    job_description_id: str | None = None


class RenderResumeJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["render_resume"] = "render_resume"
    output_id: str
    template_id: str
    session_id: str | None = None


class ParseResumeJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["parse_resume"] = "parse_resume"
    resume_id: str


class InterviewGenerateJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["interview_generate"] = "interview_generate"
    request_id: str
    practice_session_id: str
    source: Literal["jd", "resume", "both"]
    count: int
    question_style: Literal["random", "technical", "behavioral", "domain", "language", "other"] = "random"
    level: Literal["random", "easy", "medium", "hard"] = "random"
    focus_detail: str | None = None


class InterviewRefineJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["interview_refine"] = "interview_refine"
    request_id: str
    practice_session_id: str
    answer_attempt_id: str


class InterviewQuestionWire(BaseModel):
    """Question payload produced by CrewAI and persisted by the main worker."""

    model_config = ConfigDict(extra="forbid")

    prompt: str
    sample_answer: str
    metadata: dict = Field(default_factory=dict)


class InterviewGeneratePersistJob(BaseModel):
    """Persist step after CrewAI returns generated questions (or an error)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["interview_generate_persist"] = "interview_generate_persist"
    interview_job_request_id: str
    practice_session_id: str
    source: Literal["jd", "resume", "both"]
    success: bool
    questions: list[InterviewQuestionWire] | None = None
    error_text: str | None = None


class InterviewRefinePersistJob(BaseModel):
    """Persist step after CrewAI returns refine feedback (or an error)."""

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


_DiscriminatedAgentJob = Annotated[
    Union[
        ResumePdfGenerationJob,
        RenderResumeJob,
        ParseResumeJob,
        InterviewGenerateJob,
        InterviewRefineJob,
        InterviewGeneratePersistJob,
        InterviewRefinePersistJob,
    ],
    Field(discriminator="type"),
]

_job_adapter = TypeAdapter(_DiscriminatedAgentJob)

type AgentJob = (
    ResumePdfGenerationJob
    | RenderResumeJob
    | ParseResumeJob
    | InterviewGenerateJob
    | InterviewRefineJob
    | InterviewGeneratePersistJob
    | InterviewRefinePersistJob
)


def parse_agent_job(
    data: object,
) -> (
    ResumePdfGenerationJob
    | RenderResumeJob
    | ParseResumeJob
    | InterviewGenerateJob
    | InterviewRefineJob
    | InterviewGeneratePersistJob
    | InterviewRefinePersistJob
):
    """Factory: validate dict / parsed JSON into a concrete job model."""
    return _job_adapter.validate_python(data)


def serialize_job(
    job: ResumePdfGenerationJob
    | RenderResumeJob
    | ParseResumeJob
    | InterviewGenerateJob
    | InterviewRefineJob
    | InterviewGeneratePersistJob
    | InterviewRefinePersistJob,
) -> str:
    """Adapter: domain model → Redis wire string."""
    return job.model_dump_json()


def deserialize_job(
    raw: str,
) -> (
    ResumePdfGenerationJob
    | RenderResumeJob
    | ParseResumeJob
    | InterviewGenerateJob
    | InterviewRefineJob
    | InterviewGeneratePersistJob
    | InterviewRefinePersistJob
):
    """Adapter: Redis wire string → domain model (validates)."""
    return _job_adapter.validate_json(raw)
