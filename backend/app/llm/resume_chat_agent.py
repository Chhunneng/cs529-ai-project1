from __future__ import annotations

from dataclasses import dataclass
from typing import Any


import structlog
from agents import Agent, Runner
from agents.exceptions import InputGuardrailTripwireTriggered
from agents.extensions.memory import SQLAlchemySession
from agents.items import ToolCallItem
from agents.lifecycle import RunHooksBase
from agents.result import RunResult
from agents.run_context import RunContextWrapper
from agents.tool import Tool
from agents.run_error_handlers import (
    RunErrorHandlerInput,
    RunErrorHandlerResult,
    RunErrorHandlers,
)

from app.core.config import settings
from app.llm.context import ResumeAgentContext
from backend.app.llm.agents import RESUME_PDF_AGENT
from backend.app.llm.schema import ResumePdfMessageOutput

log = structlog.get_logger()

_OFF_TOPIC_SCOPE_REFUSAL = (
    "I'm only set up to help with resumes, job descriptions, and tailoring in this app. "
    "Ask something in that area—like updating your resume, reviewing a job posting, "
    "or matching your resume to a role."
)


class _ToolTraceHooks(RunHooksBase[ResumeAgentContext, Agent[ResumeAgentContext]]):
    async def on_tool_end(
        self,
        context: RunContextWrapper[ResumeAgentContext],
        agent: Agent[ResumeAgentContext],
        tool: Tool,
        result: str,
    ) -> None:
        name = getattr(tool, "name", None) or type(tool).__name__
        context.context.tool_trace.append(str(name))
        log.info(
            "chat_agent_tool",
            tool=str(name),
            session_id=str(context.context.chat_session_id),
        )





# async def _inject_workspace_instructions(
#     data: CallModelData[ResumeAgentContext],
# ) -> ModelInputData:
#     model_data = data.model_data
#     ctx = data.context
#     if ctx is None:
#         return model_data
#     rid = str(ctx.resume_id) if ctx.resume_id else "none"
#     jid = str(ctx.job_description_id) if ctx.job_description_id else "none"
#     tid = str(ctx.resume_template_id) if ctx.resume_template_id else "none"
#     block = (
#         "\n\n--- Server workspace (authoritative for this model call) ---\n"
#         f"chat_session_id={ctx.chat_session_id}\n"
#         f"resume_id={rid}\n"
#         f"job_description_id={jid}\n"
#         f"resume_template_id={tid}\n"
#         "These values are from the server. Do not fabricate or swap them.\n"
#         "Use tools to fetch resume, job description, or template content when needed."
#     )
#     base = model_data.instructions or ""
#     return ModelInputData(input=list(model_data.input), instructions=base + block)


# def _resume_chat_run_config() -> RunConfig:
#     return RunConfig(
#         call_model_input_filter=_inject_workspace_instructions,
#         input_guardrails=[],
#     )


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
    log.warning("agent_max_turns", session_id=str(inp.context.context.chat_session_id))
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


def _reply_from_scope_tripwire(exc: InputGuardrailTripwireTriggered) -> str:
    out = exc.guardrail_result.output
    info = out.output_info
    if isinstance(info, dict):
        sr = info.get("suggested_reply")
        if isinstance(sr, str) and sr.strip():
            return sr.strip()
    return _OFF_TOPIC_SCOPE_REFUSAL


async def run_resume_pdf_agent(
    *,
    user_text: str,
    tool_context: ResumeAgentContext,
    memory_session: SQLAlchemySession,
) -> ResumePdfAgentRun:
    hooks = _ToolTraceHooks()
    error_handlers: RunErrorHandlers[ResumeAgentContext] = {"max_turns": _max_turns_handler}
    try:
        result = await Runner.run(
            RESUME_PDF_AGENT,
            user_text,
            context=tool_context,
            session=memory_session,
            max_turns=settings.openai.agent_chat_max_turns,
            hooks=hooks,
            # run_config=_resume_chat_run_config(),
            error_handlers=error_handlers,
        )
    except InputGuardrailTripwireTriggered as e:
        log.info(
            "resume_chat_scope_guardrail",
            session_id=str(tool_context.chat_session_id),
            reason=(
                e.guardrail_result.output.output_info.get("reason")
                if isinstance(e.guardrail_result.output.output_info, dict)
                else None
            ),
        )
        return ResumePdfAgentRun(
            assistant_message=_reply_from_scope_tripwire(e),
            latex_document=None,
            usage=None,
            tool_calls=[],
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
