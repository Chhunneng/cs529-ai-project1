FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY worker/pyproject.toml worker/poetry.lock /app/

RUN poetry install --no-ansi

COPY worker/app /app/app
COPY backend/templates /app/templates

CMD ["python", "-m", "app.worker"]

