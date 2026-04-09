"""
Compatibility wrapper.

Routes moved to `app.features.resumes.api`.
"""

from app.features.resumes.api import router

__all__ = ["router"]
