# Worker, Redis queue, and SSE

Operator-focused reference: how background jobs run, how the chat stream gets notified, and which environment variables matter. For full stack layout see [backend/docs/ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md). For Docker quickstart see [README.md](../README.md).

## Single source of truth (sanity checks)

After refactors, these strings should stay aligned with code (grep from repo root):

```bash
rg 'queue:agent-jobs' backend/
rg 'CHAT_REPLY_CHANNEL_PREFIX|chat:reply:' backend/
```

- **Queue list key**: `settings.redis.queue_key` (default `queue:agent-jobs`) in [`backend/app/core/config.py`](../backend/app/core/config.py); used by [`backend/app/features/job_queue/redis.py`](../backend/app/features/job_queue/redis.py).
- **SSE notify**: [`backend/app/features/sessions/chat_reply_redis.py`](../backend/app/features/sessions/chat_reply_redis.py) builds the pub/sub channel (prefix + `user_message_id`) and `publish_chat_reply` when the worker finishes a chat turn.

## Process model

1. **API** (FastAPI) handles HTTP, writes rows, and calls `enqueue_job` with a JSON payload from [`backend/app/queue_jobs/payloads.py`](../backend/app/queue_jobs/payloads.py).
2. **Worker** (`python -m app.worker.runner`) runs [`backend/app/worker/runner.py`](../backend/app/worker/runner.py): blocking pop from Redis, then [`backend/app/worker/jobs.py`](../backend/app/worker/jobs.py) `handle_job` dispatches by `type`:
   - `resume_pdf_generation` → [`backend/app/features/pdf_generation/jobs.py`](../backend/app/features/pdf_generation/jobs.py)
   - `parse_resume` → [`backend/app/features/resumes/jobs.py`](../backend/app/features/resumes/jobs.py)
   - `render_resume` → [`backend/app/features/resume_outputs/jobs.py`](../backend/app/features/resume_outputs/jobs.py) (uses [`backend/app/worker/render_resume.py`](../backend/app/worker/render_resume.py) for OpenAI + LaTeX loop)

3. **LaTeX**: handlers call `compile_latex_to_pdf` in [`backend/app/features/latex/service.py`](../backend/app/features/latex/service.py), which POSTs to **`LATEX_SERVICE_URL`** (Compose default: `http://backend:8000/api/v1/internal/compile`). Same **`INTERNAL_COMPILE_TOKEN`** (if set) should be configured on **backend** and **worker**.

## Job payload summary

| `type` | Fields (see payloads module for exact schema) | Purpose |
|--------|-----------------------------------------------|---------|
| `resume_pdf_generation` | `session_id`, `user_message_id`, optional `resume_template_id`, `resume_id`, `job_description_id` | Run chat PDF agent; may attach artifact; publish SSE |
| `parse_resume` | `resume_id` | Extract structured JSON from uploaded resume text |
| `render_resume` | `output_id`, `template_id`, optional `session_id` | Fill template + compile PDF for a **resume output** row |

## Environment variables (worker and API)

Worker and API load the same [`Settings`](../backend/app/core/config.py) shape. Typical Docker / local entries (names as in `.env`):

| Variable | Purpose |
| -------- | ------- |
| `DATABASE_URL` | Async SQLAlchemy (`postgresql+asyncpg://…`) |
| `REDIS_URL` | Queue + pub/sub client |
| `QUEUE_KEY` | Optional override; default `queue:agent-jobs` |
| `OPENAI_API_KEY` | Required for worker jobs that call OpenAI |
| `OPENAI_MODEL` | Default model id for agents / extract |
| `RESUME_EXTRACT_MAX_INPUT_CHARS` | Cap on text sent to resume extract (default 24000) |
| `AGENT_CHAT_MAX_TURNS` / `AGENT_RENDER_MAX_TURNS` | Agent loop limits |
| `AGENT_RESUME_OVERVIEW_MAX_CHARS` / `AGENT_RESUME_EXCERPT_MAX_CHARS` / `AGENT_JD_TOOL_MAX_CHARS` / `AGENT_RESUME_SEARCH_MAX_SCAN_CHARS` | Tool context limits |
| `LATEX_SERVICE_URL` | Worker → backend internal compile base URL |
| `INTERNAL_COMPILE_TOKEN` | Optional shared secret for internal compile route |
| `ARTIFACTS_DIR` | Compiled PDFs and related files |
| `RESUME_UPLOADS_DIR` / `RESUME_UPLOAD_MAX_BYTES` | Resume file storage and size cap |

See [`.env.example`](../.env.example) for comments and Compose-oriented defaults.
