from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select, update

from app.core.config import settings
from app.db.session import AsyncSessionMaker
from app.models.job_description import JobDescription
from app.models.resume import Resume
from app.models.resume_output import ResumeOutput
from app.models.resume_template import ResumeTemplate
from app.queue_jobs import RenderResumeJob
from app.worker.latex_client import compile_tex_to_pdf
from app.worker.openai_resume_fill import generate_resume_fill_json
from app.worker.resume_fill_models import ResumeFillAtsV1
from app.worker.tex_renderer import load_template_tex, render_ats_v1

log = structlog.get_logger()


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
            .join(ResumeTemplate, ResumeOutput.template_id == ResumeTemplate.id)
            .where(ResumeOutput.id == output_id)
        )
        first = row.first()
        if first is None:
            raise RuntimeError("resume_output not found")
        ro, rt = first[0], first[1]
        return {
            "id": ro.id,
            "session_id": ro.session_id,
            "template_id": ro.template_id,
            "input_json": ro.input_json,
            "storage_path": rt.storage_path,
            "schema_json": rt.schema_json,
            "latex_source": rt.latex_source,
        }


async def _fetch_resume_text(resume_id: uuid.UUID) -> str | None:
    async with AsyncSessionMaker() as db:
        r = await db.get(Resume, resume_id)
        if r is None or r.parsed_json is None:
            return None
        return json.dumps(r.parsed_json, ensure_ascii=False)


async def _fetch_jd_text(session_id: uuid.UUID, jd_id: uuid.UUID) -> str | None:
    async with AsyncSessionMaker() as db:
        jd = await db.scalar(
            select(JobDescription).where(
                JobDescription.id == jd_id, JobDescription.session_id == session_id
            )
        )
        if jd is None:
            return None
        return str(jd.raw_text)


async def handle_render_resume(job: RenderResumeJob) -> None:
    output_id = uuid.UUID(job.output_id)
    log.info("render_resume_start", output_id=str(output_id))

    await _set_output_running(output_id)

    try:
        ctx = await _fetch_render_context(output_id)
        template_id = str(ctx["template_id"])
        storage_path = str(ctx["storage_path"])
        latex_source = ctx.get("latex_source")
        schema_json: dict[str, Any] = ctx["schema_json"]
        session_id = ctx["session_id"]
        if isinstance(session_id, uuid.UUID):
            sid = session_id
        else:
            sid = uuid.UUID(str(session_id))

        raw_input = ctx.get("input_json") or {}
        if isinstance(raw_input, str):
            raw_input = json.loads(raw_input)

        source_resume_id_raw = raw_input.get("source_resume_id")
        job_description_id_raw = raw_input.get("job_description_id")

        resume_context = ""
        if source_resume_id_raw:
            rid = uuid.UUID(str(source_resume_id_raw))
            rtxt = await _fetch_resume_text(rid)
            if rtxt:
                resume_context = rtxt

        jd_context: str | None = None
        if job_description_id_raw:
            jdid = uuid.UUID(str(job_description_id_raw))
            jd_context = await _fetch_jd_text(sid, jdid)

        fill_obj = await generate_resume_fill_json(
            schema=schema_json,
            resume_context=resume_context or "(no structured resume on file — invent plausible placeholder content)",
            job_description_context=jd_context,
        )

        if template_id != "ats-v1":
            raise RuntimeError(f"Unsupported template for render: {template_id}")

        data = ResumeFillAtsV1.model_validate(fill_obj)

        template_tex = None
        if isinstance(latex_source, str) and latex_source.strip():
            template_tex = latex_source
        else:
            base = Path(settings.templates_base_dir)
            template_tex = load_template_tex(base, storage_path)
        tex_body = render_ats_v1(template_tex=template_tex, data=data)

        out_dir = Path(settings.artifacts_dir) / str(output_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        tex_path = out_dir / "resume.tex"
        tex_path.write_text(tex_body, encoding="utf-8")

        pdf_bytes, _log_tail = await compile_tex_to_pdf(tex=tex_body)
        pdf_path = out_dir / "resume.pdf"
        pdf_path.write_bytes(pdf_bytes)

        merged_input: dict[str, Any] = dict(raw_input) if isinstance(raw_input, dict) else {}
        merged_input["fill"] = data.model_dump()

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