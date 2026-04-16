import uuid

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.chat_session import ChatSession
from app.models.job_description import JobDescription
from app.models.pdf_artifact import PdfArtifact
from app.models.resume import Resume
from app.models.resume_output import ResumeOutput
from app.models.resume_template import ResumeTemplate


async def get_session_or_404(
    session_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)
) -> ChatSession:
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def get_resume_or_404(
    resume_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)
) -> Resume:
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


async def get_resume_template_or_404(
    template_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)
) -> ResumeTemplate:
    result = await db.execute(select(ResumeTemplate).where(ResumeTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


async def get_resume_output_or_404(
    output_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)
) -> ResumeOutput:
    result = await db.execute(select(ResumeOutput).where(ResumeOutput.id == output_id))
    out = result.scalar_one_or_none()
    if out is None:
        raise HTTPException(status_code=404, detail="Resume output not found")
    return out


async def get_job_description_or_404(
    job_description_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)
) -> JobDescription:
    result = await db.execute(
        select(JobDescription).where(JobDescription.id == job_description_id)
    )
    job_description = result.scalar_one_or_none()
    if job_description is None:
        raise HTTPException(status_code=404, detail="Job description not found")
    return job_description


async def get_pdf_artifact_for_session_or_404(
    pdf_artifact_id: uuid.UUID,
    session: ChatSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(get_db_session),
) -> PdfArtifact:
    artifact = await db.scalar(
        select(PdfArtifact).where(
            PdfArtifact.id == pdf_artifact_id,
            PdfArtifact.session_id == session.id,
        )
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="PDF artifact not found")
    return artifact
