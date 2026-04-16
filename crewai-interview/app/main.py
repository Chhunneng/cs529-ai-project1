from __future__ import annotations

from fastapi import FastAPI

from app.crewai_mcp_support import ensure_crewai_log_filter
from app.interview_tasks import GenerateBody, RefineBody, run_generate, run_refine

ensure_crewai_log_filter()

app = FastAPI(title="CrewAI Interview Service", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.post("/v1/interview/generate")
def generate(body: GenerateBody) -> dict:
    return run_generate(body)


@app.post("/v1/interview/refine")
def refine(body: RefineBody) -> dict:
    return run_refine(body)
