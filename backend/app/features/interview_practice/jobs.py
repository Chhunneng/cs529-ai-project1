from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select

from app.db.session import AsyncSessionMaker
from app.features.interview_practice.interview_job_redis import publish_interview_job_updated
from app.features.job_queue.crewai_redis import enqueue_crewai_bridge_message
from app.llm.crewai.interview_crew import load_interview_practice_context_texts
from app.models.interview_practice import (
    InterviewAnswerAttempt,
    InterviewJobRequest,
    InterviewQuestion,
)
from app.queue_jobs import (
    CrewAiGenerateRequestMessage,
    CrewAiRefineRequestMessage,
    InterviewGenerateJob,
    InterviewGeneratePersistJob,
    InterviewRefineJob,
    InterviewRefinePersistJob,
)

log = structlog.get_logger()


async def _set_request_status(
    *,
    request_id: uuid.UUID,
    status: str,
    error_text: str | None = None,
    result_json: dict | None = None,
) -> None:
    async with AsyncSessionMaker() as db:
        row = await db.get(InterviewJobRequest, request_id)
        if row is None:
            return
        row.status = status
        row.error_text = error_text
        row.result_json = result_json
        await db.commit()
    await publish_interview_job_updated(request_id=request_id)


async def handle_interview_generate_job(job: InterviewGenerateJob) -> None:
    """Load session context and enqueue CrewAI generation (no HTTP to CrewAI)."""
    request_id = uuid.UUID(job.request_id)
    practice_session_id = uuid.UUID(job.practice_session_id)

    log.info(
        "interview_generate_prepare_start",
        interview_job_request_id=str(request_id),
        practice_session_id=str(practice_session_id),
        source=job.source,
        count=job.count,
    )
    await _set_request_status(request_id=request_id, status="running")

    try:
        job_description_text, resume_text = await load_interview_practice_context_texts(
            practice_session_id=practice_session_id,
            source=job.source,
        )
        if job.source in ("jd", "both") and not (job_description_text or "").strip():
            raise ValueError("Job description text is required when source is jd or both.")
        if job.source in ("resume", "both") and not (resume_text or "").strip():
            raise ValueError("Resume text is required when source is resume or both.")
        if job.question_style in ("domain", "language", "other"):
            if not (job.focus_detail or "").strip():
                raise ValueError(
                    "focus_detail is required when question_style is domain, language, or other.",
                )

        await enqueue_crewai_bridge_message(
            CrewAiGenerateRequestMessage(
                interview_job_request_id=str(request_id),
                practice_session_id=str(practice_session_id),
                source=job.source,
                count=int(job.count),
                job_description_text=job_description_text,
                resume_text=resume_text,
                question_style=job.question_style,
                level=job.level,
                focus_detail=job.focus_detail,
                attempt_count=0,
            )
        )
    except Exception as exception:
        log.exception("interview_generate_prepare_failed", interview_job_request_id=str(request_id))
        await _set_request_status(
            request_id=request_id,
            status="error",
            error_text=f"{type(exception).__name__}: {exception}",
        )


async def handle_interview_generate_persist_job(job: InterviewGeneratePersistJob) -> None:
    """Insert generated questions and mark the job request done (idempotent)."""
    request_id = uuid.UUID(job.interview_job_request_id)
    practice_session_id = uuid.UUID(job.practice_session_id)

    log.info(
        "interview_generate_persist_start",
        interview_job_request_id=str(request_id),
        practice_session_id=str(practice_session_id),
        success=job.success,
    )

    if not job.success:
        async with AsyncSessionMaker() as db:
            row = await db.get(InterviewJobRequest, request_id)
            if row is None or row.status in ("done", "error"):
                return
            row.status = "error"
            row.error_text = job.error_text or "CrewAI interview generation failed."
            await db.commit()
        await publish_interview_job_updated(request_id=request_id)
        return

    if not job.questions:
        await _set_request_status(
            request_id=request_id,
            status="error",
            error_text="CrewAI returned no questions to persist.",
        )
        return

    question_ids: list[uuid.UUID] = []
    async with AsyncSessionMaker() as db:
        row = await db.get(InterviewJobRequest, request_id)
        if row is None or row.status in ("done", "error"):
            return

        for item in job.questions:
            prompt = item.prompt.strip()
            sample_answer = item.sample_answer.strip()
            if not prompt or not sample_answer:
                continue
            question_row = InterviewQuestion(
                practice_session_id=practice_session_id,
                source=job.source,
                prompt=prompt,
                sample_answer=sample_answer,
                metadata_json=item.metadata if isinstance(item.metadata, dict) else {},
            )
            db.add(question_row)
            await db.flush()
            question_ids.append(question_row.id)

        if not question_ids:
            row.status = "error"
            row.error_text = "No valid questions were produced after CrewAI generation."
            await db.commit()
            await publish_interview_job_updated(request_id=request_id)
            return

        row.status = "done"
        row.result_json = {"question_ids": [str(question_id) for question_id in question_ids]}
        row.error_text = None
        await db.commit()

    await publish_interview_job_updated(request_id=request_id)

    log.info(
        "interview_generate_persist_done",
        interview_job_request_id=str(request_id),
        question_count=len(question_ids),
    )


