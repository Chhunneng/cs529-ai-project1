import asyncio

import structlog
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import engine
from app.services.queue import dequeue_job
from app.worker.jobs import handle_job

log = structlog.get_logger()


async def main() -> None:
    configure_logging(
        settings.app.log_level,
        json_logs=settings.log_json_format,
    )
    log.info("worker_starting")

    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))

    while True:
        job = await dequeue_job(timeout_seconds=5)
        if job is None:
            continue
        try:
            await handle_job(job)
        except Exception:
            log.exception("job_failed", job=job.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())
