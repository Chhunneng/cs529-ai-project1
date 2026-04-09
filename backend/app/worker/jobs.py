from __future__ import annotations

from app.features.messages.jobs import handle_chat_message_job
from app.features.resume_outputs.jobs import handle_render_resume_job
from app.features.resumes.jobs import handle_parse_resume_job
from app.queue_jobs import ChatMessageJob, ParseResumeJob, RenderResumeJob


async def handle_job(job: ChatMessageJob | RenderResumeJob | ParseResumeJob) -> None:
    if isinstance(job, RenderResumeJob):
        await handle_render_resume_job(job)
        return
    if isinstance(job, ParseResumeJob):
        await handle_parse_resume_job(job)
        return
    if isinstance(job, ChatMessageJob):
        await handle_chat_message_job(job)
        return
    raise RuntimeError(f"Unknown job type: {type(job).__name__!r}")
