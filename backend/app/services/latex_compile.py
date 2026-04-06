from __future__ import annotations

import base64
import shutil
import subprocess
import tempfile
from pathlib import Path


class LatexCompileError(Exception):
    """Raised when pdflatex fails or PDF is missing."""

    def __init__(self, message: str, log: str) -> None:
        super().__init__(message)
        self.log = log


def compile_tex_to_pdf_bytes(tex: str) -> tuple[bytes, str]:
    """
    Run pdflatex on a minimal .tex document; return PDF bytes and trimmed log.
    Blocking — call from asyncio.to_thread.
    """
    if shutil.which("pdflatex") is None:
        raise LatexCompileError("pdflatex not available in PATH", "")

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        tex_path = work / "doc.tex"
        tex_path.write_text(tex, encoding="utf-8")
        proc = subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={work}",
                str(tex_path),
            ],
            cwd=work,
            capture_output=True,
            text=True,
            timeout=120,
        )
        pdf_path = work / "doc.pdf"
        log_parts = [proc.stdout or "", proc.stderr or ""]
        full_log = "\n".join(log_parts)
        if proc.returncode != 0 or not pdf_path.is_file():
            raise LatexCompileError(
                "LaTeX compile failed",
                full_log[-8000:],
            )
        pdf_bytes = pdf_path.read_bytes()
        return pdf_bytes, full_log[-8000:]


def pdf_to_base64(pdf_bytes: bytes) -> str:
    return base64.b64encode(pdf_bytes).decode("ascii")
