from __future__ import annotations

import json
import uuid
from typing import Any

import structlog

from app.domain.resume_outputs.contracts import (
    ArtifactStore,
    LatexCompiler,
    RenderAutomation,
    ResumeOutputRepository,
)
from app.llm.context import ResumeAgentContext

log = structlog.get_logger()


def _coerce_input_json(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return dict(raw) if isinstance(raw, dict) else {}


def _build_resume_agent_context(
    *,
    output_id: uuid.UUID,
    template_id: uuid.UUID,
    raw_input: dict[str, Any],
    chat_session_id: uuid.UUID | None,
) -> ResumeAgentContext:
    source_resume_id_raw = raw_input.get("source_resume_id")
    job_description_id_raw = raw_input.get("job_description_id")

    resume_id: uuid.UUID | None = None
    if source_resume_id_raw:
        resume_id = uuid.UUID(str(source_resume_id_raw))

    job_description_id: uuid.UUID | None = None
    if job_description_id_raw:
        job_description_id = uuid.UUID(str(job_description_id_raw))

    return ResumeAgentContext(
        tool_trace=[],
        job_description_id=job_description_id,
        chat_session_id=chat_session_id,
        render_output_id=output_id,
        resume_id=resume_id,
        resume_template_id=template_id,
    )


class RenderResumeOutputService:
    def __init__(
        self,
        *,
        repository: ResumeOutputRepository,
        render_automation: RenderAutomation,
        latex_compiler: LatexCompiler,
        artifact_store: ArtifactStore,
    ) -> None:
        self._repository = repository
        self._render_automation = render_automation
        self._latex_compiler = latex_compiler
        self._artifact_store = artifact_store

    async def run(self, *, output_id: uuid.UUID, user_prompt: str) -> None:
        log.info("render_resume_start", output_id=str(output_id))
        await self._repository.mark_running(output_id)

        try:
            ctx = await self._repository.fetch_render_context(output_id)
            if not ctx.template_latex_source.strip():
                raise RuntimeError(
                    f"Template {ctx.template_id} has no LaTeX source in the database"
                )

            raw_input = _coerce_input_json(ctx.input_json)
            tool_context = _build_resume_agent_context(
                output_id=output_id,
                template_id=ctx.template_id,
                raw_input=raw_input,
                chat_session_id=ctx.chat_session_id,
            )

            tex, tool_trace = await self._render_automation.generate_latex(
                user_prompt=user_prompt,
                tool_context=tool_context,
            )
            tex = tex.strip()
            if not tex:
                raise RuntimeError("Render automation returned empty LaTeX")

            pdf_bytes = await self._latex_compiler.compile_pdf(latex=tex)
            tex_path, pdf_path = self._artifact_store.write_tex_pdf(
                output_id=output_id,
                tex=tex,
                pdf_bytes=pdf_bytes,
            )

            merged_input: dict[str, Any] = dict(raw_input)
            merged_input["generation"] = "agent_latex_v1"
            merged_input["tool_trace"] = list(tool_trace)

            await self._repository.mark_succeeded(
                output_id,
                input_json=merged_input,
                tex_path=tex_path,
                pdf_path=pdf_path,
            )
            log.info("render_resume_done", output_id=str(output_id))
        except Exception as e:
            log.exception("render_resume_failed", output_id=str(output_id))
            await self._repository.mark_failed(output_id, error_text=str(e)[:8000])
            raise

