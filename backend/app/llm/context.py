from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(kw_only=True)
class ToolTraceContext:
    """Tool trace passed to the Agents SDK ``Runner`` and tools (readable field names)."""

    tool_trace: list[str] = field(default_factory=list)


@dataclass(kw_only=True)
class JobDescriptionAgentContext:
    """Domain context passed to the Agents SDK ``Runner`` and tools (readable field names)."""

    job_description_id: uuid.UUID | None = None


@dataclass(kw_only=True)
class ResumeAgentContext(ToolTraceContext, JobDescriptionAgentContext):
    """Domain context passed to the Agents SDK ``Runner`` and tools (readable field names)."""

    chat_session_id: uuid.UUID | None = None
    render_output_id: uuid.UUID | None = None
    resume_id: uuid.UUID | None = None
    resume_template_id: uuid.UUID
