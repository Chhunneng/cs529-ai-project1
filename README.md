# AI Resume Agent (Phase 1 scaffold)

PDF-first AI Resume Agent platform scaffold:

- **frontend**: Next.js + shadcn/ui — split-pane **resume PDF preview** and chat; assistant replies arrive via **SSE** after each `**POST .../messages**`
- **backend**: FastAPI + async SQLAlchemy + Alembic + structlog — includes `**pdflatex`** for resume PDF compilation (internal HTTP endpoint). The `**worker**` runs `**python -m app.worker.runner**` (Redis queue: `**resume_pdf_generation**`, parse resume, render resume output).
- **postgres**: persistence (Alembic baseline `**0001_baseline_pdf_first_chat**`; reset DB when upgrading from older schemas)
- **redis**: job queue (`queue:agent-jobs`) and **pub/sub** (`chat:reply:{user_message_id}`) so the worker can notify the API when an assistant message is saved

## Architecture (short)

For a **layered view, feature map, and diagrams**, see [backend/docs/ARCHITECTURE.md](backend/docs/ARCHITECTURE.md).

- The **browser** only talks to the **backend** (FastAPI).
- Chat turn: backend saves the user message and **enqueues** `**resume_pdf_generation**` in **Redis**; the **worker** runs the **OpenAI Agents** flow with **SQLAlchemy-backed session memory**, compiles LaTeX to PDF when possible, saves the assistant message (and optional **pdf artifact**), then **PUBLISH**es on Redis for **SSE**.
- The browser opens `**GET /api/v1/sessions/{id}/messages/assistant-stream?user_message_id=...`** (EventSource) after `**POST .../messages**`; keep `**NEXT_PUBLIC_API_BASE_URL**` pointed at the backend and ensure **CORS** allows your frontend origin (already set for localhost dev).
- For assistant replies to appear, `**OPENAI_API_KEY`** must be set for the **worker**, and the **worker** must be running **with access to the same Redis and Postgres** as the API.
- If you put **nginx** (or another proxy) in front of the API, disable buffering for SSE (`X-Accel-Buffering: no` is already set) and set **proxy read timeout** high enough (e.g. ≥ 120s) so the stream is not cut off while waiting for the worker.

## Quickstart (Docker)

1. Copy env file (safe defaults for local dev)

```bash
cp .env.example .env
```

Put a real `**OPENAI_API_KEY**` in `.env` for the worker. Optionally set `**INTERNAL_COMPILE_TOKEN**` in `.env` for both **backend** and **worker** so the compile endpoint is not open on your LAN (same value in both services).

1. Start core services (Postgres, Redis, backend, worker, frontend)

```bash
make up
```

For **live reload** while you edit code on the host (no container restart for normal Python/TS changes), use `**make dev`** instead. It merges `**docker-compose.dev.yml**`: the API runs `**uvicorn --reload**`, the worker restarts on `.py` changes via **watchfiles**, and the frontend runs `**next dev`** with the repo bind-mounted. After you change a `**Dockerfile**` or **dependencies**, run `**make dev-build`** once so images stay in sync.

1. **Run DB migrations (required before `/api/v1/resume-templates` and related tables)**

A fresh Postgres volume only has schema from migration `0001` until you upgrade. If you skip this step you may see `**relation "resume_templates" does not exist`**.

```bash
make migrate
```

Run `**make migrate**` after `make up` whenever you pull code that adds Alembic revisions.

1. Open the app

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:8000/healthz`

## PDF / LaTeX

Resume PDF generation uses `**pdflatex` inside the backend image**. The worker calls `**LATEX_SERVICE_URL`** (default in Compose: `http://backend:8000/api/v1/internal`), which resolves to `**POST /api/v1/internal/compile**`. No separate LaTeX container is required.

If you still have an older `.env` with `LATEX_SERVICE_URL=http://latex:8090`, update it to the URL above (or rely on the Compose default by removing the line).

## REST API (v1)

- **Create session**: `POST /api/v1/sessions` (empty body) → `{ "id": "<uuid>" }`
- **List messages**: `GET /api/v1/sessions/{session_id}/messages` (includes `content`, `pdf_artifact_id`, `pdf_download_url` when present)
- **Send message**: `POST /api/v1/sessions/{session_id}/messages` with JSON `{ "content": "...", "resume_template_id"?: null, "resume_id"?: null, "job_description_id"?: null }` → returns the **user** message row (includes `id`).
- **Delete message**: `DELETE /api/v1/sessions/{session_id}/messages/{message_id}` (trims OpenAI Agents SDK rows from the same cutoff time)
- **Download chat PDF**: `GET /api/v1/sessions/{session_id}/pdf-artifacts/{pdf_artifact_id}/file`
- **Assistant reply stream (SSE)**: `GET /api/v1/sessions/{session_id}/messages/assistant-stream?user_message_id=<uuid>` — one `message` event with JSON (`type`: `assistant` | `timeout` | `error`), then the connection closes.
- **Resumes / templates / resume-outputs**: see OpenAPI at `/docs` when the backend is running.

Legacy paths under `/api/v1/session/*`, `/api/v1/chat/*`, and `/api/v1/resume/*` have been **removed**; use the routes above.

## Makefile targets


| Target           | Purpose                                                                                                             |
| ---------------- | ------------------------------------------------------------------------------------------------------------------- |
| `make up`        | `docker compose up -d --build`                                                                                      |
| `make dev`       | Dev stack with bind mounts and auto-reload (foreground)                                                             |
| `make dev-build` | Same as `make dev` but rebuilds images (after Dockerfile or Python/Node dependency changes)                         |
| `make down`      | Stop stack                                                                                                          |
| `make migrate`   | `**alembic upgrade head`** in the backend container — run after `up` when the DB is new or after pulling migrations |
| `make logs`      | Tail logs                                                                                                           |


## Notes

- No auth/users yet (kept simple for scaffold).
- `**data/artifacts**` (host dir) is mounted for generated PDFs when using resume outputs + LaTeX.
- With `**make dev**`, if you change `**frontend/package.json**`, run `**npm ci**` inside the frontend container or remove the Compose volume `**frontend_dev_node_modules**` so dependencies reinstall.