async def handle_interview_refine_job(job: InterviewRefineJob) -> None:
    """Load question and answer context and enqueue CrewAI refine (no HTTP to CrewAI)."""
    request_id = uuid.UUID(job.request_id)
    practice_session_id = uuid.UUID(job.practice_session_id)
    answer_attempt_id = uuid.UUID(job.answer_attempt_id)

    log.info(
        "interview_refine_prepare_start",
        interview_job_request_id=str(request_id),
        practice_session_id=str(practice_session_id),
        answer_attempt_id=str(answer_attempt_id),
    )
    await _set_request_status(request_id=request_id, status="running")

    try:
        async with AsyncSessionMaker() as db:
            attempt = await db.get(InterviewAnswerAttempt, answer_attempt_id)
            if attempt is None:
                raise RuntimeError("Answer attempt not found.")
            question = await db.get(InterviewQuestion, attempt.question_id)
            if question is None:
                raise RuntimeError("Question not found for this attempt.")
            question_prompt = question.prompt
            question_ideal_answer = question.sample_answer
            user_answer_text = attempt.user_answer

        await enqueue_crewai_bridge_message(
            CrewAiRefineRequestMessage(
                interview_job_request_id=str(request_id),
                practice_session_id=str(practice_session_id),
                answer_attempt_id=str(answer_attempt_id),
                question=question_prompt,
                ideal_answer=question_ideal_answer,
                user_answer=user_answer_text,
                attempt_count=0,
            )
        )
    except Exception as exception:
        log.exception("interview_refine_prepare_failed", interview_job_request_id=str(request_id))
        await _set_request_status(
            request_id=request_id,
            status="error",
            error_text=f"{type(exception).__name__}: {exception}",
        )


async def handle_interview_refine_persist_job(job: InterviewRefinePersistJob) -> None:
    """Write refine feedback to the answer attempt (idempotent)."""
    request_id = uuid.UUID(job.interview_job_request_id)
    answer_attempt_id = uuid.UUID(job.answer_attempt_id)

    log.info(
        "interview_refine_persist_start",
        interview_job_request_id=str(request_id),
        answer_attempt_id=str(answer_attempt_id),
        success=job.success,
    )

    if not job.success:
        async with AsyncSessionMaker() as db:
            row = await db.get(InterviewJobRequest, request_id)
            if row is None or row.status in ("done", "error"):
                return
            row.status = "error"
            row.error_text = job.error_text or "CrewAI interview refine failed."
            await db.commit()
        await publish_interview_job_updated(request_id=request_id)
        return

    async with AsyncSessionMaker() as db:
        request_row = await db.get(InterviewJobRequest, request_id)
        if request_row is None or request_row.status in ("done", "error"):
            return

        attempt = await db.get(InterviewAnswerAttempt, answer_attempt_id)
        if attempt is None:
            request_row.status = "error"
            request_row.error_text = "Answer attempt not found when persisting refine result."
            await db.commit()
            await publish_interview_job_updated(request_id=request_id)
            return

        feedback = str(job.feedback or "").strip() or None
        refined_answer = str(job.refined_answer or "").strip() or None
        scores = job.scores if isinstance(job.scores, dict) else None

        attempt.feedback = feedback
        attempt.refined_answer = refined_answer
        attempt.scores_json = scores

        request_row.status = "done"
        request_row.result_json = {"answer_attempt_id": str(answer_attempt_id)}
        request_row.error_text = None
        await db.commit()

    await publish_interview_job_updated(request_id=request_id)

    log.info(
        "interview_refine_persist_done",
        interview_job_request_id=str(request_id),
        answer_attempt_id=str(answer_attempt_id),
    )


async def list_questions_for_session(*, practice_session_id: uuid.UUID) -> list[InterviewQuestion]:
    async with AsyncSessionMaker() as db:
        rows = (
            await db.execute(
                select(InterviewQuestion)
                .where(InterviewQuestion.practice_session_id == practice_session_id)
                .order_by(InterviewQuestion.created_at.asc())
            )
        ).scalars()
        return list(rows.all())


async def load_answer_attempt(*, answer_attempt_id: uuid.UUID) -> InterviewAnswerAttempt | None:
    async with AsyncSessionMaker() as db:
        return await db.get(InterviewAnswerAttempt, answer_attempt_id)
