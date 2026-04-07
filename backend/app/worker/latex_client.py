from __future__ import annotations

import asyncio

import structlog

from app.services.latex_compile import LatexCompileError, compile_tex_to_pdf_bytes

log = structlog.get_logger()


async def compile_tex_to_pdf(*, tex: str) -> tuple[bytes, str]:
    """
    Run pdflatex on the TeX document (same implementation as /api/v1/internal/compile).

    Uses in-process compilation so workers and API do not need to resolve ``backend``
    over HTTP (avoids DNS errors in Docker when ``LATEX_SERVICE_URL`` is wrong).
    """
    try:
        return await asyncio.to_thread(compile_tex_to_pdf_bytes, tex)
    except LatexCompileError as e:
        log.warning("latex_compile_failed", message=e.args[0], log_tail=(e.log or "")[-500:])
        raise RuntimeError(f"LaTeX compile failed: {e.args[0]}") from e
