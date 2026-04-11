import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PdfArtifactListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    mime_type: str
    created_at: datetime
