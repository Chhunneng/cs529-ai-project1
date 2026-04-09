"""
Compatibility wrapper.

Routes moved to `app.features.job_descriptions.api`.
"""

from app.features.job_descriptions.api import router

__all__ = ["router"]
