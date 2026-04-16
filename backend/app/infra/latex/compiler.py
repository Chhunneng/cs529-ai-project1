from __future__ import annotations

from app.features.latex.service import compile_latex_to_pdf


class ServerLatexCompiler:
    async def compile_pdf(self, *, latex: str) -> bytes:
        pdf_bytes, _log_tail = await compile_latex_to_pdf(latex=latex)
        return pdf_bytes

