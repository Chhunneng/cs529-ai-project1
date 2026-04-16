import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base
from app.models.common import UUID_TYPE, UUIDPrimaryKeyMixin


class PdfArtifact(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "pdf_artifacts"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    storage_relpath: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    sha256_hex: Mapped[str] = mapped_column(Text, nullable=False)
