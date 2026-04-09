## Features package

This folder groups code by **feature** (sessions, resumes, job_descriptions, …).

### Dependency rules (keep it scalable)
- **`api.py`** calls **`service.py`**
- **`service.py`** calls **`repo.py`** and external integrations (like `features/ai/*`)
- **`repo.py`** talks to the database (`app/db`) and ORM models
- Worker runners call **`jobs.py`** (per-feature)

### Avoid
- DB access inside OpenAI integration modules
- `services/*` importing `worker/*` (and vice-versa)

