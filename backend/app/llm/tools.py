from agents import RunContextWrapper
from agents.tool import function_tool

from app.features.latex.exceptions import LaTeXCompileFailed
from app.features.resumes.repositories import load_resume_row
from app.features.resumes.service import (
    build_resume_overview_text,
    resume_excerpt,
    resume_source_text,
    search_resume_text,
)
from app.features.job_descriptions.service import fetch_full_job_description_text, fetch_job_description_excerpt
from app.features.latex.service import compile_latex_to_pdf
from app.llm.context import JobDescriptionAgentContext, ResumeAgentContext, ToolTraceContext
from app.core.config import settings
from app.db.session import AsyncSessionMaker
from app.models import ResumeTemplate


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
async def get_full_resume_text(ctx: RunContextWrapper[ResumeAgentContext]) -> str:
    """Load the full text of the user's linked resume.

    When to call: Use this when you need to understand the full resume text before
    proposing edits, rewrites, or LaTeX. Takes no arguments; the active resume comes from
    the session context.

    What you get: The full resume text.
    """
    resume_id = ctx.context.resume_id
    resume = await load_resume_row(resume_id=resume_id)
    if resume is None:
        return "Selected resume was not found."
    return resume_source_text(resume=resume)


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
async def get_active_job_description(ctx: RunContextWrapper[JobDescriptionAgentContext]) -> str:
    """Load the full active job description text for this session.

    When to call: Use this when you need to understand the full job description before
    suggesting edits, rewrites, or LaTeX. Takes no arguments; the active job description
    comes from the session context.

    What you get: The full job description text.
    """
    job_description_id = ctx.context.job_description_id
    return await fetch_full_job_description_text(job_description_id=job_description_id)


@function_tool(
    is_enabled=lambda ctx, _agent: ctx.context.resume_template_id is not None,
)
async def get_resume_template_latex(ctx: RunContextWrapper[ResumeAgentContext]) -> str:
    """Load the linked template's LaTeX for style and syntax reference—not a script to duplicate.

    When to call: Before building latex_document, so you can reuse preamble, packages, fonts,
    and the same kinds of section/list commands the template uses.

    What you get: The template source. Treat placeholder sections and example headings in the
    template as samples only: replace them with real content from get_full_resume_text /
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
    ctx: RunContextWrapper[ToolTraceContext],
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
