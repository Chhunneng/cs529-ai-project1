import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_session import AgentSession
from app.models.resume_output import ResumeOutput
from app.models.resume_template import ResumeTemplate
from app.services.queue import enqueue_job

log = structlog.get_logger()


async def create_resume_output_and_enqueue(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    template_id: str,
    source_resume_id: uuid.UUID | None,
    job_description_id: uuid.UUID | None,
) -> ResumeOutput:
    sess = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
    if sess.scalar_one_or_none() is None:
        raise ValueError("Session not found")

    tpl = await db.execute(select(ResumeTemplate).where(ResumeTemplate.id == template_id))
    if tpl.scalar_one_or_none() is None:
        raise ValueError("Template not found")

    out = ResumeOutput(
        session_id=session_id,
        template_id=template_id,
        status="queued",
        input_json={
            "source_resume_id": str(source_resume_id) if source_resume_id else None,
            "job_description_id": str(job_description_id) if job_description_id else None,
        },
    )
    db.add(out)
    await db.commit()
    await db.refresh(out)

    await enqueue_job(
        {
            "type": "render_resume",
            "output_id": str(out.id),
            "session_id": str(session_id),
            "template_id": template_id,
        }
    )
    log.info("enqueued_job", type="render_resume", output_id=str(out.id))
    return out
