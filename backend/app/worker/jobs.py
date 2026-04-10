from __future__ import annotations

from app.features.pdf_generation.jobs import handle_resume_pdf_generation_job
from app.features.resume_outputs.jobs import handle_render_resume_job
from app.features.resumes.jobs import handle_parse_resume_job
from app.queue_jobs import ParseResumeJob, RenderResumeJob, ResumePdfGenerationJob


async def handle_job(
    job: ResumePdfGenerationJob | RenderResumeJob | ParseResumeJob,
) -> None:
    if isinstance(job, RenderResumeJob):
        await handle_render_resume_job(job)
        return
    if isinstance(job, ParseResumeJob):
        await handle_parse_resume_job(job)
        return
    if isinstance(job, ResumePdfGenerationJob):
        await handle_resume_pdf_generation_job(job)
        return
    raise RuntimeError(f"Unknown job type: {type(job).__name__!r}")
