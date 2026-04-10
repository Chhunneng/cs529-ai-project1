from __future__ import annotations

import json
from typing import Any

import structlog
from agents import Agent, Runner
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.llm.agents_bootstrap import ONESHOT_AGENT_MAX_TURNS, ensure_agents_openai_configured
from app.worker.resume_fill_models import ResumeFillAtsV1

log = structlog.get_logger()

_RESUME_FILL_INSTRUCTIONS = (
    "You fill resume templates with structured data only.\n"
    "Return the final structured object matching the output schema exactly.\n"
    "Use professional, ATS-friendly wording. Do not invent employers, degrees, or dates "
    "contradicting the provided resume context unless the user asked for placeholders."
)


def _resume_fill_agent() -> Agent[Any]:
    return Agent[Any](
        name="ResumeFill",
        instructions=_RESUME_FILL_INSTRUCTIONS,
        model=settings.openai.model,
        output_type=ResumeFillAtsV1,
        tools=[],
    )


def _user_message_for_fill(
    *,
    resume_context: str,
    job_description_context: str | None,
) -> str:
    user_parts: list[str] = [
        "Produce resume content matching the template field structure below.",
        "Use professional, ATS-friendly wording.",
    ]
    if resume_context.strip():
        user_parts.append("--- Existing resume / profile data (may be partial) ---\n" + resume_context)
    if job_description_context and job_description_context.strip():
        user_parts.append("--- Target job description ---\n" + job_description_context)
    user_parts.append(
        "Fill every required section. Use sensible placeholders only when the resume context is empty."
    )
    return "\n\n".join(user_parts)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=1, max=8))
async def generate_resume_fill(
    *,
    resume_context: str,
    job_description_context: str | None,
) -> ResumeFillAtsV1:
    ensure_agents_openai_configured()
    user_message = _user_message_for_fill(
        resume_context=resume_context,
        job_description_context=job_description_context,
    )
    result = await Runner.run(
        _resume_fill_agent(),
        user_message,
        context=None,
        session=None,
        max_turns=ONESHOT_AGENT_MAX_TURNS,
    )
    final = result.final_output
    if isinstance(final, ResumeFillAtsV1):
        return final
    log.error("resume_fill_unexpected_output", output_type=type(final).__name__)
    raise RuntimeError("OpenAI agent returned unexpected output type for resume fill")
