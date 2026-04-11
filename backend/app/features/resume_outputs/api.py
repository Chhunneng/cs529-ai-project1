from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_resume_output_or_404, get_session_or_404
from app.db.session import get_db_session
from app.models.chat_session import ChatSession
from app.models.resume_output import ResumeOutput
from app.schemas.pagination import PaginatedResumeOutputsResponse
from app.schemas.resume_output import (
    ResumeOutputCreateBody,
    ResumeOutputResponse,
    StandaloneResumePdfCreateBody,
)
from app.features.resume_outputs.service import (
    create_resume_output_and_enqueue,
    create_standalone_resume_output_and_enqueue,
    delete_resume_output_row,
)

router = APIRouter(tags=["resume-outputs"])


@router.post(
    "/sessions/{session_id}/resume-outputs",
    response_model=ResumeOutputResponse,
    status_code=202,
)
async def create_resume_output(
    body: ResumeOutputCreateBody,
    session: ChatSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(get_db_session),
) -> ResumeOutputResponse:
    try:
        resume_output = await create_resume_output_and_enqueue(
            db,
            session=session,
            template_id=body.template_id,
            source_resume_id=body.source_resume_id,
            job_description_id=body.job_description_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return resume_output


@router.post("/resume-outputs", response_model=ResumeOutputResponse, status_code=202)
async def create_standalone_resume_output(
    body: StandaloneResumePdfCreateBody,
    db: AsyncSession = Depends(get_db_session),
) -> ResumeOutputResponse:
    try:
        resume_output = await create_standalone_resume_output_and_enqueue(
            db,
            template_id=body.template_id,
            source_resume_id=body.source_resume_id,
            job_description_id=body.job_description_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return resume_output


@router.get("/resume-outputs", response_model=PaginatedResumeOutputsResponse)
async def list_resume_outputs(
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None, max_length=32),
) -> PaginatedResumeOutputsResponse:
    filters = []
    if status and status.strip():
        filters.append(ResumeOutput.status == status.strip())

    count_stmt = select(func.count()).select_from(ResumeOutput)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = int(await db.scalar(count_stmt) or 0)

    stmt = select(ResumeOutput).order_by(ResumeOutput.created_at.desc()).limit(limit).offset(offset)
    if filters:
        stmt = stmt.where(*filters)
    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return PaginatedResumeOutputsResponse(
        items=[ResumeOutputResponse.model_validate(r) for r in items],
        total=total,
    )


@router.get("/resume-outputs/{output_id}", response_model=ResumeOutputResponse)
async def get_resume_output(
    resume_output: ResumeOutput = Depends(get_resume_output_or_404),
) -> ResumeOutputResponse:
    return resume_output


@router.delete("/resume-outputs/{output_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume_output(
    resume_output: ResumeOutput = Depends(get_resume_output_or_404),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    if resume_output.status in ("queued", "running"):
        raise HTTPException(
            status_code=409,
            detail="Export is still processing. Wait until it finishes or fails, then try again.",
        )
    await delete_resume_output_row(db, resume_output)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/resume-outputs/{output_id}/pdf")
async def download_resume_pdf(
    resume_output: ResumeOutput = Depends(get_resume_output_or_404),
    disposition: Literal["inline", "attachment"] = Query(
        default="attachment",
        description='Use "inline" for browser preview (e.g. iframe); "attachment" encourages download.',
    ),
) -> FileResponse:
    if not resume_output.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not ready")
    path = Path(resume_output.pdf_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="PDF file missing")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"resume-{resume_output.id}.pdf",
        content_disposition_type=disposition,
    )

