from __future__ import annotations

import uuid

from agents.extensions.memory import SQLAlchemySession
from agents.memory import SessionSettings

from app.db.session import engine
from app.llm.openai_agents_sdk_tables import (
    OPENAI_AGENTS_SDK_MESSAGES_TABLE,
    OPENAI_AGENTS_SDK_SESSIONS_TABLE,
)


def build_sqlalchemy_conversation_session(*, chat_session_id: uuid.UUID) -> SQLAlchemySession:
    """OpenAI Agents SDK session persistence backed by Postgres (async engine)."""
    return SQLAlchemySession(
        str(chat_session_id),
        engine=engine,
        create_tables=False,
        sessions_table=OPENAI_AGENTS_SDK_SESSIONS_TABLE,
        messages_table=OPENAI_AGENTS_SDK_MESSAGES_TABLE,
        session_settings=SessionSettings(limit=4),
    )
