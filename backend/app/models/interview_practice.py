import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import JSON_TYPE, UUID_TYPE, TimestampMixin, UUIDPrimaryKeyMixin


class InterviewPracticeSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "interview_practice_sessions"

    resume_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True
    )
    job_description_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("job_descriptions.id", ondelete="SET NULL"), nullable=True
    )


class InterviewQuestion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "interview_questions"

    practice_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE,
        ForeignKey("interview_practice_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Where the question came from: jd, resume, or both.",
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    sample_answer: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False, default=dict)


class InterviewAnswerAttempt(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "interview_answer_attempts"

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE,
        ForeignKey("interview_questions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    user_answer: Mapped[str] = mapped_column(Text, nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    refined_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    scores_json: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)


class InterviewJobRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "interview_job_requests"

    practice_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE,
        ForeignKey("interview_practice_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(
        Text, nullable=False, doc="generate or refine (interview practice job kind)"
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="pending", doc="pending, running, done, error"
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("interview_questions.id", ondelete="SET NULL"), nullable=True
    )
    answer_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE,
        ForeignKey("interview_answer_attempts.id", ondelete="SET NULL"),
        nullable=True,
    )
    result_json: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)

