from __future__ import annotations

from app.features.pdf_generation.jobs import handle_resume_pdf_generation_job
from app.features.interview_practice.jobs import (
    handle_interview_generate_job,
    handle_interview_generate_persist_job,
    handle_interview_refine_job,
    handle_interview_refine_persist_job,
)
from app.features.resume_outputs.jobs import handle_render_resume_job
from app.features.resumes.jobs import handle_parse_resume_job
from app.queue_jobs import (
    InterviewGenerateJob,
    InterviewGeneratePersistJob,
    InterviewRefineJob,
    InterviewRefinePersistJob,
    ParseResumeJob,
    RenderResumeJob,
    ResumePdfGenerationJob,
)


async def handle_job(
    job: ResumePdfGenerationJob
    | RenderResumeJob
    | ParseResumeJob
    | InterviewGenerateJob
    | InterviewRefineJob
    | InterviewGeneratePersistJob
    | InterviewRefinePersistJob,
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
    if isinstance(job, InterviewGenerateJob):
        await handle_interview_generate_job(job)
        return
    if isinstance(job, InterviewRefineJob):
        await handle_interview_refine_job(job)
        return
    if isinstance(job, InterviewGeneratePersistJob):
        await handle_interview_generate_persist_job(job)
        return
    if isinstance(job, InterviewRefinePersistJob):
        await handle_interview_refine_persist_job(job)
        return
    raise RuntimeError(f"Unknown job type: {type(job).__name__!r}")
