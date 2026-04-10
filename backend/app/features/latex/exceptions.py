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
