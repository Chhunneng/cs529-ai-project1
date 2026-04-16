from __future__ import annotations

from app.llm.resume_extract import extract_resume_profile_json


class OpenAIResumeProfileExtractor:
    async def extract_profile(self, *, resume_text: str) -> dict:
        return await extract_resume_profile_json(resume_text=resume_text)

