import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class AgentSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "agent_sessions"

    selected_resume_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True
    )
    active_jd_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_descriptions.id", ondelete="SET NULL"), nullable=True
    )
    state_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    openai_conversation_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    previous_response_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
