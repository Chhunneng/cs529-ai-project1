from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

import structlog
from agents import Agent, Runner, function_tool
from agents.exceptions import InputGuardrailTripwireTriggered
from agents.extensions.memory import SQLAlchemySession
from agents.items import ToolCallItem
from agents.lifecycle import RunHooksBase
from agents.result import RunResult
from agents.run_config import CallModelData, ModelInputData, RunConfig
from agents.run_context import RunContextWrapper
from agents.tool import Tool
from agents.run_error_handlers import (
    RunErrorHandlerInput,
    RunErrorHandlerResult,
    RunErrorHandlers,
)

from app.core.config import settings
from app.db.session import AsyncSessionMaker
from app.features.job_descriptions.service import fetch_job_description_excerpt
from app.features.resumes.repo import load_resume_row
from app.features.resumes.service import (
    build_resume_overview_text,
    resume_excerpt,
    search_resume_text,
)
from app.models.resume_template import ResumeTemplate
from app.llm.agents_bootstrap import ensure_agents_openai_configured
from app.llm.resume_agent_context import ResumeAgentContext

log = structlog.get_logger()

_OFF_TOPIC_SCOPE_REFUSAL = (
    "I'm only set up to help with resumes, job descriptions, and tailoring in this app. "
    "Ask something in that area—like updating your resume, reviewing a job posting, "
    "or matching your resume to a role."
)


