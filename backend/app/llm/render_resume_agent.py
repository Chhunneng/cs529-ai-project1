"""Batch LaTeX generation for the resume PDF worker (no chat memory)."""

from __future__ import annotations

from agents import Runner
from agents.run_error_handlers import (
    RunErrorHandlerInput,
    RunErrorHandlerResult,
    RunErrorHandlers,
)

import structlog

from app.core.config import settings
from app.llm.agents import RENDER_RESUME_AUTOMATION_AGENT
from app.llm.agents_bootstrap import ensure_agents_openai_configured
from app.llm.context import ResumeAgentContext
from app.llm.hooks import ResumePdfAgentToolTraceHooks
from app.llm.schema import LatexResumeSampleOutput

log = structlog.get_logger()


async def _max_turns_handler_render(
    inp: RunErrorHandlerInput[ResumeAgentContext],
) -> RunErrorHandlerResult:
    correlation = (
        str(inp.context.context.chat_session_id)
        if inp.context.context.chat_session_id is not None
        else (
            str(inp.context.context.render_output_id)
            if inp.context.context.render_output_id is not None
            else "unknown"
        )
    )
    log.warning("render_agent_max_turns", session_id=correlation)
    return RunErrorHandlerResult(
        final_output=LatexResumeSampleOutput(
            latex_resume_content=(
                "\\documentclass{article}\\begin{document}"
                "Step limit reached; document incomplete.\\end{document}\n"
            ),
        ),
        include_in_history=False,
    )


async def run_render_resume_automation(
    *,
    user_prompt: str,
    tool_context: ResumeAgentContext,
) -> LatexResumeSampleOutput:
    """Run the render automation agent (tools + structured LaTeX output, no session memory)."""
    # ensure_agents_openai_configured()
    hooks = ResumePdfAgentToolTraceHooks()
    error_handlers: RunErrorHandlers[ResumeAgentContext] = {"max_turns": _max_turns_handler_render}

    result = await Runner.run(
        RENDER_RESUME_AUTOMATION_AGENT,
        user_prompt,
        context=tool_context,
        session=None,
        max_turns=settings.openai.agent_render_max_turns,
        hooks=hooks,
        error_handlers=error_handlers,
    )
    final = result.final_output
    if isinstance(final, LatexResumeSampleOutput):
        return final
    log.error("render_resume_unexpected_output", output_type=type(final).__name__)
    raise RuntimeError("Render automation agent returned unexpected output type")
