from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview_practice import (
    InterviewAnswerAttempt,
    InterviewJobRequest,
    InterviewPracticeSession,
    InterviewQuestion,
)


async def create_practice_session(
    db: AsyncSession,
    *,
    resume_id: uuid.UUID | None,
    job_description_id: uuid.UUID | None,
) -> InterviewPracticeSession:
    row = InterviewPracticeSession(resume_id=resume_id, job_description_id=job_description_id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def load_practice_session(
    db: AsyncSession,
    *,
    practice_session_id: uuid.UUID,
) -> InterviewPracticeSession | None:
    return await db.get(InterviewPracticeSession, practice_session_id)


async def count_practice_sessions(db: AsyncSession) -> int:
    n = await db.scalar(select(func.count()).select_from(InterviewPracticeSession))
    return int(n or 0)


async def list_practice_sessions(
    db: AsyncSession,
    *,
    limit: int,
    offset: int,
) -> list[InterviewPracticeSession]:
    result = await db.execute(
        select(InterviewPracticeSession)
        .order_by(InterviewPracticeSession.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def list_answer_attempts_with_questions_for_session(
    db: AsyncSession,
    *,
    practice_session_id: uuid.UUID,
) -> list[tuple[InterviewAnswerAttempt, InterviewQuestion]]:
    """Return (attempt, question) rows for all answers in this practice session, newest attempt first."""
    stmt = (
        select(InterviewAnswerAttempt, InterviewQuestion)
        .join(InterviewQuestion, InterviewAnswerAttempt.question_id == InterviewQuestion.id)
        .where(InterviewQuestion.practice_session_id == practice_session_id)
        .order_by(InterviewAnswerAttempt.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.all())


async def create_job_request(
    db: AsyncSession,
    *,
    practice_session_id: uuid.UUID,
    kind: str,
    question_id: uuid.UUID | None = None,
    answer_attempt_id: uuid.UUID | None = None,
) -> InterviewJobRequest:
    row = InterviewJobRequest(
        practice_session_id=practice_session_id,
        kind=kind,
        status="pending",
        question_id=question_id,
        answer_attempt_id=answer_attempt_id,
        result_json=None,
        error_text=None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def load_job_request(db: AsyncSession, *, request_id: uuid.UUID) -> InterviewJobRequest | None:
    return await db.get(InterviewJobRequest, request_id)


async def list_questions(
    db: AsyncSession,
    *,
    practice_session_id: uuid.UUID,
) -> list[InterviewQuestion]:
    result = await db.execute(
        select(InterviewQuestion)
        .where(InterviewQuestion.practice_session_id == practice_session_id)
        .order_by(InterviewQuestion.created_at.asc())
    )
    return list(result.scalars().all())


async def load_question(db: AsyncSession, *, question_id: uuid.UUID) -> InterviewQuestion | None:
    return await db.get(InterviewQuestion, question_id)


async def load_answer_attempt_for_practice_session(
    db: AsyncSession,
    *,
    answer_attempt_id: uuid.UUID,
    practice_session_id: uuid.UUID,
) -> InterviewAnswerAttempt | None:
    """Return the attempt only if its question belongs to the given practice session."""
    attempt = await db.get(InterviewAnswerAttempt, answer_attempt_id)
    if attempt is None:
        return None
    q = await db.get(InterviewQuestion, attempt.question_id)
    if q is None or q.practice_session_id != practice_session_id:
        return None
    return attempt


async def upsert_answer_attempt(
    db: AsyncSession,
    *,
    question_id: uuid.UUID,
    user_answer: str,
) -> tuple[InterviewAnswerAttempt, bool]:
    """Insert or update the single attempt row for this question. Returns (row, created)."""
    existing = await db.scalar(
        select(InterviewAnswerAttempt).where(InterviewAnswerAttempt.question_id == question_id)
    )
    if existing is not None:
        existing.user_answer = user_answer
        existing.feedback = None
        existing.refined_answer = None
        existing.scores_json = None
        await db.commit()
        await db.refresh(existing)
        return existing, False

    row = InterviewAnswerAttempt(
        question_id=question_id,
        user_answer=user_answer,
        feedback=None,
        refined_answer=None,
        scores_json=None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row, True