class ResumePdfTurnOutput(BaseModel):
    """Structured final output: user-facing text plus LaTeX source for PDF compilation."""

    assistant_message: str = Field(..., description="Short reply shown in chat.")
    latex_document: str = Field(
        ...,
        description="Full LaTeX source for pdflatex (must be a complete compilable document).",
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


@function_tool(
    is_enabled=lambda ctx, _agent: ctx.context.resume_id is not None,
)
async def get_resume_overview(ctx: RunContextWrapper[ResumeAgentContext]) -> str:
    """Compact overview of the selected resume (parsed structure or start of plain text)."""
    rid = ctx.context.resume_id
    assert rid is not None
    resume = await load_resume_row(resume_id=rid)
    if resume is None:
        return "Selected resume was not found."
    return build_resume_overview_text(
        resume=resume,
        max_chars=settings.openai.agent_resume_overview_max_chars,
    )


@function_tool(
    is_enabled=lambda ctx, _agent: ctx.context.resume_id is not None,
)
async def get_resume_excerpt(
    ctx: RunContextWrapper[ResumeAgentContext],
    start_char: int,
    max_chars: int,
) -> str:
    """Return a slice of the resume source text starting at start_char (0-based), up to max_chars."""
    rid = ctx.context.resume_id
    assert rid is not None
    resume = await load_resume_row(resume_id=rid)
    if resume is None:
        return "Selected resume was not found."
    cap = min(max(1, int(max_chars)), settings.openai.agent_resume_excerpt_max_chars)
    return resume_excerpt(
        resume=resume,
        start_char=int(start_char),
        length=cap,
        max_length=settings.openai.agent_resume_excerpt_max_chars,
    )


@function_tool(
    is_enabled=lambda ctx, _agent: ctx.context.resume_id is not None,
)
async def search_in_resume(
    ctx: RunContextWrapper[ResumeAgentContext],
    needle: str,
    max_matches: int = 5,
) -> str:
    """Search the resume source for needle (case-insensitive); returns short snippets with context."""
    rid = ctx.context.resume_id
    assert rid is not None
    resume = await load_resume_row(resume_id=rid)
    if resume is None:
        return "Selected resume was not found."
    mm = max(1, min(int(max_matches), 12))
    return search_resume_text(
        resume=resume,
        needle=needle,
        max_matches=mm,
        context_chars=120,
        max_scan_chars=settings.openai.agent_resume_search_max_scan_chars,
    )


@function_tool(
    is_enabled=lambda ctx, _agent: ctx.context.job_description_id is not None,
)
async def get_active_job_description(ctx: RunContextWrapper[ResumeAgentContext]) -> str:
    """Full active job description text for this session (may be truncated for length)."""
    jid = ctx.context.job_description_id
    assert jid is not None
    text = await fetch_job_description_excerpt(
        jd_id=jid,
        max_chars=settings.openai.agent_jd_tool_max_chars,
    )
    if text is None:
        return "Active job description was not found."
    return text


@function_tool(
    is_enabled=lambda ctx, _agent: ctx.context.resume_template_id is not None,
)
async def get_resume_template_latex(ctx: RunContextWrapper[ResumeAgentContext]) -> str:
    """LaTeX source for the active resume template linked to this run."""
    tid = ctx.context.resume_template_id
    assert tid is not None
    async with AsyncSessionMaker() as db:
        row = await db.get(ResumeTemplate, tid)
    if row is None:
        return "Resume template was not found."
    return row.latex_source


_RESUME_AGENT_INSTRUCTIONS = (
    "You are a resume assistant that produces an updated resume as a PDF each turn.\n"
    "Stay in scope: resumes, job descriptions, tailoring, gaps, ATS-style tips, and interview prep "
    "that fits this workspace. Politely decline unrelated requests.\n"
    "Do not invent employers, dates, skills, or JD requirements. Use the read tools when resume or "
    "job description text is needed. Call get_resume_template_latex when a template is linked.\n"
    "Your final output must be structured with two fields: assistant_message (short chat reply) and "
    "latex_document (a complete LaTeX file that pdflatex can compile—include \\documentclass and "
    "\\begin{document}...\\end{document}). Base the document on the template LaTeX when available.\n"
    "If you cannot produce safe LaTeX, explain briefly in assistant_message and still return minimal "
    "valid LaTeX (e.g. a one-page article with the explanation)."
)


async def _inject_workspace_instructions(
    data: CallModelData[ResumeAgentContext],
) -> ModelInputData:
    model_data = data.model_data
    ctx = data.context
    if ctx is None:
        return model_data
    rid = str(ctx.resume_id) if ctx.resume_id else "none"
    jid = str(ctx.job_description_id) if ctx.job_description_id else "none"
    tid = str(ctx.resume_template_id) if ctx.resume_template_id else "none"
    block = (
        "\n\n--- Server workspace (authoritative for this model call) ---\n"
        f"chat_session_id={ctx.chat_session_id}\n"
        f"resume_id={rid}\n"
        f"job_description_id={jid}\n"
        f"resume_template_id={tid}\n"
        "These values are from the server. Do not fabricate or swap them.\n"
        "Use tools to fetch resume, job description, or template content when needed."
    )
    base = model_data.instructions or ""
    return ModelInputData(input=list(model_data.input), instructions=base + block)


def _resume_chat_run_config() -> RunConfig:
    return RunConfig(
        call_model_input_filter=_inject_workspace_instructions,
        input_guardrails=[],
    )


def resume_pdf_agent() -> Agent[ResumeAgentContext]:
    return Agent[ResumeAgentContext](
        name="ResumePdfAssistant",
        instructions=_RESUME_AGENT_INSTRUCTIONS,
        model=settings.openai.model,
        output_type=ResumePdfTurnOutput,
        tools=[
            get_resume_overview,
            get_resume_excerpt,
            search_in_resume,
            get_active_job_description,
            get_resume_template_latex,
        ],
    )


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
        final_output=ResumePdfTurnOutput(
            assistant_message=(
                "I reached the step limit for this reply. Try a shorter question, "
                "or split it into smaller parts."
            ),
            latex_document=(
                "\\documentclass{article}\\begin{document}\\end{document}\n"
            ),
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
    ensure_agents_openai_configured()
    hooks = _ToolTraceHooks()
    error_handlers: RunErrorHandlers[ResumeAgentContext] = {"max_turns": _max_turns_handler}
    try:
        result = await Runner.run(
            resume_pdf_agent(),
            user_text,
            context=tool_context,
            session=memory_session,
            max_turns=settings.openai.agent_chat_max_turns,
            hooks=hooks,
            run_config=_resume_chat_run_config(),
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
    if isinstance(final, ResumePdfTurnOutput):
        msg = final.assistant_message.strip() or "Done."
        latex = final.latex_document.strip() or None
        tool_calls = tool_context.tool_trace[:] or _tool_names_from_items(result)
        return ResumePdfAgentRun(
            assistant_message=msg,
            latex_document=latex,
            usage=_usage_from_result(result),
            tool_calls=tool_calls,
        )
    if isinstance(final, str):
        text = final.strip() or "Thanks — I've received your message."
        return ResumePdfAgentRun(
            assistant_message=text,
            latex_document=None,
            usage=_usage_from_result(result),
            tool_calls=tool_context.tool_trace[:] or _tool_names_from_items(result),
        )
    return ResumePdfAgentRun(
        assistant_message="Thanks — I've received your message.",
        latex_document=None,
        usage=_usage_from_result(result),
        tool_calls=tool_context.tool_trace[:] or _tool_names_from_items(result),
    )
