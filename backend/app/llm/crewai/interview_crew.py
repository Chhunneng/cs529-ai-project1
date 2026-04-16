from __future__ import annotations

import uuid

from app.db.session import AsyncSessionMaker
from app.features.job_descriptions.service import fetch_full_job_description_text
from app.features.resumes.repositories import load_resume_row
from app.features.resumes.service import resume_source_text
from app.models.interview_practice import InterviewPracticeSession


async def load_interview_practice_context_texts(
    *,
    practice_session_id: uuid.UUID,
    source: str,
) -> tuple[str | None, str | None]:
    """Load job description and resume text for a practice session (used before CrewAI queue dispatch)."""
    async with AsyncSessionMaker() as db:
        session = await db.get(InterviewPracticeSession, practice_session_id)
    if session is None:
        raise RuntimeError("Practice session not found.")

    job_description_text: str | None = None
    resume_text: str | None = None

    if source in ("jd", "both"):
        if session.job_description_id is None:
            job_description_text = None
        else:
            job_description_text = await fetch_full_job_description_text(job_description_id=session.job_description_id)

    if source in ("resume", "both"):
        if session.resume_id is None:
            resume_text = None
        else:
            resume = await load_resume_row(resume_id=session.resume_id)
            resume_text = resume_source_text(resume) if resume is not None else None

    return job_description_text, resume_text
