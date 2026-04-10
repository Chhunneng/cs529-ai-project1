import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

import structlog

from app.core.config import settings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage
from app.models.pdf_artifact import PdfArtifact
from app.queue_jobs import ResumePdfGenerationJob
from app.schemas.chat import ChatMessageResponse
from app.services.agents_sdk_trim import delete_agents_sdk_messages_from_cutoff
from app.services.queue import enqueue_job

log = structlog.get_logger()


def chat_message_to_response(row: ChatMessage) -> ChatMessageResponse:
    pdf_download_url = None
    if row.pdf_artifact_id is not None:
        pdf_download_url = (
            f"/api/v1/sessions/{row.session_id}/pdf-artifacts/"
            f"{row.pdf_artifact_id}/file"
        )
    return ChatMessageResponse(
        id=row.id,
        session_id=row.session_id,
        role=row.role,
        content=row.content,
        sequence=row.sequence,
        created_at=row.created_at,
        pdf_artifact_id=row.pdf_artifact_id,
        pdf_download_url=pdf_download_url,
    )


async def list_messages_for_session(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    limit: int,
    before: datetime | None,
) -> List[ChatMessageResponse]:
    q = select(ChatMessage).where(ChatMessage.session_id == session_id)
    if before is not None:
        q = q.where(ChatMessage.created_at < before)
    q = q.order_by(ChatMessage.sequence.asc(), ChatMessage.created_at.asc()).limit(limit)
    result = await db.execute(q)
    rows = list(result.scalars().all())
    return [chat_message_to_response(m) for m in rows]


async def next_message_sequence_db(db: AsyncSession, *, session_id: uuid.UUID) -> int:
    from sqlalchemy import func

    current = await db.scalar(
        select(func.coalesce(func.max(ChatMessage.sequence), 0)).where(
            ChatMessage.session_id == session_id
        )
    )
    return int(current or 0) + 1


async def create_session_turn_and_enqueue(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    content: str,
    resume_template_id: uuid.UUID | None = None,
    resume_id: uuid.UUID | None = None,
    job_description_id: uuid.UUID | None = None,
) -> ChatMessageResponse:
    sequence = await next_message_sequence_db(db, session_id=session_id)
    msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=content,
        sequence=sequence,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    input_hash = hashlib.sha256(f"{msg.session_id}:{msg.content}".encode("utf-8")).hexdigest()
    await enqueue_job(
        ResumePdfGenerationJob(
            session_id=str(msg.session_id),
            user_message_id=str(msg.id),
            input_hash=input_hash,
            resume_template_id=str(resume_template_id) if resume_template_id else None,
            resume_id=str(resume_id) if resume_id else None,
            job_description_id=str(job_description_id) if job_description_id else None,
        )
    )
    log.info(
        "enqueued_job",
        type="resume_pdf_generation",
        session_id=str(msg.session_id),
        message_id=str(msg.id),
    )

    return chat_message_to_response(msg)


def _unlink_pdf_file_if_safe(*, storage_relpath: str) -> None:
    root = Path(settings.storage.artifacts_dir).resolve()
    try:
        path = (root / storage_relpath).resolve()
        path.relative_to(root)
    except (ValueError, OSError):
        return
    if path.is_file():
        try:
            path.unlink()
        except OSError:
            pass


async def delete_chat_message_for_session(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    message_id: uuid.UUID,
) -> bool:
    row = await db.scalar(
        select(ChatMessage).where(
            ChatMessage.id == message_id,
            ChatMessage.session_id == session_id,
        )
    )
    if row is None:
        return False

    cutoff = row.created_at
    pdf_id = row.pdf_artifact_id

    if pdf_id is not None:
        art = await db.get(PdfArtifact, pdf_id)
        if art is not None and art.session_id == session_id:
            _unlink_pdf_file_if_safe(storage_relpath=art.storage_relpath)
            await db.delete(art)

    await db.delete(row)
    await db.commit()

    await delete_agents_sdk_messages_from_cutoff(chat_session_id=session_id, cutoff_utc=cutoff)
    return True
