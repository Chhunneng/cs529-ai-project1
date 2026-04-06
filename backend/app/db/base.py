from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def import_models() -> None:
    # Ensure models are imported for Alembic autogenerate (later).
    from app import models as _models  # noqa: F401

