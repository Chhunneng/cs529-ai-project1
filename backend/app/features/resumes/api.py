from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse

from app.api.v1.deps import get_resume_or_404
from app.db.session import get_db_session
from app.models.resume import Resume
from app.schemas.resume import ResumeListItem, ResumeUploadResponse
from app.services.resume_uploads import (
    ResumeUploadError,
    absolute_upload_path,
    create_resume_from_upload,
    remove_stored_file,
)

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.get("", response_model=List[ResumeListItem])
async def list_resumes(db: AsyncSession = Depends(get_db_session)) -> List[ResumeListItem]:
    result = await db.execute(select(Resume).order_by(Resume.created_at.desc()))
    items = result.scalars().all()
    return items


@router.post("", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def create_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
) -> ResumeUploadResponse:
    try:
        resume = await create_resume_from_upload(db=db, upload=file)
    except ResumeUploadError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return resume


@router.get("/{resume_id}/download")
async def download_resume(resume_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)) -> FileResponse:
    resume = await get_resume_or_404(resume_id, db)
    if not resume.storage_relpath:
        raise HTTPException(status_code=404, detail="No file for this resume.")
    path = absolute_upload_path(resume.storage_relpath)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found on disk.")
    return FileResponse(
        path=str(path),
        filename=resume.original_filename or "resume",
        media_type=resume.mime_type or "application/octet-stream",
    )


@router.get("/{resume_id}", response_model=ResumeListItem)
async def get_resume(resume_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)) -> ResumeListItem:
    resume = await get_resume_or_404(resume_id, db)
    return resume


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume: Resume = Depends(get_resume_or_404),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    relpath = resume.storage_relpath
    await db.delete(resume)
    await db.commit()
    remove_stored_file(relpath)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

