from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


@dataclass(frozen=True)
class OpenAIReply:
    model: str
    reply_text: str
    usage: dict[str, Any] | None


def _client() -> AsyncOpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return AsyncOpenAI(api_key=settings.openai_api_key)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=1, max=8))
async def generate_reply(*, user_text: str) -> OpenAIReply:
    """
    Minimal OpenAI call (Phase 1): take a user message and return a short assistant reply.
    """
    client = _client()

    resp = await client.responses.create(
        model=settings.openai_model,
        input=[
            {
                "role": "system",
                "content": "You are a helpful resume assistant. Keep replies short in Phase 1.",
            },
            {"role": "user", "content": user_text},
        ],
    )

    reply_text = getattr(resp, "output_text", None) or ""
    usage = getattr(resp, "usage", None)
    usage_dict = usage.model_dump() if hasattr(usage, "model_dump") else None

    return OpenAIReply(model=settings.openai_model, reply_text=reply_text.strip(), usage=usage_dict)

