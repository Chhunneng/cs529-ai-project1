from fastapi import APIRouter

from app.api.v1.routes import (
    internal_latex,
    job_descriptions,
    resume_outputs,
    resume_templates,
    resumes,
    sessions,
)


api_router = APIRouter()
api_router.include_router(sessions.router)
api_router.include_router(resumes.router)
api_router.include_router(resume_templates.router)
api_router.include_router(resume_outputs.router)
api_router.include_router(job_descriptions.router)
api_router.include_router(internal_latex.router, prefix="/internal", tags=["internal"])
