from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import UUIDPrimaryKeyMixin, TimestampMixin


class ResumeTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "resume_templates"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    latex_source: Mapped[str] = mapped_column(Text, nullable=False)
    schema_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
