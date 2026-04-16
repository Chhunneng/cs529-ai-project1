from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


InterviewSource = Literal["jd", "resume", "both"]
InterviewQuestionStyle = Literal["random", "technical", "behavioral", "domain", "language", "other"]
InterviewQuestionLevel = Literal["random", "easy", "medium", "hard"]
InterviewJobKind = Literal["generate", "refine"]
InterviewJobStatus = Literal["pending", "running", "done", "error"]


class InterviewPracticeSessionCreateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resume_id: uuid.UUID | None = None
    job_description_id: uuid.UUID | None = None


class InterviewPracticeSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    resume_id: uuid.UUID | None
    job_description_id: uuid.UUID | None


class InterviewQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    practice_session_id: uuid.UUID
    created_at: datetime
    source: InterviewSource
    prompt: str
    sample_answer: str
    metadata_json: dict = Field(default_factory=dict)


class InterviewGenerateRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: InterviewSource = Field(..., description="Generate questions from jd, resume, or both.")
    count: int = Field(default=8, ge=1, le=25)
    question_style: InterviewQuestionStyle = Field(
        default="random",
        description="Focus: random mix, all technical, all behavioral, or domain/language/other (use focus_detail).",
    )
    level: InterviewQuestionLevel = Field(
        default="random",
        description="Difficulty: random mix or fixed easy/medium/hard for every question.",
    )
    focus_detail: str | None = Field(
        default=None,
        description="Required when question_style is domain, language, or other.",
    )

    @model_validator(mode="after")
    def _require_focus_detail(self) -> InterviewGenerateRequestBody:
        if self.question_style in ("domain", "language", "other"):
            if not (self.focus_detail or "").strip():
                raise ValueError("focus_detail is required for question_style domain, language, or other")
        return self


class InterviewGenerateEnqueueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: uuid.UUID


class InterviewJobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    practice_session_id: uuid.UUID
    kind: InterviewJobKind
    status: InterviewJobStatus
    created_at: datetime
    updated_at: datetime
    error_text: str | None = None
    result_json: dict | None = None


class InterviewAnswerCreateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_answer: str = Field(..., min_length=1)
    refine: bool = Field(default=False, description="If true, enqueue a refinement job.")


class InterviewAnswerAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    question_id: uuid.UUID
    created_at: datetime
    user_answer: str
    feedback: str | None = None
    refined_answer: str | None = None
    scores_json: dict | None = None


class InterviewRefineEnqueueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: uuid.UUID
    answer_attempt_id: uuid.UUID


class PaginatedInterviewPracticeSessionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[InterviewPracticeSessionResponse]
    total: int


class InterviewAnswerHistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: uuid.UUID
    question_prompt: str
    attempt: InterviewAnswerAttemptResponse

