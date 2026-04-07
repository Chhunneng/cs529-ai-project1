from typing import List

from fastapi import APIRouter, Depends, status
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
        id=body.id,
        name=body.name,
        storage_path=body.storage_path,
        latex_source=body.latex_source,
        schema_json=body.schema_json or {},
    )
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return tpl


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
    if body.storage_path is not None:
        template.storage_path = body.storage_path
    if body.latex_source is not None:
        template.latex_source = body.latex_source
    if body.schema_json is not None:
        template.schema_json = body.schema_json
    await db.commit()
    await db.refresh(template)
    return template
