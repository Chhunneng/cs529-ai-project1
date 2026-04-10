from __future__ import annotations

import uuid

from app.db.session import AsyncSessionMaker
from app.models.resume import Resume


async def load_resume_row(*, resume_id: uuid.UUID) -> Resume | None:
    async with AsyncSessionMaker() as db:
        return await db.get(Resume, resume_id)

