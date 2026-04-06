import hashlib
import uuid
from datetime import datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage
from app.schemas.chat import ChatMessageResponse
from app.services.queue import enqueue_job

log = structlog.get_logger()


async def list_messages_for_session(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    limit: int,
    before: datetime | None,
) -> list[ChatMessage]:
    q = select(ChatMessage).where(ChatMessage.session_id == session_id)
    if before is not None:
        q = q.where(ChatMessage.created_at < before)
    q = q.order_by(ChatMessage.created_at.desc()).limit(limit)
    result = await db.execute(q)
    rows = list(result.scalars().all())
    rows.reverse()
    return rows


async def create_user_message_and_enqueue(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    content: str,
) -> ChatMessageResponse:
    msg = ChatMessage(session_id=session_id, role="user", message=content)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    input_hash = hashlib.sha256(f"{msg.session_id}:{msg.message}".encode("utf-8")).hexdigest()
    await enqueue_job(
        {
            "type": "chat_message",
            "session_id": str(msg.session_id),
            "message_id": str(msg.id),
            "input_hash": input_hash,
        }
    )
    log.info(
        "enqueued_job",
        type="chat_message",
        session_id=str(msg.session_id),
        message_id=str(msg.id),
    )

    return ChatMessageResponse(
        id=msg.id,
        session_id=msg.session_id,
        role=msg.role,
        message=msg.message,
        created_at=msg.created_at,
    )
