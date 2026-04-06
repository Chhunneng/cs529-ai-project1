import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.resume_output import ResumeOutput
from app.schemas.resume_output import ResumeOutputCreateBody, ResumeOutputResponse
from app.services.resume_output_jobs import create_resume_output_and_enqueue

router = APIRouter(tags=["resume-outputs"])


@router.post(
    "/sessions/{session_id}/resume-outputs",
    response_model=ResumeOutputResponse,
    status_code=202,
)
async def create_resume_output(
    session_id: uuid.UUID,
    body: ResumeOutputCreateBody,
    db: AsyncSession = Depends(get_db_session),
) -> ResumeOutputResponse:
    try:
        out = await create_resume_output_and_enqueue(
            db,
            session_id=session_id,
            template_id=body.template_id,
            source_resume_id=body.source_resume_id,
            job_description_id=body.job_description_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return ResumeOutputResponse(
        id=out.id,
        session_id=out.session_id,
        template_id=out.template_id,
        status=out.status,
        input_json=out.input_json,
        tex_path=out.tex_path,
        pdf_path=out.pdf_path,
        error_text=out.error_text,
        created_at=out.created_at,
        updated_at=out.updated_at,
    )


@router.get("/resume-outputs/{output_id}", response_model=ResumeOutputResponse)
async def get_resume_output(
    output_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)
) -> ResumeOutputResponse:
    result = await db.execute(select(ResumeOutput).where(ResumeOutput.id == output_id))
    out = result.scalar_one_or_none()
    if out is None:
        raise HTTPException(status_code=404, detail="Output not found")
    return ResumeOutputResponse(
        id=out.id,
        session_id=out.session_id,
        template_id=out.template_id,
        status=out.status,
        input_json=out.input_json,
        tex_path=out.tex_path,
        pdf_path=out.pdf_path,
        error_text=out.error_text,
        created_at=out.created_at,
        updated_at=out.updated_at,
    )


@router.get("/resume-outputs/{output_id}/pdf")
async def download_resume_pdf(
    output_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)
) -> FileResponse:
    result = await db.execute(select(ResumeOutput).where(ResumeOutput.id == output_id))
    out = result.scalar_one_or_none()
    if out is None:
        raise HTTPException(status_code=404, detail="Output not found")
    if not out.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not ready")
    path = Path(out.pdf_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="PDF file missing")
    return FileResponse(path, media_type="application/pdf", filename=f"resume-{output_id}.pdf")
