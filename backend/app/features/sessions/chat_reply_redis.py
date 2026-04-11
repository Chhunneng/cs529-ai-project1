import json
import uuid

import structlog

from app.features.job_queue.redis import get_redis_client

log = structlog.get_logger()

CHAT_REPLY_CHANNEL_PREFIX = "chat:reply:"

# Redis SET: members = user_message_id (str) for turns still queued or running.
CHAT_SESSION_PENDING_SET_PREFIX = "chat:session:"
CHAT_SESSION_PENDING_SET_SUFFIX = ":pending"
# Long enough for slow LLM + LaTeX; refreshed on each new pending add.
PENDING_REPLY_SET_TTL_SECONDS = 3600


def _session_pending_set_key(session_id: uuid.UUID) -> str:
    return f"{CHAT_SESSION_PENDING_SET_PREFIX}{session_id}{CHAT_SESSION_PENDING_SET_SUFFIX}"


async def mark_chat_turn_pending(*, session_id: uuid.UUID, user_message_id: uuid.UUID) -> None:
    try:
        client = await get_redis_client()
        key = _session_pending_set_key(session_id)
        await client.sadd(key, str(user_message_id))
        await client.expire(key, PENDING_REPLY_SET_TTL_SECONDS)
    except Exception:
        log.warning("chat_turn_pending_mark_failed", exc_info=True)


async def clear_chat_turn_pending(*, session_id: uuid.UUID, user_message_id: uuid.UUID) -> None:
    try:
        client = await get_redis_client()
        key = _session_pending_set_key(session_id)
        await client.srem(key, str(user_message_id))
    except Exception:
        log.warning("chat_turn_pending_clear_failed", exc_info=True)


async def list_pending_user_message_ids(*, session_id: uuid.UUID) -> list[str]:
    try:
        client = await get_redis_client()
        key = _session_pending_set_key(session_id)
        members = await client.smembers(key)
        if not members:
            return []
        return sorted(str(x) for x in members)
    except Exception:
        log.warning("chat_turn_pending_list_failed", exc_info=True)
        return []


def chat_reply_channel(user_message_id: uuid.UUID) -> str:
    return f"{CHAT_REPLY_CHANNEL_PREFIX}{user_message_id}"


async def publish_chat_reply(
    *,
    user_message_id: uuid.UUID,
    session_id: uuid.UUID,
    assistant_message_id: uuid.UUID,
    pdf_artifact_id: uuid.UUID | None = None,
) -> None:
    try:
        client = await get_redis_client()
        channel = chat_reply_channel(user_message_id)
        payload = json.dumps(
            {
                "assistant_message_id": str(assistant_message_id),
                "session_id": str(session_id),
                "pdf_artifact_id": str(pdf_artifact_id) if pdf_artifact_id else None,
            }
        )
        await client.publish(channel, payload)
    except Exception:
        log.warning("chat_reply_publish_failed", exc_info=True)
