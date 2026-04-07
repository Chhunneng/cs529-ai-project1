import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

import json
import structlog
from app.queue_jobs import ChatMessageJob, RenderResumeJob
from sqlalchemy import text

from app.config import settings
from app.db import AsyncSessionMaker, engine
from app.logging import configure_logging
from app.chat_reply_notify import publish_chat_reply
from app.openai_client import (
    create_openai_conversation,
    delete_openai_conversation_best_effort,
    generate_reply,
)
from app.intent_classifier import classify_intent
from app.orchestrator_router import decide_next_action
from app.queue import dequeue_job
from app.render_resume import handle_render_resume


log = structlog.get_logger()


async def checkpoint_agent_run(
    *,
    session_id: uuid.UUID,
    agent_name: str,
    input_hash: str,
    status: str,
    output_json: dict[str, Any] | None = None,
    error_text: str | None = None,
    attempt: int = 1,
) -> None:
    """
    Phase 1: simple checkpoint insert.
    Later: enforce uniqueness (session_id, agent_name, input_hash) + upsert semantics.
    """
    insert_sql = text(
        """
        INSERT INTO agent_runs (
          id, session_id, agent_name, status, attempt, input_hash,
          output_json, error_text, started_at, finished_at
        )
        VALUES (
          :id, :session_id, :agent_name, :status, :attempt, :input_hash,
          :output_json, :error_text, now(), :finished_at
        )
        """
    )

    finished_at = datetime.now(timezone.utc) if status in {"succeeded", "failed"} else None
    async with AsyncSessionMaker() as db:
        await db.execute(
            insert_sql,
            {
                "id": str(uuid.uuid4()),
                "session_id": str(session_id),
                "agent_name": agent_name,
                "status": status,
                "attempt": attempt,
                "input_hash": input_hash,
                "output_json": None if output_json is None else json.dumps(output_json),
                "error_text": error_text,
                "finished_at": finished_at,
            },
        )
        await db.commit()


async def fetch_user_message_text(*, message_id: uuid.UUID) -> tuple[uuid.UUID, str]:
    sql = text("SELECT session_id, message FROM chat_messages WHERE id = :id AND role = 'user'")
    async with AsyncSessionMaker() as db:
        result = await db.execute(sql, {"id": str(message_id)})
        row = result.first()
        if row is None:
            raise RuntimeError("User message not found")
        session_id_val = row[0]
        if isinstance(session_id_val, uuid.UUID):
            session_id_parsed = session_id_val
        else:
            session_id_parsed = uuid.UUID(str(session_id_val))
        return session_id_parsed, str(row[1])


async def insert_assistant_message(*, session_id: uuid.UUID, message: str) -> uuid.UUID:
    new_id = uuid.uuid4()
    sql = text(
        """
        INSERT INTO chat_messages (id, session_id, role, message, tool_used, created_at)
        VALUES (:id, :session_id, 'assistant', :message, :tool_used, now())
        """
    )
    async with AsyncSessionMaker() as db:
        await db.execute(
            sql,
            {
                "id": str(new_id),
                "session_id": str(session_id),
                "message": message,
                "tool_used": "openai.responses.create",
            },
        )
        await db.commit()
    return new_id


async def fetch_session_flags(
    *, session_id: uuid.UUID
) -> tuple[uuid.UUID | None, uuid.UUID | None, str | None]:
    sql = text(
        "SELECT selected_resume_id, active_jd_id, openai_conversation_id "
        "FROM agent_sessions WHERE id = :id"
    )
    async with AsyncSessionMaker() as db:
        result = await db.execute(sql, {"id": str(session_id)})
        row = result.first()
        if row is None:
            raise RuntimeError("Session not found")
        selected_resume_id_raw, active_jd_id_raw, openai_raw = row[0], row[1], row[2]

        selected_resume_id = (
            selected_resume_id_raw
            if isinstance(selected_resume_id_raw, uuid.UUID) or selected_resume_id_raw is None
            else uuid.UUID(str(selected_resume_id_raw))
        )
        active_jd_id = (
            active_jd_id_raw
            if isinstance(active_jd_id_raw, uuid.UUID) or active_jd_id_raw is None
            else uuid.UUID(str(active_jd_id_raw))
        )
        openai_conv = None if openai_raw is None else str(openai_raw)
        return selected_resume_id, active_jd_id, openai_conv


