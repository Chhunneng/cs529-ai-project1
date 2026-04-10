from __future__ import annotations

import asyncio

import structlog

from app.services.latex_compile import (
    LaTeXCompileFailed,
    LatexCompileError,
    compile_failure_detail,
    compile_latex_to_pdf_bytes,
)

log = structlog.get_logger()


async def compile_latex_to_pdf(*, latex: str) -> tuple[bytes, str]:
    """
    Run pdflatex on the TeX document.

    Uses in-process compilation so workers and API do not need to resolve `backend`
    over HTTP (avoids DNS errors in Docker when `LATEX_SERVICE_URL` is wrong).

    Applies the same LLM-artifact fixes as template generation (e.g. doubled backslash
    before ``documentclass``) so stored or pasted sources compile reliably on the server.
    """
    try:
        return await asyncio.to_thread(compile_latex_to_pdf_bytes, latex)
    except LatexCompileError as e:
        detail = compile_failure_detail(e.log or "")
        log.warning(
            "latex_compile_failed",
            message=detail.get("message"),
            latex_error=detail.get("latex_error"),
            line_number=detail.get("line_number"),
            hint=detail.get("hint"),
        )
        raise LaTeXCompileFailed(detail) from e
