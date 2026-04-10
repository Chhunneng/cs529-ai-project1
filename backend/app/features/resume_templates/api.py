from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from app.api.v1.deps import get_resume_template_or_404
from app.db.session import get_db_session
from app.models.resume_template import ResumeTemplate
from app.features.resume_templates.service import (
    stream_fix_resume_template_latex_sse,
    stream_generate_latex_from_requirements_sse,
    validate_resume_template_latex as run_validate_resume_template_latex,
)
from app.schemas.pagination import PaginatedResumeTemplatesResponse
from app.schemas.resume_template import (
    ResumeTemplateCreateBody,
    ResumeTemplateDetail,
    ResumeTemplateFixBody,
    ResumeTemplateGenerateBody,
    ResumeTemplatePatchBody,
    ResumeTemplateValidateBody,
    ResumeTemplateValidateResponse,
)
from app.features.latex.exceptions import LaTeXCompileFailed
from app.features.resume_templates.latex_preview import build_template_preview_pdf, validate_template_latex

router = APIRouter(prefix="/resume-templates", tags=["resume-templates"])

log = structlog.get_logger()

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


async def _require_compilable_latex(*, latex_source: str) -> None:
    r = await validate_template_latex(latex_source=latex_source)
    if not r.ok:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=r.model_dump(mode="json"),
        )


@router.get("", response_model=PaginatedResumeTemplatesResponse)
async def list_resume_templates(
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, max_length=200),
) -> PaginatedResumeTemplatesResponse:
    filters = []
    if q and q.strip():
        term = f"%{q.strip()}%"
        filters.append(ResumeTemplate.name.ilike(term))

    count_stmt = select(func.count()).select_from(ResumeTemplate)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = int(await db.scalar(count_stmt) or 0)

    stmt = select(ResumeTemplate).order_by(ResumeTemplate.created_at.desc()).limit(limit).offset(offset)
    if filters:
        stmt = stmt.where(*filters)
    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return PaginatedResumeTemplatesResponse(items=items, total=total)


@router.post("", response_model=ResumeTemplateDetail, status_code=status.HTTP_201_CREATED)
async def create_resume_template(
    body: ResumeTemplateCreateBody, db: AsyncSession = Depends(get_db_session)
) -> ResumeTemplateDetail:
    await _require_compilable_latex(latex_source=body.latex_source)
    tpl = ResumeTemplate(
        name=body.name,
        latex_source=body.latex_source,
        valid=True,
    )
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return tpl


@router.post("/generate-latex")
async def generate_resume_template_latex(body: ResumeTemplateGenerateBody) -> StreamingResponse:
    """Stream the LaTeX sample writer agent on free-form requirements; does not persist a template."""
    return StreamingResponse(
        stream_generate_latex_from_requirements_sse(requirements=body.requirements),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.post("/validate-latex", response_model=ResumeTemplateValidateResponse)
async def validate_resume_template_latex(body: ResumeTemplateValidateBody) -> ResumeTemplateValidateResponse:
    """Check whether LaTeX compiles with pdflatex (same pipeline as PDF preview); does not persist."""
    return await run_validate_resume_template_latex(latex_source=body.latex_source)


@router.post("/fix-latex")
async def fix_resume_template_latex(body: ResumeTemplateFixBody) -> StreamingResponse:
    """Stream the fix agent correcting LaTeX from compiler/user error text; does not persist."""
    return StreamingResponse(
        stream_fix_resume_template_latex_sse(
            latex_source=body.latex_source,
            error_message=body.error_message,
        ),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.get("/{template_id}/preview-pdf")
async def download_template_preview_pdf(
    template: ResumeTemplate = Depends(get_resume_template_or_404),
) -> Response:
    """
    Compile stored LaTeX as-is and return PDF (no placeholder filling; template must be valid TeX).
    """
    try:
        pdf_bytes = await build_template_preview_pdf(latex_source=template.latex_source)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except LaTeXCompileFailed as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.detail,
        ) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(e)},
        ) from e
    filename = f"template-preview-{template.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{template_id}", response_model=ResumeTemplateDetail)
async def get_resume_template(
    template: ResumeTemplate = Depends(get_resume_template_or_404),
) -> ResumeTemplateDetail:
    return template


@router.patch("/{template_id}", response_model=ResumeTemplateDetail)
async def patch_resume_template(
    body: ResumeTemplatePatchBody,
    template: ResumeTemplate = Depends(get_resume_template_or_404),
    db: AsyncSession = Depends(get_db_session),
) -> ResumeTemplateDetail:
    if body.name is not None:
        template.name = body.name
    if body.latex_source is not None:
        await _require_compilable_latex(latex_source=body.latex_source)
        template.latex_source = body.latex_source
        template.valid = True
    await db.commit()
    await db.refresh(template)
    return template


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_resume_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    result = await db.execute(select(ResumeTemplate).where(ResumeTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    await db.delete(template)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
