from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, update

from app.db.session import AsyncSessionMaker
from app.domain.resume_outputs.contracts import ResumeOutputRenderContext
from app.models.resume_output import ResumeOutput
from app.models.resume_template import ResumeTemplate


class SqlAlchemyResumeOutputRepository:
    async def mark_running(self, output_id: uuid.UUID) -> None:
        async with AsyncSessionMaker() as db:
            await db.execute(
                update(ResumeOutput)
                .where(ResumeOutput.id == output_id)
                .values(status="running", error_text=None)
            )
            await db.commit()

    async def mark_failed(self, output_id: uuid.UUID, *, error_text: str) -> None:
        async with AsyncSessionMaker() as db:
            await db.execute(
                update(ResumeOutput)
                .where(ResumeOutput.id == output_id)
                .values(status="failed", error_text=error_text[:8000])
            )
            await db.commit()

    async def mark_succeeded(
        self,
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

    async def fetch_render_context(self, output_id: uuid.UUID) -> ResumeOutputRenderContext:
        async with AsyncSessionMaker() as db:
            result = await db.execute(
                select(ResumeOutput, ResumeTemplate)
                .outerjoin(ResumeTemplate, ResumeOutput.template_id == ResumeTemplate.id)
                .where(ResumeOutput.id == output_id)
            )
            rows = result.first()
            if rows is None:
                raise RuntimeError("resume_output not found")
            resume_output_row, resume_template_row = rows[0], rows[1]
            if resume_template_row is None:
                raise RuntimeError(
                    "Resume template was deleted or is missing; cannot render this output."
                )

            template_id = resume_output_row.template_id
            if template_id is None:
                raise RuntimeError("resume_output missing template_id")

            return ResumeOutputRenderContext(
                output_id=resume_output_row.id,
                template_id=uuid.UUID(str(template_id)),
                chat_session_id=resume_output_row.session_id,
                input_json=resume_output_row.input_json or {},
                template_latex_source=resume_template_row.latex_source or "",
            )

