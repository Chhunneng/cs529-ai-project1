import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import JSON_TYPE, UUID_TYPE, TimestampMixin, UUIDPrimaryKeyMixin


class ChatSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "chat_sessions"

    resume_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True
    )
    job_description_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("job_descriptions.id", ondelete="SET NULL"), nullable=True
    )
    resume_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("resume_templates.id", ondelete="SET NULL"), nullable=True
    )
    state_json: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    previous_response_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
