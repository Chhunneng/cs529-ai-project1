import json
from typing import Any

import redis.asyncio as redis

from app.config import settings


async def get_redis_client() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


async def dequeue_job(timeout_seconds: int = 5) -> dict[str, Any] | None:
    client = await get_redis_client()
    result = await client.blpop(settings.queue_key, timeout=timeout_seconds)
    if result is None:
        return None
    _queue, raw = result
    return json.loads(raw)

