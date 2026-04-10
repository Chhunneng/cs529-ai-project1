"""Resume template persistence helpers (preview compile, etc.)."""

from __future__ import annotations

from app.features.latex.service import compile_latex_to_pdf
from app.schemas.resume_template import ResumeTemplateValidateResponse
from app.features.latex.exceptions import LaTeXCompileFailed


async def validate_template_latex(*, latex_source: str) -> ResumeTemplateValidateResponse:
    """
    Run the same compile path as PDF preview; return ok + parsed errors without storing a template.
    """
    latex_source = latex_source.strip()
    if not latex_source:
        return ResumeTemplateValidateResponse(ok=False, message="LaTeX source is empty.")
    try:
        await compile_latex_to_pdf(latex=latex_source)
    except LaTeXCompileFailed as e:
        d = e.detail
        return ResumeTemplateValidateResponse(
            ok=False,
            message=d.get("message"),
            latex_error=d.get("latex_error"),
            line_number=d.get("line_number"),
            line_context=d.get("line_context"),
            hint=d.get("hint"),
        )
    except RuntimeError as e:
        return ResumeTemplateValidateResponse(ok=False, message=str(e))
    return ResumeTemplateValidateResponse(
        ok=True,
        message="LaTeX compiles successfully with pdflatex.",
    )


async def build_template_preview_pdf(*, latex_source: str) -> bytes:
    """
    Compile LaTeX as-is to PDF bytes (no placeholder filling).

    The source must be valid standalone TeX for pdflatex. Filled-output rendering
    with schema-specific data is handled by the worker.
    """
    if not latex_source:
        raise ValueError("latex_source is empty")
    pdf_bytes, _log = await compile_latex_to_pdf(latex=latex_source)
    return pdf_bytes
