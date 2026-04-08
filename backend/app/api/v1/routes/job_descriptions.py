from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_job_description_or_404, get_session_or_404
from app.db.session import get_db_session
from app.models.agent_session import AgentSession
from app.models.job_description import JobDescription
from app.schemas.job_description import JobDescriptionCreateBody, JobDescriptionResponse


router = APIRouter(tags=["job-descriptions"])


@router.post(
    "/sessions/{session_id}/job-descriptions",
    response_model=JobDescriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_job_description(
    body: JobDescriptionCreateBody,
    session: AgentSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(get_db_session),
) -> JobDescriptionResponse:
    job_description = JobDescription(raw_text=body.raw_text, extracted_json=None)
    db.add(job_description)
    await db.commit()
    await db.refresh(job_description)

    if body.set_active:
        session.active_jd_id = job_description.id
        await db.commit()
    return job_description


@router.get(
    "/sessions/{session_id}/job-descriptions",
    response_model=list[JobDescriptionResponse],
)
async def list_job_descriptions_for_session(
    _session: AgentSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[JobDescriptionResponse]:
    """Same global list as ``GET /job-descriptions``; session path kept for compatible URLs."""
    result = await db.execute(
        select(JobDescription).order_by(JobDescription.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


@router.get("/job-descriptions", response_model=list[JobDescriptionResponse])
async def list_job_descriptions(
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[JobDescriptionResponse]:
    result = await db.execute(
        select(JobDescription).order_by(JobDescription.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


@router.get("/job-descriptions/{job_description_id}", response_model=JobDescriptionResponse)
async def get_job_description(
    job_description: JobDescription = Depends(get_job_description_or_404),
) -> JobDescriptionResponse:
    return job_description


@router.post(
    "/sessions/{session_id}/job-descriptions/{job_description_id}/activate",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def activate_job_description(
    session: AgentSession = Depends(get_session_or_404),
    job_description: JobDescription = Depends(get_job_description_or_404),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    session.active_jd_id = job_description.id
    await db.commit()
