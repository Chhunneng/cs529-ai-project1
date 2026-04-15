from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select, update

from app.core.config import settings
from app.db.session import AsyncSessionMaker
from app.models.resume_output import ResumeOutput
from app.models.resume_template import ResumeTemplate
from app.queue_jobs import RenderResumeJob
from app.features.latex.service import compile_latex_to_pdf
from app.llm.context import ResumeAgentContext
from app.llm.render_resume_agent import run_render_resume_automation

log = structlog.get_logger()

_RENDER_BATCH_USER_MESSAGE = (
    "Generate the final resume LaTeX for this queued PDF export. "
    "Use tools as needed, then return latex_resume_content with the full compilable document. "
    "When a job description is linked, maximize honest keyword and phrase overlap with the JD: "
    "rephrase existing bullets to use JD vocabulary only where the resume already supports it; "
    "keep every skill or capability that appears in the loaded resume (union with defensible JD terms); "
    "prefer ATS-friendly bullets and headings. Do not invent employers, dates, tools, or metrics."
)


async def _set_output_running(output_id: uuid.UUID) -> None:
    async with AsyncSessionMaker() as db:
        await db.execute(
            update(ResumeOutput)
            .where(ResumeOutput.id == output_id)
            .values(status="running", error_text=None)
        )
        await db.commit()


async def _set_output_failed(output_id: uuid.UUID, error_text: str) -> None:
    async with AsyncSessionMaker() as db:
        await db.execute(
            update(ResumeOutput)
            .where(ResumeOutput.id == output_id)
            .values(status="failed", error_text=error_text[:8000])
        )
        await db.commit()


async def _set_output_succeeded(
    output_id: uuid.UUID,
    *,
    input_json: dict[str, Any],
    tex_path: str,
    pdf_path: str,
) -> None:
    async with AsyncSessionMaker() as db:
        await db.execute(
            update(ResumeOutput)
            .where(ResumeOutput.id == output_id)
            .values(
                status="succeeded",
                input_json=input_json,
                tex_path=tex_path,
                pdf_path=pdf_path,
                error_text=None,
            )
        )
        await db.commit()


async def _fetch_render_context(output_id: uuid.UUID) -> dict[str, Any]:
    async with AsyncSessionMaker() as db:
        row = await db.execute(
            select(ResumeOutput, ResumeTemplate)
            .outerjoin(ResumeTemplate, ResumeOutput.template_id == ResumeTemplate.id)
            .where(ResumeOutput.id == output_id)
        )
        first = row.first()
        if first is None:
            raise RuntimeError("resume_output not found")
        ro, rt = first[0], first[1]
        if rt is None:
            raise RuntimeError(
                "Resume template was deleted or is missing; cannot render this output."
            )
        return {
            "id": ro.id,
            "session_id": ro.session_id,
            "template_id": ro.template_id,
            "input_json": ro.input_json,
            "latex_source": rt.latex_source,
        }


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
    job_description_id: uuid.UUID | None = None
    if source_resume_id_raw:
        resume_id = uuid.UUID(str(source_resume_id_raw))
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


async def handle_render_resume(job: RenderResumeJob) -> None:
    output_id = uuid.UUID(job.output_id)
    log.info("render_resume_start", output_id=str(output_id))

    await _set_output_running(output_id)

    try:
        ctx = await _fetch_render_context(output_id)
        template_id = ctx["template_id"]
        if not isinstance(template_id, uuid.UUID):
            template_id = uuid.UUID(str(template_id))

        latex_source = ctx.get("latex_source")
        if not isinstance(latex_source, str) or not latex_source.strip():
            raise RuntimeError(f"Template {template_id} has no LaTeX source in the database")

        raw_input = _coerce_input_json(ctx.get("input_json"))
        chat_session_id = ctx.get("session_id")
        if chat_session_id is not None and not isinstance(chat_session_id, uuid.UUID):
            chat_session_id = uuid.UUID(str(chat_session_id))

        tool_context = _build_resume_agent_context(
            output_id=output_id,
            template_id=template_id,
            raw_input=raw_input,
            chat_session_id=chat_session_id if isinstance(chat_session_id, uuid.UUID) else None,
        )

        agent_output = await run_render_resume_automation(
            user_prompt=_RENDER_BATCH_USER_MESSAGE,
            tool_context=tool_context,
        )
        tex_body = agent_output.latex_resume_content.strip()
        if not tex_body:
            raise RuntimeError("Render automation returned empty LaTeX")

        out_dir = Path(settings.storage.artifacts_dir) / str(output_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        tex_path = out_dir / "resume.tex"
        tex_path.write_text(tex_body, encoding="utf-8")

        pdf_bytes, _log_tail = await compile_latex_to_pdf(latex=tex_body)
        pdf_path = out_dir / "resume.pdf"
        pdf_path.write_bytes(pdf_bytes)

        merged_input: dict[str, Any] = dict(raw_input) if isinstance(raw_input, dict) else {}
        merged_input["generation"] = "agent_latex_v1"
        merged_input["tool_trace"] = list(tool_context.tool_trace)

        await _set_output_succeeded(
            output_id,
            input_json=merged_input,
            tex_path=str(tex_path.resolve()),
            pdf_path=str(pdf_path.resolve()),
        )
        log.info("render_resume_done", output_id=str(output_id))
    except Exception as e:
        err = str(e)[:8000]
        log.exception("render_resume_failed", output_id=str(output_id))
        await _set_output_failed(output_id, err)
        raise