async def fetch_openai_conversation_id(*, session_id: uuid.UUID) -> str | None:
    sql = text("SELECT openai_conversation_id FROM agent_sessions WHERE id = :id")
    async with AsyncSessionMaker() as db:
        result = await db.execute(sql, {"id": str(session_id)})
        row = result.first()
        if row is None:
            raise RuntimeError("Session not found")
        raw = row[0]
        return None if raw is None else str(raw)


async def try_claim_openai_conversation_id(
    *, session_id: uuid.UUID, conversation_id: str
) -> bool:
    """Persist ``conversation_id`` only if the row still has NULL. Returns True if we won the race."""
    sql = text(
        """
        UPDATE agent_sessions
        SET openai_conversation_id = :cid, updated_at = now()
        WHERE id = :sid AND openai_conversation_id IS NULL
        """
    )
    async with AsyncSessionMaker() as db:
        result = await db.execute(
            sql, {"cid": conversation_id, "sid": str(session_id)}
        )
        await db.commit()
        return (result.rowcount or 0) > 0


async def ensure_openai_conversation_id(
    *, session_id: uuid.UUID, existing: str | None
) -> str:
    if existing:
        return existing
    new_id = await create_openai_conversation()
    claimed = await try_claim_openai_conversation_id(
        session_id=session_id, conversation_id=new_id
    )
    if claimed:
        return new_id
    resolved = await fetch_openai_conversation_id(session_id=session_id)
    if resolved:
        await delete_openai_conversation_best_effort(new_id)
        return resolved
    raise RuntimeError("openai_conversation_id missing after concurrent create")


def _truncate(text_val: str, limit: int) -> str:
    if len(text_val) <= limit:
        return text_val
    return text_val[:limit].rstrip() + "…"


async def fetch_resume_context_text(*, resume_id: uuid.UUID) -> str | None:
    sql = text("SELECT parsed_json FROM resumes WHERE id = :id")
    async with AsyncSessionMaker() as db:
        result = await db.execute(sql, {"id": str(resume_id)})
        row = result.first()
        if row is None or row[0] is None:
            return None
        try:
            return _truncate(json.dumps(row[0], ensure_ascii=False), 6000)
        except Exception:
            return None


async def fetch_job_description_text(*, session_id: uuid.UUID, jd_id: uuid.UUID) -> str | None:
    sql = text(
        """
        SELECT raw_text FROM job_descriptions
        WHERE id = :id AND session_id = :session_id
        """
    )
    async with AsyncSessionMaker() as db:
        result = await db.execute(sql, {"id": str(jd_id), "session_id": str(session_id)})
        row = result.first()
        if row is None:
            return None
        return _truncate(str(row[0]), 6000)


def build_session_context_block(
    *,
    selected_resume_id: uuid.UUID | None,
    active_jd_id: uuid.UUID | None,
    resume_text: str | None,
    jd_text: str | None,
) -> str:
    parts: list[str] = []
    parts.append(f"selected_resume_id: {selected_resume_id or 'null'}")
    parts.append(f"active_jd_id: {active_jd_id or 'null'}")
    if resume_text:
        parts.append("--- Selected resume (structured JSON, may be partial) ---\n" + resume_text)
    if jd_text:
        parts.append("--- Active job description ---\n" + jd_text)
    return "\n".join(parts)


async def create_job_description_and_activate(
    *, session_id: uuid.UUID, raw_text: str
) -> uuid.UUID:
    jd_id = uuid.uuid4()
    insert_sql = text(
        """
        INSERT INTO job_descriptions (id, session_id, raw_text, extracted_json, created_at, updated_at)
        VALUES (:id, :session_id, :raw_text, NULL, now(), now())
        """
    )
    activate_sql = text(
        "UPDATE agent_sessions SET active_jd_id = :jd_id, updated_at = now() WHERE id = :session_id"
    )
    async with AsyncSessionMaker() as db:
        await db.execute(
            insert_sql,
            {"id": str(jd_id), "session_id": str(session_id), "raw_text": raw_text},
        )
        await db.execute(
            activate_sql, {"jd_id": str(jd_id), "session_id": str(session_id)}
        )
        await db.commit()
    return jd_id


