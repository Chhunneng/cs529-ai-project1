from __future__ import annotations

import uuid

from app.features.job_descriptions.repositories import load_job_description_row


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


async def fetch_job_description_excerpt(*, job_description_id: uuid.UUID, max_chars: int) -> str | None:
    job_description = await load_job_description_row(job_description_id=job_description_id)
    if job_description is None:
        return "Active job description was not found."
    raw = str(job_description.raw_text or "").strip()
    if not raw:
        return "(Job description record is empty.)"
    return _clip(raw, max_chars)

async def fetch_full_job_description_text(*, job_description_id: uuid.UUID) -> str | None:
    job_description = await load_job_description_row(job_description_id=job_description_id)
    if job_description is None:
        return "Active job description was not found."
    return str(job_description.raw_text or "").strip()
