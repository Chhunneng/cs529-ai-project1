"""Redis Pub/Sub for interview job status updates (SSE clients subscribe per request id)."""

from __future__ import annotations

import json
import uuid

import structlog

from app.features.job_queue.redis import get_redis_client

log = structlog.get_logger()

INTERVIEW_JOB_CHANNEL_PREFIX = "interview:job:"


def interview_job_channel(request_id: uuid.UUID) -> str:
    return f"{INTERVIEW_JOB_CHANNEL_PREFIX}{request_id}"


async def publish_interview_job_updated(*, request_id: uuid.UUID) -> None:
    """Notify SSE subscribers that ``InterviewJobRequest`` row changed (after DB commit)."""
    try:
        client = await get_redis_client()
        channel = interview_job_channel(request_id)
        payload = json.dumps({"request_id": str(request_id)})
        await client.publish(channel, payload)
    except Exception:
        log.warning("interview_job_publish_failed", request_id=str(request_id), exc_info=True)
