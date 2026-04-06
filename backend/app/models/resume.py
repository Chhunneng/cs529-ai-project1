from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class Resume(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "resumes"

    # Phase 1: no auth/users yet
    openai_file_id: Mapped[str | None] = mapped_column(nullable=True)
    parsed_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

