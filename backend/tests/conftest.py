"""Ensure required Settings env vars exist before ``app`` is imported by tests."""

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://resume_agent:resume_agent@127.0.0.1:5432/resume_agent",
)
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")
