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
from app.features.latex.service import compile_latex_to_pdf
from app.services.latex_compile import LaTeXCompileFailed

log = structlog.get_logger()

_OFF_TOPIC_SCOPE_REFUSAL = (
    "I'm only set up to help with resumes, job descriptions, and tailoring in this app. "
    "Ask something in that area—like updating your resume, reviewing a job posting, "
    "or matching your resume to a role."
)


class ResumePdfMessageOutput(BaseModel):
    """Structured final output: user-facing text plus LaTeX source for PDF compilation."""

    assistant_message: str = Field(..., description="Short reply shown in chat.")
    latex_document: str | None = Field(
        default=None,
        description=(
            "When the user asked for a PDF, an updated typeset resume, or similar output, "
            "set this to a complete LaTeX document pdflatex can compile. "
            "Use the linked template for style and syntax (preamble, packages, fonts, section "
            "macros)—not as a fixed layout to copy verbatim; the body must contain real resume "
            "content from tools, with sections and bullets you add or change as needed. "
            "When the user only wanted advice, Q&A, or edits without generating a document, "
            "set this field to null."
        ),
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
    """Load a short, bounded snapshot of the user's linked resume.

    When to call: Use first whenever you need to understand what is on the resume before
    proposing edits, rewrites, or LaTeX. Takes no arguments; the active resume comes from
    the session context.

    What you get: If parsing succeeded, a structured outline (summary, outline lines,
    contact fields) clipped to a max length. If not parsed yet, the start of the raw
    resume text. The result is always truncated and is not the full document.
    """
    resume_id = ctx.context.resume_id
    resume = await load_resume_row(resume_id=resume_id)
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
    """Read a specific character range of the resume source text.

    When to call: Use this when you need to read a specific part of the resume—like a
    specific job description or a particular section. Takes two arguments: start_char
    (0-based character position) and max_chars (how many characters to read).

    What you get: A substring of the resume text starting at start_char and up to max_chars.
    The result is always truncated; it is not the full document.
    """
    resume_id = ctx.context.resume_id
    resume = await load_resume_row(resume_id=resume_id)
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
    """Search the resume source for a specific phrase or keyword.

    When to call: Use this when you need to find a specific phrase or keyword in the resume.
    Takes two arguments: needle (the phrase or keyword to search for) and max_matches
    (how many matches to return).

    What you get: A list of short snippets from the resume text that contain the needle.
    The result is always truncated; it is not the full document.
    """
    resume_id = ctx.context.resume_id
    resume = await load_resume_row(resume_id=resume_id)
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
    """Load the full active job description text for this session.

    When to call: Use this when you need to understand the full job description before
    suggesting edits, rewrites, or LaTeX. Takes no arguments; the active job description
    comes from the session context.

    What you get: The full job description text. The result is always truncated; it is not the full document.
    """
    job_description_id = ctx.context.job_description_id
    text = await fetch_job_description_excerpt(
        job_description_id=job_description_id,
        max_chars=settings.openai.agent_jd_tool_max_chars,
    )
    return text


@function_tool(
    is_enabled=lambda ctx, _agent: ctx.context.resume_template_id is not None,
)
async def get_resume_template_latex(ctx: RunContextWrapper[ResumeAgentContext]) -> str:
    """Load the linked template's LaTeX for style and syntax reference—not a script to duplicate.

    When to call: Before building latex_document, so you can reuse preamble, packages, fonts,
    and the same kinds of section/list commands the template uses.

    What you get: The template source. Treat placeholder sections and example headings in the
    template as samples only: replace them with real content from get_resume_overview /
    get_resume_excerpt / search_in_resume. You may add headers, bullet key points, extra
    sections, or reorder content for the user and job; do not ship a PDF that only echoes the
    template shell with empty or generic blocks.
    """
    template_id = ctx.context.resume_template_id
    async with AsyncSessionMaker() as db:
        row = await db.get(ResumeTemplate, template_id)
    if row is None:
        return "Resume template was not found."
    return row.latex_source


@function_tool()
async def check_latex_compiles_on_server(
    ctx: RunContextWrapper[ResumeAgentContext],
    latex_source: str,
) -> str:
    """Try compiling LaTeX with the same server pipeline used for resume PDFs.

    When to call: After you draft a full document (or a large fragment), before returning
    latex_document in your final output—especially if you are unsure about syntax, packages,
    or escaping. Pass the exact string you intend to ship.

    What you get: A short text result. If compilation succeeds, it confirms pdflatex produced
    a PDF on this host (same path as compile_latex_to_pdf / PDF jobs). If it fails, you get
    the same style of error detail the worker would surface (message, line number, hint when
    available) so you can fix the source.

    Note: This runs a real compile; avoid calling it repeatedly with huge unrelated strings.
    """
    _ = ctx  # session available for hooks / tracing only
    text = latex_source.strip() if isinstance(latex_source, str) else ""
    if not text:
        return "Cannot compile: latex_source is empty."

    try:
        await compile_latex_to_pdf(latex=text)
    except LaTeXCompileFailed as e:
        detail = e.detail
        msg = detail.get("message") or str(e)
        parts = [f"Compilation failed on server: {msg}"]
        if detail.get("line_number") is not None:
            parts.append(f"line {detail['line_number']}")
        if detail.get("hint"):
            parts.append(str(detail["hint"]))
        return " ".join(parts)

    return (
        "OK: This LaTeX compiles successfully on the server using pdflatex "
        "(same pipeline as resume PDF generation)."
    )

_RESUME_AGENT_INSTRUCTIONS = (
    "You are a resume assistant. You may answer questions, give advice, and help tailor content "
    "to the linked resume and job description.\n"
    "Stay in scope: resumes, job descriptions, tailoring, gaps, ATS-style tips, and interview prep "
    "that fits this workspace. Politely decline unrelated requests.\n"
    "Do not invent employers, dates, skills, or JD requirements. Use the read tools when resume or "
    "job description text is needed. Call get_resume_template_latex when a template is linked. "
    "You may call check_latex_compiles_on_server on a draft to verify pdflatex can compile it here "
    "before you return latex_document.\n"
    "Template vs content: The linked template is for visual style and LaTeX syntax only—preamble "
    "(\\documentclass, \\usepackage), fonts, colors, and the kinds of macros/commands used for "
    "sections and lists. Do not treat the template as a fixed outline to copy. Replace any "
    "placeholder or example sections with real material from the resume tools. You may add section "
    "headings, bullet key points, summaries, or extra blocks; rename, merge, or drop template "
    "sections when it serves the user and the job. A bad outcome is a PDF that only repeats the "
    "template header or shell with little or no substantive resume content.\n"
    "Your final output uses two fields: assistant_message (the reply shown in chat) and "
    "latex_document.\n"
    "Set latex_document to null when the user did not ask you to generate a PDF, produce an updated "
    "typeset resume, or otherwise output a document for compilation—e.g. pure Q&A, brainstorming, "
    "or bullet suggestions with no build request.\n"
    "When the user clearly wants a PDF or updated resume document, set latex_document to a complete "
    "LaTeX file pdflatex can compile (\\documentclass through \\end{document}). Reuse the "
    "template's preamble and styling patterns when a template exists; build the document body from "
    "fetched resume (and JD) content, not from empty template placeholders.\n"
    "If they asked for a document but you cannot produce safe LaTeX, explain in assistant_message "
    "and either return null for latex_document or minimal valid LaTeX that states the issue."
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


def resume_pdf_agent() -> Agent[ResumeAgentContext]:
    return Agent[ResumeAgentContext](
        name="ResumePdfAssistant",
        instructions=_RESUME_AGENT_INSTRUCTIONS,
        model=settings.openai.model,
        output_type=ResumePdfMessageOutput,
        tools=[
            get_resume_overview,
            get_resume_excerpt,
            search_in_resume,
            get_active_job_description,
            get_resume_template_latex,
            check_latex_compiles_on_server,
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
        final_output=ResumePdfMessageOutput(
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
