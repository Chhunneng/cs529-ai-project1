from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.job_queue.redis import enqueue_job
from app.features.interview_practice.repositories import create_job_request
from app.queue_jobs import InterviewGenerateJob, InterviewRefineJob


async def enqueue_generate_questions(
    db: AsyncSession,
    *,
    practice_session_id: uuid.UUID,
    source: str,
    count: int,
    question_style: str = "random",
    level: str = "random",
    focus_detail: str | None = None,
) -> uuid.UUID:
    req = await create_job_request(db, practice_session_id=practice_session_id, kind="generate")
    await enqueue_job(
        InterviewGenerateJob(
            request_id=str(req.id),
            practice_session_id=str(practice_session_id),
            source=source,  # type: ignore[arg-type]
            count=int(count),
            question_style=question_style,  # type: ignore[arg-type]
            level=level,  # type: ignore[arg-type]
            focus_detail=focus_detail,
        )
    )
    return req.id


async def enqueue_refine_answer(
    db: AsyncSession,
    *,
    practice_session_id: uuid.UUID,
    answer_attempt_id: uuid.UUID,
) -> uuid.UUID:
    req = await create_job_request(
        db,
        practice_session_id=practice_session_id,
        kind="refine",
        answer_attempt_id=answer_attempt_id,
    )
    await enqueue_job(
        InterviewRefineJob(
            request_id=str(req.id),
            practice_session_id=str(practice_session_id),
            answer_attempt_id=str(answer_attempt_id),
        )
    )
    return req.id

