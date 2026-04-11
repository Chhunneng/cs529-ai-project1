from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_job_description_or_404, get_session_or_404
from app.db.session import get_db_session
from app.models.chat_session import ChatSession
from app.models.job_description import JobDescription
from app.schemas.job_description import JobDescriptionCreateBody, JobDescriptionResponse
from app.schemas.pagination import PaginatedJobDescriptionsResponse

router = APIRouter(tags=["job-descriptions"])


@router.post(
    "/sessions/{session_id}/job-descriptions",
    response_model=JobDescriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_job_description(
    body: JobDescriptionCreateBody,
    session: ChatSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(get_db_session),
) -> JobDescriptionResponse:
    job_description = JobDescription(raw_text=body.raw_text, extracted_json=None)
    db.add(job_description)
    await db.commit()
    await db.refresh(job_description)

    if body.set_active:
        session.job_description_id = job_description.id
        await db.commit()
    return job_description


@router.get(
    "/sessions/{session_id}/job-descriptions",
    response_model=PaginatedJobDescriptionsResponse,
)
async def list_job_descriptions_for_session(
    _session: ChatSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> PaginatedJobDescriptionsResponse:
    """Same global list as ``GET /job-descriptions``; session path kept for compatible URLs."""
    total = int(await db.scalar(select(func.count()).select_from(JobDescription)) or 0)
    result = await db.execute(
        select(JobDescription)
        .order_by(JobDescription.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = list(result.scalars().all())
    return PaginatedJobDescriptionsResponse(items=items, total=total)


@router.get("/job-descriptions", response_model=PaginatedJobDescriptionsResponse)
async def list_job_descriptions(
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> PaginatedJobDescriptionsResponse:
    total = int(await db.scalar(select(func.count()).select_from(JobDescription)) or 0)
    result = await db.execute(
        select(JobDescription)
        .order_by(JobDescription.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = list(result.scalars().all())
    return PaginatedJobDescriptionsResponse(items=items, total=total)


@router.post(
    "/job-descriptions",
    response_model=JobDescriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_job_description_global(
    body: JobDescriptionCreateBody,
    db: AsyncSession = Depends(get_db_session),
) -> JobDescriptionResponse:
    """Add a posting to the shared library without linking a chat session.

    ``set_active`` in the body is ignored (no session context).
    """
    job_description = JobDescription(raw_text=body.raw_text, extracted_json=None)
    db.add(job_description)
    await db.commit()
    await db.refresh(job_description)
    return job_description


@router.get("/job-descriptions/{job_description_id}", response_model=JobDescriptionResponse)
async def get_job_description(
    job_description: JobDescription = Depends(get_job_description_or_404),
) -> JobDescriptionResponse:
    return job_description


@router.post(
    "/sessions/{session_id}/job-descriptions/{job_description_id}/activate",
    status_code=status.HTTP_200_OK,
)
async def activate_job_description(
    session: ChatSession = Depends(get_session_or_404),
    job_description: JobDescription = Depends(get_job_description_or_404),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    session.job_description_id = job_description.id
    await db.commit()

