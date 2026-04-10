## Features package

This folder groups code by **feature** (sessions, resumes, job_descriptions, …).

### Dependency rules (keep it scalable)
- **`api.py`** calls **`service.py`**
- **`service.py`** calls **`repo.py`** and external integrations (like `app.llm/*`)
- **`repo.py`** talks to the database (`app/db`) and ORM models
- Worker runners call **`jobs.py`** (per-feature)

### Avoid
- DB access inside `app.llm` (keep DB in `repo.py`)
- `services/*` importing `worker/*` (and vice-versa)

