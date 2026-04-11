import shutil
import uuid
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.chat_session import ChatSession
from app.models.job_description import JobDescription
from app.models.resume import Resume
from app.queue_jobs import RenderResumeJob
from app.models.resume_output import ResumeOutput
from app.models.resume_template import ResumeTemplate
from app.features.job_queue.redis import enqueue_job
from app.features.sessions.service import _unlink_if_under_artifacts

log = structlog.get_logger()


async def enqueue_render_resume_job(
    *,
    output_id: uuid.UUID,
    template_id: uuid.UUID,
    chat_session_id: uuid.UUID | None,
) -> None:
    """Push a render job; chat_session_id is optional metadata for queue tracing."""
    await enqueue_job(
        RenderResumeJob(
            output_id=str(output_id),
            template_id=str(template_id),
            session_id=str(chat_session_id) if chat_session_id is not None else None,
        )
    )
    log.info("enqueued_job", type="render_resume", output_id=str(output_id))


async def create_standalone_resume_output_and_enqueue(
    db: AsyncSession,
    *,
    template_id: uuid.UUID,
    source_resume_id: uuid.UUID,
    job_description_id: uuid.UUID,
) -> ResumeOutput:
    template_row = await db.scalar(select(ResumeTemplate).where(ResumeTemplate.id == template_id))
    if template_row is None:
        raise ValueError("Template not found")

    resume_row = await db.get(Resume, source_resume_id)
    if resume_row is None:
        raise ValueError("Resume not found")

    job_description_row = await db.scalar(
        select(JobDescription).where(JobDescription.id == job_description_id)
    )
    if job_description_row is None:
        raise ValueError("Job description not found")

    output_row = ResumeOutput(
        session_id=None,
        template_id=template_id,
        status="queued",
        input_json={
            "source_resume_id": str(source_resume_id),
            "job_description_id": str(job_description_id),
        },
    )
    db.add(output_row)
    await db.commit()
    await db.refresh(output_row)

    await enqueue_render_resume_job(
        output_id=output_row.id,
        template_id=template_id,
        chat_session_id=None,
    )
    return output_row


async def create_resume_output_and_enqueue(
    db: AsyncSession,
    *,
    session: ChatSession,
    template_id: uuid.UUID,
    source_resume_id: uuid.UUID | None,
    job_description_id: uuid.UUID | None,
) -> ResumeOutput:
    template_row = await db.scalar(select(ResumeTemplate).where(ResumeTemplate.id == template_id))
    if template_row is None:
        raise ValueError("Template not found")

    resolved_job_description_id = (
        job_description_id if job_description_id is not None else session.job_description_id
    )

    output_row = ResumeOutput(
        session_id=session.id,
        template_id=template_id,
        status="queued",
        input_json={
            "source_resume_id": str(source_resume_id) if source_resume_id else None,
            "job_description_id": str(resolved_job_description_id)
            if resolved_job_description_id
            else None,
        },
    )
    db.add(output_row)
    await db.commit()
    await db.refresh(output_row)

    await enqueue_render_resume_job(
        output_id=output_row.id,
        template_id=template_id,
        chat_session_id=session.id,
    )
    return output_row


async def delete_resume_output_row(db: AsyncSession, row: ResumeOutput) -> None:
    """Remove PDF/TeX files and optional worker output directory, then delete the DB row."""
    root = Path(settings.storage.artifacts_dir).resolve()
    _unlink_if_under_artifacts(row.pdf_path, root)
    _unlink_if_under_artifacts(row.tex_path, root)
    try:
        out_dir = (root / str(row.id)).resolve()
        out_dir.relative_to(root)
        if out_dir.is_dir():
            shutil.rmtree(out_dir, ignore_errors=True)
    except (ValueError, OSError):
        pass
    output_id = row.id
    await db.delete(row)
    await db.commit()
    log.info("resume_output_deleted", output_id=str(output_id))
