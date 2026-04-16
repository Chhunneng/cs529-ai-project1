from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ResumeOutputRenderContext:
    output_id: uuid.UUID
    template_id: uuid.UUID
    chat_session_id: uuid.UUID | None
    input_json: dict[str, Any]
    template_latex_source: str


class ResumeOutputRepository(Protocol):
    async def mark_running(self, output_id: uuid.UUID) -> None: ...
    async def mark_failed(self, output_id: uuid.UUID, *, error_text: str) -> None: ...
    async def mark_succeeded(
        self,
        output_id: uuid.UUID,
        *,
        input_json: dict[str, Any],
        tex_path: str,
        pdf_path: str,
    ) -> None: ...
    async def fetch_render_context(self, output_id: uuid.UUID) -> ResumeOutputRenderContext: ...


class RenderAutomation(Protocol):
    async def generate_latex(self, *, user_prompt: str, tool_context: Any) -> tuple[str, list[str]]: ...


class LatexCompiler(Protocol):
    async def compile_pdf(self, *, latex: str) -> bytes: ...


class ArtifactStore(Protocol):
    def write_tex_pdf(
        self,
        *,
        output_id: uuid.UUID,
        tex: str,
        pdf_bytes: bytes,
    ) -> tuple[str, str]: ...

