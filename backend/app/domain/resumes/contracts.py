from __future__ import annotations

import uuid
from typing import Protocol


class ResumeRepository(Protocol):
    async def get_content_text(self, resume_id: uuid.UUID) -> str | None:
        """Return the resume text (or None if missing)."""

    async def save_parsed_json(self, resume_id: uuid.UUID, parsed_json: dict) -> None:
        """Persist extracted structured data for a resume."""


class ResumeProfileExtractor(Protocol):
    async def extract_profile(self, *, resume_text: str) -> dict:
        """Extract structured profile JSON from resume text."""

