from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.resume_template import ResumeTemplate
from app.schemas.resume_template import ResumeTemplateDetail, ResumeTemplateListItem

router = APIRouter(prefix="/resume-templates", tags=["resume-templates"])


@router.get("", response_model=list[ResumeTemplateListItem])
async def list_resume_templates(
    db: AsyncSession = Depends(get_db_session),
) -> list[ResumeTemplateListItem]:
    result = await db.execute(select(ResumeTemplate).order_by(ResumeTemplate.created_at.asc()))
    rows = result.scalars().all()
    return [
        ResumeTemplateListItem(
            id=r.id,
            name=r.name,
            storage_path=r.storage_path,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/{template_id}", response_model=ResumeTemplateDetail)
async def get_resume_template(
    template_id: str, db: AsyncSession = Depends(get_db_session)
) -> ResumeTemplateDetail:
    result = await db.execute(select(ResumeTemplate).where(ResumeTemplate.id == template_id))
    r = result.scalar_one_or_none()
    if r is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return ResumeTemplateDetail(
        id=r.id,
        name=r.name,
        storage_path=r.storage_path,
        schema_json=r.schema_json or {},
        created_at=r.created_at,
    )
