"""Trim OpenAI Agents SDK SQLAlchemy session rows when app chat messages are deleted."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import text

from app.db.session import engine
from app.llm.openai_agents_sdk_tables import OPENAI_AGENTS_SDK_MESSAGES_TABLE


async def delete_agents_sdk_messages_from_cutoff(
    *,
    chat_session_id: uuid.UUID,
    cutoff_utc: datetime,
) -> None:
    """
    Remove persisted SDK items at or after ``cutoff_utc``.

    ``chat_messages.created_at`` is timestamptz; the SDK table uses naive timestamps — we compare
    using the same UTC instant as naive UTC wall time.
    """
    sid = str(chat_session_id)
    if cutoff_utc.tzinfo is not None:
        cutoff_naive = cutoff_utc.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        cutoff_naive = cutoff_utc

    stmt = text(
        f"DELETE FROM {OPENAI_AGENTS_SDK_MESSAGES_TABLE} "
        "WHERE session_id = :session_id AND created_at >= :cutoff"
    )
    async with engine.begin() as conn:
        await conn.execute(stmt, {"session_id": sid, "cutoff": cutoff_naive})
