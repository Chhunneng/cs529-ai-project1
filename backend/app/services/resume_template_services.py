"""Resume template persistence helpers (preview compile, etc.)."""

from __future__ import annotations

from app.features.latex.service import compile_tex_to_pdf


async def build_template_preview_pdf(*, latex_source: str) -> bytes:
    """
    Compile LaTeX as-is to PDF bytes (no placeholder filling).

    The source must be valid standalone TeX for pdflatex. Filled-output rendering
    with schema-specific data is handled by the worker.
    """
    tex = latex_source.strip()
    if not tex:
        raise ValueError("latex_source is empty")
    pdf_bytes, _log = await compile_tex_to_pdf(tex=tex)
    return pdf_bytes
