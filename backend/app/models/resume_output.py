import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import JSON_TYPE, UUID_TYPE, UUIDPrimaryKeyMixin, TimestampMixin


class ResumeOutput(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "resume_outputs"

    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=True
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("resume_templates.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)  # queued|running|succeeded|failed
    input_json: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    tex_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
