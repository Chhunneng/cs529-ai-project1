from __future__ import annotations

import uuid

import structlog

from app.domain.resumes.contracts import ResumeProfileExtractor, ResumeRepository

log = structlog.get_logger()


async def parse_resume_and_store(
    *,
    resume_id: uuid.UUID,
    repository: ResumeRepository,
    extractor: ResumeProfileExtractor,
) -> None:
    resume_text = await repository.get_content_text(resume_id)
    if resume_text is None:
        log.warning("parse_resume_resume_missing", resume_id=str(resume_id))
        return
    resume_text = resume_text.strip()
    if not resume_text:
        log.warning("parse_resume_no_content_text", resume_id=str(resume_id))
        return

    try:
        parsed_profile = await extractor.extract_profile(resume_text=resume_text)
    except Exception:
        log.exception("parse_resume_failed", resume_id=str(resume_id))
        return

    await repository.save_parsed_json(resume_id, parsed_profile)
    log.info("parse_resume_done", resume_id=str(resume_id))

