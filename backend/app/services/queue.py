import redis.asyncio as redis

from app.queue_jobs import AgentJob, serialize_job

from app.core.config import settings


QUEUE_KEY = "queue:agent-jobs"


async def get_redis_client() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


async def enqueue_job(job: AgentJob) -> None:
    client = await get_redis_client()
    await client.rpush(QUEUE_KEY, serialize_job(job))
