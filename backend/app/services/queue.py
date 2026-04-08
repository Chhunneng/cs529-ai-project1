import redis.asyncio as redis

from app.queue_jobs import AgentJob, deserialize_job, serialize_job

from app.core.config import settings


async def get_redis_client() -> redis.Redis:
    return redis.from_url(settings.redis.url, decode_responses=True)


async def enqueue_job(job: AgentJob) -> None:
    client = await get_redis_client()
    await client.rpush(settings.redis.queue_key, serialize_job(job))


async def dequeue_job(timeout_seconds: int = 5) -> AgentJob | None:
    client = await get_redis_client()
    result = await client.blpop(settings.redis.queue_key, timeout=timeout_seconds)
    if result is None:
        return None
    _queue, raw = result
    return deserialize_job(raw)
