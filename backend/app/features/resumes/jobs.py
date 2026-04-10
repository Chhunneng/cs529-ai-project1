from __future__ import annotations

import uuid

import structlog

from app.core.config import settings
from app.db.session import AsyncSessionMaker
from app.models.resume import Resume
from app.llm.resume_extract import extract_resume_profile_json
from app.queue_jobs import ParseResumeJob

log = structlog.get_logger()


async def handle_parse_resume_job(job: ParseResumeJob) -> None:
    resume_id = uuid.UUID(job.resume_id)
    log.info("parse_resume_start", resume_id=str(resume_id))
    if not settings.openai.api_key:
        log.warn("parse_resume_skipped_no_api_key", resume_id=str(resume_id))
        return

    async with AsyncSessionMaker() as db:
        r = await db.get(Resume, resume_id)
        if r is None:
            log.warn("parse_resume_resume_missing", resume_id=str(resume_id))
            return
        body = (r.content_text or "").strip()
        if not body:
            log.warn("parse_resume_no_content_text", resume_id=str(resume_id))
            return

    try:
        parsed = await extract_resume_profile_json(resume_text=body)
    except Exception:
        log.exception("parse_resume_failed", resume_id=str(resume_id))
        return

    async with AsyncSessionMaker() as db:
        r2 = await db.get(Resume, resume_id)
        if r2 is None:
            return
        r2.parsed_json = parsed
        await db.commit()
    log.info("parse_resume_done", resume_id=str(resume_id))

