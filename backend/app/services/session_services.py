"""Agent session persistence: create, list, patch, and delete (including artifact cleanup)."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.agent_session import AgentSession
from app.models.resume_output import ResumeOutput
from app.schemas.rest import SessionPatchRequest
from app.openai.client import delete_openai_conversation_best_effort


async def create_agent_session(db: AsyncSession) -> AgentSession:
    session = AgentSession(state_json={})
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def list_agent_sessions(db: AsyncSession, *, limit: int) -> Sequence[AgentSession]:
    result = await db.execute(
        select(AgentSession).order_by(AgentSession.updated_at.desc()).limit(limit)
    )
    return result.scalars().all()


async def patch_agent_session(
    session: AgentSession,
    body: SessionPatchRequest,
    db: AsyncSession,
) -> AgentSession:
    if body.selected_resume_id is not None:
        session.selected_resume_id = body.selected_resume_id
    if body.active_jd_id is not None:
        session.active_jd_id = body.active_jd_id
    if body.state_json is not None:
        session.state_json = body.state_json
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


async def delete_session_by_id(session: AgentSession, db: AsyncSession) -> bool:
    """
    Remove session row (CASCADE: messages, runs, JDs, resume_outputs).
    Clears FK pointers that would block CASCADE on job_descriptions, then deletes
    PDF/TeX files for outputs under ``artifacts_dir``.
    """

    out_result = await db.execute(
        select(ResumeOutput).where(ResumeOutput.session_id == session.id)
    )
    outputs = out_result.scalars().all()
    root = Path(settings.artifacts_dir).resolve()
    for out in outputs:
        _unlink_if_under_artifacts(out.pdf_path, root)
        _unlink_if_under_artifacts(out.tex_path, root)

    openai_conv_id = session.openai_conversation_id
    await delete_openai_conversation_best_effort(openai_conv_id)

    session.active_jd_id = None
    session.selected_resume_id = None
    await db.flush()
    await db.delete(session)
    await db.commit()
    return True
