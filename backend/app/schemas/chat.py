import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PendingRepliesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pending_user_message_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="User message IDs whose assistant reply is still queued or running.",
    )


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    sequence: int
    created_at: datetime
    pdf_artifact_id: uuid.UUID | None = None
    pdf_download_url: str | None = Field(
        default=None,
        description="Relative URL to download the PDF when pdf_artifact_id is set.",
    )
