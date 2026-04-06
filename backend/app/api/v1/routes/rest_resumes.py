import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.resume import Resume
from app.schemas.resume import ResumeListItem, ResumeUploadRequest, ResumeUploadResponse

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.get("", response_model=list[ResumeListItem])
async def list_resumes_rest(db: AsyncSession = Depends(get_db_session)) -> list[ResumeListItem]:
    result = await db.execute(select(Resume).order_by(Resume.created_at.desc()))
    items = result.scalars().all()
    return [
        ResumeListItem(id=r.id, created_at=r.created_at, openai_file_id=r.openai_file_id)
        for r in items
    ]


@router.post("", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def create_resume_rest(
    payload: ResumeUploadRequest, db: AsyncSession = Depends(get_db_session)
) -> ResumeUploadResponse:
    resume = Resume(openai_file_id=None, parsed_json=None)
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    return ResumeUploadResponse(id=resume.id)


@router.get("/{resume_id}", response_model=ResumeListItem)
async def get_resume_rest(
    resume_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)
) -> ResumeListItem:
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    r = result.scalar_one_or_none()
    if r is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return ResumeListItem(id=r.id, created_at=r.created_at, openai_file_id=r.openai_file_id)
