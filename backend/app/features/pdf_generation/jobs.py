from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import AsyncSessionMaker
from app.features.latex.service import compile_latex_to_pdf
from app.services.latex_compile import LaTeXCompileFailed
from app.models.agent_run import AgentRun
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.job_description import JobDescription
from app.models.pdf_artifact import PdfArtifact
from app.llm.conversation_session import build_sqlalchemy_conversation_session
from app.llm.intent import classify_intent
from app.llm.resume_agent_context import ResumeAgentContext
from app.llm.resume_chat_agent import run_resume_pdf_agent
from app.llm.resume_scope import check_resume_scope
from app.queue_jobs import ResumePdfGenerationJob
from app.services.chat_reply_notify import publish_chat_reply

log = structlog.get_logger()


async def _prior_assistant_snippet(*, session_id: uuid.UUID, before_sequence: int) -> str | None:
    """Last assistant message before the given sequence (for scope context without OpenAI response chaining)."""
    async with AsyncSessionMaker() as db:
        content = await db.scalar(
            select(ChatMessage.content)
            .where(
                ChatMessage.session_id == session_id,
                ChatMessage.role == "assistant",
                ChatMessage.sequence < before_sequence,
            )
            .order_by(ChatMessage.sequence.desc())
            .limit(1)
        )
    if content is None or not str(content).strip():
        return None
    text = str(content).strip()
    if len(text) > 1200:
        return text[:1200] + "…"
    return text


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


async def fetch_user_message_row(*, message_id: uuid.UUID) -> ChatMessage | None:
    async with AsyncSessionMaker() as db:
        msg = await db.scalar(
            select(ChatMessage).where(ChatMessage.id == message_id, ChatMessage.role == "user")
        )
        return msg


async def next_message_sequence(*, session_id: uuid.UUID) -> int:
    async with AsyncSessionMaker() as db:
        current = await db.scalar(
            select(func.coalesce(func.max(ChatMessage.sequence), 0)).where(
                ChatMessage.session_id == session_id
            )
        )
        return int(current or 0) + 1


async def insert_assistant_message(
    *,
    session_id: uuid.UUID,
    content: str,
    sequence: int,
    tool_used: str | None = "openai.agents.Runner",
    pdf_artifact_id: uuid.UUID | None = None,
) -> uuid.UUID:
    new_id = uuid.uuid4()
    async with AsyncSessionMaker() as db:
        db.add(
            ChatMessage(
                id=new_id,
                session_id=session_id,
                role="assistant",
                content=content,
                sequence=sequence,
                tool_used=tool_used,
                pdf_artifact_id=pdf_artifact_id,
            )
        )
        await db.commit()
    return new_id


async def create_job_description_and_activate(*, session_id: uuid.UUID, raw_text: str) -> uuid.UUID:
    jd_id = uuid.uuid4()
    async with AsyncSessionMaker() as db:
        db.add(
            JobDescription(
                id=jd_id,
                raw_text=raw_text,
                extracted_json=None,
            )
        )
        sess = await db.get(ChatSession, session_id)
        if sess is None:
            raise RuntimeError("Session not found")
        sess.job_description_id = jd_id
        await db.commit()
    return jd_id


