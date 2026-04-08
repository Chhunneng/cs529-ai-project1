from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class JobDescription(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "job_descriptions"

    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
