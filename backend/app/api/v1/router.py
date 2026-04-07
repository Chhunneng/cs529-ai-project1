from fastapi import APIRouter

from app.api.v1.routes import (
    internal_latex,
    rest_job_descriptions,
    rest_resume_outputs,
    rest_resume_templates,
    rest_resumes,
    rest_sessions,
)


api_router = APIRouter()
api_router.include_router(rest_sessions.router)
api_router.include_router(rest_resumes.router)
api_router.include_router(rest_resume_templates.router)
api_router.include_router(rest_resume_outputs.router)
api_router.include_router(rest_job_descriptions.router)
api_router.include_router(internal_latex.router, prefix="/internal", tags=["internal"])
