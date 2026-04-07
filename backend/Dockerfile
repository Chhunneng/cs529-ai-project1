FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app

# TeX Live: broad install for pdflatex résumés/templates (fewer missing .sty / font errors).
# lmodern: Latin Modern .sty (not always pulled by texlive metapackages alone).
# If something is still missing, install texlive-full in this RUN (multi‑GB image).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        lmodern \
        texlive-bibtex-extra \
        texlive-font-utils \
        texlive-fonts-extra \
        texlive-fonts-recommended \
        texlive-lang-european \
        texlive-latex-base \
        texlive-latex-extra \
        texlive-latex-recommended \
        texlive-pictures \
        texlive-plain-generic \
        texlive-publishers \
        texlive-science \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock /app/

RUN poetry install --no-ansi

COPY app /app/app
COPY templates /app/templates
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
