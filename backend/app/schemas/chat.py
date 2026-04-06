import uuid
from datetime import datetime

from pydantic import BaseModel


class ChatMessageCreateRequest(BaseModel):
    session_id: uuid.UUID
    message: str


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    message: str
    created_at: datetime