async def handle_resume_pdf_generation_job(job: ResumePdfGenerationJob) -> None:
    session_id = uuid.UUID(job.session_id)
    input_hash = job.input_hash
    agent_name = "ResumePdfAgent"

    log.info("job_received", type=job.type, session_id=str(session_id))

    await checkpoint_agent_run(
        session_id=session_id, agent_name=agent_name, input_hash=input_hash, status="running"
    )

    message_id = uuid.UUID(job.user_message_id)
    user_msg = await fetch_user_message_row(message_id=message_id)
    if user_msg is None:
        await checkpoint_agent_run(
            session_id=session_id,
            agent_name=agent_name,
            input_hash=input_hash,
            status="failed",
            error_text="user_message_not_found",
        )
        raise RuntimeError("User message not found")

    if user_msg.session_id != session_id:
        log.warn(
            "session_id_mismatch",
            job_session_id=str(session_id),
            db_session_id=str(user_msg.session_id),
        )
        session_id = user_msg.session_id

    user_text = user_msg.content

    try:
        async with AsyncSessionMaker() as db:
            sess = await db.get(ChatSession, session_id)
            if sess is None:
                raise RuntimeError("Session not found")
            resume_id = (
                uuid.UUID(job.resume_id) if job.resume_id is not None else sess.resume_id
            )
            job_description_id = (
                uuid.UUID(job.job_description_id)
                if job.job_description_id is not None
                else sess.job_description_id
            )
            resume_template_id = (
                uuid.UUID(job.resume_template_id)
                if job.resume_template_id is not None
                else sess.resume_template_id
            )

        intent = await classify_intent(user_text=user_text)

        if intent.intent == "job_description":
            jd_id = await create_job_description_and_activate(session_id=session_id, raw_text=user_text)
            assistant_text = (
                "Saved that job description and set it as active for this session. "
                f"Job description id: {jd_id}"
            )
            seq = await next_message_sequence(session_id=session_id)
            assistant_id = await insert_assistant_message(
                session_id=session_id,
                content=assistant_text,
                sequence=seq,
                tool_used="internal.job_description_ingest",
                pdf_artifact_id=None,
            )
            await publish_chat_reply(
                user_message_id=message_id,
                session_id=session_id,
                assistant_message_id=assistant_id,
                pdf_artifact_id=None,
            )
            await checkpoint_agent_run(
                session_id=session_id,
                agent_name="JobDescriptionIngest",
                input_hash=input_hash,
                status="succeeded",
                output_json={
                    "model": "internal",
                    "reply_text": assistant_text,
                    "intent": asdict(intent),
                },
            )
            return

        prior_for_scope = await _prior_assistant_snippet(
            session_id=session_id,
            before_sequence=user_msg.sequence,
        )
        scope = await check_resume_scope(user_text=user_text, prior_context=prior_for_scope)

        seq = await next_message_sequence(session_id=session_id)

        if not scope.is_related_to_resume_job:
            assistant_text = (
                "I'm only set up to help with resumes, job descriptions, and tailoring in this app. "
                "Ask something in that area—like updating your resume, reviewing a job posting, "
                "or matching your resume to a role."
            )
            assistant_id = await insert_assistant_message(
                session_id=session_id,
                content=assistant_text,
                sequence=seq,
                tool_used="scope_guardrail",
                pdf_artifact_id=None,
            )
            await publish_chat_reply(
                user_message_id=message_id,
                session_id=session_id,
                assistant_message_id=assistant_id,
                pdf_artifact_id=None,
            )
            await checkpoint_agent_run(
                session_id=session_id,
                agent_name=agent_name,
                input_hash=input_hash,
                status="succeeded",
                output_json={
                    "model": settings.openai.model,
                    "reply_text": assistant_text,
                    "tool_calls": ["scope_guardrail"],
                    "intent": asdict(intent),
                },
            )
            return

        if resume_template_id is None:
            assistant_text = (
                "Link a resume template to this session (or pass template_id with your message) "
                "so I can generate a PDF."
            )
            assistant_id = await insert_assistant_message(
                session_id=session_id,
                content=assistant_text,
                sequence=seq,
                tool_used="server.validation",
                pdf_artifact_id=None,
            )
            await publish_chat_reply(
                user_message_id=message_id,
                session_id=session_id,
                assistant_message_id=assistant_id,
                pdf_artifact_id=None,
            )
            await checkpoint_agent_run(
                session_id=session_id,
                agent_name=agent_name,
                input_hash=input_hash,
                status="succeeded",
                output_json={"reply_text": assistant_text, "skipped": "no_template"},
            )
            return

        memory_session = build_sqlalchemy_conversation_session(chat_session_id=session_id)
        tool_ctx = ResumeAgentContext(
            chat_session_id=session_id,
            resume_id=resume_id,
            job_description_id=job_description_id,
            resume_template_id=resume_template_id,
        )
        agent_run = await run_resume_pdf_agent(
            user_text=user_text,
            tool_context=tool_ctx,
            memory_session=memory_session,
        )

        pdf_artifact_id: uuid.UUID | None = None
        assistant_text = agent_run.assistant_message
        latex = agent_run.latex_document

        if latex:
            try:
                pdf_bytes, _log_tail = await compile_latex_to_pdf(latex=latex)
            except LaTeXCompileFailed as compile_exc:
                d = compile_exc.detail
                extra = d.get("hint") or d.get("latex_error") or str(compile_exc)
                log.warning(
                    "pdf_compile_failed",
                    error=str(compile_exc),
                    line_number=d.get("line_number"),
                    latex_error=d.get("latex_error"),
                )
                assistant_text = (
                    f"{assistant_text}\n\n"
                    f"(PDF compile failed: {extra}. "
                    "Try simplifying the layout or fixing LaTeX errors.)"
                )
            except Exception as compile_exc:
                log.warning("pdf_compile_failed", error=str(compile_exc))
                assistant_text = (
                    f"{assistant_text}\n\n"
                    f"(PDF compile failed: {compile_exc!s}. "
                    "Try simplifying the layout or fixing LaTeX errors.)"
                )
            else:
                artifact_id = uuid.uuid4()
                rel_path = f"pdf-artifacts/{artifact_id}.pdf"
                root = Path(settings.storage.artifacts_dir).resolve()
                dest = (root / rel_path).resolve()
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(pdf_bytes)
                sha = hashlib.sha256(pdf_bytes).hexdigest()
                async with AsyncSessionMaker() as db:
                    db.add(
                        PdfArtifact(
                            id=artifact_id,
                            session_id=session_id,
                            storage_relpath=rel_path,
                            mime_type="application/pdf",
                            sha256_hex=sha,
                        )
                    )
                    await db.commit()
                pdf_artifact_id = artifact_id

        assistant_id = await insert_assistant_message(
            session_id=session_id,
            content=assistant_text,
            sequence=seq,
            tool_used="openai.agents.Runner",
            pdf_artifact_id=pdf_artifact_id,
        )
        await publish_chat_reply(
            user_message_id=message_id,
            session_id=session_id,
            assistant_message_id=assistant_id,
            pdf_artifact_id=pdf_artifact_id,
        )
        await checkpoint_agent_run(
            session_id=session_id,
            agent_name=agent_name,
            input_hash=input_hash,
            status="succeeded",
            output_json={
                "model": settings.openai.model,
                "reply_text": assistant_text,
                "usage": agent_run.usage,
                "tool_calls": agent_run.tool_calls,
                "pdf_artifact_id": str(pdf_artifact_id) if pdf_artifact_id else None,
                "intent": asdict(intent),
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
