# Backend dependency map (refactor guide)

This file is a **refactor aid**: it summarizes the backend's **entrypoints**, **runtime flows**, and the **most fragile dependency edges** so we can refactor safely.

## Entrypoints

- **API server**: `backend/app/main.py`
  - mounts API router at `/api/v1` via `backend/app/api/v1/router.py`
  - uses dependency helpers in `backend/app/api/v1/deps.py`
- **Worker**: `backend/app/worker/runner.py`
  - main loop: dequeue job → dispatch handler (`backend/app/worker/jobs.py`)

## Job queue (Redis)

- **Wire format**: `backend/app/queue_jobs/payloads.py`
  - `serialize_job()` / `deserialize_job()` enforce the job contract
- **Queue implementation**: `backend/app/features/job_queue/redis.py`
  - `enqueue_job()` uses `RPUSH`
  - `dequeue_job()` uses `BLPOP`

## Worker job dispatch

`backend/app/worker/jobs.py` dispatches by job type to:

- `resume_pdf_generation` → `backend/app/features/pdf_generation/jobs.py`
- `parse_resume` → `backend/app/features/resumes/jobs.py`
- `render_resume` → `backend/app/features/resume_outputs/jobs.py` → `backend/app/worker/render_resume.py`

## High-level runtime flows

### Flow_A: HTTP request handling

`client` → `backend/app/main.py` → `backend/app/api/v1/router.py` → `backend/app/api/v1/routes/*` (thin shims) → `backend/app/features/*/api.py`

### Flow_B: user message → PDF agent → assistant reply

`features/sessions/*` enqueues `ResumePdfGenerationJob` → worker dequeues → `features/pdf_generation/jobs.py` runs Agents SDK (`app/llm/*`) → may compile LaTeX (`features/latex/service.py`) → persists messages/artifacts → publishes SSE notifications.

### Flow_C: resume output render automation (queued export)

`ResumeOutput` row exists → enqueue `RenderResumeJob` → worker dequeues → `worker/render_resume.py` builds `ResumeAgentContext` → `llm/render_resume_agent.py` calls `Runner.run(RENDER_RESUME_AUTOMATION_AGENT)` → writes `.tex` + compiles pdf → updates `ResumeOutput` status + paths.

## “Fragile” dependency edges (refactor carefully)

- **Queue contract compatibility**:
  - `queue_jobs/payloads.py` is shared by API enqueue + worker dequeue; changing job fields affects both.
- **Worker vs API separation**:
  - Worker must not import FastAPI route modules; routes must not import worker runtime.
- **LLM tools → feature services/repos**:
  - `app/llm/tools.py` correctly calls feature-layer services/repos for DB access; avoid adding raw SQL inside `app/llm/*`.
- **Render pipeline**:
  - `worker/render_resume.py` touches DB, filesystem, LaTeX compile, and LLM runner in one place; this is a good first target for SOLID extraction (service + adapters) because it reduces risk across the rest of the codebase.

