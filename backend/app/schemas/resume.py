import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field


class ResumeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    original_filename: str | None = None
    mime_type: str | None = None
    byte_size: int | None = None
    storage_relpath: str | None = Field(default=None, exclude=True)
    parsed_json: dict[str, Any] | None = None

    @computed_field
    @property
    def has_file(self) -> bool:
        return bool(self.storage_relpath)

    @computed_field
    @property
    def parse_pending(self) -> bool:
        return bool(self.storage_relpath) and self.parsed_json is None


class ResumeUploadResponse(ResumeListItem):
    pass
