from __future__ import annotations

import uuid

import structlog
from sqlalchemy import func, select

from app.db.session import AsyncSessionMaker
from app.features.latex.service import compile_latex_to_pdf
from app.features.pdf_generation.pdf_artifacts import (
    insert_pdf_artifact_row,
    write_pdf_artifact_file,
)
from app.features.latex.exceptions import LaTeXCompileFailed
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.job_description import JobDescription
from app.llm.conversation_session import build_sqlalchemy_conversation_session
from app.llm.context import ResumeAgentContext
from app.llm.resume_chat_agent import run_resume_pdf_agent
from app.queue_jobs import ResumePdfGenerationJob
from app.features.sessions.chat_reply_redis import publish_chat_reply

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


async def handle_resume_pdf_generation_job(job: ResumePdfGenerationJob) -> None:
    session_id = uuid.UUID(job.session_id)

    log.info("job_received", type=job.type, session_id=str(session_id))

    message_id = uuid.UUID(job.user_message_id)
    user_message = await fetch_user_message_row(message_id=message_id)

    user_text = user_message.content

    async with AsyncSessionMaker() as db:
        session = await db.get(ChatSession, session_id)
        if session is None:
            raise RuntimeError("Session not found")
        resume_id = uuid.UUID(job.resume_id) if job.resume_id is not None else None
        job_description_id = uuid.UUID(job.job_description_id) if job.job_description_id is not None else None
        resume_template_id = uuid.UUID(job.resume_template_id) if job.resume_template_id is not None else None

    # intent = await classify_intent(user_text=user_text)

    # if intent.intent == "job_description":
    #     jd_id = await create_job_description_and_activate(session_id=session_id, raw_text=user_text)
    #     assistant_text = (
    #         "Saved that job description and set it as active for this session. "
    #         f"Job description id: {jd_id}"
    #     )
    #     seq = await next_message_sequence(session_id=session_id)
    #     assistant_id = await insert_assistant_message(
    #         session_id=session_id,
    #         content=assistant_text,
    #         sequence=seq,
    #         tool_used="internal.job_description_ingest",
    #         pdf_artifact_id=None,
    #     )
    #     await publish_chat_reply(
    #         user_message_id=message_id,
    #         session_id=session_id,
    #         assistant_message_id=assistant_id,
    #         pdf_artifact_id=None,
    #     )
    #     return

    # prior_for_scope = await _prior_assistant_snippet(
    #     session_id=session_id,
    #     before_sequence=user_message.sequence,
    # )
    # scope = await check_resume_scope(user_text=user_text, prior_context=prior_for_scope)

    seq = await next_message_sequence(session_id=session_id)

    # if not scope.is_related_to_resume_job:
    #     assistant_text = (
    #         "I'm only set up to help with resumes, job descriptions, and tailoring in this app. "
    #         "Ask something in that area—like updating your resume, reviewing a job posting, "
    #         "or matching your resume to a role."
    #     )
    #     assistant_id = await insert_assistant_message(
    #         session_id=session_id,
    #         content=assistant_text,
    #         sequence=seq,
    #         tool_used="scope_guardrail",
    #         pdf_artifact_id=None,
    #     )
    #     await publish_chat_reply(
    #         user_message_id=message_id,
    #         session_id=session_id,
    #         assistant_message_id=assistant_id,
    #         pdf_artifact_id=None,
    #     )
    #     return

    # if resume_template_id is None:
    #     assistant_text = (
    #         "Link a resume template to this session (or pass template_id with your message) "
    #         "so I can generate a PDF."
    #     )
    #     assistant_id = await insert_assistant_message(
    #         session_id=session_id,
    #         content=assistant_text,
    #         sequence=seq,
    #         tool_used="server.validation",
    #         pdf_artifact_id=None,
    #     )
    #     await publish_chat_reply(
    #         user_message_id=message_id,
    #         session_id=session_id,
    #         assistant_message_id=assistant_id,
    #         pdf_artifact_id=None,
    #     )
    #     return

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

    # log.info("pdf_agent_result", pdf_agent_result=pdf_agent_result)

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
