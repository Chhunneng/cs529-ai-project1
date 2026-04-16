from __future__ import annotations

import uuid

import structlog

from app.application.resumes.parse_resume import parse_resume_and_store
from app.infra.db.resumes.repository import SqlAlchemyResumeRepository
from app.infra.llm.resume_profile_extractor import OpenAIResumeProfileExtractor
from app.queue_jobs import ParseResumeJob

log = structlog.get_logger()


async def handle_parse_resume_job(job: ParseResumeJob) -> None:
    resume_id = uuid.UUID(job.resume_id)
    log.info("parse_resume_start", resume_id=str(resume_id))

    await parse_resume_and_store(
        resume_id=resume_id,
        repository=SqlAlchemyResumeRepository(),
        extractor=OpenAIResumeProfileExtractor(),
    )

