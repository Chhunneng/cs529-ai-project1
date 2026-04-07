from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import structlog
from app.queue_jobs import RenderResumeJob
from sqlalchemy import text

from app.config import settings
from app.db import AsyncSessionMaker
from app.latex_client import compile_tex_to_pdf
from app.openai_resume_fill import generate_resume_fill_json
from app.resume_fill_models import ResumeFillAtsV1
from app.tex_renderer import load_template_tex, render_ats_v1

log = structlog.get_logger()


async def _set_output_running(output_id: uuid.UUID) -> None:
    sql = text(
        """
        UPDATE resume_outputs
        SET status = 'running', error_text = NULL, updated_at = now()
        WHERE id = :id
        """
    )
    async with AsyncSessionMaker() as db:
        await db.execute(sql, {"id": str(output_id)})
        await db.commit()


async def _set_output_failed(output_id: uuid.UUID, error_text: str) -> None:
    sql = text(
        """
        UPDATE resume_outputs
        SET status = 'failed', error_text = :error_text, updated_at = now()
        WHERE id = :id
        """
    )
    async with AsyncSessionMaker() as db:
        await db.execute(sql, {"id": str(output_id), "error_text": error_text[:8000]})
        await db.commit()


async def _set_output_succeeded(
    output_id: uuid.UUID,
    *,
    input_json: dict[str, Any],
    tex_path: str,
    pdf_path: str,
) -> None:
    sql = text(
        """
        UPDATE resume_outputs
        SET status = 'succeeded',
            input_json = CAST(:input_json AS jsonb),
            tex_path = :tex_path,
            pdf_path = :pdf_path,
            error_text = NULL,
            updated_at = now()
        WHERE id = :id
        """
    )
    async with AsyncSessionMaker() as db:
        await db.execute(
            sql,
            {
                "id": str(output_id),
                "input_json": json.dumps(input_json),
                "tex_path": tex_path,
                "pdf_path": pdf_path,
            },
        )
        await db.commit()


async def _fetch_render_context(output_id: uuid.UUID) -> dict[str, Any]:
    sql = text(
        """
        SELECT ro.id, ro.session_id, ro.template_id, ro.input_json,
               rt.storage_path, rt.schema_json, rt.latex_source
        FROM resume_outputs ro
        JOIN resume_templates rt ON rt.id = ro.template_id
        WHERE ro.id = :id
        """
    )
    async with AsyncSessionMaker() as db:
        result = await db.execute(sql, {"id": str(output_id)})
        row = result.first()
        if row is None:
            raise RuntimeError("resume_output not found")
        cols = row._mapping
        return dict(cols)


async def _fetch_resume_text(resume_id: uuid.UUID) -> str | None:
    sql = text("SELECT parsed_json FROM resumes WHERE id = :id")
    async with AsyncSessionMaker() as db:
        result = await db.execute(sql, {"id": str(resume_id)})
        row = result.first()
        if row is None or row[0] is None:
            return None
        return json.dumps(row[0], ensure_ascii=False)


async def _fetch_jd_text(session_id: uuid.UUID, jd_id: uuid.UUID) -> str | None:
    sql = text(
        """
        SELECT raw_text FROM job_descriptions
        WHERE id = :id AND session_id = :session_id
        """
    )
    async with AsyncSessionMaker() as db:
        result = await db.execute(
            sql, {"id": str(jd_id), "session_id": str(session_id)}
        )
        row = result.first()
        if row is None:
            return None
        return str(row[0])


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
