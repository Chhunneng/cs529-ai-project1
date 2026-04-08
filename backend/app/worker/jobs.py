from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select, update

from app.core.config import settings
from app.db.session import AsyncSessionMaker
from app.models.agent_run import AgentRun
from app.models.agent_session import AgentSession
from app.models.chat_message import ChatMessage
from app.models.job_description import JobDescription
from app.models.resume import Resume
from app.orchestrator.router import decide_next_action
from app.openai.resume_extract import extract_resume_profile_json
from app.queue_jobs import ChatMessageJob, ParseResumeJob, RenderResumeJob
from app.openai.chat_tool_context import ChatToolContext
from app.openai.client import (
    create_openai_conversation,
    delete_openai_conversation_best_effort,
)
from app.openai.resume_chat_agent import run_resume_chat_agent
from app.openai.intent import classify_intent
from app.openai.resume_scope import check_resume_scope
from app.services.chat_reply_notify import publish_chat_reply
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


async def insert_assistant_message(
    *, session_id: uuid.UUID, message: str, tool_used: str | None = "openai.agents.Runner"
) -> uuid.UUID:
    new_id = uuid.uuid4()
    async with AsyncSessionMaker() as db:
        db.add(
            ChatMessage(
                id=new_id,
                session_id=session_id,
                role="assistant",
                message=message,
                tool_used=tool_used,
            )
        )
        await db.commit()
    return new_id


async def fetch_session_flags(
    *, session_id: uuid.UUID
) -> tuple[uuid.UUID | None, uuid.UUID | None, str | None, str | None]:
    async with AsyncSessionMaker() as db:
        sess = await db.get(AgentSession, session_id)
        if sess is None:
            raise RuntimeError("Session not found")
        return (
            sess.selected_resume_id,
            sess.active_jd_id,
            sess.openai_conversation_id,
            sess.previous_response_id,
        )


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


async def create_job_description_and_activate(
    *, session_id: uuid.UUID, raw_text: str
) -> uuid.UUID:
    jd_id = uuid.uuid4()
    async with AsyncSessionMaker() as db:
        db.add(
            JobDescription(
                id=jd_id,
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
        selected_resume_id, active_jd_id, openai_conversation_existing, scope_prev_id = (
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
            tool_calls: list[str] = []
        else:
            # Scope guardrail (token-efficient): chain via Responses previous_response_id.
            # Store the *used* previous_response_id on the user message row for debugging/audit.
            async with AsyncSessionMaker() as db:
                msg = await db.get(ChatMessage, message_id)
                if msg is not None and msg.role == "user":
                    msg.previous_response_id = scope_prev_id
                sess = await db.get(AgentSession, session_id)
                if sess is None:
                    raise RuntimeError("Session not found")
                # Ensure we read the current value from DB (not a stale local copy).
                scope_prev_id = sess.previous_response_id
                await db.commit()

            scope = await check_resume_scope(user_text=user_text, previous_response_id=scope_prev_id)

            # Advance the session scope thread head even if out-of-scope, so the chain stays consistent.
            if scope.response_id:
                async with AsyncSessionMaker() as db:
                    sess = await db.get(AgentSession, session_id)
                    if sess is None:
                        raise RuntimeError("Session not found")
                    sess.previous_response_id = scope.response_id
                    await db.commit()
                scope_prev_id = scope.response_id

            if not scope.is_related_to_resume_job:
                assistant_text = (
                    "I'm only set up to help with resumes, job descriptions, and tailoring in this app. "
                    "Ask something in that area—like updating your resume, reviewing a job posting, or matching your resume to a role."
                )
                reply_model = settings.openai.model
                reply_usage = None
                tool_calls = ["scope_guardrail"]
            else:
                conv_id = await ensure_openai_conversation_id(
                    session_id=session_id, existing=openai_conversation_existing
                )
                tool_ctx = ChatToolContext(
                    session_id=session_id,
                    selected_resume_id=selected_resume_id,
                    active_jd_id=active_jd_id,
                )
                agent_run = await run_resume_chat_agent(
                    conversation_id=conv_id,
                    user_text=user_text,
                    tool_context=tool_ctx,
                )
                assistant_text = agent_run.reply_text
                reply_model = settings.openai.model
                reply_usage = agent_run.usage
                tool_calls = agent_run.tool_calls

        assistant_id = await insert_assistant_message(
            session_id=session_id,
            message=assistant_text,
            tool_used=(
                "internal.jd_ingest"
                if intent.intent == "job_description"
                else "openai.agents.Runner"
            ),
        )
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
                "tool_calls": tool_calls,
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


async def handle_parse_resume_job(job: ParseResumeJob) -> None:
    resume_id = uuid.UUID(job.resume_id)
    log.info("parse_resume_start", resume_id=str(resume_id))
    if not settings.openai.api_key:
        log.warn("parse_resume_skipped_no_api_key", resume_id=str(resume_id))
        return

    async with AsyncSessionMaker() as db:
        r = await db.get(Resume, resume_id)
        if r is None:
            log.warn("parse_resume_resume_missing", resume_id=str(resume_id))
            return
        body = (r.content_text or "").strip()
        if not body:
            log.warn("parse_resume_no_content_text", resume_id=str(resume_id))
            return

    try:
        parsed = await extract_resume_profile_json(resume_text=body)
    except Exception:
        log.exception("parse_resume_failed", resume_id=str(resume_id))
        return

    async with AsyncSessionMaker() as db:
        r2 = await db.get(Resume, resume_id)
        if r2 is None:
            return
        r2.parsed_json = parsed
        await db.commit()
    log.info("parse_resume_done", resume_id=str(resume_id))


async def handle_job(job: ChatMessageJob | RenderResumeJob | ParseResumeJob) -> None:
    if isinstance(job, RenderResumeJob):
        await handle_render_resume(job)
        return
    if isinstance(job, ParseResumeJob):
        await handle_parse_resume_job(job)
        return
    if isinstance(job, ChatMessageJob):
        await handle_chat_message_job(job)
        return
    raise RuntimeError(f"Unknown job type: {type(job).__name__!r}")
