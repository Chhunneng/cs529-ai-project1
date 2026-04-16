from __future__ import annotations

import uuid

from sqlalchemy import select

from app.db.session import AsyncSessionMaker
from app.models.resume import Resume


class SqlAlchemyResumeRepository:
    async def get_content_text(self, resume_id: uuid.UUID) -> str | None:
        async with AsyncSessionMaker() as db:
            resume_text = await db.scalar(select(Resume.content_text).where(Resume.id == resume_id))
            return str(resume_text) if resume_text is not None else None

    async def save_parsed_json(self, resume_id: uuid.UUID, parsed_json: dict) -> None:
        async with AsyncSessionMaker() as db:
            resume = await db.get(Resume, resume_id)
            if resume is None:
                return
            resume.parsed_json = parsed_json
            await db.commit()

