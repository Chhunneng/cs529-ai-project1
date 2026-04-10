from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog
from agents import Agent, Runner
from pydantic import BaseModel, ConfigDict, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.llm.agents_bootstrap import ONESHOT_AGENT_MAX_TURNS, ensure_agents_openai_configured

log = structlog.get_logger()


@dataclass(frozen=True)
class ResumeScopeResult:
    is_related_to_resume_job: bool
    reason: str


class ResumeScopeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_related_to_resume_job: bool = Field(
        ...,
        description="True if the message is in scope for resume/JD assistant.",
    )
    reason: str = Field(..., description="Short justification.")


_SCOPE_INSTRUCTIONS = (
    "You are a scope checker for a resume and job-description assistant.\n"
    "Return is_related_to_resume_job=true for: editing a resume (including name/contact/header), "
    "job descriptions, tailoring, ATS tips, interview prep tied to a job, and short follow-ups "
    "that continue those tasks.\n"
    "Return false for unrelated chit-chat, unrelated coding/homework, or anything not about "
    "resume/JD/career documents.\n"
    "When uncertain, prefer true if the message could reasonably be a continuation of resume work."
)


def _resume_scope_agent() -> Agent[Any]:
    return Agent[Any](
        name="ResumeScope",
        instructions=_SCOPE_INSTRUCTIONS,
        model=settings.openai.model,
        output_type=ResumeScopeOutput,
        tools=[],
    )


def _user_message_for_scope(*, user_text: str, prior_context: str | None) -> str:
    parts = []
    if prior_context and prior_context.strip():
        parts.append(
            "--- Prior assistant reply in this chat (for context only; classify the user message below) ---\n"
            + prior_context.strip()[:2000]
        )
    parts.append(f"User message:\n{user_text}")
    return "\n\n".join(parts)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=1, max=8))
async def check_resume_scope(
    *,
    user_text: str,
    prior_context: str | None = None,
) -> ResumeScopeResult:
    """
    Classify whether the user message is in scope.

    ``prior_context`` replaces OpenAI ``previous_response_id`` chaining: pass a short snippet
    of the last assistant message (or similar) so the model can see conversational context.
    """
    ensure_agents_openai_configured()
    user_message = _user_message_for_scope(user_text=user_text, prior_context=prior_context)
    result = await Runner.run(
        _resume_scope_agent(),
        user_message,
        context=None,
        session=None,
        max_turns=ONESHOT_AGENT_MAX_TURNS,
    )
    final = result.final_output
    if isinstance(final, ResumeScopeOutput):
        return ResumeScopeResult(
            is_related_to_resume_job=final.is_related_to_resume_job,
            reason=final.reason,
        )
    log.warning("resume_scope_unexpected_output", output_type=type(final).__name__)
    return ResumeScopeResult(
        is_related_to_resume_job=True,
        reason="unexpected_model_output_default_allow",
    )
