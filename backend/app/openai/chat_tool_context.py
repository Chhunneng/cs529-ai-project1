from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class ChatToolContext:
    """Passed to the Agents SDK Runner; tools read session ids from here."""

    session_id: uuid.UUID
    selected_resume_id: uuid.UUID | None
    active_jd_id: uuid.UUID | None
    tool_trace: list[str] = field(default_factory=list)
