from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select, update

from app.db.session import AsyncSessionMaker
from app.models.agent_run import AgentRun
from app.models.agent_session import AgentSession
from app.models.chat_message import ChatMessage
from app.models.job_description import JobDescription
from app.models.resume import Resume
from app.orchestrator.router import decide_next_action
from app.queue_jobs import ChatMessageJob, RenderResumeJob
from app.services.chat_reply_notify import publish_chat_reply
from app.worker.intent_classifier import classify_intent
from app.worker.openai_client import (
    create_openai_conversation,
    delete_openai_conversation_best_effort,
    generate_reply,
)
from app.worker.render_resume import handle_render_resume

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
    finished_at = datetime.now(timezone.utc) if status in {"succeeded", "failed"} else None
    async with AsyncSessionMaker() as db:
        run = AgentRun(
            session_id=session_id,
            agent_name=agent_name,
            status=status,
            attempt=attempt,
            input_hash=input_hash,
            output_json=output_json,
            error_text=error_text,
            finished_at=finished_at,
        )
        db.add(run)
        await db.commit()


async def fetch_user_message_text(*, message_id: uuid.UUID) -> tuple[uuid.UUID, str]:
    async with AsyncSessionMaker() as db:
        msg = await db.scalar(
            select(ChatMessage).where(ChatMessage.id == message_id, ChatMessage.role == "user")
        )
        if msg is None:
            raise RuntimeError("User message not found")
        return msg.session_id, msg.message


async def insert_assistant_message(*, session_id: uuid.UUID, message: str) -> uuid.UUID:
    new_id = uuid.uuid4()
    async with AsyncSessionMaker() as db:
        db.add(
            ChatMessage(
                id=new_id,
                session_id=session_id,
                role="assistant",
                message=message,
                tool_used="openai.responses.create",
            )
        )
        await db.commit()
    return new_id


async def fetch_session_flags(
    *, session_id: uuid.UUID
) -> tuple[uuid.UUID | None, uuid.UUID | None, str | None]:
    async with AsyncSessionMaker() as db:
        sess = await db.get(AgentSession, session_id)
        if sess is None:
            raise RuntimeError("Session not found")
        return sess.selected_resume_id, sess.active_jd_id, sess.openai_conversation_id


async def fetch_openai_conversation_id(*, session_id: uuid.UUID) -> str | None:
    async with AsyncSessionMaker() as db:
        sess = await db.get(AgentSession, session_id)
        if sess is None:
            raise RuntimeError("Session not found")
        return sess.openai_conversation_id


async def try_claim_openai_conversation_id(
    *, session_id: uuid.UUID, conversation_id: str
) -> bool:
    async with AsyncSessionMaker() as db:
        result = await db.execute(
            update(AgentSession)
            .where(AgentSession.id == session_id, AgentSession.openai_conversation_id.is_(None))
            .values(openai_conversation_id=conversation_id)
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
    async with AsyncSessionMaker() as db:
        r = await db.get(Resume, resume_id)
        if r is None or r.parsed_json is None:
            return None
        try:
            return _truncate(json.dumps(r.parsed_json, ensure_ascii=False), 6000)
        except Exception:
            return None


async def fetch_job_description_text(*, session_id: uuid.UUID, jd_id: uuid.UUID) -> str | None:
    async with AsyncSessionMaker() as db:
        jd = await db.scalar(
            select(JobDescription).where(
                JobDescription.id == jd_id, JobDescription.session_id == session_id
            )
        )
        if jd is None:
            return None
        return _truncate(str(jd.raw_text), 6000)


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
    async with AsyncSessionMaker() as db:
        db.add(
            JobDescription(
                id=jd_id,
                session_id=session_id,
                raw_text=raw_text,
                extracted_json=None,
            )
        )
        sess = await db.get(AgentSession, session_id)
        if sess is None:
            raise RuntimeError("Session not found")
        sess.active_jd_id = jd_id
        await db.commit()
    return jd_id


async def handle_chat_message_job(job: ChatMessageJob) -> None:
    session_id = uuid.UUID(job.session_id)
    input_hash = job.input_hash

    log.info("job_received", type=job.type, session_id=str(session_id))

    agent_name = "OpenAIReplyAgent"
    await checkpoint_agent_run(
        session_id=session_id, agent_name=agent_name, input_hash=input_hash, status="running"
    )

    message_id = uuid.UUID(job.message_id)

    session_id_from_db, user_text = await fetch_user_message_text(message_id=message_id)
    if session_id_from_db != session_id:
        log.warn(
            "session_id_mismatch",
            job_session_id=str(session_id),
            db_session_id=str(session_id_from_db),
        )
        session_id = session_id_from_db

    try:
        selected_resume_id, active_jd_id, openai_conversation_existing = (
            await fetch_session_flags(session_id=session_id)
        )
        has_resume = selected_resume_id is not None
        has_job_description = active_jd_id is not None

        intent = await classify_intent(user_text=user_text)
        action = decide_next_action(
            has_resume=has_resume,
            has_job_description=has_job_description,
            user_intent=intent.intent,
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
                await fetch_resume_context_text(resume_id=selected_resume_id)
                if selected_resume_id
                else None
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
                "intent": {
                    "label": intent.intent,
                    "confidence": intent.confidence,
                    "rationale": intent.rationale,
                },
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
