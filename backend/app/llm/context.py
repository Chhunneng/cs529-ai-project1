from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class ResumeAgentContext:
    """Domain context passed to the Agents SDK ``Runner`` and tools (readable field names)."""

    chat_session_id: uuid.UUID
    resume_id: uuid.UUID
    job_description_id: uuid.UUID
    resume_template_id: uuid.UUID
    tool_trace: list[str] = field(default_factory=list)
