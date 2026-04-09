"""
Compatibility wrapper.

Routes moved to `app.features.resume_outputs.api`.
"""

from app.features.resume_outputs.api import router

__all__ = ["router"]
