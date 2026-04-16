from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.features.interview_practice.repositories import (
    count_practice_sessions,
    upsert_answer_attempt,
    create_practice_session,
    list_answer_attempts_with_questions_for_session,
    list_practice_sessions,
    list_questions,
    load_answer_attempt_for_practice_session,
    load_job_request,
    load_practice_session,
    load_question,
)
from app.features.interview_practice.interview_job_sse import stream_interview_job_sse
from app.features.interview_practice.service import enqueue_generate_questions, enqueue_refine_answer
from app.schemas.interview_practice import (
    InterviewAnswerAttemptResponse,
    InterviewAnswerCreateBody,
    InterviewAnswerHistoryItem,
    InterviewGenerateEnqueueResponse,
    InterviewGenerateRequestBody,
    InterviewJobStatusResponse,
    InterviewPracticeSessionCreateBody,
    InterviewPracticeSessionResponse,
    InterviewQuestionResponse,
    InterviewRefineEnqueueResponse,
    PaginatedInterviewPracticeSessionsResponse,
)

router = APIRouter(prefix="/interview-practice", tags=["interview-practice"])

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.get("/requests/{request_id}/stream")
async def stream_interview_job_status_route(request_id: uuid.UUID) -> StreamingResponse:
    return StreamingResponse(
        stream_interview_job_sse(request_id),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.get("/sessions", response_model=PaginatedInterviewPracticeSessionsResponse)
async def list_practice_sessions_route(
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> PaginatedInterviewPracticeSessionsResponse:
    total = await count_practice_sessions(db)
    rows = await list_practice_sessions(db, limit=limit, offset=offset)
    return PaginatedInterviewPracticeSessionsResponse(
        items=[InterviewPracticeSessionResponse.model_validate(r) for r in rows],
        total=total,
    )


@router.post("/sessions", response_model=InterviewPracticeSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_practice_session_route(
    body: InterviewPracticeSessionCreateBody,
    db: AsyncSession = Depends(get_db_session),
) -> InterviewPracticeSessionResponse:
    return await create_practice_session(
        db,
        resume_id=body.resume_id,
        job_description_id=body.job_description_id,
    )


@router.get("/sessions/{practice_session_id}", response_model=InterviewPracticeSessionResponse)
async def get_practice_session_route(
    practice_session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> InterviewPracticeSessionResponse:
    row = await load_practice_session(db, practice_session_id=practice_session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Practice session not found")
    return row


@router.get("/sessions/{practice_session_id}/answers", response_model=list[InterviewAnswerHistoryItem])
async def list_session_answers_route(
    practice_session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> list[InterviewAnswerHistoryItem]:
    session = await load_practice_session(db, practice_session_id=practice_session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Practice session not found")
    pairs = await list_answer_attempts_with_questions_for_session(db, practice_session_id=practice_session_id)
    out: list[InterviewAnswerHistoryItem] = []
    for attempt, question in pairs:
        out.append(
            InterviewAnswerHistoryItem(
                question_id=question.id,
                question_prompt=question.prompt,
                attempt=InterviewAnswerAttemptResponse.model_validate(attempt),
            )
        )
    return out


@router.post(
    "/sessions/{practice_session_id}/generate",
    response_model=InterviewGenerateEnqueueResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_questions_route(
    practice_session_id: uuid.UUID,
    body: InterviewGenerateRequestBody,
    db: AsyncSession = Depends(get_db_session),
) -> InterviewGenerateEnqueueResponse:
    session = await load_practice_session(db, practice_session_id=practice_session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Practice session not found")
    if body.source in ("jd", "both") and session.job_description_id is None:
        raise HTTPException(status_code=400, detail="This practice session has no job_description_id")
    if body.source in ("resume", "both") and session.resume_id is None:
        raise HTTPException(status_code=400, detail="This practice session has no resume_id")

    request_id = await enqueue_generate_questions(
        db,
        practice_session_id=practice_session_id,
        source=body.source,
        count=body.count,
        question_style=body.question_style,
        level=body.level,
        focus_detail=body.focus_detail,
    )
    return InterviewGenerateEnqueueResponse(request_id=request_id)


@router.get("/sessions/{practice_session_id}/questions", response_model=list[InterviewQuestionResponse])
async def list_questions_route(
    practice_session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> list[InterviewQuestionResponse]:
    session = await load_practice_session(db, practice_session_id=practice_session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Practice session not found")
    return await list_questions(db, practice_session_id=practice_session_id)


@router.get("/requests/{request_id}", response_model=InterviewJobStatusResponse)
async def get_request_status_route(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> InterviewJobStatusResponse:
    row = await load_job_request(db, request_id=request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Request not found")
    return row


@router.get("/answers/{answer_attempt_id}", response_model=InterviewAnswerAttemptResponse)
async def get_answer_attempt_route(
    answer_attempt_id: uuid.UUID,
    practice_session_id: uuid.UUID = Query(
        ..., description="Practice session id that owns this answer attempt."
    ),
    db: AsyncSession = Depends(get_db_session),
) -> InterviewAnswerAttemptResponse:
    session = await load_practice_session(db, practice_session_id=practice_session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Practice session not found")
    attempt = await load_answer_attempt_for_practice_session(
        db,
        answer_attempt_id=answer_attempt_id,
        practice_session_id=practice_session_id,
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Answer attempt not found")
    return attempt


@router.post(
    "/questions/{question_id}/answers",
    response_model=InterviewAnswerAttemptResponse,
)
async def create_answer_route(
    question_id: uuid.UUID,
    body: InterviewAnswerCreateBody,
    response: Response,
    practice_session_id: uuid.UUID = Query(..., description="Practice session id that owns this question."),
    db: AsyncSession = Depends(get_db_session),
) -> InterviewAnswerAttemptResponse:
    session = await load_practice_session(db, practice_session_id=practice_session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Practice session not found")
    q = await load_question(db, question_id=question_id)
    if q is None or q.practice_session_id != practice_session_id:
        raise HTTPException(status_code=404, detail="Question not found in this practice session")

    attempt, created = await upsert_answer_attempt(db, question_id=question_id, user_answer=body.user_answer)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK

    # If refine requested, enqueue it (client can use GET /requests/{id}/stream for SSE).
    if body.refine:
        await enqueue_refine_answer(db, practice_session_id=practice_session_id, answer_attempt_id=attempt.id)
    return attempt


@router.post(
    "/answers/{answer_attempt_id}/refine",
    response_model=InterviewRefineEnqueueResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def refine_answer_route(
    answer_attempt_id: uuid.UUID,
    practice_session_id: uuid.UUID = Query(..., description="Practice session id (for validation + context)."),
    db: AsyncSession = Depends(get_db_session),
) -> InterviewRefineEnqueueResponse:
    session = await load_practice_session(db, practice_session_id=practice_session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Practice session not found")

    # Basic existence check; the worker will do deeper validation.
    from app.models.interview_practice import InterviewAnswerAttempt

    attempt = await db.get(InterviewAnswerAttempt, answer_attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Answer attempt not found")

    request_id = await enqueue_refine_answer(
        db,
        practice_session_id=practice_session_id,
        answer_attempt_id=answer_attempt_id,
    )
    return InterviewRefineEnqueueResponse(request_id=request_id, answer_attempt_id=answer_attempt_id)

