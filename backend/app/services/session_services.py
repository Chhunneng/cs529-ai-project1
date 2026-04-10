"""Chat session persistence: create, list, patch, delete (including artifact cleanup)."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.chat_session import ChatSession
from app.models.pdf_artifact import PdfArtifact
from app.models.resume_output import ResumeOutput
from app.schemas.rest import SessionPatchRequest


async def create_chat_session(db: AsyncSession) -> ChatSession:
    session = ChatSession(state_json={})
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def list_chat_sessions(db: AsyncSession, *, limit: int) -> Sequence[ChatSession]:
    result = await db.execute(
        select(ChatSession).order_by(ChatSession.updated_at.desc()).limit(limit)
    )
    return result.scalars().all()


async def patch_chat_session(
    session: ChatSession,
    body: SessionPatchRequest,
    db: AsyncSession,
) -> ChatSession:
    fields_set = body.model_fields_set
    if "resume_id" in fields_set:
        session.resume_id = body.resume_id
    if "job_description_id" in fields_set:
        session.job_description_id = body.job_description_id
    if "resume_template_id" in fields_set:
        session.resume_template_id = body.resume_template_id
    if "state_json" in fields_set:
        session.state_json = body.state_json if body.state_json is not None else {}
    await db.commit()
    await db.refresh(session)
    return session


def _unlink_if_under_artifacts(path_str: str | None, artifacts_root: Path) -> None:
    if not path_str:
        return
    try:
        p = Path(path_str).expanduser().resolve()
        p.relative_to(artifacts_root)
    except (ValueError, OSError):
        return
    if p.is_file():
        try:
            p.unlink()
        except OSError:
            pass


async def delete_session_by_id(session: ChatSession, db: AsyncSession) -> bool:
    """
    Remove session row (CASCADE: messages, runs, resume_outputs, pdf_artifacts).
    Deletes PDF/TeX files for resume outputs and PDF artifacts under ``artifacts_dir``.
    """

    root = Path(settings.storage.artifacts_dir).resolve()

    out_result = await db.execute(select(ResumeOutput).where(ResumeOutput.session_id == session.id))
    outputs = out_result.scalars().all()
    for out in outputs:
        _unlink_if_under_artifacts(out.pdf_path, root)
        _unlink_if_under_artifacts(out.tex_path, root)

    art_result = await db.execute(select(PdfArtifact).where(PdfArtifact.session_id == session.id))
    for art in art_result.scalars().all():
        try:
            p = (root / art.storage_relpath).resolve()
            p.relative_to(root)
        except (ValueError, OSError):
            continue
        if p.is_file():
            try:
                p.unlink()
            except OSError:
                pass

    session.job_description_id = None
    session.resume_id = None
    session.resume_template_id = None
    await db.flush()
    await db.delete(session)
    await db.commit()
    return True
