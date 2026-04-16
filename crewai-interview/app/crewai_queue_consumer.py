"""Consume CrewAI bridge messages from Redis (BRPOPLPUSH) and enqueue persist jobs on the main worker queue."""

from __future__ import annotations

import logging
import os
import sys

import redis
from fastapi import HTTPException

from app.interview_tasks import GenerateBody, RefineBody, run_generate, run_refine
from app.queue_contracts import (
    CrewAiGenerateRequestMessage,
    CrewAiRefineRequestMessage,
    InterviewGeneratePersistJob,
    InterviewQuestionWire,
    InterviewRefinePersistJob,
    parse_crewai_bridge_message,
    serialize_persist_job,
)

log = logging.getLogger("crewai_queue_consumer")


def _format_error(exception: BaseException) -> str:
    if isinstance(exception, HTTPException):
        return f"{type(exception).__name__}: {exception.detail}"
    return f"{type(exception).__name__}: {exception}"


def _requeue_all_processing(
    redis_client: redis.Redis,
    *,
    processing_queue_key: str,
    request_queue_key: str,
) -> int:
    """Move every message from the processing list back to the request queue (crash recovery)."""
    moved = 0
    while redis_client.llen(processing_queue_key) > 0:
        raw = redis_client.rpop(processing_queue_key)
        if raw:
            redis_client.lpush(request_queue_key, raw)
            moved += 1
    if moved:
        log.warning("requeued_processing_messages", count=moved)
    return moved


def _finish_generate_success(
    message: CrewAiGenerateRequestMessage,
    *,
    raw_payload: str,
    redis_client: redis.Redis,
    main_queue_key: str,
    processing_queue_key: str,
) -> None:
    body = GenerateBody(
        source=message.source,
        count=message.count,
        job_description_text=message.job_description_text,
        resume_text=message.resume_text,
        question_style=message.question_style,
        level=message.level,
        focus_detail=message.focus_detail,
    )
    result = run_generate(body)
    questions_raw = result.get("questions")
    if not isinstance(questions_raw, list):
        raise RuntimeError("run_generate returned no questions list")

    question_wires: list[InterviewQuestionWire] = []
    for item in questions_raw:
        if not isinstance(item, dict):
            continue
        prompt = str(item.get("prompt") or "").strip()
        sample_answer = str(item.get("sample_answer") or "").strip()
        meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        if not prompt or not sample_answer:
            continue
        question_wires.append(
            InterviewQuestionWire(prompt=prompt, sample_answer=sample_answer, metadata=meta),
        )

    if not question_wires:
        raise RuntimeError("No valid questions produced by run_generate")

    persist = InterviewGeneratePersistJob(
        interview_job_request_id=message.interview_job_request_id,
        practice_session_id=message.practice_session_id,
        source=message.source,
        success=True,
        questions=question_wires,
        error_text=None,
    )
    redis_client.lrem(processing_queue_key, 1, raw_payload)
    redis_client.rpush(main_queue_key, serialize_persist_job(persist))


def _finish_refine_success(
    message: CrewAiRefineRequestMessage,
    *,
    raw_payload: str,
    redis_client: redis.Redis,
    main_queue_key: str,
    processing_queue_key: str,
) -> None:
    body = RefineBody(
        question=message.question,
        ideal_answer=message.ideal_answer,
        user_answer=message.user_answer,
    )
    result = run_refine(body)
    persist = InterviewRefinePersistJob(
        interview_job_request_id=message.interview_job_request_id,
        practice_session_id=message.practice_session_id,
        answer_attempt_id=message.answer_attempt_id,
        success=True,
        feedback=result.get("feedback"),
        refined_answer=result.get("refined_answer"),
        scores=result.get("scores") if isinstance(result.get("scores"), dict) else None,
        error_text=None,
    )
    redis_client.lrem(processing_queue_key, 1, raw_payload)
    redis_client.rpush(main_queue_key, serialize_persist_job(persist))


