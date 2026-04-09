from __future__ import annotations

import uuid

from sqlalchemy import select

from app.db.session import AsyncSessionMaker
from app.models.job_description import JobDescription


async def load_job_description_row(*, jd_id: uuid.UUID) -> JobDescription | None:
    async with AsyncSessionMaker() as db:
        return await db.scalar(select(JobDescription).where(JobDescription.id == jd_id))

