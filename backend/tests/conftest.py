"""Test environment defaults (keep tests self-contained).

The production app uses Postgres + Redis, but local/CI test runs should not require
external services to be running. We point the app at a local SQLite database and
create tables at test startup.
"""

import os

os.environ.setdefault(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./.test.db",
)
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")


import pytest_asyncio


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_test_db() -> None:
    from app.db.base import Base, import_models
    from app.db.session import engine

    import_models()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
