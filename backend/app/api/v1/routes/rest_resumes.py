from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.api.v1.deps import get_resume_or_404
from app.schemas.resume import ResumeListItem, ResumeUploadRequest, ResumeUploadResponse
from app.models.resume import Resume
from sqlalchemy import select

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.get("", response_model=List[ResumeListItem])
async def list_resumes(db: AsyncSession = Depends(get_db_session)) -> List[ResumeListItem]:
    result = await db.execute(select(Resume).order_by(Resume.created_at.desc()))
    items = result.scalars().all()
    return items


@router.post("", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def create_resume(
    payload: ResumeUploadRequest, db: AsyncSession = Depends(get_db_session)
) -> ResumeUploadResponse:
    resume = Resume(openai_file_id=None, parsed_json=None)
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    return resume


@router.get("/{resume_id}", response_model=ResumeListItem)
async def get_resume(
    resume_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)
) -> ResumeListItem:
    resume = await get_resume_or_404(resume_id, db)
    return resume
