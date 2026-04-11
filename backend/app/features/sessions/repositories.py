from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select

from app.db.session import AsyncSessionMaker
from app.models.chat_message import ChatMessage


async def get_user_message_in_session(
    *, session_id: uuid.UUID, user_message_id: uuid.UUID
) -> ChatMessage | None:
    """Load a user chat row if it belongs to the session."""
    async with AsyncSessionMaker() as db:
        return await db.scalar(
            select(ChatMessage).where(
                ChatMessage.id == user_message_id,
                ChatMessage.session_id == session_id,
                ChatMessage.role == "user",
            )
        )


async def first_assistant_after_user_created_at(
    *, session_id: uuid.UUID, user_message_created_at: datetime
) -> ChatMessage | None:
    """First assistant message in the session created strictly after the given user message time."""
    async with AsyncSessionMaker() as db:
        return await db.scalar(
            select(ChatMessage)
            .where(
                ChatMessage.session_id == session_id,
                ChatMessage.role == "assistant",
                ChatMessage.created_at > user_message_created_at,
            )
            .order_by(ChatMessage.created_at.asc())
            .limit(1)
        )
