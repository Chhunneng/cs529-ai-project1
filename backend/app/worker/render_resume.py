import uuid

import structlog

from app.application.resume_outputs.render_resume import RenderResumeOutputService
from app.infra.db.resume_outputs.repository import SqlAlchemyResumeOutputRepository
from app.infra.latex.compiler import ServerLatexCompiler
from app.infra.llm.render_resume_automation import RenderResumeAutomationClient
from app.infra.storage.artifacts import LocalArtifactStore
from app.queue_jobs import RenderResumeJob

log = structlog.get_logger()

_RENDER_BATCH_USER_MESSAGE = (
    "Generate the final resume LaTeX for this queued PDF export. "
    "Use tools as needed, then return latex_resume_content with the full compilable document. "
    "When a job description is linked, maximize honest keyword and phrase overlap with the JD: "
    "rephrase existing bullets to use JD vocabulary only where the resume already supports it; "
    "keep every skill or capability that appears in the loaded resume (union with defensible JD terms); "
    "prefer ATS-friendly bullets and headings. Do not invent employers, dates, tools, or metrics."
)


async def handle_render_resume(job: RenderResumeJob) -> None:
    output_id = uuid.UUID(job.output_id)
    service = RenderResumeOutputService(
        repository=SqlAlchemyResumeOutputRepository(),
        render_automation=RenderResumeAutomationClient(),
        latex_compiler=ServerLatexCompiler(),
        artifact_store=LocalArtifactStore(),
    )
    await service.run(output_id=output_id, user_prompt=_RENDER_BATCH_USER_MESSAGE)
