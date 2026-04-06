import json
from typing import Any

import redis.asyncio as redis

from app.core.config import settings


QUEUE_KEY = "queue:agent-jobs"


async def get_redis_client() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


async def enqueue_job(payload: dict[str, Any]) -> None:
    client = await get_redis_client()
    await client.rpush(QUEUE_KEY, json.dumps(payload))

