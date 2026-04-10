from __future__ import annotations

import base64
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class LatexCompileError(Exception):
    """Raised when pdflatex fails or PDF is missing."""

    def __init__(self, message: str, log: str) -> None:
        super().__init__(message)
        self.log = log


class LaTeXCompileFailed(RuntimeError):
    """Compile failure with structured detail for HTTP 422 and clients."""

    def __init__(self, detail: dict[str, Any]) -> None:
        self.detail = detail
        super().__init__(str(detail.get("message", "LaTeX compile failed")))


def compile_failure_detail(log: str, *, log_tail_client_max: int = 3500) -> dict[str, Any]:
    """
    Build the 422 body: ``message`` is one human-readable string so clients that only
    show ``message`` still get line number, context, and hint (avoids repr-of-dict UX).
    """
    f = summarize_pdflatex_log(log)
    tail = f.get("log_tail") or ""
    if len(tail) > log_tail_client_max:
        tail = "..." + tail[-(log_tail_client_max - 3) :]

    parts: list[str] = ["LaTeX compile failed"]
    if f.get("latex_error"):
        parts.append(str(f["latex_error"]))
    if f.get("line_number") is not None:
        parts.append(f"line {f['line_number']}")
    if f.get("line_context"):
        ctx = str(f["line_context"])
        if len(ctx) > 280:
            ctx = ctx[:277] + "..."
        parts.append(ctx)
    if f.get("hint"):
        parts.append(str(f["hint"]))

    return {
        "message": " — ".join(parts),
        "log_tail": tail,
        "latex_error": f.get("latex_error"),
        "line_number": f.get("line_number"),
        "line_context": f.get("line_context"),
        "hint": f.get("hint"),
    }


def summarize_pdflatex_log(log: str, *, tail_max: int = 8000) -> dict[str, Any]:
    """
    Pull the first error line, approximate source line number/context, and a short hint.
    pdflatex splits long source lines across log lines (e.g. l.9 \\\\g then '       eometry{...}').
    """
    tail = log[-tail_max:] if len(log) > tail_max else log
    lines = tail.splitlines()
    line_no: int | None = None
    line_context: str | None = None
    error_idx: int | None = None
    for i in range(len(lines) - 1, -1, -1):
        m = re.match(r"^l\.(\d+)\s*(.*)$", lines[i])
        if not m:
            continue
        line_no = int(m.group(1))
        parts = [m.group(2).rstrip()]
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if not nxt.strip():
                break
            if nxt.startswith(" ") or nxt.startswith("\t"):
                parts.append(nxt.strip())
                j += 1
                continue
            if nxt.startswith("!") or nxt.startswith("?"):
                break
            break
        line_context = " ".join(parts).strip() or None
        error_idx = i
        break

    latex_error: str | None = None
    if error_idx is not None:
        for k in range(error_idx - 1, -1, -1):
            if lines[k].startswith("! "):
                latex_error = lines[k][2:].strip()
                break

    hint: str | None = None
    if line_context and re.search(r"(?:\\){3,}", line_context):
        hint = (
            "This line has three or more consecutive backslashes—often from the model "
            "over-escaping. Use a single \\ before command names (e.g. \\Huge) and "
            "exactly \\\\ before optional vertical space like \\\\[6pt], not more."
        )
    elif line_context and re.search(r"(?:\\){2,}[a-zA-Z@]", line_context):
        hint = (
            "Two or more backslashes appear before a command name. "
            "LaTeX uses one backslash to start a command (e.g. \\textbf, not \\\\textbf)."
        )
    elif latex_error and "There's no line here to end" in latex_error:
        hint = (
            "TeX saw \\\\ (line break) where it is not allowed—often after \\\\ in a "
            "heading/group, or from doubled backslashes before a command."
        )
    elif latex_error and "Undefined control sequence" in latex_error:
        hint = "A command or macro is unknown—check spelling and \\usepackage lines."

    return {
        "log_tail": tail,
        "latex_error": latex_error,
        "line_number": line_no,
        "line_context": line_context,
        "hint": hint,
    }


def compile_latex_to_pdf_bytes(latex: str) -> tuple[bytes, str]:
    """
    Run pdflatex on a minimal .tex document; return PDF bytes and trimmed log.
    Blocking — call from asyncio.to_thread.
    """
    if shutil.which("pdflatex") is None:
        raise LatexCompileError("pdflatex not available in PATH", "")

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        tex_path = work / "doc.tex"
        tex_path.write_text(latex, encoding="utf-8")
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
