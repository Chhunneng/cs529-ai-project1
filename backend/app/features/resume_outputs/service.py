import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_session import ChatSession
from app.queue_jobs import RenderResumeJob
from app.models.resume_output import ResumeOutput
from app.models.resume_template import ResumeTemplate
from app.features.job_queue.redis import enqueue_job

log = structlog.get_logger()


async def create_resume_output_and_enqueue(
    db: AsyncSession,
    *,
    session: ChatSession,
    template_id: uuid.UUID,
    source_resume_id: uuid.UUID | None,
    job_description_id: uuid.UUID | None,
) -> ResumeOutput:
    resume_template = await db.execute(select(ResumeTemplate).where(ResumeTemplate.id == template_id))
    if resume_template.scalar_one_or_none() is None:
        raise ValueError("Template not found")

    resolved_jd_id = (
        job_description_id if job_description_id is not None else session.job_description_id
    )

    out = ResumeOutput(
        session_id=session.id,
        template_id=template_id,
        status="queued",
        input_json={
            "source_resume_id": str(source_resume_id) if source_resume_id else None,
            "job_description_id": str(resolved_jd_id) if resolved_jd_id else None,
        },
    )
    db.add(out)
    await db.commit()
    await db.refresh(out)

    await enqueue_job(
        RenderResumeJob(
            output_id=str(out.id),
            session_id=str(session.id),
            template_id=str(template_id),
        )
    )
    log.info("enqueued_job", type="render_resume", output_id=str(out.id))
    return out