def _handle_failure(
    message: CrewAiGenerateRequestMessage | CrewAiRefineRequestMessage,
    *,
    raw_payload: str,
    exception: BaseException,
    redis_client: redis.Redis,
    main_queue_key: str,
    request_queue_key: str,
    processing_queue_key: str,
    dead_letter_queue_key: str,
    max_attempts: int,
) -> None:
    redis_client.lrem(processing_queue_key, 1, raw_payload)
    new_attempt_count = message.attempt_count + 1
    error_text = _format_error(exception)

    if new_attempt_count >= max_attempts:
        redis_client.rpush(dead_letter_queue_key, raw_payload)
        if isinstance(message, CrewAiGenerateRequestMessage):
            persist = InterviewGeneratePersistJob(
                interview_job_request_id=message.interview_job_request_id,
                practice_session_id=message.practice_session_id,
                source=message.source,
                success=False,
                questions=None,
                error_text=error_text,
            )
        else:
            persist = InterviewRefinePersistJob(
                interview_job_request_id=message.interview_job_request_id,
                practice_session_id=message.practice_session_id,
                answer_attempt_id=message.answer_attempt_id,
                success=False,
                feedback=None,
                refined_answer=None,
                scores=None,
                error_text=error_text,
            )
        redis_client.rpush(main_queue_key, serialize_persist_job(persist))
        log.error(
            "crewai_job_failed_max_attempts",
            extra={
                "message_type": message.message_type,
                "interview_job_request_id": message.interview_job_request_id,
                "attempts": new_attempt_count,
            },
        )
        return

    updated_message = message.model_copy(update={"attempt_count": new_attempt_count})
    redis_client.rpush(request_queue_key, updated_message.model_dump_json())
    log.warning(
        "crewai_job_requeued",
        extra={
            "message_type": message.message_type,
            "interview_job_request_id": message.interview_job_request_id,
            "attempt_count": new_attempt_count,
            "error": error_text,
        },
    )


def run_consumer_loop() -> None:
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        log.error("REDIS_URL is required for the CrewAI queue consumer")
        sys.exit(1)

    main_queue_key = os.environ.get("QUEUE_KEY", "queue:agent-jobs")
    request_queue_key = os.environ.get("CREWAI_REQUEST_QUEUE_KEY", "queue:crewai-interview-requests")
    processing_queue_key = os.environ.get("CREWAI_PROCESSING_LIST_KEY", "queue:crewai-interview-processing")
    dead_letter_queue_key = os.environ.get("CREWAI_DEAD_LETTER_LIST_KEY", "queue:crewai-interview-dead-letter")
    max_attempts = int(os.environ.get("CREWAI_MAX_ATTEMPTS", "3"))
    requeue_on_start = os.environ.get("CREWAI_REQUEUE_PROCESSING_ON_START", "true").lower() in (
        "1",
        "true",
        "yes",
    )

    redis_client = redis.Redis.from_url(redis_url, decode_responses=True)

    if requeue_on_start:
        _requeue_all_processing(
            redis_client,
            processing_queue_key=processing_queue_key,
            request_queue_key=request_queue_key,
        )

    log.info(
        "crewai_queue_consumer_started",
        extra={
            "main_queue_key": main_queue_key,
            "request_queue_key": request_queue_key,
            "processing_queue_key": processing_queue_key,
            "max_attempts": max_attempts,
        },
    )

    while True:
        raw_payload = redis_client.brpoplpush(request_queue_key, processing_queue_key, timeout=5)
        if raw_payload is None:
            continue

        try:
            message = parse_crewai_bridge_message(raw_payload)
        except Exception as parse_error:
            log.exception("crewai_bridge_parse_failed", extra={"raw": raw_payload[:500]})
            redis_client.lrem(processing_queue_key, 1, raw_payload)
            redis_client.rpush(dead_letter_queue_key, raw_payload)
            continue

        try:
            if isinstance(message, CrewAiGenerateRequestMessage):
                _finish_generate_success(
                    message,
                    raw_payload=raw_payload,
                    redis_client=redis_client,
                    main_queue_key=main_queue_key,
                    processing_queue_key=processing_queue_key,
                )
            else:
                _finish_refine_success(
                    message,
                    raw_payload=raw_payload,
                    redis_client=redis_client,
                    main_queue_key=main_queue_key,
                    processing_queue_key=processing_queue_key,
                )
        except Exception as run_error:
            log.exception(
                "crewai_job_run_failed",
                extra={"interview_job_request_id": message.interview_job_request_id},
            )
            _handle_failure(
                message,
                raw_payload=raw_payload,
                exception=run_error,
                redis_client=redis_client,
                main_queue_key=main_queue_key,
                request_queue_key=request_queue_key,
                processing_queue_key=processing_queue_key,
                dead_letter_queue_key=dead_letter_queue_key,
                max_attempts=max_attempts,
            )


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(message)s",
    )
    run_consumer_loop()


if __name__ == "__main__":
    main()
