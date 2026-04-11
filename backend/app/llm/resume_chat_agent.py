from __future__ import annotations

from dataclasses import dataclass
from typing import Any


import structlog
from agents import Runner
from agents.extensions.memory import SQLAlchemySession
from agents.items import ToolCallItem
from agents.result import RunResult
from agents.run_error_handlers import (
    RunErrorHandlerInput,
    RunErrorHandlerResult,
    RunErrorHandlers,
)

from app.core.config import settings
from app.llm.context import ResumeAgentContext
from app.llm.agents import RESUME_PDF_AGENT
from app.llm.hooks import ResumePdfAgentToolTraceHooks
from app.llm.schema import ResumePdfMessageOutput

log = structlog.get_logger()


def _usage_from_result(result: RunResult) -> dict[str, Any] | None:
    for resp in reversed(result.raw_responses):
        usage = getattr(resp, "usage", None)
        if usage is not None and hasattr(usage, "model_dump"):
            return usage.model_dump()
    return None


def _tool_names_from_items(result: RunResult) -> list[str]:
    names: list[str] = []
    for item in result.new_items:
        if isinstance(item, ToolCallItem):
            raw = item.raw_item
            n = getattr(raw, "name", None)
            if isinstance(n, str) and n:
                names.append(n)
    return names


async def _max_turns_handler(
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
    log.warning("agent_max_turns", session_id=correlation)
    return RunErrorHandlerResult(
        final_output=ResumePdfMessageOutput(
            assistant_message=(
                "I reached the step limit for this reply. Try a shorter question, "
                "or split it into smaller parts."
            ),
            latex_document=("\\documentclass{article}\\begin{document}\\end{document}\n"),
        ),
        include_in_history=True,
    )


@dataclass(frozen=True)
class ResumePdfAgentRun:
    assistant_message: str
    latex_document: str | None
    usage: dict[str, Any] | None
    tool_calls: list[str]


async def run_resume_pdf_agent(
    *,
    user_text: str,
    tool_context: ResumeAgentContext,
    memory_session: SQLAlchemySession,
) -> ResumePdfAgentRun:
    hooks = ResumePdfAgentToolTraceHooks()
    error_handlers: RunErrorHandlers[ResumeAgentContext] = {"max_turns": _max_turns_handler}

    result = await Runner.run(
        RESUME_PDF_AGENT,
        user_text,
        context=tool_context,
        session=memory_session,
        max_turns=settings.openai.agent_chat_max_turns,
        hooks=hooks,
        error_handlers=error_handlers,
    )
    final = result.final_output
    if isinstance(final, ResumePdfMessageOutput):
        msg = final.assistant_message.strip() or "Done."
        raw_latex = final.latex_document
        latex = raw_latex.strip() if isinstance(raw_latex, str) else None
        latex = latex or None
        tool_calls = tool_context.tool_trace[:] or _tool_names_from_items(result)
        return ResumePdfAgentRun(
            assistant_message=msg,
            latex_document=latex,
            usage=_usage_from_result(result),
            tool_calls=tool_calls,
        )
    return ResumePdfAgentRun(
        assistant_message="Thanks — I've received your message.",
        latex_document=None,
        usage=_usage_from_result(result),
        tool_calls=tool_context.tool_trace[:] or _tool_names_from_items(result),
    )
