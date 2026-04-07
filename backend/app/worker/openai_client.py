from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

log = structlog.get_logger()

RESUME_ASSISTANT_SYSTEM_MESSAGE = (
    "You are a helpful resume assistant.\n"
    "Use any provided session context (selected resume, active job description) when relevant.\n"
    "Keep replies short in Phase 1."
)


@dataclass(frozen=True)
class OpenAIReply:
    model: str
    reply_text: str
    usage: dict[str, Any] | None


def _client() -> AsyncOpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return AsyncOpenAI(api_key=settings.openai_api_key)


async def create_openai_conversation() -> str:
    client = _client()
    conv = await client.conversations.create(
        items=[{"role": "system", "content": RESUME_ASSISTANT_SYSTEM_MESSAGE}],
    )
    return conv.id


async def delete_openai_conversation_best_effort(conversation_id: str) -> None:
    if not conversation_id or not settings.openai_api_key:
        return
    try:
        client = _client()
        await client.conversations.delete(conversation_id)
    except Exception as e:
        log.warning(
            "openai_conversation_delete_failed",
            conversation_id=conversation_id,
            error=str(e),
        )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=1, max=8))
async def generate_reply(
    *,
    conversation_id: str,
    user_text: str,
    context_text: str | None = None,
) -> OpenAIReply:
    client = _client()

    ctx = (context_text or "").strip()
    ctx_block = f"\n\n--- Session context ---\n{ctx}" if ctx else ""
    resp = await client.responses.create(
        model=settings.openai_model,
        conversation=conversation_id,
        input=[{"role": "user", "content": user_text + ctx_block}],
    )

    reply_text = getattr(resp, "output_text", None) or ""
    usage = getattr(resp, "usage", None)
    usage_dict = usage.model_dump() if hasattr(usage, "model_dump") else None

    return OpenAIReply(model=settings.openai_model, reply_text=reply_text.strip(), usage=usage_dict)
