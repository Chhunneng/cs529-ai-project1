from typing import List

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_resume_template_or_404
from app.db.session import get_db_session
from app.models.resume_template import ResumeTemplate
from app.schemas.resume_template import (
    ResumeTemplateCreateBody,
    ResumeTemplateDetail,
    ResumeTemplateListItem,
    ResumeTemplatePatchBody,
)
from app.services.resume_template_services import build_template_preview_pdf

router = APIRouter(prefix="/resume-templates", tags=["resume-templates"])


@router.get("", response_model=List[ResumeTemplateListItem])
async def list_resume_templates(
    db: AsyncSession = Depends(get_db_session),
) -> list[ResumeTemplateListItem]:
    result = await db.execute(select(ResumeTemplate).order_by(ResumeTemplate.created_at.desc()))
    resume_templates = result.scalars().all()
    return resume_templates


@router.post("", response_model=ResumeTemplateDetail, status_code=status.HTTP_201_CREATED)
async def create_resume_template(
    body: ResumeTemplateCreateBody, db: AsyncSession = Depends(get_db_session)
) -> ResumeTemplateDetail:
    tpl = ResumeTemplate(
        name=body.name,
        latex_source=body.latex_source,
        schema_json=body.schema_json or {},
    )
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return tpl


@router.get("/{template_id}/preview-pdf")
async def download_template_preview_pdf(
    template: ResumeTemplate = Depends(get_resume_template_or_404),
) -> Response:
    """
    Compile stored LaTeX as-is and return PDF (no placeholder filling; template must be valid TeX).
    """
    if not template.latex_source or not template.latex_source.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Template has no LaTeX source")
    try:
        pdf_bytes = await build_template_preview_pdf(latex_source=template.latex_source)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
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
        template.latex_source = body.latex_source
    if body.schema_json is not None:
        template.schema_json = body.schema_json
    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    result = await db.execute(select(ResumeTemplate).where(ResumeTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    await db.delete(template)
    await db.commit()
