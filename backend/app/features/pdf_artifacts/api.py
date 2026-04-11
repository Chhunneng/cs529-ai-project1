from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.pdf_artifact import PdfArtifact
from app.schemas.pagination import PaginatedPdfArtifactsResponse
from app.schemas.pdf_artifact import PdfArtifactListItem

router = APIRouter(prefix="/pdf-artifacts", tags=["pdf-artifacts"])


@router.get("", response_model=PaginatedPdfArtifactsResponse)
async def list_pdf_artifacts(
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> PaginatedPdfArtifactsResponse:
    total = int(await db.scalar(select(func.count()).select_from(PdfArtifact)) or 0)
    result = await db.execute(
        select(PdfArtifact).order_by(PdfArtifact.created_at.desc()).limit(limit).offset(offset)
    )
    rows = list(result.scalars().all())
    return PaginatedPdfArtifactsResponse(
        items=[PdfArtifactListItem.model_validate(r) for r in rows],
        total=total,
    )
