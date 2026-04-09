from __future__ import annotations

from app.queue_jobs import RenderResumeJob
from app.worker.render_resume import handle_render_resume


async def handle_render_resume_job(job: RenderResumeJob) -> None:
    await handle_render_resume(job)

