from __future__ import annotations

import uuid

import structlog
from sqlalchemy import func, select

from app.db.session import AsyncSessionMaker
from app.features.sessions.repositories import first_assistant_after_user_created_at
from app.features.latex.service import compile_latex_to_pdf
from app.features.pdf_generation.pdf_artifacts import (
    insert_pdf_artifact_row,
    write_pdf_artifact_file,
)
from app.features.latex.exceptions import LaTeXCompileFailed
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.job_description import JobDescription
from app.llm.sessions import build_sqlalchemy_conversation_session
from app.llm.context import ResumeAgentContext
from app.llm.resume_chat_agent import run_resume_pdf_agent
from app.queue_jobs import ResumePdfGenerationJob
from app.features.sessions.chat_reply_redis import (
    clear_chat_turn_pending,
    publish_chat_reply,
)

log = structlog.get_logger()

_ERROR_ASSISTANT_PREFIX = (
    "Sorry — something went wrong while generating a reply. "
    "You can try sending your message again.\n\n"
)


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
        session = await db.get(ChatSession, session_id)
        if session is None:
            raise RuntimeError("Session not found")
        session.job_description_id = jd_id
        await db.commit()
    return jd_id


async def _run_resume_pdf_generation_core(
    job: ResumePdfGenerationJob,
    *,
    session_id: uuid.UUID,
    message_id: uuid.UUID,
    user_message: ChatMessage,
) -> None:
    user_text = user_message.content

    async with AsyncSessionMaker() as db:
        session = await db.get(ChatSession, session_id)
        if session is None:
            raise RuntimeError("Session not found")
        resume_id = uuid.UUID(job.resume_id) if job.resume_id is not None else None
        job_description_id = (
            uuid.UUID(job.job_description_id) if job.job_description_id is not None else None
        )
        resume_template_id = (
            uuid.UUID(job.resume_template_id) if job.resume_template_id is not None else None
        )

    seq = await next_message_sequence(session_id=session_id)

    memory_session = build_sqlalchemy_conversation_session(chat_session_id=session_id)
    tool_context = ResumeAgentContext(
        chat_session_id=session_id,
        resume_id=resume_id,
        job_description_id=job_description_id,
        resume_template_id=resume_template_id,
    )
    pdf_agent_result = await run_resume_pdf_agent(
        user_text=user_text,
        tool_context=tool_context,
        memory_session=memory_session,
    )

    pdf_artifact_id: uuid.UUID | None = None
    assistant_text = pdf_agent_result.assistant_message
    latex = pdf_agent_result.latex_document

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
            written = write_pdf_artifact_file(pdf_bytes)
            pdf_artifact_id = await insert_pdf_artifact_row(session_id, written)

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


async def handle_resume_pdf_generation_job(job: ResumePdfGenerationJob) -> None:
    session_id = uuid.UUID(job.session_id)
    message_id = uuid.UUID(job.user_message_id)

    log.info("job_received", type=job.type, session_id=str(session_id))

    user_message = await fetch_user_message_row(message_id=message_id)
    if user_message is None:
        log.warning("user_message_missing", user_message_id=str(message_id))
        await clear_chat_turn_pending(session_id=session_id, user_message_id=message_id)
        return

    user_message_created_at = user_message.created_at
    if await first_assistant_after_user_created_at(
        session_id=session_id, user_message_created_at=user_message_created_at
    ) is not None:
        log.info("assistant_already_exists_idempotent", user_message_id=str(message_id))
        await clear_chat_turn_pending(session_id=session_id, user_message_id=message_id)
        return

    try:
        await _run_resume_pdf_generation_core(
            job, session_id=session_id, message_id=message_id, user_message=user_message
        )
    except Exception as e:
        log.exception(
            "resume_pdf_generation_failed",
            session_id=str(session_id),
            user_message_id=str(message_id),
        )
        if (
            await first_assistant_after_user_created_at(
                session_id=session_id, user_message_created_at=user_message_created_at
            )
            is None
        ):
            try:
                seq = await next_message_sequence(session_id=session_id)
                detail = f"{type(e).__name__}: {e}"
                if len(detail) > 1200:
                    detail = detail[:1200] + "…"
                err_text = _ERROR_ASSISTANT_PREFIX + detail
                if len(err_text) > 8000:
                    err_text = err_text[:8000] + "…"
                assistant_id = await insert_assistant_message(
                    session_id=session_id,
                    content=err_text,
                    sequence=seq,
                    tool_used="worker.error",
                    pdf_artifact_id=None,
                )
                await publish_chat_reply(
                    user_message_id=message_id,
                    session_id=session_id,
                    assistant_message_id=assistant_id,
                    pdf_artifact_id=None,
                )
            except Exception:
                log.exception(
                    "persist_error_assistant_failed",
                    session_id=str(session_id),
                    user_message_id=str(message_id),
                )
    finally:
        await clear_chat_turn_pending(session_id=session_id, user_message_id=message_id)
