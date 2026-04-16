"""Enqueue work to the CrewAI Redis queue (separate from the main agent job queue)."""

from __future__ import annotations

import redis.asyncio as redis

from app.core.config import settings
from app.queue_jobs.crewai_bridge import CrewAiBridgeMessage, serialize_crewai_bridge_message


async def _redis() -> redis.Redis:
    return redis.from_url(settings.redis.url, decode_responses=True)


async def enqueue_crewai_bridge_message(message: CrewAiBridgeMessage) -> None:
    """Push a message to the CrewAI request list for the CrewAI worker to process."""
    client = await _redis()
    payload = serialize_crewai_bridge_message(message)
    await client.rpush(settings.redis.crewai_request_queue_key, payload)
