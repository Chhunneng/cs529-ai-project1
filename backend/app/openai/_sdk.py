"""Shared OpenAI SDK client construction."""

from __future__ import annotations

from openai import AsyncOpenAI

from app.core.config import settings


def async_openai_client() -> AsyncOpenAI:
    if not settings.openai.api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return AsyncOpenAI(api_key=settings.openai.api_key)