async def handle_chat_message_job(job: ChatMessageJob) -> None:
    session_id = uuid.UUID(job.session_id)
    input_hash = job.input_hash

    log.info("job_received", type=job.type, session_id=str(session_id))

    agent_name = "OpenAIReplyAgent"
    await checkpoint_agent_run(session_id=session_id, agent_name=agent_name, input_hash=input_hash, status="running")

    message_id = uuid.UUID(job.message_id)

    # Load message from DB to make the worker independent from API payload shape.
    session_id_from_db, user_text = await fetch_user_message_text(message_id=message_id)
    if session_id_from_db != session_id:
        log.warn("session_id_mismatch", job_session_id=str(session_id), db_session_id=str(session_id_from_db))
        session_id = session_id_from_db

    try:
        selected_resume_id, active_jd_id, openai_conversation_existing = (
            await fetch_session_flags(session_id=session_id)
        )
        has_resume = selected_resume_id is not None
        has_job_description = active_jd_id is not None

        intent = await classify_intent(user_text=user_text)
        action = decide_next_action(
            has_resume=has_resume, has_job_description=has_job_description, user_intent=intent.intent
        )

        agent_name = action.agent_name

        if intent.intent == "job_description":
            jd_id = await create_job_description_and_activate(session_id=session_id, raw_text=user_text)
            assistant_text = (
                "Saved that job description and set it as active for this session. "
                f"JD id: {jd_id}"
            )
            reply_model = "internal"
            reply_usage = None
        else:
            resume_text = (
                await fetch_resume_context_text(resume_id=selected_resume_id) if selected_resume_id else None
            )
            jd_text = (
                await fetch_job_description_text(session_id=session_id, jd_id=active_jd_id)
                if active_jd_id
                else None
            )
            ctx = build_session_context_block(
                selected_resume_id=selected_resume_id,
                active_jd_id=active_jd_id,
                resume_text=resume_text,
                jd_text=jd_text,
            )
            conv_id = await ensure_openai_conversation_id(
                session_id=session_id, existing=openai_conversation_existing
            )
            reply = await generate_reply(
                conversation_id=conv_id,
                user_text=user_text,
                context_text=ctx,
            )
            assistant_text = reply.reply_text or "Thanks — I’ve received your message."
            reply_model = reply.model
            reply_usage = reply.usage

        assistant_id = await insert_assistant_message(session_id=session_id, message=assistant_text)
        await publish_chat_reply(
            user_message_id=message_id,
            session_id=session_id,
            assistant_message_id=assistant_id,
        )
        await checkpoint_agent_run(
            session_id=session_id,
            agent_name=agent_name,
            input_hash=input_hash,
            status="succeeded",
            output_json={
                "model": reply_model,
                "reply_text": assistant_text,
                "usage": reply_usage,
                "intent": {"label": intent.intent, "confidence": intent.confidence, "rationale": intent.rationale},
                "route": {"agent_name": action.agent_name, "reason": action.reason},
            },
        )
    except Exception as e:
        await checkpoint_agent_run(
            session_id=session_id,
            agent_name=agent_name,
            input_hash=input_hash,
            status="failed",
            error_text=str(e),
        )
        raise


async def handle_job(job: ChatMessageJob | RenderResumeJob) -> None:
    if isinstance(job, RenderResumeJob):
        await handle_render_resume(job)
        return
    if isinstance(job, ChatMessageJob):
        await handle_chat_message_job(job)
        return
    raise RuntimeError(f"Unknown job type: {type(job).__name__!r}")


async def main() -> None:
    configure_logging(settings.log_level)
    log.info("worker_starting")

    # quick connection check (will throw if misconfigured)
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))

    while True:
        job = await dequeue_job(timeout_seconds=5)
        if job is None:
            continue
        try:
            await handle_job(job)
        except Exception:
            log.exception("job_failed", job=job.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())

