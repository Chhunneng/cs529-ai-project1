import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

import json
import structlog
from sqlalchemy import text

from app.config import settings
from app.db import AsyncSessionMaker, engine
from app.logging import configure_logging
from app.chat_reply_notify import publish_chat_reply
from app.openai_client import generate_reply
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


async def handle_chat_message_job(job: dict[str, Any]) -> None:
    job_type = job.get("type")
    session_id = uuid.UUID(job["session_id"])
    input_hash = str(job.get("input_hash") or "")

    log.info("job_received", type=job_type, session_id=str(session_id))

    agent_name = "OpenAIReplyAgent"
    await checkpoint_agent_run(session_id=session_id, agent_name=agent_name, input_hash=input_hash, status="running")

    message_id_raw = job.get("message_id")
    if not message_id_raw:
        raise RuntimeError("Job missing message_id")
    message_id = uuid.UUID(str(message_id_raw))

    # Load message from DB to make the worker independent from API payload shape.
    session_id_from_db, user_text = await fetch_user_message_text(message_id=message_id)
    if session_id_from_db != session_id:
        log.warn("session_id_mismatch", job_session_id=str(session_id), db_session_id=str(session_id_from_db))
        session_id = session_id_from_db

    try:
        reply = await generate_reply(user_text=user_text)
        assistant_text = reply.reply_text or "Thanks — I’ve received your message."

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
            output_json={"model": reply.model, "reply_text": assistant_text, "usage": reply.usage},
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


async def handle_job(job: dict[str, Any]) -> None:
    job_type = job.get("type")
    if job_type == "render_resume":
        await handle_render_resume(job)
        return
    if job_type == "chat_message":
        await handle_chat_message_job(job)
        return
    raise RuntimeError(f"Unknown job type: {job_type!r}")


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
            log.exception("job_failed", job=job)


if __name__ == "__main__":
    asyncio.run(main())

