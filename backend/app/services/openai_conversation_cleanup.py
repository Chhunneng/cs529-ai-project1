"""Best-effort deletion of OpenAI server-side conversations when a session is removed."""

from __future__ import annotations

import structlog
from openai import AsyncOpenAI

from app.core.config import settings

log = structlog.get_logger()


async def delete_openai_conversation_best_effort(conversation_id: str | None) -> None:
    if not conversation_id or not settings.openai_api_key:
        return
    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        await client.conversations.delete(conversation_id)
    except Exception as e:
        log.warning(
            "openai_conversation_delete_failed",
            conversation_id=conversation_id,
            error=str(e),
        )
