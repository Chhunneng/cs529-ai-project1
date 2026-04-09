from __future__ import annotations

import uuid

from app.features.job_descriptions.repo import load_job_description_row


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


async def fetch_job_description_excerpt(*, jd_id: uuid.UUID, max_chars: int) -> str | None:
    jd = await load_job_description_row(jd_id=jd_id)
    if jd is None:
        return None
    raw = str(jd.raw_text or "").strip()
    if not raw:
        return "(Job description record is empty.)"
    return _clip(raw, max_chars)

