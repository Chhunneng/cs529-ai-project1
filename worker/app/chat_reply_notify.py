import json
import uuid

import structlog

from app.queue import get_redis_client

log = structlog.get_logger()

CHAT_REPLY_CHANNEL_PREFIX = "chat:reply:"


def chat_reply_channel(user_message_id: uuid.UUID) -> str:
    return f"{CHAT_REPLY_CHANNEL_PREFIX}{user_message_id}"


async def publish_chat_reply(
    *, user_message_id: uuid.UUID, session_id: uuid.UUID, assistant_message_id: uuid.UUID
) -> None:
    try:
        client = await get_redis_client()
        channel = chat_reply_channel(user_message_id)
        payload = json.dumps(
            {"assistant_message_id": str(assistant_message_id), "session_id": str(session_id)}
        )
        await client.publish(channel, payload)
    except Exception:
        log.warning("chat_reply_publish_failed", exc_info=True)
