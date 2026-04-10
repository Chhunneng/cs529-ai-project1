import json
import time
import uuid
from collections.abc import AsyncIterator
from datetime import datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionMaker
from app.models.chat_message import ChatMessage
from app.features.job_queue.redis import get_redis_client
from app.features.sessions.chat_messages import chat_message_to_response
from app.features.sessions.chat_reply_redis import chat_reply_channel

log = structlog.get_logger()

SSE_TIMEOUT_SECONDS = 90


def _sse_data_line(obj: dict) -> str:
    return f"data: {json.dumps(obj, default=str)}\n\n"


async def _load_assistant_for_publish(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    user_created_at: datetime,
    assistant_message_id: uuid.UUID,
):
    m = await db.scalar(select(ChatMessage).where(ChatMessage.id == assistant_message_id))
    if m is None or m.role != "assistant" or m.session_id != session_id:
        return None
    if m.created_at <= user_created_at:
        return None
    return chat_message_to_response(m)


async def stream_assistant_sse(
    session_id: uuid.UUID, user_message_id: uuid.UUID
) -> AsyncIterator[str]:
    async with AsyncSessionMaker() as db:
        user_msg = await db.scalar(
            select(ChatMessage).where(
                ChatMessage.id == user_message_id,
                ChatMessage.session_id == session_id,
                ChatMessage.role == "user",
            )
        )
        if user_msg is None:
            yield _sse_data_line({"type": "error", "detail": "user_message_not_found"})
            return

        user_created = user_msg.created_at
        assistant = await db.scalar(
            select(ChatMessage)
            .where(
                ChatMessage.session_id == session_id,
                ChatMessage.role == "assistant",
                ChatMessage.created_at > user_created,
            )
            .order_by(ChatMessage.created_at.asc())
            .limit(1)
        )

    if assistant is not None:
        resp = chat_message_to_response(assistant)
        yield _sse_data_line({"type": "assistant", "message": resp.model_dump(mode="json")})
        return

    channel = chat_reply_channel(user_message_id)
    client = await get_redis_client()
    pubsub = client.pubsub()
    try:
        await pubsub.subscribe(channel)
        deadline = time.monotonic() + SSE_TIMEOUT_SECONDS
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                yield _sse_data_line(
                    {"type": "timeout", "detail": "No assistant reply within the wait window."}
                )
                return
            msg = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=min(1.0, remaining)
            )
            if msg is None:
                continue
            if msg.get("type") != "message":
                continue
            raw = msg.get("data")
            if not isinstance(raw, str):
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if str(data.get("session_id")) != str(session_id):
                continue
            aid_raw = data.get("assistant_message_id")
            if not aid_raw:
                continue
            try:
                assistant_id = uuid.UUID(str(aid_raw))
            except ValueError:
                continue

            async with AsyncSessionMaker() as db2:
                loaded = await _load_assistant_for_publish(
                    db2,
                    session_id=session_id,
                    user_created_at=user_created,
                    assistant_message_id=assistant_id,
                )
            if loaded is None:
                log.warning(
                    "chat_reply_publish_payload_mismatch",
                    assistant_message_id=str(assistant_id),
                    user_message_id=str(user_message_id),
                )
                continue
            yield _sse_data_line({"type": "assistant", "message": loaded.model_dump(mode="json")})
            return
    finally:
        try:
            await pubsub.unsubscribe(channel)
        except Exception:
            log.warning("chat_reply_pubsub_unsubscribe_failed", exc_info=True)
        try:
            await pubsub.aclose()
        except Exception:
            log.warning("chat_reply_pubsub_close_failed", exc_info=True)
        try:
            await client.aclose()
        except Exception:
            log.warning("chat_reply_redis_client_close_failed", exc_info=True)
