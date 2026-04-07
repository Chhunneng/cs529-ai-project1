# Worker consolidation (reference)

## Verification grep (single source of truth)

After changes, these should each appear only where intended:

```bash
rg 'queue:agent-jobs' backend/
rg 'CHAT_REPLY_CHANNEL_PREFIX|chat:reply:' backend/
```

- Queue key: `app.core.config.Settings.queue_key` (default `queue:agent-jobs`) and `app.services.queue` use the same value.
- SSE notify: `app.services.chat_reply_notify` defines `chat_reply_channel` and `publish_chat_reply`.

## Environment variables (worker process)

Same as API plus worker-oriented defaults in `app.core.config`:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Async SQLAlchemy / asyncpg |
| `REDIS_URL` | Queue + pub/sub |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | LLM calls |
| `LATEX_SERVICE_URL` | Internal LaTeX compile HTTP (default `http://backend:8000/api/v1/internal`) |
| `TEMPLATES_BASE_DIR` | On-disk template root (default `/app/templates`) |
| `ARTIFACTS_DIR` | PDF output (default `/data/artifacts`) |
| `INTERNAL_COMPILE_TOKEN` | Optional header for LaTeX internal API |

## Orchestrator merge (April 2026)

Production chat routing follows the **former worker** `decide_next_action` behavior (intent classifier labels + session flags). The **former API-only** branch `upload_resume` → `ResumeParserAgent` is preserved for future callers that pass that intent string.
