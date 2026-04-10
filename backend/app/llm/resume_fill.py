from __future__ import annotations


import structlog
from agents import Runner
from tenacity import retry, stop_after_attempt, wait_exponential

from app.llm.agents_bootstrap import ONE_SHOT_AGENT_MAX_TURNS
from app.llm.schema import ResumeFillAtsV1
from app.llm.agents import RESUME_FILL_AGENT

log = structlog.get_logger()


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
        user_parts.append(
            "--- Existing resume / profile data (may be partial) ---\n" + resume_context
        )
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
    user_message = _user_message_for_fill(
        resume_context=resume_context,
        job_description_context=job_description_context,
    )
    result = await Runner.run(
        RESUME_FILL_AGENT,
        user_message,
        context=None,
        session=None,
        max_turns=ONE_SHOT_AGENT_MAX_TURNS,
    )
    final = result.final_output
    if isinstance(final, ResumeFillAtsV1):
        return final
    log.error("resume_fill_unexpected_output", output_type=type(final).__name__)
    raise RuntimeError("OpenAI agent returned unexpected output type for resume fill")
