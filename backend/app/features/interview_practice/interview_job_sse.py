"""Server-Sent Events stream for a single interview job request (replaces client polling)."""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncIterator

import structlog

from app.db.session import AsyncSessionMaker
from app.features.interview_practice.interview_job_redis import interview_job_channel
from app.features.interview_practice.repositories import load_job_request
from app.features.job_queue.redis import get_redis_client
from app.schemas.interview_practice import InterviewJobStatusResponse

log = structlog.get_logger()

INTERVIEW_JOB_SSE_TIMEOUT_SECONDS = 300


def _sse_data_line(obj: dict) -> str:
    return f"data: {json.dumps(obj, default=str)}\n\n"


def _job_to_payload(row: object) -> dict:
    return InterviewJobStatusResponse.model_validate(row).model_dump(mode="json")


async def stream_interview_job_sse(request_id: uuid.UUID) -> AsyncIterator[str]:
    """Yield SSE lines until the job is terminal, the client disconnects, or timeout."""
    async with AsyncSessionMaker() as db:
        row = await load_job_request(db, request_id=request_id)
    if row is None:
        yield _sse_data_line({"type": "error", "detail": "Request not found"})
        return

    job_payload = _job_to_payload(row)
    yield _sse_data_line({"type": "snapshot", "job": job_payload})

    if row.status in ("done", "error"):
        yield _sse_data_line({"type": "complete"})
        return

    channel = interview_job_channel(request_id)
    client = await get_redis_client()
    pubsub = client.pubsub()
    try:
        await pubsub.subscribe(channel)

        async with AsyncSessionMaker() as db2:
            row2 = await load_job_request(db2, request_id=request_id)
        if row2 is not None and row2.status in ("done", "error"):
            yield _sse_data_line({"type": "update", "job": _job_to_payload(row2)})
            yield _sse_data_line({"type": "complete"})
            return

        deadline = time.monotonic() + INTERVIEW_JOB_SSE_TIMEOUT_SECONDS
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                yield _sse_data_line(
                    {"type": "timeout", "detail": "No completion within the wait window."},
                )
                return
            msg = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=min(1.0, remaining),
            )
            if msg is None:
                continue
            if msg.get("type") != "message":
                continue
            raw_data = msg.get("data")
            if not isinstance(raw_data, str):
                continue

            async with AsyncSessionMaker() as db3:
                row3 = await load_job_request(db3, request_id=request_id)
            if row3 is None:
                yield _sse_data_line({"type": "error", "detail": "Request not found"})
                return

            yield _sse_data_line({"type": "update", "job": _job_to_payload(row3)})
            if row3.status in ("done", "error"):
                yield _sse_data_line({"type": "complete"})
                return
    finally:
        try:
            await pubsub.unsubscribe(channel)
        except Exception:
            log.warning("interview_job_sse_pubsub_unsubscribe_failed", exc_info=True)
        try:
            await pubsub.aclose()
        except Exception:
            log.warning("interview_job_sse_pubsub_close_failed", exc_info=True)
        try:
            await client.aclose()
        except Exception:
            log.warning("interview_job_sse_redis_client_close_failed", exc_info=True)
