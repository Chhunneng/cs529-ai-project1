import uuid

from sqlalchemy import ForeignKey, Integer, Text, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import UUID_TYPE, UUIDPrimaryKeyMixin, TimestampMixin


class ChatMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    tool_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_response_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pdf_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("pdf_artifacts.id", ondelete="SET NULL"), nullable=True
    )
